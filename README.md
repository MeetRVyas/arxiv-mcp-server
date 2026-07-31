# arxiv-mcp-server

[![CI](https://github.com/MeetRVyas/arxiv-mcp-server/actions/workflows/ci.yml/badge.svg)](https://github.com/MeetRVyas/arxiv-mcp-server/actions/workflows/ci.yml)

An MCP server that gives LLM agents structured access to ArXiv and Semantic Scholar. Search papers, pull full metadata, monitor category feeds, and walk citation relationships — all as first-class tool calls, open access by default with no API keys required.

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
| `search_abstract` | Search specifically in paper abstracts. |
| `batch_get_papers` | Fetch metadata for up to 20 papers in a single round-trip using ArXiv's `id_list`. |
| `search_semantic_scholar` | Broader search including non-ArXiv papers (journals, conferences). Supports year range and field-of-study filters. |

All 12 tools are read-only lookups (`readOnlyHint=True`, `destructiveHint=False`) and carry a human-readable `title` in addition to their machine name, for clients that render one.

### Resources

| URI | Description |
|-----|-------------|
| `arxiv://reference/query-syntax` | Field prefixes and boolean operators for constructing advanced `search_query` strings. |
| `arxiv://reference/categories/cs` | Full list of `cs.*` category codes (e.g., `cs.AI`, `cs.LG`) and their descriptions. |
| `arxiv://reference/categories/math` | Full list of `math.*` category codes and their descriptions. |
| `arxiv://reference/categories/physics` | Categories for Physics, Astrophysics, Condensed Matter, High Energy, etc. |
| `arxiv://reference/categories/<domain>` | Replace `<domain>` with `econ`, `eess`, `q-bio`, `q-fin`, or `stat` for their respective lists. |

### Prompts

The server exposes reusable prompts that orchestrate multiple tools into higher-level research workflows. They help the LLM perform evidence-based synthesis rather than individual API lookups.

| Prompt | Purpose |
|--------|---------|
| `literature_review` | Search broadly across the literature and synthesize the field into major research themes, representative papers, trends, challenges, and open research questions. |
| `survey_generator` | Produce a survey-style overview by organizing the literature into a taxonomy of approaches, comparing methodologies, and identifying future research directions. |
| `explain_paper` | Retrieve a paper and explain its motivation, methodology, experimental evaluation, contributions, limitations, and significance at an appropriate technical level. |
| `find_related_work` | Discover foundational, competing, complementary, and recent work related to a paper or research topic. |
| `paper_comparison` | Compare multiple papers across methodology, assumptions, experiments, strengths, limitations, and practical applicability. |
| `author_profile` | Analyze a researcher's publication history, research evolution, major contributions, and scientific impact. |
| `research_lineage` | Trace the intellectual foundations and evolution of ideas leading to a paper. |
| `field_digest` | Summarize recent developments within a research field by identifying emerging themes, trends, and representative work. |
| `gap_spotter` | Identify evidence-backed research gaps, methodological limitations, conflicting findings, and promising research opportunities. |
| `cross_domain_bridge` | Discover meaningful conceptual and methodological connections between two research domains. |
| `claim_check` | Evaluate whether the research literature supports, contradicts, or refines a scientific claim. |
| `paper_critique` | Critically evaluate a paper by assessing its methodology, evidence, limitations, and long-term influence. |
| `research_timeline` | Construct a chronological narrative describing how a research field evolved through major milestones and breakthroughs. |
| `state_of_the_art` | Identify and compare the current leading approaches, benchmarks, and remaining challenges within a research area. |
| `paper_recommender` | Recommend papers tailored to a specific learning, implementation, or research objective. |
| `method_evolution` | Trace how a research method or technique evolved through major conceptual and methodological improvements. |
| `citation_summary` | Explain why a paper became influential by analyzing how later research adopted, extended, or challenged its ideas. |
| `research_brief` | Produce a concise executive briefing summarizing the current state and direction of a research area. |
| `research_mentor` | Act as an adaptive research mentor by guiding learning, recommending literature, and suggesting future research directions. |
| `novelty_checker` | Assess the originality of a research idea by comparing it against existing literature and identifying similar work. |
| `technique_selector` | Recommend and compare research techniques best suited to solving a given scientific or engineering problem. |
| `evidence_matrix` | Organize the literature into supporting, contradicting, partial, and inconclusive evidence for a research question. |
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
arxiv-mcp-server --transport streamable-http
```

Python 3.11+ required. `--transport` defaults to `streamable-http`; pass `--transport stdio` for direct-spawn agents, or `--transport sse` for backwards compatibility.

---

## Configuration

Copy `.env.example` to `.env` and fill in what you need. Every variable is read in exactly one place (`arxiv_mcp/config.py`), and `.env` is loaded the same way whether you run `arxiv-mcp-server` directly or inside Docker Compose — there's no difference in behavior between the two paths.

```bash
# Server
PORT=8000
HOST=0.0.0.0
LOG_LEVEL=INFO          # DEBUG | INFO | WARNING | ERROR
LOG_FORMAT=text         # text | json

# Semantic Scholar (optional)
# Without a key: ~1 req/s (fine for interactive use). With one: ~10 req/s.
# Apply free at https://www.semanticscholar.org/product/api
SEMANTIC_SCHOLAR_API_KEY=

# HTTP access control (see "Security & access control" below)
MCP_API_KEY=
RATE_LIMIT_PER_MINUTE=30
ALLOWED_ORIGINS=

# Overall wall-clock budget per tool call's external HTTP work
REQUEST_DEADLINE_SECONDS=20
```

ArXiv itself requires no authentication.

---

## Security & access control

This server takes the same posture as ArXiv's own API: **open access by default**, since it's a read-only, public-data research tool with nothing sensitive to protect behind a login. Two things back that up:

- **Per-IP throttling is always on** for the HTTP transports (default 30 req/min per client IP, configurable via `RATE_LIMIT_PER_MINUTE`), so no single caller can consume the whole shared ArXiv/Semantic Scholar rate-limit budget.
- Set **`MCP_API_KEY`** to flip to gated access instead — every HTTP request then needs `Authorization: Bearer <value>`.

**CORS** is off by default (no `Access-Control-Allow-Origin` headers), since the expected clients are server-to-server or desktop-app MCP clients, not in-browser JavaScript. Set `ALLOWED_ORIGINS` (comma-separated) if a browser-based client needs to reach this server directly.

`GET /health` is always reachable, unauthenticated and unthrottled, for container orchestrators and PaaS health checks.

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

ArXiv field syntax works too (see the `arxiv://reference/query-syntax` resource for the full reference):
```
search_papers(query="ti:BERT AND au:Devlin", max_results=3)
```

**Get a specific paper**
```
get_paper_details(arxiv_id="1706.03762")
```
Returns the full record including abstract, categories, DOI, citation count, and venue — the last two sourced from Semantic Scholar. If Semantic Scholar enrichment is unavailable (rather than simply not-yet-indexed), the response says so explicitly instead of silently omitting those fields.

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

Every tool returns a single JSON object (never a bare list) — either `{"papers": [...], "total_returned": N, ...}` on success, `{"papers": [], "message": "..."}` when the search is well-formed but finds nothing, or `{"error": "..."}` on a validation or upstream failure.

---

## Running tests

```bash
pip install -e ".[dev]"
pytest -v
```

HTTP calls to ArXiv and Semantic Scholar are mocked (via `responses`) — tests run offline and fast. Coverage spans XML parsing, ID normalization/validation, error-path translation (not-found vs. upstream-unavailable), input validation, clamping behavior, the shared rate limiter's thread-safety, per-IP HTTP throttling, and — via a real in-memory FastMCP `Client` — the actual client-facing protocol surface: tool schemas, descriptions, annotations, resources, and prompts.


```bash
ruff check .            # lint
ruff format --check .   # formatting
mypy arxiv_mcp           # strict type-checking
```

All three run in CI on every push and pull request (see `.github/workflows/ci.yml`).

---

## Rate limits

**ArXiv** — the client enforces a 3-second delay between requests per [ArXiv's API guidelines](https://arxiv.org/help/api/user-manual#dos-and-donts), via a single shared, thread-safe rate limiter. Requests retry up to 2 times with backoff (starting at 1s) on 429/5xx responses, and every tool call's total external HTTP time (including retries) is bounded by `REQUEST_DEADLINE_SECONDS` (default 20s) so a slow upstream fails fast and cleanly instead of hanging.

**Semantic Scholar** — ~1 req/s without an API key, ~10 req/s with one, via its own shared rate limiter. Only `get_paper_details`, `get_related_papers`, `get_paper_citations`, and `search_semantic_scholar` hit Semantic Scholar. The rest are pure ArXiv.

Both rate limiters are in-process and single-instance — if you ever horizontally scale this server, each replica paces its own outbound traffic independently rather than sharing one global budget.

---

## ArXiv category codes

The full, canonical reference is the `arxiv://reference/categories` MCP resource this server exposes. A few common ones to get started:

```
cs.LG   Machine Learning          cs.AI   Artificial Intelligence
cs.CL   Computation & Language    cs.CV   Computer Vision
stat.ML Statistical ML            q-bio.NC Neurons & Cognition
```

Full taxonomy: https://arxiv.org/category_taxonomy

---

## Project structure

```
arxiv_mcp/
├── server.py              # FastMCP app: 12 tools, 2 resources, 3 prompts, /health route
├── arxiv.py                # ArXiv Atom/XML API client (rate-limited, retrying, HTTPS, defusedxml)
├── semantic_scholar.py     # Semantic Scholar Graph API client
├── models.py                # Paper and CitationPaper dataclasses
├── config.py                 # Centralized, typed Settings (env / .env — the only os.getenv() in the codebase)
├── validation.py              # arxiv_id / query / category input validation
├── errors.py                   # Shared exception types + error-envelope convention
├── rate_limiter.py              # Single thread-safe rate limiter shared by both API clients
├── http_utils.py                 # Retry-session builder + wall-clock call-deadline wrapper
├── middleware.py                  # Per-IP HTTP throttling + optional bearer-token auth
├── resources.py                    # Query-syntax / category reference text, owned once, exposed as Resources
└── prompts/
    ├── __init__.py            # Registers all prompt modules
    ├── learning.py            # Learning and paper understanding prompts
    ├── synthesis.py           # Literature synthesis and survey prompts
    ├── analysis.py            # Paper, author, citation, and impact analysis prompts
    ├── discovery.py           # Related work, research gaps, novelty, and cross-domain discovery
    └── evaluation.py          # Claim evaluation, technique selection, evidence, and recommendations

tests/
├── conftest.py
├── test_arxiv_client.py
├── test_semantic_scholar_client.py
├── test_validation.py
├── test_rate_limiter.py
├── test_config.py
├── test_middleware.py
├── test_server_tools.py           # direct-call unit tests of tool logic
└── test_protocol_surface.py       # real FastMCP Client: schemas, descriptions, annotations, resources, prompts

.github/workflows/ci.yml   # lint + type-check + test on every push/PR
Dockerfile                 # Multi-stage build, non-root user, healthcheck
docker-compose.yml
.env.example
pyproject.toml
```

---

## License

MIT