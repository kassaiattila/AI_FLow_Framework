"""Unit tests for ProviderMetadata Pydantic model.

Session: S47 (D0.4) — ProviderRegistry + 4 ABC
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from aiflow.providers.metadata import ProviderMetadata


def _valid_kwargs() -> dict:
    return {
        "name": "docling_standard",
        "version": "1.0.0",
        "supported_types": ["pdf", "docx"],
        "speed_class": "normal",
        "cost_class": "free",
        "license": "MIT",
    }


class TestProviderMetadataValid:
    def test_minimal_valid(self) -> None:
        meta = ProviderMetadata(**_valid_kwargs())
        assert meta.name == "docling_standard"
        assert meta.version == "1.0.0"
        assert meta.supported_types == ["pdf", "docx"]
        assert meta.speed_class == "normal"
        assert meta.gpu_required is False
        assert meta.cost_class == "free"
        assert meta.license == "MIT"

    def test_gpu_required_override(self) -> None:
        meta = ProviderMetadata(**{**_valid_kwargs(), "gpu_required": True})
        assert meta.gpu_required is True

    def test_all_speed_classes(self) -> None:
        for sc in ("fast", "normal", "slow"):
            meta = ProviderMetadata(**{**_valid_kwargs(), "speed_class": sc})
            assert meta.speed_class == sc

    def test_all_cost_classes(self) -> None:
        for cc in ("free", "cheap", "moderate", "expensive"):
            meta = ProviderMetadata(**{**_valid_kwargs(), "cost_class": cc})
            assert meta.cost_class == cc

    def test_single_supported_type(self) -> None:
        meta = ProviderMetadata(**{**_valid_kwargs(), "supported_types": ["pdf"]})
        assert meta.supported_types == ["pdf"]


class TestProviderMetadataInvalid:
    def test_empty_name_raises(self) -> None:
        with pytest.raises(ValidationError):
            ProviderMetadata(**{**_valid_kwargs(), "name": ""})

    def test_empty_version_raises(self) -> None:
        with pytest.raises(ValidationError):
            ProviderMetadata(**{**_valid_kwargs(), "version": ""})

    def test_empty_supported_types_raises(self) -> None:
        with pytest.raises(ValidationError):
            ProviderMetadata(**{**_valid_kwargs(), "supported_types": []})

    def test_invalid_speed_class_raises(self) -> None:
        with pytest.raises(ValidationError):
            ProviderMetadata(**{**_valid_kwargs(), "speed_class": "turbo"})

    def test_invalid_cost_class_raises(self) -> None:
        with pytest.raises(ValidationError):
            ProviderMetadata(**{**_valid_kwargs(), "cost_class": "priceless"})

    def test_empty_license_raises(self) -> None:
        with pytest.raises(ValidationError):
            ProviderMetadata(**{**_valid_kwargs(), "license": ""})

    def test_missing_required_field_raises(self) -> None:
        kwargs = _valid_kwargs()
        del kwargs["name"]
        with pytest.raises(ValidationError):
            ProviderMetadata(**kwargs)
