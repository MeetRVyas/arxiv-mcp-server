"""
ArXiv MCP Server
================
A production-grade MCP server exposing ArXiv and Semantic Scholar data to LLM agents.

Tools
-----
  search_papers          — keyword / field search across all of ArXiv
  get_paper_details      — full metadata for a specific paper (enriched with SS data)
  get_paper_pdf_url      — direct PDF + HTML links ready for RAG ingestion
  get_recent_papers      — "what landed in cs.LG this week?"
  get_related_papers     — reference list of a paper (Semantic Scholar)
  get_paper_citations    — papers that cite a given paper (forward citations)
  get_author_papers      — all ArXiv papers by a researcher
  search_by_category     — keyword search scoped to one ArXiv category
  search_title           — search specifically in paper titles
  batch_get_papers       — fetch up to 20 papers in a single round-trip
  search_semantic_scholar— broader search including non-ArXiv papers + citation counts
"""

import logging
import sys
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP

from arxiv_mcp.arxiv import (
    fetch_paper_by_id,
    fetch_papers_by_ids,
    get_author_papers      as _author_papers,
    get_recent_papers      as _recent_papers,
    search_arxiv,
    search_by_category     as _search_by_cat,
    search_by_title        as _search_by_title,
    _strip_version,
)
from arxiv_mcp.semantic_scholar import (
    get_citations          as _citations,
    get_paper_metadata     as _ss_metadata,
    get_references         as _references,
    search_semantic_scholar as _ss_search,
)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

# MCP App
mcp = FastMCP(
    name="ArXiv MCP Server",
    instructions="""
You have access to ArXiv and Semantic Scholar through these tools.

Guidance:
- Use `search_papers` for broad keyword queries first; narrow with `search_by_category` when the domain is clear.
- Prefer `get_paper_details` after a search to fetch full abstracts and citation counts.
- Use `get_paper_pdf_url` to get a PDF link for RAG / document ingestion pipelines.
- Use `get_recent_papers` when the user wants to know what is new in a field.
- Use `get_related_papers` + `get_paper_citations` together to explore a citation graph.
- `search_semantic_scholar` is broader — it includes conference/journal papers not on ArXiv.
- Always present: arxiv_id, title, authors, abstract, pdf_url in your summaries.
- ArXiv category codes: cs.LG, cs.AI, cs.CL, cs.CV, cs.RO, stat.ML, eess.IV, math.OC, q-bio.NC
    """,
)


# Input validation helpers
_VALID_SORT_BY    = {"relevance", "submittedDate", "lastUpdatedDate"}
_VALID_SORT_ORDER = {"ascending", "descending"}


def _clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(value, hi))


def _validate_sort(sort_by: str, sort_order: str) -> Optional[Dict[str, str]]:
    if sort_by not in _VALID_SORT_BY:
        return {"error": f"sort_by must be one of {sorted(_VALID_SORT_BY)}, got '{sort_by}'."}
    if sort_order not in _VALID_SORT_ORDER:
        return {"error": f"sort_order must be 'ascending' or 'descending', got '{sort_order}'."}
    return None


# Tool: search_papers
@mcp.tool()
def search_papers(
    query: str,
    max_results: int = 10,
    sort_by: str = "relevance",
    sort_order: str = "descending",
) -> List[Dict[str, Any]]:
    """
    Search all of ArXiv for papers matching a keyword query.

    Supports ArXiv field prefixes in the query:
      ti:attention        — search in titles
      au:"Vaswani"        — search by author name
      abs:diffusion       — search in abstracts
      cat:cs.LG           — restrict to a category
      all:transformer     — all fields (default)
    Combine with AND, OR, ANDNOT (uppercase required).
    Example: 'ti:BERT AND au:Devlin'

    Args:
        query      : Keyword query string (required)
        max_results: How many papers to return, 1–50 (default 10)
        sort_by    : 'relevance' | 'submittedDate' | 'lastUpdatedDate'
        sort_order : 'descending' (default) | 'ascending'

    Returns:
        List of paper objects — id, title, authors, abstract, categories, URLs.
    """
    err = _validate_sort(sort_by, sort_order)
    if err:
        return [err]

    max_results = _clamp(max_results, 1, 50)
    logger.info(f"search_papers query={query!r} max={max_results} sort={sort_by}/{sort_order}")

    papers = search_arxiv(query, max_results=max_results, sort_by=sort_by, sort_order=sort_order)
    if not papers:
        return [{"message": "No papers found. Try broader or different keywords."}]
    return [p.to_dict() for p in papers]


