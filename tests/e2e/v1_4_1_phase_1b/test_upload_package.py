"""E2E placeholder — POST /api/v1/intake/upload-package (Week 3 Day 13 / E3.2).

Un-skip when multipart upload-package endpoint lands.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="Phase 1b implementation pending")


def test_upload_package_multipart_creates_intake_package() -> None:
    """Multipart upload (N files + M descriptions + association_mode) → 201 + summary."""
    raise AssertionError("placeholder — implemented in S67/E3.2")


def test_upload_package_rejects_missing_tenant() -> None:
    """Missing tenant_id claim → 401, no package created."""
    raise AssertionError("placeholder — implemented in S67/E3.2")
