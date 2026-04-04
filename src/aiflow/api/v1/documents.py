"""Invoice document listing, detail, upload and processing endpoints.

Replaces the Next.js proxy layer — serves data directly from PostgreSQL
and runs skill processing in-process (no subprocess fork).
"""
from __future__ import annotations

import asyncio
import json
import os
import tempfile
import shutil
import time as _time
import uuid
from pathlib import Path
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from pydantic import BaseModel
from starlette.responses import StreamingResponse

from aiflow.api.deps import get_pool, get_engine

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

def _upload_dir() -> Path:
    """Where uploaded PDFs are stored."""
    d = Path(os.getenv("AIFLOW_UPLOAD_DIR", "./data/uploads/invoices"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def _json_fallback(resource: str) -> list[dict[str, Any]]:
    """Return empty list — legacy Next.js JSON fallback removed (aiflow-ui deleted)."""
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
        pool = await get_pool()
        async with pool.acquire() as conn:
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
                    id=str(row["id"]),  # Use real DB UUID as ID
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
# POST /api/v1/documents/process-stream — SSE real-time progress
# ---------------------------------------------------------------------------
# NOTE: Must be BEFORE /{source_file:path} catch-all route!

@router.post("/process-stream")
async def process_documents_stream(request: ProcessRequest) -> StreamingResponse:
    """Process uploaded PDFs with real-time SSE step progress.

    Streams events: step_start, step_done, error, complete.
    """
    upload_dir = _upload_dir()
    output_dir = Path(request.output_dir) if request.output_dir else Path(
        tempfile.mkdtemp(prefix="aiflow_invoice_"),
    )

    file_list = request.files
    if not file_list:
        file_list = [f.name for f in upload_dir.glob("*.pdf")]

    if not file_list:
        async def empty_stream():
            yield f"data: {json.dumps({'event': 'complete', 'results': []})}\n\n"
        return StreamingResponse(empty_stream(), media_type="text/event-stream")

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
        async def error_stream():
            yield f"data: {json.dumps({'event': 'error', 'step': 0, 'name': 'import', 'error': str(e)})}\n\n"
        return StreamingResponse(error_stream(), media_type="text/event-stream")

    # Per-file pipeline (parse through store); export runs once at the end.
    per_file_steps = [
        ("parse", parse_invoice),
        ("classify", classify_invoice),
        ("extract", extract_invoice_data),
        ("validate", validate_invoice),
        ("store", store_invoice),
    ]
    step_names = [s[0] for s in per_file_steps]

    async def event_stream():
        def sse(obj: dict[str, Any]) -> str:
            return f"data: {json.dumps(obj)}\n\n"

        total_files = len(file_list)
        yield sse({"event": "init", "total_files": total_files, "steps": step_names})

        run_id = str(uuid.uuid4())
        run_start = _time.perf_counter()
        all_step_records: list[dict[str, Any]] = []
        all_files_data: list[dict[str, Any]] = []
        results: list[dict[str, Any]] = []
        run_status = "running"
        run_error: str | None = None

        for fi, fname in enumerate(file_list):
            source = str(upload_dir / fname)
            file_data: dict[str, Any] = {
                "source_path": source,
                "output_dir": str(output_dir),
                "format": "all",
            }

            yield sse({"event": "file_start", "file": fname, "file_index": fi, "total_files": total_files})
            await asyncio.sleep(0)

            file_ok = True
            for si, (name, step_fn) in enumerate(per_file_steps):
                yield sse({"event": "file_step", "file": fname, "file_index": fi, "step_index": si, "step_name": name, "status": "running"})
                await asyncio.sleep(0)
                t = _time.perf_counter()
                try:
                    file_data = await step_fn({**file_data} if si == 0 else file_data)
                    elapsed_ms = int((_time.perf_counter() - t) * 1000)
                    all_step_records.append({"name": f"{fname}:{name}", "status": "completed", "duration_ms": elapsed_ms})
                    yield sse({"event": "file_step", "file": fname, "file_index": fi, "step_index": si, "step_name": name, "status": "done", "elapsed_ms": elapsed_ms})
                except Exception as e:
                    elapsed_ms = int((_time.perf_counter() - t) * 1000)
                    all_step_records.append({"name": f"{fname}:{name}", "status": "failed", "duration_ms": elapsed_ms, "error": str(e)})
                    run_status = "failed"
                    run_error = str(e)
                    logger.error("process_stream_file_step_failed", file=fname, step=name, error=str(e))
                    yield sse({"event": "file_error", "file": fname, "file_index": fi, "step_name": name, "error": str(e), "elapsed_ms": elapsed_ms})
                    file_ok = False
                    break

            if file_ok:
                for f in file_data.get("files", []):
                    all_files_data.append(f)
                    results.append({
                        "source_file": f.get("filename", ""),
                        "vendor": f.get("vendor", {}).get("name", ""),
                        "gross_total": f.get("totals", {}).get("gross_total", 0),
                        "is_valid": f.get("validation", {}).get("is_valid", False),
                        "confidence": f.get("validation", {}).get("confidence_score", 0),
                    })
            else:
                results.append({"source_file": fname, "error": run_error})

            yield sse({"event": "file_done", "file": fname, "file_index": fi, "ok": file_ok})

        # Run export on all successfully processed files
        if all_files_data:
            try:
                export_data: dict[str, Any] = {"files": all_files_data, "output_dir": str(output_dir), "format": "all"}
                await export_invoice(export_data)
            except Exception as e:
                logger.warning("export_step_failed", error=str(e))

        total_duration_ms = int((_time.perf_counter() - run_start) * 1000)
        if run_status == "running":
            run_status = "completed"

        # Calculate LLM cost from token usage and persist to cost_records
        total_cost_usd = 0.0
        try:
            from aiflow.models.cost import ModelCostCalculator
            from aiflow.api.cost_recorder import record_cost
            calc = ModelCostCalculator()
            for f in all_files_data:
                inp = f.get("_llm_total_input_tokens", 0)
                out = f.get("_llm_total_output_tokens", 0)
                model = f.get("_llm_model", "openai/gpt-4o")
                if inp or out:
                    file_cost = calc.calculate(model, inp, out)
                    total_cost_usd += file_cost
                    await record_cost(
                        workflow_run_id=run_id,
                        step_name="extract",
                        model=model,
                        input_tokens=inp,
                        output_tokens=out,
                        cost_usd=file_cost,
                    )
        except Exception:
            pass  # cost calculation is best-effort

        # Persist workflow_run + step_runs to DB for Runs/Costs tracking
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    """INSERT INTO workflow_runs
                       (id, workflow_name, workflow_version, skill_name, status, input_data,
                        started_at, completed_at, total_duration_ms, total_cost_usd, error)
                       VALUES ($1, $2, $3, $4, $5, $6,
                               NOW() - MAKE_INTERVAL(secs := $7::float / 1000),
                               NOW(), $7, $8, $9)""",
                    uuid.UUID(run_id), "invoice_processing", "1.0", "invoice_processor",
                    run_status, json.dumps({"files": file_list}),
                    float(total_duration_ms), total_cost_usd, run_error,
                )
                for idx, sr in enumerate(all_step_records):
                    await conn.execute(
                        """INSERT INTO step_runs
                           (id, workflow_run_id, step_name, step_index, status, duration_ms)
                           VALUES ($1, $2, $3, $4, $5, $6)""",
                        uuid.uuid4(), uuid.UUID(run_id), sr["name"], idx,
                        sr["status"], float(sr["duration_ms"]),
                    )
        except Exception as e:
            logger.warning("workflow_run_persist_failed", error=str(e), run_id=run_id)

        yield sse({"event": "complete", "results": results})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ---------------------------------------------------------------------------
# GET /api/v1/documents/images/{source_file}/page_{page}.png — render PDF page
# ---------------------------------------------------------------------------
# NOTE: Must be BEFORE /{source_file:path} catch-all!

@router.get("/images/{source_file}/page_{page}.png")
async def render_pdf_page(source_file: str, page: int = 1) -> StreamingResponse:
    """Render a PDF page as PNG using PyMuPDF (fitz).

    Returns a cached PNG image of the requested page.
    """
    upload_dir = _upload_dir()
    # Normalize: if source_file contains a path, extract just the filename
    clean_name = Path(source_file).name if ("/" in source_file or "\\" in source_file) else source_file
    pdf_path = upload_dir / clean_name

    if not pdf_path.exists():
        # Try the original path as-is (in case it's a relative path from project root)
        alt_path = Path(source_file)
        if alt_path.exists():
            pdf_path = alt_path
        else:
            raise HTTPException(status_code=404, detail=f"PDF not found: {clean_name}")

    try:
        import pypdfium2 as pdfium
        import io

        def _render() -> bytes:
            doc = pdfium.PdfDocument(str(pdf_path))
            if page < 1 or page > len(doc):
                doc.close()
                raise ValueError(f"Page {page} out of range (1-{len(doc)})")
            bitmap = doc[page - 1].render(scale=2)  # ~200 DPI
            img = bitmap.to_pil()
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            doc.close()
            return buf.getvalue()

        png_data = await asyncio.to_thread(_render)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("render_pdf_page_failed", file=source_file, page=page, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to render page: {e}")

    return StreamingResponse(
        iter([png_data]),
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=3600"},
    )


# ---------------------------------------------------------------------------
# POST /api/v1/documents/upload — multipart file upload
# ---------------------------------------------------------------------------
# NOTE: upload and process must also be BEFORE /{source_file:path}!


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

    # Build input data — pass specific file if single, otherwise directory
    if len(file_list) == 1:
        source_path = str(upload_dir / file_list[0])
    else:
        source_path = str(upload_dir)
    input_data = {
        "source_path": source_path,
        "output_dir": str(output_dir),
        "format": "all",
    }

    # Run the pipeline steps with per-step timing
    import time as _time
    timings: dict[str, float] = {}
    try:
        t = _time.perf_counter()
        data = await parse_invoice({**input_data})
        timings["parse"] = _time.perf_counter() - t

        t = _time.perf_counter()
        data = await classify_invoice(data)
        timings["classify"] = _time.perf_counter() - t

        t = _time.perf_counter()
        data = await extract_invoice_data(data)
        timings["extract"] = _time.perf_counter() - t

        t = _time.perf_counter()
        data = await validate_invoice(data)
        timings["validate"] = _time.perf_counter() - t

        t = _time.perf_counter()
        data = await store_invoice(data)
        timings["store"] = _time.perf_counter() - t

        t = _time.perf_counter()
        data = await export_invoice(data)
        timings["export"] = _time.perf_counter() - t

        logger.info("process_documents_timings", **{k: f"{v:.1f}s" for k, v in timings.items()},
                     total=f"{sum(timings.values()):.1f}s")
    except Exception as e:
        logger.error("process_documents_failed", error=str(e), timings=timings)
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


# ---------------------------------------------------------------------------
# Document Extractor Service endpoints (F1)
# ---------------------------------------------------------------------------

async def _get_doc_extractor():
    """Lazy-init Document Extractor service."""
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
    from aiflow.services.document_extractor import DocumentExtractorService

    engine = await get_engine()
    sf = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return DocumentExtractorService(sf)


class DocumentDetailResponse(BaseModel):
    """Single document detail response (flexible schema)."""
    source: str = "backend"

    model_config = {"extra": "allow"}


class ExtractorConfigItem(BaseModel):
    """A single extractor config summary."""
    name: str
    display_name: str = ""
    document_type: str = ""
    field_count: int = 0
    enabled: bool = True


class ExtractorConfigListResponse(BaseModel):
    """List of extractor configurations."""
    configs: list[ExtractorConfigItem]
    total: int
    source: str = "backend"


class VerifyRequest(BaseModel):
    """Document verification request."""
    verified_fields: dict[str, Any] = {}
    verified_by: str = "user"


class VerifyResponse(BaseModel):
    """Document verification response."""
    verified: bool
    invoice_id: str
    source: str = "backend"


@router.post("/{invoice_id}/verify", response_model=VerifyResponse)
async def verify_document(invoice_id: str, request: VerifyRequest) -> VerifyResponse:
    """Verify an extracted document — confirm or correct extracted fields."""
    svc = await _get_doc_extractor()
    await svc.start()
    try:
        ok = await svc.verify(
            invoice_id=invoice_id,
            verified_fields=request.verified_fields,
            verified_by=request.verified_by,
        )
        return VerifyResponse(verified=ok, invoice_id=invoice_id)
    except Exception as e:
        logger.error("verify_failed", error=str(e), invoice_id=invoice_id)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await svc.stop()


@router.get("/by-id/{invoice_id}", response_model=DocumentDetailResponse)
async def get_document_by_id(invoice_id: str) -> DocumentDetailResponse:
    """Get a single invoice by database ID."""
    svc = await _get_doc_extractor()
    await svc.start()
    try:
        result = await svc.get_invoice(invoice_id)
        if not result:
            raise HTTPException(status_code=404, detail=f"Invoice not found: {invoice_id}")
        result["source"] = "backend"
        return DocumentDetailResponse(**result)
    finally:
        await svc.stop()


# ---------------------------------------------------------------------------
# Document Type Config endpoints (F1)
# ---------------------------------------------------------------------------

@router.get("/extractor/configs", response_model=ExtractorConfigListResponse)
async def list_extractor_configs() -> ExtractorConfigListResponse:
    """List all document extraction configurations."""
    svc = await _get_doc_extractor()
    await svc.start()
    try:
        configs = await svc.list_configs()
        return ExtractorConfigListResponse(
            configs=[
                ExtractorConfigItem(
                    name=c.name,
                    display_name=c.display_name,
                    document_type=c.document_type,
                    field_count=len(c.fields),
                    enabled=c.enabled,
                )
                for c in configs
            ],
            total=len(configs),
            source="backend",
        )
    finally:
        await svc.stop()


class CreateConfigRequest(BaseModel):
    """Create document type config request."""
    name: str
    display_name: str = ""
    document_type: str = ""
    description: str = ""
    parser: str = "docling"
    extraction_model: str = "openai/gpt-4o"
    fields: list[dict[str, Any]] = []
    validation_rules: list[str] = []
    output_formats: list[str] = ["json"]


class CreateConfigResponse(BaseModel):
    created: bool = True
    name: str
    source: str = "backend"


@router.post("/extractor/configs", response_model=CreateConfigResponse, status_code=201)
async def create_extractor_config(request: CreateConfigRequest) -> CreateConfigResponse:
    """Create a new document extraction configuration."""
    from aiflow.services.document_extractor import DocumentTypeConfig, FieldDefinition

    svc = await _get_doc_extractor()
    await svc.start()
    try:
        config = DocumentTypeConfig(
            name=request.name,
            display_name=request.display_name or request.name,
            document_type=request.document_type,
            description=request.description,
            parser=request.parser,
            extraction_model=request.extraction_model,
            fields=[FieldDefinition(**f) for f in request.fields],
            validation_rules=request.validation_rules,
            output_formats=request.output_formats,
        )
        await svc.create_config(config)
        return CreateConfigResponse(name=config.name)
    except Exception as e:
        logger.error("create_config_failed", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        await svc.stop()


# ---------------------------------------------------------------------------
# GET /api/v1/documents/export/csv — Export all invoices as CSV
# ---------------------------------------------------------------------------

@router.get("/export/csv")
async def export_documents_csv():
    """Export all invoices as downloadable CSV file."""
    import csv
    import io

    result = await list_documents(limit=1000, offset=0)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "source_file", "direction", "vendor_name", "vendor_tax_number",
        "buyer_name", "buyer_tax_number", "invoice_number", "invoice_date",
        "due_date", "currency", "net_total", "vat_total", "gross_total",
        "is_valid", "confidence_score", "created_at",
    ])
    for doc in result.documents:
        writer.writerow([
            doc.source_file,
            doc.direction,
            doc.vendor.get("name", "") if doc.vendor else "",
            doc.vendor.get("tax_number", "") if doc.vendor else "",
            doc.buyer.get("name", "") if doc.buyer else "",
            doc.buyer.get("tax_number", "") if doc.buyer else "",
            doc.header.get("invoice_number", "") if doc.header else "",
            doc.header.get("invoice_date", "") if doc.header else "",
            doc.header.get("due_date", "") if doc.header else "",
            doc.header.get("currency", "HUF") if doc.header else "HUF",
            doc.totals.get("net_total", "") if doc.totals else "",
            doc.totals.get("vat_total", "") if doc.totals else "",
            doc.totals.get("gross_total", "") if doc.totals else "",
            doc.validation.get("is_valid", "") if doc.validation else "",
            doc.extraction_confidence or "",
            doc.created_at or "",
        ])

    from fastapi.responses import StreamingResponse
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=aiflow_invoices_export.csv"},
    )


