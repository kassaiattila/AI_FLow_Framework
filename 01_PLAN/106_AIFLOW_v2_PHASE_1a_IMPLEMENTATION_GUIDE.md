# AIFlow v2 Phase 1a — Implementation Guide (Onalló Vegrehajtasi Utmutato)

> **Verzio:** 1.0 (FINAL)
> **Datum:** 2026-04-09
> **Statusz:** AKTIV — Phase 1a (v1.4.0) sprint indulasra kesz
> **Master index:** `104_AIFLOW_v2_FINAL_MASTER_INDEX.md`
> **Cel:** **Ez az egyetlen dokumentum**, amit a fejlesztonek el kell olvasnia a Phase 1a
> elinditasahoz. Onalló, konkret, napra lebontott utmutato. Hivatkozik a reszletes forrasokra,
> de **onmagaban futtathato**.

> **Mikor kerul ez hasznalatra?** Sprint B (v1.3.0) befejezese utan, amikor a Phase 1a
> sprint kickoff-ja megkezdodik. A sprint kikerul egy uj branch-re (`feature/v1.4.0-phase-1a-foundation`).

---

## 0. TL;DR — Mit kell tennem?

1. **Olvasd el ezt a dokumentumot (60 perc)**
2. **Olvasd el a `100_b_AIFLOW_v2_DOMAIN_CONTRACTS.md`-t (30 perc)** — a 13 contract forras
3. **Olvasd el a `100_c_AIFLOW_v2_STATE_LIFECYCLE_MODEL.md`-t (15 perc)** — state machines
4. Kezdd a Day 1 feladatokkal (Section 4)
5. Ha elakadsz, nezd meg a `101_*`-ben a R/N komponens szekciojat

**Osszes olvasasi ido Phase 1a elott: ~2 ora.**

---

## 1. Kontextus 60 masodpercben

Az AIFlow v1.3.0-rol **v1.4.0**-ra lepunk. Ez a **Phase 1a (Foundation)** sprint — a
refinement terv (`100_*`) elso (negyedik resze).

**Amit MEGORZUNK:** Step + Workflow + Pipeline + Skill System + JobQueue + HumanReview +
PostgreSQL + pgvector + Langfuse + JWT RS256 — minden meglevo architektura.

**Amit HOZZAADUNK (Phase 1a-ban):**
1. **IntakePackage domain model** — multi-source intake unified entity
2. **State machines** (7 entitas) — idempotens replay + recovery
3. **PolicyEngine** (30+ parameter, profile + tenant override)
4. **ProviderRegistry** (4 ABC: parser/classifier/extractor/embedder)
5. **SkillInstance policy override** — per-instance konfig
6. **Backward compat shim layer** — meglevo pipeline-ok nem torik

**Amit NEM csinálunk Phase 1a-ban (későbbi sprintben):**
- Source adapter-ek (Phase 1b)
- document_extractor refactor (Phase 1c)
- Multi-signal routing engine (Phase 2a)
- Archival pipeline (Phase 2d)
- Vault prod impl (Phase 1.5)

**Phase 1a sprint cel:** 1 sprint (3-4 het), v1.4.0 tag.

---

## 2. Elofeltetelek (Day 0)

### 2.1 Sprint B befejezett?

- [ ] `feature/v1.3.0-service-excellence` branch merge-olve `main`-be
- [ ] v1.3.0 git tag letre
- [ ] `CLAUDE.md` + `01_PLAN/CLAUDE.md` key numbers frissitve
- [ ] `58_POST_SPRINT_HARDENING_PLAN.md` Sprint B = COMPLETE

### 2.2 Development environment kesz?

```bash
# Branch letrehozas
git checkout main
git pull
git checkout -b feature/v1.4.0-phase-1a-foundation

# Pre-migration backup (local dev DB)
docker exec aiflow_postgres pg_dump -U aiflow aiflow > backups/backup_pre_v1.4.0.sql

# Verify deps
uv sync --dev
python -c "import aiflow; print(aiflow.__version__)"
# Should print: 1.3.0

# Verify DB state
alembic current
# Should print: 029_session_recall (head)

# Smoke test baseline
pytest tests/unit/ -q  # all PASS
ruff check src/ tests/  # 0 errors
```

### 2.3 Team briefing kesz?

- [ ] Team reviewed `104_` + `100_` + `100_b_`
- [ ] Architect + lead engineer elhagyta a kickoff-ot
- [ ] Customer notification draft kesz (pre-migration uzenet, `100_d_` Section 9.1)

---

## 3. Sprint 1a — 4 heti breakdown

```
Week 1 — Contracts + State Machines
Week 2 — Policy + Provider Registry
Week 3 — SkillInstance + Backward Compat
Week 4 — Acceptance E2E + Docs + Demo
```

Reszletes napi bontas a Section 4-8-ban.

---

## 4. Week 1 — Contracts + State Machines (Day 1-5)

### Day 1 — Intake module scaffolding

**Feladat:** `src/aiflow/intake/` modul scaffolding + `IntakePackage` + `IntakeFile` + `IntakeDescription`.

#### 4.1.1 Fajlok letrehozasa

```bash
mkdir -p src/aiflow/intake
touch src/aiflow/intake/__init__.py
touch src/aiflow/intake/package.py
touch src/aiflow/intake/state_machine.py
touch src/aiflow/intake/exceptions.py
```

#### 4.1.2 `src/aiflow/intake/package.py` implementacio

**Forras:** `100_b_AIFLOW_v2_DOMAIN_CONTRACTS.md` Section 1

A teljes Pydantic kod a `100_b_*` dokumentumban talalhato — masolodj be **pontosan**, ne
modositsd:

- `IntakeSourceType` enum
- `IntakePackageStatus` enum (11 ertek)
- `DescriptionRole` enum
- `IntakeFile` BaseModel
- `IntakeDescription` BaseModel
- `IntakePackage` BaseModel + `validate_files_not_all_empty_with_descriptions` validator

**KRITIKUS**: `__all__` exports megadasa:

```python
__all__ = [
    "IntakeSourceType",
    "IntakePackageStatus",
    "DescriptionRole",
    "IntakeFile",
    "IntakeDescription",
    "IntakePackage",
]
```

#### 4.1.3 `src/aiflow/intake/exceptions.py`

```python
"""Intake-specific exceptions."""
from __future__ import annotations
from aiflow.core.errors import AIFlowError


__all__ = [
    "InvalidIntakePackageError",
    "InvalidStateTransitionError",
    "FileAssociationError",
]


class InvalidIntakePackageError(AIFlowError):
    is_transient = False


class InvalidStateTransitionError(AIFlowError):
    is_transient = False


class FileAssociationError(AIFlowError):
    is_transient = False
```

#### 4.1.4 Unit teszt scaffolding

```bash
mkdir -p tests/unit/intake
touch tests/unit/intake/__init__.py
touch tests/unit/intake/test_package.py
```

#### 4.1.5 `tests/unit/intake/test_package.py` — 10 teszt minimum

