# AIFlow v1.2.0 — Advanced RAG & Context-as-a-Service

> **Szulo terv:** `48_ORCHESTRABLE_SERVICE_ARCHITECTURE.md` (Tier 3, Phase 7)
> **Cel:** Enterprise-szintu RAG adatelokkeszites: OCR, chunking strategiak, metadata gazdagitas, reranking, VectorOps, prompt management, GraphRAG.

---

## 1. Jelenlegi Allapot vs. Cel

| Kepesseg | Jelenlegi (v1.1.4) | Cel (v1.2.0) |
|----------|-------------------|--------------|
| **Parszolas** | Docling (PDF/DOCX/XLSX) + Azure DI fallback | + Unstructured.io (tablazatok), Tesseract (OCR), parser factory |
| **Chunking** | RecursiveChunker (fix) + SemanticChunker (basic) | + 4 uj strategia: sentence_window, document_aware, parent_child, Chonkie |
| **Metadata** | Nincs auto-extraction | LLM-alapu auto-metadata (datum, szerzo, kategoria, entitasok) |
| **Kereses** | BM25 + HNSW vector + RRF (0.6/0.4) | + Cross-encoder reranking (bge-reranker-v2-m3) |
| **Tisztitas** | Nincs | LLM-alapu zaj eltavolitas (gpt-4o-mini) |
| **VectorOps** | Alapveto CRUD | Index tuning (HNSW params), bulk ops, snapshot, reindex |
| **Prompt Mgmt** | PromptManager (YAML + cache) | + Langfuse A/B testing, canary deployment, version lifecycle |
| **GraphRAG** | Nincs | Microsoft GraphRAG (LazyGraphRAG) — optional |

---

## 2. Technologiai Valasztasok

### 2.1 Parszolas + OCR

| Eszkoz | Hasznalat | Install | Megjegyzes |
|--------|-----------|---------|------------|
| **Docling** (jelenlegi) | Elso valasztas, PDF/DOCX/XLSX | `pip install docling` | IBM, MIT, lokalis, tablazat-felismeres |
| **Unstructured** | Fallback komplex tablazatokra | `pip install "unstructured[pdf,docx]"` | 25+ formatum, de nehez fuggooseg |
| **Tesseract** | OCR kepes fajlokra | `pip install pytesseract` + Tesseract 5.x binary | Magyar (`hun`) nyelvcsomag elerheto |
| **Azure DI** (jelenlegi) | Kezirasos/pecset/belyeg | Mar integralt | Legjobb OCR minoseg |

**Fallback lanc:** Docling → Unstructured → Tesseract → Azure DI

**KIHAGYVA:** LlamaParse — cloud-only, privacy kockazat, draga agentic tier. Nem illik enterprise on-premise-hoz.

**Parser Factory pattern:**
```python
# src/aiflow/services/document_extractor/parsers/parser_factory.py
class ParserFactory:
    """Select parser based on file type + config + quality requirements."""
    
    def get_parser(self, file_path: Path, config: ParserConfig) -> DocumentParser:
        # 1. Check file type
        # 2. Check config.preferred_parser
        # 3. Auto-select: docling → unstructured → tesseract → azure
        # 4. Return parser instance
    
    async def parse_with_fallback(self, file_path: Path, config: ParserConfig) -> ParsedDocument:
        # Try preferred parser, fallback on failure
```

### 2.2 Chunking Strategiak

| Strategia | Konyvtar | Mikor hasznald | Koltseg |
|-----------|----------|----------------|---------|
| **recursive** (jelenlegi) | Sajat `RecursiveChunker` | Altalanos cel, gyors | Ingyenes |
| **semantic** (jelenlegi) | Sajat `SemanticChunker` | Temavaltas-erzekeny | Embedding koltseg |
| **sentence_window** | Sajat implementacio | Pontos kereses + kontextus | Ingyenes |
| **document_aware** | Sajat implementacio | Strukturalt dokumentumok | Ingyenes |
| **parent_child** | Sajat implementacio | Kereses pontossag + kontextus bovites | Ingyenes |
| **token_fast** | Chonkie (`pip install chonkie`) | Gyors feldolgozas nagy volumennel | Ingyenes |

**KIHAGYVA:** LangChain/LlamaIndex text splitters — tulaggosan nehez fuggooseg lamc, a lenyeget 50 sor Python-ban meg tudjuk irni.

**Strategia implementacio:**
```python
# src/aiflow/services/advanced_chunker/strategies/
#   __init__.py
#   base.py          — ChunkingStrategy ABC
#   recursive.py     — meglevo RecursiveChunker adapter
#   semantic.py      — meglevo SemanticChunker adapter
#   sentence_window.py  — UJ: mondat + kornyezo kontextus
#   document_aware.py   — UJ: heading/szekicio alapu
#   parent_child.py     — UJ: nagy parent + kis child
#   strategy_factory.py — config -> strategy valasztas
```