@router.get("/export/json")
async def export_documents_json():
    """Export all invoices as downloadable JSON file."""
    result = await list_documents(limit=1000, offset=0)
    data = [doc.model_dump() for doc in result.documents]
    from fastapi.responses import JSONResponse
    return JSONResponse(
        content=data,
        headers={"Content-Disposition": "attachment; filename=aiflow_invoices_export.json"},
    )


# ---------------------------------------------------------------------------
# DELETE /api/v1/documents/delete/{invoice_id} — delete a document
# ---------------------------------------------------------------------------

@router.delete("/delete/{invoice_id}", status_code=204)
async def delete_document(invoice_id: str):
    """Delete a document by UUID."""
    from aiflow.api.deps import get_engine
    from sqlalchemy import text

    engine = await get_engine()
    async with engine.begin() as conn:
        # Delete line items first (FK cascade might not work with raw SQL)
        await conn.execute(text("DELETE FROM invoice_line_items WHERE invoice_id = CAST(:id AS uuid)"), {"id": invoice_id})
        result = await conn.execute(text("DELETE FROM invoices WHERE id = CAST(:id AS uuid)"), {"id": invoice_id})
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Document not found")
    logger.info("document_deleted", invoice_id=invoice_id)
    from aiflow.api.audit_helper import audit_log
    await audit_log("delete", "document", invoice_id)


