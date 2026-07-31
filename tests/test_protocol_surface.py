"""
Protocol-level tests, exercised through a real in-memory FastMCP `Client`
rather than by calling Python functions directly.

This is the layer several of this project's original bugs (#1, #2) were
only actually visible at — calling `search_papers(...)` directly in Python
never surfaces a broken JSON schema or a dropped parameter description,
because Python doesn't care that a dict key has trailing whitespace. The
MCP client-facing schema is a distinct contract from the Python function
signature, and needs its own tests.
"""

from __future__ import annotations

import pytest


@pytest.fixture
async def client():
    from fastmcp import Client

    from arxiv_mcp.server import mcp

    async with Client(mcp) as c:
        yield c


class TestToolSchemas:
    """Regression guard for the docstring-parsing bug (#1): every tool must
    have a real description, and every parameter in its schema must have a
    real, non-padded description."""

    async def test_expected_tool_count(self, client):
        tools = await client.list_tools()
        names = {t.name for t in tools}
        expected = {
            "search_papers",
            "get_paper_details",
            "get_paper_pdf_url",
            "get_recent_papers",
            "get_related_papers",
            "get_paper_citations",
            "get_author_papers",
            "search_by_category",
            "search_title",
            "search_abstract",  # #21 — must be reachable as a tool
            "batch_get_papers",
            "search_semantic_scholar",
        }
        assert expected <= names

    async def test_every_tool_has_a_real_description(self, client):
        tools = await client.list_tools()
        for t in tools:
            assert t.description and len(t.description.strip()) >= 20, (
                f"{t.name} has a missing or suspiciously short description: {t.description!r}"
            )

    async def test_every_parameter_has_a_description_and_clean_name(self, client):
        tools = await client.list_tools()
        for t in tools:
            props = t.inputSchema.get("properties", {})
            for pname, pschema in props.items():
                assert pname == pname.strip(), f"{t.name}.{pname!r} has padding in its name"
                desc = pschema.get("description")
                assert desc and desc.strip(), f"{t.name}.{pname} is missing a description"

    async def test_context_parameter_is_not_exposed_to_clients(self, client):
        """`ctx: Optional[Context]` must be auto-excluded from the public
        schema — it's framework-injected, not something a caller fills in."""
        tools = await client.list_tools()
        for t in tools:
            props = t.inputSchema.get("properties", {})
            assert "ctx" not in props, f"{t.name} leaked its ctx parameter into the public schema"

    async def test_every_tool_has_a_title(self, client):
        tools = await client.list_tools()
        for t in tools:
            assert t.title, f"{t.name} is missing a title (#8/#13C)"

    async def test_every_tool_has_readonly_annotations(self, client):
        """All 12 tools are read-only, side-effect-free lookups — their
        annotations should say so (#8)."""
        tools = await client.list_tools()
        for t in tools:
            assert t.annotations is not None, f"{t.name} is missing annotations"
            assert t.annotations.readOnlyHint is True, f"{t.name} should be readOnlyHint=True"
            assert t.annotations.destructiveHint is False, (
                f"{t.name} should be destructiveHint=False"
            )


class TestResources:
    async def test_reference_resources_are_registered(self, client):
        resources = await client.list_resources()
        uris = {str(r.uri) for r in resources}
        assert "arxiv://reference/query-syntax" in uris
        assert "arxiv://reference/categories" in uris

    async def test_query_syntax_resource_has_content(self, client):
        result = await client.read_resource("arxiv://reference/query-syntax")
        assert result
        text = result[0].text
        assert "ti:" in text and "AND" in text


class TestPrompts:
    async def test_expected_prompts_registered(self, client):
        prompts = await client.list_prompts()
        names = {p.name for p in prompts}
        assert {"literature_review", "explain_paper", "find_related_work"} <= names

    async def test_explain_paper_prompt_renders(self, client):
        result = await client.get_prompt("explain_paper", {"arxiv_id": "1706.03762"})
        assert result.messages
        assert "1706.03762" in result.messages[0].content.text


class TestToolCallErrorHandling:
    """Full round-trip through the protocol layer, confirming malformed
    input produces a clean error response rather than a protocol-level
    crash (#2, #15)."""

    async def test_empty_arxiv_id_via_protocol(self, client):
        result = await client.call_tool("get_paper_details", {"arxiv_id": ""})
        assert "error" in result.data

    async def test_malformed_category_via_protocol(self, client):
        result = await client.call_tool("get_recent_papers", {"category": "not a category!!"})
        assert "error" in result.data
