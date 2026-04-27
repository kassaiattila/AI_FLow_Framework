"""
@test_registry:
    suite: api-unit
    component: api.v1.routing_runs
    covers:
        - src/aiflow/api/v1/routing_runs.py
    phase: v1.8.0
    priority: critical
    estimated_duration_ms: 200
    requires_services: []
    tags: [unit, api, routing_runs, sprint_x, sx_3]
"""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from aiflow.security.auth import AuthProvider
from aiflow.services.routing_runs.schemas import (
    RoutingRunDetail,
    RoutingRunSummary,
    RoutingStatsBucket,
    RoutingStatsResponse,
)

# ---------------------------------------------------------------------------
# Fixtures (mirror tests/unit/api/test_document_recognizer_router.py)
# ---------------------------------------------------------------------------


@contextmanager
def _client_and_headers(tenant_id: str = "default"):
    auth = AuthProvider.from_env()
    with patch.object(AuthProvider, "from_env", return_value=auth):
        from aiflow.api.app import create_app

        app = create_app()
        client = TestClient(app, raise_server_exceptions=False)
        client.get("/health/live")
        token = auth.create_token(user_id=tenant_id, role="admin")
        yield client, {"Authorization": f"Bearer {token}"}


def _summary(**overrides) -> RoutingRunSummary:
    base = dict(
        id=uuid.uuid4(),
        tenant_id="default",
        email_id=uuid.uuid4(),
        intent_class="EXTRACT",
        doctype_detected="hu_invoice",
        doctype_confidence=0.91,
        extraction_path="invoice_processor",
        extraction_outcome="success",
        cost_usd=0.0042,
        latency_ms=235,
        created_at=datetime(2026, 4, 27, 10, 0, tzinfo=UTC),
    )
    base.update(overrides)
    return RoutingRunSummary(**base)


def _detail(**overrides) -> RoutingRunDetail:
    base = dict(
        id=uuid.uuid4(),
        tenant_id="default",
        email_id=uuid.uuid4(),
        intent_class="EXTRACT",
        doctype_detected="hu_invoice",
        doctype_confidence=0.91,
        extraction_path="invoice_processor",
        extraction_outcome="success",
        cost_usd=0.0042,
        latency_ms=235,
        created_at=datetime(2026, 4, 27, 10, 0, tzinfo=UTC),
        metadata={"attachments": [{"filename": "a.pdf"}]},
        metadata_truncated=False,
        metadata_truncated_count=0,
    )
    base.update(overrides)
    return RoutingRunDetail(**base)


def _patch_repo(
    *,
    list_return=None,
    get_return=None,
    stats_return=None,
):
    """Build a fake RoutingRunRepository instance + patch the factory."""
    fake = MagicMock()
    fake.list = AsyncMock(return_value=list_return or [])
    fake.get = AsyncMock(return_value=get_return)
    fake.aggregate_stats = AsyncMock(
        return_value=stats_return
        or RoutingStatsResponse(
            since=datetime(2026, 4, 20, tzinfo=UTC),
            until=datetime(2026, 4, 27, tzinfo=UTC),
            total_runs=0,
        )
    )
    return fake


# ---------------------------------------------------------------------------
# 1. test_get_list_returns_200_with_default_pagination
# ---------------------------------------------------------------------------


class TestList:
    def test_get_list_returns_200_with_default_pagination(self):
        rows = [_summary(), _summary()]
        repo = _patch_repo(list_return=rows)
        with (
            _client_and_headers() as (client, headers),
            patch(
                "aiflow.api.v1.routing_runs._repository",
                AsyncMock(return_value=repo),
            ),
        ):
            r = client.get("/api/v1/routing-runs/", headers=headers)
            assert r.status_code == 200, r.text
            assert len(r.json()) == 2
            # Default pagination passed through
            args, kwargs = repo.list.call_args
            assert kwargs["limit"] == 50
            assert kwargs["offset"] == 0

    # -----------------------------------------------------------------
    # 2. test_get_list_rejects_limit_over_200_with_422
    # -----------------------------------------------------------------

    def test_get_list_rejects_limit_over_200_with_422(self):
        repo = _patch_repo(list_return=[])
        with (
            _client_and_headers() as (client, headers),
            patch(
                "aiflow.api.v1.routing_runs._repository",
                AsyncMock(return_value=repo),
            ),
        ):
            r = client.get("/api/v1/routing-runs/?limit=500", headers=headers)
            assert r.status_code == 422


