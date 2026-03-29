# RAG Production Pipeline - Ugyfelenkenti Reprodukalhato Architektura

**Datum:** 2026-03-29
**Alapja:** Valos RAG teszt eredmenyek + Cubix RAG referencia tananyag + felulvizsgalat

---

## Jelenlegi problemak

### 1. Alembic - JAVITVA 2026-03-29
- ~~12 migracio letezik de soha nem futott~~ -> MIND LEFUTOTT (001-012)
- 005 javitva (duplicate column), 011 javitva (column name)
- 25 tabla + 3 view + rag_chunks (utobbit meg Alembic-be kell tenni!)
- **SZABALY: Soha tobbe ne hozzunk letre tablat Alembic nelkul!**

### 2. Referencia tananyag nem alkalmazott
- A Cubix RAG kurzus 7 modulja bemasoltuk a skill/reference-be
- De a pipeline nem koveti a tananyag ajanlasait
- Hianyzo: recursive chunking, heading-based split, evaluation, golden dataset

### 3. Egyetlen flat pipeline
- Nincs ugyfal/collection izolacio
- Nincs konfiguralhato chunking/embedding/search strategia
- Nincs reprodukalhato pipeline (ujrafuttathato uj dokumentumokkal)

---

## Cel architektura

### Collection-alapu izolacio
```
PostgreSQL (aiflow_dev)
  |
  rag_chunks tabla:
    collection='azhu-aszf-2024'    -> AZHU ASZF dokumentumok
    collection='azhu-hr-policy'    -> AZHU HR szabalyzatok
    collection='npra-faq-2024'     -> NPRA FAQ
    collection='bestix-internal'   -> BESTIX belso
```

Minden collection sajat:
- Chunking strategia (chunk_size, overlap, separators)
- Embedding model
- Search konfig (vector_weight, keyword_weight, top_k)
- System prompt template (role-based)
- Evaluation golden dataset

### Instance config integralas
```yaml
# deployments/azhu/instances/azhu-aszf-rag.yaml
data_sources:
  collections:
    - name: azhu-aszf-2024
      priority: 1
      chunking:
        strategy: recursive      # A Cubix tananyag altal ajanlott
        chunk_size: 2500         # Allianz pilot meret
        overlap: 300
        separators: ["\n## ", "\n### ", "\n\n", "\n", ". "]
      embedding:
        model: text-embedding-3-small
        batch_size: 5            # Magyar szoveg: konzervativan
```

---

## Implementacios fazisok

### F0: Alembic integracio - KESZ 2026-03-29
1. [KESZ] 005 javitva (duplicate team_id/user_id)
2. [KESZ] 011 javitva (finished_at -> completed_at)
3. [KESZ] 001-012 mind lefutott, 25 tabla + 3 view
4. [TODO] 013_add_rag_infrastructure.py Alembic-be (rag_chunks, rag_collections, rag_query_log)

### F1: OpenAI-kompatibilis API + OpenChat UI (1-2 nap)

**Cel:** POST /v1/chat/completions endpoint - barmely chat UI hasznalhato.

```
POST /v1/chat/completions
{
  "model": "aszf-rag:azhu-test:expert",
  "messages": [{"role": "user", "content": "Milyen adatokat kezel?"}],
  "stream": true
}
```

**Fajlok:**
1. `src/aiflow/api/v1/chat_completions.py` - OpenAI-format endpoint
2. `docker-compose.yml` - OpenChat UI service hozzaadasa
3. Reflex UI -> admin feluletre atalakitas

### F1b: Alembic integracio (a RAG tervbol - mar KESZ, lasd F0 felett)
1. `alembic/versions/013_add_rag_chunks.py` - Migracio a rag_chunks tablahoz
2. `alembic upgrade head` futtatas a Docker PG-n
3. Meglevo kozvetlenul letrehozott tabla torleseTES ujraltrehozas alembic-kel

