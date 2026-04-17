"""Canonical source-adapter observability events (Phase 1c Day 3 — C4).

@test_registry:
    suite: core-unit
    component: sources.observability
    covers: [src/aiflow/sources/observability.py]
    phase: 1c
    priority: high
    estimated_duration_ms: 800
    requires_services: []
    tags: [sources, observability, structlog, phase_1c]

The tests below establish two guarantees that dashboards and alerts depend on:

1. Every source adapter emits `source.package_received` at acknowledge and
   `source.package_rejected` at reject, with a stable payload shape
   (`package_id`, `tenant_id`, `source_type`).
2. No PII / secret material leaks into the canonical event
   (`password`, `hmac_secret`, raw `signature`, email `body`).

The legacy per-adapter events (`file_adapter_acknowledged`, ...) remain
emitted for backward compatibility; see
`aiflow.sources.observability` docstring for the deprecation timeline.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import io
import zipfile
from collections.abc import Callable
from email.message import EmailMessage
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from structlog.testing import capture_logs

from aiflow.intake.package import IntakeFile, IntakePackage, IntakeSourceType
from aiflow.sources import (
    ApiSourceAdapter,
    BatchSourceAdapter,
    EmailSourceAdapter,
    FileSourceAdapter,
    FolderSourceAdapter,
    SourceAdapter,
)
from aiflow.sources.email_adapter import ImapBackendProtocol
from aiflow.sources.observability import emit_package_event

# ---------------------------------------------------------------------------
# PII-forbidden keys — every canonical event MUST NOT surface any of these.
# ---------------------------------------------------------------------------

FORBIDDEN_KEYS: frozenset[str] = frozenset(
    {"password", "hmac_secret", "signature", "body", "raw", "payload"}
)

_TENANT = "tenant_obs"


def _assert_canonical_shape(
    record: dict[str, Any],
    *,
    expected_event: str,
    expected_source_type: str,
    expected_tenant_id: str = _TENANT,
) -> None:
    assert record["event"] == expected_event
    assert record["source_type"] == expected_source_type
    assert record["tenant_id"] == expected_tenant_id
    # package_id is a UUID string.
    from uuid import UUID

    UUID(record["package_id"])
    for key in record:
        assert key.lower() not in FORBIDDEN_KEYS, (
            f"canonical event {expected_event!r} leaked forbidden key {key!r}"
        )


def _only_canonical(events: list[dict[str, Any]], name: str) -> list[dict[str, Any]]:
    return [e for e in events if e.get("event") == name]


# ---------------------------------------------------------------------------
# 1. emit_package_event helper — direct unit tests
# ---------------------------------------------------------------------------


def _fake_package() -> IntakePackage:
    f = IntakeFile(
        file_path="/tmp/fake.txt",
        file_name="fake.txt",
        mime_type="text/plain",
        size_bytes=1,
        sha256="0" * 64,
        sequence_index=0,
    )
    return IntakePackage(
        package_id=uuid4(),
        source_type=IntakeSourceType.FILE_UPLOAD,
        tenant_id=_TENANT,
        source_metadata={"kind": "unit"},
        files=[f],
        descriptions=[],
    )


def test_helper_received_has_canonical_shape() -> None:
    pkg = _fake_package()
    with capture_logs() as events:
        emit_package_event("source.package_received", pkg, source_type="file")
    canonical = _only_canonical(events, "source.package_received")
    assert len(canonical) == 1
    _assert_canonical_shape(
        canonical[0],
        expected_event="source.package_received",
        expected_source_type="file",
    )


def test_helper_persisted_has_canonical_shape() -> None:
    pkg = _fake_package()
    with capture_logs() as events:
        emit_package_event(
            "source.package_persisted",
            pkg,
            source_type="email",
            file_count=1,
            description_count=0,
        )
    canonical = _only_canonical(events, "source.package_persisted")
    assert len(canonical) == 1
    assert canonical[0]["file_count"] == 1
    assert canonical[0]["description_count"] == 0
    _assert_canonical_shape(
        canonical[0],
        expected_event="source.package_persisted",
        expected_source_type="email",
    )


def test_helper_rejected_carries_reason() -> None:
    pkg = _fake_package()
    with capture_logs() as events:
        emit_package_event(
            "source.package_rejected", pkg, source_type="api", reason="signature_invalid"
        )
    canonical = _only_canonical(events, "source.package_rejected")
    assert len(canonical) == 1
    assert canonical[0]["reason"] == "signature_invalid"
    _assert_canonical_shape(
        canonical[0],
        expected_event="source.package_rejected",
        expected_source_type="api",
    )


# ---------------------------------------------------------------------------
# 2. Adapter factories — each returns (adapter, in_flight_package)
# ---------------------------------------------------------------------------


async def _build_file(tmp_path: Path) -> tuple[SourceAdapter, IntakePackage]:
    adapter = FileSourceAdapter(storage_root=tmp_path / "storage", tenant_id=_TENANT)
    pkg = adapter.enqueue(raw_bytes=b"hello", filename="doc.txt")
    return adapter, pkg


async def _build_folder(tmp_path: Path) -> tuple[SourceAdapter, IntakePackage]:
    watch_root = tmp_path / "watch"
    storage_root = tmp_path / "storage"
    watch_root.mkdir(parents=True, exist_ok=True)
    adapter = FolderSourceAdapter(
        watch_root=watch_root,
        storage_root=storage_root,
        tenant_id=_TENANT,
        debounce_ms=0,
        stable_mtime_window_ms=0,
        auto_start=False,
    )
    path = watch_root / "note.txt"
    path.write_bytes(b"hello")
    adapter._note_event(path)
    await adapter._drain_pending()
    pkg = await adapter.fetch_next()
    assert pkg is not None
    return adapter, pkg


async def _build_batch(tmp_path: Path) -> tuple[SourceAdapter, IntakePackage]:
    adapter = BatchSourceAdapter(storage_root=tmp_path / "storage", tenant_id=_TENANT)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_STORED) as zf:
        zf.writestr("doc.pdf", b"%PDF-1.4 test")
    pkgs = adapter.enqueue(raw_bytes=buf.getvalue(), filename="batch.zip")
    assert pkgs
    return adapter, pkgs[0]


_API_SECRET = "super-secret-webhook-key"


def _sign_api(timestamp: str, payload: bytes) -> str:
    body_b64 = base64.b64encode(payload).decode("ascii")
    message = f"{timestamp}.{body_b64}".encode("ascii")
    return hmac.new(_API_SECRET.encode("utf-8"), message, hashlib.sha256).hexdigest()


async def _build_api(tmp_path: Path) -> tuple[SourceAdapter, IntakePackage]:
    adapter = ApiSourceAdapter(
        storage_root=tmp_path / "storage",
        tenant_id=_TENANT,
        hmac_secret=_API_SECRET,
        max_clock_skew_seconds=300,
        now=lambda: 1_700_000_000,
    )
    payload = b"webhook body"
    ts = "1700000000"
    pkg = adapter.enqueue(
        payload=payload, filename="wh.bin", signature=_sign_api(ts, payload), timestamp=ts
    )
    return adapter, pkg


class _MemImapBackend(ImapBackendProtocol):
    def __init__(self, inbox: list[tuple[int, bytes]]) -> None:
        self.inbox = list(inbox)
        self.seen: set[int] = set()
        self.flagged: dict[int, str] = {}

    async def fetch_unseen(self) -> list[tuple[int, bytes]]:
        return [(u, r) for u, r in self.inbox if u not in self.seen]

    async def mark_seen(self, uid: int) -> None:
        self.seen.add(uid)

    async def mark_flagged(self, uid: int, reason: str) -> None:
        self.flagged[uid] = reason

    async def ping(self) -> bool:
        return True


def _plain_email(subject: str = "hi", body: str = "text") -> bytes:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = "a@example.com"
    msg["To"] = "b@example.com"
    msg.set_content(body)
    return msg.as_bytes()


async def _build_email(tmp_path: Path) -> tuple[SourceAdapter, IntakePackage]:
    backend = _MemImapBackend([(7, _plain_email())])
    adapter = EmailSourceAdapter(
        backend=backend,
        storage_root=tmp_path / "storage",
        tenant_id=_TENANT,
    )
    pkg = await adapter.fetch_next()
    assert pkg is not None
    return adapter, pkg


_ADAPTER_FACTORIES: list[tuple[str, Callable[[Path], Any]]] = [
    ("file", _build_file),
    ("folder", _build_folder),
    ("batch", _build_batch),
    ("api", _build_api),
    ("email", _build_email),
]


# ---------------------------------------------------------------------------
# 3. Per-adapter canonical event assertions (5 adapters)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(("source_type", "factory"), _ADAPTER_FACTORIES)
async def test_adapter_emits_canonical_received_on_acknowledge(
    source_type: str,
    factory: Callable[[Path], Any],
    tmp_path: Path,
) -> None:
    adapter, pkg = await factory(tmp_path)
    with capture_logs() as events:
        await adapter.acknowledge(pkg.package_id)
    canonical = _only_canonical(events, "source.package_received")
    assert len(canonical) == 1, (
        f"{source_type}: expected exactly one source.package_received event, got {len(canonical)}"
    )
    _assert_canonical_shape(
        canonical[0],
        expected_event="source.package_received",
        expected_source_type=source_type,
    )
    assert canonical[0]["package_id"] == str(pkg.package_id)
    assert canonical[0]["tenant_id"] == _TENANT


@pytest.mark.asyncio
@pytest.mark.parametrize(("source_type", "factory"), _ADAPTER_FACTORIES)
async def test_adapter_emits_canonical_rejected_on_reject(
    source_type: str,
    factory: Callable[[Path], Any],
    tmp_path: Path,
) -> None:
    adapter, pkg = await factory(tmp_path)
    with capture_logs() as events:
        await adapter.reject(pkg.package_id, reason="policy_violation")
    canonical = _only_canonical(events, "source.package_rejected")
    assert len(canonical) == 1, (
        f"{source_type}: expected exactly one source.package_rejected event, got {len(canonical)}"
    )
    assert canonical[0]["reason"] == "policy_violation"
    _assert_canonical_shape(
        canonical[0],
        expected_event="source.package_rejected",
        expected_source_type=source_type,
    )


# ---------------------------------------------------------------------------
# 4. Cross-adapter parity — canonical and legacy events coexist; canonical
#    set covers all 5 adapters.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_canonical_events_cover_all_five_adapters(tmp_path: Path) -> None:
    observed_sources: set[str] = set()
    for idx, (source_type, factory) in enumerate(_ADAPTER_FACTORIES):
        sub = tmp_path / f"adapter_{idx}_{source_type}"
        sub.mkdir()
        adapter, pkg = await factory(sub)
        with capture_logs() as events:
            await adapter.acknowledge(pkg.package_id)
        received = _only_canonical(events, "source.package_received")
        assert received, f"{source_type}: no canonical received event"
        observed_sources.add(received[0]["source_type"])
    assert observed_sources == {"file", "folder", "batch", "api", "email"}


@pytest.mark.asyncio
async def test_legacy_per_adapter_event_still_emitted(tmp_path: Path) -> None:
    """Backward-compat: v1.4.2 keeps the legacy event alongside the canonical one."""
    adapter, pkg = await _build_file(tmp_path)
    with capture_logs() as events:
        await adapter.acknowledge(pkg.package_id)
    legacy = [e for e in events if e.get("event") == "file_adapter_acknowledged"]
    canonical = _only_canonical(events, "source.package_received")
    assert len(legacy) == 1
    assert len(canonical) == 1