class BulkDeleteRequest(BaseModel):
    ids: list[str]


class BulkDeleteResponse(BaseModel):
    deleted: int = 0
    source: str = "backend"


@router.post("/delete-bulk", response_model=BulkDeleteResponse)
async def delete_documents_bulk(request: BulkDeleteRequest):
    """Delete multiple documents by UUID list."""
    from aiflow.api.deps import get_engine
    from sqlalchemy import text

    if not request.ids:
        return BulkDeleteResponse(deleted=0)

    engine = await get_engine()
    total_deleted = 0
    async with engine.begin() as conn:
        for doc_id in request.ids:
            await conn.execute(text("DELETE FROM invoice_line_items WHERE invoice_id = CAST(:id AS uuid)"), {"id": doc_id})
            result = await conn.execute(text("DELETE FROM invoices WHERE id = CAST(:id AS uuid)"), {"id": doc_id})
            total_deleted += result.rowcount

    logger.info("documents_bulk_deleted", count=total_deleted, ids=request.ids)
    from aiflow.api.audit_helper import audit_log
    await audit_log("bulk_delete", "document", details={"count": total_deleted, "ids": request.ids})
    return BulkDeleteResponse(deleted=total_deleted)


# ---------------------------------------------------------------------------
# POST /api/v1/documents/{document_id}/extract-free — free-text extraction
# ---------------------------------------------------------------------------


