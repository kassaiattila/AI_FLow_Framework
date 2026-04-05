"""RAG Advanced API — rerank, chunk, clean, enrich, vector-ops, parse, graph."""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter
from pydantic import BaseModel, Field

__all__ = ["router"]

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/rag-advanced", tags=["rag-advanced"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class RerankRequest(BaseModel):
    query: str = Field(..., description="Search query")
    candidates: list[dict[str, Any]] = Field(default_factory=list)
    model: str = "bge-reranker-v2-m3"
    return_top: int = 5


class RerankResponse(BaseModel):
    results: list[dict[str, Any]] = Field(default_factory=list)
    count: int = 0
    source: str = "backend"


class ChunkRequest(BaseModel):
    text: str = Field(..., description="Text to chunk")
    strategy: str = "recursive"
    chunk_size: int = 512
    chunk_overlap: int = 64


class ChunkResponse(BaseModel):
    chunks: list[dict[str, Any]] = Field(default_factory=list)
    total_chunks: int = 0
    strategy_used: str = ""
    source: str = "backend"


class CleanRequest(BaseModel):
    text: str = Field(..., description="Raw document text")
    normalize_whitespace: bool = True
    language: str = "hu"


class CleanResponse(BaseModel):
    cleaned_text: str = ""
    original_length: int = 0
    cleaned_length: int = 0
    source: str = "backend"


class EnrichRequest(BaseModel):
    text: str = Field(..., description="Document text to enrich")
    extract_keywords: bool = True
    language: str = "hu"


class EnrichResponse(BaseModel):
    title: str | None = None
    keywords: list[str] = Field(default_factory=list)
    summary: str = ""
    confidence: float = 0.0
    source: str = "backend"


class VectorHealthResponse(BaseModel):
    total_vectors: int = 0
    index_type: str = "none"
    fragmentation_pct: float = 0.0
    source: str = "backend"


class ParseRequest(BaseModel):
    file_path: str = Field(..., description="Path to document file")
    parser: str = "auto"
    ocr_enabled: bool = True


class ParseResponse(BaseModel):
    text: str = ""
    pages: int = 0
    parser_used: str = ""
    confidence: float = 0.0
    source: str = "backend"


class GraphEntityRequest(BaseModel):
    text: str = Field(..., description="Text to extract entities from")


class GraphEntityResponse(BaseModel):
    entities: list[dict[str, Any]] = Field(default_factory=list)
    count: int = 0
    source: str = "backend"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/rerank", response_model=RerankResponse, status_code=200)
async def rerank(req: RerankRequest) -> RerankResponse:
    """Rerank search result candidates by relevance to a query."""
    from aiflow.services.reranker.service import RerankConfig, RerankerConfig, RerankerService

    svc = RerankerService(config=RerankerConfig())
    await svc.start()

    results = await svc.rerank(
        query=req.query,
        candidates=req.candidates,
        config=RerankConfig(model=req.model, return_top=req.return_top),
    )
    return RerankResponse(
        results=[r.model_dump() for r in results],
        count=len(results),
    )


@router.post("/chunk", response_model=ChunkResponse, status_code=200)
async def chunk_text(req: ChunkRequest) -> ChunkResponse:
    """Chunk text using the specified strategy."""
    from aiflow.services.advanced_chunker.service import (
        AdvancedChunkerConfig,
        AdvancedChunkerService,
        ChunkConfig,
    )

    svc = AdvancedChunkerService(config=AdvancedChunkerConfig())
    await svc.start()

    result = await svc.chunk(
        text=req.text,
        config=ChunkConfig(
            strategy=req.strategy,
            chunk_size=req.chunk_size,
            chunk_overlap=req.chunk_overlap,
        ),
    )
    return ChunkResponse(
        chunks=result.chunks,
        total_chunks=result.total_chunks,
        strategy_used=result.strategy_used,
    )


@router.post("/clean", response_model=CleanResponse, status_code=200)
async def clean_text(req: CleanRequest) -> CleanResponse:
    """Clean and normalize document text."""
    from aiflow.services.data_cleaner.service import (
        CleaningConfig,
        DataCleanerConfig,
        DataCleanerService,
    )

    svc = DataCleanerService(config=DataCleanerConfig())
    await svc.start()

    result = await svc.clean(
        text=req.text,
        config=CleaningConfig(
            normalize_whitespace=req.normalize_whitespace,
            language=req.language,
        ),
    )
    return CleanResponse(
        cleaned_text=result.cleaned_text,
        original_length=result.original_length,
        cleaned_length=result.cleaned_length,
    )


@router.post("/enrich", response_model=EnrichResponse, status_code=200)
async def enrich_metadata(req: EnrichRequest) -> EnrichResponse:
    """Extract metadata (title, keywords, summary) from document text."""
    from aiflow.services.metadata_enricher.service import (
        EnrichmentConfig,
        MetadataEnricherConfig,
        MetadataEnricherService,
    )

    svc = MetadataEnricherService(config=MetadataEnricherConfig())
    await svc.start()

    result = await svc.enrich(
        text=req.text,
        config=EnrichmentConfig(
            extract_keywords=req.extract_keywords,
            language=req.language,
        ),
    )
    return EnrichResponse(
        title=result.title,
        keywords=result.keywords,
        summary=result.summary,
        confidence=result.confidence,
    )


@router.get(
    "/vector-ops/{collection_id}/health",
    response_model=VectorHealthResponse,
    status_code=200,
)
async def vector_collection_health(collection_id: str) -> VectorHealthResponse:
    """Get health information for a vector collection."""
    from aiflow.services.vector_ops.service import VectorOpsConfig, VectorOpsService

    svc = VectorOpsService(session_factory=None, config=VectorOpsConfig())
    await svc.start()

    result = await svc.get_collection_health(collection_id=collection_id)
    return VectorHealthResponse(
        total_vectors=result.total_vectors,
        index_type=result.index_type,
        fragmentation_pct=result.fragmentation_pct,
    )


@router.post("/parse", response_model=ParseResponse, status_code=200)
async def parse_document(req: ParseRequest) -> ParseResponse:
    """Parse a document file using the fallback parser chain."""
    from aiflow.services.advanced_parser.service import (
        AdvancedParserConfig,
        AdvancedParserService,
        ParserConfig,
    )

    svc = AdvancedParserService(config=AdvancedParserConfig())
    await svc.start()

    result = await svc.parse(
        file_path=req.file_path,
        config=ParserConfig(parser=req.parser, ocr_enabled=req.ocr_enabled),
    )
    return ParseResponse(
        text=result.text,
        pages=result.pages,
        parser_used=result.parser_used,
        confidence=result.confidence,
    )


@router.post("/graph/entities", response_model=GraphEntityResponse, status_code=200)
async def extract_graph_entities(req: GraphEntityRequest) -> GraphEntityResponse:
    """Extract entities from text for knowledge graph construction."""
    from aiflow.services.graph_rag.service import GraphRAGConfig, GraphRAGService

    svc = GraphRAGService(config=GraphRAGConfig())
    await svc.start()

    entities = await svc.extract_entities(text=req.text)
    return GraphEntityResponse(entities=entities, count=len(entities))
