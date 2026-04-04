"""
@test_registry:
    suite: aszf-rag-chat-unit
    component: skills.aszf_rag_chat.workflows
    covers:
        - skills/aszf_rag_chat/workflows/query.py
        - skills/aszf_rag_chat/workflows/ingest.py
        - skills/aszf_rag_chat/models/__init__.py
    phase: 4
    priority: critical
    estimated_duration_ms: 3000
    requires_services: []
    tags: [aszf-rag-chat, workflow, rag, legal, unit]
"""
from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from skills.aszf_rag_chat.models import (
    Citation,
    ConversationMessage,
    IngestInput,
    IngestOutput,
    QueryInput,
    QueryOutput,
    RoleType,
    SearchResult,
)

# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture()
def mock_prompt():
    """Return a mock PromptManager.get() result."""
    prompt = MagicMock()
    prompt.compile.return_value = [
        {"role": "system", "content": "You are a test assistant."},
        {"role": "user", "content": "Test question"},
    ]
    prompt.config = SimpleNamespace(
        model="openai/gpt-4o-mini",
        temperature=0.1,
        max_tokens=512,
    )
    return prompt


@pytest.fixture()
def mock_generate_result():
    """Return a mock ModelClient.generate() result."""
    result = MagicMock()
    result.output = SimpleNamespace(text="Rewritten test question with synonyms")
    result.cost_usd = 0.001
    result.input_tokens = 50
    result.output_tokens = 30
    return result


@pytest.fixture()
def sample_search_results():
    """Return sample search result dicts as produced by search_documents."""
    return [
        {
            "chunk_id": str(uuid.uuid4()),
            "content": "Az adatkezelés jogalapja a GDPR 6. cikk (1) a) pontja.",
            "score": 0.92,
            "vector_score": 0.88,
            "keyword_score": 0.45,
            "document_title": "AHE-43285_Adatkezelesi.pdf",
            "section_title": "1. Adatkezelés jogalapja",
            "page_start": 3,
            "metadata": {"chunk_index": 0},
        },
        {
            "chunk_id": str(uuid.uuid4()),
            "content": "Az érintett hozzájárulását bármikor visszavonhatja.",
            "score": 0.85,
            "vector_score": 0.82,
            "keyword_score": 0.30,
            "document_title": "AHE-43285_Adatkezelesi.pdf",
            "section_title": "2. Hozzájárulás visszavonása",
            "page_start": 5,
            "metadata": {"chunk_index": 1},
        },
    ]


# ══════════════════════════════════════════════════════════════════════════════
# 1. PYDANTIC MODEL TESTS (8 tests)
# ══════════════════════════════════════════════════════════════════════════════


class TestPydanticModels:
    """Validate Pydantic I/O models used by the RAG pipeline."""

    def test_query_input_defaults(self):
        qi = QueryInput(question="test")
        assert qi.collection == "default"
        assert qi.role == "baseline"
        assert qi.language == "hu"
        assert qi.top_k == 5
        assert qi.conversation_history == []

    def test_query_input_custom_values(self):
        qi = QueryInput(
            question="Mi a GDPR?",
            collection="azhu-aszf-2024",
            role="expert",
            top_k=10,
        )
        assert qi.role == "expert"
        assert qi.top_k == 10

    def test_query_output_defaults(self):
        qo = QueryOutput()
        assert qo.answer == ""
        assert qo.citations == []
        assert qo.hallucination_score == 1.0
        assert qo.cost_usd == 0.0

    def test_search_result_model(self):
        sr = SearchResult(
            chunk_id="abc-123",
            content="Test content",
            similarity_score=0.95,
            document_name="test.pdf",
            chunk_index=0,
            metadata={"page": 1},
        )
        assert sr.similarity_score == 0.95
        assert sr.metadata == {"page": 1}

    def test_citation_model(self):
        c = Citation(
            document_name="AHE.pdf",
            section="1. fejezet",
            page=3,
            chunk_index=0,
            relevance_score=0.9,
            excerpt="Rövid részlet...",
        )
        assert c.page == 3
        d = c.model_dump()
        assert "document_name" in d

    def test_citation_optional_fields(self):
        c = Citation(document_name="test.pdf")
        assert c.section == ""
        assert c.page is None
        assert c.relevance_score == 0.0

    def test_conversation_message(self):
        msg = ConversationMessage(role="user", content="Hello")
        assert msg.role == "user"

    def test_role_type_constants(self):
        assert RoleType.BASELINE == "baseline"
        assert RoleType.MENTOR == "mentor"
        assert RoleType.EXPERT == "expert"


