"""
@test_registry:
    suite: service-unit
    component: services.email_connector
    covers: [src/aiflow/services/email_connector/service.py]
    phase: B2.1
    priority: high
    estimated_duration_ms: 400
    requires_services: []
    tags: [service, email-connector, imap, postgresql]
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from aiflow.services.email_connector.service import (
    EmailConnectorConfig,
    EmailConnectorService,
)


def _make_config_row():
    """Mock SQLAlchemy result row as a tuple."""
    now = datetime.now(UTC)
    return (
        "cfg-001",  # id
        "Test IMAP",  # name
        "imap",  # provider
        "imap.example.com",  # host
        993,  # port
        True,  # use_ssl
        "INBOX",  # mailbox
        None,  # credentials_encrypted
        "{}",  # filters
        15,  # polling_interval_minutes
        50,  # max_emails_per_fetch
        True,  # is_active
        None,  # last_fetched_at
        now,  # created_at
        now,  # updated_at
    )


@pytest.fixture()
def mock_session_factory():
    """Mock SQLAlchemy async session factory."""
    session = AsyncMock()
    factory = MagicMock()

    # factory() -> context manager -> session
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=False)
    factory.return_value = ctx

    return factory, session


@pytest.fixture()
def svc(mock_session_factory) -> EmailConnectorService:
    factory, _session = mock_session_factory
    return EmailConnectorService(session_factory=factory, config=EmailConnectorConfig())


class TestEmailConnectorService:
    @pytest.mark.asyncio
    async def test_create_config(self, svc: EmailConnectorService, mock_session_factory) -> None:
        """create_config inserts and returns config dict."""
        _factory, session = mock_session_factory

        # First call: INSERT RETURNING id
        insert_result = MagicMock()
        insert_result.fetchone.return_value = ("cfg-new",)

        # Second call: SELECT for get_config
        select_result = MagicMock()
        select_result.fetchone.return_value = _make_config_row()

        session.execute = AsyncMock(side_effect=[insert_result, select_result])
        session.commit = AsyncMock()

        config = await svc.create_config(
            name="Test IMAP",
            provider="imap",
            host="imap.example.com",
            port=993,
        )
        assert config is not None
        assert config["name"] == "Test IMAP"

    @pytest.mark.asyncio
    async def test_list_configs(self, svc: EmailConnectorService, mock_session_factory) -> None:
        """list_configs returns list of config dicts."""
        _factory, session = mock_session_factory
        result = MagicMock()
        result.fetchall.return_value = [_make_config_row(), _make_config_row()]
        session.execute = AsyncMock(return_value=result)

        configs = await svc.list_configs()
        assert len(configs) == 2
        assert configs[0]["provider"] == "imap"

    @pytest.mark.asyncio
    async def test_get_config(self, svc: EmailConnectorService, mock_session_factory) -> None:
        """get_config returns config dict for existing ID."""
        _factory, session = mock_session_factory
        result = MagicMock()
        result.fetchone.return_value = _make_config_row()
        session.execute = AsyncMock(return_value=result)

        config = await svc.get_config("cfg-001")
        assert config is not None
        assert config["id"] == "cfg-001"

    @pytest.mark.asyncio
    async def test_update_config(self, svc: EmailConnectorService, mock_session_factory) -> None:
        """update_config modifies and returns updated config."""
        _factory, session = mock_session_factory

        # First call: UPDATE
        update_result = MagicMock()
        update_result.rowcount = 1
        session.commit = AsyncMock()

        # Second call: get_config SELECT
        select_result = MagicMock()
        select_result.fetchone.return_value = _make_config_row()

        session.execute = AsyncMock(side_effect=[update_result, select_result])

        config = await svc.update_config("cfg-001", name="Updated IMAP")
        assert config is not None

    @pytest.mark.asyncio
    async def test_delete_config(self, svc: EmailConnectorService, mock_session_factory) -> None:
        """delete_config returns True when row is deleted."""
        _factory, session = mock_session_factory
        result = MagicMock()
        result.rowcount = 1
        session.execute = AsyncMock(return_value=result)
        session.commit = AsyncMock()

        deleted = await svc.delete_config("cfg-001")
        assert deleted is True
