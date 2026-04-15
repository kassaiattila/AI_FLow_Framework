"""E2E placeholder — multi-source acceptance gate (Week 3 Day 14 / E3.3).

Un-skip when all 5 adapters + N4 association + upload-package endpoint land.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="Phase 1b implementation pending")


def test_all_sources_produce_valid_intake_package() -> None:
    """Parametrized: each of the 5 source types produces IntakePackage routed by PolicyEngine."""
    raise AssertionError("placeholder — implemented in S68/E3.3")


def test_n4_association_modes_roundtrip() -> None:
    """explicit / filename_match / order / single_description — each mode produces correct links."""
    raise AssertionError("placeholder — implemented in S68/E3.3")


def test_phase_1a_regression_unchanged() -> None:
    """Full 114-test Phase 1a regression still passes after Phase 1b lands."""
    raise AssertionError("placeholder — implemented in S68/E3.3")