```python
"""IntakePackage Pydantic model tests."""
import pytest
from uuid import UUID, uuid4
from aiflow.intake.package import (
    IntakePackage,
    IntakeFile,
    IntakeDescription,
    IntakeSourceType,
    IntakePackageStatus,
    DescriptionRole,
)


def test_intake_package_minimal_creation():
    """Valid package with single file."""
    pkg = IntakePackage(
        source_type=IntakeSourceType.EMAIL,
        tenant_id="test_tenant",
        files=[IntakeFile(
            file_path="/tmp/test.pdf",
            file_name="test.pdf",
            mime_type="application/pdf",
            size_bytes=1024,
            sha256="a" * 64,
        )],
    )
    assert pkg.package_id is not None
    assert pkg.status == IntakePackageStatus.RECEIVED


def test_intake_package_requires_files_or_descriptions():
    """Empty package should fail validation."""
    with pytest.raises(ValueError, match="at least one file or one description"):
        IntakePackage(
            source_type=IntakeSourceType.EMAIL,
            tenant_id="test_tenant",
        )


def test_intake_file_sha256_lowercase():
    """SHA256 should be normalized to lowercase."""
    f = IntakeFile(
        file_path="/tmp/a.pdf",
        file_name="a.pdf",
        mime_type="application/pdf",
        size_bytes=100,
        sha256="A" * 64,
    )
    assert f.sha256 == "a" * 64


def test_intake_file_sha256_invalid_chars():
    """Non-hex characters should fail."""
    with pytest.raises(ValueError, match="lowercase hex"):
        IntakeFile(
            file_path="/tmp/a.pdf",
            file_name="a.pdf",
            mime_type="application/pdf",
            size_bytes=100,
            sha256="z" * 64,
        )


def test_intake_description_default_role():
    """Default role should be FREE_TEXT."""
    d = IntakeDescription(text="Some description")
    assert d.role == DescriptionRole.FREE_TEXT


def test_intake_description_association_confidence_bounds():
    """Association confidence must be 0..1."""
    with pytest.raises(ValueError):
        IntakeDescription(text="test", association_confidence=1.5)


def test_intake_package_with_descriptions_only():
    """Package with only descriptions (no files) should be valid."""
    pkg = IntakePackage(
        source_type=IntakeSourceType.API_PUSH,
        tenant_id="test",
        descriptions=[IntakeDescription(text="only description")],
    )
    assert len(pkg.descriptions) == 1


def test_intake_package_multi_source_metadata():
    """source_metadata should accept any dict."""
    pkg = IntakePackage(
        source_type=IntakeSourceType.EMAIL,
        tenant_id="test",
        files=[IntakeFile(
            file_path="/tmp/a.pdf", file_name="a.pdf",
            mime_type="application/pdf", size_bytes=100,
            sha256="a" * 64,
        )],
        source_metadata={
            "email_from": "user@example.com",
            "email_subject": "Invoice",
            "email_date": "2026-04-09T10:00:00Z",
        },
    )
    assert pkg.source_metadata["email_from"] == "user@example.com"


def test_intake_package_json_serializable():
    """Full serialization round-trip."""
    pkg = IntakePackage(
        source_type=IntakeSourceType.FILE_UPLOAD,
        tenant_id="test",
        files=[IntakeFile(
            file_path="/tmp/a.pdf", file_name="a.pdf",
            mime_type="application/pdf", size_bytes=100,
            sha256="b" * 64,
        )],
    )
    data = pkg.model_dump_json()
    restored = IntakePackage.model_validate_json(data)
    assert restored.package_id == pkg.package_id


def test_intake_package_provenance_chain_initial_empty():
    """provenance_chain default is empty list."""
    pkg = IntakePackage(
        source_type=IntakeSourceType.BATCH_IMPORT,
        tenant_id="test",
        descriptions=[IntakeDescription(text="batch")],
    )
    assert pkg.provenance_chain == []
```

#### 4.1.6 Day 1 acceptance

```bash
pytest tests/unit/intake/ -v
# 10+ test PASS
ruff check src/aiflow/intake/
# 0 errors
python -c "from aiflow.intake.package import IntakePackage; print('OK')"
```

#### 4.1.7 Day 1 commit

```bash
git add src/aiflow/intake/ tests/unit/intake/
git commit -m "feat(intake): Phase 1a Day 1 — IntakePackage + IntakeFile + IntakeDescription contracts

- Add src/aiflow/intake/ module scaffolding
- Implement IntakePackage, IntakeFile, IntakeDescription Pydantic v2 models
- Implement IntakeSourceType, IntakePackageStatus, DescriptionRole enums
- Add validators (sha256 lowercase hex, non-empty package)
- Add 10 unit tests (minimal + validation + serialization)
- Source: 100_b_AIFLOW_v2_DOMAIN_CONTRACTS.md Section 1

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Day 2 — State machine implementation

**Feladat:** `IntakePackageStatus` allapotgep + transition validator + 6 egyeb entitas state enum.

**Forras:** `100_c_AIFLOW_v2_STATE_LIFECYCLE_MODEL.md` Sections 1-7

#### 4.2.1 `src/aiflow/intake/state_machine.py`

```python
"""State machine for IntakePackage + per-file/artifact lifecycle."""
from __future__ import annotations

from aiflow.intake.package import IntakePackageStatus
from aiflow.intake.exceptions import InvalidStateTransitionError


__all__ = [
    "VALID_PACKAGE_TRANSITIONS",
    "validate_package_transition",
    "is_terminal_status",
]


# Forras: 100_c_*.md Section 1.3 table
VALID_PACKAGE_TRANSITIONS: dict[IntakePackageStatus, set[IntakePackageStatus]] = {
    IntakePackageStatus.RECEIVED: {IntakePackageStatus.NORMALIZED, IntakePackageStatus.FAILED},
    IntakePackageStatus.NORMALIZED: {IntakePackageStatus.ROUTED, IntakePackageStatus.FAILED},
    IntakePackageStatus.ROUTED: {IntakePackageStatus.PARSED, IntakePackageStatus.FAILED},  # "PARSING" a workflow szintje
    IntakePackageStatus.PARSED: {IntakePackageStatus.CLASSIFIED, IntakePackageStatus.FAILED},
    IntakePackageStatus.CLASSIFIED: {IntakePackageStatus.EXTRACTED, IntakePackageStatus.REVIEW_PENDING, IntakePackageStatus.FAILED},
    IntakePackageStatus.EXTRACTED: {IntakePackageStatus.REVIEW_PENDING, IntakePackageStatus.ARCHIVED, IntakePackageStatus.FAILED},
    IntakePackageStatus.REVIEW_PENDING: {IntakePackageStatus.REVIEWED, IntakePackageStatus.FAILED},
    IntakePackageStatus.REVIEWED: {IntakePackageStatus.EXTRACTED, IntakePackageStatus.ARCHIVED, IntakePackageStatus.FAILED},
    IntakePackageStatus.ARCHIVED: set(),  # final
    IntakePackageStatus.FAILED: {IntakePackageStatus.RECEIVED, IntakePackageStatus.NORMALIZED},  # resume
    IntakePackageStatus.QUARANTINED: set(),  # final (admin unblock külön kod)
}