# ══════════════════════════════════════════════════════════════════════════════
# 2. QUERY WORKFLOW STEP TESTS (22 tests)
# ══════════════════════════════════════════════════════════════════════════════


class TestRewriteQuery:
    """Test rewrite_query step."""

    @pytest.mark.asyncio
    async def test_basic_rewrite(self, mock_prompt, mock_generate_result):
        from skills.aszf_rag_chat.workflows import query as qmod

        with (
            patch.object(qmod, "_prompt_manager") as pm,
            patch.object(qmod, "_model_client") as mc,
        ):
            pm.get.return_value = mock_prompt
            mc.generate = AsyncMock(return_value=mock_generate_result)

            result = await qmod.rewrite_query({"question": "Mi a biztosítás?"})

            assert "rewritten_query" in result
            assert result["original_question"] == "Mi a biztosítás?"
            pm.get.assert_called_once_with("aszf-rag/query_rewriter")

    @pytest.mark.asyncio
    async def test_empty_question_raises(self):
        from skills.aszf_rag_chat.workflows import query as qmod

        with pytest.raises(ValueError, match="empty"):
            await qmod.rewrite_query({"question": ""})

    @pytest.mark.asyncio
    async def test_whitespace_question_raises(self):
        from skills.aszf_rag_chat.workflows import query as qmod

        with pytest.raises(ValueError, match="empty"):
            await qmod.rewrite_query({"question": "   "})

    @pytest.mark.asyncio
    async def test_preserves_language(self, mock_prompt, mock_generate_result):
        from skills.aszf_rag_chat.workflows import query as qmod

        with (
            patch.object(qmod, "_prompt_manager") as pm,
            patch.object(qmod, "_model_client") as mc,
        ):
            pm.get.return_value = mock_prompt
            mc.generate = AsyncMock(return_value=mock_generate_result)

            await qmod.rewrite_query({"question": "Test?", "language": "en"})
            call_vars = mock_prompt.compile.call_args[1]["variables"]
            assert call_vars["language"] == "en"


class TestSearchDocuments:
    """Test search_documents step."""

    @pytest.mark.asyncio
    async def test_basic_search(self):
        from skills.aszf_rag_chat.workflows import query as qmod

        mock_result = MagicMock()
        mock_result.chunk_id = uuid.uuid4()
        mock_result.content = "Test chunk"
        mock_result.score = 0.9
        mock_result.vector_score = 0.85
        mock_result.keyword_score = 0.4
        mock_result.document_title = "doc.pdf"
        mock_result.section_title = "Section 1"
        mock_result.page_start = 1
        mock_result.metadata = {}

        with (
            patch.object(qmod, "_embedder") as emb,
            patch.object(qmod, "_search_engine") as se,
        ):
            emb.embed_texts = AsyncMock(return_value=[[0.1] * 1536])
            se.search = AsyncMock(return_value=[mock_result])

            result = await qmod.search_documents({
                "rewritten_query": "test query",
                "original_question": "test?",
                "collection": "test-col",
            })

            assert len(result["search_results"]) == 1
            assert result["collection"] == "test-col"
            assert isinstance(result["search_results"][0]["chunk_id"], str)

    @pytest.mark.asyncio
    async def test_empty_search_results(self):
        from skills.aszf_rag_chat.workflows import query as qmod

        with (
            patch.object(qmod, "_embedder") as emb,
            patch.object(qmod, "_search_engine") as se,
        ):
            emb.embed_texts = AsyncMock(return_value=[[0.1] * 10])
            se.search = AsyncMock(return_value=[])

            result = await qmod.search_documents({
                "rewritten_query": "nonexistent topic",
            })
            assert result["search_results"] == []

    @pytest.mark.asyncio
    async def test_default_collection(self):
        from skills.aszf_rag_chat.workflows import query as qmod

        with (
            patch.object(qmod, "_embedder") as emb,
            patch.object(qmod, "_search_engine") as se,
        ):
            emb.embed_texts = AsyncMock(return_value=[[0.1]])
            se.search = AsyncMock(return_value=[])

            result = await qmod.search_documents({"rewritten_query": "q"})
            assert result["collection"] == "default"


