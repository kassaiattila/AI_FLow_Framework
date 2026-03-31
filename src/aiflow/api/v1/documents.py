"""Invoice document listing, detail, upload and processing endpoints.

Replaces the Next.js proxy layer — serves data directly from PostgreSQL
and runs skill processing in-process (no subprocess fork).
"""
from __future__ import annotations

import json
import os
import tempfile
import shutil
from pathlib import Path
from typing import Any

import asyncpg
import structlog
from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from pydantic import BaseModel

__all__ = ["router"]

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class LineItemModel(BaseModel):
    line_number: int = 0
    description: str = ""
    quantity: float = 0
    unit: str = ""
    unit_price: float = 0
    net_amount: float = 0
    vat_rate: float = 0
    vat_amount: float = 0
    gross_amount: float = 0


class DocumentItem(BaseModel):
    """An invoice document with all extracted fields."""
    id: str
    source_file: str
    direction: str = ""
    vendor: dict[str, Any] = {}
    buyer: dict[str, Any] = {}
    header: dict[str, Any] = {}
    totals: dict[str, Any] = {}
    validation: dict[str, Any] = {}
    line_items: list[dict[str, Any]] = []
    parser_used: str = ""
    extraction_confidence: float = 0.0
    created_at: str | None = None


class DocumentListResponse(BaseModel):
    """List of invoice documents."""
    documents: list[DocumentItem]
    total: int
    source: str = "backend"


class UploadResponse(BaseModel):
    """Response after uploading files."""
    uploaded: list[str]
    count: int


class ProcessRequest(BaseModel):
    """Request to process uploaded documents."""
    files: list[str] = []
    output_dir: str = ""


class ProcessResponse(BaseModel):
    """Response after processing documents."""
    processed: int
    results: list[dict[str, Any]]
    source: str = "backend"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_db_url() -> str:
    return os.getenv(
        "AIFLOW_DATABASE_URL",
        "postgresql://aiflow:aiflow_dev_password@localhost:5433/aiflow_dev",
    )


