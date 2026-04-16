"""N4 file<->description associator — v1.4.1 Phase 1b Week 3 Day 11 (E3.1-A).

Domain logic for linking IntakePackage files to descriptions.

Source: 101_AIFLOW_v2_COMPONENT_TRANSFORMATION_PLAN.md N4.

Four association modes, in precedence order:
    1. EXPLICIT           — caller-provided ``description_id -> file_id`` map
    2. FILENAME_MATCH     — regex/glob rules per description
    3. ORDER              — ordinal pairing (description[i] <-> file[i])
    4. SINGLE_DESCRIPTION — exactly one description applies to all files

When ``mode`` is None, auto-detection walks the precedence chain and returns
the first successful mode. ``AssociationError`` is raised only when every
candidate mode fails; individual modes raise the same error.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from enum import Enum
from uuid import UUID

from aiflow.intake.exceptions import FileAssociationError
from aiflow.intake.package import IntakePackage

__all__ = [
    "AssociationError",
    "AssociationMode",
    "associate",
]


AssociationError = FileAssociationError


class AssociationMode(str, Enum):
    """Association strategy (precedence order: explicit > filename > order > single)."""

    EXPLICIT = "explicit"
    FILENAME_MATCH = "filename_match"
    ORDER = "order"
    SINGLE_DESCRIPTION = "single_description"


_PRECEDENCE: tuple[AssociationMode, ...] = (
    AssociationMode.EXPLICIT,
    AssociationMode.FILENAME_MATCH,
    AssociationMode.ORDER,
    AssociationMode.SINGLE_DESCRIPTION,
)


def associate(
    package: IntakePackage,
    *,
    mode: AssociationMode | str | None = None,
    explicit_map: dict[UUID, UUID] | None = None,
    filename_rules: Iterable[tuple[str, UUID]] | None = None,
) -> dict[UUID, UUID]:
    """Associate files to descriptions. Returns ``{file_id: description_id}``.

    Precedence when ``mode is None``: explicit > filename_match > order > single_description.
    First mode that can produce a complete mapping wins.

    Args:
        package: IntakePackage whose files/descriptions drive the mapping.
        mode: Force a specific mode, or None for auto-detect.
        explicit_map: ``{file_id: description_id}`` pre-built map for EXPLICIT.
        filename_rules: ``[(pattern, description_id), ...]`` for FILENAME_MATCH.
            Patterns are Python regexes matched with ``re.search`` against
            ``file_name`` (case-sensitive). Exactly one rule must match each file;
            multiple matching rules raise AssociationError.

    Returns:
        Mapping from file_id to description_id. Empty dict when the package
        has zero files OR zero descriptions (nothing to associate).

    Raises:
        AssociationError: No mode produced a complete mapping.
        ValueError: ``mode`` is a string that is not a valid AssociationMode.
    """
    if mode is not None and not isinstance(mode, AssociationMode):
        mode = AssociationMode(mode)

    if not package.files or not package.descriptions:
        return {}

    if mode is not None:
        return _run_mode(
            mode,
            package=package,
            explicit_map=explicit_map,
            filename_rules=filename_rules,
        )

    last_error: AssociationError | None = None
    for candidate in _PRECEDENCE:
        try:
            return _run_mode(
                candidate,
                package=package,
                explicit_map=explicit_map,
                filename_rules=filename_rules,
            )
        except AssociationError as exc:
            last_error = exc
            continue

    raise AssociationError(
        "no association mode produced a complete mapping",
        details={"last_error": str(last_error) if last_error else None},
    )


def _run_mode(
    mode: AssociationMode,
    *,
    package: IntakePackage,
    explicit_map: dict[UUID, UUID] | None,
    filename_rules: Iterable[tuple[str, UUID]] | None,
) -> dict[UUID, UUID]:
    if mode is AssociationMode.EXPLICIT:
        return _explicit(package, explicit_map)
    if mode is AssociationMode.FILENAME_MATCH:
        return _filename_match(package, filename_rules)
    if mode is AssociationMode.ORDER:
        return _order(package)
    if mode is AssociationMode.SINGLE_DESCRIPTION:
        return _single_description(package)
    raise AssociationError(f"unsupported association mode: {mode!r}")


def _explicit(
    package: IntakePackage,
    explicit_map: dict[UUID, UUID] | None,
) -> dict[UUID, UUID]:
    if not explicit_map:
        raise AssociationError("EXPLICIT mode requires a non-empty explicit_map")

    file_ids = {f.file_id for f in package.files}
    desc_ids = {d.description_id for d in package.descriptions}

    result: dict[UUID, UUID] = {}
    for file_id in (f.file_id for f in package.files):
        desc_id = explicit_map.get(file_id)
        if desc_id is None:
            raise AssociationError(
                f"EXPLICIT map missing entry for file_id={file_id}",
                details={"file_id": str(file_id)},
            )
        if desc_id not in desc_ids:
            raise AssociationError(
                f"EXPLICIT map references unknown description_id={desc_id}",
                details={"file_id": str(file_id), "description_id": str(desc_id)},
            )
        result[file_id] = desc_id

    extra = set(explicit_map) - file_ids
    if extra:
        raise AssociationError(
            "EXPLICIT map references file_id(s) not in package",
            details={"unknown_file_ids": sorted(str(fid) for fid in extra)},
        )

    return result


def _filename_match(
    package: IntakePackage,
    filename_rules: Iterable[tuple[str, UUID]] | None,
) -> dict[UUID, UUID]:
    rules = list(filename_rules) if filename_rules is not None else []
    if not rules:
        raise AssociationError("FILENAME_MATCH mode requires a non-empty filename_rules list")

    desc_ids = {d.description_id for d in package.descriptions}
    compiled: list[tuple[re.Pattern[str], UUID]] = []
    for pattern, desc_id in rules:
        if desc_id not in desc_ids:
            raise AssociationError(
                f"filename rule references unknown description_id={desc_id}",
                details={"pattern": pattern, "description_id": str(desc_id)},
            )
        try:
            compiled.append((re.compile(pattern), desc_id))
        except re.error as exc:
            raise AssociationError(
                f"invalid regex in filename rule: {pattern!r}",
                details={"pattern": pattern, "error": str(exc)},
            ) from exc

    result: dict[UUID, UUID] = {}
    for file in package.files:
        matches = [desc_id for regex, desc_id in compiled if regex.search(file.file_name)]
        if not matches:
            raise AssociationError(
                f"no filename rule matched file_name={file.file_name!r}",
                details={"file_id": str(file.file_id), "file_name": file.file_name},
            )
        unique = set(matches)
        if len(unique) > 1:
            raise AssociationError(
                f"ambiguous filename match for {file.file_name!r} (multiple descriptions matched)",
                details={
                    "file_id": str(file.file_id),
                    "file_name": file.file_name,
                    "matched_description_ids": sorted(str(d) for d in unique),
                },
            )
        result[file.file_id] = matches[0]

    return result


def _order(package: IntakePackage) -> dict[UUID, UUID]:
    if len(package.files) != len(package.descriptions):
        raise AssociationError(
            "ORDER mode requires len(files) == len(descriptions)",
            details={
                "n_files": len(package.files),
                "n_descriptions": len(package.descriptions),
            },
        )
    return {
        file.file_id: desc.description_id
        for file, desc in zip(package.files, package.descriptions, strict=True)
    }


def _single_description(package: IntakePackage) -> dict[UUID, UUID]:
    if len(package.descriptions) != 1:
        raise AssociationError(
            "SINGLE_DESCRIPTION mode requires exactly one description",
            details={"n_descriptions": len(package.descriptions)},
        )
    desc_id = package.descriptions[0].description_id
    return {file.file_id: desc_id for file in package.files}
