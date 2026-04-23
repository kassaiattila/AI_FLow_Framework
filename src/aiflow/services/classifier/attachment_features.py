"""Attachment feature extractor — UC3 Sprint O / S127.

Pure-function module: given a list of :class:`ProcessedAttachment` objects
(produced by :class:`aiflow.tools.attachment_processor.AttachmentProcessor`),
derive a compact :class:`AttachmentFeatures` Pydantic model that S128's
classifier consumes. No I/O, no async, no DB, no LLM — runs in the
orchestrator after attachment processing has already happened.

Image attachments (``image/*``) short-circuit per plan §5 (out of scope this
sprint). Oversize attachments are skipped using
:attr:`UC3AttachmentIntentSettings.max_attachment_mb` against
``metadata["raw_bytes"]`` when present, and failed attachments
(``error != ""``) are skipped silently.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from aiflow.core.config import UC3AttachmentIntentSettings
    from aiflow.tools.attachment_processor import ProcessedAttachment

__all__ = ["AttachmentFeatures", "extract_attachment_features"]


# Hungarian + English invoice number patterns — case-insensitive.
_INVOICE_NUMBER_RE = re.compile(
    r"\b(?:INV|INVOICE|SZAMLA(?:SZAM)?)[-/:\s]*\d{3,}\b",
    re.IGNORECASE,
)

# Total / amount detection — currency symbol or ISO code near a number, *or*
# a total/sum keyword followed by a number with a thousands separator.
_TOTAL_KEYWORDS = (
    r"total|grand\s*total|amount(?:\s+due)?|sum|"
    r"oss?zeg|fizetendo|vegoss?zeg|brutto|netto"
)
_CURRENCY_NEAR_NUMBER_RE = re.compile(
    r"(?:[€$£]|\bUSD\b|\bEUR\b|\bGBP\b|\bHUF\b|\bFt\b)\s*[\d.,\s]{2,}"
    r"|[\d.,\s]{2,}\s*(?:[€$£]|\bUSD\b|\bEUR\b|\bGBP\b|\bHUF\b|\bFt\b)",
    re.IGNORECASE,
)
_TOTAL_KEYWORD_NEAR_NUMBER_RE = re.compile(
    rf"(?:{_TOTAL_KEYWORDS})\s*[:=]?\s*[\d.,\s]{{3,}}",
    re.IGNORECASE,
)

# Word-boundary keyword buckets (case-insensitive).
_KEYWORD_BUCKETS: dict[str, tuple[str, ...]] = {
    "invoice": (
        "invoice",
        "invoices",
        "szamla",
        "szamlat",
        "szamlak",
        "szamlazas",
        "billing",
    ),
    "contract": (
        "contract",
        "agreement",
        "nda",
        "szerzodes",
        "szerzodest",
        "megallapodas",
        "sign",
        "signature",
        "alairas",
    ),
    "support": (
        "support",
        "ticket",
        "incident",
        "issue",
        "error",
        "problem",
        "tamogatas",
        "hibajegy",
    ),
    "report": (
        "report",
        "monthly",
        "quarterly",
        "summary",
        "statement",
        "jelentes",
        "kimutatas",
        "havi",
    ),
}

_IMAGE_MIME_PREFIX = "image/"
_DEFAULT_MAX_MB = 10


class AttachmentFeatures(BaseModel):
    """Compact attachment-derived feature bag (consumed by classifier in S128).

    Keys are deliberately small + JSON-friendly so the orchestrator can drop
    the whole model into ``workflow_runs.output_data.attachment_features``
    via ``model_dump()``.
    """

    invoice_number_detected: bool = False
    total_value_detected: bool = False
    table_count: int = 0
    mime_profile: str = "none"
    keyword_buckets: dict[str, int] = Field(default_factory=dict)
    text_quality: float = 0.0
    attachments_considered: int = 0
    attachments_skipped: int = 0


def extract_attachment_features(
    attachments: list[ProcessedAttachment],
    *,
    settings: UC3AttachmentIntentSettings | None = None,
) -> AttachmentFeatures:
    """Derive :class:`AttachmentFeatures` from a list of processed attachments.

    Pure function — no I/O, no exceptions raised on per-attachment errors.
    Image attachments are skipped (plan §5 out-of-scope). Failed attachments
    (``error != ""``) and attachments with raw bytes exceeding
    ``settings.max_attachment_mb`` are also skipped.
    """
    max_mb = settings.max_attachment_mb if settings is not None else _DEFAULT_MAX_MB
    max_bytes = max_mb * 1024 * 1024

    considered: list[ProcessedAttachment] = []
    skipped = 0
    for att in attachments:
        if att.error:
            skipped += 1
            continue
        if att.mime_type.startswith(_IMAGE_MIME_PREFIX):
            skipped += 1
            continue
        raw = att.metadata.get("raw_bytes")
        if isinstance(raw, (bytes, bytearray)) and len(raw) > max_bytes:
            skipped += 1
            continue
        considered.append(att)

    if not considered:
        return AttachmentFeatures(
            attachments_considered=0,
            attachments_skipped=skipped,
        )

    # Concatenate text once for cheap regex passes.
    blob = "\n".join(a.text for a in considered if a.text)

    invoice_number_detected = bool(_INVOICE_NUMBER_RE.search(blob))
    total_value_detected = bool(
        _CURRENCY_NEAR_NUMBER_RE.search(blob) or _TOTAL_KEYWORD_NEAR_NUMBER_RE.search(blob)
    )

    table_count = sum(len(a.tables) for a in considered)

    # Mime profile = dominant non-empty mime among considered.
    mime_counts = Counter(a.mime_type for a in considered if a.mime_type)
    mime_profile = mime_counts.most_common(1)[0][0] if mime_counts else "unknown"

    keyword_buckets: dict[str, int] = {}
    if blob:
        lowered = blob.lower()
        for bucket, terms in _KEYWORD_BUCKETS.items():
            count = 0
            for term in terms:
                count += len(re.findall(rf"\b{re.escape(term)}\b", lowered))
            if count:
                keyword_buckets[bucket] = count

    quality_scores = [
        float(a.metadata["quality_score"])
        for a in considered
        if isinstance(a.metadata.get("quality_score"), (int, float))
    ]
    text_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0

    return AttachmentFeatures(
        invoice_number_detected=invoice_number_detected,
        total_value_detected=total_value_detected,
        table_count=table_count,
        mime_profile=mime_profile,
        keyword_buckets=keyword_buckets,
        text_quality=round(text_quality, 4),
        attachments_considered=len(considered),
        attachments_skipped=skipped,
    )
