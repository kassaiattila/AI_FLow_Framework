# AIFlow [Sprint X] — Session SX-3 Prompt (Routing trace audit table + admin UI)

> **Template version:** 1.0 (mandatory Quality target header).
> **Source template:** `session_prompts/_TEMPLATE.md`.
> **Closes:** Sprint W pipeline gap §2 — operators have no way to see why a doctype was picked, which extraction path ran, or whether the rule engine matched.

---

## Quality target (MANDATORY)

- **Use-case:** UC3 + UC1 composite (this is a **persistence + observability** session — pure addition; no behaviour change in either UC)
- **Metric:** composite gate — (a) UC3 4/4 unchanged; (b) UC1 ≥ 75% / `invoice_number` ≥ 90% unchanged; (c) one `routing_runs` row written per EXTRACT-class email when the SX-2 routing flag is on; (d) `/routing-runs` admin Playwright spec `routing-runs.md` PASS on a live stack
- **Baseline (now):** UC3 4/4 (Sprint K, byte-stable); UC1 ≥ 75% / `invoice_number` ≥ 90% (Sprint Q baseline); routing observability = **none** (no DB table, no API, no UI — SX-2 returns the routing decision in the API response only)
- **Target (after this session):** all four sub-gates green. Every flag-on EXTRACT email persists a `routing_runs` row; admin UI surfaces the trail; UC3 + UC1 byte-stable (writes are pure observation).
- **Measurement command:** `pytest tests/integration/skills/test_uc3_4_intents.py tests/integration/skills/test_uc1_golden_path.py tests/integration/services/routing_runs/ -v && cd aiflow-admin && npx playwright test tests/ui-live/routing-runs.md`

> Note (deviation from "one-UC quality push"): Sprint X is operator-directed
> as a multi-UC pipeline-unification sprint (see `docs/post_sprint_w_audit.md`).
> SX-3 uses a **composite observation gate** because the value is wiring +
> persistence + UI, not metric improvement. Acceptance is binary: all four
> sub-gates pass.

---

## Goal

Make every UC3 EXTRACT routing decision visible to operators. Three layers:

1. **Persistence** — `routing_runs` table (Alembic 050) with full per-email dispatch + outcome metadata.
2. **API** — read-only `/api/v1/routing-runs` router with 3 routes (list / detail / aggregate stats).
3. **UI** — `/routing-runs` admin page with stats panel, filter chips, side-drawer detail, and deep-link back to the originating email.

The SX-2 helper (`_route_extract_by_doctype`) already produces a complete
`UC3ExtractRouting` Pydantic payload — SX-3 wires the **service-layer
write** at the dispatch boundary so the same payload lands in the audit
table without any orchestrator-level change.

---

## Predecessor context

