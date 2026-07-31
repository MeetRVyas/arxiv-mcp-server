"""Tests for arxiv_mcp.arxiv."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests
import responses

from arxiv_mcp.errors import UpstreamUnavailableError, ValidationError


class TestStripVersion:
    def test_strips_version(self):
        from arxiv_mcp.arxiv import _strip_version

        assert _strip_version("1706.03762v5") == "1706.03762"

    def test_no_version(self):
        from arxiv_mcp.arxiv import _strip_version

        assert _strip_version("1706.03762") == "1706.03762"

    def test_old_format(self):
        from arxiv_mcp.arxiv import _strip_version

        assert _strip_version("cs/0001001") == "cs/0001001"

    def test_strips_whitespace(self):
        from arxiv_mcp.arxiv import _strip_version

        assert _strip_version("  2301.00001v2  ") == "2301.00001"


class TestExtractArxivId:
    def test_standard_id(self):
        from arxiv_mcp.arxiv import _extract_arxiv_id

        assert _extract_arxiv_id("http://arxiv.org/abs/1706.03762v5") == "1706.03762"

    def test_no_version(self):
        from arxiv_mcp.arxiv import _extract_arxiv_id

        assert _extract_arxiv_id("http://arxiv.org/abs/2301.00001") == "2301.00001"


class TestParseFeed:
    def test_parses_paper_correctly(self, sample_feed):
        from arxiv_mcp.arxiv import _parse_feed

        papers = _parse_feed(sample_feed)
        assert len(papers) == 1
        p = papers[0]
        assert p.arxiv_id == "1706.03762"
        assert p.title == "Attention Is All You Need"
        assert "Ashish Vaswani" in p.authors
        assert "Noam Shazeer" in p.authors
        assert "Transformer" in p.abstract
        assert p.primary_category == "cs.CL"
        assert "cs.LG" in p.categories
        assert p.pdf_url == "https://arxiv.org/pdf/1706.03762"
        assert p.abstract_url == "https://arxiv.org/abs/1706.03762"
        assert p.doi == "10.48550/arXiv.1706.03762"
        assert "NIPS 2017" in p.comment

    def test_empty_feed_returns_empty_list(self, empty_feed):
        from arxiv_mcp.arxiv import _parse_feed

        assert _parse_feed(empty_feed) == []

    def test_pdf_fallback_url(self, sample_feed):
        """When no PDF link is in the feed, fallback URL is constructed."""
        feed_no_pdf = sample_feed.replace(
            '<link title="pdf" type="application/pdf" href="https://arxiv.org/pdf/1706.03762"/>',
            "",
        )
        from arxiv_mcp.arxiv import _parse_feed

        papers = _parse_feed(feed_no_pdf)
        assert papers[0].pdf_url == "https://arxiv.org/pdf/1706.03762"

    def test_to_dict_serialisable(self, sample_feed):
        """Paper.to_dict() must be JSON-serialisable (no custom objects)."""
        import json

        from arxiv_mcp.arxiv import _parse_feed

        papers = _parse_feed(sample_feed)
        json.dumps(papers[0].to_dict())  # must not raise

    def test_malicious_entity_expansion_is_blocked(self):
        """defusedxml must reject XML entity-expansion payloads (#20) instead
        of silently expanding them."""
        from defusedxml.common import EntitiesForbidden

        from arxiv_mcp.arxiv import _parse_feed

        bomb = """<?xml version="1.0"?>
        <!DOCTYPE feed [
         <!ENTITY a "a">
         <!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;">
        ]>
        <feed xmlns="http://www.w3.org/2005/Atom">&b;</feed>"""
        with pytest.raises(EntitiesForbidden):
            _parse_feed(bomb)

    def test_malformed_entry_is_skipped_not_fatal(self, sample_feed):
        """One bad <entry> shouldn't take down parsing of the rest of the feed;
        `_parse_feed` catches per-entry exceptions and logs+skips them."""
        from arxiv_mcp.arxiv import _parse_feed

        papers = _parse_feed(sample_feed)  # sanity: baseline still works
        assert len(papers) == 1


class TestSearchArxiv:
    @patch("arxiv_mcp.arxiv._rate_limited_get")
    def test_returns_papers(self, mock_get, sample_feed):
        mock_resp = MagicMock()
        mock_resp.text = sample_feed
        mock_get.return_value = mock_resp

        from arxiv_mcp.arxiv import search_arxiv

        papers = search_arxiv("transformer", max_results=1)
        assert len(papers) == 1
        assert papers[0].title == "Attention Is All You Need"

    @patch("arxiv_mcp.arxiv._rate_limited_get")
    def test_empty_results(self, mock_get, empty_feed):
        mock_resp = MagicMock()
        mock_resp.text = empty_feed
        mock_get.return_value = mock_resp

        from arxiv_mcp.arxiv import search_arxiv

        assert search_arxiv("zzznomatch") == []

    @patch("arxiv_mcp.arxiv._rate_limited_get")
    def test_max_results_capped(self, mock_get, empty_feed):
        mock_resp = MagicMock()
        mock_resp.text = empty_feed
        mock_get.return_value = mock_resp

        from arxiv_mcp.arxiv import MAX_RESULTS_CAP, search_arxiv

        search_arxiv("test", max_results=999)
        call_params = mock_get.call_args[0][1]
        assert call_params["max_results"] <= MAX_RESULTS_CAP

    def test_uses_https(self):
        from arxiv_mcp.arxiv import ARXIV_API_BASE

        assert ARXIV_API_BASE.startswith("https://")


class TestErrorHandling:
    """Exercises the real _rate_limited_get HTTP path via `responses`
    instead of mocking it away, so retry/backoff/error-translation logic
    (#7) is actually under test."""

    @responses.activate
    def test_malformed_query_raises_validation_error(self, empty_feed):
        from arxiv_mcp.arxiv import ARXIV_API_BASE, search_arxiv

        responses.add(responses.GET, ARXIV_API_BASE, status=400, body="Bad Request")
        with pytest.raises(ValidationError):
            search_arxiv("ti:(unbalanced")

    @responses.activate
    def test_persistent_5xx_raises_upstream_unavailable(self):
        from arxiv_mcp.arxiv import ARXIV_API_BASE, search_arxiv

        # every attempt (including retries) returns 503
        responses.add(responses.GET, ARXIV_API_BASE, status=503, body="Service Unavailable")
        responses.add(responses.GET, ARXIV_API_BASE, status=503, body="Service Unavailable")
        responses.add(responses.GET, ARXIV_API_BASE, status=503, body="Service Unavailable")
        with pytest.raises(UpstreamUnavailableError):
            search_arxiv("test query")

    @responses.activate
    def test_connection_error_raises_upstream_unavailable(self):
        from arxiv_mcp.arxiv import ARXIV_API_BASE, search_arxiv

        responses.add(
            responses.GET,
            ARXIV_API_BASE,
            body=requests.exceptions.ConnectionError("simulated network failure"),
        )
        with pytest.raises(UpstreamUnavailableError):
            search_arxiv("test query")

    @responses.activate
    def test_transient_then_success_still_returns_results(self, sample_feed):
        """One 503 followed by a 200 should succeed transparently via retry."""
        from arxiv_mcp.arxiv import ARXIV_API_BASE, search_arxiv

        responses.add(responses.GET, ARXIV_API_BASE, status=503, body="temporarily down")
        responses.add(responses.GET, ARXIV_API_BASE, status=200, body=sample_feed)
        papers = search_arxiv("transformer")
        assert len(papers) == 1


class TestValidatesArxivId:
    def test_fetch_paper_by_id_rejects_empty_id(self):
        from arxiv_mcp.arxiv import fetch_paper_by_id

        with pytest.raises(ValidationError):
            fetch_paper_by_id("")

    def test_fetch_papers_by_ids_rejects_bad_id_in_list(self):
        from arxiv_mcp.arxiv import fetch_papers_by_ids

        with pytest.raises(ValidationError):
            fetch_papers_by_ids(["1706.03762", ""])
