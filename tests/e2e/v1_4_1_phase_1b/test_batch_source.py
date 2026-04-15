"""E2E placeholder — BatchSourceAdapter (Week 2 Day 7 / E2.2).

Un-skip when src/aiflow/sources/batch_adapter.py lands.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="Phase 1b implementation pending")


def test_batch_source_unpacks_zip_to_package() -> None:
    """ZIP archive with N files → 1 IntakePackage with N IntakeFile entries."""
    raise AssertionError("placeholder — implemented in S62/E2.2")


def test_batch_source_rejects_zip_bomb() -> None:
    """Archive with suspiciously high compression ratio is quarantined."""
    raise AssertionError("placeholder — implemented in S62/E2.2")