class TestBuildContext:
    """Test build_context step (pure logic, no mocks needed)."""

    @pytest.mark.asyncio
    async def test_formats_numbered_context(self, sample_search_results):
        from skills.aszf_rag_chat.workflows.query import build_context

        result = await build_context({
            "search_results": sample_search_results,
            "original_question": "Test?",
        })

        assert "[1] Source:" in result["context"]
        assert "[2] Source:" in result["context"]
        assert len(result["sources"]) == 2

    @pytest.mark.asyncio
    async def test_empty_search_results(self):
        from skills.aszf_rag_chat.workflows.query import build_context

        result = await build_context({
            "search_results": [],
            "original_question": "Test?",
        })
        assert result["context"] == ""
        assert result["sources"] == []

    @pytest.mark.asyncio
    async def test_source_metadata(self, sample_search_results):
        from skills.aszf_rag_chat.workflows.query import build_context

        result = await build_context({
            "search_results": sample_search_results,
            "original_question": "Test?",
        })

        src = result["sources"][0]
        assert src["index"] == 1
        assert src["document_name"] == "AHE-43285_Adatkezelesi.pdf"
        assert src["page"] == 3
        assert len(src["excerpt"]) <= 200

    @pytest.mark.asyncio
    async def test_page_in_source_line(self, sample_search_results):
        from skills.aszf_rag_chat.workflows.query import build_context

        result = await build_context({
            "search_results": sample_search_results,
            "original_question": "Test?",
        })
        assert "(p. 3)" in result["context"]

    @pytest.mark.asyncio
    async def test_section_in_source_line(self, sample_search_results):
        from skills.aszf_rag_chat.workflows.query import build_context

        result = await build_context({
            "search_results": sample_search_results,
            "original_question": "Test?",
        })
        assert "1. Adatkezelés jogalapja" in result["context"]


