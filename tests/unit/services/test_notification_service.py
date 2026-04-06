"""
@test_registry:
    suite: service-unit
    component: services.notification
    covers: [src/aiflow/services/notification/service.py]
    phase: B2.1
    priority: critical
    estimated_duration_ms: 500
    requires_services: []
    tags: [service, notification, email, slack, webhook]
"""

from __future__ import annotations

# Ensure aiosmtplib is importable for patching (lazy import in service)
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aiflow.services.notification.service import (
    ChannelConfig,
    ChannelType,
    NotificationConfig,
    NotificationRequest,
    NotificationResult,
    NotificationService,
)

_aiosmtplib = MagicMock()
_aiosmtplib.send = AsyncMock()


@pytest.fixture()
def svc() -> NotificationService:
    """Service without DB (unit test mode)."""
    return NotificationService(session_factory=None, config=NotificationConfig())


class TestNotificationService:
    @pytest.mark.asyncio
    async def test_send_email_template(self, svc: NotificationService) -> None:
        """send() renders template and dispatches to email channel."""
        mock_result = NotificationResult(
            channel="email", sent=True, message_id="msg-1", recipient="test@example.com"
        )
        with patch.object(svc, "_send_single", new_callable=AsyncMock, return_value=mock_result):
            results = await svc.send(
                channel="email",
                template="Hello {{ name }}!",
                data={"name": "User"},
                recipients=["test@example.com"],
                subject="Test",
            )
        assert len(results) == 1
        assert isinstance(results[0], NotificationResult)
        assert results[0].sent is True
        assert results[0].channel == "email"

    @pytest.mark.asyncio
    async def test_send_batch(self, svc: NotificationService) -> None:
        """send_batch processes multiple notifications."""
        mock_result = NotificationResult(
            channel="email", sent=True, message_id="msg-1", recipient="x@example.com"
        )
        with patch.object(svc, "_send_single", new_callable=AsyncMock, return_value=mock_result):
            notifications = [
                NotificationRequest(
                    channel="email",
                    template="Hi {{ name }}",
                    data={"name": "A"},
                    recipients=["a@example.com"],
                    subject="Batch 1",
                ),
                NotificationRequest(
                    channel="email",
                    template="Hi {{ name }}",
                    data={"name": "B"},
                    recipients=["b@example.com"],
                    subject="Batch 2",
                ),
            ]
            results = await svc.send_batch(notifications)
        assert len(results) == 2
        assert all(r.sent is True for r in results)

    @pytest.mark.asyncio
    async def test_list_channels_no_db(self, svc: NotificationService) -> None:
        """list_channels returns empty list when no session factory."""
        channels = await svc.list_channels()
        assert channels == []

    @pytest.mark.asyncio
    async def test_create_channel_requires_db(self, svc: NotificationService) -> None:
        """create_channel raises RuntimeError without session factory."""
        cfg = ChannelConfig(name="test", channel_type=ChannelType.EMAIL)
        with pytest.raises(RuntimeError, match="No session factory"):
            await svc.create_channel(cfg)

    @pytest.mark.asyncio
    async def test_delete_channel_no_db(self, svc: NotificationService) -> None:
        """delete_channel returns False without session factory."""
        result = await svc.delete_channel("nonexistent")
        assert result is False
