"""
@test_registry:
    suite: core-unit
    component: services.routing_runs.repository
    covers:
        - src/aiflow/services/routing_runs/repository.py
        - src/aiflow/services/routing_runs/schemas.py
    phase: v1.8.0
    priority: high
    estimated_duration_ms: 60
    requires_services: []
    tags: [unit, services, routing_runs, sprint_x, sx_3]
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from aiflow.services.routing_runs.repository import (
    METADATA_BYTE_CAP,
    RoutingRunRepository,
    _build_list_sql,
)
from aiflow.services.routing_runs.schemas import (
    RoutingRunCreate,
    RoutingRunFilters,
    aggregate_outcome,
    summarize_routing_decision,
)


def _fake_pool_with_capture() -> tuple[MagicMock, dict]:
    """Mirror tests/unit/services/document_recognizer/test_repository.py pattern."""
    captured: dict[str, list] = {"execute_args": [], "fetch_args": [], "fetchrow_args": []}

    fake_conn = MagicMock()
    fake_conn.execute = AsyncMock()
    fake_conn.fetch = AsyncMock(return_value=[])
    fake_conn.fetchrow = AsyncMock(return_value=None)

    async def fake_execute(*args, **kwargs):
        captured["execute_args"].append((args, kwargs))

    async def fake_fetch(*args, **kwargs):
        captured["fetch_args"].append((args, kwargs))
        return []

    async def fake_fetchrow(*args, **kwargs):
        captured["fetchrow_args"].append((args, kwargs))
        return None

    fake_conn.execute.side_effect = fake_execute
    fake_conn.fetch.side_effect = fake_fetch
    fake_conn.fetchrow.side_effect = fake_fetchrow

    fake_acquire_cm = MagicMock()
    fake_acquire_cm.__aenter__ = AsyncMock(return_value=fake_conn)
    fake_acquire_cm.__aexit__ = AsyncMock(return_value=None)

    pool = MagicMock()
    pool.acquire = MagicMock(return_value=fake_acquire_cm)
    return pool, captured


# ---------------------------------------------------------------------------
# 1. test_insert_returns_uuid_and_persists
# ---------------------------------------------------------------------------


class TestInsert:
    @pytest.mark.asyncio
    async def test_insert_returns_uuid_and_persists(self):
        pool, captured = _fake_pool_with_capture()
        repo = RoutingRunRepository(pool)
        row = RoutingRunCreate(
            tenant_id="acme",
            email_id=uuid.uuid4(),
            intent_class="EXTRACT",
            doctype_detected="hu_invoice",
            doctype_confidence=0.93,
            extraction_path="invoice_processor",
            extraction_outcome="success",
            cost_usd=0.0042,
            latency_ms=235,
            metadata={"attachments": [{"filename": "a.pdf"}]},
        )

        run_id = await repo.insert(row)

        assert isinstance(run_id, uuid.UUID)
        assert len(captured["execute_args"]) == 1
        call = captured["execute_args"][0][0]
        sql = call[0]
        args = call[1:]
        assert "INSERT INTO routing_runs" in sql
        assert args[1] == "acme"
        assert args[3] == "EXTRACT"
        assert args[4] == "hu_invoice"
        assert args[6] == "invoice_processor"
        assert args[7] == "success"
        meta = json.loads(args[10])
        assert meta == {"attachments": [{"filename": "a.pdf"}]}

    # ---------------------------------------------------------------------
    # 2. test_insert_truncates_metadata_over_8kb_and_warns
    # ---------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_insert_truncates_metadata_over_8kb_and_warns(self, caplog):
        pool, captured = _fake_pool_with_capture()
        repo = RoutingRunRepository(pool)

        # Build a metadata payload that is reliably above the 8 KB cap.
        big_attachments = [
            {
                "attachment_id": str(i),
                "filename": f"file_{i}.pdf",
                "blob": "x" * 200,
            }
            for i in range(80)
        ]
        row = RoutingRunCreate(
            tenant_id="acme",
            email_id=uuid.uuid4(),
            intent_class="EXTRACT",
            doctype_detected="hu_invoice",
            doctype_confidence=0.9,
            extraction_path="invoice_processor",
            extraction_outcome="success",
            cost_usd=0.0,
            latency_ms=10,
            metadata={"attachments": big_attachments},
        )

        await repo.insert(row)

        sent_blob = captured["execute_args"][0][0][11]
        assert sent_blob is not None
        assert len(sent_blob.encode("utf-8")) <= METADATA_BYTE_CAP
        sent = json.loads(sent_blob)
        # Truncation flagged + count > 0 + attachments shrunk
        assert sent["_truncated"] is True
        assert sent["_truncated_count"] >= 1
        assert len(sent["attachments"]) < len(big_attachments)


# ---------------------------------------------------------------------------
# 3 & 4. List filter SQL composition
# ---------------------------------------------------------------------------


class TestListFilters:
    def test_list_filters_by_tenant_isolates_correctly(self):
        filters = RoutingRunFilters(tenant_id="acme")
        sql, params = _build_list_sql(filters, limit=50, offset=0, columns="summary")
        assert "tenant_id = $1" in sql
        assert params[0] == "acme"
        # limit + offset bound at the end
        assert sql.rstrip().endswith("LIMIT $2 OFFSET $3")
        assert params[1] == 50
        assert params[2] == 0
        # No spurious WHERE clauses (column names appear in SELECT, but
        # we want to assert they aren't bound as filter predicates).
        assert "intent_class = $" not in sql
        assert "doctype_detected = $" not in sql

    def test_list_filters_by_doctype_and_outcome_combine(self):
        filters = RoutingRunFilters(
            tenant_id="acme",
            doctype_detected="hu_invoice",
            extraction_outcome="success",
        )
        sql, params = _build_list_sql(filters, limit=25, offset=10, columns="summary")
        # All three filters AND-combined
        assert "tenant_id = $1" in sql
        assert "doctype_detected = $2" in sql
        assert "extraction_outcome = $3" in sql
        assert " AND " in sql
        assert params[:3] == ["acme", "hu_invoice", "success"]
        assert "ORDER BY created_at DESC" in sql


# ---------------------------------------------------------------------------
# 5. test_get_returns_none_for_other_tenant
# ---------------------------------------------------------------------------


class TestGet:
    @pytest.mark.asyncio
    async def test_get_returns_none_for_other_tenant(self):
        pool, captured = _fake_pool_with_capture()
        repo = RoutingRunRepository(pool)

        result = await repo.get(uuid.uuid4(), tenant_id="other-tenant")

        assert result is None
        # SQL enforces the tenant filter at the WHERE clause level
        assert len(captured["fetchrow_args"]) == 1
        sql = captured["fetchrow_args"][0][0][0]
        assert "WHERE id = $1 AND tenant_id = $2" in sql


# ---------------------------------------------------------------------------
# 6. test_aggregate_stats_returns_zero_window_safely
# ---------------------------------------------------------------------------


class TestAggregateStats:
    @pytest.mark.asyncio
    async def test_aggregate_stats_returns_zero_window_safely(self):
        # Empty-window: fetchrow returns zeroed totals; fetch returns
        # empty distributions. Repository must build a valid response
        # without hitting empty-row attribute errors.
        zero_row = {
            "total_runs": 0,
            "mean_cost": 0,
            "p50_latency": 0,
            "p95_latency": 0,
        }

        fake_conn = MagicMock()
        fake_conn.fetchrow = AsyncMock(return_value=zero_row)
        fake_conn.fetch = AsyncMock(return_value=[])
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=fake_conn)
        cm.__aexit__ = AsyncMock(return_value=None)
        pool = MagicMock()
        pool.acquire = MagicMock(return_value=cm)

        repo = RoutingRunRepository(pool)
        since = datetime(2026, 4, 1, tzinfo=UTC)
        until = datetime(2026, 4, 2, tzinfo=UTC)

        resp = await repo.aggregate_stats(tenant_id="acme", since=since, until=until)

        assert resp.total_runs == 0
        assert resp.by_doctype == []
        assert resp.by_outcome == []
        assert resp.by_extraction_path == []
        assert resp.mean_cost_usd == 0.0
        assert resp.p50_latency_ms == 0.0
        assert resp.p95_latency_ms == 0.0


# ---------------------------------------------------------------------------
# Schema helper tests (extra coverage; aggregation rules are load-bearing)
# ---------------------------------------------------------------------------


class TestAggregateOutcome:
    def test_empty_returns_skipped(self):
        assert aggregate_outcome([]) == "skipped"

    def test_single_succeeded_maps_to_success(self):
        assert aggregate_outcome(["succeeded"]) == "success"

    def test_single_timed_out_maps_to_failed(self):
        assert aggregate_outcome(["timed_out"]) == "failed"

    def test_mixed_with_success_yields_partial(self):
        assert aggregate_outcome(["succeeded", "failed"]) == "partial"

    def test_all_refused_cost_yields_refused_cost(self):
        assert aggregate_outcome(["refused_cost", "refused_cost"]) == "refused_cost"

    def test_all_failed_yields_failed(self):
        assert aggregate_outcome(["failed", "timed_out"]) == "failed"


class TestSummarizeRoutingDecision:
    def test_picks_first_attachment_doctype(self):
        decision = {
            "attachments": [
                {
                    "doctype_detected": "hu_invoice",
                    "doctype_confidence": 0.92,
                    "extraction_path": "invoice_processor",
                    "extraction_outcome": "succeeded",
                }
            ]
        }
        d, c, p, o = summarize_routing_decision(decision)
        assert d == "hu_invoice"
        assert c == pytest.approx(0.92)
        assert p == "invoice_processor"
        assert o == "success"

    def test_normalizes_rag_ingest_to_fallback(self):
        decision = {
            "attachments": [
                {
                    "doctype_detected": None,
                    "extraction_path": "rag_ingest",
                    "extraction_outcome": "succeeded",
                }
            ]
        }
        _d, _c, p, _o = summarize_routing_decision(decision)
        assert p == "rag_ingest_fallback"

    def test_empty_attachments_yields_skipped(self):
        d, c, p, o = summarize_routing_decision({"attachments": []})
        assert d is None
        assert c is None
        assert p == "skipped"
        assert o == "skipped"
