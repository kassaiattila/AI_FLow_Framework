"""AzureDocumentIntelligenceParser — cloud ParserProvider (policy-gated).

Introduced by S96 (Sprint I / UC1 session 3). Wraps Azure's
``prebuilt-layout`` model behind the optional ``[azure-di]`` extra. The
router only routes here when the tenant policy allows cloud AI AND the
``AZURE_DOC_INTEL_ENDPOINT`` env var is present, so the SDK import stays
lazy (``__init__`` does not fail if the extra is not installed — but
``register_default_parsers`` will skip registration).

Source: 101_AIFLOW_v2_COMPONENT_SPEC.md N6,
        110_USE_CASE_FIRST_REPLAN.md §4 Sprint I.
"""

from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog
from pydantic import BaseModel, Field, SecretStr

from aiflow.contracts.parser_result import ParserResult
from aiflow.providers.interfaces import ParserProvider
from aiflow.providers.metadata import ProviderMetadata

if TYPE_CHECKING:
    from aiflow.intake.package import IntakeFile, IntakePackage

__all__ = [
    "AzureDIConfig",
    "AzureDocumentIntelligenceParser",
]

logger = structlog.get_logger(__name__)

_SUPPORTED_MIMES = frozenset(
    {
        "application/pdf",
        "image/png",
        "image/jpeg",
        "image/tiff",
    }
)

_COST_PER_PAGE_USD = 0.001
"""Azure DI Layout model list price (2026-04 lookup)."""

_BYTES_PER_PAGE_HINT = 100_000
"""Fallback byte-per-page used when page_count is unknown."""


class AzureDIConfig(BaseModel):
    """Runtime config for AzureDocumentIntelligenceParser."""

    endpoint: str | None = Field(
        default=None,
        description="Azure DI endpoint URL; falls back to AZURE_DOC_INTEL_ENDPOINT.",
    )
    api_key: SecretStr | None = Field(
        default=None,
        description="Azure DI key; falls back to AZURE_DOC_INTEL_KEY.",
    )
    default_model_id: str = Field(
        default="prebuilt-layout",
        description="Azure DI model id used by begin_analyze_document.",
    )
    timeout_s: int = Field(
        default=120,
        ge=1,
        description="Per-request wall clock timeout (seconds).",
    )

    @classmethod
    def from_env(cls) -> AzureDIConfig:
        return cls(
            endpoint=os.getenv("AZURE_DOC_INTEL_ENDPOINT"),
            api_key=(
                SecretStr(os.environ["AZURE_DOC_INTEL_KEY"])
                if "AZURE_DOC_INTEL_KEY" in os.environ
                else None
            ),
        )


