"""Shared fixtures for Phase 1b source-adapter E2E tests.

Fixtures are intentionally minimal placeholders — Week 1 Day 1 (S56 / E0.2)
will populate them with real tenant / storage / IntakeRepository wiring.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def phase_1b_tenant_id() -> str:
    """Stable tenant id used across Phase 1b E2E tests."""
    return "tenant-phase-1b"