> **Datum:** 2026-04-27 (snapshot — adjust if session runs later)
> **Branch:** `feature/x-sx3-routing-trace-audit` (cut from `main` after
> SX-2 PR #64 + ROADMAP-flip PR #65 squash-merged on `main`)
> **HEAD (expected):** `8e0c619` (PR #65 ROADMAP flip on top of `c0e69fe`
> SX-2 routing layer merge)
> **Predecessor session:** SX-2 — UC3 → DocRecognizer routing layer
> (default-off; UC1 byte-stable on flag-on `hu_invoice`; 13 unit + 1
> integration scaffold; OpenAPI delta = `+ EmailDetailResponse.routing_decision`)

---

## Pre-conditions

- [ ] SX-2 PR (#64) + ROADMAP-flip PR (#65) merged on `main`
- [ ] Branch cut: `feature/x-sx3-routing-trace-audit`
- [ ] Stack runnable (`bash scripts/start_stack.sh --validate-only` GREEN)
- [ ] `alembic current` reports head `049` (will move to `050` in this session)
- [ ] PostgreSQL Docker container running (5433)
- [ ] `aiflow.contracts.uc3_routing.UC3ExtractRouting` importable (SX-2 deliverable)
- [ ] `_route_extract_by_doctype` helper available (SX-2 deliverable)
- [ ] Admin UI dev stack runs (`cd aiflow-admin && npm run dev`) on port 5174

---

## Predecessor surfaces (existing, do not modify)

- SX-2 routing helper: `src/aiflow/services/email_connector/orchestrator.py::_route_extract_by_doctype` — returns `{"extracted_fields": ..., "total_cost_usd": ..., "routing_decision": <UC3ExtractRouting.model_dump>}`
- SX-2 contracts: `src/aiflow/contracts/uc3_routing.py` (`UC3ExtractRouting`, `UC3AttachmentRoute`, `ExtractionPath`, `ExtractionOutcome`)
- SX-2 settings: `src/aiflow/core/config.py::UC3DocRecognizerRoutingSettings` (`enabled`, `confidence_threshold`, `total_budget_seconds`, `unknown_doctype_action`)
- Email detail API: `src/aiflow/api/v1/emails.py::EmailDetailResponse.routing_decision` (additive field — SX-2 wired the JSON pass-through)
- Email source table: existing `emails` table (`id UUID PRIMARY KEY`)
- DocRecognizer audit pattern: `src/aiflow/services/document_recognizer/orchestrator.py::DocumentRecognizerOrchestrator.to_audit_payload(...)` (PII redaction reference)
- Existing UC1 byte-stable test: `tests/integration/skills/test_uc1_golden_path.py`
- Existing UC3 4/4 test: `tests/integration/skills/test_uc3_4_intents.py`

---

## Tasks

### LÉPÉS 1 — Alembic 050 `routing_runs` table

```
Cél:    Persistence layer for routing decisions.
Fájlok: alembic/versions/050_routing_runs.py (NEW)
Forrás: 01_PLAN/121_SPRINT_X_INTAKE_PIPELINE_RAG_CHAT_PLAN.md §SX-3 step 1
```

Schema (per the plan):
- `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`
- `tenant_id TEXT NOT NULL DEFAULT 'default'`
- `email_id UUID NULL` — FK to `emails(id)` ON DELETE SET NULL
- `intent_class TEXT NOT NULL` — matches Sprint O FU-2 `_resolve_intent_class` output
- `doctype_detected TEXT NULL` — NULL when classifier produced no match
- `doctype_confidence FLOAT NULL`
- `extraction_path TEXT NOT NULL` — CHECK in `('invoice_processor', 'doc_recognizer_workflow', 'rag_ingest', 'skipped')` (note: matches SX-2's `ExtractionPath` literal — `rag_ingest` not `rag_ingest_fallback`; align with the contract)
- `extraction_outcome TEXT NOT NULL` — CHECK in `('succeeded', 'failed', 'refused_cost', 'skipped', 'timed_out')` (matches SX-2's `ExtractionOutcome` literal)
- `cost_usd FLOAT NULL`
- `latency_ms INTEGER NULL`
- `metadata JSONB NULL` — per-attachment detail (capped at 8 KB at write time; truncation logged WARN)
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`

Indexes:
- `idx_routing_runs_tenant_created` on `(tenant_id, created_at DESC)`
- `idx_routing_runs_email_id` on `(email_id)`
- `idx_routing_runs_extraction_outcome` on `(extraction_outcome)`

Acceptance: Alembic 050 round-trip clean (`alembic upgrade 050 && alembic downgrade 049 && alembic upgrade 050`).

### LÉPÉS 2 — `RoutingRunRepository`

```
Cél:    Service-layer persistence + read API for routing trail.
Fájlok: src/aiflow/services/routing_runs/__init__.py (NEW)
        src/aiflow/services/routing_runs/repository.py (NEW)
        src/aiflow/services/routing_runs/models.py (NEW)
Forrás: §SX-3 step 2
```

Pydantic models in `models.py`:
- `RoutingRunInsert` — input shape for `insert(...)` (mirrors `routing_runs` columns minus `id`, `created_at`)
- `RoutingRunSummary` — list-row shape (without `metadata` JSONB to keep responses small)
- `RoutingRunDetail` — full row including `metadata`
- `RoutingStatsResponse` — `{by_doctype: dict, by_outcome: dict, mean_cost_usd: float, p50_latency_ms: int, p95_latency_ms: int, total_count: int}`
- `RoutingRunListFilters` — `{tenant_id, intent_class, doctype_detected, extraction_outcome, since, until, limit, offset}`

Repository contract:
- `async insert(row: RoutingRunInsert) -> UUID`
- `async list(filters: RoutingRunListFilters) -> list[RoutingRunSummary]`
- `async get(id: UUID, tenant_id: str) -> RoutingRunDetail | None` (tenant guard: rows are per-tenant)
- `async aggregate_stats(tenant_id: str, since: datetime, until: datetime) -> RoutingStatsResponse`

Implementation notes:
- Use `aiflow.api.deps.get_pool()` for the asyncpg pool (same pattern as cost_recorder).
- `metadata` JSONB cap: enforce 8 KB before insert; if oversized, log `routing_runs.metadata_truncated` WARN with `original_size_bytes` and write a stub `{truncated: true, reason: "size_cap_8kb"}`.
- `aggregate_stats` p50/p95: use `percentile_cont` PostgreSQL aggregate.

### LÉPÉS 3 — Service-layer write at the SX-2 dispatch boundary

```
Cél:    Wire the orchestrator to call repository.insert(...) without
        changing the SX-2 byte-stable behaviour.
Fájlok: src/aiflow/services/email_connector/orchestrator.py (MODIFY — additive only)
Forrás: §SX-3 step 3
```

Approach: extend `scan_and_classify` with an optional `routing_run_repo: RoutingRunRepository | None = None` kwarg. When provided AND `routing_settings.enabled`, after `_route_extract_by_doctype` returns its payload, build a `RoutingRunInsert` and call `repo.insert(...)`. Per-email row collapses the per-attachment list down to:
- `extraction_path` = the most consequential path (`invoice_processor` > `doc_recognizer_workflow` > `rag_ingest` > `skipped` per the literal order)
- `extraction_outcome` = worst outcome (`failed` > `refused_cost` > `timed_out` > `skipped` > `succeeded`)
- `cost_usd`, `latency_ms` = `routing.total_cost_usd`, `routing.total_latency_ms`
- `metadata` = full `UC3ExtractRouting.model_dump(mode="json")` (capped at 8 KB)

PII boundary: redact `metadata.attachments[*].filename` to first 64 chars + `...` if longer; redact any `error` strings to `<error_class>: <message[:200]>`.

Flag-off path is unchanged — repository is never called when `routing_settings.enabled=False` or `routing_run_repo` is None.

### LÉPÉS 4 — `/api/v1/routing-runs` router

```
Cél:    Read-only API for the admin UI.
Fájlok: src/aiflow/api/v1/routing_runs.py (NEW)
        src/aiflow/api/app.py (MODIFY — register router)
Forrás: §SX-3 step 4
```

Routes:
- `GET /` — query params: `tenant_id`, `intent_class`, `doctype_detected`, `extraction_outcome`, `since` (ISO8601), `until`, `limit` (default 50, max 200), `offset` (default 0). Returns `list[RoutingRunSummary]`.
- `GET /{id}` — path param `id: UUID`, query `tenant_id` required (tenant guard). Returns `RoutingRunDetail` or 404.
- `GET /stats` — query `tenant_id`, `since`, `until`. Returns `RoutingStatsResponse`.

Auth: standard JWT/API-key dependency (mirror `/api/v1/emails` pattern).

### LÉPÉS 5 — `/routing-runs` admin UI page

```
Cél:    Operator-grade observability surface.
Fájlok: aiflow-admin/src/pages-new/RoutingRunsPage.tsx (NEW)
        aiflow-admin/src/components-new/routing-runs/StatsPanel.tsx (NEW)
        aiflow-admin/src/components-new/routing-runs/RoutingRunsTable.tsx (NEW)
        aiflow-admin/src/components-new/routing-runs/RoutingRunDrawer.tsx (NEW)
        aiflow-admin/src/locales/en/routing-runs.json (NEW)
        aiflow-admin/src/locales/hu/routing-runs.json (NEW)
        aiflow-admin/src/router/AppRouter.tsx (MODIFY — register /routing-runs)
        aiflow-admin/src/components-new/layout/AppSidebar.tsx (MODIFY — nav entry)
Forrás: §SX-3 step 5 + UI pipeline 7 HARD GATES (skill aiflow-ui-pipeline)
```

Layout:
- **Top stats panel** — 5 cards: total runs, doctype distribution donut, outcome distribution stacked bar, mean cost USD, p50/p95 latency.
- **Filter row** — chips for `intent_class`, `doctype_detected`, `extraction_outcome`; date-range picker for `since`/`until`; tenant picker (operator may need cross-tenant view).
- **Main table** — Untitled UI table: `created_at`, `tenant_id`, `intent_class`, `doctype_detected` (with confidence chip), `extraction_path`, `extraction_outcome` (color-coded), `cost_usd`, `latency_ms`, "View" button → opens drawer.
- **Side drawer** — full `RoutingRunDetail` JSON, per-attachment list, "View original email" deep-link to `/emails/{email_id}`.
- EN/HU locale on all labels.

UI pipeline gates (from `aiflow-ui-pipeline` skill): journey definition, API endpoint contract, Figma design optional, Untitled UI components, React Aria, Tailwind v4, Playwright live spec.

### LÉPÉS 6 — Tests (12 unit + 3 integration + 1 Playwright)

Unit:
- `tests/unit/services/routing_runs/test_repository_models.py` — 6 tests: `RoutingRunInsert` validation, `RoutingRunListFilters` defaults, `RoutingRunSummary` shape, `RoutingStatsResponse` shape, metadata-cap logic, path/outcome priority resolver.
- `tests/unit/api/v1/test_routing_runs_router.py` — 6 tests: list with filters, list pagination, detail tenant guard, detail 404, stats happy path, stats empty window.

Integration (real PG):
- `tests/integration/services/routing_runs/test_repository_real.py` — 3 tests: `insert + list` round-trip, `aggregate_stats` against fixture rows, `get` returns `None` for cross-tenant ID.

Playwright live (UI):
- `tests/ui-live/routing-runs.md` — 3 tests: list renders, filter by `doctype_detected` works, detail drawer opens.

### LÉPÉS 7 — OpenAPI snapshot refresh

```bash
.venv/Scripts/python scripts/check_openapi_drift.py --update
.venv/Scripts/python scripts/check_openapi_drift.py  # must report [ok]
```

Expected delta: 3 new paths (`/api/v1/routing-runs`, `/api/v1/routing-runs/{id}`, `/api/v1/routing-runs/stats`) + 4 new schemas (`RoutingRunSummary`, `RoutingRunDetail`, `RoutingStatsResponse`, `RoutingRunListFilters`).

### LÉPÉS 8 — Validáció + commit + PR

```bash
.venv/Scripts/python -m ruff check src/ tests/
.venv/Scripts/python -m pytest tests/unit/services/routing_runs/ tests/unit/api/v1/test_routing_runs_router.py tests/integration/services/routing_runs/ -v
cd aiflow-admin && npx tsc --noEmit && npx playwright test tests/ui-live/routing-runs.md
.venv/Scripts/python -m pytest tests/integration/skills/test_uc3_4_intents.py tests/integration/skills/test_uc1_golden_path.py -v  # byte-stable gate
/session-close SX-3
```

PR title: `feat(sprint-x): SX-3 — Routing trace audit (Alembic 050 + 3-route API + /routing-runs admin UI)`.

---

## Acceptance criteria

- [ ] **Quality target met** — all four composite sub-gates green (UC3 4/4 + UC1 byte-stable + `routing_runs` row written per EXTRACT email + Playwright `routing-runs.md` PASS)
- [ ] Alembic 050 round-trip clean (upgrade 049 → 050 → downgrade → re-upgrade)
- [ ] 12 unit tests PASS (repository models × 6 + router × 6)
- [ ] 3 integration tests PASS (real PG: insert+list, aggregate_stats, cross-tenant guard)
- [ ] Live Playwright spec `tests/ui-live/routing-runs.md` PASS on a clean dev stack
- [ ] No regression on byte-stable golden paths (UC3 4/4 + UC1 ≥ 75% / `invoice_number` ≥ 90% unchanged — this is observation-only)
- [ ] `make lint` clean
- [ ] OpenAPI snapshot refreshed (only the 3 new paths + 4 new schemas; **zero changes to existing paths or schemas**)
- [ ] `aiflow-admin && npx tsc --noEmit` clean
- [ ] PR opened against `main`, CI green
- [ ] `01_PLAN/ROADMAP.md` Sprint X table row SX-3 status → DONE
- [ ] `CLAUDE.md` Sprint X session lineup row SX-3 → DONE

---

## Constraints

- **Observation-only writes.** SX-3 must NOT change the SX-2 dispatch behaviour. The repository call is a side effect after the dispatch returns; failure to write a `routing_runs` row logs WARN but does NOT propagate (the email still completes).
- **Tenant boundary.** Every read API path requires `tenant_id`; `get_by_id` enforces tenant match (no cross-tenant leakage).
- **PII boundary.** `metadata` JSONB stores routing payload only — filenames truncated, error strings clamped to 200 chars. No email body, no attachment content.
- **8 KB metadata cap.** Enforced at write time; oversize → stub + WARN.
- **No schema change to existing tables.** Pure additive: new table only.
- **No `routing_decision` mutation in `EmailDetailResponse`.** SX-2's response field stays byte-stable; SX-3 reads from the new audit table for the admin UI, not the email detail endpoint.

---

## STOP conditions

**HARD:**
- UC3 4/4 regression on flag-off (byte-stable contract). Halt.
- UC1 < 75% or `invoice_number` < 90% on flag-on `hu_invoice` (byte-stable contract). Halt.
- Alembic 050 round-trip fails (downgrade does not restore 049 cleanly). Halt — schema bug.
- Repository write failure crashes the orchestrator (must be soft-fail with WARN). Halt.
- OpenAPI drift on existing paths/schemas (only the 3 new paths + 4 new schemas allowed). Halt.

**SOFT:**
- Operator-driven dependency missing (no admin UI dev stack) → Playwright spec deferred but unit + integration still required.
- Stats endpoint p50/p95 query slow on real-PG fixture → consider materialized view in v1.8.1 (track in `docs/sprint_x_retro.md`).
- Cross-tenant aggregate dashboard requested mid-session → out of scope; SX-3 is per-tenant only.

---

## Output / handoff format

The session ends with:

1. PR opened against `main` titled `feat(sprint-x): SX-3 — Routing trace audit (Alembic 050 + 3-route API + /routing-runs admin UI)`.
2. PR body summarizes Alembic 050 + repository + service write + API + UI + composite Quality target outcome.
3. `/session-close SX-3` invoked → generates `session_prompts/NEXT.md` for SX-4 (professional RAG chat: Alembic 051 `aszf_conversations` + `aszf_conversation_turns` + 4-route API + `/aszf/chat` UI upgrade).
4. `01_PLAN/ROADMAP.md` Sprint X table row SX-3 → DONE.
5. `CLAUDE.md` Sprint X session lineup row SX-3 → DONE.
6. (No `docs/SPRINT_HISTORY.md` entry — that lands at SX-5 sprint-close only.)

---

## References

- Sprint X plan: `01_PLAN/121_SPRINT_X_INTAKE_PIPELINE_RAG_CHAT_PLAN.md` §SX-3
- Forward queue: `01_PLAN/ROADMAP.md`
- Post-Sprint-W audit: `docs/post_sprint_w_audit.md` §"Routing trace"
- Honest alignment audit: `docs/honest_alignment_audit.md`
- SX-2 contracts (input shape): `src/aiflow/contracts/uc3_routing.py`
- SX-2 helper (write boundary): `src/aiflow/services/email_connector/orchestrator.py::_route_extract_by_doctype`
- SX-2 settings: `src/aiflow/core/config.py::UC3DocRecognizerRoutingSettings`
- DocRecognizer audit pattern (PII redaction reference): `src/aiflow/services/document_recognizer/orchestrator.py::DocumentRecognizerOrchestrator.to_audit_payload`
- UI pipeline 7 HARD GATES: skill `aiflow-ui-pipeline`
- DB rules: skill `aiflow-database`
- Observability rules: skill `aiflow-observability`
