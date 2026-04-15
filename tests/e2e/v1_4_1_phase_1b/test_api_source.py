"""E2E placeholder — ApiSourceAdapter (Week 2 Day 8-9 / E2.3).

Un-skip when src/aiflow/sources/api_adapter.py + POST /api/v1/sources/webhook land.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="Phase 1b implementation pending")


def test_api_source_webhook_accepts_signed_payload() -> None:
    """POST with valid HMAC signature → 202 + intake_package_id."""
    raise AssertionError("placeholder — implemented in S63/E2.3")


def test_api_source_webhook_rejects_bad_signature() -> None:
    """POST with tampered signature → 401, no package created."""
    raise AssertionError("placeholder — implemented in S63/E2.3")
