"""E2E placeholder — FileSourceAdapter (Week 1 Day 4 / E1.2).

Un-skip when src/aiflow/sources/file_adapter.py lands.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="Phase 1b implementation pending")


def test_file_source_happy_path() -> None:
    """Single-file upload → IntakePackage with exactly 1 IntakeFile → routed by PolicyEngine."""
    raise AssertionError("placeholder — implemented in S59/E1.2")


def test_file_source_reject_unsupported_mime() -> None:
    """Unsupported MIME type → package rejected before policy resolution."""
    raise AssertionError("placeholder — implemented in S59/E1.2")
