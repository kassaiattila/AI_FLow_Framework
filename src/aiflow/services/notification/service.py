"""Multi-channel notification service (email SMTP, Slack webhook, generic webhook)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx
import structlog
from jinja2 import BaseLoader
from jinja2.sandbox import SandboxedEnvironment
from pydantic import BaseModel, Field
from sqlalchemy import text

from aiflow.services.base import BaseService, ServiceConfig

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

__all__ = [
    "ChannelType",
    "NotificationConfig",
    "NotificationService",
    "NotificationResult",
    "NotificationRequest",
    "ChannelConfig",
]

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class ChannelType(StrEnum):
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    IN_APP = "in_app"


class ChannelConfig(BaseModel):
    """Stored channel configuration."""

    id: str = ""
    name: str
    channel_type: ChannelType
    config: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True
    team_id: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class NotificationRequest(BaseModel):
    """Single notification to send."""

    channel: str  # channel type or config_name
    template: str  # Jinja2 template string or template name
    data: dict[str, Any] = Field(default_factory=dict)
    recipients: list[str] = Field(default_factory=list)
    config_name: str | None = None  # pre-configured channel name
    subject: str | None = None


class NotificationResult(BaseModel):
    """Result of a single send attempt."""

    channel: str
    sent: bool
    message_id: str | None = None
    recipient: str = ""
    error: str | None = None
    sent_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class NotificationConfig(ServiceConfig):
    """Notification service configuration."""

    template_dir: str = "prompts/notifications"
    default_from_email: str = "noreply@aiflow.local"
    http_timeout: float = 10.0


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class NotificationService(BaseService):
    """Multi-channel notification service with template support."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
        config: NotificationConfig | None = None,
    ) -> None:
        self._ext_config = config or NotificationConfig()
        self._session_factory = session_factory
        self._jinja_env = SandboxedEnvironment(loader=BaseLoader())
        super().__init__(self._ext_config)

    @property
    def service_name(self) -> str:
        return "notification"

    @property
    def service_description(self) -> str:
        return "Multi-channel notification service (email, Slack, webhook)"

    async def _start(self) -> None:
        template_dir = Path(self._ext_config.template_dir)
        if template_dir.exists():
            self._logger.info("template_dir_found", path=str(template_dir))

    async def _stop(self) -> None:
        pass

    async def health_check(self) -> bool:
        if self._session_factory is None:
            return True
        try:
            async with self._session_factory() as session:
                r = await session.execute(text("SELECT 1"))
                return r.scalar() == 1
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Send
    # ------------------------------------------------------------------

    async def send(
        self,
        channel: str,
        template: str,
        data: dict[str, Any],
        recipients: list[str],
        config_name: str | None = None,
        subject: str | None = None,
        pipeline_run_id: str | None = None,
    ) -> list[NotificationResult]:
        """Send notification to all recipients via specified channel.

        If *config_name* is given, channel config is loaded from DB.
        Otherwise, *channel* is treated as a ChannelType literal and
        the caller must pass connection details in *data* or the message
        is rendered from template only.
        """
        results: list[NotificationResult] = []

        # Resolve channel config from DB if config_name provided
        channel_cfg: dict[str, Any] = {}
        channel_id: str | None = None
        if config_name and self._session_factory:
            ch = await self._get_channel_by_name(config_name)
            if ch:
                channel_cfg = ch.get("config", {})
                channel = ch.get("channel_type", channel)
                channel_id = ch.get("id")

        # Render template
        rendered_body = self._render_template(template, data)
        rendered_subject = self._render_template(subject, data) if subject else None

        for recipient in recipients:
            result = await self._send_single(
                channel_type=channel,
                recipient=recipient,
                body=rendered_body,
                subject=rendered_subject,
                channel_cfg=channel_cfg,
                data=data,
            )
            results.append(result)

            # Log to DB
            if self._session_factory:
                await self._log_notification(
                    channel_id=channel_id,
                    channel_type=channel,
                    recipient=recipient,
                    template_name=template[:255] if len(template) > 50 else template,
                    subject=rendered_subject,
                    status="sent" if result.sent else "failed",
                    error=result.error,
                    pipeline_run_id=pipeline_run_id,
                )

        return results

    async def send_batch(
        self,
        notifications: list[NotificationRequest],
        pipeline_run_id: str | None = None,
    ) -> list[NotificationResult]:
        """Send multiple notifications."""
        all_results: list[NotificationResult] = []
        for req in notifications:
            results = await self.send(
                channel=req.channel,
                template=req.template,
                data=req.data,
                recipients=req.recipients,
                config_name=req.config_name,
                subject=req.subject,
                pipeline_run_id=pipeline_run_id,
            )
            all_results.extend(results)
        return all_results

    # ------------------------------------------------------------------
    # Channel CRUD
    # ------------------------------------------------------------------

    async def list_channels(self) -> list[ChannelConfig]:
        if self._session_factory is None:
            return []
        async with self._session_factory() as session:
            r = await session.execute(
                text(
                    "SELECT id, name, channel_type, config, enabled, team_id, "
                    "created_at, updated_at FROM notification_channels ORDER BY name"
                )
            )
            rows = r.fetchall()
        return [
            ChannelConfig(
                id=str(row[0]),
                name=row[1],
                channel_type=row[2],
                config=row[3] if row[3] else {},
                enabled=row[4],
                team_id=str(row[5]) if row[5] else None,
                created_at=str(row[6]) if row[6] else None,
                updated_at=str(row[7]) if row[7] else None,
            )
            for row in rows
        ]

    async def create_channel(self, config: ChannelConfig) -> ChannelConfig:
        if self._session_factory is None:
            raise RuntimeError("No session factory — cannot persist channel")
        import json

        async with self._session_factory() as session:
            r = await session.execute(
                text(
                    "INSERT INTO notification_channels "
                    "(name, channel_type, config, enabled, team_id) "
                    "VALUES (:name, :ch_type, :config::jsonb, "
                    ":enabled, :team_id) "
                    "RETURNING id, created_at, updated_at"
                ),
                {
                    "name": config.name,
                    "ch_type": config.channel_type.value
                    if isinstance(config.channel_type, ChannelType)
                    else config.channel_type,
                    "config": json.dumps(config.config),
                    "enabled": config.enabled,
                    "team_id": config.team_id,
                },
            )
            row = r.fetchone()
            await session.commit()

        config.id = str(row[0])  # type: ignore[index]
        config.created_at = str(row[1])  # type: ignore[index]
        config.updated_at = str(row[2])  # type: ignore[index]
        return config

    async def update_channel(self, channel_id: str, config: ChannelConfig) -> ChannelConfig:
        if self._session_factory is None:
            raise RuntimeError("No session factory — cannot persist channel")
        import json

        async with self._session_factory() as session:
            r = await session.execute(
                text(
                    "UPDATE notification_channels "
                    "SET name = :name, channel_type = :ch_type, config = :config::jsonb, "
                    "    enabled = :enabled, team_id = :team_id, updated_at = NOW() "
                    "WHERE id = :id "
                    "RETURNING id, created_at, updated_at"
                ),
                {
                    "id": channel_id,
                    "name": config.name,
                    "ch_type": config.channel_type.value
                    if isinstance(config.channel_type, ChannelType)
                    else config.channel_type,
                    "config": json.dumps(config.config),
                    "enabled": config.enabled,
                    "team_id": config.team_id,
                },
            )
            row = r.fetchone()
            await session.commit()

        if row is None:
            raise ValueError(f"Channel {channel_id} not found")
        config.id = str(row[0])
        config.created_at = str(row[1])
        config.updated_at = str(row[2])
        return config

    async def delete_channel(self, channel_id: str) -> bool:
        if self._session_factory is None:
            return False
        async with self._session_factory() as session:
            r = await session.execute(
                text("DELETE FROM notification_channels WHERE id = :id"),
                {"id": channel_id},
            )
            await session.commit()
            return r.rowcount > 0  # type: ignore[return-value]

    async def test_channel(self, channel_id: str) -> bool:
        """Send a test message through the channel to verify configuration."""
        ch = await self._get_channel_by_id(channel_id)
        if ch is None:
            return False

        result = await self._send_single(
            channel_type=ch["channel_type"],
            recipient=ch["config"].get("test_recipient", "test@aiflow.local"),
            body="AIFlow notification channel test message.",
            subject="AIFlow Test Notification",
            channel_cfg=ch["config"],
            data={},
        )
        return result.sent

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _send_single(
        self,
        channel_type: str,
        recipient: str,
        body: str,
        subject: str | None,
        channel_cfg: dict[str, Any],
        data: dict[str, Any],
    ) -> NotificationResult:
        """Dispatch to the appropriate channel sender."""
        try:
            if channel_type == ChannelType.EMAIL or channel_type == "email":
                return await self._send_email(recipient, subject or "", body, channel_cfg)
            elif channel_type == ChannelType.SLACK or channel_type == "slack":
                return await self._send_slack(recipient, body, channel_cfg)
            elif channel_type == ChannelType.WEBHOOK or channel_type == "webhook":
                return await self._send_webhook(recipient, body, subject, channel_cfg, data)
            elif channel_type == ChannelType.IN_APP or channel_type == "in_app":
                return await self._send_in_app(recipient, body, subject, data)
            else:
                return NotificationResult(
                    channel=channel_type,
                    sent=False,
                    recipient=recipient,
                    error=f"Unknown channel type: {channel_type}",
                )
        except Exception as exc:
            self._logger.error(
                "send_failed",
                channel=channel_type,
                recipient=recipient,
                error=str(exc),
            )
            return NotificationResult(
                channel=channel_type,
                sent=False,
                recipient=recipient,
                error=str(exc),
            )

    async def _send_email(
        self,
        recipient: str,
        subject: str,
        body: str,
        cfg: dict[str, Any],
    ) -> NotificationResult:
        """Send email via aiosmtplib."""
        from email.message import EmailMessage

        import aiosmtplib

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = cfg.get("from_email", self._ext_config.default_from_email)
        msg["To"] = recipient
        msg.set_content(body)

        host = cfg.get("smtp_host", "localhost")
        port = cfg.get("smtp_port", 587)
        username = cfg.get("smtp_username")
        password = cfg.get("smtp_password")
        use_tls = cfg.get("smtp_use_tls", True)

        await aiosmtplib.send(
            msg,
            hostname=host,
            port=port,
            username=username,
            password=password,
            start_tls=use_tls,
        )

        msg_id = str(uuid.uuid4())
        self._logger.info("email_sent", recipient=recipient, subject=subject)
        return NotificationResult(
            channel="email",
            sent=True,
            message_id=msg_id,
            recipient=recipient,
        )

    async def _send_slack(
        self,
        channel_or_url: str,
        body: str,
        cfg: dict[str, Any],
    ) -> NotificationResult:
        """Send Slack message via incoming webhook."""
        webhook_url = cfg.get("webhook_url", channel_or_url)
        if not webhook_url.startswith("http"):
            return NotificationResult(
                channel="slack",
                sent=False,
                recipient=channel_or_url,
                error="No valid webhook URL",
            )

        async with httpx.AsyncClient(timeout=self._ext_config.http_timeout) as client:
            resp = await client.post(
                webhook_url,
                json={"text": body},
            )
            resp.raise_for_status()

        self._logger.info("slack_sent", channel=channel_or_url)
        return NotificationResult(
            channel="slack",
            sent=True,
            message_id=str(uuid.uuid4()),
            recipient=channel_or_url,
        )

    async def _send_webhook(
        self,
        url: str,
        body: str,
        subject: str | None,
        cfg: dict[str, Any],
        data: dict[str, Any],
    ) -> NotificationResult:
        """Send generic webhook (HTTP POST)."""
        target_url = cfg.get("url", url)
        headers = dict(cfg.get("headers", {}))
        auth_type = cfg.get("auth_type")

        if auth_type == "bearer":
            headers["Authorization"] = f"Bearer {cfg.get('token', '')}"
        elif auth_type == "basic":
            import base64

            creds = base64.b64encode(
                f"{cfg.get('username', '')}:{cfg.get('password', '')}".encode()
            ).decode()
            headers["Authorization"] = f"Basic {creds}"

        payload = {
            "subject": subject,
            "body": body,
            "data": data,
        }

        async with httpx.AsyncClient(timeout=self._ext_config.http_timeout) as client:
            resp = await client.post(target_url, json=payload, headers=headers)
            resp.raise_for_status()

        self._logger.info("webhook_sent", url=target_url)
        return NotificationResult(
            channel="webhook",
            sent=True,
            message_id=str(uuid.uuid4()),
            recipient=url,
        )

    async def _send_in_app(
        self,
        user_id: str,
        body: str,
        subject: str | None,
        data: dict[str, Any],
    ) -> NotificationResult:
        """Insert in-app notification into DB."""
        if self._session_factory is None:
            return NotificationResult(
                channel="in_app",
                sent=False,
                recipient=user_id,
                error="No session factory for in-app notifications",
            )

        async with self._session_factory() as session:
            await session.execute(
                text(
                    "INSERT INTO in_app_notifications (user_id, title, body, link) "
                    "VALUES (:uid, :title, :body, :link)"
                ),
                {
                    "uid": user_id,
                    "title": subject or "Notification",
                    "body": body,
                    "link": data.get("link"),
                },
            )
            await session.commit()

        return NotificationResult(
            channel="in_app",
            sent=True,
            message_id=str(uuid.uuid4()),
            recipient=user_id,
        )

    def _render_template(self, template: str, data: dict[str, Any]) -> str:
        """Render a Jinja2 template string with data."""
        try:
            tmpl = self._jinja_env.from_string(template)
            return tmpl.render(**data)
        except Exception:
            return template

    async def _get_channel_by_name(self, name: str) -> dict[str, Any] | None:
        if self._session_factory is None:
            return None
        async with self._session_factory() as session:
            r = await session.execute(
                text(
                    "SELECT id, name, channel_type, config, enabled "
                    "FROM notification_channels WHERE name = :name AND enabled = true"
                ),
                {"name": name},
            )
            row = r.fetchone()
        if row is None:
            return None
        return {
            "id": str(row[0]),
            "name": row[1],
            "channel_type": row[2],
            "config": row[3] if row[3] else {},
            "enabled": row[4],
        }

    async def _get_channel_by_id(self, channel_id: str) -> dict[str, Any] | None:
        if self._session_factory is None:
            return None
        async with self._session_factory() as session:
            r = await session.execute(
                text(
                    "SELECT id, name, channel_type, config, enabled "
                    "FROM notification_channels WHERE id = :id"
                ),
                {"id": channel_id},
            )
            row = r.fetchone()
        if row is None:
            return None
        return {
            "id": str(row[0]),
            "name": row[1],
            "channel_type": row[2],
            "config": row[3] if row[3] else {},
            "enabled": row[4],
        }

    async def _log_notification(
        self,
        channel_id: str | None,
        channel_type: str,
        recipient: str,
        template_name: str | None,
        subject: str | None,
        status: str,
        error: str | None,
        pipeline_run_id: str | None,
    ) -> None:
        """Write a row to notification_log."""
        try:
            async with self._session_factory() as session:  # type: ignore[union-attr]
                await session.execute(
                    text(
                        "INSERT INTO notification_log "
                        "(channel_id, channel_type, recipient, template_name, subject, "
                        " status, error, pipeline_run_id) "
                        "VALUES (:ch_id, :ch_type, :recipient, :tmpl, :subj, "
                        " :status, :error, :pr_id)"
                    ),
                    {
                        "ch_id": channel_id,
                        "ch_type": channel_type
                        if isinstance(channel_type, str)
                        else channel_type.value,
                        "recipient": recipient,
                        "tmpl": template_name,
                        "subj": subject,
                        "status": status,
                        "error": error,
                        "pr_id": pipeline_run_id,
                    },
                )
                await session.commit()
        except Exception as exc:
            self._logger.warning("notification_log_failed", error=str(exc))
