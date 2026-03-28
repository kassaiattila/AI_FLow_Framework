# Áttekintés és Navigáció

## Mi Ez Az Anyag?

Ez a gyűjtemény a **Cubix EDU LLM és RAG kurzus** teljes anyagát dolgozza fel **témánkénti, praktikus útmutatók** formájában. A 48 videó-transzkript tartalma **7 tematikus útmutatóba** és **7 futtatható kód példafájlba** lett konszolidálva.

Az anyag a kurzus 6 fejezetét követi, az LLM alapoktól a production monitoring-ig.

---

## LLM/RAG Projekt Workflow

Egy tipikus LLM/RAG alkalmazás fejlesztése az alábbi lépéseket követi:

```
1. LLM MEGÉRTÉS                   → 01_llm_mukodes_es_prompt_engineering
   ├── Transformer, tokenizálás, kontextusablak
   ├── Prompt engineering (zero-shot, few-shot, CoT)
   ├── Agent-szerű működés
   ├── System prompt tervezés
   └── MCP (Model Context Protocol)

2. RAG PIPELINE ÉPÍTÉS             → 02_rag_pipeline_es_dokumentum_feldolgozas
   ├── Dokumentum betöltés és előfeldolgozás
   ├── Chunkolási stratégiák
   ├── Metaadat gazdagítás
   └── Retrieval pipeline

3. EMBEDDING ÉS VEKTOR DB          → 03_embedding_es_vektoradatbazisok
   ├── Embedding modell választás
   ├── Vektoradatbázis (Chroma, FAISS, Weaviate)
   ├── Feltöltés és keresés
   └── Hibrid keresés (dense + sparse)

4. BACKEND INTEGRÁCIÓ               → 04_backend_architektura_es_integracio
   ├── API endpoint tervezés
   ├── Request pipeline
   ├── Next.js + Vercel AI SDK
   ├── Tool/Function calling
   └── Session management

5. EVALUÁCIÓ ÉS TESZTELÉS          → 05_evaluacio_es_teszteles
   ├── RAG szintű mérés
   ├── LLM-as-Judge
   ├── A/B tesztelés
   └── Golden dataset

6. ESZKÖZÖK ÉS CI/CD               → 06_eszkozok_es_cicd
   ├── Promptfoo (prompt validálás)
   ├── Braintrust (feedback pipeline)
   ├── Arize Phoenix (tracing)
   └── GitHub Actions integráció

7. MONITORING ÉS PRODUCTION        → 07_monitoring_es_production
   ├── Latency, success rate, error monitoring
   ├── Dashboards (Streamlit, Grafana)
   ├── Felhasználói visszajelzések
   └── Fine-tuning triggerelés
```

---

## Útmutatók Áttekintése

| # | Útmutató | Tartalom | Sorok | Kód példa |
|---|----------|----------|-------|-----------|
| 01 | [LLM Működés és Prompt Engineering](01_llm_mukodes_es_prompt_engineering.md) | Transformer, tokenizálás, prompt patterns, agents, MCP, system prompt | 725 | [llm_es_prompt_engineering.py](_kod_peldak/llm_es_prompt_engineering.py) |
| 02 | [RAG Pipeline és Dokumentum Feldolgozás](02_rag_pipeline_es_dokumentum_feldolgozas.md) | RAG architektúra, chunkolás, metaadatok, retrieval | 568 | [rag_pipeline.py](_kod_peldak/rag_pipeline.py) |
| 03 | [Embedding és Vektoradatbázisok](03_embedding_es_vektoradatbazisok.md) | Embedding modellek, Chroma, FAISS, Weaviate, semantic search | 802 | [embedding_es_vektordb.py](_kod_peldak/embedding_es_vektordb.py) |
| 04 | [Backend Architektúra és Integráció](04_backend_architektura_es_integracio.md) | API design, Next.js, streaming, tool calling, session mgmt | 811 | [backend_es_api.py](_kod_peldak/backend_es_api.py) |
| 05 | [Evaluáció és Tesztelés](05_evaluacio_es_teszteles.md) | RAG metrics, LLM-as-Judge, A/B testing, golden dataset | 823 | [evaluacio_es_teszteles.py](_kod_peldak/evaluacio_es_teszteles.py) |
| 06 | [Eszközök és CI/CD](06_eszkozok_es_cicd.md) | Promptfoo, Braintrust, Arize Phoenix, GitHub Actions | 681 | [eszkozok_es_cicd.py](_kod_peldak/eszkozok_es_cicd.py) |
| 07 | [Monitoring és Production](07_monitoring_es_production.md) | Logging, dashboards, feedback loop, fine-tuning trigger | 653 | [monitoring_es_production.py](_kod_peldak/monitoring_es_production.py) |

**Összesen**: ~5,063 sor útmutató + 7 futtatható Python fájl (~4,062 sor kód)

---

## Mikor Melyik Útmutatót Használd?

### Feladat szerint

| Kérdés | Útmutató |
|--------|----------|
| "Mi az az LLM és hogyan működik?" | [01 - LLM Alapok](01_llm_mukodes_es_prompt_engineering.md) |
| "Hogyan írjak jó promptot?" | [01 - Prompt Engineering](01_llm_mukodes_es_prompt_engineering.md) |
| "Mi az a RAG és mire jó?" | [02 - RAG Pipeline](02_rag_pipeline_es_dokumentum_feldolgozas.md) |
| "Hogyan dolgozzam fel a dokumentumokat?" | [02 - Chunkolás](02_rag_pipeline_es_dokumentum_feldolgozas.md) |
| "Melyik embedding modellt válasszam?" | [03 - Embedding](03_embedding_es_vektoradatbazisok.md) |
| "Melyik vektoradatbázist használjam?" | [03 - Vektor DB](03_embedding_es_vektoradatbazisok.md) |
| "Hogyan építsek API-t az LLM köré?" | [04 - Backend](04_backend_architektura_es_integracio.md) |
| "Hogyan mérjem a RAG rendszer minőségét?" | [05 - Evaluáció](05_evaluacio_es_teszteles.md) |
| "Hogyan teszteljem a promptjaimat?" | [06 - Promptfoo](06_eszkozok_es_cicd.md) |
| "Hogyan monitorozzam production-ben?" | [07 - Monitoring](07_monitoring_es_production.md) |
| "Mikor kell fine-tuning?" | [07 - Fine-tuning](07_monitoring_es_production.md) |

