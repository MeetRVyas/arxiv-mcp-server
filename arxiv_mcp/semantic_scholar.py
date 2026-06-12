"""
Semantic Scholar API client.

Uses the public Graph API (https://api.semanticscholar.org/graph/v1).
No API key required, but an optional key raises rate limits significantly.
Set the SEMANTIC_SCHOLAR_API_KEY env var to use one.

Free-tier limits  : ~1 req/s   (~100 req/5 min)
With API key      : ~10 req/s  (apply at https://www.semanticscholar.org/product/api)
"""

import logging
import os
import time
from typing import Any, Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from arxiv_mcp.models import CitationPaper

logger = logging.getLogger(__name__)

# Constants
SS_BASE = "https://api.semanticscholar.org/graph/v1"

# Fields to request for full paper metadata
_PAPER_FIELDS = (
    "paperId,title,authors,year,abstract,"
    "citationCount,influentialCitationCount,"
    "externalIds,venue,fieldsOfStudy,publicationDate"
)

# Lighter field set for citation / reference lists
_REF_FIELDS = (
    "title,authors,year,"
    "externalIds,citationCount,influentialCitationCount,venue"
)

if os.getenv("SEMANTIC_SCHOLAR_API_KEY", "").strip() :
    _RATE_LIMIT_DELAY = 0.1 # seconds;
else :
    _RATE_LIMIT_DELAY = 1.1 # seconds; conservative for no-key usage
_last_request_time: float = 0.0


# HTTP Session
def _build_ss_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=4,
        backoff_factor=2.0,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers.update({"User-Agent": "ArXivMCPServer/1.0"})

    api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "").strip()
    if api_key:
        session.headers.update({"x-api-key": api_key})
        logger.info("Semantic Scholar: using API key (elevated rate limits)")
    else:
        logger.info("Semantic Scholar: no API key — rate-limited to ~1 req/s")

    return session


_ss_session = _build_ss_session()


def _get(url: str, params: Optional[Dict] = None, timeout: int = 15) -> Optional[Dict[str, Any]]:
    """Rate-limited GET that returns parsed JSON or None on failure."""
    global _last_request_time
    elapsed = time.monotonic() - _last_request_time
    if elapsed < _RATE_LIMIT_DELAY:
        time.sleep(_RATE_LIMIT_DELAY - elapsed)

    try:
        logger.debug(f"SS GET {url}  params={params}")
        resp = _ss_session.get(url, params=params or {}, timeout=timeout)
        _last_request_time = time.monotonic()

        if resp.status_code == 404:
            logger.info(f"Semantic Scholar 404: {url}")
            return None
        if resp.status_code == 429:
            # Back off and retry once manually (adapter already retries, but be explicit)
            logger.warning("Semantic Scholar rate-limited (429). Waiting 10 s …")
            time.sleep(10)
            resp = _ss_session.get(url, params=params or {}, timeout=timeout)
            _last_request_time = time.monotonic()

        resp.raise_for_status()
        return resp.json()

    except requests.RequestException as exc:
        logger.error(f"Semantic Scholar request failed: {exc}")
        return None


# Helpers
def _ss_paper_id(arxiv_id: str) -> str:
    """Semantic Scholar accepts 'arXiv:2301.00001' as a paper identifier."""
    return f"arXiv:{arxiv_id.strip()}"


def _citation_paper_from_raw(raw: Dict[str, Any]) -> CitationPaper:
    ext = raw.get("externalIds") or {}
    arxiv_id = ext.get("ArXiv")
    return CitationPaper(
        arxiv_id=arxiv_id,
        semantic_scholar_id=raw.get("paperId"),
        title=raw.get("title") or "",
        authors=[a.get("name", "") for a in (raw.get("authors") or [])],
        year=raw.get("year"),
        citation_count=raw.get("citationCount") or 0,
        influential_citation_count=raw.get("influentialCitationCount") or 0,
        abstract_url=f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else None,
        pdf_url=f"https://arxiv.org/pdf/{arxiv_id}" if arxiv_id else None,
        venue=raw.get("venue"),
    )