TERMINAL_STATUSES = {
    IntakePackageStatus.ARCHIVED,
    IntakePackageStatus.QUARANTINED,
}


def validate_package_transition(
    from_status: IntakePackageStatus,
    to_status: IntakePackageStatus,
) -> None:
    """Raise InvalidStateTransitionError if transition is not valid."""
    allowed = VALID_PACKAGE_TRANSITIONS.get(from_status, set())
    if to_status not in allowed:
        raise InvalidStateTransitionError(
            f"Invalid transition: {from_status.value} → {to_status.value}. "
            f"Allowed: {[s.value for s in allowed] if allowed else 'terminal (no transitions)'}"
        )


def is_terminal_status(status: IntakePackageStatus) -> bool:
    return status in TERMINAL_STATUSES
```

#### 4.2.2 Teszt (~8 teszt minimum)

```python
# tests/unit/intake/test_state_machine.py
import pytest
from aiflow.intake.package import IntakePackageStatus
from aiflow.intake.state_machine import (
    validate_package_transition,
    is_terminal_status,
)
from aiflow.intake.exceptions import InvalidStateTransitionError


def test_valid_happy_path_transitions():
    """Happy path transition chain."""
    chain = [
        (IntakePackageStatus.RECEIVED, IntakePackageStatus.NORMALIZED),
        (IntakePackageStatus.NORMALIZED, IntakePackageStatus.ROUTED),
        (IntakePackageStatus.ROUTED, IntakePackageStatus.PARSED),
        (IntakePackageStatus.PARSED, IntakePackageStatus.CLASSIFIED),
        (IntakePackageStatus.CLASSIFIED, IntakePackageStatus.EXTRACTED),
        (IntakePackageStatus.EXTRACTED, IntakePackageStatus.ARCHIVED),
    ]
    for from_s, to_s in chain:
        validate_package_transition(from_s, to_s)  # no exception


def test_invalid_transition_raises():
    """Skipping states should fail."""
    with pytest.raises(InvalidStateTransitionError):
        validate_package_transition(
            IntakePackageStatus.RECEIVED,
            IntakePackageStatus.EXTRACTED,
        )


def test_terminal_statuses_no_further():
    """ARCHIVED has no further transitions."""
    with pytest.raises(InvalidStateTransitionError):
        validate_package_transition(
            IntakePackageStatus.ARCHIVED,
            IntakePackageStatus.EXTRACTED,
        )


def test_failed_can_resume_to_received():
    """FAILED → RECEIVED (resume) is valid."""
    validate_package_transition(
        IntakePackageStatus.FAILED,
        IntakePackageStatus.RECEIVED,
    )


def test_review_pending_branch():
    """EXTRACTED → REVIEW_PENDING → REVIEWED → ARCHIVED."""
    validate_package_transition(IntakePackageStatus.EXTRACTED, IntakePackageStatus.REVIEW_PENDING)
    validate_package_transition(IntakePackageStatus.REVIEW_PENDING, IntakePackageStatus.REVIEWED)
    validate_package_transition(IntakePackageStatus.REVIEWED, IntakePackageStatus.ARCHIVED)


def test_is_terminal_status():
    assert is_terminal_status(IntakePackageStatus.ARCHIVED) is True
    assert is_terminal_status(IntakePackageStatus.QUARANTINED) is True
    assert is_terminal_status(IntakePackageStatus.RECEIVED) is False


def test_any_state_to_failed():
    """Any non-terminal state should be transitionable to FAILED."""
    # NOTE: implementacio lehetseges — de explicit-en a VALID_PACKAGE_TRANSITIONS-ben
    validate_package_transition(IntakePackageStatus.PARSED, IntakePackageStatus.FAILED)
    validate_package_transition(IntakePackageStatus.EXTRACTED, IntakePackageStatus.FAILED)


def test_reviewed_can_re_extract():
    """REVIEWED → EXTRACTED (re-extract after review correction)."""
    validate_package_transition(
        IntakePackageStatus.REVIEWED,
        IntakePackageStatus.EXTRACTED,
    )
```

#### 4.2.3 Day 2 commit

```bash
git add src/aiflow/intake/state_machine.py tests/unit/intake/test_state_machine.py
git commit -m "feat(intake): Phase 1a Day 2 — IntakePackage state machine + transition validator

- Add VALID_PACKAGE_TRANSITIONS map (100_c_*.md Section 1.3)
- Add validate_package_transition() with InvalidStateTransitionError
- Add is_terminal_status() helper
- Add 8 unit tests (happy path, invalid, terminal, resume, review branch)
- Source: 100_c_AIFLOW_v2_STATE_LIFECYCLE_MODEL.md Section 1

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Day 3 — Alembic migration 030 (intake tables)

**Feladat:** DB schema: `intake_packages`, `intake_files`, `intake_descriptions`, `package_associations`.

**Forras:** `100_d_AIFLOW_v2_MIGRATION_PLAYBOOK.md` Section 2

#### 4.3.1 Uj migration

```bash
# Generate skeleton
cd src/aiflow/state
alembic revision -m "Phase 1a: intake tables (packages, files, descriptions, associations)"
# Creates: migrations/versions/<hash>_phase_1a_intake_tables.py
```

#### 4.3.2 Migration content

```python
"""Phase 1a: intake tables

Revision ID: 030_intake_tables
Revises: 029_session_recall
Create Date: 2026-04-15 ...
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "030_intake_tables"
down_revision = "029_session_recall"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # intake_packages
    op.create_table(
        "intake_packages",
        sa.Column("package_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="received"),
        sa.Column("source_metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("package_context", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("cross_document_signals", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column("received_by", sa.String(255), nullable=True),
        sa.Column("provenance_chain", postgresql.ARRAY(postgresql.UUID()), nullable=False, server_default="{}"),
        sa.Column("routing_decision_id", postgresql.UUID(), nullable=True),
        sa.Column("review_task_id", postgresql.UUID(), nullable=True),
    )
    op.create_index("idx_intake_packages_tenant", "intake_packages", ["tenant_id"])
    op.create_index("idx_intake_packages_status", "intake_packages", ["status"])
    op.create_index("idx_intake_packages_created", "intake_packages", ["created_at"])

    # intake_files
    op.create_table(
        "intake_files",
        sa.Column("file_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "package_id",
            postgresql.UUID(),
            sa.ForeignKey("intake_packages.package_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("file_name", sa.String(500), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("source_metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("sequence_index", sa.Integer(), nullable=True),
    )
    op.create_index("idx_intake_files_package", "intake_files", ["package_id"])
    op.create_index("idx_intake_files_sha256", "intake_files", ["sha256"])

    # intake_descriptions
    op.create_table(
        "intake_descriptions",
        sa.Column("description_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "package_id",
            postgresql.UUID(),
            sa.ForeignKey("intake_packages.package_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("language", sa.String(10), nullable=True),
        sa.Column("role", sa.String(50), nullable=False, server_default="free_text"),
        sa.Column("association_confidence", sa.Float(), nullable=True),
        sa.Column("association_method", sa.String(50), nullable=True),
    )
    op.create_index("idx_intake_descriptions_package", "intake_descriptions", ["package_id"])

    # package_associations (file ↔ description many-to-many)
    op.create_table(
        "package_associations",
        sa.Column("file_id", postgresql.UUID(), sa.ForeignKey("intake_files.file_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("description_id", postgresql.UUID(), sa.ForeignKey("intake_descriptions.description_id", ondelete="CASCADE"), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table("package_associations")
    op.drop_index("idx_intake_descriptions_package", table_name="intake_descriptions")
    op.drop_table("intake_descriptions")
    op.drop_index("idx_intake_files_sha256", table_name="intake_files")
    op.drop_index("idx_intake_files_package", table_name="intake_files")
    op.drop_table("intake_files")
    op.drop_index("idx_intake_packages_created", table_name="intake_packages")
    op.drop_index("idx_intake_packages_status", table_name="intake_packages")
    op.drop_index("idx_intake_packages_tenant", table_name="intake_packages")
    op.drop_table("intake_packages")
```

