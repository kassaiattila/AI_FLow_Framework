"""Notifications API — send, channel CRUD, test, log."""

from __future__ import annotations

import json as json_mod
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from aiflow.api.deps import get_pool, get_session_factory

__all__ = ["router"]

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class SendRequest(BaseModel):
    channel: str = Field(..., description="Channel type: email, slack, webhook, in_app")
    template: str = Field(..., description="Jinja2 template or template name")
    data: dict[str, Any] = Field(default_factory=dict)
    recipients: list[str] = Field(..., min_length=1)
    config_name: str | None = None
    subject: str | None = None


class SendResultItem(BaseModel):
    channel: str
    sent: bool
    message_id: str | None = None
    recipient: str = ""
    error: str | None = None


class SendResponse(BaseModel):
    sent_count: int
    failed_count: int
    results: list[SendResultItem]
    source: str = "backend"


class ChannelItem(BaseModel):
    id: str
    name: str
    channel_type: str
    config: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True
    team_id: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class ChannelListResponse(BaseModel):
    channels: list[ChannelItem]
    total: int
    source: str = "backend"


class ChannelCreateRequest(BaseModel):
    name: str
    channel_type: str
    config: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True
    team_id: str | None = None


class ChannelCreateResponse(BaseModel):
    id: str
    name: str
    channel_type: str
    source: str = "backend"


class ChannelTestResponse(BaseModel):
    success: bool
    message: str
    source: str = "backend"


class LogItem(BaseModel):
    id: str
    channel_type: str
    recipient: str
    template_name: str | None = None
    subject: str | None = None
    status: str
    error: str | None = None
    sent_at: str | None = None


class LogListResponse(BaseModel):
    log: list[LogItem]
    total: int
    source: str = "backend"


class InAppItem(BaseModel):
    id: str
    user_id: str
    title: str
    body: str | None = None
    link: str | None = None
    read: bool = False
    created_at: str | None = None


class InAppListResponse(BaseModel):
    notifications: list[InAppItem]
    total: int
    source: str = "backend"


class UnreadCountResponse(BaseModel):
    count: int
    source: str = "backend"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/send", response_model=SendResponse, status_code=200)
async def send_notification(req: SendRequest) -> SendResponse:
    """Send a notification to one or more recipients."""
    from aiflow.services.notification.service import (
        NotificationConfig,
        NotificationService,
    )

    sf = await get_session_factory()
    svc = NotificationService(session_factory=sf, config=NotificationConfig())
    await svc.start()

    results = await svc.send(
        channel=req.channel,
        template=req.template,
        data=req.data,
        recipients=req.recipients,
        config_name=req.config_name,
        subject=req.subject,
    )

    items = [
        SendResultItem(
            channel=r.channel,
            sent=r.sent,
            message_id=r.message_id,
            recipient=r.recipient,
            error=r.error,
        )
        for r in results
    ]
    sent = sum(1 for r in results if r.sent)
    failed = sum(1 for r in results if not r.sent)
    return SendResponse(sent_count=sent, failed_count=failed, results=items)


@router.get("/channels", response_model=ChannelListResponse)
async def list_channels() -> ChannelListResponse:
    """List all notification channels."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, name, channel_type, config, enabled, team_id, "
            "created_at, updated_at FROM notification_channels ORDER BY name"
        )
    channels = []
    for r in rows:
        cfg = r["config"]
        if isinstance(cfg, str):
            cfg = json_mod.loads(cfg)
        channels.append(
            ChannelItem(
                id=str(r["id"]),
                name=r["name"],
                channel_type=r["channel_type"],
                config=cfg if cfg else {},
                enabled=r["enabled"],
                team_id=str(r["team_id"]) if r["team_id"] else None,
                created_at=str(r["created_at"]) if r["created_at"] else None,
                updated_at=str(r["updated_at"]) if r["updated_at"] else None,
            )
        )
    return ChannelListResponse(channels=channels, total=len(channels))


@router.post("/channels", response_model=ChannelCreateResponse, status_code=201)
async def create_channel(req: ChannelCreateRequest) -> ChannelCreateResponse:
    """Create a new notification channel."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        try:
            row = await conn.fetchrow(
                "INSERT INTO notification_channels (name, channel_type, config, enabled, team_id) "
                "VALUES ($1, $2, $3::jsonb, $4, $5) RETURNING id",
                req.name,
                req.channel_type,
                json_mod.dumps(req.config),
                req.enabled,
                req.team_id,
            )
        except Exception as exc:
            if "unique" in str(exc).lower() or "duplicate" in str(exc).lower():
                raise HTTPException(
                    status_code=409,
                    detail=f"Channel '{req.name}' already exists",
                ) from exc
            raise

    return ChannelCreateResponse(
        id=str(row["id"]),  # type: ignore[index]
        name=req.name,
        channel_type=req.channel_type,
    )


