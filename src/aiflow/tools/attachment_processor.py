"""Multi-layer attachment processor - docling (local) -> Azure DI (cloud) -> LLM vision."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import structlog
from pydantic import BaseModel, Field

__all__ = ["AttachmentProcessor", "ProcessedAttachment", "AttachmentConfig"]
logger = structlog.get_logger(__name__)


class AttachmentConfig(BaseModel):
    primary_processor: str = "docling"
    fallback_processor: str = "azure_di"
    azure_enabled: bool = False
    azure_endpoint: str = ""
    azure_api_key: str = ""
    azure_model: str = "prebuilt-layout"
    max_size_mb: int = 25
    quality_threshold: float = 0.5  # Below this, escalate to Azure DI


class ProcessedAttachment(BaseModel):
    filename: str
    mime_type: str = ""
    text: str = ""
    markdown: str = ""
    tables: list[dict] = Field(default_factory=list)
    extracted_fields: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    processor_used: str = ""
    error: str = ""


class AttachmentProcessor:
    """Three-layer attachment processor: docling -> Azure DI -> LLM vision."""

    DOCLING_TYPES = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "text/html",
        "text/markdown",
        "text/plain",
    }
    OCR_TYPES = {"image/png", "image/jpeg", "image/tiff", "image/bmp"}

    def __init__(self, config: AttachmentConfig | None = None):
        self.config = config or AttachmentConfig()

    async def process(self, filename: str, content: bytes, mime_type: str) -> ProcessedAttachment:
        """Process attachment with intelligent routing.

        Cost-optimized 3-layer strategy:
        1. Docling (local, free, fast) - always try first for supported types
        2. Azure DI (cloud, paid) - ONLY when docling fails quality check:
           - Empty/too short text vs file size (= likely scan/image PDF)
           - Image files (PNG/JPG/TIFF) needing OCR
           - Docling returned text but quality is poor (ratio check)
        3. LLM Vision - images where text extraction isn't enough

        Azure DI cost: ~$1-10 per 1000 pages. Used sparingly.
        """
        if len(content) > self.config.max_size_mb * 1024 * 1024:
            return ProcessedAttachment(
                filename=filename, error=f"File too large: {len(content)} bytes"
            )

        file_size_kb = len(content) / 1024

        # --- Images: always need OCR (Azure DI or LLM Vision) ---
        if mime_type in self.OCR_TYPES:
            if self.config.azure_enabled:
                result = await self._process_azure(filename, content, mime_type)
                if result.text:
                    logger.info("azure_di_ocr_image", filename=filename, chars=len(result.text))
                    return result
            # Fallback: LLM Vision for images
            return await self._process_llm_vision(filename, content, mime_type)

        # --- Documents (PDF/DOCX/XLSX etc): try docling first ---
        if mime_type in self.DOCLING_TYPES or self._extension_matches_docling(filename):
            result = await self._process_docling(filename, content)

            if result.text:
                # Structural quality score (multi-factor, not just char count)
                quality = _compute_quality_score(result, file_size_kb)
                result.metadata["quality_score"] = round(quality.score, 3)
                result.metadata["quality_factors"] = quality.factors

                if quality.score < self.config.quality_threshold:
                    logger.info(
                        "docling_quality_low",
                        filename=filename,
                        score=round(quality.score, 3),
                        factors=quality.factors,
                    )
                    # Escalate to Azure DI for better extraction
                    if self.config.azure_enabled:
                        azure_result = await self._process_azure(filename, content, mime_type)
                        if azure_result.text:
                            azure_quality = _compute_quality_score(azure_result, file_size_kb)
                            azure_result.metadata["quality_score"] = round(azure_quality.score, 3)
                            azure_result.metadata["quality_factors"] = azure_quality.factors
                            if azure_quality.score > quality.score:
                                logger.info(
                                    "azure_di_improved",
                                    filename=filename,
                                    docling_score=round(quality.score, 3),
                                    azure_score=round(azure_quality.score, 3),
                                )
                                return azure_result
                        logger.info("azure_di_no_improvement", filename=filename)

                # Docling result is good enough
                return result

            # Docling returned empty - try Azure DI
            logger.info("docling_empty", filename=filename, file_kb=round(file_size_kb))
            if self.config.azure_enabled:
                result = await self._process_azure(filename, content, mime_type)
                if result.text:
                    return result

        return ProcessedAttachment(
            filename=filename,
            mime_type=mime_type,
            error="Unsupported format or all processors failed",
            processor_used="none",
        )

    async def _process_docling(self, filename: str, content: bytes) -> ProcessedAttachment:
        try:
            from aiflow.ingestion.parsers.docling_parser import DoclingParser

            parser = DoclingParser()

            with tempfile.NamedTemporaryFile(suffix=Path(filename).suffix, delete=False) as f:
                f.write(content)
                f.flush()
                tmp_path = f.name

            parsed = parser.parse(tmp_path)
            Path(tmp_path).unlink(missing_ok=True)

            return ProcessedAttachment(
                filename=filename,
                text=parsed.text,
                markdown=parsed.markdown,
                tables=[t.model_dump() for t in parsed.tables],
                metadata=parsed.metadata,
                processor_used="docling",
            )
        except Exception as e:
            logger.warning("docling_process_failed", filename=filename, error=str(e))
            return ProcessedAttachment(
                filename=filename, error=str(e), processor_used="docling_failed"
            )

    async def _process_azure(
        self, filename: str, content: bytes, mime_type: str
    ) -> ProcessedAttachment:
        try:
            from aiflow.tools.azure_doc_intelligence import AzureDocIntelligence

            client = AzureDocIntelligence(self.config.azure_endpoint, self.config.azure_api_key)
            result = await client.analyze(content, model=self.config.azure_model)

            return ProcessedAttachment(
                filename=filename,
                text=result.get("text", ""),
                markdown=result.get("markdown", ""),
                tables=result.get("tables", []),
                extracted_fields=result.get("key_value_pairs", {}),
                metadata={"azure_model": self.config.azure_model},
                processor_used="azure_di",
            )
        except Exception as e:
            logger.warning("azure_process_failed", filename=filename, error=str(e))
            return ProcessedAttachment(
                filename=filename, error=str(e), processor_used="azure_failed"
            )

    async def _process_llm_vision(
        self, filename: str, content: bytes, mime_type: str
    ) -> ProcessedAttachment:
        import base64

        b64 = base64.b64encode(content).decode("ascii")
        # Use ModelClient for vision (placeholder - actual implementation depends on LLM)
        return ProcessedAttachment(
            filename=filename,
            text=f"[Image: {filename}, {len(content)} bytes - LLM vision analysis pending]",
            metadata={"base64_length": len(b64)},
            processor_used="llm_vision_placeholder",
        )

    def _extension_matches_docling(self, filename: str) -> bool:
        ext = Path(filename).suffix.lower()
        return ext in {
            ".pdf",
            ".docx",
            ".pptx",
            ".xlsx",
            ".html",
            ".htm",
            ".md",
            ".txt",
        }


# ---------------------------------------------------------------------------
# Quality scoring
# ---------------------------------------------------------------------------


class _QualityResult:
    """Multi-factor quality assessment for extracted text."""

    __slots__ = ("score", "factors")

    def __init__(self, score: float, factors: dict[str, float]):
        self.score = score
        self.factors = factors


def _compute_quality_score(result: ProcessedAttachment, file_size_kb: float) -> _QualityResult:
    """Compute structural quality score for extracted text (0.0 - 1.0).

    Factors (weighted):
    - text_density:     chars per KB of original file (scan detection)
    - word_coherence:   ratio of real words (not broken fragments)
    - table_extraction: tables found vs file size expectation
    - line_structure:   meaningful lines vs noise lines
    - content_length:   absolute text length reasonableness
    """
    import re

    text = result.text
    factors: dict[str, float] = {}

    # 1. Text density: chars per KB (low = likely scan/image PDF)
    chars_per_kb = len(text) / max(file_size_kb, 1)
    if chars_per_kb >= 10:
        factors["text_density"] = 1.0
    elif chars_per_kb >= 2:
        factors["text_density"] = chars_per_kb / 10.0
    else:
        factors["text_density"] = max(0.0, chars_per_kb / 5.0)

    # 2. Word coherence: ratio of words with 3+ letters vs fragments
    words = text.split()
    if words:
        real_words = sum(1 for w in words if len(w) >= 3 and re.match(r"[\w]+", w))
        factors["word_coherence"] = min(1.0, real_words / len(words))
    else:
        factors["word_coherence"] = 0.0

    # 3. Table extraction: bonus if tables were found (expected for PDF/XLSX)
    if result.tables:
        factors["table_quality"] = min(1.0, len(result.tables) * 0.3 + 0.4)
    else:
        # No tables: neutral if small file, penalty if large (tables expected)
        factors["table_quality"] = 0.5 if file_size_kb < 200 else 0.3

    # 4. Line structure: ratio of meaningful lines (not empty/noise)
    lines = text.split("\n")
    if lines:
        meaningful = sum(
            1
            for line in lines
            if len(line.strip()) > 10  # More than just a number or header artifact
        )
        factors["line_structure"] = min(1.0, meaningful / max(len(lines), 1))
    else:
        factors["line_structure"] = 0.0

    # 5. Content length: absolute minimum for the file to be considered "extracted"
    if len(text) >= 500:
        factors["content_length"] = 1.0
    elif len(text) >= 100:
        factors["content_length"] = len(text) / 500.0
    elif len(text) > 0:
        factors["content_length"] = 0.1
    else:
        factors["content_length"] = 0.0

    # Weighted average
    weights = {
        "text_density": 0.25,
        "word_coherence": 0.25,
        "table_quality": 0.15,
        "line_structure": 0.20,
        "content_length": 0.15,
    }
    score = sum(factors[k] * weights[k] for k in weights)

    return _QualityResult(score=min(1.0, max(0.0, score)), factors=factors)
