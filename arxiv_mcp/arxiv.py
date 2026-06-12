"""
ArXiv API client.

Wraps the ArXiv Atom/XML API (https://arxiv.org/help/api/user-manual).
No authentication required. Rate-limited to 1 req/3 s per ArXiv guidelines.
"""

import logging
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from typing import List, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from arxiv_mcp.models import Paper

logger = logging.getLogger(__name__)

# Constants
ARXIV_API_BASE = "http://export.arxiv.org/api/query"

# XML namespaces used in ArXiv Atom feed
ATOM_NS  = "http://www.w3.org/2005/Atom"
ARXIV_NS = "http://arxiv.org/schemas/atom"

# ArXiv recommends no more than 1 request every 3 seconds for automated access
_RATE_LIMIT_DELAY = 3.0
_last_request_time: float = 0.0

# Hard cap to stay well within ArXiv's acceptable-use policy
MAX_RESULTS_CAP = 100


# HTTP Session
def _build_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=4,
        backoff_factor=2.0,                        # 2 s, 4 s, 8 s, 16 s
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    # Polite User-Agent as requested by ArXiv ToS
    session.headers.update({
        "User-Agent": "ArXivMCPServer/1.0 (https://github.com/MeetRVyas/arxiv-mcp-server; research tool)"
    })
    return session


_session = _build_session()


def _rate_limited_get(url: str, params: dict, timeout: int = 30) -> requests.Response:
    """GET with rate limiting and raise_for_status."""
    global _last_request_time
    elapsed = time.monotonic() - _last_request_time
    if elapsed < _RATE_LIMIT_DELAY:
        sleep_for = _RATE_LIMIT_DELAY - elapsed
        logger.debug(f"Rate-limit sleep {sleep_for:.2f}s")
        time.sleep(sleep_for)

    logger.debug(f"GET {url}  params={params}")
    resp = _session.get(url, params=params, timeout=timeout)
    _last_request_time = time.monotonic()
    resp.raise_for_status()
    return resp


# XML Parsing Helpers
_NS = {"atom": ATOM_NS, "arxiv": ARXIV_NS}


def _text(el: ET.Element, tag: str) -> Optional[str]:
    """Return stripped text of a child element, or None."""
    child = el.find(tag, _NS)
    return child.text.strip() if child is not None and child.text else None


def _clean_whitespace(s: str) -> str:
    """Collapse newlines / form-feeds / multiple spaces into single spaces."""
    return " ".join(s.split())


def _extract_arxiv_id(entry_id_url: str) -> str:
    """
    ArXiv entry <id> looks like:
        http://arxiv.org/abs/2301.00001v2
    Strip the base URL and any version suffix.
    """
    raw = entry_id_url.split("/abs/")[-1]   # "2301.00001v2"
    return raw.rsplit("v", 1)[0] if raw[-1].isdigit() and "v" in raw else raw


def _parse_entry(entry: ET.Element) -> Paper:
    """Parse a single <entry> element into a Paper dataclass."""
    entry_id_url = _text(entry, "atom:id") or ""
    arxiv_id = _extract_arxiv_id(entry_id_url)

    title    = _clean_whitespace(_text(entry, "atom:title") or "")
    abstract = _clean_whitespace(_text(entry, "atom:summary") or "")

    authors = [
        name.text.strip()
        for author in entry.findall("atom:author", _NS)
        for name in author.findall("atom:name", _NS)
        if name.text
    ]

    published = _text(entry, "atom:published") or ""
    updated   = _text(entry, "atom:updated") or ""

    # Primary category
    prim_el = entry.find("arxiv:primary_category", _NS)
    primary_category = prim_el.get("term", "") if prim_el is not None else ""

    # All categories
    categories = [
        cat.get("term", "")
        for cat in entry.findall("atom:category", _NS)
        if cat.get("term")
    ]

    # Links — ArXiv provides two: rel="alternate" (abstract page) and title="pdf"
    pdf_url = abstract_url = ""
    for link in entry.findall("atom:link", _NS):
        href = link.get("href", "")
        if link.get("title") == "pdf":
            pdf_url = href
        elif link.get("rel") == "alternate":
            abstract_url = href

    # Reliable fallbacks
    if not pdf_url:
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"
    if not abstract_url:
        abstract_url = f"https://arxiv.org/abs/{arxiv_id}"

    return Paper(
        arxiv_id=arxiv_id,
        title=title,
        authors=authors,
        abstract=abstract,
        published=published,
        updated=updated,
        primary_category=primary_category,
        categories=categories,
        pdf_url=pdf_url,
        abstract_url=abstract_url,
        doi=_text(entry, "arxiv:doi"),
        journal_ref=_text(entry, "arxiv:journal_ref"),
        comment=_text(entry, "arxiv:comment"),
    )


