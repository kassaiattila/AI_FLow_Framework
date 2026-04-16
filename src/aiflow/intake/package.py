"""Intake package — multi-source unified domain entity.

Source: 100_b_AIFLOW_v2_DOMAIN_CONTRACTS.md Section 1 (SIGNED OFF v2.0)
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_validator

__all__ = [
    "AssociationMode",
    "IntakeSourceType",
    "IntakePackageStatus",
    "DescriptionRole",
    "IntakeFile",
    "IntakeDescription",
    "IntakePackage",
]


class AssociationMode(str, Enum):
    """File<->description association strategy (see N4 associator)."""

    EXPLICIT = "explicit"
    FILENAME_MATCH = "filename_match"
    ORDER = "order"
    SINGLE_DESCRIPTION = "single_description"


class IntakeSourceType(str, Enum):
    """Source type from which a package was received."""

    EMAIL = "email"
    FILE_UPLOAD = "file_upload"
    FOLDER_IMPORT = "folder_import"
    BATCH_IMPORT = "batch_import"
    API_PUSH = "api_push"


class IntakePackageStatus(str, Enum):
    """Lifecycle status (see 100_c State Lifecycle Model)."""

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

    Alias: ``SourceFile`` (document_pipeline.md terminology).
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

    Alias: ``SourceDescription`` (document_pipeline.md terminology).
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
    tenant_id: str = Field(
        ..., min_length=1, description="Tenant identifier (multi-tenant boundary)."
    )
    status: IntakePackageStatus = Field(
        IntakePackageStatus.RECEIVED, description="Lifecycle status."
    )

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
            "Lineage event IDs ordered by occurrence. "
            "See 100_c State Lifecycle Model + N17 LineageRecord."
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

    association_mode: AssociationMode | None = Field(
        None,
        description=(
            "How files were associated to descriptions by the N4 associator. "
            "NULL when associations have not been computed (e.g., single-file "
            "packages or descriptions absent). See aiflow.intake.associator."
        ),
    )

    @model_validator(mode="after")
    def validate_not_empty(self) -> IntakePackage:
        if not self.files and not self.descriptions:
            raise ValueError("IntakePackage must have at least one file or one description")
        return self