# Tool: get_paper_details
@mcp.tool()
def get_paper_details(arxiv_id: str) -> Dict[str, Any]:
    """
    Retrieve full metadata for a specific ArXiv paper, enriched with
    citation counts and fields-of-study from Semantic Scholar.

    Args:
        arxiv_id: ArXiv paper ID — e.g. '1706.03762', '2301.00001', 'cs/0001001'.
                  Version suffixes ('v2', 'v3') are accepted and stripped.

    Returns:
        Full paper record including title, authors, abstract, categories, DOI,
        journal reference, citation_count, influential_citation_count, fields_of_study.
    """
    logger.info(f"get_paper_details id={arxiv_id!r}")
    paper = fetch_paper_by_id(arxiv_id)

    if not paper:
        return {"error": f"Paper '{arxiv_id}' not found. Check the ID is correct."}

    result = paper.to_dict()
    result["html_url"] = paper.html_url     # ar5iv HTML rendering

    # Enrich with Semantic Scholar metadata (best-effort)
    ss = _ss_metadata(paper.arxiv_id)
    if ss:
        result["citation_count"]             = ss.get("citation_count")
        result["influential_citation_count"] = ss.get("influential_citation_count")
        result["fields_of_study"]            = ss.get("fields_of_study", [])
        result["venue"]                      = ss.get("venue")
        result["semantic_scholar_id"]        = ss.get("semantic_scholar_id")

    return result


# Tool: get_paper_pdf_url
@mcp.tool()
def get_paper_pdf_url(arxiv_id: str) -> Dict[str, str]:
    """
    Return the direct PDF download URL and related links for an ArXiv paper.
    Ideal for feeding into a RAG / document ingestion pipeline.

    Args:
        arxiv_id: ArXiv paper ID (e.g. '1706.03762')

    Returns:
        Dict with pdf_url (direct download), abstract_url, html_url (ar5iv),
        and a latex_source_url for the raw LaTeX source tarball.
    """
    clean_id = _strip_version(arxiv_id.strip())
    return {
        "arxiv_id":         clean_id,
        "pdf_url":          f"https://arxiv.org/pdf/{clean_id}",
        "abstract_url":     f"https://arxiv.org/abs/{clean_id}",
        "html_url":         f"https://ar5iv.org/abs/{clean_id}",
        "latex_source_url": f"https://arxiv.org/src/{clean_id}",
        "note": (
            "pdf_url is the direct download link suitable for RAG ingestion. "
            "html_url provides a rendered HTML version (better for text extraction). "
            "latex_source_url gives the raw LaTeX source tarball."
        ),
    }


# Tool: get_recent_papers
@mcp.tool()
def get_recent_papers(
    category: str,
    days_back: int = 7,
    max_results: int = 20,
) -> List[Dict[str, Any]]:
    """
    Fetch papers recently submitted to a specific ArXiv category.
    Great for a daily/weekly research digest.

    Common category codes:
      cs.LG  — Machine Learning          cs.AI  — Artificial Intelligence
      cs.CL  — Computation & Language    cs.CV  — Computer Vision
      cs.RO  — Robotics                  cs.CR  — Cryptography & Security
      stat.ML — Statistical ML           eess.IV — Image & Video Processing
      math.OC — Optimization & Control   q-bio.NC — Neurons & Cognition
      physics.data-an — Data Analysis in Physics

    Args:
        category  : ArXiv category code (e.g. 'cs.LG')
        days_back : Look back this many days, 1–30 (default 7)
        max_results: Number of papers to return, 1–50 (default 20)

    Returns:
        List of papers sorted by submission date, newest first.
    """
    days_back   = _clamp(days_back, 1, 30)
    max_results = _clamp(max_results, 1, 50)

    logger.info(f"get_recent_papers cat={category!r} days={days_back} max={max_results}")
    papers = _recent_papers(category, days_back=days_back, max_results=max_results)

    if not papers:
        return [{
            "message": (
                f"No recent papers found in '{category}'. "
                "Verify the category code or try a larger days_back window."
            )
        }]
    return [p.to_dict() for p in papers]


