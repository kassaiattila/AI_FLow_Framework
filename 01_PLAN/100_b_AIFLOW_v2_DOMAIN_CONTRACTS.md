# AIFlow v2 — Domain Contracts (Contract-First Specifikacio)

> **Verzio:** 2.0 (FINAL — SIGNED OFF)
> **Datum:** 2026-04-09
> **Statusz:** ELFOGADVA (SIGNED OFF) — `103_*` 2. ciklus + `105_*` P0-P4 hardening utan
> **Master index:** `104_AIFLOW_v2_FINAL_MASTER_INDEX.md` (kezdd itt az olvasast!)
> **Szulo:** `100_AIFLOW_v2_ARCHITECTURE_REFINEMENT_OVERVIEW.md`
> **Rokon:** `100_c_AIFLOW_v2_STATE_LIFECYCLE_MODEL.md`, `100_d_AIFLOW_v2_MIGRATION_PLAYBOOK.md`
> **Forras:** `102_AIFLOW_v2_FIRST_REVIEW_CYCLE.md` Section 3.1 (Must fix)
>
> **Valtozas naplo:**
> - **v2.0 (2026-04-09):** Status "AKTIV" → "ELFOGADVA (SIGNED OFF)". Sign-off `103_*` utan,
>   P0 hardening korrekcio (`105_*`-ben rogzitve).
> - **v1.0 (2026-04-08):** Initial draft, 13 contract teljes definicio.

> **Cel:** Phase 1 implementacio NEM start-elheto domain contractok formal definicio nelkul.
> Ez a dokumentum rogziti a 13 kulcs Pydantic modell teljes shapejet, **MIELOTT** barmely
> komponenst implementaljanak. Az adapter shape drift kockazat ezzel kizart.

> **Stilus:** Type-strict Pydantic v2, `from __future__ import annotations`, `BaseModel`-bol szarmazo,
> kotelezo `__all__`, doc string minden mezohoz. NE csak deklaraljon, hanem MAGYARAZZA a mezo szerepet
> es a constraint-eket.

---

## 0. Tartalomjegyzek

| # | Domain entity | Hol implementalva (target) |
|---|--------------|---------------------------|
| 1 | `IntakePackage` | `src/aiflow/intake/package.py` |
| 2 | `IntakeFile` (alias: `SourceFile`) | `src/aiflow/intake/package.py` |
| 3 | `IntakeDescription` (alias: `SourceDescription`) | `src/aiflow/intake/package.py` |
| 4 | `RoutingDecision` | `src/aiflow/routing/decision.py` |
| 5 | `ParserResult` | `src/aiflow/providers/interfaces.py` |
| 6 | `ClassificationResult` | `src/aiflow/providers/interfaces.py` |
| 7 | `ExtractionResult` | `src/aiflow/providers/interfaces.py` |
| 8 | `ArchivalArtifact` | `src/aiflow/archival/artifact.py` |
| 9 | `ValidationResult` (veraPDF) | `src/aiflow/archival/validation.py` |
| 10 | `EmbeddingDecision` | `src/aiflow/embeddings/decision.py` |
| 11 | `ReviewTask` (kibovites) | `src/aiflow/services/human_review/task.py` |
| 12 | `LineageRecord` | `src/aiflow/audit/lineage.py` |
| 13 | `ProvenanceMap` | `src/aiflow/provenance/map.py` |

---

## 1. `IntakePackage` — Multi-source intake unified domain entity

**Modul:** `src/aiflow/intake/package.py`

