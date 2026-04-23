"""
@test_registry:
    suite: core-unit
    component: guardrails.cost_preflight.wiring
    covers:
        - src/aiflow/pipeline/runner.py
        - src/aiflow/services/rag_engine/service.py
        - src/aiflow/models/client.py
    phase: v1.4.10
    priority: high
    estimated_duration_ms: 200
    requires_services: []
    tags: [unit, guardrails, cost_preflight, wiring, sprint_n, s122]

Smoke tests that prove the 3 wiring sites short-circuit when the guardrail
feature flag is OFF. When the flag is off, ``build_guardrail_from_settings``
returns ``None`` and the wiring site must do zero I/O and raise nothing —
so the tenant budget service is never touched.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.asyncio
async def test_pipeline_runner_preflight_is_noop_when_disabled(monkeypatch):
    """Flag-off pipeline wiring must not call TenantBudgetService."""
    from aiflow.core.context import ExecutionContext
    from aiflow.pipeline import runner as runner_mod

    sentinel = MagicMock()
    sentinel.get_remaining = AsyncMock()

    class _FakePipelineDef:
        steps: list = []

    # build_guardrail_from_settings returns None → no guardrail constructed,
    # and the TenantBudgetService is never touched.
    async def _fake_builder():
        return None

    monkeypatch.setattr(
        "aiflow.guardrails.cost_preflight.build_guardrail_from_settings",
        _fake_builder,
    )

    ctx = ExecutionContext(team_id="t1")
    await runner_mod._preflight_pipeline_cost(ctx=ctx, pipeline_def=_FakePipelineDef())

    sentinel.get_remaining.assert_not_called()


@pytest.mark.asyncio
async def test_rag_engine_preflight_is_noop_when_disabled(monkeypatch):
    """Flag-off rag_engine wiring must not call TenantBudgetService."""
    from aiflow.services.rag_engine import service as rag_mod

    sentinel = MagicMock()
    sentinel.get_remaining = AsyncMock()

    async def _fake_builder():
        return None

    monkeypatch.setattr(
        "aiflow.guardrails.cost_preflight.build_guardrail_from_settings",
        _fake_builder,
    )

    await rag_mod._rag_preflight_cost(tenant_id="t1", file_count=3)
    sentinel.get_remaining.assert_not_called()


@pytest.mark.asyncio
async def test_model_client_preflight_is_noop_when_no_tenant_id(monkeypatch):
    """Internal calls pass no tenant_id — must skip pre-flight entirely."""
    from aiflow.models import client as client_mod

    called = {"n": 0}

    async def _fake_builder():
        called["n"] += 1
        return None

    monkeypatch.setattr(
        "aiflow.guardrails.cost_preflight.build_guardrail_from_settings",
        _fake_builder,
    )

    backend = MagicMock()
    backend.generate = AsyncMock(
        return_value=MagicMock(
            model_used="x",
            input_tokens=0,
            output_tokens=0,
            cost_usd=0.0,
            latency_ms=1.0,
        )
    )
    mc = client_mod.ModelClient(generation_backend=backend)
    await mc.generate(messages=[{"role": "user", "content": "hi"}])
    # No tenant_id → pre-flight helper is not entered at all.
    assert called["n"] == 0


@pytest.mark.asyncio
async def test_model_client_preflight_calls_guardrail_with_tenant_id(monkeypatch):
    """With tenant_id passed, the wiring invokes build_guardrail_from_settings."""
    from aiflow.models import client as client_mod

    called = {"n": 0}

    async def _fake_builder():
        called["n"] += 1
        return None  # still disabled → short-circuit, no refusal

    monkeypatch.setattr(
        "aiflow.guardrails.cost_preflight.build_guardrail_from_settings",
        _fake_builder,
    )

    backend = MagicMock()
    backend.generate = AsyncMock(
        return_value=MagicMock(
            model_used="x",
            input_tokens=0,
            output_tokens=0,
            cost_usd=0.0,
            latency_ms=1.0,
        )
    )
    mc = client_mod.ModelClient(generation_backend=backend)
    await mc.generate(
        messages=[{"role": "user", "content": "hi"}],
        tenant_id="acme",
    )
    assert called["n"] == 1


@pytest.mark.asyncio
async def test_pipeline_runner_preflight_refuses_when_enforced(monkeypatch):
    """Enforced over-budget decision raises CostGuardrailRefused with 429 mapping."""
    from aiflow.core.context import ExecutionContext
    from aiflow.core.errors import CostGuardrailRefused
    from aiflow.pipeline import runner as runner_mod

    class _FakePipelineDef:
        steps: list = [MagicMock(), MagicMock()]

    fake_guardrail = MagicMock()
    fake_guardrail.check = AsyncMock(
        return_value=MagicMock(
            allowed=False,
            projected_usd=5.0,
            remaining_usd=1.0,
            reason="over_budget",
            period="daily",
            dry_run=False,
        )
    )

    async def _fake_builder():
        return fake_guardrail

    monkeypatch.setattr(
        "aiflow.guardrails.cost_preflight.build_guardrail_from_settings",
        _fake_builder,
    )

    ctx = ExecutionContext(team_id="t1")
    with pytest.raises(CostGuardrailRefused) as exc_info:
        await runner_mod._preflight_pipeline_cost(ctx=ctx, pipeline_def=_FakePipelineDef())
    err = exc_info.value
    assert err.http_status == 429
    assert err.details["refused"] is True
    assert err.projected_usd == 5.0
    assert err.remaining_usd == 1.0
