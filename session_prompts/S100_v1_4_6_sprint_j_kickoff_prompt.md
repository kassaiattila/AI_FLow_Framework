# AIFlow v1.4.6 Sprint J — Session 100 Prompt (UC2 RAG kickoff: EmbedderProvider + EmbeddingDecision)

> **Datum:** 2026-04-22 (tervezett start)
> **Branch:** `feature/v1.4.5-hardening` már ki van cutoolva S99 végén, de ez Sprint J munka — első dolgod: `git switch -c feature/v1.4.6-rag-chat` `main`-ről (lásd LÉPÉS 0). A `feature/v1.4.5-hardening` branch üres marad; töröld, ha Sprint J tisztán elindul.
> **HEAD prereq:** `ae2e7d1` — `v1.4.5 — UC1 document processing (Sprint I, S94–S98) (#13)` merge commit `main`-en. Tag `v1.4.5-uc1` megvan.
> **Port:** API 8102 | Frontend Vite :5174
> **Plan:** `01_PLAN/110_USE_CASE_FIRST_REPLAN.md` §4 Sprint J + §6 UC2 blockers table (S99-jelölésű sor a replanben = ez a session scope-ja, sequential ID szerint S100).
> **Session tipus:** KICKOFF — új sprint első session. Scope: provider abstraction + contract stub + új Alembic migration. Code risk: MEDIUM (provider registry touch). Process risk: LOW.

---

## KONTEXTUS

### Honnan jöttünk

- **S99 ZÁRVA** — webhook_router sequence-hang root-cause + fix (`tests/integration/conftest.py` Langfuse-gate), UC1 Playwright golden-path ÉLŐ stack ellen ZÖLD (`tests/e2e/test_package_detail.py`), PR #13 mergelve `main`-be (`ae2e7d1`), `v1.4.5-uc1` tag megvan.
- CI 6/6 zöld (lint, unit-tests, integration-tests, openapi-drift, Python Lint+Test, Admin Dashboard Build). Az `alembic/env.py` és a két alembic teszt fájl (036, 037) mostantól honor-olja az `AIFLOW_DATABASE__URL`-t — CI-friendly.
- 1949 unit PASS, 410 E2E collect, 49 integration PASS (a korábbi 5 hang megoldva).
- Alembic head: **039** (nem 038 — a replan S99 rubrikában említett "039 embedding_decisions" jelölés drifted, az új migration ebben a session-ben **040** lesz).

### Hova tartunk — Sprint J (v1.4.6) "RAG chat usable"

Use-Case 2 (UC2) célja: működő RAG chat Playwright golden-path E2E-vel, UI-ból bemutatható. A `Parser → Chunker → Embedder` flow közös UC1-gyel; most az **Embedder** réteg provider-abstractionje a blocker. Ezt a session hozza be.

### Jelenlegi állapot (induláskor várt)

```
27 service | 181 endpoint | 50 DB tábla | 39 Alembic migration (head: 039)
1949 unit PASS / 0 FAIL | 410 E2E collected | 49 integration PASS
0 ruff error | 0 ts error | CI 6/6 PASS on main
Branch: feature/v1.4.5-hardening (üres) — Sprint J munka új branch-re
```

---

## ELŐFELTÉTELEK

```bash
# LÉPÉS 0 — branch váltás Sprint J-re (main-ről)
git branch --show-current            # Most: feature/v1.4.5-hardening (S99 close hozta ki)
git switch main                      # main-en HEAD=ae2e7d1 (v1.4.5-uc1 tag)
git pull origin main                 # up-to-date
git switch -c feature/v1.4.6-rag-chat
git branch -D feature/v1.4.5-hardening  # üres volt — törölhető

# Sanity
.venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov      # 1949 PASS
.venv/Scripts/python.exe -m ruff check src/ tests/ --quiet      # exit 0
PYTHONPATH=src .venv/Scripts/python.exe -m alembic current      # 039
docker ps --filter "name=07_ai_flow_framwork" --format "table {{.Names}}\t{{.Status}}"
# db + redis healthy — ha nem: docker compose up -d db redis
```

---

## FELADATOK

### LÉPÉS 1 — `EmbedderProvider` ABC + registry slot

Hely: `src/aiflow/providers/embedder/` (új modul; lásd meglévő `providers/parsers/` mintát S95-ből).

- `base.py`: `EmbedderProvider` ABC — `async embed(texts: list[str]) -> list[list[float]]` + `embedding_dim: int` + `model_name: str` property.
- Registráld a `ProviderRegistry`-be (`src/aiflow/providers/registry.py`) ugyanúgy, ahogy a parser/classifier/extractor.
- Csak az ABC + registry slot ebben a lépésben — impl-t a következő két lépés hoz.

**Exit:** `.venv/Scripts/python.exe -c "from aiflow.providers.embedder import EmbedderProvider; print(EmbedderProvider)"` sikeres.

### LÉPÉS 2 — Provider implek: BGE-M3 (Profile A) + Azure OpenAI (Profile B)

Fájlok:
- `src/aiflow/providers/embedder/bge_m3.py` — local model, FlagEmbedding vagy `sentence_transformers` használatával. Dim: 1024.
- `src/aiflow/providers/embedder/azure_openai.py` — `openai` SDK `AzureOpenAI` kliens, `text-embedding-3-small`. Dim: 1536. Env: `AIFLOW_AZURE_OPENAI__*` (mint a parser Azure DI mintája S96-ban).

