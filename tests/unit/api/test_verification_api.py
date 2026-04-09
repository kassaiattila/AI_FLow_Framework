"""
@test_registry:
    suite: api-unit
    component: api.verifications
    covers: [src/aiflow/api/v1/verifications.py]
    phase: B7
    priority: critical
    estimated_duration_ms: 500
    requires_services: [postgresql]
    tags: [api, verification, edits, crud]
"""

import uuid
from contextlib import asynccontextmanager  # noqa: F401 — used in _mock_pool
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from aiflow.security.auth import AuthProvider

# Create a SHARED auth provider — patch must be active when middleware initializes lazily
_shared_auth = AuthProvider.from_env()
_from_env_patcher = patch.object(AuthProvider, "from_env", return_value=_shared_auth)
_from_env_patcher.start()

from aiflow.api.app import create_app  # noqa: E402 — must come after auth patch

app = create_app()
_test_token = _shared_auth.create_token(user_id="test-user", role="admin")
_AUTH_HEADERS = {"Authorization": f"Bearer {_test_token}"}

client = TestClient(app, raise_server_exceptions=False)

# Warmup request triggers Starlette middleware build (which calls from_env)
client.get("/health/live")
# Now safe to remove the patch so it doesn't leak into other test modules
_from_env_patcher.stop()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DOC_ID = str(uuid.uuid4())
EDIT_ID = str(uuid.uuid4())
NOW = datetime.now(UTC)


def _make_row(**overrides):
    base = {
        "id": EDIT_ID,
        "document_id": DOC_ID,
        "field_name": "header.invoice_number",
        "field_category": "header",
        "original_value": "INV-001",
        "edited_value": "INV-0001",
        "confidence_score": 0.85,
        "editor_user_id": None,
        "status": "pending",
        "comment": None,
        "created_at": NOW,
        "updated_at": NOW,
    }
    base.update(overrides)
    return base


def _mock_record(data: dict):
    """Create mock asyncpg Record that supports both dict() and key access."""
    rec = MagicMock()
    rec.__getitem__ = lambda s, k: data[k]
    rec.get = lambda k, d=None: data.get(k, d)
    rec.keys.return_value = data.keys()
    rec.values.return_value = data.values()
    rec.items.return_value = data.items()
    return rec


