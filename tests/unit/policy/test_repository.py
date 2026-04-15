"""Unit tests for PolicyOverrideRepository + PolicyEngine.from_yaml_with_db.

Session: S48 (D0.5) — Alembic 033 policy_overrides + PolicyEngine DB
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from aiflow.policy.engine import PolicyEngine
from aiflow.policy.repository import PolicyOverrideRepository, _parse_jsonb

PROFILES_DIR = Path(__file__).resolve().parents[3] / "config" / "profiles"


# ---------------------------------------------------------------------------
# Mock pool helper (same pattern as test_repository.py for intake)
# ---------------------------------------------------------------------------


def _mock_pool() -> tuple[MagicMock, AsyncMock]:
    """Create a mock asyncpg pool with nested connection context manager."""
    pool = MagicMock()
    conn = AsyncMock()

    acq = MagicMock()
    acq.__aenter__ = AsyncMock(return_value=conn)
    acq.__aexit__ = AsyncMock(return_value=False)
    pool.acquire = MagicMock(return_value=acq)

    return pool, conn


# ---------------------------------------------------------------------------
# _parse_jsonb tests
# ---------------------------------------------------------------------------


class TestParseJsonb:
    def test_none_returns_empty_dict(self) -> None:
        assert _parse_jsonb(None) == {}

    def test_dict_passthrough(self) -> None:
        d = {"cloud_ai_allowed": True}
        assert _parse_jsonb(d) is d

    def test_json_string_parsed(self) -> None:
        assert _parse_jsonb('{"cloud_ai_allowed": true}') == {"cloud_ai_allowed": True}

    def test_empty_string_object(self) -> None:
        assert _parse_jsonb("{}") == {}


# ---------------------------------------------------------------------------
# get_overrides_for_tenant tests
# ---------------------------------------------------------------------------


class TestGetOverridesForTenant:
    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self) -> None:
        pool, conn = _mock_pool()
        conn.fetchrow.return_value = None
        repo = PolicyOverrideRepository(pool)

        result = await repo.get_overrides_for_tenant("unknown_tenant")

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_parsed_policy_json(self) -> None:
        pool, conn = _mock_pool()
        conn.fetchrow.return_value = {
            "policy_json": {"cloud_ai_allowed": True, "daily_document_cap": 1000},
        }
        repo = PolicyOverrideRepository(pool)

        result = await repo.get_overrides_for_tenant("acme")

        assert result == {"cloud_ai_allowed": True, "daily_document_cap": 1000}

    @pytest.mark.asyncio
    async def test_query_filters_instance_id_null(self) -> None:
        pool, conn = _mock_pool()
        conn.fetchrow.return_value = None
        repo = PolicyOverrideRepository(pool)

        await repo.get_overrides_for_tenant("t1")

        sql = conn.fetchrow.call_args.args[0]
        assert "instance_id IS NULL" in sql
        assert conn.fetchrow.call_args.args[1] == "t1"


# ---------------------------------------------------------------------------
# get_overrides_for_instance tests
# ---------------------------------------------------------------------------


class TestGetOverridesForInstance:
    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self) -> None:
        pool, conn = _mock_pool()
        conn.fetchrow.return_value = None
        repo = PolicyOverrideRepository(pool)

        result = await repo.get_overrides_for_instance("t1", "inst_1")

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_parsed_policy_json(self) -> None:
        pool, conn = _mock_pool()
        conn.fetchrow.return_value = {
            "policy_json": {"azure_di_enabled": True},
        }
        repo = PolicyOverrideRepository(pool)

        result = await repo.get_overrides_for_instance("t1", "inst_1")

        assert result == {"azure_di_enabled": True}

    @pytest.mark.asyncio
    async def test_query_passes_both_ids(self) -> None:
        pool, conn = _mock_pool()
        conn.fetchrow.return_value = None
        repo = PolicyOverrideRepository(pool)

        await repo.get_overrides_for_instance("t1", "inst_1")

        args = conn.fetchrow.call_args.args
        assert args[1] == "t1"
        assert args[2] == "inst_1"


# ---------------------------------------------------------------------------
# upsert_override tests
# ---------------------------------------------------------------------------


class TestUpsertOverride:
    @pytest.mark.asyncio
    async def test_upsert_returns_uuid(self) -> None:
        pool, conn = _mock_pool()
        expected_id = uuid4()
        conn.fetchval.return_value = expected_id
        repo = PolicyOverrideRepository(pool)

        result = await repo.upsert_override("t1", {"cloud_ai_allowed": True})

        assert result == expected_id

    @pytest.mark.asyncio
    async def test_upsert_passes_json_serialized(self) -> None:
        pool, conn = _mock_pool()
        conn.fetchval.return_value = uuid4()
        repo = PolicyOverrideRepository(pool)

        policy = {"cloud_ai_allowed": True, "daily_document_cap": 500}
        await repo.upsert_override("t1", policy)

        args = conn.fetchval.call_args.args
        assert args[1] == "t1"
        assert args[2] is None  # instance_id
        assert json.loads(args[3]) == policy

    @pytest.mark.asyncio
    async def test_upsert_with_instance_id(self) -> None:
        pool, conn = _mock_pool()
        conn.fetchval.return_value = uuid4()
        repo = PolicyOverrideRepository(pool)

        await repo.upsert_override("t1", {"azure_di_enabled": True}, instance_id="inst_1")

        args = conn.fetchval.call_args.args
        assert args[1] == "t1"
        assert args[2] == "inst_1"

    @pytest.mark.asyncio
    async def test_upsert_sql_has_on_conflict(self) -> None:
        pool, conn = _mock_pool()
        conn.fetchval.return_value = uuid4()
        repo = PolicyOverrideRepository(pool)

        await repo.upsert_override("t1", {"x": 1})

        sql = conn.fetchval.call_args.args[0]
        assert "ON CONFLICT" in sql
        assert "DO UPDATE" in sql


# ---------------------------------------------------------------------------
# delete_override tests
# ---------------------------------------------------------------------------


class TestDeleteOverride:
    @pytest.mark.asyncio
    async def test_delete_returns_true_when_row_deleted(self) -> None:
        pool, conn = _mock_pool()
        conn.execute.return_value = "DELETE 1"
        repo = PolicyOverrideRepository(pool)

        result = await repo.delete_override("t1")

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_returns_false_when_no_row(self) -> None:
        pool, conn = _mock_pool()
        conn.execute.return_value = "DELETE 0"
        repo = PolicyOverrideRepository(pool)

        result = await repo.delete_override("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_tenant_only_filters_null_instance(self) -> None:
        pool, conn = _mock_pool()
        conn.execute.return_value = "DELETE 1"
        repo = PolicyOverrideRepository(pool)

        await repo.delete_override("t1")

        sql = conn.execute.call_args.args[0]
        assert "instance_id IS NULL" in sql

    @pytest.mark.asyncio
    async def test_delete_with_instance_id(self) -> None:
        pool, conn = _mock_pool()
        conn.execute.return_value = "DELETE 1"
        repo = PolicyOverrideRepository(pool)

        await repo.delete_override("t1", instance_id="inst_1")

        args = conn.execute.call_args.args
        assert "instance_id = $2" in args[0]
        assert args[1] == "t1"
        assert args[2] == "inst_1"


# ---------------------------------------------------------------------------
# get_all_tenant_overrides tests
# ---------------------------------------------------------------------------


class TestGetAllTenantOverrides:
    @pytest.mark.asyncio
    async def test_empty_returns_empty_dict(self) -> None:
        pool, conn = _mock_pool()
        conn.fetch.return_value = []
        repo = PolicyOverrideRepository(pool)

        result = await repo.get_all_tenant_overrides()

        assert result == {}

    @pytest.mark.asyncio
    async def test_returns_tenant_keyed_dict(self) -> None:
        pool, conn = _mock_pool()
        conn.fetch.return_value = [
            {"tenant_id": "t1", "policy_json": {"cloud_ai_allowed": True}},
            {"tenant_id": "t2", "policy_json": {"azure_di_enabled": True}},
        ]
        repo = PolicyOverrideRepository(pool)

        result = await repo.get_all_tenant_overrides()

        assert result == {
            "t1": {"cloud_ai_allowed": True},
            "t2": {"azure_di_enabled": True},
        }

    @pytest.mark.asyncio
    async def test_query_filters_instance_id_null(self) -> None:
        pool, conn = _mock_pool()
        conn.fetch.return_value = []
        repo = PolicyOverrideRepository(pool)

        await repo.get_all_tenant_overrides()

        sql = conn.fetch.call_args.args[0]
        assert "instance_id IS NULL" in sql


# ---------------------------------------------------------------------------
# PolicyEngine.from_yaml_with_db tests
# ---------------------------------------------------------------------------


class TestFromYamlWithDb:
    @pytest.mark.asyncio
    async def test_loads_profile_and_overrides(self) -> None:
        pool, conn = _mock_pool()
        conn.fetch.return_value = [
            {"tenant_id": "acme", "policy_json": {"cloud_ai_allowed": True}},
        ]

        engine = await PolicyEngine.from_yaml_with_db(
            PROFILES_DIR / "profile_a.yaml",
            pool,
        )

        assert engine.profile_config.cloud_ai_allowed is False
        assert engine.tenant_overrides == {"acme": {"cloud_ai_allowed": True}}

        merged = engine.get_for_tenant("acme")
        assert merged.cloud_ai_allowed is True

    @pytest.mark.asyncio
    async def test_no_db_overrides_uses_yaml_only(self) -> None:
        pool, conn = _mock_pool()
        conn.fetch.return_value = []

        engine = await PolicyEngine.from_yaml_with_db(
            PROFILES_DIR / "profile_a.yaml",
            pool,
        )

        assert engine.tenant_overrides == {}
        assert engine.profile_config.cloud_ai_allowed is False

    @pytest.mark.asyncio
    async def test_backward_compat_from_yaml_unchanged(self) -> None:
        """from_yaml() still works without DB — backward compatibility."""
        engine = PolicyEngine.from_yaml(PROFILES_DIR / "profile_a.yaml")

        assert isinstance(engine, PolicyEngine)
        assert engine.tenant_overrides == {}
        assert engine.profile_config.cloud_ai_allowed is False

    @pytest.mark.asyncio
    async def test_multiple_tenant_overrides_from_db(self) -> None:
        pool, conn = _mock_pool()
        conn.fetch.return_value = [
            {"tenant_id": "t1", "policy_json": {"cloud_ai_allowed": True}},
            {
                "tenant_id": "t2",
                "policy_json": {"azure_di_enabled": True, "daily_document_cap": 200},
            },
        ]

        engine = await PolicyEngine.from_yaml_with_db(
            PROFILES_DIR / "profile_a.yaml",
            pool,
        )

        assert len(engine.tenant_overrides) == 2

        t1_cfg = engine.get_for_tenant("t1")
        assert t1_cfg.cloud_ai_allowed is True
        assert t1_cfg.azure_di_enabled is False

        t2_cfg = engine.get_for_tenant("t2")
        assert t2_cfg.azure_di_enabled is True
        assert t2_cfg.daily_document_cap == 200
