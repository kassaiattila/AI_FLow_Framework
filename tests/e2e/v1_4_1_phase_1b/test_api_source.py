"""E2E — ApiSourceAdapter (Phase 1b Week 2 Day 10 / E2.4).

@test_registry
suite: phase_1b_e2e
tags: [e2e, phase_1b, intake, source_adapter, api_push]

Exercises the adapter directly — NOT the FastAPI router (that lives in
``tests/integration/sources/test_webhook_router.py``). The envelope is signed
with the real production algorithm (HMAC-SHA256 over ``timestamp.base64(body)``)
and payloads are written to a real tmp storage_root.

DB persistence round-trip is out of scope per feedback_asyncpg_pool_event_loop.md.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
from pathlib import Path
from uuid import uuid4

import pytest

from aiflow.intake.package import IntakePackage, IntakeSourceType
from aiflow.sources import ApiSourceAdapter, SourceAdapterError
from aiflow.sources.registry import SourceAdapterRegistry

_SECRET = "phase-1b-e2e-webhook-secret"
_FIXED_NOW = 1_700_000_000


def _sign(secret: str, timestamp: str, payload: bytes) -> str:
    body_b64 = base64.b64encode(payload).decode("ascii")
    message = f"{timestamp}.{body_b64}".encode("ascii")
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


def _make_adapter(
    *,
    storage_root: Path,
    tenant_id: str,
    max_clock_skew_seconds: int = 300,
    max_package_bytes: int | None = None,
) -> ApiSourceAdapter:
    return ApiSourceAdapter(
        storage_root=storage_root,
        tenant_id=tenant_id,
        hmac_secret=_SECRET,
        max_clock_skew_seconds=max_clock_skew_seconds,
        max_package_bytes=max_package_bytes,
        now=lambda: _FIXED_NOW,
    )


def test_api_source_valid_signature_emits_intake_package(
    phase_1b_storage_root: Path,
    phase_1b_source_registry: SourceAdapterRegistry,
) -> None:
    """Valid envelope → one IntakePackage with correct sha256 + real disk spill."""
    tenant_id = f"tenant-e2e-api-happy-{uuid4().hex[:8]}"
    storage_root = phase_1b_storage_root / f"api_happy_{uuid4().hex[:8]}"

    adapter = _make_adapter(storage_root=storage_root, tenant_id=tenant_id)
    phase_1b_source_registry.register(ApiSourceAdapter)
    assert phase_1b_source_registry.has(IntakeSourceType.API_PUSH)

    payload = b"%PDF-1.4 api-push e2e payload"
    ts = str(_FIXED_NOW - 5)
    sig = _sign(_SECRET, ts, payload)

    pkg = adapter.enqueue(
        payload=payload,
        filename="webhook.pdf",
        signature=sig,
        timestamp=ts,
    )
    assert isinstance(pkg, IntakePackage)
    assert pkg.source_type == IntakeSourceType.API_PUSH
    assert pkg.tenant_id == tenant_id
    assert pkg.source_metadata["webhook_timestamp"] == int(ts)

    on_disk = Path(pkg.files[0].file_path)
    assert on_disk.read_bytes() == payload
    assert pkg.files[0].sha256 == hashlib.sha256(payload).hexdigest()
    assert on_disk.is_relative_to(storage_root / tenant_id / str(pkg.package_id))


def test_api_source_invalid_signature_rejected_and_nothing_queued(
    phase_1b_storage_root: Path,
) -> None:
    """Tampered signature → SourceAdapterError + no queue/disk side-effect."""
    tenant_id = f"tenant-e2e-api-invalid-{uuid4().hex[:8]}"
    storage_root = phase_1b_storage_root / f"api_invalid_{uuid4().hex[:8]}"

    adapter = _make_adapter(storage_root=storage_root, tenant_id=tenant_id)
    ts = str(_FIXED_NOW)
    bogus_sig = "0" * 64

    with pytest.raises(SourceAdapterError, match="invalid HMAC signature"):
        adapter.enqueue(
            payload=b"attacker",
            filename="x.bin",
            signature=bogus_sig,
            timestamp=ts,
        )

    assert len(adapter._queue) == 0
    tenant_dir = storage_root / tenant_id
    if tenant_dir.exists():
        leaked = [p for p in tenant_dir.rglob("*") if p.is_file()]
        assert leaked == []


def test_api_source_replay_window_expired_rejected(
    phase_1b_storage_root: Path,
) -> None:
    """Timestamp older than the replay window → SourceAdapterError."""
    tenant_id = f"tenant-e2e-api-replay-{uuid4().hex[:8]}"
    storage_root = phase_1b_storage_root / f"api_replay_{uuid4().hex[:8]}"

    adapter = _make_adapter(
        storage_root=storage_root,
        tenant_id=tenant_id,
        max_clock_skew_seconds=300,
    )
    # 1 hour behind the fixed now → well outside the 300 second window.
    ts = str(_FIXED_NOW - 3600)
    payload = b"late"
    sig = _sign(_SECRET, ts, payload)

    with pytest.raises(SourceAdapterError, match="replay window"):
        adapter.enqueue(payload=payload, filename="a.bin", signature=sig, timestamp=ts)


def test_api_source_duplicate_idempotency_key_rejected(
    phase_1b_storage_root: Path,
) -> None:
    """Same idempotency key twice → first accepted, second SourceAdapterError."""
    tenant_id = f"tenant-e2e-api-idem-{uuid4().hex[:8]}"
    storage_root = phase_1b_storage_root / f"api_idem_{uuid4().hex[:8]}"

    adapter = _make_adapter(storage_root=storage_root, tenant_id=tenant_id)
    ts = str(_FIXED_NOW)
    payload = b"once"
    sig = _sign(_SECRET, ts, payload)

    first = adapter.enqueue(
        payload=payload,
        filename="a.bin",
        signature=sig,
        timestamp=ts,
        idempotency_key="evt_e2e_1",
    )
    assert first.source_type == IntakeSourceType.API_PUSH

    with pytest.raises(SourceAdapterError, match="duplicate idempotency_key"):
        adapter.enqueue(
            payload=payload,
            filename="a.bin",
            signature=sig,
            timestamp=ts,
            idempotency_key="evt_e2e_1",
        )


@pytest.mark.asyncio
async def test_api_source_fetch_next_then_acknowledge_lifecycle(
    phase_1b_storage_root: Path,
) -> None:
    """enqueue → fetch_next → acknowledge; double-ack raises."""
    tenant_id = f"tenant-e2e-api-ack-{uuid4().hex[:8]}"
    storage_root = phase_1b_storage_root / f"api_ack_{uuid4().hex[:8]}"

    adapter = _make_adapter(storage_root=storage_root, tenant_id=tenant_id)
    ts = str(_FIXED_NOW)
    payload = b"ack-payload"
    sig = _sign(_SECRET, ts, payload)

    enqueued = adapter.enqueue(
        payload=payload,
        filename="ack.bin",
        signature=sig,
        timestamp=ts,
    )
    drained = await adapter.fetch_next()
    assert drained is not None
    assert drained.package_id == enqueued.package_id
    assert await adapter.fetch_next() is None

    await adapter.acknowledge(drained.package_id)
    with pytest.raises(SourceAdapterError):
        await adapter.acknowledge(drained.package_id)


@pytest.mark.asyncio
async def test_api_source_fetch_next_then_reject_lifecycle(
    phase_1b_storage_root: Path,
) -> None:
    """enqueue → fetch_next → reject; double-reject raises."""
    tenant_id = f"tenant-e2e-api-reject-{uuid4().hex[:8]}"
    storage_root = phase_1b_storage_root / f"api_reject_{uuid4().hex[:8]}"

    adapter = _make_adapter(storage_root=storage_root, tenant_id=tenant_id)
    ts = str(_FIXED_NOW)
    payload = b"reject-payload"
    sig = _sign(_SECRET, ts, payload)

    enqueued = adapter.enqueue(
        payload=payload,
        filename="reject.bin",
        signature=sig,
        timestamp=ts,
    )
    drained = await adapter.fetch_next()
    assert drained is not None
    assert drained.package_id == enqueued.package_id

    await adapter.reject(drained.package_id, reason="e2e-policy-violation")
    with pytest.raises(SourceAdapterError):
        await adapter.reject(drained.package_id, reason="double-reject")


def test_api_source_oversize_payload_rejected_no_disk_leak(
    phase_1b_storage_root: Path,
) -> None:
    """Payload larger than max_package_bytes → SourceAdapterError, nothing spilled."""
    tenant_id = f"tenant-e2e-api-oversize-{uuid4().hex[:8]}"
    storage_root = phase_1b_storage_root / f"api_oversize_{uuid4().hex[:8]}"

    adapter = _make_adapter(
        storage_root=storage_root,
        tenant_id=tenant_id,
        max_package_bytes=16,
    )
    ts = str(_FIXED_NOW)
    payload = b"X" * 4096
    sig = _sign(_SECRET, ts, payload)

    with pytest.raises(SourceAdapterError, match="exceeds max_package_bytes"):
        adapter.enqueue(payload=payload, filename="huge.bin", signature=sig, timestamp=ts)

    tenant_dir = storage_root / tenant_id
    if tenant_dir.exists():
        leaked = [p for p in tenant_dir.rglob("*") if p.is_file()]
        assert leaked == []
