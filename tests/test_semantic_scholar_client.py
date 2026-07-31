"""Tests for arxiv_mcp.semantic_scholar."""

from __future__ import annotations

import pytest
import requests
import responses

from arxiv_mcp.errors import UpstreamUnavailableError


@pytest.fixture
def ss_paper_url():
    from arxiv_mcp.semantic_scholar import SS_BASE

    return f"{SS_BASE}/paper/arXiv:1706.03762"


class TestGetPaperMetadata:
    @responses.activate
    def test_success(self, ss_paper_url):
        responses.add(
            responses.GET,
            ss_paper_url,
            json={
                "paperId": "abc123",
                "title": "Attention Is All You Need",
                "authors": [{"name": "A. Vaswani"}],
                "year": 2017,
                "citationCount": 100000,
                "influentialCitationCount": 20000,
                "venue": "NeurIPS",
                "fieldsOfStudy": ["Computer Science"],
                "externalIds": {"ArXiv": "1706.03762"},
            },
            status=200,
        )
        from arxiv_mcp.semantic_scholar import get_paper_metadata

        result = get_paper_metadata("1706.03762")
        assert result is not None
        assert result["citation_count"] == 100000
        assert result["semantic_scholar_id"] == "abc123"

    @responses.activate
    def test_not_indexed_returns_none_not_error(self, ss_paper_url):
        """A 404 (paper simply not indexed yet) is a normal, expected
        outcome — it must return None, not raise (#7)."""
        responses.add(responses.GET, ss_paper_url, status=404, json={"error": "not found"})
        from arxiv_mcp.semantic_scholar import get_paper_metadata

        assert get_paper_metadata("1706.03762") is None

    @responses.activate
    def test_upstream_down_raises_distinct_error(self, ss_paper_url):
        """A genuine outage must be distinguishable from "not indexed" (#7) —
        it raises instead of silently returning None."""
        responses.add(responses.GET, ss_paper_url, status=503, body="down")
        responses.add(responses.GET, ss_paper_url, status=503, body="down")
        responses.add(responses.GET, ss_paper_url, status=503, body="down")
        from arxiv_mcp.semantic_scholar import get_paper_metadata

        with pytest.raises(UpstreamUnavailableError):
            get_paper_metadata("1706.03762")

    @responses.activate
    def test_connection_error_raises_upstream_unavailable(self, ss_paper_url):
        responses.add(
            responses.GET,
            ss_paper_url,
            body=requests.exceptions.ConnectionError("simulated failure"),
        )
        from arxiv_mcp.semantic_scholar import get_paper_metadata

        with pytest.raises(UpstreamUnavailableError):
            get_paper_metadata("1706.03762")


class TestGetReferencesAndCitations:
    @responses.activate
    def test_references_not_indexed_returns_empty_list(self, ss_paper_url):
        responses.add(responses.GET, f"{ss_paper_url}/references", status=404, json={})
        from arxiv_mcp.semantic_scholar import get_references

        assert get_references("1706.03762") == []

    @responses.activate
    def test_references_upstream_down_raises(self, ss_paper_url):
        for _ in range(3):
            responses.add(responses.GET, f"{ss_paper_url}/references", status=503, body="down")
        from arxiv_mcp.semantic_scholar import get_references

        with pytest.raises(UpstreamUnavailableError):
            get_references("1706.03762")

    @responses.activate
    def test_citations_success(self, ss_paper_url):
        responses.add(
            responses.GET,
            f"{ss_paper_url}/citations",
            json={
                "data": [
                    {
                        "citingPaper": {
                            "title": "Follow-up Paper",
                            "authors": [{"name": "B. Someone"}],
                            "year": 2020,
                            "citationCount": 50,
                            "influentialCitationCount": 5,
                            "externalIds": {"ArXiv": "2001.00001"},
                        }
                    }
                ]
            },
            status=200,
        )
        from arxiv_mcp.semantic_scholar import get_citations

        results = get_citations("1706.03762")
        assert len(results) == 1
        assert results[0]["title"] == "Follow-up Paper"
        assert results[0]["arxiv_id"] == "2001.00001"


class TestSearchSemanticScholar:
    @responses.activate
    def test_search_success(self):
        from arxiv_mcp.semantic_scholar import SS_BASE, search_semantic_scholar

        responses.add(
            responses.GET,
            f"{SS_BASE}/paper/search",
            json={
                "data": [
                    {
                        "paperId": "xyz",
                        "title": "Some Paper",
                        "authors": [{"name": "C. Author"}],
                        "year": 2022,
                        "citationCount": 10,
                        "influentialCitationCount": 1,
                        "externalIds": {},
                    }
                ]
            },
            status=200,
        )
        results = search_semantic_scholar("some query")
        assert len(results) == 1
        assert results[0]["title"] == "Some Paper"
        assert results[0]["arxiv_id"] is None
