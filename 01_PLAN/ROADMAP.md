# AIFlow Forward Roadmap

> **Status:** ACTIVE — single-source forward queue for `/auto-sprint` and `/next`.
> **Last refreshed:** 2026-04-28 (S93, v1.4.4.6)
> **Owner:** Sprint H consolidation. Subsequent maintainers: update after every session-close.
> **Scope:** This document is a **forward pointer**, not a recipe. Each session prompt
> still lives under `session_prompts/`; this file declares the *order* and *intent*.

---

## How to read this

- Sessions are listed in execution order within each track.
- A session line carries: id, scope summary, primary deliverable, link/anchor.
- "DONE" lines stay in place as anchor (history lives in git + `session_prompts/archive/`).
- When a track finishes, fold it into the relevant tag/PR row at the top of the file.
- `/auto-sprint` consumes the next **non-DONE** session prompt referenced by `NEXT.md`.
  This file does **not** replace `NEXT.md`; it explains what `NEXT.md` will point to next.

---

## Active sprint — v1.4.4 Consolidation (Sprint H)

Branch: `feature/v1.4.4-consolidation` | Base: `v1.4.3-phase-1d` (`0d669aa`).

| Session | Scope | Status |
|---|---|---|
| S88 / v1.4.4.1 | Version reconcile, port doc fix, stale prompt archive, NEXT.md cleanup | DONE |
| S89 / v1.4.4.2 | Frontend dev-env live, journey E2E triage, Untitled UI ADR | DONE |
| S90 / v1.4.4.3 | Journey E2E rerun + contract regressions | DONE |
| S91 / v1.4.4.4 | `test_auth` leak fix, e2e asyncio markers, **coverage roadmap** (HARD STOP) | DONE |
| S92 / v1.4.4.5 | ROADMAP.md + 104_* drift fix + v1.4.4 PR draft | DONE |
| **S93 / v1.4.4.6** | **`test_alembic_034` head-relative (ScriptDirectory), `out/` cleanup + .gitignore, `CLAUDE.md` counts sync** | **IN-PROGRESS** |

**Sprint exit gate:** S93 close → cut `v1.4.4` PR + tag (uses `docs/v1.4.4_pr_description.md`).
After S93, the coverage uplift mini-sprint (S91.A-D) and Phase 1.5 are unblocked in parallel.

---

## Coverage uplift mini-sprint (parallel to v1.4.5)

Source: `out/s91_coverage_plan.md`. Goal: 67.0% → ≥80%, close issue #7, flip gate to `fail_under=80`.

| Session | Target modules | Expected gain |
|---|---|---|
| S91.A | `api/v1/emails.py`, `api/v1/documents.py` (router HTTP tests) | +2.7 p.p. |
| S91.B | `api/v1/rag_engine.py`, `api/v1/pipelines.py`, `api/v1/process_docs.py`, `api/v1/intent_schemas.py` | +2.4 p.p. |
| S91.C | `services/email_connector/service.py`, `services/rag_engine/service.py`, `services/notification/service.py`, `pipeline/runner.py` | +2.8 p.p. |
| S91.D | `vectorstore/pgvector_store.py`, `aiflow.tools/*` decision, auth hardening, gate flip | +2.9..4.6 p.p. |

**Cumulative projection:** 67% → ~76–79% after S91.A-C; S91.D crosses ≥80% and flips gate.

---

## v1.4.5 — Phase 1.5 (Profile A air-gapped ready, Phase 1 closer)

Reference: `01_PLAN/104_AIFLOW_v2_FINAL_MASTER_INDEX.md` §6.4 + §8.4.

| Session | Scope | Acceptance |
|---|---|---|
| S94 | Vault `hvac` prod implementation + token rotation tests | `test_vault_token_rotation.py` PASS |
| S95 | Self-hosted Langfuse Docker + Profile A air-gapped E2E | Full pipeline runs with `cloud_disallowed=true` |

