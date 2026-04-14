"""IntakePackage Pydantic model tests.

Source: 100_b_AIFLOW_v2_DOMAIN_CONTRACTS.md Section 1
"""

from uuid import UUID

import pytest

from aiflow.intake.package import (
    DescriptionRole,
    IntakeDescription,
    IntakeFile,
    IntakePackage,
    IntakePackageStatus,
    IntakeSourceType,
)


def _make_file(**overrides) -> IntakeFile:
    defaults = {
        "file_path": "/tmp/test.pdf",
        "file_name": "test.pdf",
        "mime_type": "application/pdf",
        "size_bytes": 1024,
        "sha256": "a" * 64,
    }
    defaults.update(overrides)
    return IntakeFile(**defaults)


def _make_package(**overrides) -> IntakePackage:
    defaults = {
        "source_type": IntakeSourceType.EMAIL,
        "tenant_id": "test_tenant",
        "files": [_make_file()],
    }
    defaults.update(overrides)
    return IntakePackage(**defaults)


class TestIntakePackageCreation:
    def test_minimal_creation_with_file(self):
        pkg = _make_package()
        assert isinstance(pkg.package_id, UUID)
        assert pkg.status == IntakePackageStatus.RECEIVED
        assert pkg.tenant_id == "test_tenant"
        assert len(pkg.files) == 1

    def test_creation_with_descriptions_only(self):
        pkg = IntakePackage(
            source_type=IntakeSourceType.API_PUSH,
            tenant_id="test",
            descriptions=[IntakeDescription(text="only description")],
        )
        assert len(pkg.descriptions) == 1
        assert len(pkg.files) == 0

    def test_creation_with_files_and_descriptions(self):
        pkg = _make_package(
            descriptions=[IntakeDescription(text="cover note", role=DescriptionRole.CASE_NOTE)],
        )
        assert len(pkg.files) == 1
        assert len(pkg.descriptions) == 1

    def test_requires_files_or_descriptions(self):
        with pytest.raises(ValueError, match="at least one file or one description"):
            IntakePackage(
                source_type=IntakeSourceType.EMAIL,
                tenant_id="test_tenant",
            )

    def test_empty_files_and_empty_descriptions_fails(self):
        with pytest.raises(ValueError, match="at least one file or one description"):
            IntakePackage(
                source_type=IntakeSourceType.EMAIL,
                tenant_id="test_tenant",
                files=[],
                descriptions=[],
            )


class TestIntakePackageFields:
    def test_tenant_id_required_nonempty(self):
        with pytest.raises(ValueError):
            _make_package(tenant_id="")

    def test_default_status_is_received(self):
        pkg = _make_package()
        assert pkg.status == IntakePackageStatus.RECEIVED

    def test_source_type_enum_validation(self):
        for st in IntakeSourceType:
            pkg = _make_package(source_type=st)
            assert pkg.source_type == st

    def test_invalid_source_type_rejected(self):
        with pytest.raises(ValueError):
            _make_package(source_type="invalid_source")

    def test_source_metadata_accepts_any_dict(self):
        pkg = _make_package(
            source_metadata={
                "email_from": "user@example.com",
                "email_subject": "Invoice",
                "email_date": "2026-04-09T10:00:00Z",
            },
        )
        assert pkg.source_metadata["email_from"] == "user@example.com"

    def test_package_context_default_empty(self):
        pkg = _make_package()
        assert pkg.package_context == {}

    def test_cross_document_signals_default_empty(self):
        pkg = _make_package()
        assert pkg.cross_document_signals == {}

    def test_provenance_chain_initial_empty(self):
        pkg = _make_package()
        assert pkg.provenance_chain == []

    def test_routing_decision_id_optional(self):
        pkg = _make_package()
        assert pkg.routing_decision_id is None

    def test_review_task_id_optional(self):
        pkg = _make_package()
        assert pkg.review_task_id is None

    def test_received_by_optional(self):
        pkg = _make_package(received_by="admin@test.com")
        assert pkg.received_by == "admin@test.com"


class TestIntakeFile:
    def test_sha256_lowercase_normalization(self):
        f = _make_file(sha256="A" * 64)
        assert f.sha256 == "a" * 64

    def test_sha256_invalid_chars_rejected(self):
        with pytest.raises(ValueError, match="lowercase hex"):
            _make_file(sha256="z" * 64)

    def test_sha256_too_short_rejected(self):
        with pytest.raises(ValueError):
            _make_file(sha256="a" * 63)

    def test_sha256_too_long_rejected(self):
        with pytest.raises(ValueError):
            _make_file(sha256="a" * 65)

    def test_size_bytes_non_negative(self):
        f = _make_file(size_bytes=0)
        assert f.size_bytes == 0

    def test_size_bytes_negative_rejected(self):
        with pytest.raises(ValueError):
            _make_file(size_bytes=-1)

    def test_file_id_auto_generated(self):
        f = _make_file()
        assert isinstance(f.file_id, UUID)

    def test_sequence_index_optional(self):
        f = _make_file(sequence_index=0)
        assert f.sequence_index == 0
        f2 = _make_file()
        assert f2.sequence_index is None

    def test_source_metadata_default_empty(self):
        f = _make_file()
        assert f.source_metadata == {}


class TestIntakeDescription:
    def test_default_role_is_free_text(self):
        d = IntakeDescription(text="Some description")
        assert d.role == DescriptionRole.FREE_TEXT

    def test_all_roles_valid(self):
        for role in DescriptionRole:
            d = IntakeDescription(text="test", role=role)
            assert d.role == role

    def test_association_confidence_bounds(self):
        d = IntakeDescription(text="test", association_confidence=0.5)
        assert d.association_confidence == 0.5

    def test_association_confidence_too_high(self):
        with pytest.raises(ValueError):
            IntakeDescription(text="test", association_confidence=1.5)

    def test_association_confidence_too_low(self):
        with pytest.raises(ValueError):
            IntakeDescription(text="test", association_confidence=-0.1)

    def test_text_nonempty_required(self):
        with pytest.raises(ValueError):
            IntakeDescription(text="")

    def test_association_method_literal_values(self):
        for method in ("rule", "llm", "manual", "explicit"):
            d = IntakeDescription(text="test", association_method=method)
            assert d.association_method == method

    def test_associated_file_ids_default_empty(self):
        d = IntakeDescription(text="test")
        assert d.associated_file_ids == []

    def test_language_optional(self):
        d = IntakeDescription(text="test", language="hu")
        assert d.language == "hu"

    def test_description_id_auto_generated(self):
        d = IntakeDescription(text="test")
        assert isinstance(d.description_id, UUID)


class TestSerialization:
    def test_json_round_trip(self):
        pkg = _make_package()
        data = pkg.model_dump_json()
        restored = IntakePackage.model_validate_json(data)
        assert restored.package_id == pkg.package_id
        assert restored.status == pkg.status
        assert restored.tenant_id == pkg.tenant_id

    def test_dict_round_trip(self):
        pkg = _make_package(
            descriptions=[IntakeDescription(text="note")],
            source_metadata={"key": "value"},
        )
        d = pkg.model_dump()
        restored = IntakePackage.model_validate(d)
        assert restored.package_id == pkg.package_id
        assert len(restored.descriptions) == 1

    def test_file_json_round_trip(self):
        f = _make_file(source_metadata={"email_attachment_id": "att-1"})
        data = f.model_dump_json()
        restored = IntakeFile.model_validate_json(data)
        assert restored.file_id == f.file_id
        assert restored.source_metadata["email_attachment_id"] == "att-1"
