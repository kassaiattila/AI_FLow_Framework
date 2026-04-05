# AIFlow - Vector Adatbazis es Forrasadat-kezeles (RAG)

## Fo Dontesek

| Dontes | Valasztás | Indoklas |
|--------|----------|----------|
| Vector DB | **pgvector** (pgvector/pgvector:pg16 Docker image) | Mar van PostgreSQL, 12k chunk problemamentes, HNSW index |
| Embedding | text-embedding-3-small (1536 dim) | Multilingual (90% magyar), $0.12 teljes ingest |
| Search | **Hybrid** (vector + BM25 RRF) | Egy DB-ben, tsvector + pgvector egyutt |
| Collection | Per-skill izolacio, shared option | Mint prompt namespace: skill_name/collection_name |
| Migration path | pgvector -> Qdrant | Ha p95 > 200ms 100k+ chunk-nal |

---

## Dokumentum Eletciklus

```
draft -> active -> superseded -> revoked -> archived
                        |
                        +-- Uj verzio felvaltja (supersedes_id)
                        +-- Regi chunk-ok kiszurve (freshness enforcement)
                        +-- Uj chunk-ok generalva es indexelve
```

**Freshness Enforcement:** MINDEN kereses automatikusan szuri:
```sql
WHERE document_status = 'active'
  AND (effective_from IS NULL OR effective_from <= CURRENT_DATE)
  AND (effective_until IS NULL OR effective_until >= CURRENT_DATE)
```
A `HybridSearchEngine` retegben kikenyszeritve -> skill kod nem kerukheti meg.

---

## Adatbazis Schema (Fo Tablak)

### documents (Dokumentum Nyilvantartas)
```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    filename VARCHAR(500) NOT NULL,
    file_type VARCHAR(20) NOT NULL,         -- pdf, docx, xlsx
    file_hash_sha256 VARCHAR(64) NOT NULL,  -- Valtozas detektalas
    document_type VARCHAR(100) NOT NULL,    -- aszf, szabalyzat, jogszabaly
    department VARCHAR(100),
    language VARCHAR(10) DEFAULT 'hu',
    status VARCHAR(20) DEFAULT 'draft',     -- draft/active/superseded/revoked/archived
    effective_from DATE,
    effective_until DATE,
    version_number INT DEFAULT 1,
    supersedes_id UUID REFERENCES documents(id),
    skill_name VARCHAR(255) NOT NULL,
    collection_name VARCHAR(255) NOT NULL,
    chunk_count INT DEFAULT 0,
    embedding_model VARCHAR(100),
    ingestion_status VARCHAR(20) DEFAULT 'pending',
    source_type VARCHAR(50),                -- upload, sharepoint, s3, gdrive
    source_uri TEXT,
    storage_path TEXT NOT NULL
);
```

### chunks (Vektor Tarolás + BM25)
```sql
CREATE TABLE chunks (
    id UUID PRIMARY KEY,
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    token_count INT NOT NULL,
    chunk_index INT NOT NULL,
    page_start INT, page_end INT,
    section_title VARCHAR(500),
    section_hierarchy JSONB,                -- ["3. Fejezet", "3.2 Szakasz"]
    parent_chunk_id UUID REFERENCES chunks(id),  -- Hierarchikus chunking
    embedding vector(1536),                 -- pgvector
    embedding_model VARCHAR(100) NOT NULL,
    content_tsv tsvector,                   -- BM25 full-text search
    skill_name VARCHAR(255) NOT NULL,
    collection_name VARCHAR(255) NOT NULL,
    -- Denormalizalt metadata (gyors szures)
    document_title VARCHAR(500),
    document_status VARCHAR(20),
    effective_from DATE, effective_until DATE,
    language VARCHAR(10), department VARCHAR(100)
);

-- HNSW index (cosine)
CREATE INDEX idx_chunks_embedding ON chunks
    USING hnsw (embedding vector_cosine_ops) WITH (m=16, ef_construction=64);
-- BM25 index
CREATE INDEX idx_chunks_tsv ON chunks USING GIN (content_tsv);
-- Szuro index-ek
CREATE INDEX idx_chunks_skill_coll ON chunks(skill_name, collection_name);
CREATE INDEX idx_chunks_status ON chunks(document_status);
```