```python
"""Intake package — multi-source unified domain entity."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator

__all__ = [
    "IntakeSourceType",
    "IntakePackageStatus",
    "IntakePackage",
    "IntakeFile",
    "IntakeDescription",
    "DescriptionRole",
]


class IntakeSourceType(str, Enum):
    """Source type from which a package was received."""

    EMAIL = "email"
    FILE_UPLOAD = "file_upload"
    FOLDER_IMPORT = "folder_import"
    BATCH_IMPORT = "batch_import"
    API_PUSH = "api_push"


class IntakePackageStatus(str, Enum):
    """Lifecycle status (lasd 100_c State Lifecycle Model)."""

    RECEIVED = "received"
    NORMALIZED = "normalized"
    ROUTED = "routed"
    PARSED = "parsed"
    CLASSIFIED = "classified"
    EXTRACTED = "extracted"
    REVIEW_PENDING = "review_pending"
    REVIEWED = "reviewed"
    ARCHIVED = "archived"
    FAILED = "failed"
    QUARANTINED = "quarantined"


class DescriptionRole(str, Enum):
    """Role of a free-text description in the package."""

    CASE_NOTE = "case_note"
    USER_NOTE = "user_note"
    FORM_INPUT = "form_input"
    PACKAGE_CONTEXT = "package_context"
    EMAIL_BODY = "email_body"
    FREE_TEXT = "free_text"


class IntakeFile(BaseModel):
    """Single file within an intake package.

    Alias: ``SourceFile`` (a ``document_pipeline.md`` terminologia szerint).
    """

    file_id: UUID = Field(default_factory=uuid4, description="Stable file identifier.")
    file_path: str = Field(..., description="Absolute or relative path to the file.")
    file_name: str = Field(..., description="Original filename.")
    mime_type: str = Field(..., description="Detected MIME type (python-magic).")
    size_bytes: int = Field(..., ge=0, description="File size in bytes.")
    sha256: str = Field(..., min_length=64, max_length=64, description="SHA256 hex digest.")
    source_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Source-specific metadata (e.g., email_attachment_id, folder_path).",
    )
    sequence_index: int | None = Field(
        None,
        description="Order in which the file arrived in the package (0-indexed).",
    )

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, v: str) -> str:
        if not all(c in "0123456789abcdef" for c in v.lower()):
            raise ValueError("sha256 must be lowercase hex digest")
        return v.lower()


class IntakeDescription(BaseModel):
    """Free-text description associated with the package or specific files.

    Alias: ``SourceDescription`` (a ``document_pipeline.md`` terminologia szerint).
    """

    description_id: UUID = Field(default_factory=uuid4)
    text: str = Field(..., min_length=1, description="Description text.")
    language: str | None = Field(None, description="Language code (hu, en, ...). Detected if None.")
    role: DescriptionRole = Field(
        DescriptionRole.FREE_TEXT,
        description="Description role hint for association logic.",
    )
    associated_file_ids: list[UUID] = Field(
        default_factory=list,
        description="File IDs to which this description applies. Filled by association layer (N4).",
    )
    association_confidence: float | None = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Confidence score from the association layer (0..1).",
    )
    association_method: Literal["rule", "llm", "manual", "explicit"] | None = Field(
        None,
        description="How the association was made.",
    )


class IntakePackage(BaseModel):
    """Multi-source intake package — unified domain entity.

    Container for: files + free-text descriptions + package context + metadata.
    Single root domain object that downstream pipeline steps work with.
    """

    package_id: UUID = Field(default_factory=uuid4, description="Stable package identifier.")
    source_type: IntakeSourceType = Field(..., description="Origin source type.")
    tenant_id: str = Field(..., min_length=1, description="Tenant identifier (multi-tenant boundary).")
    status: IntakePackageStatus = Field(IntakePackageStatus.RECEIVED, description="Lifecycle status.")

    files: list[IntakeFile] = Field(default_factory=list, description="Files in the package.")
    descriptions: list[IntakeDescription] = Field(
        default_factory=list,
        description="Free-text descriptions in the package.",
    )

    source_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Source-specific metadata (e.g., email_from, email_subject, email_date, "
            "folder_path, batch_id, api_caller_id)."
        ),
    )
    package_context: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Package-level business context (e.g., case_id, request_id, project_code). "
            "Used by data_router and HITL routing."
        ),
    )
    cross_document_signals: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Cross-document signals filled during classification + routing (e.g., "
            "has_invoice=true, has_delivery_note=true, total_amount=...)."
        ),
    )

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    received_by: str | None = Field(None, description="User/service who received the package.")

    provenance_chain: list[UUID] = Field(
        default_factory=list,
        description=(
            "Lineage event IDs ordered by occurrence (NEM allapotvaltozas — minden szignifikans "
            "esemeny). Lasd 100_c State Lifecycle Model + N17 LineageRecord."
        ),
    )

    routing_decision_id: UUID | None = Field(
        None,
        description="Reference to RoutingDecision (filled by N7 routing engine).",
    )
    review_task_id: UUID | None = Field(
        None,
        description="Reference to ReviewTask if package entered HITL.",
    )

    @field_validator("files")
    @classmethod
    def validate_files_not_all_empty_with_descriptions(
        cls, v: list[IntakeFile], info
    ) -> list[IntakeFile]:
        # at least one file OR at least one description must be present
        descriptions = info.data.get("descriptions", [])
        if not v and not descriptions:
            raise ValueError("IntakePackage must have at least one file or one description")
        return v
```

