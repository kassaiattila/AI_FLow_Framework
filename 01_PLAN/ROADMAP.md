# AIFlow Forward Roadmap

> **Status:** ACTIVE — single-source forward queue for `/auto-sprint` and `/next`.
> **Last refreshed:** 2026-04-26 (Sprint W close + honest alignment audit).
> **Owner:** Sprint X (v1.8.0) and onward. Maintainers: update after every sprint-close.
> **Scope:** Forward pointer, not a recipe. Each session prompt lives under
> `session_prompts/`; this file declares the *order* and *intent*.
>
> **Policy (binding, from `110_USE_CASE_FIRST_REPLAN.md` + `docs/honest_alignment_audit.md`):**
> every sprint must close with **measurable quality improvement on exactly one
> use-case** (UC1 / UC2 / UC3 / DocRecognizer). Architecture / infra work
> rides the use-case it enables; it does not get its own sprint until the 4
> use-cases are all "production-grade" (Sprint Z gate).

---

## How to read this

- Sessions listed in execution order within each sprint.
- Each non-DONE session line carries: id, scope summary, **mandatory quality target metric**.
- "DONE" sprint summary lines stay as anchors (full history in `docs/SPRINT_HISTORY.md`).
- `/auto-sprint` consumes the next non-DONE session prompt referenced by `NEXT.md`.
- This file does **not** replace `NEXT.md`; it explains what `NEXT.md` points to next.

---

## Closed sprints (J → W) — history snapshot

Full per-sprint trajectory: `docs/SPRINT_HISTORY.md`.

| Sprint | Tag | Use-case-zar | Headline |
|---|---|---|---|
| J | v1.4.5-sprint-j-uc2 | UC2 | RAG providers + UnstructuredChunker + MRR@5 0.55 baseline |
| K | v1.4.7 | UC3 | Email intent + 4-test golden path |
| L | v1.4.8 | UC4 monitoring | Cost monitoring + ci-cross-uc 42-test smoke |
| M | v1.4.9 | (drift: infra-only) | Vault hvac + self-hosted Langfuse |
| N | v1.4.10 | (drift: infra-only) | Per-tenant budget + cost preflight guardrail |
| O | v1.4.11 | UC3 | Attachment-aware intent (misclass 56% → 32%) |
| P | v1.4.12 | UC3 | LLM-fallback body/mixed (misclass 32% → 4%) |
| Q | v1.5.0 | UC1 | Intent + extraction unification (85.7% accuracy 10-fixture) |
| R | v1.5.1 | (drift: scaffold-only) | PromptWorkflow scaffold |
| S | v1.5.2 | (drift: infra-only) | Multi-tenant + multi-profile vector DB |
| T | v1.5.3 | (drift: refactor) | PromptWorkflow per-skill consumer migration (byte-stable) |
| U | v1.5.4 | (drift: polish) | Operational hardening (own plan: "zero new functional capability") |
| V | v1.6.0 | DocRecognizer | Generic document recognizer skill (5 doctype synthetic-only) |
| W | v1.7.0 | (drift: polish) | Multi-tenant cleanup + boot guard + Langfuse stub |

**Drift count:** 11 sprints — **6 sprintek (M, N, R, S, U, W) megsertették a
"one use-case per sprint" szabalyt.** Reszletes elemzes:
`docs/honest_alignment_audit.md`.

---

## Active sprint — v1.8.0 "Intake pipeline unification + Professional RAG chat management" (Sprint X)

Branch: `feature/x-sx{N}-*` (per-session) → squash-merge to `main` after each PR.
Plan: `01_PLAN/121_SPRINT_X_INTAKE_PIPELINE_RAG_CHAT_PLAN.md`.
Audit (Sprint W → X handoff): `docs/post_sprint_w_audit.md`.
Goal: zar 3 pipeline-rest Sprint W felfedte de nem dratoltt:
(1) UC3 EXTRACT path hardcode-olt `invoice_processor`-ra → DocRecognizer-mediated
dispatch; (2) nincs routing trace → operator nem latja miert lett egy
doctype valasztva; (3) `/aszf/chat` stateless → professzionalis kezelo
felulet (conversation persistence + persona switcher + cost meter +
transcript export).

> **Operator-directed deviation note.** Sprint X **nem** "one-UC quality
> push" — multi-UC pipeline-unification sprint, mert a 3 gap szorosan
> kapcsolt (UC3 → DocRecognizer routing CSAK akkor megfigyelheto ha a
> trace ship-el; chat persistence CSAK akkor ertelmes ha a routing
> hatasa nyomon kovetheto). A `110_USE_CASE_FIRST_REPLAN.md` policy-tol
> tudatos eltérés, dokumentalva `docs/post_sprint_w_audit.md`-ben.

