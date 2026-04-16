"""N4 file<->description associator tests — v1.4.1 Phase 1b E3.1-A.

Source: 101_AIFLOW_v2_COMPONENT_TRANSFORMATION_PLAN.md N4
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from aiflow.intake.associator import (
    AssociationError,
    AssociationMode,
    associate,
)
from aiflow.intake.package import (
    IntakeDescription,
    IntakeFile,
    IntakePackage,
    IntakeSourceType,
)


def _make_file(file_name: str = "doc.pdf", **overrides) -> IntakeFile:
    defaults = {
        "file_path": f"/tmp/{file_name}",
        "file_name": file_name,
        "mime_type": "application/pdf",
        "size_bytes": 1024,
        "sha256": "a" * 64,
    }
    defaults.update(overrides)
    return IntakeFile(**defaults)


def _make_desc(text: str = "desc") -> IntakeDescription:
    return IntakeDescription(text=text)


def _make_package(
    files: list[IntakeFile] | None = None,
    descriptions: list[IntakeDescription] | None = None,
) -> IntakePackage:
    return IntakePackage(
        source_type=IntakeSourceType.BATCH_IMPORT,
        tenant_id="tenant_a",
        files=files if files is not None else [_make_file()],
        descriptions=descriptions if descriptions is not None else [_make_desc()],
    )


# ---------------------------------------------------------------- EXPLICIT


class TestExplicit:
    def test_happy_path(self) -> None:
        f1, f2 = _make_file("a.pdf"), _make_file("b.pdf")
        d1, d2 = _make_desc("d1"), _make_desc("d2")
        pkg = _make_package([f1, f2], [d1, d2])

        result = associate(
            pkg,
            mode=AssociationMode.EXPLICIT,
            explicit_map={f1.file_id: d1.description_id, f2.file_id: d2.description_id},
        )

        assert result == {f1.file_id: d1.description_id, f2.file_id: d2.description_id}

    def test_missing_file_id_in_map(self) -> None:
        f1, f2 = _make_file("a.pdf"), _make_file("b.pdf")
        d1 = _make_desc()
        pkg = _make_package([f1, f2], [d1])

        with pytest.raises(AssociationError, match="missing entry"):
            associate(
                pkg,
                mode=AssociationMode.EXPLICIT,
                explicit_map={f1.file_id: d1.description_id},
            )

    def test_unknown_description_id(self) -> None:
        f1 = _make_file()
        d1 = _make_desc()
        pkg = _make_package([f1], [d1])
        stranger = uuid4()

        with pytest.raises(AssociationError, match="unknown description_id"):
            associate(
                pkg,
                mode=AssociationMode.EXPLICIT,
                explicit_map={f1.file_id: stranger},
            )

    def test_empty_map_raises(self) -> None:
        pkg = _make_package()
        with pytest.raises(AssociationError, match="non-empty explicit_map"):
            associate(pkg, mode=AssociationMode.EXPLICIT, explicit_map={})

    def test_none_map_raises(self) -> None:
        pkg = _make_package()
        with pytest.raises(AssociationError, match="non-empty explicit_map"):
            associate(pkg, mode=AssociationMode.EXPLICIT, explicit_map=None)

    def test_map_references_file_not_in_package(self) -> None:
        f1 = _make_file()
        d1 = _make_desc()
        pkg = _make_package([f1], [d1])
        stranger_file = uuid4()

        with pytest.raises(AssociationError, match="not in package"):
            associate(
                pkg,
                mode=AssociationMode.EXPLICIT,
                explicit_map={
                    f1.file_id: d1.description_id,
                    stranger_file: d1.description_id,
                },
            )


# ---------------------------------------------------------- FILENAME_MATCH


class TestFilenameMatch:
    def test_happy_path_regex(self) -> None:
        inv = _make_file("invoice-001.pdf")
        note = _make_file("note-001.pdf")
        d_inv, d_note = _make_desc("invoices"), _make_desc("notes")
        pkg = _make_package([inv, note], [d_inv, d_note])

        result = associate(
            pkg,
            mode=AssociationMode.FILENAME_MATCH,
            filename_rules=[
                (r"^invoice-", d_inv.description_id),
                (r"^note-", d_note.description_id),
            ],
        )

        assert result == {inv.file_id: d_inv.description_id, note.file_id: d_note.description_id}

    def test_no_rule_matches(self) -> None:
        f = _make_file("random.pdf")
        d = _make_desc()
        pkg = _make_package([f], [d])

        with pytest.raises(AssociationError, match="no filename rule matched"):
            associate(
                pkg,
                mode=AssociationMode.FILENAME_MATCH,
                filename_rules=[(r"^invoice-", d.description_id)],
            )

    def test_ambiguous_two_rules_match(self) -> None:
        f = _make_file("invoice-note.pdf")
        d1, d2 = _make_desc("inv"), _make_desc("notes")
        pkg = _make_package([f], [d1, d2])

        with pytest.raises(AssociationError, match="ambiguous filename match"):
            associate(
                pkg,
                mode=AssociationMode.FILENAME_MATCH,
                filename_rules=[
                    (r"invoice", d1.description_id),
                    (r"note", d2.description_id),
                ],
            )

    def test_empty_rules_raises(self) -> None:
        pkg = _make_package()
        with pytest.raises(AssociationError, match="non-empty filename_rules"):
            associate(pkg, mode=AssociationMode.FILENAME_MATCH, filename_rules=[])

    def test_rule_references_unknown_description(self) -> None:
        f = _make_file("a.pdf")
        d = _make_desc()
        pkg = _make_package([f], [d])
        stranger = uuid4()

        with pytest.raises(AssociationError, match="unknown description_id"):
            associate(
                pkg,
                mode=AssociationMode.FILENAME_MATCH,
                filename_rules=[(r".*", stranger)],
            )

    def test_invalid_regex_raises(self) -> None:
        f = _make_file()
        d = _make_desc()
        pkg = _make_package([f], [d])

        with pytest.raises(AssociationError, match="invalid regex"):
            associate(
                pkg,
                mode=AssociationMode.FILENAME_MATCH,
                filename_rules=[(r"[unclosed", d.description_id)],
            )


# ---------------------------------------------------------------- ORDER


class TestOrder:
    def test_happy_path(self) -> None:
        f1, f2 = _make_file("a.pdf"), _make_file("b.pdf")
        d1, d2 = _make_desc("x"), _make_desc("y")
        pkg = _make_package([f1, f2], [d1, d2])

        result = associate(pkg, mode=AssociationMode.ORDER)

        assert result == {f1.file_id: d1.description_id, f2.file_id: d2.description_id}

    def test_length_mismatch_raises(self) -> None:
        pkg = _make_package(
            [_make_file("a.pdf"), _make_file("b.pdf")],
            [_make_desc("only")],
        )

        with pytest.raises(AssociationError, match="len\\(files\\) == len\\(descriptions\\)"):
            associate(pkg, mode=AssociationMode.ORDER)


# ------------------------------------------------------ SINGLE_DESCRIPTION


class TestSingleDescription:
    def test_happy_path(self) -> None:
        f1, f2, f3 = _make_file("a"), _make_file("b"), _make_file("c")
        d = _make_desc("the one note")
        pkg = _make_package([f1, f2, f3], [d])

        result = associate(pkg, mode=AssociationMode.SINGLE_DESCRIPTION)

        assert result == {
            f1.file_id: d.description_id,
            f2.file_id: d.description_id,
            f3.file_id: d.description_id,
        }

    def test_multiple_descriptions_raises(self) -> None:
        pkg = _make_package(
            [_make_file("a")],
            [_make_desc("x"), _make_desc("y")],
        )
        with pytest.raises(AssociationError, match="exactly one description"):
            associate(pkg, mode=AssociationMode.SINGLE_DESCRIPTION)


# -------------------------------------------------------------- edge cases


class TestEmptyPackages:
    def test_no_files_returns_empty(self) -> None:
        pkg = IntakePackage(
            source_type=IntakeSourceType.API_PUSH,
            tenant_id="t",
            descriptions=[_make_desc()],
        )
        assert associate(pkg) == {}

    def test_no_descriptions_returns_empty(self) -> None:
        pkg = IntakePackage(
            source_type=IntakeSourceType.API_PUSH,
            tenant_id="t",
            files=[_make_file()],
        )
        assert associate(pkg) == {}


# ---------------------------------------------------------------- precedence


class TestPrecedence:
    def test_explicit_wins_over_filename(self) -> None:
        f = _make_file("invoice-1.pdf")
        d_inv, d_other = _make_desc("inv"), _make_desc("other")
        pkg = _make_package([f], [d_inv, d_other])

        result = associate(
            pkg,
            explicit_map={f.file_id: d_other.description_id},
            filename_rules=[(r"invoice", d_inv.description_id)],
        )

        assert result == {f.file_id: d_other.description_id}

    def test_filename_wins_over_order(self) -> None:
        f1, f2 = _make_file("invoice-1.pdf"), _make_file("note-1.pdf")
        d_inv, d_note = _make_desc("inv"), _make_desc("note")
        pkg = _make_package([f1, f2], [d_inv, d_note])

        result = associate(
            pkg,
            filename_rules=[
                (r"invoice", d_inv.description_id),
                (r"note", d_note.description_id),
            ],
        )

        assert result == {f1.file_id: d_inv.description_id, f2.file_id: d_note.description_id}

    def test_order_wins_over_single(self) -> None:
        f1, f2 = _make_file("a"), _make_file("b")
        d1, d2 = _make_desc("d1"), _make_desc("d2")
        pkg = _make_package([f1, f2], [d1, d2])

        result = associate(pkg)

        assert result == {f1.file_id: d1.description_id, f2.file_id: d2.description_id}

    def test_autodetect_falls_back_to_single(self) -> None:
        f1, f2 = _make_file("a"), _make_file("b")
        d = _make_desc("only")
        pkg = _make_package([f1, f2], [d])

        result = associate(pkg)

        assert result == {f1.file_id: d.description_id, f2.file_id: d.description_id}

    def test_autodetect_raises_when_nothing_works(self) -> None:
        f1, f2, f3 = _make_file("a"), _make_file("b"), _make_file("c")
        d1, d2 = _make_desc("d1"), _make_desc("d2")
        pkg = _make_package([f1, f2, f3], [d1, d2])

        with pytest.raises(AssociationError, match="no association mode produced"):
            associate(pkg)


# ----------------------------------------------------------------- misc


class TestMisc:
    def test_invalid_mode_string_raises_valueerror(self) -> None:
        pkg = _make_package()
        with pytest.raises(ValueError):
            associate(pkg, mode="invalid_mode")

    def test_string_mode_accepted(self) -> None:
        f1, f2 = _make_file("a"), _make_file("b")
        d1, d2 = _make_desc("d1"), _make_desc("d2")
        pkg = _make_package([f1, f2], [d1, d2])

        result = associate(pkg, mode="order")

        assert result == {f1.file_id: d1.description_id, f2.file_id: d2.description_id}

    def test_result_is_deterministic(self) -> None:
        files = [_make_file(f"f{i}.pdf") for i in range(5)]
        descs = [_make_desc(f"d{i}") for i in range(5)]
        pkg = _make_package(files, descs)

        r1 = associate(pkg, mode=AssociationMode.ORDER)
        r2 = associate(pkg, mode=AssociationMode.ORDER)

        assert list(r1.keys()) == list(r2.keys())
        assert list(r1.values()) == list(r2.values())
        assert r1 == r2

    def test_result_keys_are_file_ids_values_are_description_ids(self) -> None:
        f = _make_file()
        d = _make_desc()
        pkg = _make_package([f], [d])

        result = associate(pkg, mode=AssociationMode.SINGLE_DESCRIPTION)

        key, value = next(iter(result.items()))
        assert isinstance(key, UUID)
        assert isinstance(value, UUID)
        assert key == f.file_id
        assert value == d.description_id