def _upload_dir() -> Path:
    """Where uploaded PDFs are stored."""
    d = Path(os.getenv("AIFLOW_UPLOAD_DIR", "./data/uploads/invoices"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def _json_fallback(resource: str) -> list[dict[str, Any]]:
    """Load data from Next.js JSON files as fallback when DB is empty."""
    for base in [Path("aiflow-ui/data"), Path("aiflow-ui/public/data")]:
        f = base / f"{resource}.json"
        if f.exists():
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    return data
                if isinstance(data, dict) and "documents" in data:
                    return data["documents"]
            except Exception:
                pass
    return []


# ---------------------------------------------------------------------------
# GET /api/v1/documents — list invoices from DB
# ---------------------------------------------------------------------------

@router.get("", response_model=DocumentListResponse)
async def list_documents(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> DocumentListResponse:
    """List all invoice documents from PostgreSQL."""
    documents: list[DocumentItem] = []
    total = 0

    try:
        conn = await asyncpg.connect(_get_db_url())
        try:
            count_row = await conn.fetchrow("SELECT COUNT(*) AS cnt FROM invoices")
            total = count_row["cnt"] if count_row else 0

            rows = await conn.fetch(
                """
                SELECT id, source_file, direction,
                       vendor_name, vendor_address, vendor_tax_number, vendor_bank_account, vendor_bank_name,
                       buyer_name, buyer_address, buyer_tax_number,
                       invoice_number, invoice_date, fulfillment_date, due_date,
                       currency, payment_method, invoice_type,
                       net_total, vat_total, gross_total,
                       is_valid, validation_errors, confidence_score,
                       parser_used, created_at
                FROM invoices
                ORDER BY created_at DESC NULLS LAST
                LIMIT $1 OFFSET $2
                """,
                limit, offset,
            )

            invoice_ids = [row["id"] for row in rows]

            # Fetch all line items in one query
            items_by_invoice: dict[str, list[dict[str, Any]]] = {}
            if invoice_ids:
                item_rows = await conn.fetch(
                    """
                    SELECT invoice_id, line_number, description, quantity, unit,
                           unit_price, net_amount, vat_rate, vat_amount, gross_amount
                    FROM invoice_line_items
                    WHERE invoice_id = ANY($1::uuid[])
                    ORDER BY line_number
                    """,
                    invoice_ids,
                )
                for ir in item_rows:
                    iid = str(ir["invoice_id"])
                    if iid not in items_by_invoice:
                        items_by_invoice[iid] = []
                    items_by_invoice[iid].append({
                        "line_number": ir["line_number"],
                        "description": ir["description"],
                        "quantity": float(ir["quantity"] or 0),
                        "unit": ir["unit"] or "",
                        "unit_price": float(ir["unit_price"] or 0),
                        "net_amount": float(ir["net_amount"] or 0),
                        "vat_rate": float(ir["vat_rate"] or 0),
                        "vat_amount": float(ir["vat_amount"] or 0),
                        "gross_amount": float(ir["gross_amount"] or 0),
                    })

            for row in rows:
                rid = str(row["id"])
                validation_errors = row["validation_errors"]
                if isinstance(validation_errors, str):
                    validation_errors = json.loads(validation_errors)

                documents.append(DocumentItem(
                    id=row["source_file"],  # Use source_file as ID for compatibility
                    source_file=row["source_file"],
                    direction=row["direction"] or "",
                    vendor={
                        "name": row["vendor_name"] or "",
                        "address": row["vendor_address"] or "",
                        "tax_number": row["vendor_tax_number"] or "",
                        "bank_account": row["vendor_bank_account"] or "",
                        "bank_name": row["vendor_bank_name"] or "",
                    },
                    buyer={
                        "name": row["buyer_name"] or "",
                        "address": row["buyer_address"] or "",
                        "tax_number": row["buyer_tax_number"] or "",
                    },
                    header={
                        "invoice_number": row["invoice_number"] or "",
                        "invoice_date": str(row["invoice_date"]) if row["invoice_date"] else "",
                        "fulfillment_date": str(row["fulfillment_date"]) if row["fulfillment_date"] else "",
                        "due_date": str(row["due_date"]) if row["due_date"] else "",
                        "currency": row["currency"] or "HUF",
                        "payment_method": row["payment_method"] or "",
                        "invoice_type": row["invoice_type"] or "",
                    },
                    totals={
                        "net_total": float(row["net_total"] or 0),
                        "vat_total": float(row["vat_total"] or 0),
                        "gross_total": float(row["gross_total"] or 0),
                    },
                    validation={
                        "is_valid": row["is_valid"],
                        "errors": validation_errors or [],
                        "confidence_score": float(row["confidence_score"] or 0),
                    },
                    line_items=items_by_invoice.get(rid, []),
                    parser_used=row["parser_used"] or "",
                    extraction_confidence=float(row["confidence_score"] or 0),
                    created_at=row["created_at"].isoformat() if row["created_at"] else None,
                ))
        finally:
            await conn.close()
    except Exception as e:
        logger.warning("documents_db_failed", error=str(e))

    # Fallback to JSON files if DB is empty or unavailable
    if not documents:
        fallback = _json_fallback("invoices")
        for item in fallback:
            sf = item.get("source_file", "")
            documents.append(DocumentItem(
                id=sf,
                source_file=sf,
                direction=item.get("direction", ""),
                vendor=item.get("vendor", {}),
                buyer=item.get("buyer", {}),
                header=item.get("header", {}),
                totals=item.get("totals", {}),
                validation=item.get("validation", {}),
                line_items=item.get("line_items", []),
                parser_used=item.get("parser_used", ""),
                extraction_confidence=item.get("extraction_confidence", 0),
            ))
        if documents:
            return DocumentListResponse(documents=documents, total=len(documents), source="demo")

    return DocumentListResponse(documents=documents, total=total, source="backend")


# ---------------------------------------------------------------------------
# GET /api/v1/documents/{source_file} — single invoice detail
# ---------------------------------------------------------------------------

@router.get("/{source_file:path}", response_model=DocumentItem)
async def get_document(source_file: str) -> DocumentItem:
    """Get a single invoice document by source_file."""
    result = await list_documents(limit=500, offset=0)
    for doc in result.documents:
        if doc.source_file == source_file:
            return doc
    raise HTTPException(status_code=404, detail=f"Document not found: {source_file}")


# ---------------------------------------------------------------------------
# POST /api/v1/documents/upload — multipart file upload
# ---------------------------------------------------------------------------

@router.post("/upload", response_model=UploadResponse)
async def upload_documents(files: list[UploadFile] = File(...)) -> UploadResponse:
    """Upload PDF invoice files for processing."""
    upload_dir = _upload_dir()
    uploaded: list[str] = []

    for f in files:
        if not f.filename:
            continue
        dest = upload_dir / f.filename
        content = await f.read()
        dest.write_bytes(content)
        uploaded.append(f.filename)
        logger.info("document_uploaded", filename=f.filename, size=len(content))

    return UploadResponse(uploaded=uploaded, count=len(uploaded))


# ---------------------------------------------------------------------------
# POST /api/v1/documents/process — run invoice processor skill in-process
# ---------------------------------------------------------------------------

@router.post("/process", response_model=ProcessResponse)
async def process_documents(request: ProcessRequest) -> ProcessResponse:
    """Process uploaded invoice PDFs using the invoice_processor skill.

    Runs the skill steps directly (no subprocess) via SkillRunner.
    """
    upload_dir = _upload_dir()
    output_dir = Path(request.output_dir) if request.output_dir else Path(tempfile.mkdtemp(prefix="aiflow_invoice_"))

    # Determine which files to process
    file_list = request.files
    if not file_list:
        file_list = [f.name for f in upload_dir.glob("*.pdf")]

    if not file_list:
        return ProcessResponse(processed=0, results=[], source="backend")

    # Import skill steps
    try:
        from skills.invoice_processor.workflows.process import (
            parse_invoice,
            classify_invoice,
            extract_invoice_data,
            validate_invoice,
            store_invoice,
            export_invoice,
        )
    except ImportError as e:
        logger.error("skill_import_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Invoice processor skill not available: {e}")

    # Build input data
    source_path = str(upload_dir)
    input_data = {
        "source_path": source_path,
        "output_dir": str(output_dir),
        "format": "all",
    }

    # Run the pipeline steps sequentially
    try:
        data = await parse_invoice({**input_data})
        data = await classify_invoice(data)
        data = await extract_invoice_data(data)
        data = await validate_invoice(data)
        data = await store_invoice(data)
        data = await export_invoice(data)
    except Exception as e:
        logger.error("process_documents_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

    # Build response
    results = []
    for f in data.get("files", []):
        results.append({
            "source_file": f.get("filename", ""),
            "vendor": f.get("vendor", {}).get("name", ""),
            "gross_total": f.get("totals", {}).get("gross_total", 0),
            "is_valid": f.get("validation", {}).get("is_valid", False),
            "confidence": f.get("validation", {}).get("confidence_score", 0),
            "error": f.get("error"),
        })

    logger.info("process_documents_done", count=len(results))
    return ProcessResponse(
        processed=len(results),
        results=results,
        source="backend",
    )
