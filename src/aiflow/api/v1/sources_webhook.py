"""Webhook intake router — wires ``ApiSourceAdapter`` to HTTP.

Source: 01_PLAN/session_S55_v1_4_1_phase_1b_sources_kickoff.md Day 9 (E2.3-B),
        101_AIFLOW_v2_COMPONENT_TRANSFORMATION_PLAN.md R1.

Endpoint: ``POST /api/v1/sources/webhook``.

The caller signs ``<timestamp>.<base64(body)>`` with a shared HMAC-SHA256 secret
and submits the raw body plus ``X-Webhook-Signature`` / ``X-Webhook-Timestamp``
/ ``X-Filename`` headers; ``Idempotency-Key`` is optional. The adapter does all
security checks — this router only translates ``SourceAdapterError`` messages
to HTTP status codes and exposes the contract in OpenAPI.

Auth note: HMAC verification replaces bearer/API-key auth on this path, so the
router is registered under ``_PUBLIC_PREFIXES`` in ``aiflow.api.middleware``.
The HMAC secret is loaded at adapter-construction time from
``AIFLOW_WEBHOOK_HMAC_SECRET`` and never appears in responses or log fields.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated

import asyncpg
import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field

from aiflow.api.deps import get_pool
from aiflow.sources.api_adapter import ApiSourceAdapter
from aiflow.sources.exceptions import SourceAdapterError
from aiflow.sources.sink import IntakePackageSink
from aiflow.state.repositories.intake import IntakeRepository

__all__ = [
    "router",
    "get_api_source_adapter",
    "get_intake_package_sink",
    "reset_api_source_adapter",
]


async def get_intake_package_sink() -> IntakePackageSink:
    """FastAPI dependency returning a sink bound to the shared asyncpg pool.

    Override via ``app.dependency_overrides[get_intake_package_sink]`` in tests
    so each test can supply its own pool / repo (or a fake sink).
    """
    pool: asyncpg.Pool = await get_pool()
    return IntakePackageSink(repo=IntakeRepository(pool))


logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/sources", tags=["sources"])


class WebhookAcceptedResponse(BaseModel):
    """Returned on successful enqueue."""

    package_id: str = Field(..., description="UUID of the accepted IntakePackage")
    status: str = Field("accepted", description="Always ``accepted`` on 202")


class WebhookErrorResponse(BaseModel):
    """Error envelope for 4xx responses."""

    detail: str = Field(..., description="Human-readable error reason (no secrets)")


_adapter_singleton: ApiSourceAdapter | None = None


def _load_adapter_from_env() -> ApiSourceAdapter:
    """Build the singleton from environment variables.

    Required: ``AIFLOW_WEBHOOK_HMAC_SECRET``. Optional overrides mirror the
    adapter kwargs (storage_root, tenant_id, max_package_bytes, max_clock_skew).
    """
    secret = os.getenv("AIFLOW_WEBHOOK_HMAC_SECRET", "")
    if not secret:
        raise RuntimeError(
            "AIFLOW_WEBHOOK_HMAC_SECRET env var is required to serve "
            "/api/v1/sources/webhook. Set it or override the adapter via "
            "FastAPI dependency_overrides in tests."
        )
    storage_root = Path(os.getenv("AIFLOW_WEBHOOK_STORAGE_ROOT", "./var/intake/webhook"))
    tenant_id = os.getenv("AIFLOW_WEBHOOK_TENANT_ID", "default")
    max_bytes_env = os.getenv("AIFLOW_WEBHOOK_MAX_BYTES", "").strip()
    max_package_bytes = int(max_bytes_env) if max_bytes_env else None
    max_skew = int(os.getenv("AIFLOW_WEBHOOK_MAX_CLOCK_SKEW_SECONDS", "300"))
    return ApiSourceAdapter(
        storage_root=storage_root,
        tenant_id=tenant_id,
        hmac_secret=secret,
        max_clock_skew_seconds=max_skew,
        max_package_bytes=max_package_bytes,
    )


def get_api_source_adapter() -> ApiSourceAdapter:
    """FastAPI dependency returning the module-level adapter singleton.

    Override via ``app.dependency_overrides[get_api_source_adapter]`` in tests
    so each test can supply its own secret / storage_root / clock.
    """
    global _adapter_singleton
    if _adapter_singleton is None:
        _adapter_singleton = _load_adapter_from_env()
    return _adapter_singleton


def reset_api_source_adapter() -> None:
    """Drop the cached singleton; next call to the dependency rebuilds it."""
    global _adapter_singleton
    _adapter_singleton = None


def _status_for(message: str) -> int:
    """Map a ``SourceAdapterError`` message to an HTTP status code.

    Ordering matters — more specific phrases first, because the adapter
    sometimes embeds the idempotency key or filename into the message.
    """
    msg = message.lower()
    if "duplicate idempotency_key" in msg:
        return 409
    if "exceeds max_package_bytes" in msg:
        return 413
    if "invalid timestamp" in msg or msg.startswith("missing timestamp"):
        return 400
    if (
        msg.startswith("missing signature")
        or msg.startswith("invalid hmac")
        or "replay window" in msg
    ):
        return 401
    return 400


_RESPONSES: dict[int | str, dict[str, object]] = {
    201: {
        "description": "Webhook accepted and persisted as IntakePackage.",
        "model": WebhookAcceptedResponse,
    },
    400: {
        "description": "Malformed request (missing filename, bad timestamp).",
        "model": WebhookErrorResponse,
    },
    401: {
        "description": "HMAC signature missing, invalid, or outside replay window.",
        "model": WebhookErrorResponse,
    },
    409: {
        "description": "Idempotency-Key already seen — request is a duplicate.",
        "model": WebhookErrorResponse,
    },
    413: {
        "description": "Payload exceeds the adapter's max_package_bytes cap.",
        "model": WebhookErrorResponse,
    },
}


@router.post(
    "/webhook",
    status_code=201,
    response_model=WebhookAcceptedResponse,
    responses=_RESPONSES,
    summary="Accept an HMAC-signed webhook upload",
    description=(
        "Raw bytes body is signed as ``<timestamp>.<base64(body)>`` with "
        "HMAC-SHA256. Caller must send ``X-Webhook-Signature`` (hex), "
        "``X-Webhook-Timestamp`` (unix seconds), and ``X-Filename``. "
        "Optional ``Idempotency-Key`` guards against duplicate delivery. "
        "The body MUST NOT be parsed as JSON by intermediaries — the "
        "signature covers the exact bytes submitted."
    ),
)
async def accept_webhook(
    request: Request,
    x_filename: Annotated[
        str,
        Header(
            alias="X-Filename",
            description="Upload filename (required).",
            min_length=1,
        ),
    ],
    adapter: Annotated[ApiSourceAdapter, Depends(get_api_source_adapter)],
    sink: Annotated[IntakePackageSink, Depends(get_intake_package_sink)],
    x_webhook_signature: Annotated[
        str | None,
        Header(
            alias="X-Webhook-Signature",
            description="Hex-encoded HMAC-SHA256 over ``<timestamp>.<base64(body)>``.",
        ),
    ] = None,
    x_webhook_timestamp: Annotated[
        str | None,
        Header(
            alias="X-Webhook-Timestamp",
            description="Unix epoch seconds when the signature was computed.",
        ),
    ] = None,
    idempotency_key: Annotated[
        str | None,
        Header(
            alias="Idempotency-Key",
            description="Optional caller-chosen de-duplication token.",
        ),
    ] = None,
    content_type: Annotated[
        str | None,
        Header(alias="Content-Type", description="MIME type of the body."),
    ] = None,
) -> WebhookAcceptedResponse:
    payload = await request.body()

    try:
        pkg = adapter.enqueue(
            payload=payload,
            filename=x_filename,
            signature=x_webhook_signature or "",
            timestamp=x_webhook_timestamp or "",
            idempotency_key=idempotency_key,
            mime_type=content_type,
        )
    except SourceAdapterError as exc:
        status = _status_for(str(exc))
        logger.info(
            "webhook_rejected",
            status=status,
            reason=str(exc),
            size_bytes=len(payload),
            has_idempotency_key=idempotency_key is not None,
        )
        raise HTTPException(status_code=status, detail=str(exc)) from None
    except ValueError as exc:
        logger.info("webhook_bad_request", reason=str(exc), size_bytes=len(payload))
        raise HTTPException(status_code=400, detail=str(exc)) from None

    # Phase 1d: persist via the canonical sink so the webhook is durable
    # (not just queued in the adapter's in-memory deque). Sink emits the
    # `source.package_persisted` event for free.
    await sink.handle(pkg)
    logger.info(
        "webhook_persisted",
        package_id=str(pkg.package_id),
        size_bytes=len(payload),
        has_idempotency_key=idempotency_key is not None,
    )

    return WebhookAcceptedResponse(package_id=str(pkg.package_id), status="accepted")
