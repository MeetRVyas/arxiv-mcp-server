# ── Build stage ───────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build tooling only (not carried into final image)
RUN pip install --no-cache-dir hatchling

COPY pyproject.toml README.md ./
COPY arxiv_mcp/ ./arxiv_mcp/

# Build wheel
RUN pip wheel --no-deps --wheel-dir /wheels .


# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Non-root user for security
RUN addgroup --system mcp && adduser --system --ingroup mcp mcpuser

WORKDIR /app

# Install only runtime wheel + dependencies (no build tools)
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*.whl && rm -rf /wheels

# Owned by mcpuser
USER mcpuser

# Environment defaults (override via docker-compose or --env-file)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LOG_LEVEL=INFO \
    PORT=8000 \
    HOST=0.0.0.0

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" \
    || exit 1

ENTRYPOINT ["arxiv-mcp-server"]
CMD ["--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8000"]