**Constraint-ok**:
- `package_id`: stable, UUID4 default
- `tenant_id`: kotelezo, multi-tenant boundary alapja
- `files` VAGY `descriptions` legalabb egyikenek nem ures lennie kell
- `status` lifecycle: lasd 100_c

**Migration impact**: Uj DB tablak (alembic 030):
- `intake_packages`
- `intake_files`
- `intake_descriptions`

---

## 2. `RoutingDecision` — Multi-signal parser routing audit

**Modul:** `src/aiflow/routing/decision.py`

```python
"""Routing decision — multi-signal parser/classifier/extractor routing audit."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator

__all__ = [
    "RoutingDecisionStatus",
    "RoutingSignal",
    "RoutingDecision",
    "ProviderType",
    "RoutingScore",
]


class ProviderType(str, Enum):
    PARSER = "parser"
    CLASSIFIER = "classifier"
    EXTRACTOR = "extractor"
    EMBEDDER = "embedder"


class RoutingDecisionStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXECUTED = "executed"
    FALLBACK_USED = "fallback_used"
    ALL_FAILED = "all_failed"
    HUMAN_OVERRIDE = "human_override"


class RoutingSignal(BaseModel):
    """Single routing signal value with provenance."""

    name: str = Field(..., description="Signal name (e.g., text_layer_ratio).")
    value: Any = Field(..., description="Signal value (numeric, string, or bool).")
    extracted_at: datetime = Field(default_factory=datetime.utcnow)
    extractor: str = Field(..., description="Component that extracted the signal.")


class RoutingScore(BaseModel):
    """Per-provider score from the routing engine."""

    provider_name: str = Field(..., description="Provider identifier (e.g., docling_standard).")
    score: float = Field(..., ge=0.0, le=1.0, description="Calculated suitability score.")
    rationale: str = Field(..., description="Why this score (signal contributions summary).")
    blocking_constraints: list[str] = Field(
        default_factory=list,
        description="Policy constraints that block this provider (e.g., azure_di_disabled).",
    )


class RoutingDecision(BaseModel):
    """Multi-signal routing decision with audit trail."""

    decision_id: UUID = Field(default_factory=uuid4)
    package_id: UUID = Field(..., description="Package this decision applies to.")
    file_id: UUID | None = Field(
        None,
        description="Specific file (None = package-level decision).",
    )
    provider_type: ProviderType
    status: RoutingDecisionStatus = RoutingDecisionStatus.PENDING

    signals_used: list[RoutingSignal] = Field(
        default_factory=list,
        description="Ordered list of signals consulted.",
    )
    candidate_scores: list[RoutingScore] = Field(
        default_factory=list,
        description="All candidate providers with scores.",
    )

    selected_provider: str = Field(..., description="Provider chosen by the engine.")
    selection_reason: str = Field(..., description="Human-readable rationale.")
    selection_confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence in the routing decision (rule-based + signal-weighted).",
    )

    fallback_chain: list[str] = Field(
        default_factory=list,
        description="Ordered fallback providers if selected fails.",
    )
    used_fallback_provider: str | None = Field(
        None,
        description="Provider actually used after fallback (None = selected_provider succeeded).",
    )

    policy_constraints: dict[str, Any] = Field(
        default_factory=dict,
        description="Policy snapshot at decision time (cloud_ai_allowed, ...).",
    )
    tenant_id: str = Field(..., description="Tenant context.")

    created_at: datetime = Field(default_factory=datetime.utcnow)
    executed_at: datetime | None = Field(None, description="When the chosen provider ran.")

    human_override_user: str | None = Field(
        None,
        description="User ID if a human overrode the engine choice.",
    )

    @field_validator("selection_confidence")
    @classmethod
    def confidence_must_be_valid(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("selection_confidence must be in [0.0, 1.0]")
        return v
```

