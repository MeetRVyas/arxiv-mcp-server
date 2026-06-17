"""
Unit tests for ArXiv MCP Server.

Run with:  pytest tests/ -v
"""

import pytest
from unittest.mock import MagicMock, patch

# ─── Fixtures ─────────────────────────────────────────────────────────────────

SAMPLE_ATOM_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:arxiv="http://arxiv.org/schemas/atom">

  <entry>
    <id>http://arxiv.org/abs/1706.03762v5</id>
    <title>Attention Is All You Need</title>
    <author><name>Ashish Vaswani</name></author>
    <author><name>Noam Shazeer</name></author>
    <summary>
      The dominant sequence transduction models are based on complex recurrent
      or convolutional neural networks. We propose a new simple network
      architecture, the Transformer.
    </summary>
    <published>2017-06-12T17:57:34Z</published>
    <updated>2023-08-02T00:00:00Z</updated>
    <arxiv:primary_category term="cs.CL" scheme="http://arxiv.org/schemas/atom"/>
    <category term="cs.CL" scheme="http://arxiv.org/schemas/atom"/>
    <category term="cs.LG" scheme="http://arxiv.org/schemas/atom"/>
    <link rel="alternate" type="text/html" href="https://arxiv.org/abs/1706.03762"/>
    <link title="pdf" type="application/pdf" href="https://arxiv.org/pdf/1706.03762"/>
    <arxiv:doi>10.48550/arXiv.1706.03762</arxiv:doi>
    <arxiv:comment>15 pages, 5 figures. NIPS 2017.</arxiv:comment>
  </entry>

</feed>"""

EMPTY_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:arxiv="http://arxiv.org/schemas/atom">
</feed>"""


# ─── arxiv_client tests ───────────────────────────────────────────────────────

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
    def test_parses_paper_correctly(self):
        from arxiv_mcp.arxiv import _parse_feed
        papers = _parse_feed(SAMPLE_ATOM_FEED)

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

    def test_empty_feed_returns_empty_list(self):
        from arxiv_mcp.arxiv import _parse_feed
        assert _parse_feed(EMPTY_FEED) == []

    def test_pdf_fallback_url(self):
        """When no PDF link is in the feed, fallback URL is constructed."""
        feed_no_pdf = SAMPLE_ATOM_FEED.replace(
            '<link title="pdf" type="application/pdf" href="https://arxiv.org/pdf/1706.03762"/>',
            "",
        )
        from arxiv_mcp.arxiv import _parse_feed
        papers = _parse_feed(feed_no_pdf)
        assert papers[0].pdf_url == "https://arxiv.org/pdf/1706.03762"

    def test_to_dict_serialisable(self):
        """Paper.to_dict() must be JSON-serialisable (no custom objects)."""
        import json
        from arxiv_mcp.arxiv import _parse_feed
        papers = _parse_feed(SAMPLE_ATOM_FEED)
        json.dumps(papers[0].to_dict())    # must not raise


class TestSearchArxiv:
    @patch("arxiv_mcp.arxiv._rate_limited_get")
    def test_returns_papers(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.text = SAMPLE_ATOM_FEED
        mock_get.return_value = mock_resp

        from arxiv_mcp.arxiv import search_arxiv
        papers = search_arxiv("transformer", max_results=1)
        assert len(papers) == 1
        assert papers[0].title == "Attention Is All You Need"

    @patch("arxiv_mcp.arxiv._rate_limited_get")
    def test_empty_results(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.text = EMPTY_FEED
        mock_get.return_value = mock_resp

        from arxiv_mcp.arxiv import search_arxiv
        assert search_arxiv("zzznomatch") == []

    @patch("arxiv_mcp.arxiv._rate_limited_get")
    def test_max_results_capped(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.text = EMPTY_FEED
        mock_get.return_value = mock_resp

        from arxiv_mcp.arxiv import search_arxiv, MAX_RESULTS_CAP
        search_arxiv("test", max_results=999)
        call_params = mock_get.call_args[0][1]
        assert call_params["max_results"] <= MAX_RESULTS_CAP


# ─── server tool tests ────────────────────────────────────────────────────────

class TestGetPaperPdfUrl:
    def test_returns_expected_urls(self):
        from arxiv_mcp.server import get_paper_pdf_url
        result = get_paper_pdf_url("1706.03762v5")
        assert result["arxiv_id"]     == "1706.03762"
        assert result["pdf_url"]      == "https://arxiv.org/pdf/1706.03762"
        assert result["abstract_url"] == "https://arxiv.org/abs/1706.03762"
        assert result["html_url"]     == "https://ar5iv.org/abs/1706.03762"
        assert "latex_source_url" in result


class TestSearchPapersValidation:
    def test_invalid_sort_by(self):
        from arxiv_mcp.server import search_papers
        result = search_papers("test", sort_by="magic")
        assert "error" in result[0]

    def test_invalid_sort_order(self):
        from arxiv_mcp.server import search_papers
        result = search_papers("test", sort_order="sideways")
        assert "error" in result[0]


class TestBatchGetPapersValidation:
    def test_empty_list(self):
        from arxiv_mcp.server import batch_get_papers
        result = batch_get_papers([])
        assert "error" in result

    def test_too_many_ids(self):
        from arxiv_mcp.server import batch_get_papers
        ids = [f"000{i}.00001" for i in range(21)]
        result = batch_get_papers(ids)
        assert "error" in result


class TestGetRecentPapersClamping:
    @patch("arxiv_mcp.server._recent_papers", return_value=[])
    def test_days_back_clamped(self, mock_fn):
        from arxiv_mcp.server import get_recent_papers
        get_recent_papers("cs.LG", days_back=999)
        _, kwargs = mock_fn.call_args
        assert kwargs["days_back"] <= 30

    @patch("arxiv_mcp.server._recent_papers", return_value=[])
    def test_max_results_clamped(self, mock_fn):
        from arxiv_mcp.server import get_recent_papers
        get_recent_papers("cs.LG", max_results=999)
        _, kwargs = mock_fn.call_args
        assert kwargs["max_results"] <= 50