### collections (Logikai Csoportositas)
```sql
CREATE TABLE collections (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    skill_name VARCHAR(255) NOT NULL,
    embedding_model_id UUID REFERENCES embedding_models(id),
    document_count INT DEFAULT 0,
    chunk_count INT DEFAULT 0,
    is_shared BOOLEAN DEFAULT FALSE,        -- Mas skill-ek olvashatjak?
    chunking_config JSONB DEFAULT '{}',
    search_config JSONB DEFAULT '{}',
    team_id UUID REFERENCES teams(id),
    UNIQUE(name, skill_name)
);
```

### document_sync_schedules (Kulso Forras Szinkronizacio)
```sql
CREATE TABLE document_sync_schedules (
    id UUID PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    collection_id UUID REFERENCES collections(id),
    source_type VARCHAR(50) NOT NULL,       -- sharepoint, s3, gdrive
    source_config JSONB NOT NULL,           -- Kapcsolodasi adatok
    sync_cron VARCHAR(100) NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    last_sync_at TIMESTAMPTZ,
    last_sync_status VARCHAR(20)
);
```

### Monitoring View-k
```sql
-- Collection egeszseg
CREATE VIEW v_collection_health AS
SELECT c.name, c.skill_name, c.chunk_count,
    COUNT(DISTINCT d.id) FILTER (WHERE d.status = 'active') as active_docs,
    COUNT(ch.id) FILTER (WHERE ch.embedding IS NULL) as missing_embeddings,
    MAX(d.last_ingested_at) as last_ingestion
FROM collections c
LEFT JOIN documents d ON d.collection_name = c.name
LEFT JOIN chunks ch ON ch.document_id = d.id
GROUP BY c.id;

-- Dokumentum frissesseg
CREATE VIEW v_document_freshness AS
SELECT d.title, d.status,
    CASE WHEN effective_until < CURRENT_DATE THEN 'expired'
         WHEN effective_from > CURRENT_DATE THEN 'future'
         WHEN status = 'active' THEN 'current'
         ELSE status END as freshness_status
FROM documents d;
```

---

## Python Interfeszek

### VectorStore (Adapter Pattern)

```python
class VectorStore(ABC):
    async def upsert_chunks(self, collection, skill_name, chunks, embeddings) -> int: ...
    async def search(self, collection, skill_name, query_embedding,
                     query_text=None, top_k=10, filters=None,
                     search_mode="hybrid") -> list[SearchResult]: ...
    async def delete_by_document(self, collection, skill_name, document_id) -> int: ...

class SearchResult(BaseModel):
    chunk_id: UUID
    content: str
    score: float                    # Kombinalt relevancia
    vector_score: float | None
    keyword_score: float | None
    document_id: UUID
    document_title: str
    section_title: str | None
    page_start: int | None
    effective_from: date | None
```

### HybridSearchEngine (Vector + BM25 + RRF)

```python
class HybridSearchEngine:
    def __init__(self, vector_store, embedder,
                 vector_weight=0.6, keyword_weight=0.4, rrf_k=60): ...

    async def search(self, query, collection, skill_name, ctx,
                     top_k=10, filters=None,
                     freshness_enforced=True) -> list[SearchResult]: ...
```

### DocumentRegistry (Eletciklus Kezeles)

```python
class DocumentRegistry:
    async def register(self, file_path, skill_name, collection_name,
                       document_type, effective_from=None, effective_until=None,
                       supersedes_id=None) -> Document: ...
    async def update_status(self, document_id, new_status, reason=None) -> Document: ...
    async def supersede(self, old_id, new_id) -> None: ...  # Atomikus tranzakcio
    async def check_freshness(self, skill_name, collection_name) -> FreshnessReport: ...
```

---

## Ingestion Pipeline (AIFlow Workflow!)

Az ingestion **maga is AIFlow workflow** - ugyanaz az observability, retry, cost tracking:

```python
@workflow(name="document-ingest", version="1.0.0", skill="aszf_rag_chat")
def document_ingest(wf: WorkflowBuilder):
    wf.step(validate_document)          # Tipus, meret, duplikatum check
    wf.step(parse_document)             # PDF/DOCX -> text (pymupdf/python-docx)
    wf.step(extract_metadata)           # Cim, fejezetek, datumok
    wf.step(chunk_document)             # Szemantikus chunking (500 token, 100 overlap)
    wf.step(generate_embeddings)        # Batch embed (LiteLLM, cost tracked)
    wf.step(store_chunks)              # pgvector upsert
    wf.step(validate_ingestion)        # Minoseg check
    wf.quality_gate(after="validate_ingestion",
                    gate=QualityGate(metric="embedding_coverage",
                                    threshold=0.80, on_fail="flag_for_review"))
    wf.step(update_registry)           # document.ingestion_status = "completed"
```

