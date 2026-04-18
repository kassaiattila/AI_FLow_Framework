"""E2E — Multi-source acceptance gate (Phase 1b Week 3 Day 14 / E3.3).

@test_registry
suite: phase_1b_e2e
component: sources.[email|file|folder|batch|api], intake.associator,
           state.repositories.intake, api.v1.intake
covers: [src/aiflow/sources/*.py, src/aiflow/intake/associator.py,
         src/aiflow/state/repositories/intake.py, src/aiflow/api/v1/intake.py]
phase: 1b
priority: critical
requires_services: [postgres]
tags: [e2e, phase_1b, intake, source_adapter, multi_source, acceptance_gate,
       association_mode, regression]

Three acceptance-gate contracts for Week 3 Day 14 (E3.3):

1. ``test_all_sources_produce_valid_intake_package`` — parametrized over the
   5 source adapters (email, file_upload, folder_import, batch_import,
   api_push). Each case exercises: adapter produce → storage spill → sha256
   match → PolicyEngine.get_for_tenant() resolves → IntakeRepository
   insert_package + get_package round-trip. One asyncio loop per parametrize
   case owns its own asyncpg pool — keeps the loop-bound pool contract from
   feedback_asyncpg_pool_event_loop.md intact.

2. ``test_n4_association_modes_roundtrip`` — all 4 ``AssociationMode`` values
   (EXPLICIT / FILENAME_MATCH / ORDER / SINGLE_DESCRIPTION). Three modes go
   through the real ``POST /api/v1/intake/upload-package`` endpoint; EXPLICIT
   uses the direct adapter path because the multipart form cannot bind the
   explicit file_id→description_id map to server-generated file_ids in the
   same request. All four land in Postgres and are hydrated with the chosen
   mode + associations intact.

3. ``test_phase_1a_regression_unchanged`` — spawns a fresh pytest subprocess
   to re-run the Phase 1a E2E suite (``tests/e2e/v1_4_0_phase_1a/``) and
   asserts exit code 0 plus the summary line reports 199 passing tests. This
   is the hard backward-compat gate: Phase 1b changes must not touch Phase 1a
   behaviour.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import io
import json
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path
from unittest.mock import patch
from uuid import UUID, uuid4

import asyncpg
import pytest
from fastapi.testclient import TestClient

from aiflow.intake.associator import associate
from aiflow.intake.package import (
    AssociationMode,
    IntakeDescription,
    IntakePackage,
    IntakeSourceType,
)
from aiflow.policy.engine import PolicyEngine
from aiflow.security.auth import AuthProvider
from aiflow.sources import (
    ApiSourceAdapter,
    BatchSourceAdapter,
    EmailSourceAdapter,
    FileSourceAdapter,
    FolderSourceAdapter,
    IntakePackageSink,
)
from aiflow.state.repositories.intake import IntakeRepository
from tests.unit.sources.test_email_adapter import (
    FakeImapBackend,
    _make_multipart_with_attachments,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
PROFILE_A_PATH = REPO_ROOT / "config" / "profiles" / "profile_a.yaml"

_WEBHOOK_SECRET = "phase-1b-multi-source-secret"
_FIXED_NOW = 1_700_500_000

pytestmark = pytest.mark.e2e


def _db_url() -> str:
    url = os.environ.get(
        "AIFLOW_DATABASE__URL",
        "postgresql+asyncpg://aiflow:aiflow_dev_password@localhost:5433/aiflow_dev",
    )
    return url.replace("postgresql+asyncpg://", "postgresql://")


def _make_zip(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_STORED) as zf:
        for name, data in files.items():
            zf.writestr(name, data)
    return buf.getvalue()


def _sign_api_envelope(secret: str, timestamp: str, payload: bytes) -> str:
    body_b64 = base64.b64encode(payload).decode("ascii")
    message = f"{timestamp}.{body_b64}".encode("ascii")
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


# ---------------------------------------------------------------------------
# LEPES 1 — multi-source adapter matrix
# ---------------------------------------------------------------------------


async def _produce_email(tenant_id: str, storage_root: Path) -> IntakePackage:
    payload = b"%PDF-1.4 email-matrix payload\n"
    raw = _make_multipart_with_attachments(
        subject="multi-source matrix",
        sender="supplier@example.com",
        body="invoice attached for matrix gate",
        attachments=[("matrix-invoice.pdf", "application/pdf", payload)],
    )
    adapter = EmailSourceAdapter(
        backend=FakeImapBackend([(9101, raw)]),
        storage_root=storage_root,
        tenant_id=tenant_id,
    )
    pkg = await adapter.fetch_next()
    assert pkg is not None
    return pkg


async def _produce_file(tenant_id: str, storage_root: Path) -> IntakePackage:
    adapter = FileSourceAdapter(storage_root=storage_root, tenant_id=tenant_id)
    return adapter.enqueue(
        raw_bytes=b"%PDF-1.4 file-upload matrix payload",
        filename="matrix-upload.pdf",
        description="matrix single upload",
    )


async def _produce_folder(tenant_id: str, storage_root: Path) -> IntakePackage:
    watch_root = storage_root.parent / f"{storage_root.name}_watch"
    watch_root.mkdir(parents=True, exist_ok=True)
    adapter = FolderSourceAdapter(
        watch_root=watch_root,
        storage_root=storage_root,
        tenant_id=tenant_id,
        debounce_ms=0,
        stable_mtime_window_ms=0,
        auto_start=False,
    )
    payload = b"%PDF-1.4 folder matrix payload"
    dropped = watch_root / "matrix-folder.pdf"
    dropped.write_bytes(payload)
    adapter._note_event(dropped)
    pkg = await adapter.fetch_next()
    assert pkg is not None
    return pkg


async def _produce_batch(tenant_id: str, storage_root: Path) -> IntakePackage:
    adapter = BatchSourceAdapter(storage_root=storage_root, tenant_id=tenant_id)
    archive = _make_zip({"batch-item.pdf": b"%PDF-1.4 batch matrix payload"})
    pkgs = adapter.enqueue(raw_bytes=archive, filename="matrix.zip")
    assert len(pkgs) == 1
    return pkgs[0]


async def _produce_api(tenant_id: str, storage_root: Path) -> IntakePackage:
    adapter = ApiSourceAdapter(
        storage_root=storage_root,
        tenant_id=tenant_id,
        hmac_secret=_WEBHOOK_SECRET,
        max_clock_skew_seconds=300,
        now=lambda: _FIXED_NOW,
    )
    payload = b"%PDF-1.4 api-push matrix payload"
    ts = str(_FIXED_NOW - 5)
    return adapter.enqueue(
        payload=payload,
        filename="matrix-api.pdf",
        signature=_sign_api_envelope(_WEBHOOK_SECRET, ts, payload),
        timestamp=ts,
    )


_PRODUCERS: dict[str, tuple[IntakeSourceType, object]] = {
    "email": (IntakeSourceType.EMAIL, _produce_email),
    "file_upload": (IntakeSourceType.FILE_UPLOAD, _produce_file),
    "folder_import": (IntakeSourceType.FOLDER_IMPORT, _produce_folder),
    "batch_import": (IntakeSourceType.BATCH_IMPORT, _produce_batch),
    "api_push": (IntakeSourceType.API_PUSH, _produce_api),
}


async def _cleanup_package(pool: asyncpg.Pool, package_id: UUID) -> None:
    async with pool.acquire() as conn, conn.transaction():
        await conn.execute(
            """
            DELETE FROM package_associations
            WHERE file_id IN (SELECT file_id FROM intake_files WHERE package_id = $1)
            """,
            package_id,
        )
        await conn.execute("DELETE FROM intake_descriptions WHERE package_id = $1", package_id)
        await conn.execute("DELETE FROM intake_files WHERE package_id = $1", package_id)
        await conn.execute("DELETE FROM intake_packages WHERE package_id = $1", package_id)


async def _matrix_case(
    source_type: str,
    tenant_id: str,
    storage_root: Path,
    policy_engine: PolicyEngine,
) -> None:
    expected, producer = _PRODUCERS[source_type]
    pkg = await producer(tenant_id, storage_root)  # type: ignore[operator]

    assert pkg.source_type == expected
    assert pkg.tenant_id == tenant_id
    assert len(pkg.files) >= 1
    for f in pkg.files:
        on_disk = Path(f.file_path)
        assert on_disk.exists(), f"{source_type}: file not materialized at {on_disk}"
        assert on_disk.stat().st_size == f.size_bytes
        assert hashlib.sha256(on_disk.read_bytes()).hexdigest() == f.sha256

    tenant_policy = policy_engine.get_for_tenant(tenant_id)
    assert tenant_policy is not None

    pool = await asyncpg.create_pool(_db_url(), min_size=1, max_size=2)
    try:
        repo = IntakeRepository(pool)
        # Phase 1d: persist via the canonical sink so the 037 CHECK trigger
        # sees `association_mode` populated for description-bearing packages
        # (email + file_upload). Folder/Batch/Api have no descriptions, so
        # the sink's resolver short-circuits and mode stays NULL — fine.
        sink = IntakePackageSink(repo=repo)
        await sink.handle(pkg)
        hydrated = await repo.get_package(pkg.package_id)
        assert hydrated is not None
        assert hydrated.package_id == pkg.package_id
        assert hydrated.source_type == expected
        assert hydrated.tenant_id == tenant_id
        assert len(hydrated.files) == len(pkg.files)

        orig_by_id = {f.file_id: f for f in pkg.files}
        for hf in hydrated.files:
            of = orig_by_id[hf.file_id]
            assert hf.sha256 == of.sha256
            assert hf.size_bytes == of.size_bytes
            assert hf.mime_type == of.mime_type
            assert hf.file_name == of.file_name
    finally:
        try:
            await _cleanup_package(pool, pkg.package_id)
        finally:
            await pool.close()


@pytest.mark.parametrize("source_type", sorted(_PRODUCERS.keys()))
def test_all_sources_produce_valid_intake_package(
    source_type: str,
    tmp_path: Path,
) -> None:
    """5-adapter matrix: each produces IntakePackage that survives DB round-trip."""
    tenant_id = f"tenant-e2e-matrix-{source_type}-{uuid4().hex[:6]}"
    storage_root = tmp_path / f"matrix_{source_type}"
    storage_root.mkdir(parents=True, exist_ok=True)
    policy_engine = PolicyEngine.from_yaml(PROFILE_A_PATH)
    asyncio.run(_matrix_case(source_type, tenant_id, storage_root, policy_engine))


# ---------------------------------------------------------------------------
# LEPES 2 — N4 association-mode round-trip
# ---------------------------------------------------------------------------


_shared_auth = AuthProvider.from_env()
_from_env_patcher = patch.object(AuthProvider, "from_env", return_value=_shared_auth)
_from_env_patcher.start()

from aiflow.api.app import create_app  # noqa: E402


@pytest.fixture(scope="module")
def _warmed_app(tmp_path_factory: pytest.TempPathFactory):
    os.environ.setdefault("AIFLOW_WEBHOOK_HMAC_SECRET", "placeholder-for-tests")
    upload_root = tmp_path_factory.mktemp("e2e_multi_source_uploads")
    os.environ["AIFLOW_INTAKE_UPLOAD_ROOT"] = str(upload_root)

    from aiflow.api import deps as _deps

    # asyncpg pool is loop-bound — reset so TestClient's lifespan creates it
    # on its own loop (feedback_asyncpg_pool_event_loop.md).
    _deps._pool = None
    app = create_app()
    with TestClient(app, raise_server_exceptions=False) as c:
        c.get("/health/live")
        yield c
    _deps._pool = None


@pytest.fixture()
def client(_warmed_app: TestClient) -> TestClient:
    return _warmed_app


def _auth_headers(tenant_id: str) -> dict[str, str]:
    token = _shared_auth.create_token(user_id="e2e-multi-user", role="admin", team_id=tenant_id)
    return {"Authorization": f"Bearer {token}"}


async def _cleanup_tenant(tenant_id: str) -> None:
    conn = await asyncpg.connect(_db_url())
    try:
        rows = await conn.fetch(
            "SELECT package_id FROM intake_packages WHERE tenant_id = $1", tenant_id
        )
        if not rows:
            return
        ids = [r["package_id"] for r in rows]
        async with conn.transaction():
            await conn.execute(
                """
                DELETE FROM package_associations
                WHERE file_id IN (SELECT file_id FROM intake_files WHERE package_id = ANY($1::uuid[]))
                """,
                ids,
            )
            await conn.execute(
                "DELETE FROM intake_descriptions WHERE package_id = ANY($1::uuid[])",
                ids,
            )
            await conn.execute("DELETE FROM intake_files WHERE package_id = ANY($1::uuid[])", ids)
            await conn.execute(
                "DELETE FROM intake_packages WHERE package_id = ANY($1::uuid[])", ids
            )
    finally:
        await conn.close()


async def _read_mode_and_assocs(
    package_id: UUID,
) -> tuple[str | None, dict[UUID, list[UUID]]]:
    conn = await asyncpg.connect(_db_url())
    try:
        mode = await conn.fetchval(
            "SELECT association_mode FROM intake_packages WHERE package_id = $1",
            package_id,
        )
        rows = await conn.fetch(
            """
            SELECT pa.description_id, pa.file_id
            FROM package_associations pa
            JOIN intake_files f ON f.file_id = pa.file_id
            WHERE f.package_id = $1
            """,
            package_id,
        )
    finally:
        await conn.close()

    assocs: dict[UUID, list[UUID]] = {}
    for r in rows:
        assocs.setdefault(r["description_id"], []).append(r["file_id"])
    return mode, assocs


def test_n4_association_modes_roundtrip(client: TestClient, tmp_path: Path) -> None:
    """All 4 AssociationMode values persist + hydrate correctly end-to-end."""
    # --- 1. ORDER (via HTTP endpoint, N==M==2) ------------------------------
    tenant_order = f"tenant-e2e-mode-order-{uuid4().hex[:6]}"
    try:
        resp = client.post(
            "/api/v1/intake/upload-package",
            headers=_auth_headers(tenant_order),
            files=[
                ("files", ("first.pdf", b"order-one", "application/pdf")),
                ("files", ("second.pdf", b"order-two", "application/pdf")),
            ],
            data={
                "descriptions": json.dumps([{"text": "first note"}, {"text": "second note"}]),
                "association_mode": "order",
            },
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["association_mode"] == "order"
        pkg_id = UUID(body["package_id"])

        mode, assocs = asyncio.run(_read_mode_and_assocs(pkg_id))
        assert mode == "order"
        assert len(assocs) == 2  # each description owns one file
        assert sum(len(v) for v in assocs.values()) == 2
    finally:
        asyncio.run(_cleanup_tenant(tenant_order))

    # --- 2. FILENAME_MATCH (via HTTP endpoint) ------------------------------
    tenant_filename = f"tenant-e2e-mode-filename-{uuid4().hex[:6]}"
    try:
        inv_id = str(uuid4())
        rec_id = str(uuid4())
        resp = client.post(
            "/api/v1/intake/upload-package",
            headers=_auth_headers(tenant_filename),
            files=[
                ("files", ("invoice-a.pdf", b"inv-a", "application/pdf")),
                ("files", ("invoice-b.pdf", b"inv-b", "application/pdf")),
                ("files", ("receipt-c.pdf", b"rec-c", "application/pdf")),
            ],
            data={
                "descriptions": json.dumps(
                    [
                        {"description_id": inv_id, "text": "invoices"},
                        {"description_id": rec_id, "text": "receipts"},
                    ]
                ),
                "association_mode": "filename_match",
                "filename_rules": json.dumps(
                    [
                        {"pattern": r"^invoice-", "description_id": inv_id},
                        {"pattern": r"^receipt-", "description_id": rec_id},
                    ]
                ),
            },
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["association_mode"] == "filename_match"
        pkg_id = UUID(body["package_id"])

        mode, assocs = asyncio.run(_read_mode_and_assocs(pkg_id))
        assert mode == "filename_match"
        assert len(assocs[UUID(inv_id)]) == 2
        assert len(assocs[UUID(rec_id)]) == 1
    finally:
        asyncio.run(_cleanup_tenant(tenant_filename))

    # --- 3. SINGLE_DESCRIPTION (via HTTP endpoint, auto-detected) ----------
    tenant_single = f"tenant-e2e-mode-single-{uuid4().hex[:6]}"
    try:
        resp = client.post(
            "/api/v1/intake/upload-package",
            headers=_auth_headers(tenant_single),
            files=[
                ("files", ("alpha.pdf", b"single-a", "application/pdf")),
                ("files", ("beta.pdf", b"single-b", "application/pdf")),
                ("files", ("gamma.pdf", b"single-c", "application/pdf")),
            ],
            data={
                "descriptions": json.dumps([{"text": "covers everything"}]),
                # Omit association_mode → auto-detect: EXPLICIT (fail, no map)
                # → FILENAME_MATCH (fail, no rules) → ORDER (fail, 3 != 1)
                # → SINGLE_DESCRIPTION (succeeds).
            },
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["association_mode"] == "single_description"
        pkg_id = UUID(body["package_id"])

        mode, assocs = asyncio.run(_read_mode_and_assocs(pkg_id))
        assert mode == "single_description"
        assert len(assocs) == 1
        only_desc_files = next(iter(assocs.values()))
        assert len(only_desc_files) == 3
    finally:
        asyncio.run(_cleanup_tenant(tenant_single))

    # --- 4. EXPLICIT (direct adapter path — HTTP form cannot bind file_ids) -
    tenant_explicit = f"tenant-e2e-mode-explicit-{uuid4().hex[:6]}"
    try:
        archive = _make_zip(
            {
                "contract-01.pdf": b"%PDF-1.4 contract one",
                "contract-02.pdf": b"%PDF-1.4 contract two",
            }
        )
        adapter = BatchSourceAdapter(
            storage_root=tmp_path / "explicit",
            tenant_id=tenant_explicit,
        )
        d_contract = IntakeDescription(text="contract batch")
        d_appendix = IntakeDescription(text="appendix batch")

        # BatchSourceAdapter without descriptions produces one package per file,
        # giving us stable server-assigned file_ids. We then build a merged
        # package + explicit_map manually so EXPLICIT can address those ids.
        raw_pkgs = adapter.enqueue(raw_bytes=archive, filename="contracts.zip")
        assert len(raw_pkgs) == 2
        merged = IntakePackage(
            source_type=IntakeSourceType.BATCH_IMPORT,
            tenant_id=tenant_explicit,
            files=[raw_pkgs[0].files[0], raw_pkgs[1].files[0]],
            descriptions=[d_contract, d_appendix],
            source_metadata={"origin": "e2e-explicit"},
        )

        explicit_map = {
            merged.files[0].file_id: d_contract.description_id,
            merged.files[1].file_id: d_appendix.description_id,
        }
        mapping = associate(merged, mode=AssociationMode.EXPLICIT, explicit_map=explicit_map)
        assert mapping == explicit_map

        desc_to_files: dict[UUID, list[UUID]] = {d.description_id: [] for d in merged.descriptions}
        for file_id, desc_id in mapping.items():
            desc_to_files[desc_id].append(file_id)
        for d in merged.descriptions:
            d.associated_file_ids = desc_to_files[d.description_id]
        merged.association_mode = AssociationMode.EXPLICIT

        async def _insert_and_fetch() -> IntakePackage | None:
            pool = await asyncpg.create_pool(_db_url(), min_size=1, max_size=2)
            try:
                repo = IntakeRepository(pool)
                await repo.insert_package(merged)
                return await repo.get_package(merged.package_id)
            finally:
                await pool.close()

        hydrated = asyncio.run(_insert_and_fetch())
        assert hydrated is not None
        assert hydrated.association_mode is AssociationMode.EXPLICIT
        hydrated_by_id = {d.description_id: d for d in hydrated.descriptions}
        assert hydrated_by_id[d_contract.description_id].associated_file_ids == [
            merged.files[0].file_id
        ]
        assert hydrated_by_id[d_appendix.description_id].associated_file_ids == [
            merged.files[1].file_id
        ]

        mode_row, _ = asyncio.run(_read_mode_and_assocs(merged.package_id))
        assert mode_row == "explicit"
    finally:
        asyncio.run(_cleanup_tenant(tenant_explicit))


# ---------------------------------------------------------------------------
# LEPES 3 — Phase 1a regression gate (backward-compat hard gate)
# ---------------------------------------------------------------------------


_PYTEST_SUMMARY_RE = re.compile(
    r"(?P<passed>\d+)\s+passed(?:,\s+(?P<warnings>\d+)\s+warnings?)?",
)


def test_phase_1a_regression_unchanged() -> None:
    """Phase 1a E2E suite (199 tests) stays fully green under Phase 1b changes."""
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/e2e/v1_4_0_phase_1a/",
        "-q",
        "--tb=no",
        "--no-header",
    ]
    env = {**os.environ, "PYTHONPATH": str(REPO_ROOT / "src")}
    result = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=600,
    )
    assert result.returncode == 0, (
        f"Phase 1a regression FAILED (exit={result.returncode}). stdout:\n{result.stdout[-4000:]}\nstderr:\n{result.stderr[-2000:]}"
    )

    match = _PYTEST_SUMMARY_RE.search(result.stdout)
    assert match is not None, (
        "could not parse pytest summary from stdout:\n" + result.stdout[-2000:]
    )
    passed = int(match.group("passed"))
    assert passed == 199, (
        f"Phase 1a regression count drifted: expected 199, got {passed}. "
        "Either un-skip was intentional (update this gate) or a test leaked in."
    )
