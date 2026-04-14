"""Policy configuration — tenant-aware policy parameters for v2 pipeline.

Source: 100_b_AIFLOW_v2_DOMAIN_CONTRACTS.md Section 6,
        106_AIFLOW_v2_PHASE_1a_IMPLEMENTATION_GUIDE.md Section 5.1
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

__all__ = [
    "PolicyConfig",
]


class PolicyConfig(BaseModel):
    """Policy parameters (32 fields) governing pipeline behavior per tenant.

    Defaults represent Profile A (cloud-disallowed, on-prem air-gapped).
    """

    # Cloud & storage policy
    cloud_ai_allowed: bool = False
    cloud_storage_allowed: bool = False
    document_content_may_leave_tenant: bool = False

    # Embedding & vectorization
    embedding_enabled: bool = True
    pii_embedding_allowed: bool = False
    redaction_before_embedding_required: bool = True
    self_hosted_embedding_model: str = "BAAI/bge-m3"
    azure_embedding_model: str = ""

    # Self-hosted parsing
    self_hosted_parsing_enabled: bool = True
    docling_vlm_enabled: bool = False
    qwen_vllm_enabled: bool = False

    # Azure services
    azure_di_enabled: bool = False
    azure_search_enabled: bool = False
    azure_embedding_enabled: bool = False

    # Archival & validation
    archival_pdfa_required: bool = True
    pdfa_validation_required: bool = True

    # Review threshold
    manual_review_confidence_threshold: float = Field(
        default=0.70,
        ge=0.0,
        le=1.0,
        description="Below this confidence, items go to manual review.",
    )

    # Default providers
    default_parser_provider: str = "docling_standard"
    default_classifier_provider: str = "hybrid_ml_llm"
    default_extractor_provider: str = "llm_field_extract"
    default_embedding_provider: str = "bge_m3"

    # Storage providers
    vector_store_provider: str = "pgvector"
    object_store_provider: str = "local_fs"

    # Tenant override
    tenant_override_enabled: bool = True

    # Fallback chain
    fallback_provider_order: dict[str, list[str]] = Field(default_factory=dict)

    # Source adapter
    source_adapter_type: str = "unified"

    # Intake
    intake_package_enabled: bool = True
    source_text_ingestion_enabled: bool = True
    file_description_association_mode: str = "rule_first_llm_fallback"
    package_level_context_enabled: bool = True
    cross_document_context_enabled: bool = True

    # Daily caps
    daily_document_cap: int | None = Field(
        default=None,
        ge=0,
        description="Soft cap on daily documents (advisory). None = unlimited.",
    )
    daily_document_hard_cap: int | None = Field(
        default=None,
        ge=0,
        description="Hard cap on daily documents (enforced). None = unlimited.",
    )

    @field_validator("daily_document_hard_cap")
    @classmethod
    def hard_cap_gte_soft_cap(cls, v: int | None, info: object) -> int | None:
        soft = info.data.get("daily_document_cap") if hasattr(info, "data") else None  # type: ignore[union-attr]
        if v is not None and soft is not None and v < soft:
            raise ValueError("daily_document_hard_cap must be >= daily_document_cap")
        return v
