"""Pydantic I/O models for Email Intent Processor skill.

Field details driven by schemas/ at runtime; these models define
the typed structure for step inputs and outputs.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

__all__ = [
    "EmailInput",
    "AttachmentInfo",
    "IntentResult",
    "EntityResult",
    "Entity",
    "PriorityResult",
    "RoutingDecision",
    "EmailProcessingResult",
]


class AttachmentInfo(BaseModel):
    """Metadata and extracted content from an email attachment."""

    filename: str
    mime_type: str = ""
    size_bytes: int = 0
    extracted_text: str = ""
    extracted_fields: dict[str, Any] = Field(default_factory=dict)
    document_type: str = ""  # From document_types.json
    processor_used: str = ""
    error: str = ""


class EmailInput(BaseModel):
    """Input for the email processing pipeline."""

    subject: str = ""
    body: str = ""
    sender: str = ""
    recipients: list[str] = Field(default_factory=list)
    date: str = ""
    message_id: str = ""
    in_reply_to: str = ""
    thread_id: str = ""
    attachments: list[AttachmentInfo] = Field(default_factory=list)
    raw_eml_path: str = ""  # Optional: path to .eml file


class IntentResult(BaseModel):
    """Result of intent classification."""

    intent_id: str = ""  # From intents.json
    intent_display_name: str = ""
    confidence: float = 0.0
    sub_intent: str | None = ""
    method: str = ""  # "sklearn", "llm", "hybrid"
    sklearn_intent: str | None = ""
    sklearn_confidence: float = 0.0
    llm_intent: str | None = ""
    llm_confidence: float = 0.0
    alternatives: list[dict[str, Any]] = Field(default_factory=list)
    reasoning: str = ""


class Entity(BaseModel):
    """A single extracted entity."""

    entity_type: str  # From entities.json (e.g., "person_name", "contract_number")
    value: str
    normalized_value: str = ""
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source: str = ""  # "body", "subject", "attachment"
    extraction_method: str = ""  # "regex", "llm"
    start_offset: int | None = None
    end_offset: int | None = None


class EntityResult(BaseModel):
    """Result of entity extraction."""

    entities: list[Entity] = Field(default_factory=list)
    entity_count: int = 0
    extraction_methods_used: list[str] = Field(default_factory=list)

    def get_by_type(self, entity_type: str) -> list[Entity]:
        """Get all entities of a given type."""
        return [e for e in self.entities if e.entity_type == entity_type]

    def has_entity(self, entity_type: str) -> bool:
        """Check if at least one entity of the given type was found."""
        return any(e.entity_type == entity_type for e in self.entities)


class PriorityResult(BaseModel):
    """Result of priority scoring."""

    priority_level: int = Field(ge=1, le=5)
    priority_name: str = ""  # "critical", "high", "medium", "low", "minimal"
    priority_display_name: str = ""
    sla_hours: int = 48
    matched_rule: str = ""  # Rule ID from priorities.json
    boosts_applied: list[str] = Field(default_factory=list)
    reasoning: str = ""


class RoutingDecision(BaseModel):
    """Result of routing decision."""

    queue_id: str
    queue_name: str = ""
    department_id: str
    department_name: str = ""
    department_email: str = ""
    auto_escalate_after_minutes: int = 0
    matched_rule: str = ""  # Rule ID from routing_rules.json
    escalation_triggered: bool = False
    escalation_reason: str = ""
    notes: str = ""


class EmailProcessingResult(BaseModel):
    """Complete result of the email processing pipeline."""

    # Input summary
    email_id: str = ""
    subject: str = ""
    sender: str = ""
    received_date: str = ""
    has_attachments: bool = False
    attachment_count: int = 0

    # Pipeline results
    intent: IntentResult | None = None
    entities: EntityResult | None = None
    priority: PriorityResult | None = None
    routing: RoutingDecision | None = None

    # Attachment details
    attachment_summaries: list[AttachmentInfo] = Field(default_factory=list)

    # Pipeline metadata
    processing_time_ms: float = 0.0
    pipeline_version: str = "1.0.0"
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
