# AIFlow Forward Roadmap

> **Status:** ACTIVE — single-source forward queue for `/auto-sprint` and `/next`.
> **Last refreshed:** 2026-04-28 (S93 close + use-case-first replan).
> **Owner:** Sprint I (v1.4.5) and onward. Maintainers: update after every session-close.
> **Scope:** Forward pointer, not a recipe. Each session prompt lives under
> `session_prompts/`; this file declares the *order* and *intent*.
>
> **Policy (new, from `110_USE_CASE_FIRST_REPLAN.md`):** every sprint from v1.4.5
> must close with exactly one end-user use-case going end-to-end green. Architecture
> work rides the use-case it enables; it does not get its own sprint.

---

## How to read this

- Sessions listed in execution order within each sprint.
- A session line carries: id, scope summary, status.
- "DONE" lines stay as anchors (history in git + `session_prompts/archive/`).
- `/auto-sprint` consumes the next **non-DONE** session prompt referenced by `NEXT.md`.
- This file does **not** replace `NEXT.md`; it explains what `NEXT.md` points to next.

---

## Closed sprint — v1.4.4 Consolidation (Sprint H)

Branch: `feature/v1.4.4-consolidation` | Base: `v1.4.3-phase-1d` (`0d669aa`).
Status: **SCOPE DONE (S88–S93). PR cut + tag `v1.4.4` pending user approval.**

| Session | Scope | Status |
|---|---|---|
| S88 / v1.4.4.1 | Version reconcile, port doc fix, stale prompt archive, NEXT.md cleanup | DONE |
| S89 / v1.4.4.2 | Frontend dev-env live, journey E2E triage, Untitled UI ADR | DONE |
| S90 / v1.4.4.3 | Journey E2E rerun + contract regressions | DONE |
| S91 / v1.4.4.4 | `test_auth` leak fix, e2e asyncio markers, coverage roadmap (HARD STOP) | DONE |
| S92 / v1.4.4.5 | ROADMAP.md + 104_* drift fix + v1.4.4 PR draft | DONE |
| S93 / v1.4.4.6 | `test_alembic_034` head-relative (ScriptDirectory) + `out/` cleanup + CLAUDE.md sync + **use-case-first replan authored** (`110_*`) | DONE |

**Sprint exit gate:** v1.4.4 PR open + merge + tag. After tag, `feature/v1.4.5-doc-processing`
is cut from `main` and Sprint I begins with S94.

---

## Active sprint — v1.4.5 "Document processing usable" (Sprint I)

Branch: `feature/v1.4.5-doc-processing` (cut from `main` after `v1.4.4` tag).
Plan: `01_PLAN/110_USE_CASE_FIRST_REPLAN.md` §4 Sprint I.

