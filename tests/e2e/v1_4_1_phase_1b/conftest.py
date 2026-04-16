"""Shared fixtures for Phase 1b source-adapter E2E tests.

@test_registry
suite: phase_1b_e2e
tags: [e2e, phase_1b, intake, source_adapter, conftest]

Design notes (CLAUDE.md / feedback_asyncpg_pool_event_loop.md):
- asyncpg pools are event-loop-bound. Use `aiflow.api.deps.get_pool()` —
  a single module-level pool wired to pytest-asyncio's session loop.
- Fresh `SourceAdapterRegistry` per test to keep registration isolated.
- `phase_1b_storage_root` is a per-session tmp directory — Week 1 Day 2+
  file/folder adapters will materialize IntakeFile bytes under it.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from aiflow.api.deps import get_pool
from aiflow.policy.engine import PolicyEngine
from aiflow.sources import SourceAdapterRegistry
from aiflow.state.repositories.intake import IntakeRepository

if TYPE_CHECKING:
    import asyncpg

REPO_ROOT = Path(__file__).resolve().parents[3]
PROFILE_A_PATH = REPO_ROOT / "config" / "profiles" / "profile_a.yaml"


@pytest.fixture
def phase_1b_tenant_id() -> str:
    """Stable tenant id used across Phase 1b E2E tests."""
    return "tenant-phase-1b"


@pytest.fixture(scope="session")
def phase_1b_storage_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Per-session scratch directory for file/folder adapter payloads."""
    root = tmp_path_factory.mktemp("phase_1b_storage")
    (root / "inbox").mkdir(parents=True, exist_ok=True)
    (root / "uploads").mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture
async def phase_1b_db_pool() -> asyncpg.Pool:
    """Shared asyncpg pool — loop-safe via aiflow.api.deps.get_pool()."""
    return await get_pool()


@pytest.fixture
async def phase_1b_intake_repository(
    phase_1b_db_pool: asyncpg.Pool,
) -> IntakeRepository:
    """IntakeRepository bound to the shared pool."""
    return IntakeRepository(phase_1b_db_pool)


@pytest.fixture
def phase_1b_policy_engine() -> PolicyEngine:
    """PolicyEngine loaded from profile_a (Phase 1b default)."""
    return PolicyEngine.from_yaml(PROFILE_A_PATH)


@pytest.fixture
def phase_1b_source_registry() -> SourceAdapterRegistry:
    """Fresh registry per test — no cross-test adapter leakage."""
    return SourceAdapterRegistry()
