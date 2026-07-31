"""
HTTP-layer access control for the `streamable-http` deployment.

Setting `MCP_API_KEY` flips the deployment to require a bearer
token on every request, using FastMCP's `TokenVerifier` — a lightweight fit
for a single shared credential, without standing up a full OAuth server.
"""

from __future__ import annotations

import threading
import time

from fastmcp.server.auth import AccessToken, TokenVerifier
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp


class PerIPRateLimitMiddleware(BaseHTTPMiddleware):
    """A simple fixed-window per-IP request limiter."""

    def __init__(self, app: ASGIApp, requests_per_minute: int = 30) -> None:
        super().__init__(app)
        self._limit = requests_per_minute
        self._window_seconds = 60.0
        self._lock = threading.Lock()
        # client_ip -> (window_start_monotonic, count_in_window)
        self._buckets: dict[str, tuple[float, int]] = {}

    def _client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"

    def _allow(self, client_ip: str) -> bool:
        now = time.monotonic()
        with self._lock:
            window_start, count = self._buckets.get(client_ip, (now, 0))
            if now - window_start >= self._window_seconds:
                window_start, count = now, 0
            count += 1
            self._buckets[client_ip] = (window_start, count)
            return count <= self._limit

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Only throttle the MCP protocol traffic itself — leave /health
        # reachable for orchestrators regardless of caller volume.
        if request.url.path == "/health":
            response: Response = await call_next(request)
            return response

        client_ip = self._client_ip(request)
        if not self._allow(client_ip):
            return JSONResponse(
                {"error": "Rate limit exceeded. Slow down and try again shortly."},
                status_code=429,
            )
        response = await call_next(request)
        return response


class StaticTokenVerifier(TokenVerifier):
    """Verifies a single shared bearer token against `MCP_API_KEY`.

    Intentionally minimal: one static credential, no scopes, no expiry —
    the lightweight end of what FastMCP's `TokenVerifier` supports, for a
    deployment that just wants to gate access behind one shared secret
    rather than build out full OAuth.
    """

    def __init__(self, expected_token: str) -> None:
        super().__init__()
        self._expected_token = expected_token

    async def verify_token(self, token: str) -> AccessToken | None:
        if token == self._expected_token:
            return AccessToken(token=token, client_id="shared-client", scopes=[])
        return None