**Constraint-ok**:
- `signals_used` minimum 1 signal
- `selection_reason` kotelezo, audit-friendly
- `policy_constraints` snapshot a dontes idejen
- `decision_id` queryelt audit endpointen

**Migration impact**: Uj DB tabla `routing_decisions` (alembic 033)

---

## 3. `ParserResult` — Universal parser provider output

**Modul:** `src/aiflow/providers/interfaces.py`

```python
"""Provider interfaces — parser, classifier, extractor, embedder result schemas."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

__all__ = [
    "ParserResult",
    "ParsedPage",
    "ParsedTable",
    "ParserError",
]


class ParserError(BaseModel):
    """Parser error or warning."""

    severity: Literal["error", "warning", "info"]
    code: str
    message: str
    page_number: int | None = None


class ParsedPage(BaseModel):
    page_number: int = Field(..., ge=1)
    text: str = Field("", description="Plain text of the page.")
    markdown: str = Field("", description="Markdown rendering (preserves layout).")
    width: int | None = None
    height: int | None = None
    is_scan: bool | None = Field(None, description="True if page has no text layer.")


class ParsedTable(BaseModel):
    table_index: int = Field(..., ge=0)
    page_number: int | None = None
    markdown: str = Field("", description="Markdown table representation.")
    caption: str = Field("")
    row_count: int | None = None
    col_count: int | None = None


class ParserResult(BaseModel):
    """Universal parser result — every parser provider returns this.

    Stable contract — adapter shape drift NEM lehet.
    """

    result_id: UUID = Field(default_factory=uuid4)
    file_id: UUID = Field(..., description="Source file ID.")
    package_id: UUID = Field(..., description="Source package ID.")
    routing_decision_id: UUID = Field(..., description="Which routing decision led here.")

    provider_name: str = Field(..., description="Parser provider used.")
    provider_version: str = Field(..., description="Provider version (for reproducibility).")

    text: str = Field("", description="Full extracted plain text.")
    markdown: str = Field("", description="Full markdown rendering.")
    pages: list[ParsedPage] = Field(default_factory=list)
    tables: list[ParsedTable] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    page_count: int = Field(0, ge=0)
    word_count: int = Field(0, ge=0)
    char_count: int = Field(0, ge=0)
    has_text_layer: bool = Field(False, description="True if file has born-digital text.")
    is_scan_dominant: bool = Field(False, description="True if >50% pages are scans.")

    parse_duration_ms: int = Field(0, ge=0)
    cost_usd: float = Field(0.0, ge=0.0, description="Cost incurred (0 for self-hosted).")
    errors: list[ParserError] = Field(default_factory=list)

    created_at: datetime = Field(default_factory=datetime.utcnow)
```

---

## 4. `ClassificationResult` — Classifier provider output

```python
class ClassificationResult(BaseModel):
    """Classifier provider result."""

    result_id: UUID = Field(default_factory=uuid4)
    file_id: UUID
    package_id: UUID
    routing_decision_id: UUID

    provider_name: str
    provider_version: str

    primary_class: str = Field(..., description="Top-1 class (e.g., 'invoice', 'contract').")
    primary_confidence: float = Field(..., ge=0.0, le=1.0)
    all_scores: dict[str, float] = Field(
        default_factory=dict,
        description="Class → confidence map (top-K).",
    )

    classification_method: Literal["ml_only", "llm_only", "hybrid_ml_llm", "visual_vlm"]
    is_calibrated: bool = Field(False, description="Confidence passed through calibration layer.")
    calibration_method: str | None = None

    page_classifications: list["PageClassification"] | None = Field(
        None,
        description="Per-page classification (visual classifier).",
    )
    boundary_markers: list["BoundaryMarker"] | None = Field(
        None,
        description="Document boundary positions (visual classifier).",
    )

    cost_usd: float = Field(0.0, ge=0.0)
    duration_ms: int = Field(0, ge=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PageClassification(BaseModel):
    page_number: int = Field(..., ge=1)
    class_name: str
    confidence: float = Field(..., ge=0.0, le=1.0)


class BoundaryMarker(BaseModel):
    page_number: int = Field(..., ge=1)
    is_document_start: bool
    confidence: float = Field(..., ge=0.0, le=1.0)
```

---

## 5. `ExtractionResult` — Extractor provider output (kibovites R4)