class FreeTextQueryItem(BaseModel):
    query: str
    hint: str = ""


class FreeTextExtractRequest(BaseModel):
    queries: list[FreeTextQueryItem]
    model: str | None = None


class FreeTextResultItem(BaseModel):
    query: str
    answer: str
    confidence: float = 0.0
    source_span: str = ""


class FreeTextExtractResponse(BaseModel):
    document_id: str
    results: list[FreeTextResultItem]
    extraction_time_ms: float = 0.0
    model_used: str = ""
    source: str = "backend"


@router.post("/{document_id}/extract-free", response_model=FreeTextExtractResponse)
async def extract_free_text(document_id: str, request: FreeTextExtractRequest) -> FreeTextExtractResponse:
    """Extract answers to arbitrary queries from a stored document using LLM."""
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
    from aiflow.services.document_extractor.free_text import (
        FreeTextExtractorService,
        FreeTextQuery,
    )

    if not request.queries:
        raise HTTPException(status_code=400, detail="At least one query is required")

    engine = await get_engine()
    sf = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    svc = FreeTextExtractorService(sf)
    await svc.start()
    try:
        queries = [FreeTextQuery(query=q.query, hint=q.hint) for q in request.queries]
        response = await svc.extract(
            document_id=document_id,
            queries=queries,
            model=request.model,
        )
        return FreeTextExtractResponse(
            document_id=response.document_id,
            results=[
                FreeTextResultItem(
                    query=r.query,
                    answer=r.answer,
                    confidence=r.confidence,
                    source_span=r.source_span,
                )
                for r in response.results
            ],
            extraction_time_ms=response.extraction_time_ms,
            model_used=response.model_used,
        )
    except Exception as e:
        logger.error("extract_free_failed", error=str(e), document_id=document_id)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await svc.stop()


# ---------------------------------------------------------------------------
# GET /api/v1/documents/{source_file} — single invoice detail (CATCH-ALL, MUST BE LAST!)
# ---------------------------------------------------------------------------

@router.get("/{source_file:path}", response_model=DocumentItem)
async def get_document(source_file: str) -> DocumentItem:
    """Get a single invoice document by source_file."""
    result = await list_documents(limit=500, offset=0)
    for doc in result.documents:
        if doc.source_file == source_file:
            return doc
    raise HTTPException(status_code=404, detail=f"Document not found: {source_file}")
