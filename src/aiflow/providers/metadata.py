"""Provider metadata — capability descriptor for pluggable providers.

Source: 103_AIFLOW_v2_FINAL_VALIDATION.md Section 5 (MF6),
        106_AIFLOW_v2_PHASE_1a_IMPLEMENTATION_GUIDE.md Section 5.6-5.10
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

__all__ = [
    "ProviderMetadata",
]


class ProviderMetadata(BaseModel):
    """Descriptor for a pluggable provider's capabilities and constraints."""

    name: str = Field(
        ..., min_length=1, description="Provider identifier (e.g. 'docling_standard')."
    )
    version: str = Field(..., min_length=1, description="Semver version string.")
    supported_types: list[str] = Field(
        ...,
        min_length=1,
        description="MIME type shorthands this provider handles (e.g. ['pdf', 'docx']).",
    )
    speed_class: Literal["fast", "normal", "slow"] = Field(
        ...,
        description="Relative speed tier.",
    )
    gpu_required: bool = Field(
        default=False,
        description="Whether this provider requires GPU acceleration.",
    )
    cost_class: Literal["free", "cheap", "moderate", "expensive"] = Field(
        ...,
        description="Relative cost tier.",
    )
    license: str = Field(
        ...,
        min_length=1,
        description="License identifier (AGPL, MIT, commercial, proprietary).",
    )
