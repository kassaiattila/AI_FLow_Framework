"""E2E placeholder — EmailSourceAdapter (Week 1 Day 2-3 / E1.1).

Un-skip when src/aiflow/sources/email_adapter.py lands.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="Phase 1b implementation pending")


def test_email_source_happy_path() -> None:
    """IMAP backend fetch → IntakePackage persisted → acknowledged."""
    raise AssertionError("placeholder — implemented in S57/E1.1")


def test_email_source_reject_oversize_attachment() -> None:
    """Attachment >max_package_bytes rejected with reason='size_guard'."""
    raise AssertionError("placeholder — implemented in S57/E1.1")