# Public API
def get_paper_metadata(arxiv_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch enriched metadata from Semantic Scholar for a given ArXiv paper.
    Returns citation count, influential citations, venue, fields of study, etc.
    """
    data = _get(
        f"{SS_BASE}/paper/{_ss_paper_id(arxiv_id)}",
        params={"fields": _PAPER_FIELDS},
    )
    if not data:
        return None

    ext = data.get("externalIds") or {}
    return {
        "semantic_scholar_id":        data.get("paperId"),
        "title":                      data.get("title", ""),
        "authors":                    [a.get("name", "") for a in (data.get("authors") or [])],
        "year":                       data.get("year"),
        "publication_date":           data.get("publicationDate"),
        "abstract":                   data.get("abstract", ""),
        "citation_count":             data.get("citationCount", 0),
        "influential_citation_count": data.get("influentialCitationCount", 0),
        "venue":                      data.get("venue"),
        "fields_of_study":            data.get("fieldsOfStudy") or [],
        "external_ids":               ext,
    }


def get_references(arxiv_id: str, max_results: int = 15) -> List[Dict[str, Any]]:
    """
    Papers referenced BY the given paper (outgoing citations / bibliography).
    These are typically the papers the authors built upon.
    """
    data = _get(
        f"{SS_BASE}/paper/{_ss_paper_id(arxiv_id)}/references",
        params={"fields": _REF_FIELDS, "limit": min(max_results, 500)},
    )
    if not data:
        return []

    results = []
    for item in (data.get("data") or [])[:max_results]:
        cited = item.get("citedPaper") or {}
        if cited:
            results.append(_citation_paper_from_raw(cited).to_dict())
    return results


def get_citations(arxiv_id: str, max_results: int = 20) -> List[Dict[str, Any]]:
    """
    Papers that CITE the given paper (incoming citations / forward citations).
    Useful for finding follow-up work.
    """
    data = _get(
        f"{SS_BASE}/paper/{_ss_paper_id(arxiv_id)}/citations",
        params={"fields": _REF_FIELDS, "limit": min(max_results, 500)},
    )
    if not data:
        return []

    results = []
    for item in (data.get("data") or [])[:max_results]:
        citing = item.get("citingPaper") or {}
        if citing:
            results.append(_citation_paper_from_raw(citing).to_dict())
    return results


def search_semantic_scholar(
    query: str,
    max_results: int = 10,
    fields_of_study: Optional[List[str]] = None,
    year_range: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Search Semantic Scholar directly (broader than ArXiv — includes non-ArXiv papers).

    Args:
        query         : keyword query
        max_results   : results to return
        fields_of_study: filter by field, e.g. ["Computer Science", "Mathematics"]
        year_range    : e.g. "2020-2024" or "2023-"
    """
    params: Dict[str, Any] = {
        "query": query,
        "limit": min(max_results, 100),
        "fields": _PAPER_FIELDS,
    }
    if fields_of_study:
        params["fieldsOfStudy"] = ",".join(fields_of_study)
    if year_range:
        params["year"] = year_range

    data = _get(f"{SS_BASE}/paper/search", params=params)
    if not data:
        return []

    results = []
    for paper in (data.get("data") or [])[:max_results]:
        ext = paper.get("externalIds") or {}
        arxiv_id = ext.get("ArXiv")
        results.append({
            "semantic_scholar_id":        paper.get("paperId"),
            "arxiv_id":                   arxiv_id,
            "title":                      paper.get("title", ""),
            "authors":                    [a.get("name", "") for a in (paper.get("authors") or [])],
            "year":                       paper.get("year"),
            "citation_count":             paper.get("citationCount", 0),
            "influential_citation_count": paper.get("influentialCitationCount", 0),
            "venue":                      paper.get("venue"),
            "fields_of_study":            paper.get("fieldsOfStudy") or [],
            "abstract_url":               f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else None,
            "pdf_url":                    f"https://arxiv.org/pdf/{arxiv_id}" if arxiv_id else None,
            "abstract":                   paper.get("abstract", ""),
        })
    return results