# Tool: get_related_papers
@mcp.tool()
def get_related_papers(
    arxiv_id: str,
    max_results: int = 10,
) -> Dict[str, Any]:
    """
    Get papers referenced by the given paper (its bibliography / related work).
    Uses Semantic Scholar's citation graph. Excellent for tracing intellectual lineage.

    Args:
        arxiv_id   : ArXiv paper ID (e.g. '1706.03762')
        max_results: Number of references to return, 1–30 (default 10)

    Returns:
        Dict with 'arxiv_id', 'total_returned', and a 'related_papers' list.
        Each entry includes title, authors, year, arxiv_id (if available), and citation_count.
    """
    max_results = _clamp(max_results, 1, 30)
    logger.info(f"get_related_papers id={arxiv_id!r} max={max_results}")

    refs = _references(arxiv_id, max_results=max_results)
    if not refs:
        return {
            "arxiv_id": arxiv_id,
            "message": (
                "No references found. The paper may not yet be indexed in Semantic Scholar "
                "(papers typically appear within a few days of ArXiv submission)."
            ),
            "related_papers": [],
        }

    return {
        "arxiv_id":       arxiv_id,
        "total_returned": len(refs),
        "related_papers": refs,
    }


# Tool: get_paper_citations
@mcp.tool()
def get_paper_citations(
    arxiv_id: str,
    max_results: int = 20,
) -> Dict[str, Any]:
    """
    Get papers that cite the given paper (forward / incoming citations).
    Use this to find follow-up work, extensions, or applications of a paper.

    Args:
        arxiv_id   : ArXiv paper ID
        max_results: Number of citing papers to return, 1–50 (default 20)

    Returns:
        Dict with 'arxiv_id', 'citations_returned', and 'citing_papers' list.
    """
    max_results = _clamp(max_results, 1, 50)
    logger.info(f"get_paper_citations id={arxiv_id!r} max={max_results}")

    citations = _citations(arxiv_id, max_results=max_results)
    if not citations:
        return {
            "arxiv_id": arxiv_id,
            "message": (
                "No citations found. The paper may be too recent, have few citations, "
                "or not yet indexed in Semantic Scholar."
            ),
            "citing_papers": [],
        }

    return {
        "arxiv_id":           arxiv_id,
        "citations_returned": len(citations),
        "citing_papers":      citations,
    }


# Tool: get_author_papers
@mcp.tool()
def get_author_papers(
    author_name: str,
    max_results: int = 15,
    sort_by: str = "submittedDate",
) -> Dict[str, Any]:
    """
    Get ArXiv papers by a specific author, sorted by date or relevance.
    Supports partial name matching (last name only works well).

    Args:
        author_name: Full or partial name (e.g. 'Yann LeCun', 'Hinton', 'Bengio')
        max_results: Papers to return, 1–50 (default 15)
        sort_by    : 'submittedDate' (default) | 'relevance' | 'lastUpdatedDate'

    Returns:
        Dict with 'author', 'papers_found', and 'papers' list.
    """
    if sort_by not in _VALID_SORT_BY:
        sort_by = "submittedDate"
    max_results = _clamp(max_results, 1, 50)

    logger.info(f"get_author_papers author={author_name!r} max={max_results}")
    papers = _author_papers(author_name, max_results=max_results, sort_by=sort_by)

    if not papers:
        return {
            "author":  author_name,
            "message": "No papers found. Try a partial name (e.g. just the last name) or check spelling.",
            "papers":  [],
        }

    return {
        "author":       author_name,
        "papers_found": len(papers),
        "papers":       [p.to_dict() for p in papers],
    }


# Tool: search_by_category
@mcp.tool()
def search_by_category(
    category: str,
    query: str,
    max_results: int = 10,
    sort_by: str = "relevance",
) -> List[Dict[str, Any]]:
    """
    Search for papers within a specific ArXiv category.
    More precise than a general search when you already know the domain.

    Args:
        category  : ArXiv category code (e.g. 'cs.LG', 'stat.ML', 'cs.CV')
        query     : Keywords or ArXiv field prefixes (ti:, au:, abs:)
        max_results: Results to return, 1–50 (default 10)
        sort_by   : 'relevance' | 'submittedDate' | 'lastUpdatedDate'

    Returns:
        List of papers in the specified category matching the query.
    """
    err = _validate_sort(sort_by, "descending")
    if err:
        return [err]
    max_results = _clamp(max_results, 1, 50)

    logger.info(f"search_by_category cat={category!r} query={query!r}")
    papers = _search_by_cat(category, query, max_results=max_results, sort_by=sort_by)

    if not papers:
        return [{"message": f"No results in '{category}' for '{query}'. Try broader terms."}]
    return [p.to_dict() for p in papers]