#### 4.3.3 Migration teszt

```bash
# Fresh DB test
alembic upgrade head
alembic current  # should print 030_intake_tables

# Data insert test
psql aiflow -c "INSERT INTO intake_packages (package_id, source_type, tenant_id) VALUES (gen_random_uuid(), 'email', 'test');"

# Downgrade test
alembic downgrade 029_session_recall
alembic current  # back to 029

# Re-upgrade
alembic upgrade head
```

#### 4.3.4 Day 3 commit

```bash
git add src/aiflow/state/migrations/versions/030_*.py
git commit -m "feat(db): Phase 1a Day 3 — alembic 030 intake tables

- Add intake_packages, intake_files, intake_descriptions, package_associations
- Add indexes: tenant_id, status, created_at, sha256
- Foreign keys: files/descriptions → packages (ON DELETE CASCADE)
- Tested upgrade + downgrade + re-upgrade cycle
- Source: 100_d_AIFLOW_v2_MIGRATION_PLAYBOOK.md Section 2

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Day 4-5 — Repository layer + IntakeNormalizationLayer

**Feladat:**
1. `src/aiflow/state/repositories/intake.py` — CRUD repository
2. `src/aiflow/intake/normalization.py` — `IntakeNormalizationLayer` (N3)

**Forras:** `101_AIFLOW_v2_COMPONENT_TRANSFORMATION_PLAN.md` N3 szekcio

#### 4.4.1 `src/aiflow/state/repositories/intake.py`

```python
"""IntakePackage repository (asyncpg-based)."""
from __future__ import annotations

from uuid import UUID
import asyncpg
from aiflow.intake.package import IntakePackage, IntakeFile, IntakeDescription, IntakePackageStatus
from aiflow.intake.state_machine import validate_package_transition
from aiflow.observability.logging import get_logger


__all__ = ["IntakeRepository"]


logger = get_logger(__name__)


