# S91 — Coverage Plan & HARD STOP Report

**Date:** 2026-04-27
**Branch:** `feature/v1.4.4-consolidation`
**Baseline log:** `out/s91_coverage_baseline.log`
**HTML report:** `out/coverage_s91/index.html`

---

## Baseline

| Metric | Value |
|---|---|
| Statements | 19 434 |
| Missed | 6 414 |
| **Global coverage** | **67.00 %** |
| Target gate (`fail_under`) | 80 % |
| **Gap** | **13 p.p.** |
| Missed stmts to cover | ~2 528 |

Run: `1 939 passed, 1 failed, 396 warnings in 126 s`.

---

## HARD STOP

Session prompt STOP rule: *"Global coverage gap is too large to close in one session (> 10 p.p. below 80%) — halt, plan a multi-session coverage roadmap instead of mechanically chasing numbers."*

Gap is **13 p.p.**, above the threshold. S91 scope flips to roadmap-only; `fail_under=80` stays off; issue #7 stays open.

Separate regression noted: `tests/unit/security/test_auth.py::TestAuthProviderFromEnv::test_from_env_production_requires_keys` fails (expects `RuntimeError: REQUIRED in production`, but `AuthProvider.from_env` no longer raises). Production-env auth hardening may have regressed during Phase 1d — needs its own fix session, not bundled with coverage.

---

## Worst-covered modules (ranked by missed statements)

| Module | Stmts | Missed | Cov | Notes |
|---|---:|---:|---:|---|
| `services/email_connector/service.py` | 607 | 481 | 21% | Largest single offender. Needs real IMAP/OAuth fixtures — heavy. |
| `api/v1/emails.py` | 665 | 480 | 28% | Router; HTTP-level integration tests give the best return. |
| `api/v1/documents.py` | 462 | 318 | 31% | Router; pairs with `emails.py`. |
| `api/v1/rag_engine.py` | 388 | 247 | 36% | Router; RAG endpoint surfaces. |
| `api/v1/pipelines.py` | 397 | 220 | 45% | Router; partial tests exist — extend. |
| `vectorstore/pgvector_store.py` | 223 | 172 | 23% | Needs real pgvector integration tests. |
| `ingestion/parsers/docling_parser.py` | 165 | 165 | 0% | Heavy dependency; evaluate skip vs test. |
| `services/rag_engine/service.py` | 246 | 139 | 43% | Service-level; pairs with router work. |
| `tools/attachment_processor.py` | 136 | 136 | 0% | Entire `aiflow.tools.*` subtree at 0%. |
| `tools/playwright_browser.py` | 132 | 132 | 0% | |
| `pipeline/runner.py` | 163 | 126 | 23% | Orchestration hot path — important. |
| `api/v1/process_docs.py` | 148 | 119 | 20% | |
| `services/notification/service.py` | 238 | 109 | 54% | |
| `tools/human_loop.py` | 106 | 106 | 0% | |
| `api/v1/intent_schemas.py` | 187 | 105 | 44% | |

`aiflow.tools.*` (attachment_processor, azure_doc_intelligence, email_parser, human_loop, playwright_browser, robotframework_runner, schema_registry, shell) = **~900 stmts, all at 0%**. Single-session opportunity if we decide these are in-scope.

Other zero-covered: `execution/sla_checker.py` (21), `ingestion/chunkers/recursive_chunker.py` (94), `api/audit_helper.py` (15), `api/cost_recorder.py` (21).

---

## Proposed roadmap — Sprint H.1 (coverage uplift, 4 sessions)

Budget: ~630 missed stmts / session → 4 sessions.

### S91.A — Router hot paths (emails + documents)
**Closes:** `api/v1/emails.py` 28→75%, `api/v1/documents.py` 31→75%.
**Method:** FastAPI `TestClient` (real Postgres/Redis) exercising each endpoint group (list/get/create/update/delete/status transitions).
**Expected gain:** ~520 stmts → **+2.7 p.p.**

### S91.B — RAG + pipelines + process_docs routers
**Closes:** `api/v1/rag_engine.py` 36→75%, `api/v1/pipelines.py` 45→80%, `api/v1/process_docs.py` 20→70%, `api/v1/intent_schemas.py` 44→75%.
**Method:** extend existing router integration tests; real pgvector for RAG.
**Expected gain:** ~475 stmts → **+2.4 p.p.**

### S91.C — Services layer + pipeline runner
**Closes:** `services/email_connector/service.py` 21→55% (IMAP fixture), `services/rag_engine/service.py` 43→80%, `services/notification/service.py` 54→85%, `pipeline/runner.py` 23→75%.
**Method:** real IMAP test account (or skip if not feasible — surface to user first); targeted state-machine tests.
**Expected gain:** ~540 stmts → **+2.8 p.p.**

### S91.D — Vectorstore + tools decision + auth hardening fix
**Closes:** `vectorstore/pgvector_store.py` 23→80% (real pgvector), decide on `aiflow.tools/*` (cover the 2-3 most used, archive or `# pragma: no cover` the dead ones — user decision), fix the `test_auth` regression, sweep remaining sub-70% pockets (`api/v1/auth.py` 47%, `api/v1/chat_completions.py` 37%, `api/v1/spec_writer.py` 44%, `api/v1/runs.py` 42%, `skill_system/*`).
**Expected gain:** ~560–900 stmts → **+2.9…4.6 p.p.**

**Cumulative projection:** 67% → ~76–79% after S91.A-C; S91.D flips to ≥80% and enables the gate, closing issue #7.

---

## STOP FELTETEL — adding tests = production refactor?

Not yet evaluated per module. Expected candidates needing light refactors to be testable: `services/email_connector/service.py` (IMAP client injection), `pipeline/runner.py` (observer hooks). If a module requires > ~30 LoC of refactor to be testable, split into its own session per the S91 prompt's second HARD rule.

---

## Decision point for user

Three options:

1. **Accept roadmap, commit roadmap-only S91 and queue S91.A next** (recommended — matches STOP feltétel spirit).
2. **Narrow S91 to one module** (e.g. S91.A: emails router only), ship the coverage gain, and still defer the gate flip. Keeps motion but risks S91 = S91.A collision with the above plan.
3. **Override the HARD stop** and attempt a multi-module blast in this session. Not recommended; stop exists to prevent mechanical test churn.

Also surfacing: `test_auth.py::test_from_env_production_requires_keys` is a real regression (not a coverage gap). Separate one-shot fix needed.
