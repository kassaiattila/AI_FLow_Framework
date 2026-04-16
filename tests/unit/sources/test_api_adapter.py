"""Unit tests for ApiSourceAdapter (Phase 1b — Week 2 Day 8 — E2.3-A).

@test_registry: phase_1b.sources.api_adapter

Covers metadata shape, HMAC-SHA256 signature verification, replay window,
idempotency guard, size guard, queue draining, ack/reject bookkeeping,
filename sanitization, and health_check. The signed-string layout is
``<timestamp>.<base64(body)>`` — tests exercise both valid and tampered
variants to prove timing-safe compare_digest is actually wired up.
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

_SECRET = "super-secret-webhook-key"


def _sign(secret: str, timestamp: str, payload: bytes) -> str:
    body_b64 = base64.b64encode(payload).decode("ascii")
    message = f"{timestamp}.{body_b64}".encode("ascii")
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


@pytest.fixture()
def storage_root(tmp_path: Path) -> Path:
    return tmp_path / "storage"


def _make_adapter(
    *,
    storage_root: Path,
    tenant_id: str = "tenant_a",
    hmac_secret: str = _SECRET,
    max_clock_skew_seconds: int = 300,
    max_package_bytes: int | None = None,
    now: int = 1_700_000_000,
) -> ApiSourceAdapter:
    return ApiSourceAdapter(
        storage_root=storage_root,
        tenant_id=tenant_id,
        hmac_secret=hmac_secret,
        max_clock_skew_seconds=max_clock_skew_seconds,
        max_package_bytes=max_package_bytes,
        now=lambda: now,
    )


# ---------------------------------------------------------------------------
# 1. Metadata shape
# ---------------------------------------------------------------------------


def test_metadata_shape(storage_root: Path) -> None:
    adapter = _make_adapter(storage_root=storage_root)
    meta = adapter.metadata
    assert meta.source_type == IntakeSourceType.API_PUSH
    assert meta.transport == "push"
    assert meta.requires_ack is False
    assert meta.supports_batching is False
    assert meta.name == "api_push"
    assert ApiSourceAdapter.source_type == IntakeSourceType.API_PUSH


# ---------------------------------------------------------------------------
# 2. Valid signature → IntakePackage with correct sha256 + size
# ---------------------------------------------------------------------------


def test_valid_signature_emits_intake_package(storage_root: Path) -> None:
    adapter = _make_adapter(storage_root=storage_root)
    payload = b"%PDF-1.4 dummy webhook"
    ts = "1700000000"
    sig = _sign(_SECRET, ts, payload)

    pkg = adapter.enqueue(payload=payload, filename="doc.pdf", signature=sig, timestamp=ts)

    assert isinstance(pkg, IntakePackage)
    assert pkg.source_type == IntakeSourceType.API_PUSH
    assert pkg.tenant_id == "tenant_a"
    assert len(pkg.files) == 1
    f = pkg.files[0]
    assert f.size_bytes == len(payload)
    assert f.sha256 == hashlib.sha256(payload).hexdigest()
    assert Path(f.file_path).read_bytes() == payload


# ---------------------------------------------------------------------------
# 3. Invalid signature → SourceAdapterError, nothing queued
# ---------------------------------------------------------------------------


def test_invalid_signature_rejected(storage_root: Path) -> None:
    adapter = _make_adapter(storage_root=storage_root)
    ts = "1700000000"
    bogus = "0" * 64
    with pytest.raises(SourceAdapterError, match="invalid HMAC signature"):
        adapter.enqueue(payload=b"hello", filename="x.bin", signature=bogus, timestamp=ts)
    assert len(adapter._queue) == 0  # noqa: SLF001


# ---------------------------------------------------------------------------
# 4. Tampered payload (signature of a different body) → rejected
# ---------------------------------------------------------------------------


def test_tampered_payload_rejected(storage_root: Path) -> None:
    adapter = _make_adapter(storage_root=storage_root)
    ts = "1700000000"
    sig_for_original = _sign(_SECRET, ts, b"original")
    with pytest.raises(SourceAdapterError, match="invalid HMAC signature"):
        adapter.enqueue(
            payload=b"tampered",
            filename="x.bin",
            signature=sig_for_original,
            timestamp=ts,
        )


# ---------------------------------------------------------------------------
# 5. Expired timestamp (outside replay window) → rejected
# ---------------------------------------------------------------------------


def test_expired_timestamp_rejected(storage_root: Path) -> None:
    adapter = _make_adapter(storage_root=storage_root, max_clock_skew_seconds=300)
    # now = 1_700_000_000, ts is 1 hour old
    ts = "1699996400"
    sig = _sign(_SECRET, ts, b"x")
    with pytest.raises(SourceAdapterError, match="replay window"):
        adapter.enqueue(payload=b"x", filename="a.bin", signature=sig, timestamp=ts)


def test_future_timestamp_rejected(storage_root: Path) -> None:
    adapter = _make_adapter(storage_root=storage_root, max_clock_skew_seconds=300)
    # Clock-skew in the future must also be rejected (abs check).
    ts = "1700003600"
    sig = _sign(_SECRET, ts, b"x")
    with pytest.raises(SourceAdapterError, match="replay window"):
        adapter.enqueue(payload=b"x", filename="a.bin", signature=sig, timestamp=ts)


# ---------------------------------------------------------------------------
# 6. Clock skew within tolerance → accepted
# ---------------------------------------------------------------------------


def test_clock_skew_within_tolerance_accepted(storage_root: Path) -> None:
    adapter = _make_adapter(storage_root=storage_root, max_clock_skew_seconds=300)
    ts = "1699999850"  # 150 seconds behind adapter now
    sig = _sign(_SECRET, ts, b"x")
    pkg = adapter.enqueue(payload=b"x", filename="a.bin", signature=sig, timestamp=ts)
    assert pkg.source_type == IntakeSourceType.API_PUSH


# ---------------------------------------------------------------------------
# 7. Idempotency key duplicate → rejected
# ---------------------------------------------------------------------------


def test_duplicate_idempotency_key_rejected(storage_root: Path) -> None:
    adapter = _make_adapter(storage_root=storage_root)
    ts = "1700000000"
    sig = _sign(_SECRET, ts, b"payload")
    pkg = adapter.enqueue(
        payload=b"payload",
        filename="a.bin",
        signature=sig,
        timestamp=ts,
        idempotency_key="evt_123",
    )
    assert pkg.source_type == IntakeSourceType.API_PUSH
    with pytest.raises(SourceAdapterError, match="duplicate idempotency_key"):
        adapter.enqueue(
            payload=b"payload",
            filename="a.bin",
            signature=sig,
            timestamp=ts,
            idempotency_key="evt_123",
        )


def test_idempotency_key_not_poisoned_by_forged_request(storage_root: Path) -> None:
    """An attacker's forged request must not consume a legitimate idempotency key."""
    adapter = _make_adapter(storage_root=storage_root)
    ts = "1700000000"
    bad_sig = "0" * 64

    with pytest.raises(SourceAdapterError, match="invalid HMAC signature"):
        adapter.enqueue(
            payload=b"x",
            filename="a.bin",
            signature=bad_sig,
            timestamp=ts,
            idempotency_key="evt_456",
        )

    # Legitimate caller with the same key must still succeed.
    good_sig = _sign(_SECRET, ts, b"x")
    pkg = adapter.enqueue(
        payload=b"x",
        filename="a.bin",
        signature=good_sig,
        timestamp=ts,
        idempotency_key="evt_456",
    )
    assert pkg.source_type == IntakeSourceType.API_PUSH