class IntakeRepository:
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    async def insert_package(self, package: IntakePackage) -> None:
        """Insert a new package + files + descriptions atomically."""
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("""
                    INSERT INTO intake_packages (
                        package_id, source_type, tenant_id, status,
                        source_metadata, package_context, cross_document_signals,
                        created_at, updated_at, received_by, provenance_chain
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                """,
                    package.package_id, package.source_type.value, package.tenant_id,
                    package.status.value, package.source_metadata, package.package_context,
                    package.cross_document_signals, package.created_at, package.updated_at,
                    package.received_by, package.provenance_chain,
                )
                for f in package.files:
                    await conn.execute("""
                        INSERT INTO intake_files (
                            file_id, package_id, file_path, file_name, mime_type,
                            size_bytes, sha256, source_metadata, sequence_index
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    """,
                        f.file_id, package.package_id, f.file_path, f.file_name,
                        f.mime_type, f.size_bytes, f.sha256, f.source_metadata, f.sequence_index,
                    )
                for d in package.descriptions:
                    await conn.execute("""
                        INSERT INTO intake_descriptions (
                            description_id, package_id, text, language, role,
                            association_confidence, association_method
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                        d.description_id, package.package_id, d.text, d.language,
                        d.role.value, d.association_confidence, d.association_method,
                    )
        logger.info("intake_package_inserted", package_id=str(package.package_id))

    async def get_package(self, package_id: UUID) -> IntakePackage | None:
        """Get a package with all files + descriptions."""
        # Implementacio: fetch package + files + descriptions + rebuild Pydantic
        pass  # TODO Day 5

    async def transition_status(
        self,
        package_id: UUID,
        new_status: IntakePackageStatus,
    ) -> None:
        """Atomic status transition with validation."""
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                current = await conn.fetchval(
                    "SELECT status FROM intake_packages WHERE package_id = $1 FOR UPDATE",
                    package_id,
                )
                if current is None:
                    raise ValueError(f"Package {package_id} not found")

                current_status = IntakePackageStatus(current)
                if current_status == new_status:
                    logger.info("idempotent_skip", from_status=current, to_status=new_status.value)
                    return

                validate_package_transition(current_status, new_status)
                await conn.execute(
                    "UPDATE intake_packages SET status = $1, updated_at = NOW() WHERE package_id = $2",
                    new_status.value,
                    package_id,
                )
        logger.info(
            "package_status_transitioned",
            package_id=str(package_id),
            from_status=current_status.value,
            to_status=new_status.value,
        )
```

#### 4.4.2 `src/aiflow/intake/normalization.py`

Forras: `101_*` N3 szekcio. Kis modul, egyszerű.

```python
"""Intake normalization layer."""
from __future__ import annotations

import hashlib
import mimetypes
from pathlib import Path
from uuid import uuid4

from aiflow.intake.package import (
    IntakePackage, IntakeFile, IntakeDescription,
    IntakeSourceType, IntakePackageStatus,
)


__all__ = ["IntakeNormalizationLayer"]


class IntakeNormalizationLayer:
    """Normalize raw source data to canonical IntakePackage."""

    def detect_mime(self, file_path: Path) -> str:
        mime, _ = mimetypes.guess_type(str(file_path))
        return mime or "application/octet-stream"

    def compute_sha256(self, file_path: Path) -> str:
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    def normalize_file_upload(
        self,
        tenant_id: str,
        files: list[Path],
        descriptions: list[str] | None = None,
    ) -> IntakePackage:
        """Create IntakePackage from uploaded files + optional descriptions."""
        intake_files = [
            IntakeFile(
                file_path=str(f.absolute()),
                file_name=f.name,
                mime_type=self.detect_mime(f),
                size_bytes=f.stat().st_size,
                sha256=self.compute_sha256(f),
                sequence_index=i,
            )
            for i, f in enumerate(files)
        ]
        intake_descs = [
            IntakeDescription(text=d) for d in (descriptions or [])
        ]
        return IntakePackage(
            source_type=IntakeSourceType.FILE_UPLOAD,
            tenant_id=tenant_id,
            files=intake_files,
            descriptions=intake_descs,
            status=IntakePackageStatus.NORMALIZED,
        )

    # normalize_email, normalize_folder, normalize_batch, normalize_api
    # → Phase 1b-ben (Day 11+)
```

#### 4.4.3 Tesztek

- `tests/unit/state/test_intake_repository.py` — insert, get, transition (5+ teszt)
- `tests/unit/intake/test_normalization.py` — mime, sha256, file_upload (5+ teszt)

#### 4.4.4 Day 4-5 commit

```bash
git add src/aiflow/state/repositories/intake.py src/aiflow/intake/normalization.py tests/unit/
git commit -m "feat(intake): Phase 1a Day 4-5 — IntakeRepository + IntakeNormalizationLayer

- Add IntakeRepository: atomic insert + get + status transition
- Add IntakeNormalizationLayer: mime detection + sha256 + file_upload normalize
- Integration with validate_package_transition() for atomic transitions
- Add 10+ unit tests (repository + normalization)
- Source: 101_*.md N3 section

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## 5. Week 2 — Policy Engine + Provider Registry (Day 6-10)

### Day 6-7 — PolicyEngine + profile config files

**Feladat:** `src/aiflow/policy/engine.py` + `config/profiles/profile_a.yaml` + `profile_b.yaml`.

**Forras:** `100_` Section 6 + `101_` N5

#### 5.1 `src/aiflow/policy/engine.py` skeleton

```python
"""Policy engine with profile + tenant override support."""
from __future__ import annotations

from pathlib import Path
from typing import Any
import yaml
from pydantic import BaseModel, Field


__all__ = ["PolicyEngine", "PolicyConfig"]


class PolicyConfig(BaseModel):
    """Policy parameters (30+ fields)."""
    cloud_ai_allowed: bool = False
    cloud_storage_allowed: bool = False
    document_content_may_leave_tenant: bool = False
    embedding_enabled: bool = True
    pii_embedding_allowed: bool = False
    self_hosted_parsing_enabled: bool = True
    azure_di_enabled: bool = False
    azure_search_enabled: bool = False
    azure_embedding_enabled: bool = False
    archival_pdfa_required: bool = True
    pdfa_validation_required: bool = True
    manual_review_confidence_threshold: float = 0.70
    default_parser_provider: str = "docling_standard"
    default_classifier_provider: str = "hybrid_ml_llm"
    default_extractor_provider: str = "llm_field_extract"
    default_embedding_provider: str = "bge_m3"
    vector_store_provider: str = "pgvector"
    object_store_provider: str = "local_fs"
    tenant_override_enabled: bool = True
    fallback_provider_order: dict = Field(default_factory=dict)
    docling_vlm_enabled: bool = False
    qwen_vllm_enabled: bool = False
    self_hosted_embedding_model: str = "BAAI/bge-m3"
    azure_embedding_model: str = ""
    redaction_before_embedding_required: bool = True
    source_adapter_type: str = "unified"
    intake_package_enabled: bool = True
    source_text_ingestion_enabled: bool = True
    file_description_association_mode: str = "rule_first_llm_fallback"
    package_level_context_enabled: bool = True
    cross_document_context_enabled: bool = True
    daily_document_cap: int | None = None
    daily_document_hard_cap: int | None = None


class PolicyEngine:
    def __init__(self, profile_config: PolicyConfig, tenant_overrides: dict[str, dict] | None = None):
        self.profile_config = profile_config
        self.tenant_overrides = tenant_overrides or {}

    @classmethod
    def from_yaml(cls, profile_path: Path) -> "PolicyEngine":
        """Load from profile YAML (config/profiles/profile_a.yaml)."""
        with open(profile_path) as f:
            data = yaml.safe_load(f)
        return cls(profile_config=PolicyConfig(**data.get("policy", {})))

    def get_for_tenant(self, tenant_id: str) -> PolicyConfig:
        """Return merged config (profile + tenant override)."""
        override = self.tenant_overrides.get(tenant_id, {})
        if not override:
            return self.profile_config
        merged = self.profile_config.model_dump()
        merged.update(override)
        return PolicyConfig(**merged)

    def is_allowed(self, capability: str, tenant_id: str | None = None) -> bool:
        """Check if a capability is allowed under current policy."""
        cfg = self.get_for_tenant(tenant_id) if tenant_id else self.profile_config
        return getattr(cfg, capability, False)

    def get_default_provider(self, provider_type: str, tenant_id: str | None = None) -> str:
        """Return default provider for parser/classifier/extractor/embedder."""
        cfg = self.get_for_tenant(tenant_id) if tenant_id else self.profile_config
        return getattr(cfg, f"default_{provider_type}_provider", "")
```

#### 5.2 `config/profiles/profile_a.yaml`

```yaml
# Profile A — Cloud-disallowed (on-prem air-gapped)
# Forras: 100_*.md Section 6

policy:
  cloud_ai_allowed: false
  cloud_storage_allowed: false
  document_content_may_leave_tenant: false
  embedding_enabled: true
  pii_embedding_allowed: false
  self_hosted_parsing_enabled: true
  azure_di_enabled: false
  azure_search_enabled: false
  azure_embedding_enabled: false
  archival_pdfa_required: true
  pdfa_validation_required: true
  manual_review_confidence_threshold: 0.70
  default_parser_provider: docling_standard
  default_classifier_provider: hybrid_ml_llm
  default_extractor_provider: llm_field_extract
  default_embedding_provider: bge_m3
  vector_store_provider: pgvector
  object_store_provider: local_fs
  tenant_override_enabled: true
  fallback_provider_order:
    parser: [pymupdf4llm, docling_standard, docling_vlm]
    embedder: [bge_m3, e5_large]
  docling_vlm_enabled: false
  qwen_vllm_enabled: false
  self_hosted_embedding_model: BAAI/bge-m3
  azure_embedding_model: ""
  redaction_before_embedding_required: true
  source_adapter_type: unified
  intake_package_enabled: true
  source_text_ingestion_enabled: true
  file_description_association_mode: rule_first_llm_fallback
  package_level_context_enabled: true
  cross_document_context_enabled: true
  daily_document_cap: 500
  daily_document_hard_cap: 1800
```

#### 5.3 `config/profiles/profile_b.yaml`

```yaml
# Profile B — Cloud-allowed (Azure-optimized)

policy:
  cloud_ai_allowed: true
  cloud_storage_allowed: true
  document_content_may_leave_tenant: true
  azure_di_enabled: true
  azure_search_enabled: true
  azure_embedding_enabled: true
  default_parser_provider: docling_standard
  default_embedding_provider: azure_openai_embedding_3_small
  azure_embedding_model: text-embedding-3-small
  vector_store_provider: pgvector
  object_store_provider: azure_blob
  pii_embedding_allowed: false
  redaction_before_embedding_required: true
  # a tobbi orokli a profile_a default-et
```

#### 5.4 Tesztek (10+)

- profile_a load + getattr-ek
- profile_b load + getattr-ek
- tenant_override: cloud_ai_allowed OFF → ON
- is_allowed(): azure_di_enabled
- get_default_provider(): parser, embedder
- Pydantic validation error if invalid

#### 5.5 Day 6-7 commit

```bash
git add src/aiflow/policy/ config/profiles/ tests/unit/policy/
git commit -m "feat(policy): Phase 1a Day 6-7 — PolicyEngine + 2 profile config files

- Add PolicyConfig Pydantic (30+ parameter)
- Add PolicyEngine with profile loading + tenant override
- Add config/profiles/profile_a.yaml (cloud-disallowed)
- Add config/profiles/profile_b.yaml (Azure-optimized)
- Add 10+ unit tests (profile load, tenant override, is_allowed)
- Source: 100_*.md Section 6 + 101_*.md N5

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Day 8-9 — ProviderRegistry + 4 ABC

**Feladat:** `src/aiflow/providers/` modul + `ParserProvider`, `ClassifierProvider`, `ExtractorProvider`, `EmbedderProvider` ABC-k.

**Forras:** `103_*` Section 5.1 (provider abstraction contract)

```bash
mkdir -p src/aiflow/providers
touch src/aiflow/providers/{__init__.py,registry.py,interfaces.py,metadata.py}
mkdir -p tests/integration/providers
touch tests/integration/providers/{__init__.py,test_contract.py}
```

#### 5.6 `src/aiflow/providers/metadata.py`

```python
"""Provider metadata model."""
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel


__all__ = ["ProviderMetadata"]


class ProviderMetadata(BaseModel):
    name: str
    version: str
    supported_types: list[str]
    speed_class: Literal["fast", "normal", "slow"]
    gpu_required: bool = False
    cost_class: Literal["free", "cheap", "moderate", "expensive"]
    license: str  # AGPL, MIT, commercial, proprietary
```

#### 5.7 `src/aiflow/providers/interfaces.py`

Forras: `103_*` Section 5.1 — **pontos masolat**.

```python
"""Provider ABCs — parser, classifier, extractor, embedder."""
from __future__ import annotations
from abc import ABC, abstractmethod

from aiflow.intake.package import IntakeFile, IntakePackage
from aiflow.providers.metadata import ProviderMetadata


__all__ = [
    "ParserProvider",
    "ClassifierProvider",
    "ExtractorProvider",
    "EmbedderProvider",
]


class ParserProvider(ABC):
    @property
    @abstractmethod
    def metadata(self) -> ProviderMetadata: ...

    @abstractmethod
    async def parse(
        self,
        file: IntakeFile,
        package_context: IntakePackage,
    ) -> "ParserResult": ...

    @abstractmethod
    async def health_check(self) -> bool: ...

    @abstractmethod
    async def estimate_cost(self, file: IntakeFile) -> float: ...


class ClassifierProvider(ABC):
    @property
    @abstractmethod
    def metadata(self) -> ProviderMetadata: ...

    @abstractmethod
    async def classify(
        self,
        file: IntakeFile,
        parser_result: "ParserResult",
        candidate_classes: list[str],
    ) -> "ClassificationResult": ...

    @abstractmethod
    async def health_check(self) -> bool: ...


class ExtractorProvider(ABC):
    @property
    @abstractmethod
    def metadata(self) -> ProviderMetadata: ...

    @abstractmethod
    async def extract(
        self,
        file: IntakeFile,
        parser_result: "ParserResult",
        config: dict,  # DocumentTypeConfig — Phase 2c
    ) -> "ExtractionResult": ...


class EmbedderProvider(ABC):
    @property
    @abstractmethod
    def metadata(self) -> ProviderMetadata: ...

    @property
    @abstractmethod
    def dimensions(self) -> int: ...

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]: ...

    @abstractmethod
    async def health_check(self) -> bool: ...
```

> **Megjegyzes:** A `ParserResult`, `ClassificationResult`, `ExtractionResult` stringként
> jelenek meg — a teljes Pydantic definiciok a `100_b_*` Section 3-5 alatt, de azok
> implementacioja (`src/aiflow/providers/results.py`) Phase 1b/2-ben lesz (Phase 1a-ban
> NEM szuksegesek — csak az interface kell).

#### 5.8 `src/aiflow/providers/registry.py`

```python
"""Provider registry."""
from __future__ import annotations

from aiflow.providers.interfaces import (
    ParserProvider, ClassifierProvider, ExtractorProvider, EmbedderProvider,
)


__all__ = ["ProviderRegistry"]


class ProviderRegistry:
    def __init__(self):
        self._parsers: dict[str, type[ParserProvider]] = {}
        self._classifiers: dict[str, type[ClassifierProvider]] = {}
        self._extractors: dict[str, type[ExtractorProvider]] = {}
        self._embedders: dict[str, type[EmbedderProvider]] = {}

    def register_parser(self, name: str, provider_cls: type[ParserProvider]) -> None:
        if not issubclass(provider_cls, ParserProvider):
            raise TypeError(f"{provider_cls} must implement ParserProvider")
        self._parsers[name] = provider_cls

    def register_embedder(self, name: str, provider_cls: type[EmbedderProvider]) -> None:
        if not issubclass(provider_cls, EmbedderProvider):
            raise TypeError(f"{provider_cls} must implement EmbedderProvider")
        self._embedders[name] = provider_cls

    def get_parser(self, name: str) -> type[ParserProvider]:
        if name not in self._parsers:
            raise KeyError(f"Parser provider '{name}' not registered. Available: {list(self._parsers.keys())}")
        return self._parsers[name]

    def list_parsers(self) -> list[str]:
        return sorted(self._parsers.keys())

    # register_classifier, register_extractor, get_classifier, get_extractor, get_embedder, list_*
    # → hasonlo minta
```

#### 5.9 Contract test framework

```python
# tests/integration/providers/test_contract.py
"""Contract tests — every provider MUST pass these."""
import pytest
from aiflow.providers.interfaces import ParserProvider, EmbedderProvider


# Phase 1a-ban UK meg nincs konkret provider implementacio — ez a framework csak scaffold
# Phase 1b-tol itt kerulnek parametricke a valos providerek


class _DummyParserProvider(ParserProvider):
    """Test fixture — dummy parser for contract test framework validation."""
    @property
    def metadata(self):
        from aiflow.providers.metadata import ProviderMetadata
        return ProviderMetadata(
            name="dummy", version="0.0.1", supported_types=["pdf"],
            speed_class="fast", gpu_required=False, cost_class="free",
            license="MIT",
        )

    async def parse(self, file, package_context):
        return None  # placeholder

    async def health_check(self):
        return True

    async def estimate_cost(self, file):
        return 0.0


class TestParserProviderContract:
    """Every ParserProvider MUST pass these."""

    @pytest.fixture
    def provider(self):
        return _DummyParserProvider()

    def test_metadata_present(self, provider):
        meta = provider.metadata
        assert meta.name
        assert meta.version
        assert meta.supported_types

    def test_metadata_pydantic_valid(self, provider):
        from aiflow.providers.metadata import ProviderMetadata
        meta = provider.metadata
        assert isinstance(meta, ProviderMetadata)

    @pytest.mark.asyncio
    async def test_health_check_runs(self, provider):
        result = await provider.health_check()
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_estimate_cost_returns_float(self, provider):
        from aiflow.intake.package import IntakeFile
        f = IntakeFile(
            file_path="/tmp/x.pdf", file_name="x.pdf",
            mime_type="application/pdf", size_bytes=100,
            sha256="c" * 64,
        )
        cost = await provider.estimate_cost(f)
        assert isinstance(cost, (int, float))
        assert cost >= 0
```

#### 5.10 Day 8-9 commit

```bash
git add src/aiflow/providers/ tests/integration/providers/
git commit -m "feat(providers): Phase 1a Day 8-9 — ProviderRegistry + 4 ABC + contract test framework

- Add ProviderMetadata Pydantic model
- Add ParserProvider, ClassifierProvider, ExtractorProvider, EmbedderProvider ABCs
- Add ProviderRegistry with register_*/get_*/list_* methods
- Add contract test framework with dummy provider fixture
- Source: 103_*.md Section 5.1

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Day 10 — Alembic 031 (policy_overrides) + PolicyEngine DB integration

**Feladat:** `policy_overrides` tabla + `PolicyEngine.load_tenant_overrides_from_db()`.

```python
# alembic 031
op.create_table(
    "policy_overrides",
    sa.Column("override_id", postgresql.UUID(as_uuid=True), primary_key=True),
    sa.Column("tenant_id", sa.String(255), nullable=False),
    sa.Column("instance_id", sa.String(255), nullable=True),  # opcionalis per-instance
    sa.Column("policy_json", postgresql.JSONB(), nullable=False),
    sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
)
op.create_index("idx_policy_overrides_tenant", "policy_overrides", ["tenant_id"])
op.create_unique_constraint(
    "uq_policy_overrides_tenant_instance",
    "policy_overrides",
    ["tenant_id", "instance_id"],
)
```

Day 10 commit, Week 2 kesz.

---

## 6. Week 3 — SkillInstance + Backward Compat Shim (Day 11-15)

### Day 11-12 — R13: SkillInstance policy_override

**Forras:** `101_*` R13

- `src/aiflow/skill_system/instance.py`: `SkillInstanceConfig.policy_override: dict | None`
- `src/aiflow/skill_system/instance_loader.py`: load `instances/{customer}/policy.yaml`
- Teszt: multi-instance override + merge check

### Day 13-14 — Backward compat shim layer

**Forras:** `100_d_*` Section 4

**Ket szint:**
1. `services/document_extractor.extract(file_path)` → single-file package shim
2. `pipeline/compatibility.py:upgrade_pipeline_v1_3_to_v1_4()` auto-upgrade

```python
# src/aiflow/services/document_extractor/service.py
class DocumentExtractorService:
    async def extract(self, file_path, config_name, **kwargs):
        """LEGACY shim — call extract_from_package() with single-file package."""
        warnings.warn(
            "extract(file_path) is deprecated in v1.4.0. Use extract_from_package().",
            DeprecationWarning,
            stacklevel=2,
        )
        package = await self._build_single_file_package(file_path, kwargs.get("tenant_id", "default"))
        return await self.extract_from_package(package, config_name)

    async def _build_single_file_package(self, file_path, tenant_id):
        from aiflow.intake.normalization import IntakeNormalizationLayer
        norm = IntakeNormalizationLayer()
        return norm.normalize_file_upload(
            tenant_id=tenant_id,
            files=[Path(file_path)],
        )

    async def extract_from_package(self, package, config_name):
        """NEW primary API — placeholder in Phase 1a.
        Full implementation in Phase 1c (R4).
        """
        # Phase 1a: csak return shim - a valos extractor logika Phase 1c-ben
        raise NotImplementedError("extract_from_package full impl in Phase 1c")
```

> **Megjegyzes:** A shim layer Phase 1a-ban **csak a skeleton**. A teljes logika Phase 1c-ben
> kerul ki — ott Implement `extract_from_package()` hivasra a meglevo extractor kod.

### Day 15 — Pipeline auto-upgrade layer

`src/aiflow/pipeline/compatibility.py` — forras: `100_d_*` Section 3.3.

Week 3 commit.

---

## 7. Week 4 — Acceptance E2E + Dokumentacio + Demo (Day 16-20)

### Day 16-17 — Phase 1a E2E teszt suite

```
tests/e2e/v1_4_0_phase_1a/
  test_intake_package_lifecycle.py       # state machine happy path
  test_policy_engine_profile_switch.py   # Profile A vs B
  test_provider_registry_contract.py     # contract test runs
  test_skill_instance_policy_override.py
  test_backward_compat_extract_file.py   # legacy extract(file) API
  test_pipeline_auto_upgrade.py          # v1.3 → v1.4 auto-upgrade
  fixtures/
    sample_policy_a.yaml
    sample_policy_b.yaml
    sample_legacy_pipeline.yaml
```

### Day 18 — Backward compat regression suite (P4)

**Forras:** `103_*` Section 9.5.1

```
tests/regression/backward_compat/
  test_invoice_finder_v1_3_pipeline.py
  test_extract_file_legacy_api.py
  test_skill_instance_without_policy.py
```

### Day 19 — Dokumentacio frissites

- [ ] `CLAUDE.md` root — key numbers update (v1.4.0 Phase 1a DONE)
- [ ] `01_PLAN/CLAUDE.md` — key numbers update
- [ ] `58_POST_SPRINT_HARDENING_PLAN.md` — Phase 1a = DONE
- [ ] `FEATURES.md` — v1.4.0 row hozzaadas
- [ ] `01_PLAN/104_*` integritas check update
- [ ] OpenAPI export: `python scripts/export_openapi.py`

### Day 20 — Demo + Sprint review

- Team walkthrough (60 perc)
- Phase 1a acceptance gate check (Section 9 alul)
- Sprint retro
- Phase 1b kickoff session prompt draft

---

## 8. Git Workflow

### 8.1 Branch strategy

```
main                                ← stable, v1.3.0
  └── feature/v1.4.0-phase-1a-foundation  ← Phase 1a branch
```

### 8.2 Commit naming convention

```
feat(intake): Phase 1a Day N — short description
feat(policy): Phase 1a Day N — short description
feat(providers): Phase 1a Day N — short description
feat(db): Phase 1a Day N — alembic XXX description
feat(skill-system): Phase 1a Day N — R13 policy override
feat(compat): Phase 1a Day N — backward compat shim
test(phase-1a): Day N — E2E test description
docs(phase-1a): Day N — documentation update
refactor(phase-1a): Day N — refactor description

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
```

### 8.3 PR strategy

- Phase 1a = **egyetlen PR** a `main`-be, Day 20 vegen
- Az egyes daily commitok NEM mennek PR-kent — csak a sprint vegen
- PR description hasznaljon a `103_*` Section 9.1 acceptance checklistre

---

## 9. Phase 1a Acceptance Gate Checklist

> **Masold be a PR description-be.** Ha bármely nem check-elt, Phase 1a NEM kesz.

### 9.1 Implementacio

- [ ] `src/aiflow/intake/` modul letrehozva
- [ ] `IntakePackage`, `IntakeFile`, `IntakeDescription` Pydantic v2 modellek
- [ ] `IntakePackageStatus` state machine + transition validator
- [ ] `IntakeNormalizationLayer` (file_upload mode)
- [ ] `IntakeRepository` (asyncpg) — atomic insert + status transition
- [ ] `src/aiflow/policy/engine.py:PolicyEngine` (30+ parameter)
- [ ] `config/profiles/profile_a.yaml` + `profile_b.yaml`
- [ ] `src/aiflow/providers/` modul + 4 ABC + registry
- [ ] `ProviderMetadata` Pydantic
- [ ] Contract test framework
- [ ] `SkillInstanceConfig.policy_override` field
- [ ] `instances/{customer}/policy.yaml` loader
- [ ] `DocumentExtractorService.extract()` backward compat shim
- [ ] `pipeline/compatibility.py` auto-upgrade function

### 9.2 Adatbazis

- [ ] Alembic 030 (intake tables) sikeres upgrade
- [ ] Alembic 031 (policy_overrides) sikeres upgrade
- [ ] Alembic downgrade 029 + re-upgrade tesztelt
- [ ] Rollback rehearsal staging-ben

### 9.3 Tesztek

- [ ] `tests/unit/intake/` — 25+ teszt PASS
- [ ] `tests/unit/policy/` — 10+ teszt PASS
- [ ] `tests/integration/providers/test_contract.py` — contract framework PASS
- [ ] `tests/e2e/v1_4_0_phase_1a/` — 6+ E2E teszt PASS
- [ ] `tests/regression/backward_compat/` — 3+ regression teszt PASS
- [ ] **Coverage >= 80% a uj modulokra** (intake/, policy/, providers/)
- [ ] Meglevo tesztek NEM regreszalnak (`pytest tests/unit/ -q`)

### 9.4 Minoseg

- [ ] `ruff check src/ tests/` → 0 error
- [ ] `mypy src/aiflow/intake/ src/aiflow/policy/ src/aiflow/providers/` → 0 error
- [ ] `pytest tests/unit/ -q` → ALL PASS
- [ ] CI workflow (`ci-v1-4-0.yml`) zöld (minden 7 job)

### 9.5 Dokumentacio

- [ ] `CLAUDE.md` key numbers frissitve
- [ ] `01_PLAN/CLAUDE.md` frissitve
- [ ] `58_POST_SPRINT_HARDENING_PLAN.md` Phase 1a = DONE
- [ ] `FEATURES.md` v1.4.0 row
- [ ] OpenAPI export frissitve

### 9.6 Uzletiseg

- [ ] Customer notification kuldve
- [ ] Architect + lead engineer sign-off (Phase 1a demo utan)
- [ ] Phase 1b session prompt draft elkeszult

---

## 10. Rollback Plan (ha bármi kitör)

**Forras:** `100_d_*` Section 12 (Rollback Decision Matrix)

| Mi tort el? | Strategia |
|------------|-----------|
| Alembic 030/031 hibas staging-ben | `alembic downgrade 029`, fix, re-run |
| Alembic 030/031 hibas prod-ban | Blue-green: Blue marad v1.3.0, Green fix, re-deploy |
| IntakePackage Pydantic schema breaking | Forward-fix: schema javitas + release v1.4.0.1 |
| Backward compat shim hiba | Forward-fix: shim logic fix |
| Meglevo extract(file) teszt regresszio | Shim hiba → azonnali patch + commit |
| CI 1 job nem zöld | Investigate + fix (NEM blokkolja a local dev-et) |

**Nuclear option (ha Phase 1a teljes restart):**

```bash
git checkout main
git branch -D feature/v1.4.0-phase-1a-foundation
# Fresh start from Phase 1a Day 1 (after retrospective)
```

---

## 11. Daily Standup Template

```markdown
# Phase 1a Day N — Standup

## Yesterday
- [commit hash] feat(intake): short description

## Today
- Day N task: [section reference, e.g., 4.3 Alembic 030]

## Blockers
- None / [list]

## Acceptance progress
- [ ] X of Y items in Section 9 checklist
```

---

## 12. Hivatkozasok (melyik dokumentum mit ad)

> Ha elakadsz, ITT talalod a reszleteket:

| Kerdes | Dokumentum | Szakasz |
|-------|-----------|---------|
| "Mi az IntakePackage pontos schemaja?" | `100_b_*` | Section 1 |
| "Milyen allapotok vannak?" | `100_c_*` | Section 1-7 |
| "Mi a valid transition?" | `100_c_*` | Section 1.3 |
| "Hogyan migráljam a meglevo DB-t?" | `100_d_*` | Section 2 |
| "Mi tortenjen ha backward compat tor?" | `100_d_*` | Section 12 |
| "Melyik policy parameter mit jelent?" | `100_*` | Section 6 |
| "Hogyan valasztja a routing engine a parser-t?" | `101_*` N7 + `103_*` Section 4 | — |
| "Mi a 4 provider ABC pontos signaturaja?" | `103_*` | Section 5 |
| "Multi-tenant isolation hogyan mukodik?" | `103_*` | Section 6 |
| "Mely CI workflow kell?" | `103_*` | Section 9.5 |
| "GPU vs CPU kapacitas?" | `100_e_*` | Section 1-2 |
| "HITL review queue mennyit bir?" | `100_f_*` | Section 1-2 |
| "CrewAI dontes miert?" | `100_*` | Section 2.A (ADR-1) |
| "Mi a Phase 1a pontos task listaja?" | `103_*` | Section 3.1 |
| "Hol talalom az osszes dokumentumot?" | `104_*` | Section 1 |
| "Mit valtoztunk a P0-P4 hardening soran?" | `105_*` | Teljes |

---

## 13. Sprint B → Phase 1a atmenet

Sprint B lezarva (`main`-re mergelve) → az **elso commit** `feature/v1.4.0-phase-1a-foundation`-on:

```bash
git commit --allow-empty -m "chore(phase-1a): Phase 1a kickoff — feature/v1.4.0-phase-1a-foundation

Sprint B (v1.3.0) DONE. Phase 1a (v1.4.0) starts.

Implementation guide: 01_PLAN/106_AIFLOW_v2_PHASE_1a_IMPLEMENTATION_GUIDE.md
Master index: 01_PLAN/104_AIFLOW_v2_FINAL_MASTER_INDEX.md

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## 14. Phase 1a Exit Criteria (Gate)

**KOVETKEZO sprintbe (Phase 1b) CSAK AKKOR lephet:**

- [x] Minden Section 9 acceptance item check
- [x] Demo sikeresen megtortent
- [x] Architect + lead engineer sign-off
- [x] Customer notification confirmed
- [x] `v1.4.0-phase-1a` git tag letrehozva
- [x] Merge to `main`
- [x] `feature/v1.4.1-phase-1b-sources` branch letrehozva
- [x] Phase 1b session prompt kesz (`01_PLAN/session_XX_v1_4_1_phase_1b_sources.md`)

---

> **Vegleges:** Ez az implementation guide **onalloan futtathato** — a Phase 1a sprint-hez
> minden szukseges informaciot tartalmaz. Ha tobb reszletre van szukseg, a Section 12 tablazata
> mutatja hol talalod.
>
> **Olvasasi ido Phase 1a kezdese elott:**
> 1. Ez a dokumentum (~60 perc)
> 2. `100_b_*` (~30 perc, contractok pontos kodja)
> 3. `100_c_*` (~15 perc, state machine atmenetek)
>
> **Osszesen: ~2 ora, aztan indulhat a Day 1.**
