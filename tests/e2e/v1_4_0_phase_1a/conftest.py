"""Shared fixtures for Phase 1a E2E acceptance tests.

@test_registry
suite: phase_1a_e2e
tags: [e2e, phase_1a, intake, policy, provider, skill_instance, compat]
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    """Absolute path to the YAML fixtures directory."""
    return FIXTURES_DIR


@pytest.fixture
def profile_a_path() -> Path:
    return FIXTURES_DIR / "sample_policy_a.yaml"


@pytest.fixture
def profile_b_path() -> Path:
    return FIXTURES_DIR / "sample_policy_b.yaml"


@pytest.fixture
def legacy_pipeline_path() -> Path:
    return FIXTURES_DIR / "sample_legacy_pipeline.yaml"


@pytest.fixture
def test_tenant_id() -> str:
    return "phase_1a_test_tenant"


@pytest.fixture
def mock_pool() -> tuple[MagicMock, AsyncMock]:
    """Create a mock asyncpg Pool with async connection + transaction context.

    Matches the pattern used in tests/unit/intake/test_repository.py so that
    repository methods can be exercised without a live PostgreSQL instance.
    """
    pool = MagicMock()
    conn = AsyncMock()

    tx = MagicMock()
    tx.__aenter__ = AsyncMock(return_value=tx)
    tx.__aexit__ = AsyncMock(return_value=False)
    conn.transaction = MagicMock(return_value=tx)

    acq = MagicMock()
    acq.__aenter__ = AsyncMock(return_value=conn)
    acq.__aexit__ = AsyncMock(return_value=False)
    pool.acquire = MagicMock(return_value=acq)

    return pool, conn
