"""Tests for arxiv_mcp.server tool functions (direct-call style).

These call the underlying tool functions directly (not through the MCP
protocol) to unit-test business logic in isolation — `ctx` defaults to
`None` for exactly this purpose. Protocol-level concerns (schemas,
descriptions, annotations, resources, prompts) are covered separately in
test_protocol_surface.py via a real FastMCP Client, which is the only way
several of the bugs this project fixed were ever actually visible.
"""

from __future__ import annotations

from unittest.mock import patch

from arxiv_mcp.models import Paper


def _sample_paper(arxiv_id="1706.03762", title="Attention Is All You Need") -> Paper:
    return Paper(
        arxiv_id=arxiv_id,
        title=title,
        authors=["A. Vaswani"],
        abstract="We propose the Transformer.",
        published="2017-06-12T17:57:34Z",
        updated="2023-08-02T00:00:00Z",
        primary_category="cs.CL",
        categories=["cs.CL", "cs.LG"],
        pdf_url=f"https://arxiv.org/pdf/{arxiv_id}",
        abstract_url=f"https://arxiv.org/abs/{arxiv_id}",
    )


class TestGetPaperPdfUrl:
    def test_returns_expected_urls(self):
        from arxiv_mcp.server import get_paper_pdf_url

        result = get_paper_pdf_url("1706.03762v5")
        assert result["arxiv_id"] == "1706.03762"
        assert result["pdf_url"] == "https://arxiv.org/pdf/1706.03762"
        assert result["abstract_url"] == "https://arxiv.org/abs/1706.03762"
        assert result["html_url"] == "https://ar5iv.org/abs/1706.03762"
        assert "latex_source_url" in result

    def test_empty_id_returns_clean_error_not_crash(self):
        """The exact input that used to raise a raw IndexError (#2)."""
        from arxiv_mcp.server import get_paper_pdf_url

        result = get_paper_pdf_url("")
        assert "error" in result
        assert "IndexError" not in result["error"]


class TestSearchPapersEnvelope:
    def test_invalid_sort_by_returns_error_dict(self):
        """search_papers now returns a Dict envelope, not a List (#14) — this
        used to be `result[0]["error"]` when the return type was a list."""
        from arxiv_mcp.server import search_papers

        result = search_papers("test", sort_by="magic")
        assert isinstance(result, dict)
        assert "error" in result

    def test_invalid_sort_order_returns_error_dict(self):
        from arxiv_mcp.server import search_papers

        result = search_papers("test", sort_order="sideways")
        assert isinstance(result, dict)
        assert "error" in result

    @patch("arxiv_mcp.server.search_arxiv")
    def test_success_envelope_shape(self, mock_search):
        mock_search.return_value = [_sample_paper()]
        from arxiv_mcp.server import search_papers

        result = search_papers("transformer")
        assert result["query"] == "transformer"
        assert result["total_returned"] == 1
        assert isinstance(result["papers"], list)
        assert result["papers"][0]["title"] == "Attention Is All You Need"

    @patch("arxiv_mcp.server.search_arxiv")
    def test_empty_results_envelope_has_message(self, mock_search):
        mock_search.return_value = []
        from arxiv_mcp.server import search_papers

        result = search_papers("zzznomatch")
        assert result["papers"] == []
        assert "message" in result


class TestBatchGetPapersValidation:
    def test_empty_list(self):
        from arxiv_mcp.server import batch_get_papers

        result = batch_get_papers([])
        assert "error" in result

    def test_too_many_ids(self):
        from arxiv_mcp.server import batch_get_papers

        ids = [f"2301.{i:05d}" for i in range(21)]
        result = batch_get_papers(ids)
        assert "error" in result

    @patch("arxiv_mcp.server.fetch_papers_by_ids")
    def test_reports_not_found_ids_distinctly(self, mock_fetch):
        mock_fetch.return_value = [_sample_paper("1706.03762")]
        from arxiv_mcp.server import batch_get_papers

        result = batch_get_papers(["1706.03762", "9999.99999"])
        assert result["found"] == 1
        assert "9999.99999" in result["not_found"]


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

    def test_invalid_category_returns_clean_error(self):
        from arxiv_mcp.server import get_recent_papers

        result = get_recent_papers("???")
        assert "error" in result


class TestSearchAbstractIsWiredUp:
    """search_abstract existed as working logic in arxiv.py but was never
    exposed as a tool (#21) — it must now be reachable from server.py."""

    @patch("arxiv_mcp.server._search_by_abstract")
    def test_search_abstract_tool_exists_and_works(self, mock_search):
        mock_search.return_value = [_sample_paper()]
        from arxiv_mcp.server import search_abstract

        result = search_abstract("diffusion models")
        assert result["total_returned"] == 1
        mock_search.assert_called_once()


class TestCentralizedErrorHandling:
    @patch("arxiv_mcp.server.search_arxiv")
    def test_unexpected_exception_becomes_generic_safe_message(self, mock_search):
        """An unexpected bug (not one of our purpose-raised exceptions) must
        not leak raw Python exception text to the caller (#15)."""
        mock_search.side_effect = RuntimeError("some obscure internal detail")
        from arxiv_mcp.server import search_papers

        result = search_papers("test")
        assert "error" in result
        assert "obscure internal detail" not in result["error"]

    @patch("arxiv_mcp.server.fetch_paper_by_id")
    def test_not_found_paper_returns_clean_message(self, mock_fetch):
        mock_fetch.return_value = None
        from arxiv_mcp.server import get_paper_details

        result = get_paper_details("2301.00001")
        assert "error" in result
        assert "not found" in result["error"].lower()

    @patch("arxiv_mcp.server._ss_metadata")
    @patch("arxiv_mcp.server.fetch_paper_by_id")
    def test_semantic_scholar_outage_does_not_fail_whole_tool(self, mock_fetch, mock_ss):
        """Semantic Scholar enrichment is explicitly best-effort — an outage
        there must not take down the whole get_paper_details call, since the
        base ArXiv metadata is still perfectly valid on its own."""
        from arxiv_mcp.errors import UpstreamUnavailableError

        mock_fetch.return_value = _sample_paper()
        mock_ss.side_effect = UpstreamUnavailableError("Semantic Scholar is down")
        from arxiv_mcp.server import get_paper_details

        result = get_paper_details("1706.03762")
        assert "error" not in result
        assert result["title"] == "Attention Is All You Need"
        assert "unavailable" in result["semantic_scholar_enrichment"]