class AzureDocumentIntelligenceParser(ParserProvider):
    """Cloud parser backed by Azure Document Intelligence (prebuilt-layout)."""

    PROVIDER_NAME = "azure_document_intelligence"

    def __init__(self, config: AzureDIConfig | None = None) -> None:
        self._config = config or AzureDIConfig.from_env()
        self._metadata = ProviderMetadata(
            name=self.PROVIDER_NAME,
            version="1.0",
            supported_types=["pdf", "png", "jpg", "tiff"],
            speed_class="normal",
            gpu_required=False,
            cost_class="moderate",
            license="commercial",
        )

    @property
    def metadata(self) -> ProviderMetadata:
        return self._metadata

    async def parse(
        self,
        file: IntakeFile,
        package_context: IntakePackage,
    ) -> ParserResult:
        """Submit ``file`` to Azure DI and map the response to ParserResult."""
        start = time.perf_counter()
        endpoint = self._config.endpoint or os.getenv("AZURE_DOC_INTEL_ENDPOINT")
        key = (
            self._config.api_key.get_secret_value()
            if self._config.api_key is not None
            else os.getenv("AZURE_DOC_INTEL_KEY")
        )
        if not endpoint or not key:
            raise RuntimeError(
                "AzureDocumentIntelligenceParser requires both AZURE_DOC_INTEL_ENDPOINT "
                "and AZURE_DOC_INTEL_KEY to be configured."
            )

        path = Path(file.file_path)
        model_id = self._config.default_model_id
        timeout_s = self._config.timeout_s

        def _do_parse() -> dict[str, Any]:
            from azure.ai.documentintelligence import DocumentIntelligenceClient
            from azure.core.credentials import AzureKeyCredential

            client = DocumentIntelligenceClient(
                endpoint=endpoint,
                credential=AzureKeyCredential(key),
            )
            with path.open("rb") as fh:
                poller = client.begin_analyze_document(
                    model_id=model_id,
                    body=fh,
                )
            result = poller.result(timeout=timeout_s)
            return _result_to_dict(result)

        payload = await asyncio.to_thread(_do_parse)
        duration_ms = (time.perf_counter() - start) * 1000.0
        text = payload.get("content", "") or ""
        tables = payload.get("tables", [])
        page_count = payload.get("page_count", 0)

        parser_result = ParserResult(
            file_id=file.file_id,
            parser_name=self.PROVIDER_NAME,
            text=text,
            markdown=text,
            tables=tables,
            page_count=page_count,
            parse_duration_ms=duration_ms,
            metadata={
                "mime_type": file.mime_type,
                "file_size_bytes": file.size_bytes,
                "parser_used": self.PROVIDER_NAME,
                "model_id": model_id,
                "package_id": str(package_context.package_id),
                "tenant_id": package_context.tenant_id,
            },
        )
        logger.info(
            "azure_di_parse_done",
            file_id=str(file.file_id),
            package_id=str(package_context.package_id),
            chars=len(text),
            pages=page_count,
            duration_ms=round(duration_ms),
        )
        return parser_result

    async def health_check(self) -> bool:
        try:
            await asyncio.to_thread(self._import_check)
        except Exception as exc:
            logger.warning("azure_di_health_check_failed", error=str(exc))
            return False
        return bool(
            (self._config.endpoint or os.getenv("AZURE_DOC_INTEL_ENDPOINT"))
            and (self._config.api_key or os.getenv("AZURE_DOC_INTEL_KEY"))
        )

    @staticmethod
    def _import_check() -> None:
        from azure.ai.documentintelligence import DocumentIntelligenceClient  # noqa: F401

    async def estimate_cost(self, file: IntakeFile) -> float:
        """Estimate at ~0.001 USD / page using a byte-per-page floor."""
        pages = max(1, file.size_bytes // _BYTES_PER_PAGE_HINT)
        return round(pages * _COST_PER_PAGE_USD, 6)

    @classmethod
    def supports_mime(cls, mime_type: str) -> bool:
        return mime_type in _SUPPORTED_MIMES


def _result_to_dict(result: Any) -> dict[str, Any]:
    """Normalize an Azure DI AnalyzeResult into a JSON-friendly dict."""
    content = getattr(result, "content", "") or ""
    pages = list(getattr(result, "pages", None) or [])
    tables_raw = list(getattr(result, "tables", None) or [])

    tables: list[dict[str, Any]] = []
    for idx, table in enumerate(tables_raw):
        caption = ""
        caption_obj = getattr(table, "caption", None)
        if caption_obj is not None:
            caption = getattr(caption_obj, "content", "") or ""
        page_number = None
        bounding_regions = getattr(table, "bounding_regions", None) or []
        if bounding_regions:
            page_number = getattr(bounding_regions[0], "page_number", None)
        tables.append(
            {
                "index": idx,
                "markdown": _table_to_markdown(table),
                "caption": caption,
                "page_number": page_number,
            }
        )

    return {
        "content": content,
        "tables": tables,
        "page_count": len(pages),
    }


def _table_to_markdown(table: Any) -> str:
    """Flatten an Azure DI table into a simple markdown grid."""
    row_count = int(getattr(table, "row_count", 0) or 0)
    column_count = int(getattr(table, "column_count", 0) or 0)
    if row_count <= 0 or column_count <= 0:
        return ""
    grid: list[list[str]] = [["" for _ in range(column_count)] for _ in range(row_count)]
    for cell in getattr(table, "cells", None) or []:
        r = int(getattr(cell, "row_index", 0) or 0)
        c = int(getattr(cell, "column_index", 0) or 0)
        if 0 <= r < row_count and 0 <= c < column_count:
            grid[r][c] = str(getattr(cell, "content", "") or "").strip()
    lines = ["| " + " | ".join(row) + " |" for row in grid]
    if row_count >= 1:
        separator = "| " + " | ".join(["---"] * column_count) + " |"
        lines.insert(1, separator)
    return "\n".join(lines)
