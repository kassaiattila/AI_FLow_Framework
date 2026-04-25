# AIFlow — Session 144 Prompt (Sprint S S144 — admin UI `/rag/collections` + per-tenant collection list + set-profile mutation)

> **Datum:** 2026-04-25
> **Branch:** `feature/s-s144-rag-collections-admin-ui` (cut from `main` @ `95ec89e` = Sprint S S143 squash, PR #34).
> **HEAD (parent):** S143 squash-merge on `main` (PR #34, 2026-04-25 03:43 UTC).
> **Port:** API 8102 | UI 5173
> **Elozo session:** S143 — `RAGEngineService.query()` ProviderRegistry refactor + Alembic 046 `rag_collections.tenant_id` + `embedder_profile_id`. Sprint J FU-1 zarva (1024-dim BGE-M3 queryable real PG-n + real BGE-M3 weights-szel). 2347 → 2361 unit (+14), 4 uj integration zold, 0 skill kod modositas, NULL-fallback backward-compat — flag-mentes.
> **Terv:** `01_PLAN/116_SPRINT_S_FUNCTIONAL_VECTOR_DB_PLAN.md` §2 S144 + `01_PLAN/114_CAPABILITY_ROADMAP_Q_R_S.md` §4.
> **Session tipus:** UI + API. **7 HARD GATE** kotelezo (`aiflow-ui-pipeline` skill): `ui-journey → ui-api-endpoint → ui-design → ui-page → component reuse check → live-test → CI`.

---

## 1. MISSION

Tedd lathatova az S143-ban bevezetett `tenant_id` + `embedder_profile_id` osztott vector DB modellet az admin UI-ban. A mai `rag_collections` tabla nem queryelheto a UI-bol szervezett listaval, igy egy operator nem latja, hogy melyik kollekcio melyik tenant-hoz tartozik, sem azt, hogy melyik embedder profil-t hasznalja query-koz. S144 ezt megoldja:

1. **3 endpoint** a `/api/v1/rag/collections` router alatt:
   - `GET /api/v1/rag/collections?tenant_id=<x>` — lapozhato lista (tenant-szurt vagy osszes), tartalmazza: `id`, `name`, `tenant_id`, `embedder_profile_id`, `embedding_dim`, `chunk_count`, `document_count`, `updated_at`.
   - `GET /api/v1/rag/collections/{id}` — egyetlen kollekcio reszletes nezete (mint a lista row, plusz `description`, `language`, `embedding_model`, `created_at`, `config`).
   - `PATCH /api/v1/rag/collections/{id}/embedder-profile` — body: `{"embedder_profile_id": "bge_m3" | "azure_openai" | "openai" | null}`. Validalas: ha a kollekcio `chunk_count > 0` ES `embedder_profile_id` valtozasa **dim-mismatch**-et okozna (pl. 1536 → bge_m3 1024) → HTTP 409 `DimensionMismatch` (nincs DB modositas). A jelenlegi `RAGEngineService` nem ad ehhez metodust → vegy hozza `set_embedder_profile()` szervizmetodust.
2. **Admin UI** `/rag/collections` page (`aiflow-admin/src/pages/rag-collections/`):
   - Tabla: oszlopok `Name`, `Tenant`, `Embedder Profile` (badge: `bge_m3` zold, `azure_openai` kek, `openai` szurke, `NULL` = "Default" sarga), `Embedding Dim`, `Chunks`, `Updated`.
   - Per-tenant filter (chip dropdown) + `?tenant=` deep-link (Sprint N S123 budget page mintajara).
   - Detail pane (modal vagy oldal-panel): tartalmazza a "Set embedder profile" select dropdown-ot + `Save` gomb a `PATCH` endpoint-tal. Sikeres save → toast + lista refresh.
   - Empty state: "No collections yet — ingest documents via the RAG Engine API."
   - EN + HU locale (`aiflow-admin/src/locales/{en,hu}/rag-collections.json`).
3. **1 Playwright E2E live-stack-en** (no route mock — Sprint Q S136 / Sprint N S123 mintaja): seedel 2 kollekciot (kulonbozo `tenant_id`-vel + kulonbozo `embedder_profile_id`-vel), a UI lista mindketto sort latja, a tenant filter szuri, a detail "Set profile" actiot tegezi, a backend valtozas megjelenik a listaban hard-reload utan.
4. **+8 unit + +3 router integration teszt**.

S144 **nem** modositja az S143-ban szallitott `RAGEngineService.query()` resolver-t. **Nem ad** uj Alembic migraciot (S143 046 head marad). **Nem migral** mas skill-t a ProviderRegistry profile-ra (az S141-FU-1/2/3 path).

---

## 2. KONTEXTUS

### S143 mit hagyott S144-nek

S143 PR #34 (`95ec89e`) ezeket szallitotta:
- `rag_collections.tenant_id` (NOT NULL, default `'default'`) + `embedder_profile_id` (nullable) oszlop.
- `CollectionInfo.tenant_id` + `embedder_profile_id` Pydantic mezo.
- `list_collections` + `get_collection` SELECT olvas tenant + profile-t.
- `_resolve_query_embedder` adapter NULL-fallback-kel.

**Hianyzik az operator-felulet**: nem lathato sehol a UI-bol, hogy melyik kollekcio mit hasznal query-kor. S144 ezt zarja le.

### Miert csak GET + PATCH (nincs CREATE / DELETE)

- `create_collection` ma a `RAGEngineService.create_collection(name, customer, ...)` szervizmetodus + a `customer` mezo NOT NULL — refactor (SS-FU-5) kulon kerdes. **S144 hatokoren kivul**.
- `delete_collection` szinten szervizmetodus de operator-felulet kockazatos (pgvector chunk drop). **Sprint S vegere ha indokolt, S145+ FU**.
- Admin UI csak az **olvasas + profile-attach** muveletet adja (a fo S144 deliverable: visibility + profile-management). Egyeb CRUD kesobbi sprintbe.

### Carry forward

| ID | Eredet | Itt zarjuk-e |
|---|---|---|
| SS-FU-1 (`create_collection` tenant-aware arg) | S143 PR | **NEM** — kulon refactor, `customer` deprecation szukseges |
| SS-FU-2 (`/rag/collections` admin UI) | S143 PR | **IGEN** — ez S144 fo deliverable |
| SS-FU-3 (nightly MRR@5) | S143 PR | **NEM** — S145 |
| SS-FU-4 (`(tenant_id, name)` unique) | S143 PR | **OPCIONALIS** — ha PATCH endpoint mukodik tenant-multiplicitassal, akkor most landol egy **additiv** Alembic 047. Ha PATCH csak `embedder_profile_id`-t bantja (nev marad), akkor halaszthato. **Default: halasztas S145-re**, `set_embedder_profile()` ne valtozzon nev / tenant. |
| SS-FU-5 (`customer` deprecation) | S143 PR | **NEM** — kulon |
| SS-SKIP-1 (BGE-M3 weight CI preload) | S143 plan §8 | **NEM** — S145 |
| SS-SKIP-2 (Profile B Azure live MRR) | S143 plan §8 | **NEM** — S145 |

---

## 3. ELOFELTETELEK

```bash
git checkout main
git pull --ff-only origin main                     # 95ec89e Sprint S S143 tip
git checkout -b feature/s-s144-rag-collections-admin-ui
git log --oneline -3                                # 95ec89e tip
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov 2>&1 | tail -1   # 2361 baseline
docker compose ps                                   # postgres 5433 + redis 6379 healthy
PYTHONPATH="src;." .venv/Scripts/python.exe -m alembic current   # head: 046
cd aiflow-admin && npx tsc --noEmit && cd ..       # FE TS clean baseline
```

Stop, ha:
- Unit baseline ≠ 2361 — masik branch nyitva.
- Alembic current ≠ 046 — S143 nem alkalmazva.
- `aiflow-admin` TS dirty — meglevo regresszio elobb.

---

## 4. FELADATOK

### LEPES 1 — Service mutation method

`src/aiflow/services/rag_engine/service.py`:

- Add `async def set_embedder_profile(self, collection_id: str, embedder_profile_id: str | None) -> CollectionInfo | None`:
  - Validalas:
    - `coll = await self.get_collection(collection_id)` — None → return None.
    - Ha `embedder_profile_id` not in `{None, "bge_m3", "azure_openai", "openai"}` → raise `UnknownEmbedderProfile` (S143 errorklass reuse).
    - **Dim-mismatch guard**: ha `coll.chunk_count > 0`:
      - NULL → uj profile esete: csak akkor engedj, ha az uj provider `embedding_dim == coll.embedding_dim`. Bejarhato csak instantialassal — wrap try/except, error → raise `DimensionMismatch` (uj `AIFlowError` subclass, `is_transient=False`, HTTP 409).
      - profile → NULL: tilos ha `coll.embedding_dim != 1536` (a legacy `self._embedder` mindig 1536-dim). Ugyanaz a `DimensionMismatch`.
      - profile → masik profile: hasonlo ellenorzes az uj provider dim-jen.
    - Ha `chunk_count == 0` → engedj barmelyiket (ures kollekciora barmilyen profile attach-elhetetlen-mentes). `coll.embedding_dim` is frissuljon az uj provider dim-jere (mintaja: `_update_collection_embedding_dim`).
  - SQL: `UPDATE rag_collections SET embedder_profile_id = :p, updated_at = NOW() WHERE id = :id`.
  - Visszateres: `await self.get_collection(collection_id)` (frissitett snapshot).
- Add `DimensionMismatch(AIFlowError)` `# noqa: N818` mintajara `UnknownEmbedderProfile` mintaval. `error_code = "RAG_DIM_MISMATCH"`, `http_status = 409`.

Unit teszt `tests/unit/services/test_rag_engine_set_embedder_profile.py` (8 db):
- collection_id ismeretlen → None.
- ismeretlen profile → `UnknownEmbedderProfile`.
- chunk_count == 0 + uj profile → `embedding_dim` frissul + visszater a frissitett `CollectionInfo`.
- chunk_count > 0 + dim-equal profile → siker.
- chunk_count > 0 + dim-mismatch (1536 → bge_m3 1024) → `DimensionMismatch`.
- chunk_count > 0 + profile → NULL ahol embedding_dim != 1536 → `DimensionMismatch`.
- chunk_count > 0 + profile → NULL ahol embedding_dim == 1536 → siker.
- profile → masik profile dim-equal → siker.

Mockold a `BGEM3Embedder` / `OpenAIEmbedder` classt monkeypatchel mint S143 unit tesztben (ne tolts BGE-M3 weight-et).

### LEPES 2 — Router

`src/aiflow/api/v1/routers/rag_collections.py`:

```python
router = APIRouter(prefix="/api/v1/rag/collections", tags=["rag-collections"])
```

3 route:
- `GET /` — `tenant_id: Annotated[str | None, Query()] = None` filter, `limit / offset` paging (default 50). Visszateres: `RagCollectionListResponse` Pydantic (`items: list[RagCollectionListItem], total: int`).
- `GET /{collection_id}` — `RagCollectionDetailResponse` Pydantic. 404 ha None.
- `PATCH /{collection_id}/embedder-profile` — body `RagCollectionEmbedderProfileUpdate(embedder_profile_id: str | None)`. Hivja `service.set_embedder_profile(...)`. 404, 409, 200.

Auth: `auth_required` dependency (mas RAG router mintajara).

Mount: `src/aiflow/api/v1/__init__.py` — figyelni, hogy a meglevo `prompts` router mintajara **a catch-all elott** mountolj (S143-ban nem volt prompts-shadow gond, de elovigyazatossagbol).

OpenAPI snapshot regeneralas (Sprint O FU-1 mintajara): `python -m scripts.export_openapi` vagy a meglevo `tests/api/openapi/snapshot.json` regenerator.

Router unit teszt `tests/unit/api/v1/routers/test_rag_collections_router.py` (3 db):
- `GET /` lefedi a tenant filter parametert (mock `service.list_collections`).
- `GET /{id}` 404.
- `PATCH /{id}/embedder-profile` 409 ha `DimensionMismatch` jon.

Router integration teszt `tests/integration/api/v1/test_rag_collections_router.py` (3 db, real PG):
- Seed 2 collection (kulonbozo tenant) → `GET /?tenant_id=t1` csak az egyiket adja vissza.
- `PATCH /{id}/embedder-profile` ures kollekcion → ujra `GET` mutatja az uj profile-t.
- `PATCH /{id}/embedder-profile` chunk_count > 0 + dim-mismatch → 409 + DB nem valtozott.

### LEPES 3 — Admin UI page

7 GATE szerint (`.claude/skills/aiflow-ui-pipeline`):

1. **Journey** — `tests/ui-live/rag-collections.md` user journey doc (operator: lat-tab, szur tenant-re, set-profile, lat refresh).
2. **API endpoint** — fent (LEPES 2).
3. **Design** — Untitled UI table + chip filter + side drawer pattern. `aiflow-admin/src/pages/rag-collections/RagCollectionsPage.tsx` skeleton.
4. **Page** — implement.
5. **Component reuse check** — hasznald a meglevo `Table`, `Badge`, `ChipFilter`, `SideDrawer` komponenseket az `aiflow-admin/src/components-new/` aloli (Sprint Q `ExtractedFieldsCard`, Sprint N `BudgetCard` mintajara).
6. **Live-test** — `/live-test rag-collections` (Playwright MCP, real dev stack).
7. **CI** — Playwright spec `tests/ui/specs/rag_collections.spec.ts` 1 teszttel.

Files:
- `aiflow-admin/src/pages/rag-collections/RagCollectionsPage.tsx`
- `aiflow-admin/src/pages/rag-collections/RagCollectionDetailDrawer.tsx`
- `aiflow-admin/src/pages/rag-collections/types.ts`
- `aiflow-admin/src/locales/en/rag-collections.json`
- `aiflow-admin/src/locales/hu/rag-collections.json`
- `aiflow-admin/src/router/routes.ts` — uj `/rag/collections` + sidebar `aiflow.menu.rag.collections`.
- `aiflow-admin/src/api/ragCollections.ts` — fetch wrapper.

EN locale kulcsok:
- `rag-collections.title` = "RAG Collections"
- `rag-collections.filter.tenant` = "Tenant"
- `rag-collections.column.name` = "Name"
- `rag-collections.column.tenant` = "Tenant"
- `rag-collections.column.embedderProfile` = "Embedder Profile"
- `rag-collections.column.embeddingDim` = "Dim"
- `rag-collections.column.chunks` = "Chunks"
- `rag-collections.column.updated` = "Updated"
- `rag-collections.detail.setProfile` = "Set Embedder Profile"
- `rag-collections.detail.save` = "Save"
- `rag-collections.detail.dimMismatch` = "Cannot change profile: existing chunks use a different dimension."
- `rag-collections.empty` = "No collections yet — ingest documents via the RAG Engine API."

HU locale ekvivalens.

### LEPES 4 — Live-test report

Futtasd a `/live-test rag-collections` skill-t:
1. `make api` futassa az API-t.
2. `cd aiflow-admin && npm run dev` futassa a UI-t.
3. Seed 2 kollekciot direkt SQL-lel:
   ```sql
   INSERT INTO rag_collections (id, name, customer, skill_name, embedder_profile_id, tenant_id, embedding_dim)
   VALUES (gen_random_uuid(), 's144-uc2-hu', 'bestix', 'rag_engine', NULL, 'bestix', 1536),
          (gen_random_uuid(), 's144-bge-m3-test', 'doha', 'rag_engine', 'bge_m3', 'doha', 1024);
   ```
4. Playwright MCP-vel: `/rag/collections` page → assert mindketto latszik → tenant filter `bestix` → csak az egyik → click row → drawer → set profile `openai` ures kollekcion → save → reload → assert `openai` badge.
5. Report `tests/ui-live/rag-collections.md`.

### LEPES 5 — Playwright E2E spec

`tests/ui/specs/rag_collections.spec.ts` (1 teszt, no route mock — Sprint N S123 / Sprint Q S136 mintajara):
- DB seed via API helper vagy direct SQL fixture.
- Playwright navigate + assert + interakt + assert.
- Cleanup teardown.

### LEPES 6 — Regression + commit + PR

```bash
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/ --no-cov -q                  # 2361 → 2369 (+8)
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/integration/api/v1/test_rag_collections_router.py --no-cov -q   # 3 zold
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/api/v1/routers/test_rag_collections_router.py --no-cov -q  # 3 zold
cd aiflow-admin && npx tsc --noEmit && npm run lint && cd ..
.venv/Scripts/python.exe -m ruff check src/ tests/ && .venv/Scripts/python.exe -m ruff format --check src/ tests/
```

Commit:
```
feat(sprint-s): S144 — admin UI /rag/collections + per-tenant list + set-profile mutation

- 3 endpoint (GET list w/ tenant filter, GET detail, PATCH embedder-profile)
- RAGEngineService.set_embedder_profile() w/ dim-mismatch guard (DimensionMismatch HTTP 409)
- Admin UI page + drawer + EN/HU locale + sidebar nav
- 8 unit (set_embedder_profile dim guards) + 3 router unit + 3 router integration (real PG)
- 1 Playwright E2E live-stack (no route mock)
- 0 Alembic, 0 skill code change, NULL-fallback unchanged
```

PR cut:
```bash
gh pr create \
  --title "Sprint S S144: admin UI /rag/collections + per-tenant list + set-profile (flag-free)" \
  --body-file docs/sprint_s_s144_pr_description.md \
  --base main
```

### LEPES 7 — CLAUDE.md numbers update

- API endpoints: `193 → 196` (+3)
- API routers: `30 → 31` (+1)
- Unit tests: `2361 → ~2369` (+8)
- Integration tests: `~107 → ~110` (+3)
- E2E tests: `429 → 430` (+1 Playwright Sprint S S144 rag-collections)
- UI pages: `25 → 26`
- Banner: `Sprint S S143 IN-PROGRESS` → `Sprint S S144 IN-PROGRESS` (vagy bovites `S143 + S144`).

---

## 5. STOP FELTETELEK

**HARD:**
1. UC2 `aszf_rag_chat` golden-path regresszio (NULL-fallback path elromlik) → halt + revert.
2. `rag_collections` row INSERT vagy SELECT regresszio S143 utan (defensive row-length checks regresszionak elnezni keptelennek) → halt.
3. `gh pr create` credentials hiany autonomous loop-ban → halt + user beavatkozas.
4. Playwright E2E live stackre nem sikerul felhozni → SOFT fail dokumentalva, **halt csak akkor**, ha a CI-spec is fail-el.

**SOFT:**
- `(tenant_id, name)` unique constraint felhozasa (SS-FU-4) ha a PATCH-endpoint igenyelne — opcionalis, **halaszthato S145-re** ha a hatokor szuk marad.
- `customer` oszlop deprecation (SS-FU-5) — kulon refactor sprintbe, **NE keverd S144-be**.

---

## 6. SESSION VEGEN

```
/session-close S144
```

A `/session-close` generalja:
- `docs/sprint_s_s144_pr_description.md`
- CLAUDE.md numbers update.
- Skipped-items append (ha PG-S145-be tolt valami).
- Kovetkezo `NEXT.md` (S145 — nightly MRR@5 scheduled job + Grafana panel).

---

## 7. SKIPPED-ITEMS TRACKER (folytatas, ne legyen elveszve)

S143-bol orokolt nyitott items:

| ID | Hely | Mi | Unskip feltetel |
|---|---|---|---|
| SS-SKIP-1 | `tests/integration/services/rag_engine/test_query_1024_dim.py` | BGE-M3 weight skip-guard | S145 CI weight preload |
| SS-SKIP-2 | `01_PLAN/116_*` §8 | Profile B (Azure OpenAI) MRR@5 | Azure credit |
| SS-FU-1 | PR #34 body | `create_collection` tenant-aware arg + `customer` deprecation | Kulon refactor sprint |
| SS-FU-3 | PR #34 body | Nightly MRR@5 + Grafana | S145 |
| SS-FU-4 | PR #34 body | `(tenant_id, name)` unique constraint | S145 (vagy S144 ha kicsiben jol megfer) |
| SS-FU-5 | PR #34 body | `rag_collections.customer` deprecation | Kulon refactor |

S144 ezek kozul **csak SS-FU-2-t** zarja le. A tobbi felmeretvenyezve marad a kovetkezo session prompt-ben.