class TestGenerateAnswer:
    """Test generate_answer step."""

    @pytest.mark.asyncio
    async def test_baseline_role(self, mock_prompt, mock_generate_result):
        from skills.aszf_rag_chat.workflows import query as qmod

        mock_generate_result.output.text = "Az adatkezelés jogalapja a GDPR."

        with (
            patch.object(qmod, "_prompt_manager") as pm,
            patch.object(qmod, "_model_client") as mc,
        ):
            pm.get.return_value = mock_prompt
            mc.generate = AsyncMock(return_value=mock_generate_result)

            result = await qmod.generate_answer({
                "context": "GDPR context...",
                "question": "Mi a jogalap?",
                "sources": [],
                "search_results": [],
                "role": "baseline",
            })

            assert result["answer"] == "Az adatkezelés jogalapja a GDPR."
            assert result["role"] == "baseline"

    @pytest.mark.asyncio
    async def test_expert_role(self, mock_prompt, mock_generate_result):
        from skills.aszf_rag_chat.workflows import query as qmod

        mock_generate_result.output.text = "Expert answer"

        with (
            patch.object(qmod, "_prompt_manager") as pm,
            patch.object(qmod, "_model_client") as mc,
        ):
            pm.get.return_value = mock_prompt
            mc.generate = AsyncMock(return_value=mock_generate_result)

            result = await qmod.generate_answer({
                "context": "context",
                "question": "Q?",
                "sources": [],
                "search_results": [],
                "role": "expert",
            })
            assert result["role"] == "expert"

    @pytest.mark.asyncio
    async def test_fallback_on_prompt_error(self, mock_generate_result):
        from skills.aszf_rag_chat.workflows import query as qmod

        mock_generate_result.output.text = "Fallback answer"

        with (
            patch.object(qmod, "_prompt_manager") as pm,
            patch.object(qmod, "_model_client") as mc,
        ):
            pm.get.side_effect = Exception("Prompt not found")
            mc.generate = AsyncMock(return_value=mock_generate_result)

            result = await qmod.generate_answer({
                "context": "ctx",
                "question": "Q?",
                "sources": [],
                "search_results": [],
            })
            assert result["answer"] == "Fallback answer"

    @pytest.mark.asyncio
    async def test_conversation_history_injected(self, mock_prompt, mock_generate_result):
        from skills.aszf_rag_chat.workflows import query as qmod

        mock_generate_result.output.text = "Answer with history"

        with (
            patch.object(qmod, "_prompt_manager") as pm,
            patch.object(qmod, "_model_client") as mc,
        ):
            pm.get.return_value = mock_prompt
            mc.generate = AsyncMock(return_value=mock_generate_result)

            result = await qmod.generate_answer({
                "context": "ctx",
                "question": "Follow-up?",
                "sources": [],
                "search_results": [],
                "conversation_history": [
                    {"role": "user", "content": "Prev question"},
                    {"role": "assistant", "content": "Prev answer"},
                ],
            })
            # History should be injected into messages
            call_messages = mc.generate.call_args[1]["messages"]
            assert len(call_messages) >= 3  # system + history + user

    @pytest.mark.asyncio
    async def test_passthrough_fields(self, mock_prompt, mock_generate_result):
        from skills.aszf_rag_chat.workflows import query as qmod

        mock_generate_result.output.text = "ans"

        with (
            patch.object(qmod, "_prompt_manager") as pm,
            patch.object(qmod, "_model_client") as mc,
        ):
            pm.get.return_value = mock_prompt
            mc.generate = AsyncMock(return_value=mock_generate_result)

            sources = [{"doc": "test"}]
            result = await qmod.generate_answer({
                "context": "c",
                "question": "q",
                "sources": sources,
                "search_results": [{"x": 1}],
            })
            assert result["sources"] == sources
            assert result["search_results"] == [{"x": 1}]


class TestExtractCitations:
    """Test extract_citations step."""

    @pytest.mark.asyncio
    async def test_extracts_citations(self, mock_prompt):
        from skills.aszf_rag_chat.workflows import query as qmod

        mock_result = MagicMock()
        mock_result.output = SimpleNamespace(
            structured=[
                Citation(document_name="AHE.pdf", section="1", page=3, relevance_score=0.9, excerpt="..."),
            ]
        )

        with (
            patch.object(qmod, "_prompt_manager") as pm,
            patch.object(qmod, "_model_client") as mc,
        ):
            pm.get.return_value = mock_prompt
            mc.generate = AsyncMock(return_value=mock_result)

            result = await qmod.extract_citations({
                "answer": "Answer [1]",
                "context": "ctx",
                "sources": [],
                "search_results": [],
            })
            assert len(result["citations"]) == 1
            assert result["citations"][0]["document_name"] == "AHE.pdf"

    @pytest.mark.asyncio
    async def test_empty_citations(self, mock_prompt):
        from skills.aszf_rag_chat.workflows import query as qmod

        mock_result = MagicMock()
        mock_result.output = SimpleNamespace(structured=[])

        with (
            patch.object(qmod, "_prompt_manager") as pm,
            patch.object(qmod, "_model_client") as mc,
        ):
            pm.get.return_value = mock_prompt
            mc.generate = AsyncMock(return_value=mock_result)

            result = await qmod.extract_citations({
                "answer": "No citations",
                "context": "",
                "sources": [],
                "search_results": [],
            })
            assert result["citations"] == []


