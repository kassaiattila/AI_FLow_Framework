"""Shared associator helper tests — Phase 1d G0.2.

@test_registry: unit/intake/association

Source: 01_PLAN/session_S80_v1_4_3_phase_1d_kickoff.md Day 1.
Covers :func:`aiflow.intake.association.resolve_mode_and_associations` — the
pure helper shared by `api/v1/intake.py:upload_package` and (Phase 1d)
every source adapter through :class:`IntakePackageSink`.

Branch coverage: EXPLICIT, FILENAME_MATCH, ORDER, SINGLE_DESCRIPTION, None
(empty descriptions), plus forced-mode pinning and error passthrough.
"""

from __future__ import annotations

import pytest

from aiflow.intake.association import resolve_mode_and_associations
from aiflow.intake.exceptions import FileAssociationError
from aiflow.intake.package import (
    AssociationMode,
    IntakeDescription,
    IntakeFile,
    IntakePackage,
    IntakeSourceType,
)


def _make_file(file_name: str = "doc.pdf") -> IntakeFile:
    return IntakeFile(
        file_path=f"/tmp/{file_name}",
        file_name=file_name,
        mime_type="application/pdf",
        size_bytes=1024,
        sha256="a" * 64,
    )


def _make_desc(text: str = "desc") -> IntakeDescription:
    return IntakeDescription(text=text)


def _make_package(
    files: list[IntakeFile] | None = None,
    descriptions: list[IntakeDescription] | None = None,
) -> IntakePackage:
    return IntakePackage(
        source_type=IntakeSourceType.EMAIL,
        tenant_id="tenant-a",
        files=files if files is not None else [],
        descriptions=descriptions if descriptions is not None else [],
    )


class TestNoDescriptions:
    def test_empty_descriptions_is_noop(self) -> None:
        pkg = _make_package(files=[_make_file()], descriptions=[])

        result = resolve_mode_and_associations(pkg)

        assert result is pkg
        assert pkg.association_mode is None


class TestOrderInferred:
    def test_two_files_two_descriptions_picks_order(self) -> None:
        f1, f2 = _make_file("a.pdf"), _make_file("b.pdf")
        d1, d2 = _make_desc("d1"), _make_desc("d2")
        pkg = _make_package([f1, f2], [d1, d2])

        resolve_mode_and_associations(pkg)

        assert pkg.association_mode is AssociationMode.ORDER
        d1_map = next(d for d in pkg.descriptions if d.description_id == d1.description_id)
        d2_map = next(d for d in pkg.descriptions if d.description_id == d2.description_id)
        assert d1_map.associated_file_ids == [f1.file_id]
        assert d2_map.associated_file_ids == [f2.file_id]


class TestSingleDescriptionInferred:
    def test_one_description_many_files(self) -> None:
        f1, f2, f3 = _make_file("a.pdf"), _make_file("b.pdf"), _make_file("c.pdf")
        d1 = _make_desc("sole")
        pkg = _make_package([f1, f2, f3], [d1])

        resolve_mode_and_associations(pkg)

        assert pkg.association_mode is AssociationMode.SINGLE_DESCRIPTION
        assert set(pkg.descriptions[0].associated_file_ids) == {
            f1.file_id,
            f2.file_id,
            f3.file_id,
        }


class TestFilenameMatchInferred:
    def test_rules_take_precedence_over_order(self) -> None:
        f_inv, f_rec = _make_file("invoice.pdf"), _make_file("receipt.pdf")
        d_inv, d_rec = _make_desc("invoice-desc"), _make_desc("receipt-desc")
        pkg = _make_package([f_inv, f_rec], [d_inv, d_rec])

        rules = [
            (r"^invoice", d_inv.description_id),
            (r"^receipt", d_rec.description_id),
        ]
        resolve_mode_and_associations(pkg, filename_rules=rules)

        assert pkg.association_mode is AssociationMode.FILENAME_MATCH
        d_inv_map = next(d for d in pkg.descriptions if d.description_id == d_inv.description_id)
        d_rec_map = next(d for d in pkg.descriptions if d.description_id == d_rec.description_id)
        assert d_inv_map.associated_file_ids == [f_inv.file_id]
        assert d_rec_map.associated_file_ids == [f_rec.file_id]


class TestExplicitInferred:
    def test_map_takes_precedence_over_everything(self) -> None:
        f1, f2 = _make_file("a.pdf"), _make_file("b.pdf")
        d1, d2 = _make_desc("d1"), _make_desc("d2")
        pkg = _make_package([f1, f2], [d1, d2])

        # Cross-wire: file_a → desc2, file_b → desc1 (not order-pairing)
        explicit = {f1.file_id: d2.description_id, f2.file_id: d1.description_id}
        resolve_mode_and_associations(pkg, explicit_map=explicit)

        assert pkg.association_mode is AssociationMode.EXPLICIT
        d1_map = next(d for d in pkg.descriptions if d.description_id == d1.description_id)
        d2_map = next(d for d in pkg.descriptions if d.description_id == d2.description_id)
        assert d1_map.associated_file_ids == [f2.file_id]
        assert d2_map.associated_file_ids == [f1.file_id]


class TestForcedMode:
    def test_forced_order_is_persisted_even_when_other_inputs_present(self) -> None:
        f1, f2 = _make_file("a.pdf"), _make_file("b.pdf")
        d1, d2 = _make_desc("d1"), _make_desc("d2")
        pkg = _make_package([f1, f2], [d1, d2])

        resolve_mode_and_associations(pkg, forced_mode=AssociationMode.ORDER)

        assert pkg.association_mode is AssociationMode.ORDER


class TestErrorPassthrough:
    def test_associator_error_raises_unchanged(self) -> None:
        f1 = _make_file("only.pdf")
        d1, d2, d3 = _make_desc("d1"), _make_desc("d2"), _make_desc("d3")
        pkg = _make_package([f1], [d1, d2, d3])

        with pytest.raises(FileAssociationError):
            resolve_mode_and_associations(pkg, forced_mode=AssociationMode.ORDER)
