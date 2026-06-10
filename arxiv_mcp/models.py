"""Data models for ArXiv MCP Server."""

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional


@dataclass
class Paper:
    """Represents a single ArXiv paper with full metadata."""

    arxiv_id: str
    title: str
    authors: List[str]
    abstract: str
    published: str          # ISO 8601, e.g. "2023-01-01T00:00:00Z"
    updated: str
    primary_category: str
    categories: List[str]
    pdf_url: str
    abstract_url: str
    doi: Optional[str] = None
    journal_ref: Optional[str] = None
    comment: Optional[str] = None   # Author-submitted comment (e.g. "15 pages, 4 figures")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def html_url(self) -> str:
        """ar5iv HTML rendering of the paper (LaTeX → HTML)."""
        return f"https://ar5iv.org/abs/{self.arxiv_id}"