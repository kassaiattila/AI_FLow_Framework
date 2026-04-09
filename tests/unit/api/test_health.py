"""
@test_registry:
    suite: api-unit
    component: api.health
    covers: [src/aiflow/api/v1/health.py]
    phase: 5
    priority: critical
    estimated_duration_ms: 300
    requires_services: []
    tags: [api, health, fastapi]
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from aiflow._version import __version__
from aiflow.api.app import create_app
from aiflow.api.v1.health import ReadyCheck


class TestHealthEndpoints:
    @pytest.fixture
    def client(self):
        app = create_app()
        return TestClient(app)

    def test_liveness(self, client):
        resp = client.get("/health/live")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "alive"

    def test_readiness(self, client):
        # Mock external service checks — unit tests must not depend on Docker
        mock_checks = {
            "_check_database": ReadyCheck(
                name="database", status="ok", message="PostgreSQL connected"
            ),
            "_check_pgvector": ReadyCheck(name="pgvector", status="ok", message="pgvector v0.7"),
            "_check_rag_data": ReadyCheck(name="rag_data", status="ok", message="2 collections"),
            "_check_redis": ReadyCheck(name="redis", status="ok", message="Redis PONG"),
            "_check_langfuse": ReadyCheck(
                name="langfuse", status="disabled", message="Not configured"
            ),
        }
        with (
            patch(
                "aiflow.api.v1.health._check_database",
                new_callable=AsyncMock,
                return_value=mock_checks["_check_database"],
            ),
            patch(
                "aiflow.api.v1.health._check_pgvector",
                new_callable=AsyncMock,
                return_value=mock_checks["_check_pgvector"],
            ),
            patch(
                "aiflow.api.v1.health._check_rag_data",
                new_callable=AsyncMock,
                return_value=mock_checks["_check_rag_data"],
            ),
            patch(
                "aiflow.api.v1.health._check_redis",
                new_callable=AsyncMock,
                return_value=mock_checks["_check_redis"],
            ),
            patch(
                "aiflow.api.v1.health._check_langfuse",
                new_callable=AsyncMock,
                return_value=mock_checks["_check_langfuse"],
            ),
        ):
            resp = client.get("/health/ready")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "ready"
            assert isinstance(data["checks"], list)
            assert len(data["checks"]) >= 2
            check_names = [c["name"] for c in data["checks"]]
            assert "database" in check_names
            assert "redis" in check_names

    def test_health_combined(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["version"] == __version__
        assert "environment" in data
        assert "checks" in data
        assert "status" in data

    def test_health_has_correct_version(self, client):
        resp = client.get("/health")
        data = resp.json()
        assert data["version"] == __version__

    def test_ready_checks_have_status(self, client):
        resp = client.get("/health/ready")
        data = resp.json()
        for check in data["checks"]:
            assert "name" in check
            assert "status" in check