# ---------------------------------------------------------------------------
# 8. Size guard
# ---------------------------------------------------------------------------


def test_size_guard_rejects_oversized_payload(storage_root: Path) -> None:
    adapter = _make_adapter(storage_root=storage_root, max_package_bytes=16)
    ts = "1700000000"
    payload = b"X" * 64
    sig = _sign(_SECRET, ts, payload)
    with pytest.raises(SourceAdapterError, match="exceeds max_package_bytes"):
        adapter.enqueue(payload=payload, filename="big.bin", signature=sig, timestamp=ts)
    assert len(adapter._queue) == 0  # noqa: SLF001


# ---------------------------------------------------------------------------
# 9. Invalid timestamp format
# ---------------------------------------------------------------------------


def test_invalid_timestamp_format_rejected(storage_root: Path) -> None:
    adapter = _make_adapter(storage_root=storage_root)
    sig = "0" * 64
    with pytest.raises(SourceAdapterError, match="invalid timestamp"):
        adapter.enqueue(payload=b"x", filename="a.bin", signature=sig, timestamp="not-a-number")


def test_missing_signature_rejected(storage_root: Path) -> None:
    adapter = _make_adapter(storage_root=storage_root)
    with pytest.raises(SourceAdapterError, match="missing signature"):
        adapter.enqueue(payload=b"x", filename="a.bin", signature="", timestamp="1700000000")


def test_missing_timestamp_rejected(storage_root: Path) -> None:
    adapter = _make_adapter(storage_root=storage_root)
    with pytest.raises(SourceAdapterError, match="missing timestamp"):
        adapter.enqueue(payload=b"x", filename="a.bin", signature="abc", timestamp="")


# ---------------------------------------------------------------------------
# 10. fetch_next drains queue FIFO
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_next_drains_queue_fifo(storage_root: Path) -> None:
    adapter = _make_adapter(storage_root=storage_root)
    ts = "1700000000"
    sig_a = _sign(_SECRET, ts, b"one")
    sig_b = _sign(_SECRET, ts, b"two")
    p1 = adapter.enqueue(payload=b"one", filename="a.txt", signature=sig_a, timestamp=ts)
    p2 = adapter.enqueue(payload=b"two", filename="b.txt", signature=sig_b, timestamp=ts)

    first = await adapter.fetch_next()
    second = await adapter.fetch_next()
    third = await adapter.fetch_next()
    assert first is not None and first.package_id == p1.package_id
    assert second is not None and second.package_id == p2.package_id
    assert third is None