def _mock_pool(fetch_rows=None, execute_result="UPDATE 0"):
    """Create a mock pool with proper async context manager for acquire()."""
    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=[_mock_record(r) for r in (fetch_rows or [])])
    conn.execute = AsyncMock(return_value=execute_result)

    pool = MagicMock()

    @asynccontextmanager
    async def _acquire():
        yield conn

    pool.acquire = _acquire
    return pool, conn


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSaveVerificationEdits:
    """POST /api/v1/documents/{id}/verifications"""

    @patch("aiflow.api.v1.verifications.get_pool")
    def test_save_edits_creates_records(self, mock_get_pool):
        pool, conn = _mock_pool()
        mock_get_pool.return_value = pool

        resp = client.post(
            f"/api/v1/documents/{DOC_ID}/verifications",
            headers=_AUTH_HEADERS,
            json={
                "edits": [
                    {
                        "field_name": "header.invoice_number",
                        "field_category": "header",
                        "original_value": "INV-001",
                        "edited_value": "INV-0001",
                        "confidence_score": 0.85,
                    },
                    {
                        "field_name": "totals.gross_total",
                        "field_category": "totals",
                        "original_value": "1000",
                        "edited_value": "1100",
                    },
                ],
            },
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert data["document_id"] == DOC_ID
        assert data["source"] == "backend"
        assert len(data["edits"]) == 2
        assert data["edits"][0]["field_name"] == "header.invoice_number"
        assert data["edits"][1]["field_name"] == "totals.gross_total"
        # Verify pending edits were deleted first (UPSERT logic)
        conn.execute.assert_any_await(
            "DELETE FROM verification_edits WHERE document_id = $1 AND status = 'pending'",
            DOC_ID,
        )

    @patch("aiflow.api.v1.verifications.get_pool")
    def test_save_edits_replaces_pending(self, mock_get_pool):
        """UPSERT: old pending edits are deleted before inserting new ones."""
        pool, conn = _mock_pool()
        mock_get_pool.return_value = pool

        resp = client.post(
            f"/api/v1/documents/{DOC_ID}/verifications",
            headers=_AUTH_HEADERS,
            json={"edits": [{"field_name": "vendor.name", "edited_value": "New"}]},
        )

        assert resp.status_code == 200
        # First call should be DELETE
        first_call_sql = conn.execute.call_args_list[0][0][0]
        assert "DELETE FROM verification_edits" in first_call_sql


class TestGetVerificationEdits:
    """GET /api/v1/documents/{id}/verifications"""

    @patch("aiflow.api.v1.verifications.get_pool")
    def test_get_edits_returns_all(self, mock_get_pool):
        rows = [_make_row(), _make_row(id=str(uuid.uuid4()), field_name="vendor.name")]
        pool, _ = _mock_pool(fetch_rows=rows)
        mock_get_pool.return_value = pool

        resp = client.get(f"/api/v1/documents/{DOC_ID}/verifications", headers=_AUTH_HEADERS)

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert data["document_id"] == DOC_ID

    @patch("aiflow.api.v1.verifications.get_pool")
    def test_get_edits_with_status_filter(self, mock_get_pool):
        pool, conn = _mock_pool(fetch_rows=[_make_row(status="approved")])
        mock_get_pool.return_value = pool

        resp = client.get(
            f"/api/v1/documents/{DOC_ID}/verifications?status=approved", headers=_AUTH_HEADERS
        )

        assert resp.status_code == 200
        # Verify query included status filter
        sql = conn.fetch.call_args[0][0]
        assert "status = $" in sql


class TestApproveVerificationEdits:
    """PATCH /api/v1/documents/{id}/verifications/approve"""

    @patch("aiflow.api.v1.verifications.get_pool")
    def test_approve_changes_status(self, mock_get_pool):
        pool, _ = _mock_pool(execute_result="UPDATE 3")
        mock_get_pool.return_value = pool

        resp = client.patch(
            f"/api/v1/documents/{DOC_ID}/verifications/approve",
            headers=_AUTH_HEADERS,
            json={"reviewer_id": "admin-user"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 3
        assert data["status"] == "approved"
        assert data["document_id"] == DOC_ID


class TestRejectVerificationEdits:
    """PATCH /api/v1/documents/{id}/verifications/reject"""

    @patch("aiflow.api.v1.verifications.get_pool")
    def test_reject_requires_comment(self, mock_get_pool):
        pool, _ = _mock_pool()
        mock_get_pool.return_value = pool

        # No comment → 422
        resp = client.patch(
            f"/api/v1/documents/{DOC_ID}/verifications/reject",
            headers=_AUTH_HEADERS,
            json={"reviewer_id": "admin"},
        )
        assert resp.status_code == 422

    @patch("aiflow.api.v1.verifications.get_pool")
    def test_reject_with_comment_succeeds(self, mock_get_pool):
        pool, _ = _mock_pool(execute_result="UPDATE 2")
        mock_get_pool.return_value = pool

        resp = client.patch(
            f"/api/v1/documents/{DOC_ID}/verifications/reject",
            headers=_AUTH_HEADERS,
            json={"reviewer_id": "admin", "comment": "Incorrect amounts"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 2
        assert data["status"] == "rejected"


class TestVerificationHistory:
    """GET /api/v1/verifications/history"""

    @patch("aiflow.api.v1.verifications.get_pool")
    def test_history_with_filters(self, mock_get_pool):
        rows = [_make_row(status="approved")]
        pool, conn = _mock_pool(fetch_rows=rows)
        mock_get_pool.return_value = pool

        resp = client.get(
            f"/api/v1/verifications/history?document_id={DOC_ID}&status=approved&limit=10",
            headers=_AUTH_HEADERS,
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        # Verify query included both filters
        sql = conn.fetch.call_args[0][0]
        assert "document_id = $" in sql
        assert "status = $" in sql