def _parse_feed(xml_text: str) -> List[Paper]:
    """Parse the full Atom feed and return a list of Papers."""
    root = ET.fromstring(xml_text)
    papers: List[Paper] = []
    for entry in root.findall(f"{{{ATOM_NS}}}entry"):
        try:
            papers.append(_parse_entry(entry))
        except Exception as exc:
            logger.warning(f"Skipping malformed entry: {exc}")
    return papers


# Public API
def search_arxiv(
    query: str,
    max_results: int = 10,
    sort_by: str = "relevance",
    sort_order: str = "descending",
    start: int = 0,
) -> List[Paper]:
    """
    Generic ArXiv search.

    query supports ArXiv field prefixes:
      ti:   — title
      au:   — author
      abs:  — abstract
      cat:  — category
      all:  — all fields (default)
    Combine with AND, OR, ANDNOT.
    """
    params = {
        "search_query": query,
        "start": start,
        "max_results": min(max_results, MAX_RESULTS_CAP),
        "sortBy": sort_by,
        "sortOrder": sort_order,
    }
    resp = _rate_limited_get(ARXIV_API_BASE, params)
    return _parse_feed(resp.text)


def fetch_paper_by_id(arxiv_id: str) -> Optional[Paper]:
    """Fetch a single paper by its ArXiv ID (version suffix is stripped)."""
    clean_id = _strip_version(arxiv_id)
    params = {"id_list": clean_id, "max_results": 1}
    resp = _rate_limited_get(ARXIV_API_BASE, params)
    papers = _parse_feed(resp.text)
    return papers[0] if papers else None


def fetch_papers_by_ids(arxiv_ids: List[str]) -> List[Paper]:
    """Fetch multiple papers in one HTTP call using the id_list parameter."""
    clean_ids = ",".join(_strip_version(aid) for aid in arxiv_ids)
    params = {"id_list": clean_ids, "max_results": len(arxiv_ids)}
    resp = _rate_limited_get(ARXIV_API_BASE, params)
    return _parse_feed(resp.text)


def get_recent_papers(
    category: str,
    days_back: int = 7,
    max_results: int = 20,
) -> List[Paper]:
    """
    Papers submitted to `category` in the last `days_back` days.
    Uses ArXiv's submittedDate range filter.
    """
    now   = datetime.now(timezone.utc)
    start = now - timedelta(days=days_back)
    # ArXiv date format for submittedDate filter: YYYYMMDD*
    date_range = f"[{start.strftime('%Y%m%d')}* TO {now.strftime('%Y%m%d')}*]"
    query = f"cat:{category} AND submittedDate:{date_range}"
    return search_arxiv(
        query,
        max_results=max_results,
        sort_by="submittedDate",
        sort_order="descending",
    )


def get_author_papers(
    author_name: str,
    max_results: int = 10,
    sort_by: str = "submittedDate",
) -> List[Paper]:
    """Papers authored by `author_name`. Supports partial names."""
    query = f'au:"{author_name}"'
    return search_arxiv(query, max_results=max_results, sort_by=sort_by, sort_order="descending")


def search_by_category(
    category: str,
    query: str,
    max_results: int = 10,
    sort_by: str = "relevance",
) -> List[Paper]:
    """Keyword search scoped to a specific ArXiv category."""
    full_query = f"cat:{category} AND ({query})"
    return search_arxiv(full_query, max_results=max_results, sort_by=sort_by)


def search_by_title(title: str, max_results: int = 10) -> List[Paper]:
    """Search specifically in paper titles."""
    return search_arxiv(f"ti:{title}", max_results=max_results)


def search_by_abstract(terms: str, max_results: int = 10) -> List[Paper]:
    """Search specifically in abstracts."""
    return search_arxiv(f"abs:{terms}", max_results=max_results)


# Utilities
def _strip_version(arxiv_id: str) -> str:
    """Remove version suffix: '1706.03762v5' → '1706.03762'."""
    aid = arxiv_id.strip()
    # Pattern: ends with vN where N is a digit
    if aid[-1].isdigit() and "v" in aid:
        return aid.rsplit("v", 1)[0]
    return aid