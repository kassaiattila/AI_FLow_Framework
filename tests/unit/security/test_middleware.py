"""
@test_registry:
    suite: security-unit
    component: api.middleware
    covers: [src/aiflow/api/middleware.py]
    phase: 5
    priority: critical
    estimated_duration_ms: 300
    requires_services: []
    tags: [security, middleware, headers, rate-limit, upload-size]
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from aiflow.api.middleware import (
    MaxBodySizeMiddleware,
    SecurityHeadersMiddleware,
)


def _make_app(*middlewares) -> FastAPI:
    """Create a minimal FastAPI app with the given middleware classes."""
    app = FastAPI()

    for mw in middlewares:
        app.add_middleware(mw)

    @app.get("/test")
    async def test_endpoint():
        return {"ok": True}

    @app.post("/upload")
    async def upload_endpoint():
        return {"uploaded": True}

    return app


class TestSecurityHeadersMiddleware:
    @pytest.fixture
    def client(self):
        app = _make_app(SecurityHeadersMiddleware)
        return TestClient(app)

    def test_x_content_type_options(self, client):
        r = client.get("/test")
        assert r.headers["X-Content-Type-Options"] == "nosniff"

    def test_x_frame_options(self, client):
        r = client.get("/test")
        assert r.headers["X-Frame-Options"] == "DENY"

    def test_x_xss_protection(self, client):
        r = client.get("/test")
        assert r.headers["X-XSS-Protection"] == "1; mode=block"

    def test_referrer_policy(self, client):
        r = client.get("/test")
        assert r.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

    def test_permissions_policy(self, client):
        r = client.get("/test")
        assert "camera=()" in r.headers["Permissions-Policy"]

    def test_csp(self, client):
        r = client.get("/test")
        assert "default-src 'self'" in r.headers["Content-Security-Policy"]
        assert "frame-ancestors 'none'" in r.headers["Content-Security-Policy"]

    def test_no_hsts_on_http(self, client):
        """HSTS should NOT be set for plain HTTP requests."""
        r = client.get("/test")
        assert "Strict-Transport-Security" not in r.headers


class TestMaxBodySizeMiddleware:
    def test_small_body_accepted(self):
        app = _make_app(MaxBodySizeMiddleware)
        client = TestClient(app)
        r = client.post("/upload", content=b"small data", headers={"content-length": "10"})
        assert r.status_code == 200

    def test_oversized_body_rejected(self, monkeypatch):
        monkeypatch.setenv("AIFLOW_MAX_UPLOAD_BYTES", "100")
        # Re-import to pick up the env change — or test with a large Content-Length header
        app = _make_app(MaxBodySizeMiddleware)
        client = TestClient(app)
        # Send a request claiming to be very large
        r = client.post(
            "/upload",
            content=b"x",
            headers={"content-length": str(100 * 1024 * 1024)},
        )
        assert r.status_code == 413
        assert "too large" in r.json()["detail"].lower()

    def test_no_content_length_passes(self):
        app = _make_app(MaxBodySizeMiddleware)
        client = TestClient(app)
        r = client.get("/test")
        assert r.status_code == 200