# Tool: search_title
@mcp.tool()
def search_title(
    title_query: str,
    max_results: int = 10,
) -> List[Dict[str, Any]]:
    """
    Search specifically in ArXiv paper titles (more precise than full-text search).
    Useful when you know part of a paper's title.

    Args:
        title_query: Title keywords (e.g. 'attention is all you need')
        max_results: Results to return, 1–30 (default 10)

    Returns:
        List of papers whose titles match the query.
    """
    max_results = _clamp(max_results, 1, 30)
    logger.info(f"search_title query={title_query!r}")

    papers = _search_by_title(title_query, max_results=max_results)
    if not papers:
        return [{"message": f"No papers with title matching '{title_query}'."}]
    return [p.to_dict() for p in papers]


# Tool: batch_get_papers
@mcp.tool()
def batch_get_papers(arxiv_ids: List[str]) -> Dict[str, Any]:
    """
    Fetch metadata for multiple ArXiv papers in a single API round-trip.
    Efficient when you have a list of IDs from another tool's output.

    Args:
        arxiv_ids: List of ArXiv IDs, maximum 20.
                   E.g. ['1706.03762', '1810.04805', '2005.14165']

    Returns:
        Dict with 'found' count, 'papers' list, and 'not_found' IDs.
    """
    if not arxiv_ids:
        return {"error": "Provide at least one arxiv_id."}
    if len(arxiv_ids) > 20:
        return {"error": "Maximum 20 IDs per batch request. Split into multiple calls."}

    logger.info(f"batch_get_papers count={len(arxiv_ids)}")
    papers = fetch_papers_by_ids(arxiv_ids)

    found_ids    = {p.arxiv_id for p in papers}
    requested_ids = {_strip_version(aid.strip()) for aid in arxiv_ids}
    not_found    = sorted(requested_ids - found_ids)

    return {
        "requested": len(arxiv_ids),
        "found":     len(papers),
        "not_found": not_found,
        "papers":    [p.to_dict() for p in papers],
    }


# Tool: search_semantic_scholar
@mcp.tool()
def search_semantic_scholar(
    query: str,
    max_results: int = 10,
    fields_of_study: Optional[List[str]] = None,
    year_range: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Search Semantic Scholar — broader than ArXiv (includes journals, conference papers,
    and non-preprint work). Returns citation counts and influence metrics.

    Args:
        query          : Keyword query
        max_results    : Results to return, 1–50 (default 10)
        fields_of_study: Optional filter list, e.g. ['Computer Science', 'Mathematics']
                         Valid values: Computer Science, Physics, Mathematics, Medicine,
                         Biology, Chemistry, Economics, Engineering, etc.
        year_range     : Optional year filter, e.g. '2020-2024', '2023-', '-2020'

    Returns:
        List of papers with title, authors, year, citation_count,
        influential_citation_count, venue, fields_of_study, abstract_url.
    """
    max_results = _clamp(max_results, 1, 50)
    logger.info(f"search_semantic_scholar query={query!r} max={max_results}")

    results = _ss_search(
        query,
        max_results=max_results,
        fields_of_study=fields_of_study,
        year_range=year_range,
    )
    if not results:
        return [{"message": "No results from Semantic Scholar for this query."}]
    return results


# Entry point
def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="ArXiv MCP Server")
    parser.add_argument(
        "--transport",
        default="streamable-http",
        choices=["stdio", "sse", "streamable-http"],
        help="MCP transport protocol (default: streamable-http)",
    )
    parser.add_argument("--host",      default="0.0.0.0",   help="Bind host")
    parser.add_argument("--port",      type=int, default=8000, help="Bind port")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    args = parser.parse_args()

    logging.getLogger().setLevel(getattr(logging, args.log_level))
    logger.info(
        f"ArXiv MCP Server starting — transport={args.transport} "
        f"host={args.host} port={args.port}"
    )
    mcp.run(transport=args.transport, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
