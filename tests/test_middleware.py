"""Tests for arxiv_mcp.middleware."""

from __future__ import annotations

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from arxiv_mcp.middleware import PerIPRateLimitMiddleware, StaticTokenVerifier


def _build_app(requests_per_minute: int) -> Starlette:
    async def health(request):
        return PlainTextResponse("ok")

    async def other(request):
        return PlainTextResponse("handled")

    return Starlette(
        routes=[Route("/health", health), Route("/mcp", other, methods=["POST"])],
        middleware=[Middleware(PerIPRateLimitMiddleware, requests_per_minute=requests_per_minute)],
    )


class TestPerIPRateLimitMiddleware:
    def test_health_endpoint_is_never_throttled(self):
        app = _build_app(requests_per_minute=1)
        with TestClient(app) as client:
            for _ in range(10):
                resp = client.get("/health")
                assert resp.status_code == 200

    def test_throttles_after_limit_exceeded(self):
        app = _build_app(requests_per_minute=2)
        with TestClient(app) as client:
            r1 = client.post("/mcp")
            r2 = client.post("/mcp")
            r3 = client.post("/mcp")
            assert r1.status_code == 200
            assert r2.status_code == 200
            assert r3.status_code == 429

    def test_429_response_has_clean_error_body(self):
        app = _build_app(requests_per_minute=1)
        with TestClient(app) as client:
            client.post("/mcp")
            resp = client.post("/mcp")
            assert resp.status_code == 429
            assert "error" in resp.json()

    def test_different_ips_tracked_independently(self):
        app = _build_app(requests_per_minute=1)
        with TestClient(app) as client:
            r1 = client.post("/mcp", headers={"x-forwarded-for": "1.1.1.1"})
            r2 = client.post("/mcp", headers={"x-forwarded-for": "2.2.2.2"})
            assert r1.status_code == 200
            assert r2.status_code == 200  # different client IP, own budget


class TestStaticTokenVerifier:
    async def test_correct_token_verifies(self):
        verifier = StaticTokenVerifier("secret-token")
        result = await verifier.verify_token("secret-token")
        assert result is not None
        assert result.token == "secret-token"

    async def test_wrong_token_rejected(self):
        verifier = StaticTokenVerifier("secret-token")
        result = await verifier.verify_token("wrong-token")
        assert result is None
