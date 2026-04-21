"""ParserResult — v1 stub returned by ParserProvider.parse().

v2 upgrade (full structure + page range + provenance fields) is Phase 2b
(v1.5.1) scope. Today it carries just enough to drive extract_from_package
through Docling standard.

Source: 101_AIFLOW_v2_COMPONENT_SPEC.md N6 (ParserProvider),
        110_USE_CASE_FIRST_REPLAN.md §4 Sprint I
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "ParserResult",
]


class ParserResult(BaseModel):
    """Minimal parser output — text + markdown + table markdown blobs."""

    model_config = ConfigDict(extra="forbid")

    file_id: UUID = Field(..., description="IntakeFile.file_id this result corresponds to.")
    parser_name: str = Field(
        ..., min_length=1, description="Parser provider name (e.g. 'docling_standard')."
    )
    text: str = Field(default="", description="Plain-text content extracted from the file.")
    markdown: str = Field(
        default="",
        description="Markdown-formatted content (preserves tables, headings).",
    )
    tables: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Extracted tables as {index, markdown, caption, page_number} dicts.",
    )
    page_count: int = Field(default=0, ge=0, description="Number of pages parsed.")
    parse_duration_ms: float = Field(default=0.0, ge=0.0, description="Wall clock time.")
    parsed_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Parser-specific metadata (mime, file_size, fallback flags).",
    )