```python
class FieldConfidence(BaseModel):
    """Per-field calibrated confidence."""

    field_name: str
    extracted_value: Any
    confidence: float = Field(..., ge=0.0, le=1.0)
    confidence_layers: dict[str, float] = Field(
        default_factory=dict,
        description="Per-layer confidence (rule_based, ml, llm_judge).",
    )
    extraction_method: Literal["regex", "llm", "rule", "hybrid"]
    source_evidence: list[str] = Field(
        default_factory=list,
        description="Text snippets supporting the extraction.",
    )
    requires_review: bool = Field(False, description="Flag for HITL routing.")


class ExtractionResult(BaseModel):
    """Extraction result with per-field confidence + cross-document signals."""

    result_id: UUID = Field(default_factory=uuid4)
    file_id: UUID
    package_id: UUID
    routing_decision_id: UUID

    config_name: str = Field(..., description="DocumentTypeConfig name.")
    config_version: str

    extracted_fields: dict[str, Any] = Field(default_factory=dict)
    field_confidences: list[FieldConfidence] = Field(default_factory=list)

    overall_confidence: float = Field(..., ge=0.0, le=1.0)
    overall_method: Literal["aggregate", "min", "weighted_mean", "calibrated"] = "calibrated"

    validation_errors: list[str] = Field(default_factory=list)
    validation_warnings: list[str] = Field(default_factory=list)

    cross_document_signals: dict[str, Any] = Field(
        default_factory=dict,
        description="Signals propagated to package context.",
    )
    free_text_extractions: dict[str, str] = Field(
        default_factory=dict,
        description="Free-text extractions (e.g., 'summary', 'parties').",
    )

    routing_decision: Literal["auto_approve", "review_pending", "auto_reject"]
    review_reason: str | None = None

    cost_usd: float = Field(0.0, ge=0.0)
    duration_ms: int = Field(0, ge=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

---

## 6. `ArchivalArtifact` — PDF/A archival artifact

**Modul:** `src/aiflow/archival/artifact.py`

```python
"""Archival artifact — PDF/A converted file with validation history."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

__all__ = ["ArchivalArtifact", "ArchivalStatus", "PDFAProfile"]


class ArchivalStatus(str, Enum):
    PENDING = "pending"
    CONVERTING = "converting"
    CONVERTED = "converted"
    VALIDATING = "validating"
    VALID = "valid"
    INVALID = "invalid"
    QUARANTINED = "quarantined"
    FAILED = "failed"


class PDFAProfile(str, Enum):
    A_1A = "PDF/A-1a"
    A_1B = "PDF/A-1b"
    A_2A = "PDF/A-2a"
    A_2B = "PDF/A-2b"
    A_3A = "PDF/A-3a"
    A_3B = "PDF/A-3b"


class ArchivalArtifact(BaseModel):
    """PDF/A converted artifact with validation lineage.

    Lifecycle: lasd 100_c State Lifecycle Model.
    """

    artifact_id: UUID = Field(default_factory=uuid4)
    source_file_id: UUID = Field(..., description="Original source IntakeFile.")
    package_id: UUID

    artifact_path: str = Field(..., description="Storage path of the PDF/A file.")
    artifact_sha256: str = Field(..., min_length=64, max_length=64)
    profile: PDFAProfile

    status: ArchivalStatus = ArchivalStatus.PENDING
    validation_result_id: UUID | None = Field(
        None,
        description="Reference to ValidationResult (veraPDF).",
    )
    is_validated: bool = Field(False, description="True only after veraPDF PASS.")

    converter: Literal["gotenberg", "manual_upload"] = "gotenberg"
    converter_version: str
    conversion_duration_ms: int = Field(0, ge=0)

    quarantine_reason: str | None = None
    quarantine_path: str | None = None

    retention_until: datetime | None = Field(
        None,
        description="When this artifact may be deleted (compliance retention).",
    )

    created_at: datetime = Field(default_factory=datetime.utcnow)
    converted_at: datetime | None = None
    validated_at: datetime | None = None
```

---

## 7. `ValidationResult` — veraPDF validation output

**Modul:** `src/aiflow/archival/validation.py`

```python
"""veraPDF validation result."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

__all__ = ["ValidationResult", "ValidationError"]