class TestDetectHallucination:
    """Test detect_hallucination step."""

    @pytest.mark.asyncio
    async def test_high_score(self, mock_prompt):
        from skills.aszf_rag_chat.workflows import query as qmod

        mock_result = MagicMock()
        mock_result.output = SimpleNamespace(text="0.95")
        mock_result.cost_usd = 0.001

        with (
            patch.object(qmod, "_prompt_manager") as pm,
            patch.object(qmod, "_model_client") as mc,
        ):
            pm.get.return_value = mock_prompt
            mc.generate = AsyncMock(return_value=mock_result)

            result = await qmod.detect_hallucination({
                "answer": "Grounded answer",
                "citations": [],
                "sources": [],
                "search_results": [{"content": "source text"}],
            })
            assert result["hallucination_score"] == 0.95

    @pytest.mark.asyncio
    async def test_low_score(self, mock_prompt):
        from skills.aszf_rag_chat.workflows import query as qmod

        mock_result = MagicMock()
        mock_result.output = SimpleNamespace(text="0.2 - mostly hallucinated")
        mock_result.cost_usd = 0.001

        with (
            patch.object(qmod, "_prompt_manager") as pm,
            patch.object(qmod, "_model_client") as mc,
        ):
            pm.get.return_value = mock_prompt
            mc.generate = AsyncMock(return_value=mock_result)

            result = await qmod.detect_hallucination({
                "answer": "Made up answer",
                "citations": [],
                "sources": [],
                "search_results": [],
            })
            assert result["hallucination_score"] == 0.2

    @pytest.mark.asyncio
    async def test_parse_error_defaults_to_half(self, mock_prompt):
        from skills.aszf_rag_chat.workflows import query as qmod

        mock_result = MagicMock()
        mock_result.output = SimpleNamespace(text="cannot parse this")
        mock_result.cost_usd = 0.0

        with (
            patch.object(qmod, "_prompt_manager") as pm,
            patch.object(qmod, "_model_client") as mc,
        ):
            pm.get.return_value = mock_prompt
            mc.generate = AsyncMock(return_value=mock_result)

            result = await qmod.detect_hallucination({
                "answer": "ans",
                "citations": [],
                "sources": [],
                "search_results": [],
            })
            assert result["hallucination_score"] == 0.5

    @pytest.mark.asyncio
    async def test_clamps_above_one(self, mock_prompt):
        from skills.aszf_rag_chat.workflows import query as qmod

        mock_result = MagicMock()
        mock_result.output = SimpleNamespace(text="1.5")
        mock_result.cost_usd = 0.0

        with (
            patch.object(qmod, "_prompt_manager") as pm,
            patch.object(qmod, "_model_client") as mc,
        ):
            pm.get.return_value = mock_prompt
            mc.generate = AsyncMock(return_value=mock_result)

            result = await qmod.detect_hallucination({
                "answer": "a",
                "citations": [],
                "sources": [],
                "search_results": [],
            })
            assert result["hallucination_score"] == 1.0

    @pytest.mark.asyncio
    async def test_cost_usd_passthrough(self, mock_prompt):
        from skills.aszf_rag_chat.workflows import query as qmod

        mock_result = MagicMock()
        mock_result.output = SimpleNamespace(text="0.8")
        mock_result.cost_usd = 0.0042

        with (
            patch.object(qmod, "_prompt_manager") as pm,
            patch.object(qmod, "_model_client") as mc,
        ):
            pm.get.return_value = mock_prompt
            mc.generate = AsyncMock(return_value=mock_result)

            result = await qmod.detect_hallucination({
                "answer": "a",
                "citations": [],
                "sources": [],
                "search_results": [],
            })
            assert result["cost_usd"] == 0.0042


