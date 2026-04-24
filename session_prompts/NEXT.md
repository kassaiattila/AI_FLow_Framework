# AIFlow — Session 143 Prompt (Sprint S S143 — Sprint S kickoff + RagEngineService.query() refactor to ProviderRegistry + rag_collections additive migration)

> **Datum:** 2026-05-15
> **Branch:** `feature/s-s143-rag-query-registry` (cut from `main` @ `ffd7618` = Sprint R S142 squash).
> **HEAD (parent):** Sprint R close (PR #33, tag `v1.5.1`).
> **Port:** API 8102 | UI 5173
> **Elozo session:** S142 — Sprint R close. PromptWorkflow foundation shipped (model + loader + admin UI + executor scaffold + 3 descriptors), flag-off, 0 skill migrations (deferred to S141-FU-1/2/3).
> **Terv:** `01_PLAN/114_CAPABILITY_ROADMAP_Q_R_S.md` §4 Sprint S — Functional vector DB teljes kör.
> **Session tipus:** Sprint kickoff — plan doc + Alembic 046 + query-path ProviderRegistry refactor + integration test a 1024-dim BGE-M3 queryability-re.

---

## 1. MISSION

Zárd le a Sprint J legrégebbi carry-forwardját (FU-1 query-path provider registry). A `RagEngineService.query()` ma hardcoded `self._embedder`-t használ → **1024-dim BGE-M3 kollekciók nem queryable-ek** (csak ingest működik). Sprint S S143 célja:

1. **Alembic 046** — `rag_collections` additív bővítés: `tenant_id TEXT` (default `'default'`) + `embedder_profile_id TEXT NULL`.
2. **`RagEngineService.query()` refactor** — kollekcióra regisztrált `embedder_profile_id` → `ProviderRegistry.get_embedder(profile_id)` → `embed_query`. Backward-compat: ha `embedder_profile_id IS NULL` → fallback a jelenlegi `self._embedder`-re (nulla változás a meglévő 1536-dim kollekciókra).
3. **Integration test real Postgres + real BGE-M3 Profile A** — create 1024-dim collection → ingest 3 chunk → `query()` → top-k visszatér.
4. **Plan doc** `01_PLAN/116_SPRINT_S_FUNCTIONAL_VECTOR_DB_PLAN.md` — Sprint S teljes session-terv (S143 → S146), success metrics, STOP conditions, rollback.

S143 **nem** érinti az admin UI-t (S144) és a nightly MRR mérést (S145). S143 **nem** törli a hardcoded fallback path-t — az marad addig, amíg minden meglévő kollekcióra be nem regisztráltunk egy profilt (migrációs adat, későbbi sprint).

---

## 2. KONTEXTUS

### Sprint J carry-forward ami ma záródik

Sprint J (v1.4.5) bevezette a `ProviderRegistry` 5-slot-os ABC-t: parser, classifier, extractor, **embedder (S100)**, **chunker (S101)**. Az **ingest path** (`RagEngineService.ingest()`) használja a registry-t + `PolicyEngine.pick_embedder()`-t. A **query path** (`RagEngineService.query()`, `service.py:779`) viszont közvetlenül a konstruktorban injektált `self._embedder`-re hív → egyetlen globális embedder-dim van a query oldalon.

Sprint J retro (`docs/sprint_j_retro.md`) explicit carry: *"query() refactor to provider registry (1024-dim collections not queryable yet — Sprint K S105)"* — eddig egyik sprint sem vette fel, mert az intent + extraction + cost guardrail + vault + budget + PromptWorkflow mind prioritásosabbak voltak. Most nyitva van az ablak.

### Miért additív migráció

`rag_collections` tábla létezik (013 alap + 018 F3 bővítés + 042 `embedding_dim`). A 046 két nullable oszlopot ad (`tenant_id` server default `'default'`, `embedder_profile_id` NULL). Unique constraint **nem változik** — `(tenant_id, name)` unique-ot S144 (admin UI) fogja felvenni, amikor tényleges multi-tenant kollekció-lista készül. S143 pusztán a **query-path unblock**.

### Per-skill code változás

`aszf_rag_chat` skill `workflows/query.py`-je változatlanul hívja a `RagEngineService.query()`-t. Ha a skill által használt kollekcióhoz nincs `embedder_profile_id` regisztrálva → fallback a régi viselkedésre → Sprint J UC2 MRR@5 gate (≥ 0.55) **nem regresszál**.

---

## 3. ELOFELTETELEK

```bash
git checkout -b feature/s-s143-rag-query-registry ffd7618
git branch --show-current                       # feature/s-s143-rag-query-registry
git log --oneline -3                            # ffd7618 Sprint R S142 tip
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov 2>&1 | tail -1   # 2347 pass baseline
docker compose ps                               # postgres + redis healthy (5433 / 6379)
alembic current                                 # head: 045 (tenant_budgets)
```

Stop, ha:
- Az unit baseline ≠ 2347 — először záródjon le a másik branch.
- `alembic current` ≠ 045 — más migráció van queue-ban.

---

## 4. FELADATOK

### LEPES 1 — Plan doc

Írd meg `01_PLAN/116_SPRINT_S_FUNCTIONAL_VECTOR_DB_PLAN.md`-t az előzményt követve (115 Sprint Q mintájára). Tartalma:

- **Scope**: Sprint S = UC2 RAG záró sprint. 4 session (S143 query-registry + 046, S144 admin UI `/rag/collections` + per-tenant lista, S145 nightly MRR@5 scheduled job + dashboard, S146 close + tag `v1.5.2`).
- **Success metrics**:
  - 1024-dim BGE-M3 Profile A kollekció end-to-end queryable (integration test).
  - MRR@5 Profile A ≥ 0.55 **változatlan** (Sprint J retrieval baseline).
  - MRR@5 Profile B (Azure OpenAI, ha credit elérhető) ≥ 0.55 (mérés, nem gate).
  - 0 UC2 golden-path regresszió (`aszf_rag_chat` workflow zöld).
  - +3 integration teszt (query-path registry / 1024-dim queryable / fallback viselkedés).
  - +8..12 unit teszt (query-registry dispatch + NULL fallback + unknown profile error).
- **STOP conditions** (HARD): UC2 MRR@5 regresszió < 0.55 → halt és rollback. ProviderRegistry embedder slot instabilitás → halt.
- **Rollback**: 046 additív — `alembic downgrade -1` elég; `query()` refactor flag-nélküli, de NULL fallback garantálja a visszafelé kompatibilitást → revert egyetlen commit.

### LEPES 2 — Alembic 046

`alembic/versions/046_rag_collections_tenant_embedder_profile.py`:

- `op.add_column("rag_collections", sa.Column("tenant_id", sa.Text(), nullable=False, server_default=sa.text("'default'")))`
- `op.add_column("rag_collections", sa.Column("embedder_profile_id", sa.Text(), nullable=True))`
- `op.create_index("ix_rag_collections_tenant_id", "rag_collections", ["tenant_id"])`
- Downgrade: drop index + 2 column.

Futtatás: `alembic upgrade head` → 046. Rollback-ellenőrzés: `alembic downgrade -1` → vissza 045-re → `alembic upgrade head` → újra 046. 2 integration teszt `tests/integration/alembic/test_046_rag_collections.py`: (a) fresh upgrade + columns present, (b) downgrade + columns absent.

### LEPES 3 — Query-path ProviderRegistry refactor

`src/aiflow/services/rag_engine/service.py`:

1. A `Collection` model + `get_collection()` read-path vegye fel az `embedder_profile_id`-t és a `tenant_id`-t.
2. A `query()` elején:
   ```python
   embedder = await self._resolve_query_embedder(coll)
   ```
   ahol `_resolve_query_embedder`:
   - Ha `coll.embedder_profile_id` NULL → `return self._embedder` (backward-compat).
   - Ha nem NULL → `ProviderRegistry.get_embedder(coll.embedder_profile_id)` (a Sprint J S100-ban bevezetett pattern). Ha a profil nem regisztrált → `UnknownEmbedderProfile` (új `AIFlowError` subclass, `is_transient=False`) → `QueryResult` hibaüzenettel (nem dobás, a meglévő try/except mintára).
3. A `_search_engine.search()` hívásnál továbbra is `embedding_dim`-scoped query megy (042 óta), úgyhogy a több-dim coexistence már megvan — csak az embedder dispatch hiányzik.
4. **Ne töröld** a `self._embedder`-t a konstruktorból — az a fallback.

Unit tesztek `tests/unit/services/rag_engine/test_query_embedder_resolver.py` (~8-12 db):
- NULL profile → `self._embedder`.
- Regisztrált profile → registry-ből jön vissza a helyes példány.
- Unknown profile → `UnknownEmbedderProfile` → `QueryResult.answer` tartalmazza a hibát, response_time_ms kitöltve.
- Mock `ProviderRegistry`, ne hívjon valós LLM-et.

### LEPES 4 — Integration test (valós Postgres + valós BGE-M3)

`tests/integration/services/rag_engine/test_query_1024_dim.py` (1 db, `@pytest.mark.integration`):

1. Fresh `rag_collections` row `embedder_profile_id='bge-m3-profile-a'`, `embedding_dim=1024`.
2. Ingest 3 kézi chunk (sync függvény, ne a teljes doc pipeline — kellő a pgvector INSERT).
3. `service.query(collection_id=..., question="...")` → `len(result.sources) > 0`.
4. Cleanup fixture-ben.

**SOHA ne mockolj embedder-t itt** — ez a Sprint S **funkcionális bizonyítéka**. Real PG (5433), real BGE-M3 weight (hf_cache-ben Sprint J S103 után elérhető), real pgvector hybrid search. Ha BGE-M3 weight nincs local cache-ben → `pytest.skip` üzenettel, hogy CI-ben futtasd akkor, amikor a weight preload lépés (Sprint J FU — BGE-M3 weight cache as CI artifact) landol.

### LEPES 5 — Regression + commit + PR

```bash
/regression                             # unit: 2347 → 2355-2360 (kb +8-12); integration: +3
/lint-check                             # ruff + ruff format + tsc clean
```

Commit message:
```
feat(sprint-s): S143 — RagEngineService.query() ProviderRegistry refactor + Alembic 046 rag_collections tenant/embedder_profile

- Alembic 046: rag_collections.tenant_id (default 'default') + embedder_profile_id (nullable)
- RagEngineService.query() resolves embedder via ProviderRegistry when embedder_profile_id set, falls back to self._embedder otherwise
- Integration test: 1024-dim BGE-M3 Profile A collection is now queryable end-to-end (Sprint J FU-1 closed)
- 0 UC2 golden-path regression, 0 breaking changes to existing 1536-dim collections
```

PR cut:
```bash
gh pr create \
  --title "Sprint S S143: RagEngineService.query() ProviderRegistry refactor + Alembic 046 (flag-free, backward-compat)" \
  --body-file docs/sprint_s_s143_pr_description.md \
  --base main
```

### LEPES 6 — Frissítsd a CLAUDE.md banner-t

- Banner: `v1.5.1 Sprint R CLOSE 2026-05-14` → add hozzá `+ Sprint S S143 IN-PROGRESS 2026-05-15` (vagy session-close-ban egy sprintkezdő bekezdés).
- Alembic head: `045 → 046`.
- Unit tests: `2347 → <új szám>`.
- Integration tests: `~103 → ~106` (+3).

---

## 5. STOP FELTETELEK

**HARD:**
1. UC2 MRR@5 Profile A < 0.55 a live `aszf_rag_chat` smoke-on → halt + rollback commit.
2. `alembic upgrade head` vagy `downgrade -1` failel 046-on → halt.
3. Sprint K UC3 golden-path 4/4 regresszió (BGE-M3 share-elés miatt) → halt.
4. `gh pr create` credentials hiány → halt + felhasználói beavatkozás.

**SOFT:**
- BGE-M3 weight nincs local cache-ben → integration test `skip`, dokumentálni a PR description-ben, hogy CI-ben (weight preload lépéssel) kell lefuttatni.
- Profile B (Azure OpenAI) credit hiány → csak Profile A mérünk, nem gate.

---

## 6. SESSION VEGEN

```
/session-close S143
```

A `/session-close` generál `docs/sprint_s_s143_pr_description.md`-t, frissíti a CLAUDE.md számokat, bumpolja az Alembic head-et a key numbers tábláján, és generálja a következő `NEXT.md`-t (S144 — admin UI `/rag/collections` + per-tenant collection list, `ui-journey → ui-api-endpoint → ui-design → ui-page` gate-ekkel).
