"""Data models for ArXiv MCP Server."""

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional


@dataclass
class Paper:
    """Represents a single ArXiv paper with full metadata."""

    arxiv_id: str
    title: str
    authors: list[str]
    abstract: str
    published: str # ISO 8601, e.g. "2023-01-01T00:00:00Z"
    updated: str
    primary_category: str
    categories: list[str]
    pdf_url: str
    abstract_url: str
    doi: str | None = None
    journal_ref: str | None = None
    comment: str | None = None # Author-submitted comment (e.g. "15 pages, 4 figures")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def html_url(self) -> str:
        """ar5iv HTML rendering of the paper (LaTeX → HTML)."""
        return f"https://ar5iv.org/abs/{self.arxiv_id}"


@dataclass
class CitationPaper:
    """A paper in a citation / reference list (lighter weight)."""

    arxiv_id: str | None
    semantic_scholar_id: str | None
    title: str
    authors: list[str]
    year: int | None
    citation_count: int
    influential_citation_count: int
    abstract_url: str | None
    pdf_url: str | None
    venue: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)