### F2: Chunking strategia a tananyag alapjan (1 nap)
A referencia tananyag (02_rag_pipeline) 4 strategiat ir le:
1. **Fixed-size** - egyszeru, de kontextust veszt
2. **Recursive** (AJANLOTT) - hierarchikus spliteles: paragraph -> sentence -> word
3. **Heading-based** - Markdown fejlecek menten
4. **Semantic** - embedding alapu (draga, lassu)

Implementacio:
- `src/aiflow/ingestion/chunkers/` - boviteni a recursive es heading-based strategiakkal
- A `skill_config.yaml`-ban konfiguralhato melyiket hasznalja
- Default: recursive (a legjobb kompromisszum)

### F3: Evaluation framework (2-3 nap)
A referencia tananyag (05_evaluacio) altal ajanlott:
1. **Golden dataset** - 50+ kerdes/valasz par per collection
2. **LLM-as-Judge** - automatikus minoseg ertekeles
3. **Metrikak**: retrieval precision, answer relevance, hallucination rate
4. **Promptfoo integracio** - CI/CD-be beepitheto

### F4: Ugyfal-specifikus pipeline konfiguracio (1-2 nap)
- Instance config -> collection config -> chunking/embedding/search parameterek
- CLI: `python -m skills.aszf_rag_chat ingest --config deployments/azhu/instances/azhu-aszf-rag.yaml`
- Automatikus collection izolacio

---

## Cubix RAG tananyag checklist

### Modul 01: LLM alapok ✅ (hasznaljuk a ModelClient-et)
### Modul 02: RAG Pipeline ✅ (recursive chunking mukodik)
- [x] Dokumentum betoltes (docling)
- [x] Chunking (alap paragraph split)
- [x] Recursive chunking (tananyag ajanlasa!) - KESZ 2026-03-29
- [ ] Heading-based chunking (jovobeli)
- [x] Metadata enrichment (collection, skill_name)
- [ ] Metadata: fejezet, oldal, datum

### Modul 03: Embedding + VectorDB ✅ (pgvector mukodik)
- [x] text-embedding-3-small (1536 dim)
- [x] Batch embedding (batch=5)
- [x] pgvector cosine search
- [ ] IVFFlat index optimalizacio (lists parameter)
- [ ] BM25 tsvector integracio (hybrid search)

### Modul 04: Backend + API ✅ (OpenAI-compat API mukodik)
- [x] CLI interface
- [x] Reflex GUI (alap)
- [x] Open WebUI (profi chat) - KESZ 2026-03-29
- [x] API endpoint (FastAPI /v1/chat/completions + /v1/models)
- [ ] Streaming valasz
- [ ] Conversation memory (DB)

### Modul 05: Evaluacio ⚠️ (alapok kesz)
- [x] Golden dataset (14 kerdes/valasz) - KESZ 2026-03-29
- [x] Evaluation runner (eval_runner.py) - KESZ 2026-03-29
- [x] Eredmeny: 12/14 PASS (86%)
- [ ] LLM-as-Judge scoring (jovobeli)
- [ ] Promptfoo teszt config (jovobeli)
- [ ] Negativ teszt szures javitasa

### Modul 06: Eszkozok + CI/CD ✅ (KESZ 2026-03-29)
- [x] Promptfoo config (7 test, provider script) - KESZ
- [x] Feedback API (POST /v1/feedback) - KESZ
- [ ] Langfuse SSOT (Phase B)
- [ ] GitHub Actions CI/CD (Phase B)

### Modul 07: Monitoring + Production ✅ (alap KESZ 2026-03-29)
- [x] Query log (rag_query_log + log_query step) - KESZ
- [x] Health endpoint (DB/pgvector/Redis check) - KESZ
- [x] Cost tracking (CostTracker kod kesz)
- [ ] Dashboard (Phase B)
- [ ] SLA monitoring (Phase B)
