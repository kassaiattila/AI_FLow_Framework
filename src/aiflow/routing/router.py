"""MultiSignalRouter — size + MIME + policy rule-based parser selection.

S95 scope (UC1 session 2):

1. Small born-digital text (<= 5 MB, supported MIME) → ``unstructured_fast``
   with ``docling_standard`` as fallback.
2. Everything else handled by Docling → ``docling_standard``.
3. Cloud-only MIME + ``cloud_ai_allowed=False`` → ``skipped_policy``.

S96 extension (UC1 session 3):

2.5 Scan-hint PDF + ``cloud_ai_allowed=True`` + Azure DI endpoint configured
    → ``azure_document_intelligence`` with ``docling_standard`` fallback.
    Full scan-aware detection (Tesseract/fastText signals, per-page density)
    lives in S97+; S96 ships the basic signal plumbing only.

Source: 101_AIFLOW_v2_COMPONENT_SPEC.md N7,
        110_USE_CASE_FIRST_REPLAN.md §4 Sprint I.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import structlog

from aiflow.contracts.routing_decision import RoutingDecision

if TYPE_CHECKING:
    from aiflow.intake.package import IntakeFile, IntakePackage
    from aiflow.policy.engine import PolicyEngine
    from aiflow.providers.registry import ProviderRegistry

__all__ = [
    "MultiSignalRouter",
    "UNSTRUCTURED_FAST_PARSER",
    "DOCLING_STANDARD_PARSER",
    "AZURE_DOCUMENT_INTELLIGENCE_PARSER",
    "SKIPPED_POLICY",
    "FAST_PATH_SIZE_LIMIT",
    "FAST_PATH_MIMES",
]

logger = structlog.get_logger(__name__)

UNSTRUCTURED_FAST_PARSER = "unstructured_fast"
DOCLING_STANDARD_PARSER = "docling_standard"
AZURE_DOCUMENT_INTELLIGENCE_PARSER = "azure_document_intelligence"
SKIPPED_POLICY = "skipped_policy"

FAST_PATH_SIZE_LIMIT = 5_000_000
"""Byte threshold below which the Unstructured fast-path is preferred."""

FAST_PATH_MIMES = frozenset(
    {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
        "text/html",
        "text/markdown",
    }
)
"""MIME types for which Unstructured's fast partitioner gives equivalent
quality to Docling at a fraction of the CPU cost. Born-digital hint for
PDFs — real scan detection lives in S96+."""

DOCLING_SUPPORTED_MIMES = frozenset(
    {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "text/html",
        "text/markdown",
        "text/plain",
        "image/png",
        "image/jpeg",
        "image/tiff",
    }
)

_IMAGE_MIMES = frozenset({"image/png", "image/jpeg", "image/tiff"})
_SCAN_PDF_PAGE_BYTE_THRESHOLD = 500_000
"""Bytes/page that roughly separates born-digital from scanned PDFs when a
``page_count`` hint is present on IntakeFile.source_metadata."""


class MultiSignalRouter:
    """Rule-based parser router.

    The router does **not** instantiate providers — it only picks a name.
    The caller (DocumentExtractorService.extract_from_package) resolves
    ``chosen_parser`` through the ProviderRegistry.
    """

    def __init__(
        self,
        policy_engine: PolicyEngine,
        registry: ProviderRegistry,
    ) -> None:
        self._policy_engine = policy_engine
        self._registry = registry

    async def decide(
        self,
        package: IntakePackage,
        file: IntakeFile,
    ) -> RoutingDecision:
        """Evaluate rules against ``file`` and emit a RoutingDecision."""
        policy = self._policy_engine.get_for_tenant(package.tenant_id)
        cloud_ai_allowed = bool(getattr(policy, "cloud_ai_allowed", False))
        needs_ocr = _needs_ocr(file)
        azure_endpoint_present = bool(os.getenv("AZURE_DOC_INTEL_ENDPOINT"))

        signals = {
            "size_bytes": file.size_bytes,
            "mime_type": file.mime_type,
            "cloud_ai_allowed": cloud_ai_allowed,
            "needs_ocr": needs_ocr,
            "azure_endpoint_present": azure_endpoint_present,
        }

        # Rule 3 (policy gate): cloud-only MIME with cloud disallowed.
        if (
            file.mime_type not in DOCLING_SUPPORTED_MIMES
            and file.mime_type not in FAST_PATH_MIMES
            and not cloud_ai_allowed
        ):
            decision = RoutingDecision(
                package_id=package.package_id,
                file_id=file.file_id,
                tenant_id=package.tenant_id,
                chosen_parser=SKIPPED_POLICY,
                reason="cloud_ai_disallowed_for_mime",
                signals=signals,
                fallback_chain=[],
                cost_estimate=0.0,
            )
            logger.info(
                "routing_decision_skipped_policy",
                package_id=str(package.package_id),
                file_id=str(file.file_id),
                mime_type=file.mime_type,
            )
            return decision

        # Rule 2.5 (Azure DI): scan-hint + cloud allowed + endpoint configured.
        if needs_ocr and cloud_ai_allowed and azure_endpoint_present:
            decision = RoutingDecision(
                package_id=package.package_id,
                file_id=file.file_id,
                tenant_id=package.tenant_id,
                chosen_parser=AZURE_DOCUMENT_INTELLIGENCE_PARSER,
                reason="scan_pdf_cloud_allowed_azure_di",
                signals=signals,
                fallback_chain=[DOCLING_STANDARD_PARSER],
                cost_estimate=0.0,
            )
            logger.info(
                "routing_decision_azure_di",
                package_id=str(package.package_id),
                file_id=str(file.file_id),
                size_bytes=file.size_bytes,
                mime_type=file.mime_type,
            )
            return decision

        # Rule 1: small born-digital text → fast path.
        if file.size_bytes <= FAST_PATH_SIZE_LIMIT and file.mime_type in FAST_PATH_MIMES:
            decision = RoutingDecision(
                package_id=package.package_id,
                file_id=file.file_id,
                tenant_id=package.tenant_id,
                chosen_parser=UNSTRUCTURED_FAST_PARSER,
                reason="small_born_digital_text_fast_path",
                signals=signals,
                fallback_chain=[DOCLING_STANDARD_PARSER],
                cost_estimate=0.0,
            )
            logger.info(
                "routing_decision_fast_path",
                package_id=str(package.package_id),
                file_id=str(file.file_id),
                size_bytes=file.size_bytes,
                mime_type=file.mime_type,
            )
            return decision

        # Rule 2: everything else (large, DOCX-heavy, images, scans) → Docling.
        decision = RoutingDecision(
            package_id=package.package_id,
            file_id=file.file_id,
            tenant_id=package.tenant_id,
            chosen_parser=DOCLING_STANDARD_PARSER,
            reason=_docling_reason(file.size_bytes, file.mime_type),
            signals=signals,
            fallback_chain=[],
            cost_estimate=0.0,
        )
        logger.info(
            "routing_decision_docling",
            package_id=str(package.package_id),
            file_id=str(file.file_id),
            size_bytes=file.size_bytes,
            mime_type=file.mime_type,
        )
        return decision


def _needs_ocr(file: IntakeFile) -> bool:
    """Emit a scan-hint signal for the router.

    True when the MIME is an image, or when a PDF carries a ``page_count``
    hint in ``source_metadata`` and the bytes/page ratio crosses the scan
    threshold. Without a page hint we default to False on PDFs — the S97
    scan detector will replace this heuristic with a real signal.
    """
    if file.mime_type in _IMAGE_MIMES:
        return True
    if file.mime_type != "application/pdf":
        return False
    meta = file.source_metadata or {}
    hint = meta.get("page_count") if isinstance(meta, dict) else None
    if not isinstance(hint, int) or hint <= 0:
        return False
    return (file.size_bytes / hint) > _SCAN_PDF_PAGE_BYTE_THRESHOLD


def _docling_reason(size_bytes: int, mime_type: str) -> str:
    if size_bytes > FAST_PATH_SIZE_LIMIT:
        return "size_exceeds_fast_path_threshold"
    if mime_type.startswith("image/"):
        return "image_requires_docling_ocr"
    return "mime_outside_fast_path_set"
