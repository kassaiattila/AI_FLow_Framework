"""
@test_registry:
    suite: service-unit
    component: services.audit
    covers: [src/aiflow/services/audit/service.py]
    phase: B2.1
    priority: critical
    estimated_duration_ms: 400
    requires_services: []
    tags: [service, audit, postgresql, immutable]
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from aiflow.services.audit.service import AuditEntry, AuditTrailService


def _make_row(
    action: str = "create",
    resource_type: str = "document",
    resource_id: str | None = "doc-1",
    user_id=None,
    details: str | None = None,
    ip_address: str | None = None,
) -> dict:
    """Create a mock DB row dict."""
    return {
        "id": uuid.uuid4(),
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "user_id": user_id,
        "details": details,
        "ip_address": ip_address,
        "timestamp": datetime.now(UTC),
    }


@pytest.fixture()
def svc(mock_pool) -> AuditTrailService:
    pool, _conn = mock_pool
    service = AuditTrailService()
    service._pool = pool
    return service


class TestAuditTrailService:
    @pytest.mark.asyncio
    async def test_log_creates_entry(self, svc: AuditTrailService, mock_pool) -> None:
        """log() creates an audit entry and returns AuditEntry."""
        _pool, conn = mock_pool
        row = _make_row(action="create", resource_type="document")
        conn.fetchrow = AsyncMock(return_value=row)

        entry = await svc.log(action="create", entity_type="document", entity_id="doc-1")
        assert isinstance(entry, AuditEntry)
        assert entry.action == "create"
        assert entry.entity_type == "document"
        conn.fetchrow.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_list_entries_filter(self, svc: AuditTrailService, mock_pool) -> None:
        """list_entries with filter returns matching entries."""
        _pool, conn = mock_pool
        rows = [
            _make_row(action="create", resource_type="document"),
            _make_row(action="create", resource_type="document"),
        ]
        conn.fetch = AsyncMock(return_value=rows)

        entries = await svc.list_entries(action="create", entity_type="document")
        assert len(entries) == 2
        assert all(e.action == "create" for e in entries)

    @pytest.mark.asyncio
    async def test_get_entry_by_id(self, svc: AuditTrailService, mock_pool) -> None:
        """get_entry returns AuditEntry for existing ID."""
        _pool, conn = mock_pool
        entry_id = str(uuid.uuid4())
        row = _make_row()
        conn.fetchrow = AsyncMock(return_value=row)

        entry = await svc.get_entry(entry_id)
        assert entry is not None
        assert isinstance(entry, AuditEntry)

    @pytest.mark.asyncio
    async def test_get_entry_not_found(self, svc: AuditTrailService, mock_pool) -> None:
        """get_entry returns None for non-existent ID."""
        _pool, conn = mock_pool
        conn.fetchrow = AsyncMock(return_value=None)

        entry = await svc.get_entry(str(uuid.uuid4()))
        assert entry is None

    @pytest.mark.asyncio
    async def test_log_immutable(self, svc: AuditTrailService, mock_pool) -> None:
        """AuditEntry is a frozen-like record — no update method exposed."""
        _pool, conn = mock_pool
        row = _make_row(action="delete", resource_type="user")
        conn.fetchrow = AsyncMock(return_value=row)

        entry = await svc.log(action="delete", entity_type="user")
        # AuditTrailService exposes no update/delete methods
        assert not hasattr(svc, "update_entry")
        assert not hasattr(svc, "delete_entry")
        assert entry.action == "delete"