@pytest.mark.asyncio
async def test_fetch_next_empty_queue_returns_none(storage_root: Path) -> None:
    adapter = _make_adapter(storage_root=storage_root)
    assert await adapter.fetch_next() is None


# ---------------------------------------------------------------------------
# 11. acknowledge / reject bookkeeping
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_acknowledge_unknown_package_id_raises(storage_root: Path) -> None:
    adapter = _make_adapter(storage_root=storage_root)
    with pytest.raises(SourceAdapterError):
        await adapter.acknowledge(uuid4())


@pytest.mark.asyncio
async def test_reject_unknown_package_id_raises(storage_root: Path) -> None:
    adapter = _make_adapter(storage_root=storage_root)
    with pytest.raises(SourceAdapterError):
        await adapter.reject(uuid4(), reason="nope")


@pytest.mark.asyncio
async def test_acknowledge_clears_in_flight_and_double_ack_raises(storage_root: Path) -> None:
    adapter = _make_adapter(storage_root=storage_root)
    ts = "1700000000"
    sig = _sign(_SECRET, ts, b"x")
    pkg = adapter.enqueue(payload=b"x", filename="a.bin", signature=sig, timestamp=ts)
    await adapter.acknowledge(pkg.package_id)
    with pytest.raises(SourceAdapterError):
        await adapter.acknowledge(pkg.package_id)


# ---------------------------------------------------------------------------
# 12. Filename sanitization
# ---------------------------------------------------------------------------


def test_unsafe_filename_is_sanitized(storage_root: Path) -> None:
    adapter = _make_adapter(storage_root=storage_root)
    ts = "1700000000"
    sig = _sign(_SECRET, ts, b"x")
    pkg = adapter.enqueue(payload=b"x", filename="../../etc/passwd", signature=sig, timestamp=ts)
    dest = Path(pkg.files[0].file_path)
    assert dest.parent == storage_root / "tenant_a" / str(pkg.package_id)
    assert "/" not in dest.name
    assert "\\" not in dest.name
    assert pkg.files[0].file_name == "../../etc/passwd"  # preserved for audit


# ---------------------------------------------------------------------------
# 13. Construction guards
# ---------------------------------------------------------------------------


def test_empty_tenant_id_rejected(storage_root: Path) -> None:
    with pytest.raises(ValueError, match="tenant_id"):
        ApiSourceAdapter(storage_root=storage_root, tenant_id="", hmac_secret=_SECRET)


def test_empty_hmac_secret_rejected(storage_root: Path) -> None:
    with pytest.raises(ValueError, match="hmac_secret"):
        ApiSourceAdapter(storage_root=storage_root, tenant_id="t", hmac_secret="")


def test_zero_clock_skew_rejected(storage_root: Path) -> None:
    with pytest.raises(ValueError, match="max_clock_skew_seconds"):
        ApiSourceAdapter(
            storage_root=storage_root,
            tenant_id="t",
            hmac_secret=_SECRET,
            max_clock_skew_seconds=0,
        )


def test_empty_filename_rejected(storage_root: Path) -> None:
    adapter = _make_adapter(storage_root=storage_root)
    ts = "1700000000"
    sig = _sign(_SECRET, ts, b"x")
    with pytest.raises(ValueError, match="filename"):
        adapter.enqueue(payload=b"x", filename="", signature=sig, timestamp=ts)


# ---------------------------------------------------------------------------
# 14. health_check
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_check_creates_and_probes_storage_root(tmp_path: Path) -> None:
    storage = tmp_path / "nested" / "storage"
    adapter = ApiSourceAdapter(
        storage_root=storage,
        tenant_id="t",
        hmac_secret=_SECRET,
    )
    assert await adapter.health_check() is True
    assert storage.is_dir()


# ---------------------------------------------------------------------------
# 15. Secret is not exposed on the adapter's public surface
# ---------------------------------------------------------------------------


def test_secret_not_leaked_in_repr_or_metadata(storage_root: Path) -> None:
    adapter = _make_adapter(storage_root=storage_root, hmac_secret="LEAK_CANARY_42")
    # metadata only carries public fields
    meta_dump = adapter.metadata.model_dump_json()
    assert "LEAK_CANARY_42" not in meta_dump
    # repr must not expose the secret either
    assert "LEAK_CANARY_42" not in repr(adapter)


# ---------------------------------------------------------------------------
# 16. Package metadata records webhook_timestamp + idempotency_key
# ---------------------------------------------------------------------------


def test_package_metadata_records_envelope_fields(storage_root: Path) -> None:
    adapter = _make_adapter(storage_root=storage_root)
    ts = "1700000000"
    sig = _sign(_SECRET, ts, b"p")
    pkg = adapter.enqueue(
        payload=b"p",
        filename="a.bin",
        signature=sig,
        timestamp=ts,
        idempotency_key="evt_789",
    )
    assert pkg.source_metadata["webhook_timestamp"] == 1_700_000_000
    assert pkg.source_metadata["idempotency_key"] == "evt_789"
    assert pkg.files[0].source_metadata["idempotency_key"] == "evt_789"