class ValidationError(BaseModel):
    rule_id: str = Field(..., description="veraPDF rule (e.g., '6.2.3.3-1').")
    severity: Literal["error", "warning"]
    message: str
    location: str | None = None


class ValidationResult(BaseModel):
    """veraPDF validation result for an ArchivalArtifact."""

    validation_id: UUID = Field(default_factory=uuid4)
    artifact_id: UUID
    profile: str = Field(..., description="PDF/A profile validated against.")

    is_valid: bool
    error_count: int = Field(0, ge=0)
    warning_count: int = Field(0, ge=0)
    errors: list[ValidationError] = Field(default_factory=list)
    warnings: list[ValidationError] = Field(default_factory=list)

    raw_xml_report: str = Field("", description="Full veraPDF XML report (audit).")
    verapdf_version: str
    validated_at: datetime = Field(default_factory=datetime.utcnow)
    duration_ms: int = Field(0, ge=0)
```

---

## 8. `EmbeddingDecision` — Embedding governance audit

**Modul:** `src/aiflow/embeddings/decision.py`

```python
"""Embedding decision — embedding governance audit."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

__all__ = ["EmbeddingDecision", "RedactionAction"]


class RedactionAction(BaseModel):
    action: Literal["mask", "block", "allow_with_audit"]
    pii_type: str
    original_position: tuple[int, int]
    masked_value: str | None = None


class EmbeddingDecision(BaseModel):
    """Audit record for an embedding ingestion decision."""

    decision_id: UUID = Field(default_factory=uuid4)
    package_id: UUID
    file_id: UUID | None
    chunk_id: str = Field(..., description="Chunk identifier.")
    tenant_id: str

    embedder_provider: str = Field(..., description="Provider name (e.g., bge_m3).")
    embedder_version: str
    dimensions: int

    pii_check_passed: bool
    redactions: list[RedactionAction] = Field(
        default_factory=list,
        description="Per-PII redaction actions.",
    )
    redaction_mode: Literal["mask", "block", "allow_with_audit"]

    policy_snapshot: dict = Field(
        default_factory=dict,
        description="Policy at decision time.",
    )

    embed_duration_ms: int = Field(0, ge=0)
    cost_usd: float = Field(0.0, ge=0.0)
    embedded_at: datetime = Field(default_factory=datetime.utcnow)
    blocked: bool = Field(False, description="True if embedding was blocked by policy.")
```

---

## 9. `ReviewTask` — Kibovitett HITL review task

**Modul:** `src/aiflow/services/human_review/task.py`

```python
"""Review task — extended HumanReview model for IntakePackage context."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

__all__ = ["ReviewTask", "ReviewStatus", "ReviewPriority", "ReviewType"]