**Sentence Window strategia (reszletek):**
```
Ingest:
  Szoveg → mondatokra bontas → minden mondat = 1 child chunk
  Melleklet: window_before=2, window_after=2 mondat metadata-ban

Query:
  Kereses a child chunk-ok kozott (pontos talalat)
  Valasz generalasnal a window kontextust hasznaljuk (bovebb ertelmezes)
```

**Parent-Child strategia (reszletek):**
```
Ingest:
  Szoveg → parent chunks (2048 token) → child chunks (256 token)
  Minden child hivatkozik a parent-jere (parent_chunk_id)

Query:
  Kereses a child-ok kozott (pontos)
  Ha a top-K child-ok >50%-a ugyanahhoz a parent-hez tartozik → a parent-et adjuk az LLM-nek
```

### 2.3 Reranking

| Modell | Tipus | Latencia | Minoseg | Nyelv |
|--------|-------|----------|---------|-------|
| **BAAI/bge-reranker-v2-m3** | Lokalis (sentence-transformers) | ~10ms/doc (GPU) | Nagyon jo | Multilingvalis (magyar is) |
| **FlashRank multilingual** | Lokalis (ONNX, CPU) | ~2ms/doc | Jo | 100+ nyelv (150MB) |
| **Cohere rerank-v3.5** | Cloud API | ~50ms/batch | Legjobb | 100+ nyelv |

**Ajanlott konfiguracio:**
```yaml
reranking:
  primary: bge-reranker-v2-m3      # Lokalis GPU, legjobb minoseg/koltseg
  fallback: flashrank-multilingual   # CPU fallback ha nincs GPU
  premium: cohere-rerank-v3.5       # Magas ertek lekerdezesekhez (optional)
  top_k_candidates: 20              # Hany eredmenyt rankoljunk ujra
  return_top: 5                     # Hanyat adjunk vissza
```

**Integracio a jelenlegi HybridSearchEngine-be:**
```
Jelenlegi: query → embed → hybrid search (BM25+HNSW+RRF) → top_k → LLM
Uj:        query → embed → hybrid search → top_20 → RERANK → top_5 → LLM
```

A `SearchConfig.rerank` mezo MAR LETEZIK de nincs implementalva — ezt aktivaljuk.

### 2.4 VectorOps

pgvector 0.8.0 uj kepessegek:
- **Iterative index scans** — megoldja a szurt keresek pontossagi problemajat
- **HNSW tuning:** `m=32`, `ef_construction=200`, `ef_search=100` (jelenlegi default: m=16, ef_construction=64)
- **Scalar quantization** (halfvec) — 50% memoria megtakaritas

**VectorOps service metódusok:**
```python
optimize_index(collection_id, config)  # HNSW param tuning
bulk_update(collection_id, updates)    # Re-embed model valtas utan
bulk_delete(collection_id, filter)     # Metadata alapu torles
reindex(collection_id, new_config)     # Teljes ujraindezelés
version_snapshot(collection_id)        # Visszaallithato pillanatkep
collection_stats(collection_id)        # Fragmentacio, stale vektorok, drift
```

### 2.5 Prompt Management Bovites

Langfuse MAR integralt — bovites:
- **A/B testing:** `PromptManager.get(name, label="prod-a")` vs `label="prod-b"` random routing
- **Canary deploy:** 10% forgalom uj prompt variansra, automatikus minoseg monitoring
- **Version lifecycle:** `dev` → `staging` → `production` label flow
- **Metrikkak prompt variansonkent:** latency, cost, quality score, user feedback

### 2.6 GraphRAG (OPTIONAL — Phase 7E)

**Microsoft GraphRAG + LazyGraphRAG:**
- LazyGraphRAG: NEM epiti fel az egesz grafot elore, hanem query-kor on-the-fly
- Koltseg: nehany cent/dokumentum (vs. szazak a teljes GraphRAG-nal)
- Mikor hasznald: multi-hop kerdesek ("melyik szerzodeses feltetel erinti melyik reszleg eljarasat?")

**KIHAGYVA egyelore:** Neo4j — tulzott operational overhead, a Microsoft GraphRAG standalone mukodik.
**Kesobbi opcio:** Ha kell graph lekerdezesekhez, Neo4j hozzaadható a pipeline-hoz.

---

## 3. Szolgaltatas Architektura

### 3.1 Uj szolgaltatasok