# ══════════════════════════════════════════════════════════════════════════════
# 3. INGEST WORKFLOW STEP TESTS (14 tests)
# ══════════════════════════════════════════════════════════════════════════════


class TestLoadDocuments:
    """Test load_documents step."""

    @pytest.mark.asyncio
    async def test_loads_files(self, tmp_path):
        from skills.aszf_rag_chat.workflows.ingest import load_documents

        (tmp_path / "doc1.pdf").write_bytes(b"PDF content")
        (tmp_path / "doc2.md").write_text("# Heading", encoding="utf-8")
        (tmp_path / "ignored.exe").write_bytes(b"binary")

        result = await load_documents({
            "source_path": str(tmp_path),
            "collection": "test-col",
        })

        assert len(result["files"]) == 2
        assert result["collection"] == "test-col"
        names = {f["name"] for f in result["files"]}
        assert "doc1.pdf" in names
        assert "doc2.md" in names
        assert "ignored.exe" not in names

    @pytest.mark.asyncio
    async def test_nonexistent_path_raises(self):
        from skills.aszf_rag_chat.workflows.ingest import load_documents

        with pytest.raises(FileNotFoundError):
            await load_documents({
                "source_path": "/nonexistent/path",
                "collection": "test",
            })

    @pytest.mark.asyncio
    async def test_empty_directory_raises(self, tmp_path):
        from skills.aszf_rag_chat.workflows.ingest import load_documents

        with pytest.raises(ValueError, match="No supported"):
            await load_documents({
                "source_path": str(tmp_path),
                "collection": "test",
            })

    @pytest.mark.asyncio
    async def test_recursive_scan(self, tmp_path):
        from skills.aszf_rag_chat.workflows.ingest import load_documents

        sub = tmp_path / "subdir"
        sub.mkdir()
        (sub / "nested.txt").write_text("content", encoding="utf-8")

        result = await load_documents({
            "source_path": str(tmp_path),
            "collection": "test",
        })
        assert len(result["files"]) == 1
        assert result["files"][0]["name"] == "nested.txt"

    @pytest.mark.asyncio
    async def test_default_language(self, tmp_path):
        from skills.aszf_rag_chat.workflows.ingest import load_documents

        (tmp_path / "doc.txt").write_text("x", encoding="utf-8")
        result = await load_documents({
            "source_path": str(tmp_path),
            "collection": "test",
        })
        assert result["language"] == "hu"


class TestChunkDocuments:
    """Test chunk_documents step."""

    @pytest.mark.asyncio
    async def test_creates_chunks(self):
        from skills.aszf_rag_chat.workflows import ingest as imod

        mock_chunk = MagicMock()
        mock_chunk.text = "Chunk text"
        mock_chunk.metadata = {"start": 0, "end": 100}
        mock_chunker_cls = MagicMock(
            return_value=MagicMock(chunk_text=MagicMock(return_value=[mock_chunk]))
        )

        with patch(
            "aiflow.ingestion.chunkers.recursive_chunker.RecursiveChunker",
            mock_chunker_cls,
        ):
            result = await imod.chunk_documents({
                "documents": [
                    {"name": "doc.pdf", "text": "Long document text " * 50},
                ],
                "collection": "test-col",
                "language": "hu",
            })

            assert result["total_chunks"] >= 1
            assert result["collection"] == "test-col"
            chunk = result["chunks"][0]
            assert "chunk_id" in chunk
            assert "content" in chunk
            assert "document_name" in chunk

    @pytest.mark.asyncio
    async def test_chunk_ids_are_uuids(self):
        from skills.aszf_rag_chat.workflows import ingest as imod

        mock_chunk = MagicMock()
        mock_chunk.text = "Text"
        mock_chunk.metadata = {}
        mock_chunker_cls = MagicMock(
            return_value=MagicMock(chunk_text=MagicMock(return_value=[mock_chunk]))
        )

        with patch(
            "aiflow.ingestion.chunkers.recursive_chunker.RecursiveChunker",
            mock_chunker_cls,
        ):
            result = await imod.chunk_documents({
                "documents": [{"name": "d.pdf", "text": "text"}],
                "collection": "c",
                "language": "hu",
            })
            # Should be valid UUID
            uuid.UUID(result["chunks"][0]["chunk_id"])


