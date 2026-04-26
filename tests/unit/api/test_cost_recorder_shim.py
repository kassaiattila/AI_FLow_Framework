"""
@test_registry:
    suite: api-unit
    component: api.cost_recorder (Sprint U S154 thin shim)
    covers:
        - src/aiflow/api/cost_recorder.py
        - src/aiflow/state/cost_repository.py (insert_attribution boundary)
    phase: v1.5.4
    priority: high
    estimated_duration_ms: 80
    requires_services: []
    tags: [unit, api, cost, sprint_u, s154, sn_fu]
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aiflow.api.cost_recorder import record_cost
from aiflow.contracts.cost_attribution import CostAttribution


class TestRecordCostShim:
    """Sprint U S154 — record_cost is now a thin shim over CostAttributionRepository."""

    @pytest.mark.asyncio
    async def test_record_cost_routes_through_repository(self):
        """record_cost(...) builds a CostAttribution and calls
        CostAttributionRepository.insert_attribution(...)."""
        captured: dict[str, CostAttribution] = {}

        async def fake_insert(attribution: CostAttribution) -> None:
            captured["arg"] = attribution

        with (
            patch("aiflow.api.cost_recorder.get_pool", new=AsyncMock(return_value=MagicMock())),
            patch("aiflow.api.cost_recorder.CostAttributionRepository") as repo_cls,
        ):
            repo_cls.return_value.insert_attribution = fake_insert

            await record_cost(
                workflow_run_id=uuid.uuid4(),
                step_name="extract_invoice",
                model="openai/gpt-4o-mini",
                input_tokens=1000,
                output_tokens=200,
                cost_usd=0.0042,
                team_id="tenant-acme",
            )

        attr = captured["arg"]
        assert isinstance(attr, CostAttribution)
        assert attr.skill == "extract_invoice"
        assert attr.model == "openai/gpt-4o-mini"
        assert attr.provider == "openai"
        assert attr.tenant_id == "tenant-acme"
        assert attr.input_tokens == 1000
        assert attr.output_tokens == 200
        assert attr.cost_usd == pytest.approx(0.0042)

    @pytest.mark.asyncio
    async def test_record_cost_maps_team_id_to_tenant_id(self):
        """team_id="acme" -> CostAttribution.tenant_id="acme" (string cast)."""
        captured: dict[str, CostAttribution] = {}

        async def fake_insert(attribution: CostAttribution) -> None:
            captured["arg"] = attribution

        with (
            patch("aiflow.api.cost_recorder.get_pool", new=AsyncMock(return_value=MagicMock())),
            patch("aiflow.api.cost_recorder.CostAttributionRepository") as repo_cls,
        ):
            repo_cls.return_value.insert_attribution = fake_insert

            await record_cost(
                step_name="x",
                model="openai/gpt-4o-mini",
                input_tokens=10,
                output_tokens=5,
                cost_usd=0.0001,
                team_id="acme",
            )

        assert captured["arg"].tenant_id == "acme"

    @pytest.mark.asyncio
    async def test_record_cost_defaults_tenant_when_team_id_none(self):
        """team_id=None -> CostAttribution.tenant_id='default' (avoids min_length trip)."""
        captured: dict[str, CostAttribution] = {}

        async def fake_insert(attribution: CostAttribution) -> None:
            captured["arg"] = attribution

        with (
            patch("aiflow.api.cost_recorder.get_pool", new=AsyncMock(return_value=MagicMock())),
            patch("aiflow.api.cost_recorder.CostAttributionRepository") as repo_cls,
        ):
            repo_cls.return_value.insert_attribution = fake_insert

            await record_cost(
                step_name="x",
                model="openai/gpt-4o-mini",
                input_tokens=10,
                output_tokens=5,
                cost_usd=0.0001,
                team_id=None,
            )

        assert captured["arg"].tenant_id == "default"

    @pytest.mark.asyncio
    async def test_record_cost_handles_uuid_workflow_run_id(self):
        """workflow_run_id as UUID is passed through string-cast to run_id."""
        captured: dict[str, CostAttribution] = {}

        async def fake_insert(attribution: CostAttribution) -> None:
            captured["arg"] = attribution

        run_uuid = uuid.uuid4()

        with (
            patch("aiflow.api.cost_recorder.get_pool", new=AsyncMock(return_value=MagicMock())),
            patch("aiflow.api.cost_recorder.CostAttributionRepository") as repo_cls,
        ):
            repo_cls.return_value.insert_attribution = fake_insert

            await record_cost(
                workflow_run_id=run_uuid,
                step_name="x",
                model="openai/gpt-4o-mini",
                input_tokens=10,
                output_tokens=5,
                cost_usd=0.0001,
                team_id="t1",
            )

        assert captured["arg"].run_id == str(run_uuid)

    @pytest.mark.asyncio
    async def test_record_cost_swallows_exceptions(self):
        """Best-effort contract: any exception logs a warning, never raises."""
        with (
            patch(
                "aiflow.api.cost_recorder.get_pool",
                new=AsyncMock(side_effect=RuntimeError("pool unavailable")),
            ),
        ):
            # Must not raise
            await record_cost(
                step_name="x",
                model="openai/gpt-4o-mini",
                input_tokens=10,
                output_tokens=5,
                cost_usd=0.0001,
                team_id="t1",
            )

    @pytest.mark.asyncio
    async def test_record_cost_extracts_provider_from_model(self):
        """provider is parsed as the prefix before '/' in the model string."""
        captured: dict[str, CostAttribution] = {}

        async def fake_insert(attribution: CostAttribution) -> None:
            captured["arg"] = attribution

        with (
            patch("aiflow.api.cost_recorder.get_pool", new=AsyncMock(return_value=MagicMock())),
            patch("aiflow.api.cost_recorder.CostAttributionRepository") as repo_cls,
        ):
            repo_cls.return_value.insert_attribution = fake_insert

            await record_cost(
                step_name="x",
                model="anthropic/claude-3-haiku",
                input_tokens=10,
                output_tokens=5,
                cost_usd=0.0001,
                team_id="t1",
            )
        assert captured["arg"].provider == "anthropic"

        captured.clear()
        with (
            patch("aiflow.api.cost_recorder.get_pool", new=AsyncMock(return_value=MagicMock())),
            patch("aiflow.api.cost_recorder.CostAttributionRepository") as repo_cls,
        ):
            repo_cls.return_value.insert_attribution = fake_insert

            await record_cost(
                step_name="x",
                model="bare-model-no-slash",  # no slash
                input_tokens=10,
                output_tokens=5,
                cost_usd=0.0001,
                team_id="t1",
            )
        assert captured["arg"].provider == "unknown"