| Session | Scope | Status |
|---|---|---|
| **S94 / v1.4.5.1** | `DocumentExtractorService.extract_from_package()` impl (replaces `NotImplementedError`) + Docling standard pipeline wired as default extractor + PolicyEngine gate | **QUEUED** |
| S95 / v1.4.5.2 | `RoutingDecision` Pydantic stub + `MultiSignalRouter` + Alembic 038 + Unstructured + Docling std registered as `ParserProvider` impls | QUEUED |
| S96 / v1.4.5.3 | Azure DI parser (Profile B gated) + PII redaction gate v0 | QUEUED |
| S97 / v1.4.5.4 | UI: `DocumentDetail` parser badge + extraction JSON + Langfuse trace link. `Prompts.tsx` v1 read-only | QUEUED |
| S98 / v1.4.5.5 | Golden-path E2E (3 test docs, 1 per parser path) + `/regression` + `/lint-check` + PR + tag `v1.4.5` | QUEUED |
| SI.H1 (issue [#12](https://github.com/kassaiattila/AI_FLow_Framework/issues/12)) | **CI infra housekeeping** — `alembic/env.py` reads `AIFLOW_DATABASE__URL` env var first, falls back to INI. Unmasked by v1.4.4 coverage waiver; `integration-tests` job red on PR CI until fixed. Single-session; schedule as prerequisite for S94 if Docling integration tests need it, otherwise between S94 and S95. | QUEUED |

**Sprint exit gate:** upload real PDF in admin UI → see parser badge + extraction JSON + clickable Langfuse trace.

---

## Queued sprint — v1.4.6 "RAG chat usable" (Sprint J)

Branch: `feature/v1.4.6-rag-chat` (cut from `main` after `v1.4.5` tag).
Plan: `01_PLAN/110_USE_CASE_FIRST_REPLAN.md` §4 Sprint J.

| Session | Scope |
|---|---|
| S99 / v1.4.6.1 | `EmbedderProvider` abstraction: BGE-M3 (Profile A) + Azure OpenAI text-embedding-3-small (Profile B) + `EmbeddingDecision` contract + Alembic 039 |
| S100 / v1.4.6.2 | `UnstructuredChunker` as RAG ingest step, replaces hardcoded path |
| S101 / v1.4.6.3 | UI: `Rag` chunk viewer + embedding-model badge + retrieval metrics panel |
| S102 / v1.4.6.4 | PII redaction gate between Chunker and Embedder + `PIIRedactionReport` stub |
| S103 / v1.4.6.5 | Golden-path E2E (collection-ingest → chat → citations) + PR + tag `v1.4.6` |

---

## Queued sprint — v1.4.7 "Email intent usable" (Sprint K)

Branch: `feature/v1.4.7-email-intent` (cut from `main` after `v1.4.6` tag).
Plan: `01_PLAN/110_USE_CASE_FIRST_REPLAN.md` §4 Sprint K.

| Session | Scope |
|---|---|
| S104 / v1.4.7.1 | `EmailSource` → `IntakePackageSink` → `IntentClassifier` glue (adapter exists from Phase 1d) |
| S105 / v1.4.7.2 | `IntentRoutingPolicy` per tenant (notify / extract / archive / manual review) via PolicyEngine |
| S106 / v1.4.7.3 | UI: `Emails` scan button + intent badge + routing chip + trace link |
| S107 / v1.4.7.4 | `Prompts.tsx` v2: edit Langfuse-synced prompts from UI (round-trip PUT + read-back) |
| S108 / v1.4.7.5 | Golden-path E2E (mailbox scan → 3 emails → intents + routing) + PR + tag `v1.4.7` |

---

## Queued sprint — v1.4.8 "Cross-cutting monitoring + cost" (Sprint L, 1 week)

Branch: `feature/v1.4.8-monitoring-cost` (cut from `main` after `v1.4.7` tag).
Plan: `01_PLAN/110_USE_CASE_FIRST_REPLAN.md` §4 Sprint L.

| Session | Scope |
|---|---|
| S109 / v1.4.8.1 | `Runs.tsx` + `Monitoring.tsx`: Langfuse drill-down (trace tree, step timings, token counts) |
| S110 / v1.4.8.2 | `Costs.tsx` + `CostAttribution` stub + PolicyEngine cost-cap enforced at Extractor + Embedder (429 on breach) |
| S111 / v1.4.8.3 | Playwright regression pack (UC1 + UC2 + UC3 together) + PR + tag `v1.4.8` |

**Sprint exit gate:** v1.4.8 ship-ready — 3 use-cases production-usable, monitored, cost-capped, prompts admin-editable.

---

## v1.4.9 — Vault prod + self-hosted Langfuse

Deferred from old v1.4.5 (0.5-sprint estimate was wrong — full standalone sprint needed).
Branch: `feature/v1.4.9-vault-langfuse-selfhost`.

| Session | Scope | Acceptance |
|---|---|---|
| S112 | Vault `hvac` prod client + token rotation + `test_vault_token_rotation.py` | Vault dev + prod profile tested with real Vault container |
| S113 | Self-hosted Langfuse Docker + Profile A air-gapped E2E | Full UC1 pipeline runs with `cloud_disallowed=true` and zero outbound cloud calls |
| S114 | PR + tag `v1.4.9-phase-1-5`. **Phase 1 officially complete end-to-end.** | — |

---

## v1.5.x — Phase 2 (architectural refinement)

Reference: `104_*` §4 phase ordering. Each version = one Phase 2 sub-phase ≈ 1 sprint.
Sequencing policy: Phase 2 sub-phase kicks off **only after** its enabling pre-work spike (PP0) is green.

| Version | Sub-phase | Scope |
|---|---|---|
| v1.5.0 | 2a — VLM hard-case fallback | Docling VLM + Qwen25-VL + vLLM registered as `ParserProvider`; router picks VLM when OCR-conf below threshold |
| v1.5.1 | 2b — Embedding provider variety | e5-large registered alongside BGE-M3 + Azure OpenAI; EmbeddingDecision v2 upgrade |
| v1.5.2 | 2c — Archival | Gotenberg + veraPDF + `ArchivalArtifact` + `QuarantineItem` + `CostAttribution` upgrade |
| v1.5.3 | 2d — Acceptance | 10 processing-flow E2E + Profile A/B parity + Phase 2 acceptance matrix |

Exit: tag `v1.5.3-phase-2`. After v1.5.3, **Phase 2 is complete** and the system is feature-complete for the target processing architecture.

**PP0 (pre-work spike, blocks each Phase 2 sprint):** for each new provider (Qwen25-VL, e5-large, Gotenberg, veraPDF), 1-day sandbox + contract ADR + capacity bench **before** the Phase 2 sub-sprint plans that provider.

---

## v1.6.x — Phase 3 (governance & ops)

Reference: `104_*` §4. Sequenced after Phase 2 acceptance.

- **v1.6.0** — Audit lineage (N17) + provenance map (N18) + `ProvenanceRecord` contract activation.
- **v1.6.1** — OTel tracer (N19) + Prometheus metrics (N20) + `ValidationResult` contract.
- **v1.6.2** — CrewAI bounded sidecar (N22 + N22b experiment) + `ReviewTask` + `EmbeddingDecision` v2 + N23 typer CLI extensions.

Exit: tag `v1.6.2-phase-3`. After v1.6.2, **Phase 3 closes** and the platform is ops-ready.

---

## v2.0.0+ — Phase 4 (optional)

Not committed; activated only if business case lands.

- N24 Microsoft LazyGraphRAG.
- N25 Kafka event bus.
- Multi-tenant SaaS hardening (per-tenant rate limiting, billing pipeline).
- Azure AI Search vector store as alternative to pgvector.

---

## Cross-cutting backlogs

Reassessed S93-close (many prior items were stale or already solved):

- **`aiflow-admin` Untitled UI fragmentation** — ADR `01_PLAN/ADR-UI-Library.md` binding; per-UI-session enforcement.
- **LangChain opt-in scope** — max 3 importers (classifier, extractor, prompt-template helper). Re-audit at v1.4.8 tag cut.
- **§10.3 deferred contracts** — 7 remain after v1.4.8 (see `110_*` §5). Each lands in its owning Phase 2/3 sub-sprint.
- **Coverage gate flip** — from `fail_under=67` to `fail_under=80`. Target: v1.4.8 tag. Drivers: new tests per sprint already push coverage up; S91.A–D coverage mini-sprint no longer standalone, absorbed into the sprint-by-sprint new-test target.

**Retired (done or obsolete):**
- ~~`test_alembic_034` head assertion drift~~ — DONE S93.
- ~~`out/` log accumulation cleanup~~ — DONE S93.
- ~~`CLAUDE.md` key-numbers sync~~ — DONE S93, enforced every sprint close going forward.
- ~~S91.A–D coverage mini-sprint~~ — absorbed into sprint-by-sprint new-test targets.

---

## Pointers

- Use-case-first replan: `01_PLAN/110_USE_CASE_FIRST_REPLAN.md`
- Master architecture index: `01_PLAN/104_AIFLOW_v2_FINAL_MASTER_INDEX.md`
- Phase 1a implementation guide (done): `01_PLAN/106_AIFLOW_v2_PHASE_1a_IMPLEMENTATION_GUIDE.md`
- Sprint H kickoff (done): `01_PLAN/session_S88_v1_4_4_consolidation_kickoff.md`
- DOHA auto-sprint reference: `DOHA/01_PLAN/19_DOHA_AUTO_SPRINT_GUIDE.md`
