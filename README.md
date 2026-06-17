# arxiv-mcp-server

An MCP server that gives LLM agents structured access to ArXiv and Semantic Scholar. Search papers, pull full metadata, monitor category feeds, and walk citation relationships — all as first-class tool calls with no API keys required.

Built with [FastMCP](https://github.com/jlowin/fastmcp). Runs over `streamable-http`, `sse`, or `stdio`.

---

## Tools

| Tool | What it does |
|------|-------------|
| `search_papers` | Keyword search across all of ArXiv. Supports field prefixes (`ti:`, `au:`, `abs:`, `cat:`) and boolean operators. |
| `get_paper_details` | Full metadata for a paper by ID — enriched with citation count, venue, and fields of study from Semantic Scholar. |
| `get_paper_pdf_url` | Returns PDF, HTML (ar5iv), and LaTeX source URLs for a paper. Drop the PDF link straight into a RAG pipeline. |
| `get_recent_papers` | Papers submitted to a category in the last N days, sorted newest first. Good for daily/weekly digests. |
| `get_related_papers` | Outgoing references for a paper (its bibliography) via Semantic Scholar's citation graph. |
| `get_paper_citations` | Incoming citations (papers that cite a given paper). Useful for finding follow-up work. |
| `get_author_papers` | All ArXiv papers by an author. Partial name matching works. |
| `search_by_category` | Keyword search scoped to a specific ArXiv category. |
| `search_title` | Search specifically in paper titles — more precise than full-text search. |
| `batch_get_papers` | Fetch metadata for up to 20 papers in a single round-trip using ArXiv's `id_list`. |
| `search_semantic_scholar` | Broader search including non-ArXiv papers (journals, conferences). Supports year range and field-of-study filters. |

---

## Quickstart

**With Docker (recommended)**

```bash
git clone https://github.com/MeetRVyas/arxiv-mcp-server
cd arxiv-mcp-server

cp .env.example .env
docker compose up
```

Server is available at `http://localhost:8000`.

**Without Docker**

```bash
pip install -e .
arxiv-mcp-server --transport streamable-http --port 8000
```

Python 3.11+ required.

---

## Configuration

Copy `.env.example` to `.env`. The only variable that matters in practice:

```bash
# Optional — without this you get ~1 req/s to Semantic Scholar (fine for interactive use).
# With it you get ~10 req/s. Apply free at https://www.semanticscholar.org/product/api
SEMANTIC_SCHOLAR_API_KEY=your_key_here

LOG_LEVEL=INFO   # DEBUG | INFO | WARNING | ERROR
PORT=8000
```

ArXiv itself requires no authentication.

---

## Connecting to an MCP client

**Claude Desktop** — add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "arxiv": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

**stdio mode** (for agents that spawn the process directly):

```bash
arxiv-mcp-server --transport stdio
```

```json
{
  "mcpServers": {
    "arxiv": {
      "command": "arxiv-mcp-server",
      "args": ["--transport", "stdio"]
    }
  }
}
```

---

## Usage examples

**Search for papers**
```
search_papers(query="diffusion models image generation", max_results=5, sort_by="submittedDate")
```

ArXiv field syntax works too:
```
search_papers(query="ti:BERT AND au:Devlin", max_results=3)
```

**Get a specific paper**
```
get_paper_details(arxiv_id="1706.03762")
```
Returns the full record including abstract, categories, DOI, citation count, and venue — the last two sourced from Semantic Scholar.

**What dropped in cs.LG this week**
```
get_recent_papers(category="cs.LG", days_back=7, max_results=20)
```

**Explore a citation graph manually**
```
# Papers this paper cites (its intellectual foundations)
get_related_papers(arxiv_id="1706.03762", max_results=10)

# Papers that cite it (follow-up work)
get_paper_citations(arxiv_id="1706.03762", max_results=20)
```

**Fetch a PDF link for RAG ingestion**
```
get_paper_pdf_url(arxiv_id="2301.00001")
# → { "pdf_url": "https://arxiv.org/pdf/2301.00001", "html_url": "https://ar5iv.org/abs/2301.00001", ... }
```
`html_url` (ar5iv) is often better for text extraction than the raw PDF.

**Author lookup**
```
get_author_papers(author_name="Andrej Karpathy", max_results=10)
```

**Batch fetch**
```
batch_get_papers(arxiv_ids=["1706.03762", "1810.04805", "2005.14165"])
```

---

## Running tests

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

```
collected 20 items

tests/test_arxiv_mcp.py::TestStripVersion::test_strips_version PASSED
tests/test_arxiv_mcp.py::TestStripVersion::test_no_version PASSED
...
tests/test_arxiv_mcp.py::TestGetRecentPapersClamping::test_max_results_clamped PASSED

20 passed in 5.21s
```

HTTP calls to ArXiv and Semantic Scholar are mocked — tests run offline and fast. Coverage includes XML parsing, ID normalisation, PDF URL fallback logic, input validation, and clamping behaviour.

---

## Rate limits

**ArXiv** — the client enforces a 3-second delay between requests per [ArXiv's API guidelines](https://arxiv.org/help/api/user-manual#dos-and-donts). Requests also retry up to 4 times with exponential backoff (2 s, 4 s, 8 s, 16 s) on 429/5xx responses.

**Semantic Scholar** — ~1 req/s without an API key, ~10 req/s with one. Only `get_paper_details`, `get_related_papers`, `get_paper_citations`, and `search_semantic_scholar` hit Semantic Scholar. The rest are pure ArXiv.

---

## ArXiv category codes

A few common ones for reference:

```
cs.LG   Machine Learning          cs.AI   Artificial Intelligence
cs.CL   Computation & Language    cs.CV   Computer Vision
cs.RO   Robotics                  cs.CR   Cryptography & Security
stat.ML Statistical ML            eess.IV Image & Video Processing
math.OC Optimization & Control    q-bio.NC Neurons & Cognition
```

Full list at https://arxiv.org/category_taxonomy.

---

## Project structure

```
arxiv_mcp/
├── server.py             # FastMCP app and all 11 tool definitions
├── arxiv_client.py       # ArXiv Atom/XML API client (rate-limited, retrying)
├── semantic_scholar.py   # Semantic Scholar Graph API client
└── models.py             # Paper and CitationPaper dataclasses

tests/
└── test_arxiv_mcp.py     # 20 unit tests (mocked HTTP, no network required)

Dockerfile                # Multi-stage build, non-root user, healthcheck
docker-compose.yml
.env.example
pyproject.toml
```

---

## License

MIT