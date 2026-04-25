# Sprint S — Retrospective (v1.5.2 Functional vector DB at Sprint L/N parity)

> **Sprint window:** 2026-04-25 → 2026-04-26 (3 sessions: S143, S144, S145; close in S146)
> **Branch:** `chore/sprint-s-close` (cut from `main` @ `d6ee813`, S145 squash-merge of PR #37)
> **Tag:** `v1.5.2` — queued for post-merge on `main`
> **PRs:** #34 (S143), #35 (S144), #36 (chore env), #37 (S145), plus this close PR (S146)
> **Predecessor:** `v1.5.1` (Sprint R — PromptWorkflow foundation, MERGED)
> **Plan reference:** `01_PLAN/116_SPRINT_S_FUNCTIONAL_VECTOR_DB_PLAN.md` + `01_PLAN/114_CAPABILITY_ROADMAP_Q_R_S.md` §4

## Headline

Sprint S converts the multi-tenant + multi-profile vector DB from "data model + scaffolding" (Sprint J) to **operator-usable capability**, at parity with Sprint L (monitoring) and Sprint N (per-tenant budgets). Three deliveries: the query-path ProviderRegistry refactor that makes 1024-dim BGE-M3 collections actually queryable (S143), the admin UI for listing collections per tenant and attaching/detaching embedder profiles (S144), and the operability close-out — nightly MRR@5 harness, `(tenant_id, name)` uniqueness, BGE-M3 weight CI cache (S145).

```
S143:  RAGEngineService.query() resolver + adapter           ← contract refactor
       Alembic 046 (tenant_id, embedder_profile_id)
S144:  /api/v1/rag-collections admin router + UI page        ← operator surface
       set_embedder_profile() with DimensionMismatch guard
S145:  RagMetricsHarness + 20-item HU corpus + CLI runner    ← operability
       Alembic 047 swap UNIQUE(name) → UNIQUE(tenant_id,name)
       BGE-M3 weight cache step in nightly-regression.yml
```

NULL-fallback path for legacy 1536-dim collections is byte-for-byte identical to pre-S143 behaviour. Every `rag_collections` row landed in the multi-tenant world with `tenant_id='default'` (server-default backfill from migration 046). No skill code touched; no behaviour change for any UC running on a NULL-profile collection.

## Scope by session

| Session | Commit | Deliverable |
|---|---|---|
| **S143** | `95ec89e` (PR #34) | `RAGEngineService.query()` ProviderRegistry refactor: `_resolve_query_embedder(coll)` dispatch (NULL → legacy `self._embedder` fallback / known alias → `_QueryEmbedderAdapter` over fresh `EmbedderProvider` / unknown alias → `UnknownEmbedderProfile` returned via `QueryResult.answer` with no exception). Alembic **046** additive: `rag_collections.tenant_id TEXT NOT NULL DEFAULT 'default'` + `rag_collections.embedder_profile_id TEXT NULL` + `ix_rag_collections_tenant_id`. **+14 unit** (resolver dispatch + adapter surface + unknown-profile error + `CollectionInfo` defaults), **+2 alembic integration** (046 round-trip + server-default backfill), **+2 rag_engine integration** on real PG + real BGE-M3 weights (1024-dim production via adapter, pgvector flex-dim search end-to-end). Per-skill `aszf_rag_chat` code unchanged. |
| **S144** | `bc59a8f` (PR #35) | `RAGEngineService.set_embedder_profile()` mutation with empty-collection short-circuit + dim-equality guard + `DimensionMismatch → HTTP 409 RAG_DIM_MISMATCH`. New 3-route admin router at `/api/v1/rag-collections` (hyphenated, see SS-2): `GET /` (list with optional `tenant_id` filter), `GET /{id}` (detail), `PATCH /{id}/embedder-profile`. New admin page `/#/rag/collections` (`pages-new/RagCollections/`): table list, tenant chip filter with `?tenant=` deep-link, side drawer + profile select + Save. EN/HU locale, sidebar nav `Tudasbazis → RAG kollekciok`. **+9 unit** (set_embedder_profile dim-guard matrix), **+3 unit** (router list filter / 404 / 409 surface), **+3 integration** on real PG (two-tenant filter, empty-collection PATCH persistence, populated 1536→1024 PATCH refusal), **+1 Python Playwright** at `tests/e2e/test_rag_collections.py`. |
| **S145** | `d6ee813` (PR #37) | `RagMetricsHarness` (`src/aiflow/services/rag_metrics/`) — async batch retrieval-quality measurement over a `QuerySpec` corpus, emits `MetricsSnapshot` (mrr_at_k, p95_latency_ms, error_count) + JSONL row payloads ready for psql ingest. `data/fixtures/rag_metrics/uc2_aszf_query_set.json` 20-item HU UC2 query corpus. `scripts/run_nightly_rag_metrics.py` CLI runner. `docs/grafana/rag_collection_metrics_panel.json` 4-panel dashboard. `docs/runbooks/rag_metrics_nightly.md` operator runbook. Alembic **047** swap of legacy `UNIQUE (name)` for `UNIQUE (tenant_id, name)` on `rag_collections` (pre-flight duplicate scan returned 0 rows — metadata-only DDL, zero data churn). `actions/cache@v4` BGE-M3 weight step in `.github/workflows/nightly-regression.yml` so 1024-dim integration tests un-skip on the nightly run. **+6 unit** (MRR@5 / p95 / QuerySpec / JSONL emission / harness iteration / empty-set sentinel), **+2 alembic integration** (047 round-trip + cross-tenant collision matrix), **+1 rag_metrics integration** gated by `AIFLOW_RUN_NIGHTLY_RAG_METRICS=1` + `OPENAI_API_KEY`. |
| **S146** | _(this commit)_ | Sprint close — `docs/sprint_s_retro.md`, `docs/sprint_s_pr_description.md`, CLAUDE.md banner flip + numbers, PR cut against `main`, tag `v1.5.2` queued (not pushed). |

Plus the side-branch `chore/consolidate-dev-env` (PR #36, `ec3e672`) cut between S144 and S145 to unblock the operator live-test of `/rag/collections`. Sourced from S145 prereq work but landed first because the live-test required a single canonical `.env` file with the seeded admin creds — captured in this retro for ops-history continuity.

## Test deltas

| Suite | Before (Sprint R tip) | S143 tip | S144 tip | After (S145 tip) | Sprint Δ |
|---|---|---|---|---|---|
| Unit | 2347 | 2361 | 2373 | **2379** | **+32** (14 + 12 + 6) |
| Integration | ~103 | ~107 | ~110 | **~113** | **+10** (4 + 3 + 3) |
| E2E collected | 429 | 429 | **430** | 430 | **+1** (S144 rag-collections Playwright) |
| API endpoints | 193 | 193 | **196** | 196 | **+3** (S144: list / detail / PATCH) |
| API routers | 30 | 30 | **31** | 31 | **+1** (S144: rag-collections) |
| UI pages | 25 | 25 | **26** | 26 | **+1** (S144: RagCollections) |
| Alembic head | 045 | **046** | 046 | **047** | **+2** (S143: 046, S145: 047) |
| Ruff / TSC | clean | clean | clean | clean | 0 new errors |

S143 unit math: 2347 + 14 (rag_engine resolver / adapter / unknown-profile / CollectionInfo defaults) = 2361.
S144 unit math: 2361 + 9 (set_embedder_profile dim-guard) + 3 (rag-collections router unit) = 2373.
S145 unit math: 2373 + 6 (MRR@5 / p95 / QuerySpec / JSONL / iteration / empty-sentinel) = 2379.

Integration breakdown:
- S143 +4: 2 alembic 046 (round-trip + server-default backfill) + 2 rag_engine (1024-dim adapter end-to-end + pgvector flex-dim).
- S144 +3: rag-collections router (two-tenant list, empty-collection PATCH, populated dim-mismatch 409) on real PG.
- S145 +3: 2 alembic 047 (constraint round-trip + cross-tenant collision matrix) + 1 rag_metrics harness boundary-shape (skip-by-default behind `AIFLOW_RUN_NIGHTLY_RAG_METRICS=1` + `OPENAI_API_KEY`).

## Contracts + architecture delivered

- **`RAGEngineService.query()` ProviderRegistry refactor (S143)** — Single resolver `_resolve_query_embedder(coll)` keeps the legacy 1536-dim path byte-for-byte identical (NULL `embedder_profile_id` → `self._embedder`) and adds the multi-profile path (`bge_m3` / `azure_openai` / `openai` → `_QueryEmbedderAdapter` over a freshly instantiated `EmbedderProvider`). Unknown aliases surface as `UnknownEmbedderProfile` (`AIFlowError`, `is_transient=False`) returned via `QueryResult.answer` rather than raising — keeps callers from catching exceptions in the query happy path.
- **Alembic 046 (S143)** — `rag_collections` gains `tenant_id TEXT NOT NULL DEFAULT 'default'` (server default backfills every existing row), `embedder_profile_id TEXT NULL`, and `ix_rag_collections_tenant_id`. Additive only; downgrade drops cleanly. The default-tenant backfill is what made the multi-tenant rollout zero-downtime: every legacy collection becomes queryable as tenant `default` automatically.
- **`set_embedder_profile()` mutation (S144)** — `RAGEngineService` gains a single mutation method with structured failure modes:
  - empty collection (`chunk_count == 0`) → accept any known alias, refresh `embedding_dim` to provider dim;
  - populated collection, profile-to-profile → require dim-equality;
  - populated collection, detach to NULL → require existing `embedding_dim == 1536` (legacy `self._embedder` dim);
  - any dim conflict → `DimensionMismatch` (`AIFlowError`, `is_transient=False`, surfaced as HTTP 409 with `error_code = "RAG_DIM_MISMATCH"`).
- **`/api/v1/rag-collections` admin router (S144)** — 3 routes (`GET /`, `GET /{id}`, `PATCH /{id}/embedder-profile`). Mounted at the **hyphenated** prefix to avoid colliding with the existing `/api/v1/rag/collections` ingest/query/CRUD routes consumed by the UC2 RAG UI (see decision SS-2).
- **`pages-new/RagCollections/` admin page (S144)** — table list with tenant chip filter (`?tenant=` deep-link), side drawer for detail + `EmbedderProfileBadge` + profile select + Save action. EN/HU locale (`aiflow.menu.ragCollections`, `aiflow.rag.collections.*`). Sidebar nav under `Tudasbazis`.
- **`RagMetricsHarness` + corpus + CLI + Grafana panel (S145)** — `src/aiflow/services/rag_metrics/{contracts.py,harness.py}` exposes `QuerySpec` + `MetricsSnapshot` + `RagMetricsHarness.run()`. The harness emits `JSONL` rows ready for psql ingest into the `rag_collection_metrics_jsonl` table (operator-managed, runbook-driven — keeps the AIFlow runtime air-gap-safe; see SS-5). `scripts/run_nightly_rag_metrics.py` is the CLI shim. `data/fixtures/rag_metrics/uc2_aszf_query_set.json` provides 20 HU UC2 baseline queries. `docs/grafana/rag_collection_metrics_panel.json` is a 4-panel dashboard (MRR@5 trend, p95 latency, error count, coverage). `docs/runbooks/rag_metrics_nightly.md` walks operators through provisioning + scheduling.
- **Alembic 047 (S145)** — Drops `uq_rag_collections_name` (legacy `UNIQUE (name)`) and creates `uq_rag_collections_tenant_id_name` (`UNIQUE (tenant_id, name)`). Pre-flight duplicate scan returned 0 rows; the swap is metadata-only. Cross-tenant name reuse (`tenant=A,name=foo` + `tenant=B,name=foo`) becomes legal — required for the multi-tenant story to make sense.
- **BGE-M3 weight cache in nightly CI (S145)** — `actions/cache@v4` step in `.github/workflows/nightly-regression.yml` with key derived from `pyproject.toml` hash. The 1024-dim integration tests (S143's rag_engine real-PG/real-weights tests) un-skip only on nightly; main CI stays at ~3 min. Closes SS-SKIP-1.

## Key numbers (Sprint S tip)

```
27 service | 196 endpoint (31 routers) | 50 DB table | 47 Alembic (head: 047)
2379 unit PASS / 1 skipped (xfail-quarantined: resilience 50ms timing flake)
~113 integration PASS (Sprint S +10)
430 E2E collected (Sprint S +1, S144 rag-collections Playwright)
26 UI pages (Sprint S +1, S144 RagCollections)
0 ruff error on changed files | 0 TSC error | OpenAPI snapshot refreshed
Branch: chore/sprint-s-close (HEAD prepared, 4 commits on main ahead of
        Sprint R tip ffd7618)
Flag defaults on merge: NULL-fallback unchanged, no new feature flags
                        (Sprint R/Q/P/O/N/M flags all unchanged)
1 multi-tenant constraint:    UNIQUE (tenant_id, name) on rag_collections
3 known embedder aliases:     bge_m3 / azure_openai / openai
1 nightly retrieval harness:  RagMetricsHarness + 20-item HU UC2 corpus
```

## Decisions log

- **SS-1 — ProviderRegistry adapter on the query path keeps NULL-fallback byte-for-byte for legacy 1536-dim collections.** `_resolve_query_embedder(coll)` short-circuits to `self._embedder` whenever `embedder_profile_id IS NULL`. No behaviour change for any pre-Sprint-S collection. The adapter only kicks in when a profile is explicitly attached. This is what made the 046 + 047 migrations safe for live tenants.
- **SS-2 — Admin router mounted at `/api/v1/rag-collections` (hyphenated) to avoid colliding with the legacy `/api/v1/rag/collections` UC2 ingest/query routes.** The legacy `rag_engine.py` router owns `/api/v1/rag/collections` for ingest, query, document, chunk, feedback, and stats endpoints — all consumed by the existing UC2 RAG UI page. Mounting an admin-shape router in front would shadow the GET endpoints with an incompatible response shape and break UC2. Hyphenated prefix preserves the operator UX without touching legacy callers.
- **SS-3 — `set_embedder_profile()` short-circuits on empty collections (no `DimensionMismatch` raised when `chunk_count = 0`).** Operator expectation is that an empty collection's profile is freely changeable; only populated collections need the dim-equality guard. The mutation refreshes `embedding_dim` to the new provider's dim on the empty path so subsequent ingest sees the right value.
- **SS-4 — Alembic 047 drops the legacy `UNIQUE (name)` instead of preserving both.** Preserving both would block cross-tenant name reuse (e.g. `tenant=A,name=knowledge_base` + `tenant=B,name=knowledge_base`), defeating the multi-tenancy story. Pre-flight duplicate scan returned 0 rows, so the swap is metadata-only with zero data churn. The new constraint name (`uq_rag_collections_tenant_id_name`) follows the existing naming convention.
- **SS-5 — MRR@5 harness persists *externally* via runbook-driven psql ingest — keeps the AIFlow runtime air-gap-safe and lets operators choose retention policy.** `RagMetricsHarness.run()` emits JSONL row payloads but never writes them. The runbook (`docs/runbooks/rag_metrics_nightly.md`) walks operators through provisioning the `rag_collection_metrics_jsonl` table + scheduling the CLI runner + ingest. This keeps the AIFlow runtime free of a metrics-store dependency (compatible with Sprint M air-gap Profile A) and lets each tenant pick their own retention.
- **SS-6 — BGE-M3 weight cache lives in `nightly-regression.yml`, not `ci.yml` — main CI stays fast (~3 min); the 1024-dim integration tests un-skip only on the nightly run.** The full BGE-M3 weight set is ~2 GB. Caching it on every PR build would inflate the cache budget and slow startup; running the 1024-dim tests on every PR would slow CI. Nightly regression is the right cadence for multi-profile retrieval-quality validation.
- **SS-7 — `chore/consolidate-dev-env` (PR #36) cut as a side branch off `main` between S144 and S145 to unblock the operator live-test of `/rag/collections` — not strictly Sprint S scope, captured here for ops-history continuity.** The S144 live-test surfaced trailing whitespace in the seeded admin password (env-file consolidation between `.env`, `.env.example`, `.env.langfuse.example`). Fixed in PR #36 alongside `scripts/seed_admin.py` reading the canonical `.env` directly. Ops-history note: the env consolidation is what makes future live-tests reproducible — should be reused for Sprint T.

## What worked

- **Three-step capability rollout (data model → operator surface → operability) at exactly one capability per session.** S143 made 1024-dim collections queryable but invisible; S144 made them operator-visible; S145 closed the operability gap (uniqueness, nightly metrics, CI cache). Each session merged independently. None of the 3 PRs blocked on the next.
- **NULL-fallback as the multi-tenant rollout bridge.** The Alembic 046 server default + the resolver short-circuit together meant every legacy collection survived the schema change with byte-for-byte identical query behaviour. Operators can adopt the multi-profile path one collection at a time via the new admin UI; no big-bang migration.
- **Hyphenated admin prefix as a low-cost path-collision fix.** SS-2 turned a real collision risk into a documented one-character difference. Reusing the legacy `/api/v1/rag/...` ingest routes for UC2 stays free; the new admin surface is unambiguous.
- **Pre-flight duplicate scan before Alembic 047 swap.** Knowing 0 rows would collide turned a potentially data-loss-risky DDL into a metadata-only swap. This pattern (always scan before tightening uniqueness) is worth canonizing for future schema changes.
- **Operator runbook for the metrics harness.** Keeping retention + scheduling out of the AIFlow runtime makes the harness portable to air-gap (Sprint M) deployments without any code change. Operators that want richer storage can wire JSONL straight into ClickHouse / Druid / etc.

## What hurt

- **Trailing-space seeded admin password (S144 live-test).** Discovered during the operator live-test of `/rag/collections` after PR #35 squash-merged. Forced the side-branch PR #36 to consolidate env files and fix `scripts/seed_admin.py` to read `.env` directly. Lesson: env-file fragmentation is a real ops-debt; consolidating to a single canonical `.env` should have happened in Sprint M (when Vault landed). Captured as decision SS-7 for future-archeology.
- **Sprint S did not migrate `customer` column to `tenant_id` semantics in the model layer.** SS-FU-1 + SS-FU-5 are deliberately deferred to a separate refactor sprint — the cross-call surface for `customer` is wide, and bundling the rename with multi-tenancy rollout would have made the diff opaque. Trade-off: the model still has a `customer` column that is *de facto* dead but still readable. Future Sprint T (or earlier) needs to plan the rename explicitly.
- **Profile B (Azure OpenAI) live MRR@5 still pending Azure credit (SS-SKIP-2).** S145's harness can measure Profile B today; we just haven't got billable Azure credit. Carries from Sprint J. Operator activation step.
- **No live-test rerun for `/prompts/workflows` (SR-FU-4 carry from Sprint R).** Sprint S close acknowledges it as carry-forward, does not resolve. Sprint T scope.

## Open follow-ups

| ID | Description | Target |
|---|---|---|
| SS-FU-1 | `create_collection` tenant-aware arg + `customer` deprecation | Separate refactor sprint |
| SS-FU-5 | `rag_collections.customer` column drop | Separate refactor (after SS-FU-1) |
| SS-SKIP-2 | Profile B (Azure OpenAI) live MRR@5 | Azure credit landing |
| SS-FU-3 | Nightly MRR@5 + Grafana | **CLOSED in S145** — operator activation pending (provision `rag_collection_metrics_jsonl` table + import dashboard JSON + schedule cron) |
| SS-FU-4 | `(tenant_id, name)` unique constraint | **CLOSED in S145** |
| SS-SKIP-1 | BGE-M3 weight CI cache | **CLOSED in S145** — confirm with first nightly run |
| S141-FU-1/2/3 | Per-skill PromptWorkflow migration | Sprint T (S147+) |
| SR-FU-4 | Live-stack Playwright for `/prompts/workflows` | Sprint T |
| SR-FU-5 | `vite build` pre-commit hook | Sprint T |
| SR-FU-6 | Langfuse workflow listing | Sprint T |
| Sprint J Clock seam | Resilience timing flake fix | **DEADLINE 2026-04-30 — overdue at S146 close, must triage in S147** |

## Lessons learned

- **Trailing-space passwords in env files.** `.env` has no escape mechanism for trailing whitespace; `python-dotenv` preserves it; `scripts/seed_admin.py` was hashing the trailing-space variant; the operator was logging in with the trimmed variant. Three days of "but the password is right" before SS-7 root-cause. Going forward, env-loaded secrets should `.strip()` at the boundary, and the seed script should log the SHA-256 prefix so the operator can verify match.
- **Single-canonical `.env`** is the only env-file pattern that survives an operator live-test. Sprint M shipped Vault but kept three separate `.env*.example` files; SS-7 consolidates them. Sprint T should not introduce a fourth.
- **Pre-flight scan before tightening uniqueness.** Sprint S's Alembic 047 was risk-free because the operator ran `SELECT name, COUNT(*) FROM rag_collections GROUP BY name HAVING COUNT(*) > 1;` first and got 0 rows. Future sprints should canonize this — a one-row script that prints "OK to swap" or "N collisions" before any unique-tightening migration goes near `main`.
- **Air-gap-safe metrics persistence is achievable with a JSONL emit + operator runbook.** Sprint M's Profile A constraint forced the design; the result is that the metrics harness is portable to ClickHouse / Druid / plain psql without any AIFlow code change. Pattern reusable for Sprint T monitoring extensions.

## Cost

| Session | Wall clock | LLM cost | Notes |
|---|---|---|---|
| S143 | ~3.5 h | TBD | Mostly local — resolver design + pgvector flex-dim integration. Real-PG + real-BGE-M3 integration runs cost ~$0.10 in compute (BGE-M3 inference is local). |
| S144 | ~4 h | TBD | UI authoring (Tailwind v4 + React Aria) + 3 integration tests on real PG. ~$0.05 in operator-side LLM (admin-bootstrap script). |
| S145 | ~3 h | TBD | Harness scaffold + 20-query corpus + Grafana panel + runbook + Alembic 047. Negligible LLM cost — harness gated by `AIFLOW_RUN_NIGHTLY_RAG_METRICS=1`. |
| S146 (this) | ~30 min | ~$0 | Docs only, no code change. |

LLM-cost numbers will be filled in from Langfuse traces once the operator confirms a baseline window. **TBD** placeholders kept per the soft-stop rule in NEXT.md §5.

## Carried (Sprint R / Q / P / O / N / M / J — unchanged)

Sprint R `S141-FU-1/2/3` per-skill PromptWorkflow migrations + `SR-FU-4..6` (live-stack Playwright, vite-build pre-commit, Langfuse workflow listing) all carry to Sprint T. Sprint Q `SQ-FU-1..4` (issue_date extraction, docling warmup at boot, corpus extension, `_parse_date` ISO roundtrip) unchanged. Sprint P `SP-FU-1..3` unchanged. Sprint N/M/J residuals unchanged. The Sprint J resilience `Clock` seam deadline (2026-04-30) is now overdue — Sprint T (S147) must triage on its first session.