Exit: tag `v1.4.5-phase-1-5`. After S95, **Phase 1 is officially complete** end-to-end.

---

## Phase 2 prep (mandatory before v1.5.0 kickoff)

Pre-work that must close before Phase 2 starts. Each is its own session-pack.

- **PP1** — `100_e_AIFLOW_v2_CAPACITY_PLANNING.md` real GPU bench (replace paper-numbers with measured Qwen25-VL VRAM, BGE-M3 throughput, Docling parse latency on the chosen GPU profile).
- **PP2** — Sign-off the **10 deferred v2 contracts** (see `104_*` §10.3): RoutingDecision v2, ExtractionResult v2, ArchivalArtifact, ReviewTask, ProvenanceRecord, ValidationResult, EmbeddingDecision, PIIRedactionReport, QuarantineItem, CostAttribution. Each contract gets a one-page ADR + Pydantic stub + state-machine sketch before its owning Phase 2 sub-phase starts.
- **PP3** — `100_f_AIFLOW_v2_HITL_WORKLOAD_MODEL.md` review-queue SLA validation against actual review volume from Phase 1 production data.

These three are sequencing constraints, not date constraints. Do not date-stamp.

---

## v1.5.x — Phase 2 (architectural refinement)

Reference: `104_*` §4 phase ordering. Each version = one Phase 2 sub-phase = ~1 sprint.

| Version | Sub-phase | Scope |
|---|---|---|
| v1.5.0 | 2a — Multi-signal routing | PyMuPDF4LLM + Docling provider + RoutingDecision v2 contract activation |
| v1.5.1 | 2b — VLM stack | Docling VLM + Qwen25-VL + vLLM; activates ExtractionResult v2 |
| v1.5.2 | 2c — Embedding providers | BGE-M3 + e5-large + Azure OpenAI + PIIRedactionReport contract |
| v1.5.3 | 2d — Archival | Gotenberg + veraPDF + ArchivalArtifact + QuarantineItem + CostAttribution contracts |
| v1.5.4 | 2e — Acceptance | 10 processing-flow E2E + Profile A/B parity + Phase 2 acceptance matrix |

Exit: tag `v1.5.4-phase-2`. After v1.5.4, **Phase 2 is complete** and the system is feature-complete for the document_pipeline target architecture.

---

## v1.6.x — Phase 3 (governance & ops)

Reference: `104_*` §4. Three sprints. Sequenced after Phase 2 acceptance.

- **v1.6.0** — Audit lineage (N17) + provenance map (N18) + ProvenanceRecord contract activation.
- **v1.6.1** — OTel tracer (N19) + Prometheus metrics (N20) + ValidationResult contract.
- **v1.6.2** — CrewAI bounded sidecar (N22 + N22b experiment) + ReviewTask + EmbeddingDecision contract activation + N23 typer CLI extensions.

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

These do not block any phase but should ride along with the nearest relevant session:

- `tests/e2e/v1_4_1_phase_1b/test_alembic_034.py` head assertion drift (035→037). Owner: S93.
- `out/` log accumulation cleanup (~25 untracked log/json files). Owner: S93.
- `CLAUDE.md` "Key Numbers" sync (test counts, services, endpoints). Owner: S93 + every sprint close.
- Frontend `pages-new/` vs `src/components/` Untitled UI fragmentation — ADR exists (`01_PLAN/ADR-UI-Library.md`); enforcement is per-UI-session.

---

## Pointers

- Master architecture index: `01_PLAN/104_AIFLOW_v2_FINAL_MASTER_INDEX.md`
- Phase 1a guide: `01_PLAN/106_AIFLOW_v2_PHASE_1a_IMPLEMENTATION_GUIDE.md`
- Sprint H kickoff: `01_PLAN/session_S88_v1_4_4_consolidation_kickoff.md`
- Coverage plan: `out/s91_coverage_plan.md`
- DOHA auto-sprint reference: `DOHA/01_PLAN/19_DOHA_AUTO_SPRINT_GUIDE.md`
