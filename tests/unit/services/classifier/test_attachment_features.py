"""
@test_registry:
    suite: services-unit
    component: services.classifier.attachment_features
    covers: [src/aiflow/services/classifier/attachment_features.py]
    phase: 1
    priority: critical
    estimated_duration_ms: 200
    requires_services: []
    tags: [classifier, attachment, uc3, sprint-o]
"""

from __future__ import annotations

from aiflow.core.config import UC3AttachmentIntentSettings
from aiflow.services.classifier.attachment_features import (
    AttachmentFeatures,
    extract_attachment_features,
)
from aiflow.tools.attachment_processor import ProcessedAttachment

PDF_MIME = "application/pdf"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _att(
    text: str = "",
    *,
    filename: str = "doc.pdf",
    mime_type: str = PDF_MIME,
    tables: list[dict] | None = None,
    metadata: dict | None = None,
    error: str = "",
) -> ProcessedAttachment:
    return ProcessedAttachment(
        filename=filename,
        mime_type=mime_type,
        text=text,
        tables=tables or [],
        metadata=metadata or {},
        error=error,
    )


class TestExtractAttachmentFeatures:
    def test_empty_list_returns_zeroed_features(self) -> None:
        features = extract_attachment_features([])
        assert isinstance(features, AttachmentFeatures)
        assert features.invoice_number_detected is False
        assert features.total_value_detected is False
        assert features.table_count == 0
        assert features.mime_profile == "none"
        assert features.keyword_buckets == {}
        assert features.text_quality == 0.0
        assert features.attachments_considered == 0
        assert features.attachments_skipped == 0

    def test_invoice_number_detected_inv_pattern(self) -> None:
        att = _att(text="Please pay invoice INV-2026-0042 by Friday.", filename="bill.pdf")
        features = extract_attachment_features([att])
        assert features.invoice_number_detected is True

    def test_invoice_like_text_without_regex_match_is_false(self) -> None:
        att = _att(text="See attached invoice for your records.", filename="note.pdf")
        features = extract_attachment_features([att])
        assert features.invoice_number_detected is False
        # 'invoice' word still hits keyword bucket
        assert features.keyword_buckets.get("invoice", 0) >= 1

    def test_total_value_detected_in_huf(self) -> None:
        att = _att(text="Total: 48,500 HUF\nThank you.", filename="invoice.pdf")
        features = extract_attachment_features([att])
        assert features.total_value_detected is True

    def test_contract_keyword_bucket_with_nda(self) -> None:
        att = _att(
            text="Please sign the attached NDA before our next meeting.",
            filename="nda.docx",
            mime_type=DOCX_MIME,
        )
        features = extract_attachment_features([att])
        assert features.keyword_buckets.get("contract", 0) >= 2  # 'sign' + 'NDA'

    def test_support_bucket_not_invoice(self) -> None:
        att = _att(
            text="Support ticket #1234: incident report — login error after upgrade.",
            filename="support.pdf",
        )
        features = extract_attachment_features([att])
        assert features.keyword_buckets.get("support", 0) >= 2
        assert features.invoice_number_detected is False

    def test_table_count_sums_across_attachments(self) -> None:
        a = _att(text="x", tables=[{"id": 1}, {"id": 2}])
        b = _att(text="y", tables=[{"id": 3}], filename="b.pdf")
        features = extract_attachment_features([a, b])
        assert features.table_count == 3

    def test_image_attachment_skipped(self) -> None:
        img = _att(text="OCR-text-from-image", mime_type="image/png", filename="scan.png")
        pdf = _att(text="real pdf text", filename="doc.pdf")
        features = extract_attachment_features([img, pdf])
        assert features.attachments_considered == 1
        assert features.attachments_skipped == 1
        assert features.mime_profile == PDF_MIME

    def test_oversize_attachment_skipped(self) -> None:
        big = _att(
            text="payload",
            filename="big.pdf",
            metadata={"raw_bytes": b"x" * (11 * 1024 * 1024)},
        )
        small = _att(text="small file", filename="small.pdf")
        settings = UC3AttachmentIntentSettings(enabled=True, max_attachment_mb=10)
        features = extract_attachment_features([big, small], settings=settings)
        assert features.attachments_considered == 1
        assert features.attachments_skipped == 1

    def test_failed_attachment_skipped_and_does_not_crash(self) -> None:
        good = _att(text="hello world", filename="good.pdf")
        bad = _att(text="", filename="bad.pdf", error="docling failed")
        features = extract_attachment_features([good, bad])
        assert features.attachments_considered == 1
        assert features.attachments_skipped == 1

    def test_dominant_mime_returned(self) -> None:
        a = _att(text="t1", mime_type=PDF_MIME, filename="a.pdf")
        b = _att(text="t2", mime_type=DOCX_MIME, filename="b.docx")
        c = _att(text="t3", mime_type=DOCX_MIME, filename="c.docx")
        features = extract_attachment_features([a, b, c])
        assert features.mime_profile == DOCX_MIME

    def test_text_quality_mean(self) -> None:
        a = _att(text="x", filename="a.pdf", metadata={"quality_score": 0.8})
        b = _att(text="y", filename="b.pdf", metadata={"quality_score": 0.4})
        c = _att(text="z", filename="c.pdf")  # no quality_score → ignored in mean
        features = extract_attachment_features([a, b, c])
        assert features.text_quality == 0.6

    def test_hu_invoice_number_pattern_matches(self) -> None:
        att = _att(text="Szamlaszam: SZAMLA-2026-0001 fizetendo", filename="hu.pdf")
        features = extract_attachment_features([att])
        assert features.invoice_number_detected is True

    def test_image_only_returns_zeroed_with_skipped_count(self) -> None:
        img = _att(text="x", mime_type="image/jpeg", filename="scan.jpg")
        features = extract_attachment_features([img])
        assert features.attachments_considered == 0
        assert features.attachments_skipped == 1
        assert features.mime_profile == "none"
