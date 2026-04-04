"""Pipeline adapters for RAGEngineService: ingest + query."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from aiflow.core.context import ExecutionContext
from aiflow.pipeline.adapter_base import BaseAdapter, adapter_registry

# --- Ingest adapter ---


class RAGIngestInput(BaseModel):
    """Input schema for RAG document ingestion."""

    collection_id: str = Field(..., description="Target collection UUID")
    file_paths: list[str] = Field(..., description="Paths to documents to ingest")
    language: str | None = Field(None, description="Language override (e.g. 'hu', 'en')")


class RAGIngestOutput(BaseModel):
    """Output schema for RAG ingestion result."""

    collection_id: str = ""
    documents_processed: int = 0
    chunks_created: int = 0
    errors: list[str] = Field(default_factory=list)


class RAGIngestAdapter(BaseAdapter):
    """Adapter wrapping RAGEngineService.ingest_documents for pipeline use."""

    service_name = "rag_engine"
    method_name = "ingest"
    input_schema = RAGIngestInput
    output_schema = RAGIngestOutput

    def __init__(self, service: Any = None) -> None:
        self._service = service

    async def _get_service(self) -> Any:
        if self._service is not None:
            return self._service
        from aiflow.api.deps import get_session_factory
        from aiflow.services.rag_engine.service import RAGEngineConfig, RAGEngineService

        sf = await get_session_factory()
        svc = RAGEngineService(session_factory=sf, config=RAGEngineConfig())
        await svc.start()
        return svc

    async def _run(
        self,
        input_data: BaseModel,
        config: dict[str, Any],
        ctx: ExecutionContext,
    ) -> dict[str, Any]:
        if not isinstance(input_data, RAGIngestInput):
            input_data = RAGIngestInput.model_validate(input_data)
        data = input_data
        svc = await self._get_service()

        result = await svc.ingest_documents(
            collection_id=data.collection_id,
            file_paths=data.file_paths,
            language=data.language,
        )

        return {
            "collection_id": data.collection_id,
            "documents_processed": getattr(result, "documents_processed", 0),
            "chunks_created": getattr(result, "chunks_created", 0),
            "errors": getattr(result, "errors", []),
        }


# --- Query adapter ---


class RAGQueryInput(BaseModel):
    """Input schema for RAG query."""

    collection_id: str = Field(..., description="Collection to query")
    question: str = Field(..., description="User question")
    role: str = Field("expert", description="System role for answer generation")
    top_k: int | None = Field(None, description="Number of results to retrieve")
    model: str | None = Field(None, description="LLM model override")


class RAGQueryOutput(BaseModel):
    """Output schema for RAG query result."""

    answer: str = ""
    sources: list[dict[str, Any]] = Field(default_factory=list)
    response_time_ms: float = 0.0
    query_id: str = ""


class RAGQueryAdapter(BaseAdapter):
    """Adapter wrapping RAGEngineService.query for pipeline use."""

    service_name = "rag_engine"
    method_name = "query"
    input_schema = RAGQueryInput
    output_schema = RAGQueryOutput

    def __init__(self, service: Any = None) -> None:
        self._service = service

    async def _get_service(self) -> Any:
        if self._service is not None:
            return self._service
        from aiflow.api.deps import get_session_factory
        from aiflow.services.rag_engine.service import RAGEngineConfig, RAGEngineService

        sf = await get_session_factory()
        svc = RAGEngineService(session_factory=sf, config=RAGEngineConfig())
        await svc.start()
        return svc

    async def _run(
        self,
        input_data: BaseModel,
        config: dict[str, Any],
        ctx: ExecutionContext,
    ) -> dict[str, Any]:
        if not isinstance(input_data, RAGQueryInput):
            input_data = RAGQueryInput.model_validate(input_data)
        data = input_data
        svc = await self._get_service()

        result = await svc.query(
            collection_id=data.collection_id,
            question=data.question,
            role=data.role,
            top_k=data.top_k,
            model=data.model,
        )

        return {
            "answer": getattr(result, "answer", ""),
            "sources": getattr(result, "sources", []),
            "response_time_ms": getattr(result, "response_time_ms", 0.0),
            "query_id": getattr(result, "query_id", ""),
        }


adapter_registry.register(RAGIngestAdapter())
adapter_registry.register(RAGQueryAdapter())