**Nem kell** `rag_engine` szolgáltatást átírni — ez külön session (S101 vagy S102). Ebben a session-ben csak a provider létezik + unit teszt.

**Exit:** `tests/unit/providers/embedder/` új könyvtár, minimum 1-1 unit teszt provideronként, ami **valós** embeddinget hív (BGE-M3 local, Azure Openai ha kulcs van — különben `pytest.skip`-pel). SOHA mock embedding!

### LÉPÉS 3 — `EmbeddingDecision` contract stub

Hely: `src/aiflow/contracts/embedding_decision.py` (lásd S94 `ExtractionResult` mintát).

- Pydantic v1 stub (v1.4.6 körben — §10.3 teljes upgrade későbbi sprint).
- Mezők: `provider_name: str`, `model_name: str`, `embedding_dim: int`, `profile: Literal["A","B"]`, `tenant_override_applied: bool`, `decision_at: datetime`, `decision_id: UUID`.
- Export: `src/aiflow/contracts/__init__.py`-be felvenni.

**Exit:** `tests/unit/contracts/test_embedding_decision.py` létezik, happy + invalid paths lefedve.

### LÉPÉS 4 — Alembic 040: `embedding_decisions` tábla

Parancs:
```bash
PYTHONPATH=src .venv/Scripts/python.exe -m alembic revision -m "embedding_decisions"
# → alembic/versions/040_*.py új fájl
```

Séma (additive, `nullable=True` új oszlopoknál):
```sql
CREATE TABLE embedding_decisions (
    decision_id UUID PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    provider_name TEXT NOT NULL,
    model_name TEXT NOT NULL,
    embedding_dim INTEGER NOT NULL,
    profile CHAR(1) NOT NULL CHECK (profile IN ('A','B')),
    tenant_override_applied BOOLEAN NOT NULL DEFAULT FALSE,
    decision_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX ix_embedding_decisions_tenant ON embedding_decisions (tenant_id, decision_at DESC);
```

Run + verify:
```bash
PYTHONPATH=src .venv/Scripts/python.exe -m alembic upgrade head      # → 040
PYTHONPATH=src .venv/Scripts/python.exe -m alembic downgrade -1      # → 039 (downgrade test)
PYTHONPATH=src .venv/Scripts/python.exe -m alembic upgrade head      # → 040 újra
```

`tests/integration/alembic/test_040_embedding_decisions.py` — 2 teszt: (a) upgrade head után tábla + index létezik, (b) downgrade tisztán visszaáll. A `_resolve_db_url()` helpert használd (S99 minta — `test_036`-ból).

### LÉPÉS 5 — PolicyEngine integráció

Hely: `src/aiflow/core/policy_engine.py` (meglévő).

- Új method: `pick_embedder(tenant_id: str, profile: Literal["A","B"]) -> type[EmbedderProvider]`.
- Szabály: Profile A → BGE-M3, Profile B → Azure OpenAI. Tenant override: ha `skill_instance.policy_override.embedder_provider` set, azt használd.
- Logolj `structlog`-gal: `policy_engine.embedder_selected provider=... profile=... tenant_override=...`.

**Exit:** `tests/unit/core/test_policy_engine_embedder.py` — 3 teszt: Profile A default, Profile B default, tenant override.

### LÉPÉS 6 — Regression + session-close

```bash
.venv/Scripts/python.exe -m ruff check src/ tests/ --quiet
.venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov                                   # cél: 1949 + ~10 új teszt
.venv/Scripts/python.exe -m pytest tests/integration/ --no-cov                               # cél: 49+2 PASS
cd aiflow-admin && npx tsc --noEmit && cd ..                                                 # 0 hiba
PYTHONPATH=src .venv/Scripts/python.exe scripts/export_openapi.py                            # OpenAPI drift gate
.venv/Scripts/python.exe -m pytest tests/unit/providers/embedder/ --no-cov -v                # spot check

/session-close S100
```

---

## STOP FELTÉTELEK

- **HARD:** BGE-M3 model letöltés >500MB és nincs lokális cache → kérdezz (Profile A bootstrap lesz issue).
- **HARD:** Azure OpenAI kulcs nincs `.env`-ben — a provider teszt `pytest.skip`-pel ugorjon, NE commitolj placeholder kulcsot.
- **HARD:** Új Alembic downgrade NEM tiszta (FK maradék, sequence drift) → ne erőltesd, inkább `op.execute("DROP ... CASCADE")` explicit + indítsd újra a DB-t.
- **HARD:** `EmbedderProvider.embed()` szignatúra változna `rag_engine` szolgáltatás átírása közben → külön session (S101), ez a session CSAK bevezet, NEM cserél.
- **SOFT:** Ha a 040 migration tesztelése elviszi a session 60%-át, a PolicyEngine integrációt (LÉPÉS 5) csuszd S101-re és zárd S100-at az első 4 lépéssel.

---

## SESSION VÉGÉN

```
/session-close S100
```

Utána `/clear` és S101 (UnstructuredChunker RAG ingest step) — lásd `01_PLAN/110_USE_CASE_FIRST_REPLAN.md` §4 Sprint J second row.
