"""ABC contract test — parametrized over all 5 Phase 1b source adapters.

@test_registry: phase_1b.sources.adapter_contract

Proves every concrete SourceAdapter honors the same abstract contract:
  1. metadata is a SourceAdapterMetadata whose source_type matches the
     adapter's ClassVar source_type.
  2. fetch_next() yields a well-formed IntakePackage with the expected
     source_type and a non-empty tenant_id.
  3. acknowledge lifecycle: single ack succeeds, double-ack raises
     SourceAdapterError.
  4. reject lifecycle: single reject succeeds, double-reject raises
     SourceAdapterError.
  5. health_check() returns a bool.

Each ``factory`` prepares a fresh adapter already primed with at least one
IntakePackage so the ack / reject lifecycle can be exercised deterministically
without touching external services. The factories intentionally avoid sharing
state — every invocation yields an isolated instance with its own tmp storage.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import io
import zipfile
from collections.abc import Callable
from pathlib import Path

import pytest

from aiflow.intake.package import IntakePackage
from aiflow.sources import (
    ApiSourceAdapter,
    BatchSourceAdapter,
    EmailSourceAdapter,
    FileSourceAdapter,
    FolderSourceAdapter,
    SourceAdapter,
    SourceAdapterError,
    SourceAdapterMetadata,
)

# The FakeImapBackend + MIME builder are reused from the unit tests instead of
# duplicating them here. This is the same pattern used by test_email_source.py
# (see session_S60 STOP rule on fake duplication).
from tests.unit.sources.test_email_adapter import (
    FakeImapBackend,
    _make_multipart_with_attachments,
)

_API_SECRET = "contract-test-webhook-secret"
_API_NOW = 1_700_000_000


def _sign(secret: str, timestamp: str, payload: bytes) -> str:
    body_b64 = base64.b64encode(payload).decode("ascii")
    message = f"{timestamp}.{body_b64}".encode("ascii")
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


def _make_zip(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_STORED) as zf:
        for name, data in files.items():
            zf.writestr(name, data)
    return buf.getvalue()


def _email_factory(tmp_path: Path) -> SourceAdapter:
    msg = _make_multipart_with_attachments(
        subject="contract",
        sender="sender@example.com",
        body="contract-test body",
        attachments=[("doc.pdf", "application/pdf", b"%PDF-1.4 x")],
    )
    backend = FakeImapBackend([(9001, msg)])
    return EmailSourceAdapter(
        backend=backend,
        storage_root=tmp_path / "email",
        tenant_id="tenant-contract-email",
    )


def _file_factory(tmp_path: Path) -> SourceAdapter:
    adapter = FileSourceAdapter(
        storage_root=tmp_path / "file",
        tenant_id="tenant-contract-file",
    )
    adapter.enqueue(raw_bytes=b"file contract payload", filename="doc.pdf")
    return adapter


def _folder_factory(tmp_path: Path) -> SourceAdapter:
    watch_root = tmp_path / "folder_watch"
    watch_root.mkdir(parents=True, exist_ok=True)
    adapter = FolderSourceAdapter(
        watch_root=watch_root,
        storage_root=tmp_path / "folder_storage",
        tenant_id="tenant-contract-folder",
        debounce_ms=0,
        stable_mtime_window_ms=0,
        auto_start=False,
    )
    path = watch_root / "doc.txt"
    path.write_bytes(b"folder contract payload")
    adapter._note_event(path)
    return adapter


def _batch_factory(tmp_path: Path) -> SourceAdapter:
    adapter = BatchSourceAdapter(
        storage_root=tmp_path / "batch",
        tenant_id="tenant-contract-batch",
    )
    adapter.enqueue(
        raw_bytes=_make_zip({"one.txt": b"1", "two.txt": b"2"}),
        filename="pair.zip",
    )
    return adapter


def _api_factory(tmp_path: Path) -> SourceAdapter:
    adapter = ApiSourceAdapter(
        storage_root=tmp_path / "api",
        tenant_id="tenant-contract-api",
        hmac_secret=_API_SECRET,
        max_clock_skew_seconds=300,
        now=lambda: _API_NOW,
    )
    ts = str(_API_NOW)
    payload = b"api contract payload"
    sig = _sign(_API_SECRET, ts, payload)
    adapter.enqueue(payload=payload, filename="doc.bin", signature=sig, timestamp=ts)
    return adapter


_FACTORIES: list[tuple[str, Callable[[Path], SourceAdapter]]] = [
    ("email", _email_factory),
    ("file", _file_factory),
    ("folder", _folder_factory),
    ("batch", _batch_factory),
    ("api", _api_factory),
]


@pytest.mark.parametrize(
    "factory",
    [f for _, f in _FACTORIES],
    ids=[n for n, _ in _FACTORIES],
)
@pytest.mark.asyncio
async def test_adapter_conforms_to_abc(
    factory: Callable[[Path], SourceAdapter], tmp_path: Path
) -> None:
    """Every adapter honors the SourceAdapter ABC uniformly."""
    adapter = factory(tmp_path / "ack_round")

    meta = adapter.metadata
    assert isinstance(meta, SourceAdapterMetadata)
    assert meta.source_type == type(adapter).source_type
    assert meta.transport in {"push", "pull"}
    assert isinstance(meta.name, str) and meta.name
    assert isinstance(meta.version, str) and meta.version

    pkg = await adapter.fetch_next()
    assert isinstance(pkg, IntakePackage)
    assert pkg.source_type == meta.source_type
    assert pkg.tenant_id

    await adapter.acknowledge(pkg.package_id)
    with pytest.raises(SourceAdapterError):
        await adapter.acknowledge(pkg.package_id)

    health = await adapter.health_check()
    assert isinstance(health, bool)

    reject_adapter = factory(tmp_path / "reject_round")
    pkg_r = await reject_adapter.fetch_next()
    assert isinstance(pkg_r, IntakePackage)
    await reject_adapter.reject(pkg_r.package_id, reason="contract-test")
    with pytest.raises(SourceAdapterError):
        await reject_adapter.reject(pkg_r.package_id, reason="contract-test")