### Fejlesztési fázis szerint

| Fázis | Elsődleges útmutató | Kiegészítő |
|-------|---------------------|------------|
| **Prototípus** | [01](01_llm_mukodes_es_prompt_engineering.md) + [02](02_rag_pipeline_es_dokumentum_feldolgozas.md) | [03](03_embedding_es_vektoradatbazisok.md) |
| **MVP** | [03](03_embedding_es_vektoradatbazisok.md) + [04](04_backend_architektura_es_integracio.md) | [05](05_evaluacio_es_teszteles.md) |
| **Production** | [05](05_evaluacio_es_teszteles.md) + [06](06_eszkozok_es_cicd.md) | [07](07_monitoring_es_production.md) |
| **Üzemeltetés** | [07](07_monitoring_es_production.md) | [06](06_eszkozok_es_cicd.md) |

---

## Kód Példák Használata

A `_kod_peldak/` mappában 7 futtatható Python fájl található:

```bash
python _kod_peldak/llm_es_prompt_engineering.py
python _kod_peldak/rag_pipeline.py
python _kod_peldak/embedding_es_vektordb.py
python _kod_peldak/backend_es_api.py
python _kod_peldak/evaluacio_es_teszteles.py
python _kod_peldak/eszkozok_es_cicd.py
python _kod_peldak/monitoring_es_production.py
```

**Szükséges csomagok**:
```bash
pip install numpy
# Opcionális (LLM API):
pip install openai tiktoken
# Opcionális (vektor DB):
pip install chromadb faiss-cpu
# Opcionális (backend):
pip install flask
# Opcionális (RAG framework):
pip install langchain
```

---

## Gyors Technológia-Választó

```
Mit építesz?
│
├── RAG chatbot? → [02] + [03] + [04]
│   ├── Kis tudásbázis (<1000 dok)? → Chroma
│   ├── Nagy tudásbázis, sebesség kell? → FAISS
│   └── Managed megoldás? → Weaviate / Qdrant
│
├── Prompt-alapú alkalmazás (RAG nélkül)? → [01]
│   ├── Egyszerű Q&A? → Zero-shot / Few-shot
│   ├── Komplex logika? → Chain-of-Thought / Agent
│   └── Biztonsági követelmények? → System prompt + Policy
│
├── Evaluációs rendszer? → [05] + [06]
│   ├── Offline értékelés? → Golden dataset + LLM-as-Judge
│   ├── Online értékelés? → Braintrust
│   └── A/B teszt? → Promptfoo + statisztika
│
└── Production monitoring? → [07]
    ├── Metrikák? → Latency, success rate, cost
    ├── Dashboard? → Streamlit / Grafana
    └── Feedback loop? → Data flywheel
```

---

## Forrás-Hozzárendelés

| Eredeti transzkript | Útmutató |
|---------------------|----------|
| `01_01` (Kick-off LIVE) | [01](01_llm_mukodes_es_prompt_engineering.md) - Q&A |
| `01_02` - `01_04` (LLM működés) | [01](01_llm_mukodes_es_prompt_engineering.md) |
| `01_05` - `01_08` (Prompt eng., Agent, System prompt, AI policy) | [01](01_llm_mukodes_es_prompt_engineering.md) |
| `01_09` - `01_10` (Promptfoo, MCP) | [01](01_llm_mukodes_es_prompt_engineering.md) |
| `01_14` (LIVE) | [01](01_llm_mukodes_es_prompt_engineering.md) - Q&A |
| `02_01` - `02_02` (RAG, chunkolás) | [02](02_rag_pipeline_es_dokumentum_feldolgozas.md) |
| `02_03` - `02_06` (Embedding, vektor DB) | [03](03_embedding_es_vektoradatbazisok.md) |
| `02_10` (LIVE) | [02](02_rag_pipeline_es_dokumentum_feldolgozas.md) + [03](03_embedding_es_vektoradatbazisok.md) - Q&A |
| `03_01` - `03_07` (Backend, Next.js, UX, tools) | [04](04_backend_architektura_es_integracio.md) |
| `03_11` (LIVE) | [04](04_backend_architektura_es_integracio.md) - Q&A |
| `04_01` - `04_09` (Evaluáció, LLM-as-Judge, A/B) | [05](05_evaluacio_es_teszteles.md) |
| `04_12` (LIVE) | [05](05_evaluacio_es_teszteles.md) - Q&A |
| `05_01` - `05_05` (Promptfoo, Braintrust, CI/CD) | [06](06_eszkozok_es_cicd.md) |
| `05_08` (LIVE) | [06](06_eszkozok_es_cicd.md) - Q&A |
| `06_01` - `06_05` (Monitoring, dashboards, fine-tuning) | [07](07_monitoring_es_production.md) |
| `06_07` (LIVE) | [07](07_monitoring_es_production.md) - Q&A |

---

## További Források

Lásd: [_forrasok/hasznos_linkek.md](_forrasok/hasznos_linkek.md) - LLM API-k, RAG keretrendszerek, vektor DB-k, evaluációs eszközök, monitoring megoldások linkgyűjteménye.
