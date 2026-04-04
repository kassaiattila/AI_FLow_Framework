"""Free-text extraction — answer arbitrary queries against a document.

Unlike structured extraction (which uses predefined field schemas),
free-text extraction lets users ask ad-hoc questions about document content.
"""
from __future__ import annotations

import json
import time
from typing import Any

import structlog
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from aiflow.services.base import BaseService, ServiceConfig

__all__ = [
    "FreeTextQuery",
    "FreeTextResult",
    "FreeTextExtractionResponse",
    "FreeTextExtractorService",
]

logger = structlog.get_logger(__name__)


class FreeTextQuery(BaseModel):
    """A single query to answer from document text."""

    query: str
    hint: str = ""


class FreeTextResult(BaseModel):
    """Result for a single free-text query."""

    query: str
    answer: str
    confidence: float = 0.0
    source_span: str = ""


class FreeTextExtractionResponse(BaseModel):
    """Response containing all query results."""

    document_id: str
    results: list[FreeTextResult] = Field(default_factory=list)
    extraction_time_ms: float = 0.0
    model_used: str = ""
    source: str = "backend"


class FreeTextExtractorConfig(ServiceConfig):
    """Config for the free-text extraction service."""

    default_model: str = "openai/gpt-4o-mini"
    max_queries: int = 20
    max_document_chars: int = 30000