| Szolgaltatas | File | Leiras |
|-------------|------|--------|
| **DataCleanerService** | `src/aiflow/services/data_cleaner/service.py` | LLM-alapu dokumentum tisztitas |
| **AdvancedChunkerService** | `src/aiflow/services/advanced_chunker/service.py` | 6 chunking strategia |
| **MetadataEnricherService** | `src/aiflow/services/metadata_enricher/service.py` | Automatikus metadata kinyeres |
| **RerankerService** | `src/aiflow/services/reranker/service.py` | Cross-encoder ujrarangsorolas |
| **VectorOpsService** | `src/aiflow/services/vector_ops/service.py` | Vektor index eletciklus |
| **GraphRAGService** | `src/aiflow/services/graph_rag/service.py` | Tudasgraf (optional) |

### 3.2 Modositando meglevo szolgaltatasok

| Szolgaltatas | Modositas |
|-------------|-----------|
| **DocumentExtractorService** | Parser factory integracio (uj parserek hozzaadasa) |
| **RAGEngineService** | `ingest_chunks()` uj method (mar chunkolt adatot fogad) |
| **HybridSearchEngine** | Reranker integracio (`SearchConfig.rerank` aktivalas) |

### 3.3 Context-as-a-Service Pipeline

A teljes adatelokkeszitesi lanc egyetlen YAML pipeline-kent:

```yaml
name: context_as_a_service
description: "Enterprise RAG data preparation pipeline"
version: "1.0.0"
trigger:
  type: manual
input_schema:
  files: { type: array, required: true }
  collection_id: { type: string, required: true }
  chunking_strategy: { type: string, default: "recursive" }
  enable_metadata: { type: boolean, default: true }
  enable_reranking: { type: boolean, default: true }
  enable_graph: { type: boolean, default: false }

steps:
  - name: parse
    service: document_extractor
    method: parse
    for_each: "{{ input.files }}"
    config:
      parser: auto
      ocr_enabled: true

  - name: clean
    service: data_cleaner
    method: clean_batch
    depends_on: [parse]
    config:
      model: openai/gpt-4o-mini
      fix_ocr_errors: true
      remove_boilerplate: true
      language: hu

  - name: enrich_metadata
    service: metadata_enricher
    method: enrich
    depends_on: [clean]
    condition: "input.enable_metadata == true"
    config:
      model: openai/gpt-4o-mini
      extract_entities: true
      extract_keywords: true
      auto_categorize: true

  - name: chunk
    service: advanced_chunker
    method: chunk
    depends_on: [clean]
    config:
      strategy: "{{ input.chunking_strategy }}"
      chunk_size: 512
      chunk_overlap: 64

  - name: embed_and_store
    service: rag_engine
    method: ingest_chunks
    depends_on: [chunk, enrich_metadata]
    config:
      collection_id: "{{ input.collection_id }}"
      embedding_model: openai/text-embedding-3-small

  - name: build_graph
    service: graph_rag
    method: build_graph
    depends_on: [enrich_metadata]
    condition: "input.enable_graph == true"
    config:
      collection_id: "{{ input.collection_id }}"

  - name: optimize_index
    service: vector_ops
    method: optimize_index
    depends_on: [embed_and_store]
    config:
      collection_id: "{{ input.collection_id }}"
      algorithm: hnsw
      m: 32
      ef_construction: 200
```

---

## 4. Reszletes Interfeszek

### 4.1 DataCleanerService

```python
class CleaningConfig(BaseModel):
    model: str = "openai/gpt-4o-mini"
    remove_headers_footers: bool = True
    fix_ocr_errors: bool = True
    normalize_whitespace: bool = True
    remove_boilerplate: bool = True
    language: str = "hu"
    custom_rules: list[str] = []  # Egyedi Jinja2 prompt szabalyok

class CleanedDocument(BaseModel):
    cleaned_text: str
    original_length: int
    cleaned_length: int
    removed_sections: list[str]
    corrections: list[dict]      # [{"original": "...", "corrected": "...", "type": "ocr"}]
    auto_metadata: dict          # Mellektermek: kinyert alapmetadata
    cost_usd: float
```

**Prompt strategia:** Egyetlen LLM hivas per dokumentum, nem chunk-onkent. A gpt-4o-mini 128K kontextusablaka elegendo a legtobb dokumentumra. Prompt YAML-ben tarolva a `prompts/` mappaban.

### 4.2 AdvancedChunkerService

```python
class ChunkConfig(BaseModel):
    strategy: Literal["fixed", "recursive", "semantic", "sentence_window", "document_aware", "parent_child"]
    chunk_size: int = 512
    chunk_overlap: int = 64
    # Semantic:
    similarity_threshold: float = 0.75
    embedding_model: str = "openai/text-embedding-3-small"
    # Sentence window:
    window_size: int = 3
    # Document-aware:
    heading_patterns: list[str] = ["^#{1,3}\\s", "^\\d+\\.\\s"]
    # Parent-child:
    parent_chunk_size: int = 2048
    child_chunk_size: int = 256

class ChunkResult(BaseModel):
    chunks: list[Chunk]
    strategy_used: str
    total_chunks: int
    avg_chunk_size: int
    parent_chunks: list[Chunk] | None = None  # parent-child strategianal
```