class TestGenerateEmbeddings:
    """Test generate_embeddings step."""

    @pytest.mark.asyncio
    async def test_embeds_chunks(self):
        from skills.aszf_rag_chat.workflows import ingest as imod

        chunks = [
            {"chunk_id": "1", "content": "Chunk 1", "document_name": "d.pdf"},
            {"chunk_id": "2", "content": "Chunk 2", "document_name": "d.pdf"},
        ]

        with patch.object(imod, "_embedder") as emb:
            emb.embed_texts = AsyncMock(return_value=[[0.1] * 1536, [0.2] * 1536])

            result = await imod.generate_embeddings({
                "chunks": chunks,
                "collection": "test",
            })

            assert len(result["chunks_with_embeddings"]) == 2
            assert "embedding" in result["chunks_with_embeddings"][0]
            assert len(result["chunks_with_embeddings"][0]["embedding"]) == 1536


class TestStoreChunks:
    """Test store_chunks step."""

    @pytest.mark.asyncio
    async def test_stores_to_pgvector(self):
        from skills.aszf_rag_chat.workflows import ingest as imod

        chunks_with_emb = [
            {
                "chunk_id": "1",
                "content": "c1",
                "document_name": "d.pdf",
                "embedding": [0.1] * 1536,
            },
        ]

        with patch.object(imod, "_vector_store") as vs:
            vs.upsert_chunks = AsyncMock(return_value=1)

            result = await imod.store_chunks({
                "chunks_with_embeddings": chunks_with_emb,
                "collection": "test",
            })
            assert result["stored_count"] == 1
            vs.upsert_chunks.assert_called_once()


class TestVerifyIngestion:
    """Test verify_ingestion step."""

    @pytest.mark.asyncio
    async def test_verify_healthy(self):
        from skills.aszf_rag_chat.workflows import ingest as imod

        with patch.object(imod, "_vector_store") as vs:
            vs.health_check = AsyncMock(return_value=True)

            result = await imod.verify_ingestion({
                "stored_count": 10,
                "collection": "test",
            })
            assert result["verified"] is True
            assert result["total_chunks"] == 10

    @pytest.mark.asyncio
    async def test_verify_unhealthy(self):
        from skills.aszf_rag_chat.workflows import ingest as imod

        with patch.object(imod, "_vector_store") as vs:
            vs.health_check = AsyncMock(return_value=False)

            result = await imod.verify_ingestion({
                "stored_count": 0,
                "collection": "test",
            })
            assert result["verified"] is False


# ══════════════════════════════════════════════════════════════════════════════
# 4. EDGE CASE & ERROR HANDLING TESTS (8 tests)
# ══════════════════════════════════════════════════════════════════════════════