@router.delete("/channels/{channel_id}")
async def delete_channel(channel_id: str) -> dict[str, Any]:
    """Delete a notification channel."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        r = await conn.execute("DELETE FROM notification_channels WHERE id = $1", channel_id)
    if r == "DELETE 0":
        raise HTTPException(status_code=404, detail="Channel not found")
    return {"deleted": True, "id": channel_id, "source": "backend"}


@router.post(
    "/channels/{channel_id}/test",
    response_model=ChannelTestResponse,
)
async def test_channel(channel_id: str) -> ChannelTestResponse:
    """Test a notification channel by sending a test message."""
    from aiflow.services.notification.service import (
        NotificationConfig,
        NotificationService,
    )

    sf = await get_session_factory()
    svc = NotificationService(session_factory=sf, config=NotificationConfig())
    await svc.start()

    success = await svc.test_channel(channel_id)
    return ChannelTestResponse(
        success=success,
        message="Test sent successfully" if success else "Test failed — check channel config",
    )


@router.get("/log", response_model=LogListResponse)
async def list_notification_log(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    status: str | None = Query(None),
) -> LogListResponse:
    """List notification log entries."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        where = ""
        args: list[Any] = []
        idx = 1
        if status:
            where = f"WHERE status = ${idx}"
            args.append(status)
            idx += 1

        total = await conn.fetchval(f"SELECT COUNT(*) FROM notification_log {where}", *args)

        args_q = list(args)
        args_q.append(limit)
        args_q.append(offset)
        rows = await conn.fetch(
            f"SELECT id, channel_type, recipient, template_name, subject, "
            f"status, error, sent_at FROM notification_log {where} "
            f"ORDER BY sent_at DESC LIMIT ${idx} OFFSET ${idx + 1}",
            *args_q,
        )

    items = [
        LogItem(
            id=str(r["id"]),
            channel_type=r["channel_type"],
            recipient=r["recipient"],
            template_name=r["template_name"],
            subject=r["subject"],
            status=r["status"],
            error=r["error"],
            sent_at=str(r["sent_at"]) if r["sent_at"] else None,
        )
        for r in rows
    ]
    return LogListResponse(log=items, total=total)


# ---------------------------------------------------------------------------
# In-app notifications
# ---------------------------------------------------------------------------


@router.get("/in-app", response_model=InAppListResponse)
async def list_in_app(
    user_id: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> InAppListResponse:
    """List in-app notifications, unread first."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        where = ""
        args: list[Any] = []
        idx = 1
        if user_id:
            where = f"WHERE user_id = ${idx}::uuid"
            args.append(user_id)
            idx += 1

        total = await conn.fetchval(f"SELECT COUNT(*) FROM in_app_notifications {where}", *args)

        args_q = list(args)
        args_q.append(limit)
        args_q.append(offset)
        rows = await conn.fetch(
            f"SELECT id, user_id, title, body, link, read, created_at "
            f"FROM in_app_notifications {where} "
            f"ORDER BY read ASC, created_at DESC "
            f"LIMIT ${idx} OFFSET ${idx + 1}",
            *args_q,
        )

    items = [
        InAppItem(
            id=str(r["id"]),
            user_id=str(r["user_id"]),
            title=r["title"],
            body=r["body"],
            link=r["link"],
            read=r["read"],
            created_at=str(r["created_at"]) if r["created_at"] else None,
        )
        for r in rows
    ]
    return InAppListResponse(notifications=items, total=total or 0)


@router.get("/in-app/unread-count", response_model=UnreadCountResponse)
async def unread_count(
    user_id: str | None = Query(None),
) -> UnreadCountResponse:
    """Get count of unread in-app notifications."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        if user_id:
            cnt = await conn.fetchval(
                "SELECT COUNT(*) FROM in_app_notifications "
                "WHERE user_id = $1::uuid AND read = false",
                user_id,
            )
        else:
            cnt = await conn.fetchval(
                "SELECT COUNT(*) FROM in_app_notifications WHERE read = false"
            )
    return UnreadCountResponse(count=cnt or 0)


@router.post("/in-app/{notification_id}/read")
async def mark_read(notification_id: str) -> dict[str, Any]:
    """Mark a single in-app notification as read."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        r = await conn.execute(
            "UPDATE in_app_notifications SET read = true WHERE id = $1::uuid",
            notification_id,
        )
    if r == "UPDATE 0":
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"read": True, "id": notification_id, "source": "backend"}


@router.post("/in-app/read-all")
async def mark_all_read(
    user_id: str | None = Query(None),
) -> dict[str, Any]:
    """Mark all in-app notifications as read."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        if user_id:
            r = await conn.execute(
                "UPDATE in_app_notifications SET read = true "
                "WHERE user_id = $1::uuid AND read = false",
                user_id,
            )
        else:
            r = await conn.execute("UPDATE in_app_notifications SET read = true WHERE read = false")
    count = int(r.split()[-1]) if r else 0
    return {"marked_read": count, "source": "backend"}
