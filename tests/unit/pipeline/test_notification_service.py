"""
@test_registry:
    suite: service-unit
    component: services.notification
    covers: [src/aiflow/services/notification/service.py]
    phase: C7
    priority: critical
    estimated_duration_ms: 600
    requires_services: []
    tags: [service, notification, template, channel]
"""

from __future__ import annotations

from typing import Any

import pytest

from aiflow.services.notification.service import (
    ChannelConfig,
    ChannelType,
    NotificationConfig,
    NotificationRequest,
    NotificationResult,
    NotificationService,
)


@pytest.fixture()
def svc() -> NotificationService:
    """Service without DB (unit test mode)."""
    return NotificationService(session_factory=None, config=NotificationConfig())


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


class TestModels:
    def test_channel_type_values(self) -> None:
        assert ChannelType.EMAIL.value == "email"
        assert ChannelType.SLACK.value == "slack"
        assert ChannelType.WEBHOOK.value == "webhook"
        assert ChannelType.IN_APP.value == "in_app"

    def test_channel_config_defaults(self) -> None:
        cfg = ChannelConfig(name="test", channel_type=ChannelType.EMAIL)
        assert cfg.enabled is True
        assert cfg.config == {}
        assert cfg.team_id is None

    def test_notification_request(self) -> None:
        req = NotificationRequest(
            channel="email",
            template="Hello {{ name }}",
            data={"name": "World"},
            recipients=["a@b.com"],
            subject="Test",
        )
        assert req.channel == "email"
        assert len(req.recipients) == 1

    def test_notification_result_defaults(self) -> None:
        r = NotificationResult(channel="email", sent=True, recipient="a@b.com")
        assert r.sent is True
        assert r.error is None
        assert r.sent_at is not None

    def test_notification_config_defaults(self) -> None:
        cfg = NotificationConfig()
        assert cfg.template_dir == "prompts/notifications"
        assert cfg.default_from_email == "noreply@aiflow.local"
        assert cfg.http_timeout == 10.0


# ---------------------------------------------------------------------------
# Service lifecycle
# ---------------------------------------------------------------------------


class TestServiceLifecycle:
    def test_service_name(self, svc: NotificationService) -> None:
        assert svc.service_name == "notification"

    def test_service_description(self, svc: NotificationService) -> None:
        assert "notification" in svc.service_description.lower()

    @pytest.mark.asyncio
    async def test_start_stop(self, svc: NotificationService) -> None:
        await svc.start()
        assert svc.status.value == "running"
        await svc.stop()
        assert svc.status.value == "stopped"

    @pytest.mark.asyncio
    async def test_health_check_no_db(self, svc: NotificationService) -> None:
        result = await svc.health_check()
        assert result is True  # No DB = trivially healthy


# ---------------------------------------------------------------------------
# Template rendering
# ---------------------------------------------------------------------------


class TestTemplateRendering:
    def test_simple_render(self, svc: NotificationService) -> None:
        result = svc._render_template("Hello {{ name }}!", {"name": "World"})
        assert result == "Hello World!"

    def test_render_with_loop(self, svc: NotificationService) -> None:
        tmpl = "{% for i in items %}{{ i }},{% endfor %}"
        result = svc._render_template(tmpl, {"items": ["a", "b", "c"]})
        assert result == "a,b,c,"

    def test_render_with_condition(self, svc: NotificationService) -> None:
        tmpl = "{% if count > 0 %}Has items{% else %}Empty{% endif %}"
        assert svc._render_template(tmpl, {"count": 5}) == "Has items"
        assert svc._render_template(tmpl, {"count": 0}) == "Empty"

    def test_render_missing_var_graceful(self, svc: NotificationService) -> None:
        result = svc._render_template("Hello {{ name }}", {})
        assert result == "Hello "

    def test_render_plain_text_passthrough(self, svc: NotificationService) -> None:
        result = svc._render_template("No templates here.", {})
        assert result == "No templates here."

    def test_render_invalid_template_returns_raw(self, svc: NotificationService) -> None:
        result = svc._render_template("{{ broken }", {})
        # Should return raw template on error
        assert "broken" in result


# ---------------------------------------------------------------------------
# Send dispatch (no DB, tests channel routing)
# ---------------------------------------------------------------------------


class TestSendDispatch:
    @pytest.mark.asyncio
    async def test_unknown_channel_returns_error(self, svc: NotificationService) -> None:
        result = await svc._send_single(
            channel_type="carrier_pigeon",
            recipient="bird@sky.com",
            body="Coo coo",
            subject="Test",
            channel_cfg={},
            data={},
        )
        assert result.sent is False
        assert "Unknown channel type" in (result.error or "")

    @pytest.mark.asyncio
    async def test_slack_no_url_fails(self, svc: NotificationService) -> None:
        result = await svc._send_single(
            channel_type="slack",
            recipient="not-a-url",
            body="Test",
            subject=None,
            channel_cfg={},
            data={},
        )
        assert result.sent is False
        assert "webhook URL" in (result.error or "")

    @pytest.mark.asyncio
    async def test_in_app_no_db_fails(self, svc: NotificationService) -> None:
        result = await svc._send_single(
            channel_type="in_app",
            recipient="user-uuid",
            body="Test notification",
            subject="Hello",
            channel_cfg={},
            data={},
        )
        assert result.sent is False
        assert "session factory" in (result.error or "")


# ---------------------------------------------------------------------------
# Channel CRUD (no DB)
# ---------------------------------------------------------------------------


class TestChannelCrudNoDB:
    @pytest.mark.asyncio
    async def test_list_channels_empty(self, svc: NotificationService) -> None:
        channels = await svc.list_channels()
        assert channels == []

    @pytest.mark.asyncio
    async def test_create_channel_raises_without_db(self, svc: NotificationService) -> None:
        cfg = ChannelConfig(name="test", channel_type=ChannelType.EMAIL)
        with pytest.raises(RuntimeError, match="session factory"):
            await svc.create_channel(cfg)

    @pytest.mark.asyncio
    async def test_delete_channel_returns_false(self, svc: NotificationService) -> None:
        result = await svc.delete_channel("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_test_channel_returns_false(self, svc: NotificationService) -> None:
        result = await svc.test_channel("nonexistent")
        assert result is False


# ---------------------------------------------------------------------------
# Batch send
# ---------------------------------------------------------------------------


class TestBatchSend:
    @pytest.mark.asyncio
    async def test_empty_batch(self, svc: NotificationService) -> None:
        results = await svc.send_batch([])
        assert results == []