### 4.3 MetadataEnricherService

```python
class EnrichmentConfig(BaseModel):
    model: str = "openai/gpt-4o-mini"
    extract_entities: bool = True
    extract_keywords: bool = True
    extract_dates: bool = True
    auto_categorize: bool = True
    language: str = "hu"

class EnrichedMetadata(BaseModel):
    title: str | None
    author: str | None
    date: datetime | None
    version: str | None
    language: str
    category: str | None         # szerzodes, szamla, jelentes, szabalyzat, ...
    keywords: list[str]
    entities: list[NamedEntity]  # {name, type, confidence}
    summary: str                 # 1-2 mondatos osszefoglalas
    document_type: str | None
    confidence: float
    cost_usd: float
```

### 4.4 RerankerService

```python
class RerankConfig(BaseModel):
    model: str = "bge-reranker-v2-m3"  # vagy "flashrank-multilingual", "cohere-rerank-v3.5"
    top_k: int = 20           # Hany eredmenyt rankoljunk ujra
    return_top: int = 5       # Hanyat adjunk vissza
    score_threshold: float = 0.0
    batch_size: int = 32

class RankedResult(BaseModel):
    original_rank: int
    new_rank: int
    score: float              # Reranker relevancia score
    content: str
    metadata: dict
    chunk_id: str
```

### 4.5 VectorOpsService

```python
class IndexConfig(BaseModel):
    algorithm: Literal["hnsw", "ivfflat"] = "hnsw"
    m: int = 32
    ef_construction: int = 200
    ef_search: int = 100
    lists: int = 100           # IVF-hez
    probes: int = 10           # IVF-hez
    quantization: Literal["none", "halfvec", "binary"] = "none"

class CollectionHealth(BaseModel):
    total_vectors: int
    index_type: str
    index_params: dict
    fragmentation_pct: float
    stale_vectors: int         # Reg, nem frissitett vektorok
    embedding_model: str
    last_optimized: datetime | None
    estimated_search_latency_ms: float
```

---

## 5. Fuggosegek (pyproject.toml)

```toml
[project.optional-dependencies]
rag-advanced = [
    "chonkie>=1.6",           # Gyors chunking
    "FlashRank>=0.2.10",      # CPU reranker
]
rag-ocr = [
    "unstructured[pdf,docx]", # Fallback parser
    "pytesseract",            # OCR
]
rag-graph = [
    "graphrag>=3.0",          # Microsoft GraphRAG
]
rag-premium = [
    "cohere>=5.0",            # Cloud reranker
]
```

**Alapertelmezett:** `sentence-transformers` (mar fuggooseg) + `bge-reranker-v2-m3` (auto-download HuggingFace-rol).

---

## 6. Fejlesztesi Fazisok

| Fazis | Szolgaltatas | Becsult meret | Fuggoseg |
|-------|-------------|---------------|----------|
| **7A** | DataCleanerService | ~200 sor + prompt YAML | Onallo |
| **7B** | AdvancedChunkerService (6 strategia) | ~500 sor + strategy fajlok | Onallo |
| **7C** | MetadataEnricherService | ~250 sor + prompt YAML | Onallo |
| **7D** | RerankerService + HybridSearchEngine integracio | ~300 sor | Onallo |
| **7F** | VectorOpsService | ~200 sor + pgvector 0.8.0 upgrade | Onallo |
| **7G** | Parser Factory + Unstructured + Tesseract | ~300 sor | Onallo |
| **7E** | GraphRAGService (optional) | ~400 sor + graphrag dep | 7C fugg (entitasok) |

Mindegyik FUGGETLEN — barmilyen sorrendben, barmely subset implementalhato.

---

## 7. Verifikacio

### 7.1 Minden szolgaltatasra:
1. Unit teszt: min 5 test case
2. Integracio teszt: valos fajllal, valos LLM hivassal
3. Pipeline teszt: YAML pipeline-ban hasznalva, WorkflowRunner-rel futtatva
4. Teljesitmeny teszt: 100 dokumentummal, koltseg es idomeresssel

### 7.2 End-to-end Context-as-a-Service teszt:
```bash
# 1. Teljes pipeline futtas
curl -X POST /api/v1/pipelines/context_as_a_service/run \
  -d '{"files": ["test.pdf"], "collection_id": "test", "chunking_strategy": "semantic"}'

# 2. Ellenorzes: chunks leteznek, metadata gazdagitott, index optimalizalt
curl /api/v1/rag/collections/test  # chunk_count > 0

# 3. Query + reranking
curl -X POST /api/v1/rag/collections/test/query \
  -d '{"question": "Mi a szerzodes tartalma?", "rerank": true}'
# Eredmeny: pontos, releváns valasz forrasokkal
```
