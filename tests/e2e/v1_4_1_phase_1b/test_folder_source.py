"""E2E placeholder — FolderSourceAdapter (Week 2 Day 6 / E2.1).

Un-skip when src/aiflow/sources/folder_adapter.py lands.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="Phase 1b implementation pending")


def test_folder_source_detects_new_file() -> None:
    """Drop file into watched directory → IntakePackage emitted after debounce window."""
    raise AssertionError("placeholder — implemented in S61/E2.1")


def test_folder_source_ignores_mid_write_file() -> None:
    """File with changing mtime is skipped until stable."""
    raise AssertionError("placeholder — implemented in S61/E2.1")
