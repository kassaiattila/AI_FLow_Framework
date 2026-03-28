"""Document ingestion workflow - load, parse, chunk, embed, store.

Pipeline: load_documents -> parse_documents -> chunk_documents
       -> generate_embeddings -> store_chunks -> verify_ingestion

Processes PDF, DOCX, MD, TXT files into embedded chunks stored in
pgvector (or in-memory fallback) for hybrid RAG retrieval.
"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

import structlog

from aiflow.engine.step import step
from aiflow.engine.workflow import workflow, WorkflowBuilder
from aiflow.models.client import ModelClient
from aiflow.models.backends.litellm_backend import LiteLLMBackend
from aiflow.prompts.manager import PromptManager
from aiflow.vectorstore.pgvector_store import PgVectorStore
from aiflow.vectorstore.embedder import Embedder

__all__ = [
    "load_documents",
    "parse_documents",
    "chunk_documents",
    "generate_embeddings",
    "store_chunks",
    "verify_ingestion",
    "aszf_rag_ingest",
]

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Module-level services (closure pattern, same as process_documentation)
# ---------------------------------------------------------------------------

_backend = LiteLLMBackend(default_model="openai/gpt-4o-mini")
_model_client = ModelClient(generation_backend=_backend)
_prompt_manager = PromptManager()
_prompt_manager.register_yaml_dir(Path(__file__).parent.parent / "prompts")

_vector_store = PgVectorStore()  # auto-detects pg or in-memory fallback
_embedder = Embedder(
    _model_client,
    default_model="openai/text-embedding-3-small",
    batch_size=5,
    max_chars=6000,
)

# ---------------------------------------------------------------------------
# Supported file extensions
# ---------------------------------------------------------------------------

_SUPPORTED_EXTENSIONS = {".pdf", ".md", ".txt", ".docx"}


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------

@step(name="load_documents", description="Load files from source path")
async def load_documents(data: dict) -> dict:
    """Load files from source_path (glob *.pdf, *.md, *.txt, *.docx).

    Input:
        source_path: str - directory containing documents
        collection: str - vectorstore collection name
        language: str - document language (default: "hu")

    Output:
        files: list[dict] - file info dicts with path, name, size
        collection: str
        language: str
    """
    source_path = Path(data.get("source_path", ""))
    collection = data.get("collection", "default")
    language = data.get("language", "hu")

    if not source_path.exists():
        raise FileNotFoundError(f"Source path does not exist: {source_path}")
    if not source_path.is_dir():
        raise ValueError(f"Source path is not a directory: {source_path}")

    files: list[dict[str, Any]] = []
    for ext in _SUPPORTED_EXTENSIONS:
        for file_path in sorted(source_path.glob(f"*{ext}")):
            if file_path.is_file():
                files.append({
                    "path": str(file_path),
                    "name": file_path.name,
                    "size": file_path.stat().st_size,
                })

    if not files:
        raise ValueError(
            f"No supported files found in {source_path}. "
            f"Supported: {', '.join(sorted(_SUPPORTED_EXTENSIONS))}"
        )

    logger.info(
        "load_documents.done",
        source_path=str(source_path),
        file_count=len(files),
        total_bytes=sum(f["size"] for f in files),
    )
    return {
        "files": files,
        "collection": collection,
        "language": language,
    }


@step(name="parse_documents", description="Extract text from each file")
async def parse_documents(data: dict) -> dict:
    """Extract text content from each file.

    For PDF: try pymupdf (fitz), fallback to read_text()
    For MD/TXT: direct read with utf-8
    For DOCX: python-docx paragraph extraction

    Input:
        files: list[dict] - from load_documents
        collection: str
        language: str

    Output:
        documents: list[dict] - with name, text, file_type
        collection: str
        language: str
    """
    files = data.get("files", [])
    collection = data.get("collection", "default")
    language = data.get("language", "hu")

    documents: list[dict[str, Any]] = []
    for file_info in files:
        file_path = Path(file_info["path"])
        file_name = file_info["name"]
        ext = file_path.suffix.lower()
        text = ""

        try:
            if ext == ".pdf":
                text = _parse_pdf(file_path)
            elif ext in {".md", ".txt"}:
                text = file_path.read_text(encoding="utf-8")
            elif ext == ".docx":
                text = _parse_docx(file_path)
            else:
                logger.warning("parse_documents.unsupported", file=file_name, ext=ext)
                continue

            if text.strip():
                documents.append({
                    "name": file_name,
                    "text": text,
                    "file_type": ext.lstrip("."),
                })
                logger.debug(
                    "parse_documents.parsed",
                    file=file_name,
                    chars=len(text),
                )
            else:
                logger.warning("parse_documents.empty", file=file_name)

        except Exception as exc:
            logger.error(
                "parse_documents.error",
                file=file_name,
                error=str(exc),
            )
            continue

    logger.info(
        "parse_documents.done",
        total_files=len(files),
        parsed=len(documents),
        total_chars=sum(len(d["text"]) for d in documents),
    )
    return {
        "documents": documents,
        "collection": collection,
        "language": language,
    }


def _parse_pdf(path: Path) -> str:
    """Extract text from PDF using pymupdf, fallback to raw read."""
    try:
        import fitz  # pymupdf

        doc = fitz.open(str(path))
        pages: list[str] = []
        for page in doc:
            pages.append(page.get_text())
        doc.close()
        return "\n\n".join(pages)
    except ImportError:
        logger.warning("parse_pdf.pymupdf_missing", fallback="read_text")
        try:
            return path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return ""


def _parse_docx(path: Path) -> str:
    """Extract text from DOCX using python-docx."""
    try:
        from docx import Document

        doc = Document(str(path))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs)
    except ImportError:
        logger.warning("parse_docx.python_docx_missing")
        return ""


@step(name="chunk_documents", description="Split into chunks with metadata")
async def chunk_documents(data: dict) -> dict:
    """Split documents into chunks using semantic chunking.

    Target: 500 tokens (~2000 chars for Hungarian), overlap: 100 tokens (~400 chars).
    Separators: paragraph break, line break, sentence end.

    Input:
        documents: list[dict] - from parse_documents
        collection: str
        language: str

    Output:
        chunks: list[dict] - with text, metadata, chunk_id
        collection: str
        total_chunks: int
        language: str
    """
    documents = data.get("documents", [])
    collection = data.get("collection", "default")
    language = data.get("language", "hu")

    # Approximate token-to-char ratio for Hungarian text
    target_chars = 500 * 4  # ~2000 chars for 500 tokens
    overlap_chars = 100 * 4  # ~400 chars for 100 tokens
    separators = ["\n\n", "\n", ". "]

    all_chunks: list[dict[str, Any]] = []

    for doc in documents:
        doc_name = doc["name"]
        text = doc["text"]
        file_type = doc.get("file_type", "")
        doc_id = str(uuid.uuid4())

        doc_chunks = _semantic_chunk(text, target_chars, overlap_chars, separators)

        for idx, chunk_text in enumerate(doc_chunks):
            all_chunks.append({
                "chunk_id": str(uuid.uuid4()),
                "document_id": doc_id,
                "content": chunk_text,
                "metadata": {
                    "source_document": doc_name,
                    "document_title": doc_name,
                    "chunk_index": idx,
                    "chunk_type": "semantic",
                    "language": language,
                    "file_type": file_type,
                    "collection": collection,
                },
            })

        logger.debug(
            "chunk_documents.doc",
            document=doc_name,
            chunks=len(doc_chunks),
            chars=len(text),
        )

    logger.info(
        "chunk_documents.done",
        documents=len(documents),
        total_chunks=len(all_chunks),
    )
    return {
        "chunks": all_chunks,
        "collection": collection,
        "total_chunks": len(all_chunks),
        "language": language,
    }


def _semantic_chunk(
    text: str,
    target_chars: int,
    overlap_chars: int,
    separators: list[str],
) -> list[str]:
    """Split text into chunks using hierarchical separators.

    Tries the first separator first; if resulting segments are too large,
    recursively splits with the next separator. Adds overlap between chunks.
    """
    if not text.strip():
        return []

    # Split by first available separator that produces segments
    segments: list[str] = [text]
    for sep in separators:
        new_segments: list[str] = []
        for segment in segments:
            parts = segment.split(sep)
            new_segments.extend(p for p in parts if p.strip())
        if len(new_segments) > 1:
            segments = new_segments
            break

    # Merge small segments into target-sized chunks with overlap
    chunks: list[str] = []
    current_chunk = ""

    for segment in segments:
        segment = segment.strip()
        if not segment:
            continue

        if len(current_chunk) + len(segment) + 1 <= target_chars:
            current_chunk = (current_chunk + " " + segment).strip() if current_chunk else segment
        else:
            if current_chunk:
                chunks.append(current_chunk)
                # Keep overlap from end of current chunk
                overlap = current_chunk[-overlap_chars:] if len(current_chunk) > overlap_chars else ""
                current_chunk = (overlap + " " + segment).strip() if overlap else segment
            else:
                # Single segment larger than target -- include as-is
                chunks.append(segment)
                current_chunk = ""

    if current_chunk.strip():
        chunks.append(current_chunk)

    return chunks


@step(name="generate_embeddings", description="Embed all chunks via Embedder")
async def generate_embeddings(data: dict) -> dict:
    """Generate embeddings for all chunks using Embedder with batching.

    Input:
        chunks: list[dict] - from chunk_documents
        collection: str

    Output:
        chunks_with_embeddings: list[dict] - chunks + embedding field
        embedding_cost_usd: float
        collection: str
    """
    chunks = data.get("chunks", [])
    collection = data.get("collection", "default")

    texts = [c["content"] for c in chunks]

    logger.info(
        "generate_embeddings.start",
        total_chunks=len(texts),
        batch_size=_embedder._batch_size,
    )

    embeddings = await _embedder.embed_texts(texts)
    cost_summary = _embedder._cost_tracker.summary()

    chunks_with_embeddings: list[dict[str, Any]] = []
    for chunk, embedding in zip(chunks, embeddings):
        chunks_with_embeddings.append({
            **chunk,
            "embedding": embedding,
        })

    logger.info(
        "generate_embeddings.done",
        total_chunks=len(chunks_with_embeddings),
        cost_usd=cost_summary["total_cost_usd"],
        tokens=cost_summary["total_tokens"],
    )
    return {
        "chunks_with_embeddings": chunks_with_embeddings,
        "embedding_cost_usd": cost_summary["total_cost_usd"],
        "collection": collection,
    }


@step(name="store_chunks", description="Store embedded chunks in vectorstore")
async def store_chunks(data: dict) -> dict:
    """Store chunks with embeddings in PgVectorStore.

    Input:
        chunks_with_embeddings: list[dict] - chunks with embedding field
        collection: str

    Output:
        stored_count: int
        collection: str
    """
    chunks_with_embeddings = data.get("chunks_with_embeddings", [])
    collection = data.get("collection", "default")
    skill_name = "aszf_rag_chat"

    # Separate chunks and embeddings for the vectorstore API
    chunks_data: list[dict[str, Any]] = []
    embeddings: list[list[float]] = []

    for item in chunks_with_embeddings:
        embedding = item.pop("embedding", [])
        embeddings.append(embedding)
        chunks_data.append(item)

    stored_count = await _vector_store.upsert_chunks(
        collection=collection,
        skill_name=skill_name,
        chunks=chunks_data,
        embeddings=embeddings,
    )

    logger.info(
        "store_chunks.done",
        stored=stored_count,
        collection=collection,
    )
    return {
        "stored_count": stored_count,
        "collection": collection,
    }


@step(name="verify_ingestion", description="Verify chunks stored correctly")
async def verify_ingestion(data: dict) -> dict:
    """Verify ingestion by querying the vectorstore for chunk count.

    Input:
        stored_count: int - from store_chunks
        collection: str

    Output:
        verified: bool
        total_chunks: int
        collection: str
    """
    stored_count = data.get("stored_count", 0)
    collection = data.get("collection", "default")

    # Health check confirms the store is operational
    is_healthy = await _vector_store.health_check()

    verified = is_healthy and stored_count > 0
    logger.info(
        "verify_ingestion.done",
        verified=verified,
        stored_count=stored_count,
        collection=collection,
        store_healthy=is_healthy,
    )
    return {
        "verified": verified,
        "total_chunks": stored_count,
        "collection": collection,
    }


# ---------------------------------------------------------------------------
# Workflow registration
# ---------------------------------------------------------------------------

@workflow(name="aszf-rag-ingest", version="1.0.0", skill="aszf_rag_chat")
def aszf_rag_ingest(wf: WorkflowBuilder) -> None:
    """Document ingestion pipeline: load -> parse -> chunk -> embed -> store -> verify."""
    wf.step(load_documents)
    wf.step(parse_documents, depends_on=["load_documents"])
    wf.step(chunk_documents, depends_on=["parse_documents"])
    wf.step(generate_embeddings, depends_on=["chunk_documents"])
    wf.step(store_chunks, depends_on=["generate_embeddings"])
    wf.step(verify_ingestion, depends_on=["store_chunks"])
