"""Shared associator helper — pure function, no FastAPI dependencies.

Source: extracted from ``api/v1/intake.py:upload_package`` in Phase 1d / G0.2
so that all 5 source adapters (Email, File, Folder, Batch, Api) reuse the
same associator + mode-inference logic via the Phase 1d sink pattern.

The helper mutates the package's descriptions (``associated_file_ids``) and
sets ``package.association_mode`` to the mode that was forced OR inferred,
mirroring the precedence of :func:`aiflow.intake.associator.associate`.

Raises :class:`FileAssociationError` on associator failure; callers decide
how to surface (HTTP 422, adapter reject, worker log+drop).
"""

from __future__ import annotations

from uuid import UUID

from aiflow.intake.associator import associate
from aiflow.intake.package import AssociationMode, IntakePackage

__all__ = [
    "resolve_mode_and_associations",
]


def resolve_mode_and_associations(
    package: IntakePackage,
    *,
    forced_mode: AssociationMode | None = None,
    filename_rules: list[tuple[str, UUID]] | None = None,
    explicit_map: dict[UUID, UUID] | None = None,
) -> IntakePackage:
    """Run the N4 associator and persist the chosen mode on the package.

    No-ops when ``package.descriptions`` is empty (returns the package
    unchanged). When ``forced_mode`` is None, walks the associator precedence
    chain (EXPLICIT > FILENAME_MATCH > ORDER > SINGLE_DESCRIPTION) and
    records the first mode that produced a mapping via :func:`_infer_mode`.

    Args:
        package: IntakePackage to associate. Mutated in place.
        forced_mode: If provided, pin the associator to this mode (and
            persist it on the package).
        filename_rules: ``[(pattern, description_id), ...]`` for FILENAME_MATCH.
        explicit_map: ``{file_id: description_id}`` for EXPLICIT.

    Returns:
        The same package instance, with ``descriptions[].associated_file_ids``
        populated and ``association_mode`` set (or left None when there are
        no descriptions to associate).
    """
    if not package.descriptions:
        return package

    mapping = associate(
        package,
        mode=forced_mode,
        explicit_map=explicit_map,
        filename_rules=filename_rules,
    )

    desc_to_files: dict[UUID, list[UUID]] = {d.description_id: [] for d in package.descriptions}
    for file_id, desc_id in mapping.items():
        desc_to_files.setdefault(desc_id, []).append(file_id)
    for desc in package.descriptions:
        desc.associated_file_ids = desc_to_files.get(desc.description_id, [])

    package.association_mode = (
        forced_mode
        if forced_mode is not None
        else _infer_mode(
            package=package,
            filename_rules=filename_rules,
            explicit_map=explicit_map,
        )
    )
    return package


def _infer_mode(
    *,
    package: IntakePackage,
    filename_rules: list[tuple[str, UUID]] | None,
    explicit_map: dict[UUID, UUID] | None,
) -> AssociationMode | None:
    """Mirror :func:`associate` precedence to persist which mode was picked."""
    if explicit_map:
        return AssociationMode.EXPLICIT
    if filename_rules:
        return AssociationMode.FILENAME_MATCH
    if len(package.files) == len(package.descriptions) and len(package.files) > 0:
        return AssociationMode.ORDER
    if len(package.descriptions) == 1 and package.files:
        return AssociationMode.SINGLE_DESCRIPTION
    return None