class TestEdgeCases:
    """Test error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_build_context_no_page(self):
        from skills.aszf_rag_chat.workflows.query import build_context

        result = await build_context({
            "search_results": [{
                "content": "text",
                "document_title": "doc",
                "section_title": "",
                "page_start": None,
                "score": 0.5,
                "metadata": {},
            }],
            "original_question": "q",
        })
        assert "(p." not in result["context"]

    @pytest.mark.asyncio
    async def test_build_context_no_section(self):
        from skills.aszf_rag_chat.workflows.query import build_context

        result = await build_context({
            "search_results": [{
                "content": "text",
                "document_title": "doc",
                "section_title": "",
                "page_start": 1,
                "score": 0.5,
                "metadata": {},
            }],
            "original_question": "q",
        })
        assert "/" not in result["context"].split("\n")[0]

    @pytest.mark.asyncio
    async def test_generate_answer_unknown_role_fallback(self, mock_prompt, mock_generate_result):
        from skills.aszf_rag_chat.workflows import query as qmod

        mock_generate_result.output.text = "fallback ans"

        with (
            patch.object(qmod, "_prompt_manager") as pm,
            patch.object(qmod, "_model_client") as mc,
        ):
            pm.get.return_value = mock_prompt
            mc.generate = AsyncMock(return_value=mock_generate_result)

            result = await qmod.generate_answer({
                "context": "c",
                "question": "q",
                "sources": [],
                "search_results": [],
                "role": "nonexistent_role",
            })
            # Falls back to baseline
            assert result["answer"] == "fallback ans"

    @pytest.mark.asyncio
    async def test_log_query_best_effort(self):
        """log_query should not raise even if DB is unavailable."""
        from skills.aszf_rag_chat.workflows import query as qmod

        # _log_query_to_db internally catches exceptions; mock asyncpg.connect to fail
        with patch("skills.aszf_rag_chat.workflows.query.asyncpg") as mock_pg:
            mock_pg.connect = AsyncMock(side_effect=Exception("DB down"))

            result = await qmod.log_query({
                "answer": "test",
                "collection": "test",
            })
            # Should return data without raising
            assert "answer" in result

    @pytest.mark.asyncio
    async def test_search_with_custom_top_k(self):
        from skills.aszf_rag_chat.workflows import query as qmod

        with (
            patch.object(qmod, "_embedder") as emb,
            patch.object(qmod, "_search_engine") as se,
        ):
            emb.embed_texts = AsyncMock(return_value=[[0.1]])
            se.search = AsyncMock(return_value=[])

            await qmod.search_documents({
                "rewritten_query": "q",
                "top_k": 10,
            })
            call_kwargs = se.search.call_args[1]
            assert call_kwargs["top_k"] == 10

    @pytest.mark.asyncio
    async def test_hallucination_clamps_below_zero(self, mock_prompt):
        from skills.aszf_rag_chat.workflows import query as qmod

        mock_result = MagicMock()
        mock_result.output = SimpleNamespace(text="-0.5")
        mock_result.cost_usd = 0.0

        with (
            patch.object(qmod, "_prompt_manager") as pm,
            patch.object(qmod, "_model_client") as mc,
        ):
            pm.get.return_value = mock_prompt
            mc.generate = AsyncMock(return_value=mock_result)

            result = await qmod.detect_hallucination({
                "answer": "a", "citations": [], "sources": [], "search_results": [],
            })
            assert result["hallucination_score"] == 0.0

    @pytest.mark.asyncio
    async def test_extract_citations_non_list_returns_empty(self, mock_prompt):
        from skills.aszf_rag_chat.workflows import query as qmod

        mock_result = MagicMock()
        mock_result.output = SimpleNamespace(structured="not a list")

        with (
            patch.object(qmod, "_prompt_manager") as pm,
            patch.object(qmod, "_model_client") as mc,
        ):
            pm.get.return_value = mock_prompt
            mc.generate = AsyncMock(return_value=mock_result)

            result = await qmod.extract_citations({
                "answer": "a", "context": "", "sources": [], "search_results": [],
            })
            assert result["citations"] == []

    def test_ingest_input_model(self):
        ii = IngestInput(source_path="/tmp/docs", collection="test")
        assert ii.language == "hu"

    def test_ingest_output_model(self):
        io = IngestOutput(total_chunks=42, collection="test")
        assert io.total_chunks == 42