### Chunking Konfiguracio

```python
class ChunkingConfig(BaseModel):
    strategy: Literal["semantic", "fixed", "hierarchical"] = "semantic"
    target_chunk_tokens: int = 500
    max_chunk_tokens: int = 800
    overlap_tokens: int = 100
    section_separators: list[str] = ["\n## ", "\n### ", "\n\n"]
    min_chunk_tokens: int = 50
```

---

## Kulso Forras Szinkronizacio

```yaml
# aiflow.yaml
vectorstore:
  sync_sources:
    - name: "sharepoint-hr-policies"
      type: sharepoint
      collection: aszf_documents
      config:
        site_url: "https://company.sharepoint.com/sites/HR"
        folder: "/Policies"
        auth: vault://sharepoint/credentials
      cron: "0 2 * * *"            # Minden ejjel 2-kor

    - name: "s3-legal-docs"
      type: s3
      collection: aszf_documents
      config:
        bucket: "company-legal-docs"
        prefix: "aszf/"
      cron: "0 */6 * * *"          # 6 orankent
```

**Szinkronizacios logika:**
1. Felsorolja a forras fajlokat
2. Osszehasonlitja a `file_hash_sha256`-ot a `documents` tablaval
3. Uj/valtozot fajlokat letolti
4. Triggereli a `document-ingest` workflow-t
5. Regi verziokat `superseded` statuszba allitja

---

## Multi-Skill Megosztas

```yaml
# Skill A letrehozza a collection-t
skills/aszf_rag_chat/skill.yaml:
  vectorstore:
    collections:
      - name: aszf_documents
        shared: true                # Mas skill-ek OLVASHATJAK

# Skill B hasznalja (read-only)
skills/contract_review/skill.yaml:
  vectorstore:
    uses_collections:
      - skill: aszf_rag_chat
        collection: aszf_documents
        access: read
```

**Szabaly:** Minden collection-nak EGYETLEN embedding modell. Ha masik modell kell -> uj collection.

---

## Embedding Modell Migracio

Ha az embedding modellt csereljuk (pl. text-embedding-3-small -> 3-large):

1. Uj collection letrehozasa az uj modell-lel
2. Migracios workflow: re-embed MINDEN chunk-ot (batch, hatterben)
3. Atomikus swap: search config atallitasa az uj collection-re
4. Regi collection megtartasa grace period-ra (rollback lehetoseg)
5. Cleanup: regi collection torlese

---

## Konyvtar Struktura

```
src/aiflow/
    vectorstore/                     # Vector DB absztrakcio
        base.py                      # VectorStore ABC, SearchResult, SearchFilter
        pgvector_store.py            # pgvector implementacio + HNSW + BM25
        embedder.py                  # Embedding generalas (LiteLLM wrapper)
        search.py                    # HybridSearchEngine (vector + BM25 + RRF)
    ingestion/                       # Dokumentum feldolgozas
        pipeline.py                  # IngestionPipeline
        parsers/pdf_parser.py, docx_parser.py, xlsx_parser.py
        chunkers/semantic_chunker.py, fixed_size_chunker.py, hierarchical_chunker.py
        quality.py                   # Chunk minoseg validacio
    documents/                       # Dokumentum eletciklus
        registry.py                  # DocumentRegistry (CRUD + lifecycle)
        versioning.py                # Verziokezeles, supersession
        sync.py                      # Kulso forras sync (SharePoint, S3, GDrive)
        freshness.py                 # Frissesseg kikenyszerites
```

## Docker Valtozas

```yaml
# docker-compose.yml - EGYETLEN valtozas:
postgres:
    image: pgvector/pgvector:pg16    # Volt: postgres:16-alpine
    # Minden mas valtozatlan!
```

## Uj Fuggosegek

```toml
[project.optional-dependencies]
vectorstore = [
    "pgvector>=0.3",           # pgvector Python bindings
    "tiktoken>=0.7",           # Token szamlalas chunk-olashoz
    "pymupdf>=1.24",           # PDF parser
]
```

## Implementacios Sorrend

| Fazis | Het | Tartalom |
|-------|-----|----------|
| A. Foundation | 1-2 | DB tablak, VectorStore ABC, pgvector impl, Embedder |
| B. Document Mgmt | 2-3 | DocumentRegistry, versioning, freshness |
| C. ASZF Skill | 3-5 | Ingestion workflow, Q&A workflow, 150 teszt |
| D. Production | 5-6 | Kulso sync, monitoring view-k, consistency check workflow |