class ReviewStatus(str, Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    EXPIRED = "expired"


class ReviewPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ReviewType(str, Enum):
    LOW_CONFIDENCE_EXTRACTION = "low_confidence_extraction"
    AMBIGUOUS_BOUNDARY = "ambiguous_boundary"
    AMBIGUOUS_PROVIDER = "ambiguous_provider"
    AMBIGUOUS_FILE_DESCRIPTION = "ambiguous_file_description"
    AMBIGUOUS_PACKAGE_CONTEXT = "ambiguous_package_context"
    VALIDATION_FAILURE = "validation_failure"
    QUARANTINE = "quarantine"
    POLICY_VIOLATION = "policy_violation"


class ReviewTask(BaseModel):
    """Human-in-the-loop review task with package context."""

    task_id: UUID = Field(default_factory=uuid4)
    package_id: UUID
    file_id: UUID | None
    tenant_id: str

    review_type: ReviewType
    priority: ReviewPriority = ReviewPriority.MEDIUM
    status: ReviewStatus = ReviewStatus.PENDING

    title: str = Field(..., max_length=200)
    description: str
    context_snapshot: dict[str, Any] = Field(
        default_factory=dict,
        description="Snapshot of package context at task creation.",
    )

    affected_fields: list[str] = Field(
        default_factory=list,
        description="Per-field flags (extraction context).",
    )

    options: list[str] = Field(
        default_factory=list,
        description="Suggested decision options for the reviewer.",
    )

    assigned_to: str | None = None
    assigned_at: datetime | None = None

    sla_deadline: datetime | None = Field(None, description="When the task expires (per-tenant SLA).")
    escalation_target: str | None = None
    escalated_at: datetime | None = None

    resolution: str | None = None
    resolved_by: str | None = None
    resolved_at: datetime | None = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

---

## 10. `LineageRecord` — File→derivative→extraction→embedding lineage

**Modul:** `src/aiflow/audit/lineage.py`

```python
"""Lineage record — full audit trail for a file."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

__all__ = ["LineageRecord", "LineageEventType"]


class LineageEventType(str, Enum):
    INTAKE = "intake"
    NORMALIZE = "normalize"
    ROUTE = "route"
    PARSE = "parse"
    CLASSIFY = "classify"
    EXTRACT = "extract"
    REDACT = "redact"
    EMBED = "embed"
    STORE = "store"
    REVIEW_REQUEST = "review_request"
    REVIEW_RESOLVE = "review_resolve"
    ARCHIVE = "archive"
    VALIDATE = "validate"
    QUARANTINE = "quarantine"


class LineageRecord(BaseModel):
    """Single lineage event."""

    event_id: UUID = Field(default_factory=uuid4)
    parent_event_id: UUID | None = Field(None, description="Previous event in chain.")

    event_type: LineageEventType
    package_id: UUID
    file_id: UUID | None = None
    tenant_id: str

    component: str = Field(..., description="Producing component (e.g., parser_factory).")
    provider: str | None = None
    routing_decision_id: UUID | None = None

    input_refs: list[UUID] = Field(
        default_factory=list,
        description="Input artifact references.",
    )
    output_refs: list[UUID] = Field(
        default_factory=list,
        description="Output artifact references.",
    )

    metadata: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime = Field(default_factory=datetime.utcnow)
    duration_ms: int = Field(0, ge=0)
    cost_usd: float = Field(0.0, ge=0.0)

    user_id: str | None = None
```

---

## 11. `ProvenanceMap` — File ↔ description ↔ package mapping

**Modul:** `src/aiflow/provenance/map.py`

```python
"""Provenance map — bidirectional searchable mapping."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

__all__ = ["ProvenanceMap", "ProvenanceLink", "ProvenanceLinkType"]


class ProvenanceLinkType(str, Enum):
    FILE_TO_DESCRIPTION = "file_to_description"
    FILE_TO_PACKAGE = "file_to_package"
    DESCRIPTION_TO_FILE = "description_to_file"
    DESCRIPTION_TO_PACKAGE = "description_to_package"
    PACKAGE_TO_TENANT = "package_to_tenant"
    EXTRACTION_TO_FILE = "extraction_to_file"
    EMBEDDING_TO_FILE = "embedding_to_file"
    ARCHIVAL_TO_FILE = "archival_to_file"


class ProvenanceLink(BaseModel):
    link_id: UUID
    source_id: UUID
    target_id: UUID
    link_type: ProvenanceLinkType
    confidence: float = Field(..., ge=0.0, le=1.0)
    method: Literal["explicit", "rule", "llm", "manual"]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str | None = None


class ProvenanceMap(BaseModel):
    """Provenance map for a tenant — collection of links."""

    tenant_id: str
    links: list[ProvenanceLink] = Field(default_factory=list)
    snapshot_at: datetime = Field(default_factory=datetime.utcnow)
```

---

## Sign-off Checklist (Phase 1 indulas elott)

- [ ] Minden 13 contract-en code review (architect + lead engineer)
- [ ] Pydantic v2 syntax verified
- [ ] DB schema migration draft (alembic 030+)
- [ ] Existing model compatibility check (HumanReview, FetchedEmail, ParsedDocument)
- [ ] Backward compat aliases definied (R1/R4 wrappers)
- [ ] OpenAPI schema export (FastAPI)
- [ ] Test fixtures (`tests/fixtures/intake/*.json`)

---

## Mit NEM tartalmaz ez a dokumentum

- Implementacios kod (nem csak schema)
- Repository / DAL layer (kulon dokumentum)
- API endpoint definicio (`22_API_SPECIFICATION.md` kibovites)
- UI typing (`aiflow-admin/src/types/`)

A `100_d_AIFLOW_v2_MIGRATION_PLAYBOOK.md` ad migracios receptet, a `100_c_AIFLOW_v2_STATE_LIFECYCLE_MODEL.md`
adja az allapot atmenetek formal modelljet.