class FreeTextExtractorService(BaseService):
    """Extracts answers to arbitrary queries from document text via LLM."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        config: FreeTextExtractorConfig | None = None,
    ) -> None:
        self._config = config or FreeTextExtractorConfig()
        self._session_factory = session_factory
        super().__init__(self._config)

    @property
    def service_name(self) -> str:
        return "free_text_extractor"

    @property
    def service_description(self) -> str:
        return "Free-text query extraction from documents via LLM"

    async def _start(self) -> None:
        pass

    async def _stop(self) -> None:
        pass

    async def health_check(self) -> bool:
        return True

    async def extract(
        self,
        document_id: str,
        queries: list[FreeTextQuery],
        model: str | None = None,
    ) -> FreeTextExtractionResponse:
        """Extract answers to queries from a stored document.

        1. Load document text from DB (invoices table raw_text or direct text)
        2. Send document + queries to LLM
        3. Parse structured JSON response
        4. Log extraction attempt
        """
        start = time.time()
        model = model or self._config.default_model

        if len(queries) > self._config.max_queries:
            queries = queries[: self._config.max_queries]

        # Load document text from DB
        doc_text = await self._load_document_text(document_id)
        if not doc_text:
            return FreeTextExtractionResponse(
                document_id=document_id,
                results=[
                    FreeTextResult(query=q.query, answer="Document not found", confidence=0.0)
                    for q in queries
                ],
                extraction_time_ms=(time.time() - start) * 1000,
                model_used=model,
            )

        # Truncate to max chars
        doc_text = doc_text[: self._config.max_document_chars]

        # Call LLM
        results = await self._call_llm(doc_text, queries, model)

        elapsed = (time.time() - start) * 1000

        # Log extraction
        await self._log_extraction(document_id, queries, results, elapsed, model)

        self._logger.info(
            "free_text_extracted",
            document_id=document_id,
            queries=len(queries),
            time_ms=round(elapsed),
        )

        return FreeTextExtractionResponse(
            document_id=document_id,
            results=results,
            extraction_time_ms=elapsed,
            model_used=model,
        )

    async def extract_from_text(
        self,
        document_text: str,
        queries: list[FreeTextQuery],
        model: str | None = None,
    ) -> list[FreeTextResult]:
        """Extract answers from provided text (no DB lookup)."""
        model = model or self._config.default_model
        doc_text = document_text[: self._config.max_document_chars]
        return await self._call_llm(doc_text, queries, model)

    async def _load_document_text(self, document_id: str) -> str | None:
        """Load document raw text from the invoices table."""
        try:
            async with self._session_factory() as session:
                result = await session.execute(
                    text("""
                        SELECT COALESCE(
                            NULLIF(raw_text_hash, ''),
                            vendor_name || ' ' || buyer_name || ' ' || COALESCE(invoice_number, '')
                        ) AS doc_text
                        FROM invoices WHERE id = CAST(:id AS uuid)
                    """),
                    {"id": document_id},
                )
                row = result.fetchone()
                if row and row[0]:
                    # raw_text_hash is actually a hash — try to get full text from
                    # the extraction_history if available, otherwise compose from fields
                    return await self._get_full_text(document_id, session)
                return None
        except Exception as exc:
            self._logger.warning("load_document_failed", error=str(exc))
            return None

    async def _get_full_text(self, document_id: str, session: AsyncSession) -> str:
        """Compose a text representation from stored invoice fields."""
        result = await session.execute(
            text("""
                SELECT source_file, vendor_name, vendor_address, vendor_tax_number,
                       buyer_name, buyer_address, buyer_tax_number,
                       invoice_number, invoice_date, currency,
                       net_total, vat_total, gross_total,
                       COALESCE(config_name, '') as config_name
                FROM invoices WHERE id = CAST(:id AS uuid)
            """),
            {"id": document_id},
        )
        row = result.fetchone()
        if not row:
            return ""

        parts = [
            f"Source file: {row[0]}",
            f"Vendor: {row[1]}, Address: {row[2]}, Tax: {row[3]}",
            f"Buyer: {row[4]}, Address: {row[5]}, Tax: {row[6]}",
            f"Invoice number: {row[7]}, Date: {row[8]}",
            f"Currency: {row[9]}",
            f"Net total: {row[10]}, VAT total: {row[11]}, Gross total: {row[12]}",
        ]

        # Also fetch line items
        items_result = await session.execute(
            text("""
                SELECT line_number, description, quantity, unit, unit_price,
                       net_amount, vat_rate, gross_amount
                FROM invoice_line_items
                WHERE invoice_id = CAST(:id AS uuid)
                ORDER BY line_number
            """),
            {"id": document_id},
        )
        for item_row in items_result.fetchall():
            parts.append(
                f"Line {item_row[0]}: {item_row[1]} "
                f"qty={item_row[2]} unit={item_row[3]} "
                f"price={item_row[4]} net={item_row[5]} "
                f"vat_rate={item_row[6]} gross={item_row[7]}"
            )

        return "\n".join(parts)

    async def _call_llm(
        self,
        doc_text: str,
        queries: list[FreeTextQuery],
        model: str,
    ) -> list[FreeTextResult]:
        """Send document + queries to LLM, parse structured response."""
        from aiflow.models.client import ModelClient

        queries_block = "\n".join(
            f"{i+1}. {q.query}" + (f" (hint: {q.hint})" if q.hint else "")
            for i, q in enumerate(queries)
        )

        system_prompt = (
            "You are a document analysis assistant. "
            "Given a document and a list of queries, answer each query based ONLY on the document content. "
            "Return a JSON array where each element has: "
            '"query" (the original query), '
            '"answer" (your answer — use "Not found" if the document does not contain the information), '
            '"confidence" (0.0–1.0 how confident you are), '
            '"source_span" (the relevant text snippet from the document, max 200 chars).'
        )

        user_prompt = (
            f"DOCUMENT:\n{doc_text}\n\n"
            f"QUERIES:\n{queries_block}\n\n"
            "Answer each query. Return JSON array only."
        )

        try:
            client = ModelClient()
            result = await client.generate(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                model=model,
                temperature=0.0,
                response_format={"type": "json_object"},
            )

            raw = json.loads(result.output.text)
            # Handle both {"results": [...]} and direct [...] formats
            items = raw if isinstance(raw, list) else raw.get("results", raw.get("answers", []))

            results = []
            for item in items:
                results.append(FreeTextResult(
                    query=item.get("query", ""),
                    answer=item.get("answer", "Not found"),
                    confidence=float(item.get("confidence", 0.0)),
                    source_span=item.get("source_span", "")[:200],
                ))

            # Ensure we have results for all queries
            answered_queries = {r.query for r in results}
            for q in queries:
                if q.query not in answered_queries:
                    results.append(FreeTextResult(
                        query=q.query, answer="Not found", confidence=0.0
                    ))

            return results

        except Exception as exc:
            self._logger.error("free_text_llm_failed", error=str(exc))
            return [
                FreeTextResult(query=q.query, answer=f"Error: {exc}", confidence=0.0)
                for q in queries
            ]

    async def _log_extraction(
        self,
        document_id: str,
        queries: list[FreeTextQuery],
        results: list[FreeTextResult],
        elapsed_ms: float,
        model: str,
    ) -> None:
        """Log extraction attempt to audit trail (best-effort)."""
        try:
            from aiflow.api.audit_helper import audit_log

            await audit_log(
                "free_text_extract",
                "document",
                document_id,
                details={
                    "query_count": len(queries),
                    "model": model,
                    "elapsed_ms": round(elapsed_ms),
                    "avg_confidence": (
                        sum(r.confidence for r in results) / len(results)
                        if results
                        else 0.0
                    ),
                },
            )
        except Exception:
            pass