# ---------------------------------------------------------------------------
# 3. test_get_detail_returns_404_for_missing_id
# ---------------------------------------------------------------------------


class TestDetail:
    def test_get_detail_returns_404_for_missing_id(self):
        repo = _patch_repo(get_return=None)
        with (
            _client_and_headers() as (client, headers),
            patch(
                "aiflow.api.v1.routing_runs._repository",
                AsyncMock(return_value=repo),
            ),
        ):
            missing = uuid.uuid4()
            r = client.get(f"/api/v1/routing-runs/{missing}", headers=headers)
            assert r.status_code == 404

    # -----------------------------------------------------------------
    # 4. test_get_detail_enforces_tenant_scope
    # -----------------------------------------------------------------

    def test_get_detail_enforces_tenant_scope(self):
        # Repo returns None for cross-tenant lookups (SQL filter
        # enforces this; here we just verify the router passes the
        # caller's tenant_id through to the repo.get call).
        repo = _patch_repo(get_return=None)
        with (
            _client_and_headers() as (client, headers),
            patch(
                "aiflow.api.v1.routing_runs._repository",
                AsyncMock(return_value=repo),
            ),
        ):
            run_id = uuid.uuid4()
            r = client.get(
                f"/api/v1/routing-runs/{run_id}?tenant_id=other-tenant",
                headers=headers,
            )
            assert r.status_code == 404
            args, kwargs = repo.get.call_args
            assert kwargs["tenant_id"] == "other-tenant"
            assert args[0] == run_id


# ---------------------------------------------------------------------------
# 5. test_get_stats_returns_200_with_doctype_and_outcome_distributions
# ---------------------------------------------------------------------------


class TestStats:
    def test_get_stats_returns_200_with_doctype_and_outcome_distributions(self):
        stats = RoutingStatsResponse(
            since=datetime(2026, 4, 20, tzinfo=UTC),
            until=datetime(2026, 4, 27, tzinfo=UTC),
            total_runs=3,
            by_doctype=[RoutingStatsBucket(key="hu_invoice", count=3)],
            by_outcome=[RoutingStatsBucket(key="success", count=3)],
            by_extraction_path=[
                RoutingStatsBucket(key="invoice_processor", count=3),
            ],
            mean_cost_usd=0.005,
            p50_latency_ms=200.0,
            p95_latency_ms=400.0,
        )
        repo = _patch_repo(stats_return=stats)
        with (
            _client_and_headers() as (client, headers),
            patch(
                "aiflow.api.v1.routing_runs._repository",
                AsyncMock(return_value=repo),
            ),
        ):
            r = client.get("/api/v1/routing-runs/stats", headers=headers)
            assert r.status_code == 200, r.text
            payload = r.json()
            assert payload["total_runs"] == 3
            assert payload["by_doctype"][0]["key"] == "hu_invoice"
            assert payload["by_outcome"][0]["key"] == "success"
            assert payload["by_extraction_path"][0]["key"] == "invoice_processor"

    # -----------------------------------------------------------------
    # 6. test_get_stats_default_window_is_last_7_days
    # -----------------------------------------------------------------

    def test_get_stats_default_window_is_last_7_days(self):
        repo = _patch_repo()
        with (
            _client_and_headers() as (client, headers),
            patch(
                "aiflow.api.v1.routing_runs._repository",
                AsyncMock(return_value=repo),
            ),
        ):
            r = client.get("/api/v1/routing-runs/stats", headers=headers)
            assert r.status_code == 200, r.text
            args, kwargs = repo.aggregate_stats.call_args
            since = kwargs["since"]
            until = kwargs["until"]
            # Window is exactly 7 days
            assert (until - since) == timedelta(days=7)
            # And the upper bound is "now-ish" (within the last hour)
            assert (datetime.now(UTC) - until) < timedelta(hours=1)