| Session | Scope | Composite gate | Status |
|---|---|---|---|
| **SX-1** | Post-Sprint-W audit + Sprint X plan + intake-pipeline kickoff (this row) | doc-only deliverables (audit + plan + NEXT + CLAUDE slim merge) | **IN PROGRESS** |
| SX-2 | UC3 → DocRecognizer routing layer (default-off; flag-on `hu_invoice` byte-stable on existing `invoice_processor`; other doctypes route to SW-1 extraction) | UC3 4/4 unchanged (flag-off) + UC1 ≥ 75% / `invoice_number` ≥ 90% (flag-on `hu_invoice`) + id_card ≥ 3 fields confidence ≥ 0.7 (flag-on integration test) | **DONE** (PR #64, 13 unit + 1 integration scaffold, OpenAPI delta = `+ EmailDetailResponse.routing_decision`, all 8 CI green incl. inherited fixes) |
| SX-3 | Routing trace — Alembic 050 `routing_runs` + `RoutingRunRepository` + 3-route `/api/v1/routing-runs` API + `/routing-runs` admin UI | UC3 4/4 + UC1 byte-stable (observation-only writes) + `routing_runs` row written per EXTRACT email + Playwright `routing-runs.md` PASS | **DONE** (Alembic 050, +3 paths/+4 schemas, 21 unit + 2 integration + 1 round-trip + Playwright 3-scenario spec, ruff/tsc clean, 0 surrounding regressions) |
| SX-4 | Professional RAG chat — Alembic 051 `aszf_conversations` + `aszf_conversation_turns` + `ConversationService` + 4-route `/api/v1/conversations` API + additive `/api/v1/aszf/chat` thin wrapper (citations + cost + latency) + `/aszf/chat` UI upgrade (sidebar history + persona switcher + collection picker + citation card + cost meter + transcript export) | UC2 MRR@5 ≥ 0.55 unchanged (`/v1/chat/completions` retrieval API byte-stable; SX-4 surface is purely additive) + Playwright `aszf-chat.md` 4-test spec drafted | **DONE** (Alembic 051 round-trip clean, +4 OpenAPI paths/+5 schemas, 15 unit + 3 integration PASS, ruff/tsc clean, 0 surrounding regressions) |
| SX-5 | Sprint X close + Sprint W follow-up bundle (SW-FU-2 admin UI source-toggle on `/prompts/workflows` + SW-FU-3 `audit_customer_references.py` extension to `skill_instances` / `intent_schemas` / `document_extractor`) + retro + PR description + tag `v1.8.0` queued + NEXT.md → SY-1 | All four UCs unchanged + `bash scripts/run_quality_baseline.sh --strict` UC2 ≥ 0.55 + UC3 ≤ 4% + UC1 ≥ 75% + DocRecognizer 5-doctype ≥ 80% (no-regression gate, not a quality push) | QUEUED |

**Sprint X exit gate:** all four UC golden paths byte-stable +
DocRecognizer-mediated dispatch flag-on green + routing_runs observability
live + `/aszf/chat` conversation persistence live + tag `v1.8.0` queued.
UC2 quality push (MRR@5 ≥ 0.65) explicitly **out of scope** — Sprint Y.

---

## Queued sprint — v1.9.0 "UC2 RAG Depth Push" (Sprint Y)

Branch: `feature/y-sy{N}-*` (cut from `main` after `v1.8.0` tag).
Goal: professzionalis chunkolas + vektor DB menedzsment.

| Session | Scope | Quality target metric |
|---|---|---|
| SY-1 | Semantic chunker (heading-aware + table-preservation) + multilingual HU+EN ProviderRegistry slot | UC2 MRR@5 0.55 → ≥ 0.65 (Profile A BGE-M3) |
| SY-2 | Hybrid search (BM25 + vector RRF) + cross-encoder reranker production wiring | UC2 MRR@5 0.65 → ≥ 0.72 |
| SY-3 | Reembedding workflow (collection re-embed UI + worker) + collection split/merge/rename API + UI | nincs → live + 1 Playwright |
| SY-4 | Per-tenant izolacio E2E test + `aszf_rag_chat` Reflex ingest UI completion | gap → closed |
| SY-5 | Sprint Y close — tag `v1.9.0` + run_quality_baseline.sh PASS | UC2 ≥ 0.72; ingest UI live |

**Sprint Y exit gate:** UC2 MRR@5 ≥ 0.72 Profile A; collection management
Playwright PASS; aszf_rag_chat ingest UI mukodik.

---

## Conditional sprint — v2.0.0 "Phase 3 Ops + Audit" (Sprint Z)

**Csak akkor indul,** ha Sprint X+Y mind zold (4 UC szilardan target felett).
Ha barmely UC nem ert celt → extension sprint indul a leszakadt UC-re,
Sprint Z ujra elhalasztva.

Plan: TBD — Sprint Y close session writes `01_PLAN/123_SPRINT_Z_PHASE_3_OPS_PLAN.md`.

| Tema | Forras-FU | Effort becsules |
|---|---|---|
| OTel tracer + Prometheus metrics | Phase 3 N19/N20, jelen STUB | M |
| Audit lineage + ProvenanceRecord activation | Phase 3 N17/N18 | M |
| Grafana cost panels (`cost_guardrail_refused` vs `cost_cap_breached`) | SN-FU-3 | S |
| Coverage uplift 70% → 80% | SJ-FU-7 | M (cross-cutting) |
| Vault rotation E2E + AppRole IaC | SM-FU-1 + SW-FU-4 | M |
| ci-cross-uc UC1-General slot | (Sprint X SX-3 sets up) | S |

---

## Cross-cutting backlog — STRICT-DEFERRED

Az alabbi follow-up ID-k explicit nincsenek Sprint X scope-ban, **ne keruljenek be
session-prompt-okba** kivéve, ha kozvetlenul a 4 UC valamelyikene melyitenek.

| ID | Topic | Indok |
|---|---|---|
| SW-FU-1 | Langfuse v4 list-by-prefix SDK helper | SDK-fuggo, Sprint Z scope |
| SW-FU-2 | Admin UI source-toggle widget /prompts/workflows | UI polish, halasztva |
| SW-FU-3 | audit_customer_references.py kiterjesztes masik tablakra | multi-tenant cleanup folytatas, Sprint Z |
| SW-FU-4 | Vault AppRole IaC E2E test | infra, Sprint Z |
| SV-FU-2 | UI bundle size guardrail | CI polish, halasztva |
| SV-FU-5 | Monaco editor for DocTypeDetailDrawer | nice-to-have, halasztva |
| SU-FU-2 | scripts/ ruff cleanup | code hygiene |
| SU-FU-3 | Alembic invoice_date SQL column rename | nincs funkcionalis nyomas |
| SS-SKIP-2 | Profile B Azure live MRR@5 | blocked: Azure credit pending |
| SO-FU-2/6/7 | UC3 minor follow-ups | beolvad SX-4-be |

**Az alabbiak Sprint X scope-ban — felulkulonbozteto a fenti listatol:**

| ID | Topic | Sprint X session |
|---|---|---|
| Sprint W gap §1 | UC3 EXTRACT hardcode-olt `invoice_processor`-ra | **SX-2** (DocRecognizer-mediated dispatch) |
| Sprint W gap §2 | Nincs routing trace | **SX-3** (Alembic 050 `routing_runs` + admin UI) |
| Sprint W gap §3 | `/aszf/chat` stateless API | **SX-4** (Alembic 051 conversations + UI upgrade) |
| SW-FU-2 | Admin UI source-toggle widget /prompts/workflows | **SX-5** (Sprint W follow-up bundle) |
| SW-FU-3 | `audit_customer_references.py` kiterjesztes masik tablakra | **SX-5** (Sprint W follow-up bundle) |

**Sprint Y-re halasztva** (eredeti Quality Push tervekbol carry-forward):

| ID | Topic | Indok |
|---|---|---|
| SQ-FU-3 | UC1 corpus extension to 25 fixtures | UC1 quality push, Sprint Y or operator ad-hoc |
| SW-FU-5 / SV-FU-1 | DocRecognizer real-document fixture corpus | operator-driven anonymization |
| SP-FU-1 | UC3 `024_complaint` body-vs-attachment | UC3 quality push, Sprint Y |
| SP-FU-3 | UC3 thread-aware classifier | architecture sprint, Sprint Y or Z |

---

## Pointers

- Honest alignment audit: `docs/honest_alignment_audit.md`
- Use-case-first replan (binding policy): `01_PLAN/110_USE_CASE_FIRST_REPLAN.md`
- Sprint X plan: `01_PLAN/121_SPRINT_X_INTAKE_PIPELINE_RAG_CHAT_PLAN.md`
- Sprint X audit (operator-directed deviation rationale): `docs/post_sprint_w_audit.md`
- Sprint history (J–W trajectory): `docs/SPRINT_HISTORY.md`
- Master architecture index: `01_PLAN/104_AIFLOW_v2_FINAL_MASTER_INDEX.md`
- Session-prompt template: `session_prompts/_TEMPLATE.md`
- Quality baseline script: `scripts/run_quality_baseline.sh`
