# Sprint J — Retrospective (v1.4.6 UC2 RAG chat)

> **Sprint window:** 2026-04-22 → 2026-04-25 (5 sessions, S100 → S104)
> **Branch:** `feature/v1.4.6-rag-chat`
> **Tag:** `v1.4.5-sprint-j-uc2` (cut at S104 PR merge)
> **PR:** opened at S104 against `main` — see `docs/sprint_j_pr_description.md`
> **Predecessor:** `v1.4.3-phase-1d` (Phase 1d MERGED 2026-04-24, PR #9 / `0d669aa`)
> **Plan reference:** `01_PLAN/110_USE_CASE_FIRST_REPLAN.md` §4 Sprint J

## Scope delivered

UC2 RAG ingest path refactored onto the shared `Parser → Chunker → Embedder` flow with a
multi-profile provider abstraction, pgvector flex-dim storage, and a live retrieval baseline
proving both Profile A (air-gapped BGE-M3) and Profile B (cloud OpenAI) clear MRR@5 ≥ 0.55 on a
bilingual corpus. Admin UI `Rag` page now renders the new chunk provenance end-to-end.

| Session | Commit | Deliverable |
|---|---|---|
| **S100** | `9b3c610` | `EmbedderProvider` ABC + BGE-M3 (Profile A) + Azure OpenAI (Profile B) + `EmbeddingDecision` contract + Alembic 040 + `PolicyEngine.pick_embedder`. |
| **S101** | `953e7cd` | `ChunkResult` contract + `ChunkerProvider` ABC (5th registry slot) + `UnstructuredChunker` (tiktoken cl100k_base, 512/50) + rag_engine opt-in provider-registry ingest path + Alembic 041 `rag_chunks.embedding_dim`. |
| **S102** | `37d5ba7` | UC2 RAG UI — `ChunkViewer` (paginated + embedding_dim badge + modal) + `GET /collections/{id}/chunks` provenance fields (chunk_index, token_count, embedding_dim, metadata) + 3 Playwright E2E. |
| **S103** | `fa6324a` | Retrieval baseline — Alembic 042 pgvector flex-dim (widen `vector` + add `rag_collections.embedding_dim`) + `OpenAIEmbedder` (Profile B surrogate) + `scripts/bootstrap_bge_m3.py` + live `test_retrieval_baseline.py` (MRR@5 ≥ 0.55 both profiles) + reranker OSError fallback hardening. |
| **S104** | _(this commit)_ | Sprint J close — resilience flake quarantine + `docs/quarantine.md` + `docs/sprint_j_retro.md` + plan + CLAUDE.md update + PR description + PR cut + tag. |

## Test deltas

| Suite | Before (Phase 1d tip) | After (Sprint J tip) | Delta |
|---|---|---|---|
| Unit | 1898 | 1994 | **+96** (embedder/chunker providers, contracts, PolicyEngine, alembic up/down) |
| Integration | 42 | 55+ | **+13+** (alembic 040/041/042, rag_engine UC2 end-to-end) |
| E2E collected | 410 | 413 | **+3** (UC2 RAG S102 Playwright) |
| Alembic migrations | 40 (head: 040 planned) | 42 (head: **042**) | **+2** (041, 042) |
| OpenAPI drift | — | ChunkItem + 4 fields in S102; none in S103/S104 | Snapshotted |

## Contracts + architecture delivered

- **`EmbedderProvider` ABC** — normalized surface (`embedding_dim`, `model_name`), 3 impls: `BGEM3Embedder` (local 1024-dim), `AzureOpenAIEmbedder` (1536), `OpenAIEmbedder` (1536, Profile B surrogate).
- **`ChunkerProvider` ABC** — 5th slot on `ProviderRegistry`; `UnstructuredChunker` shipped.
- **`ChunkResult` + `EmbeddingDecision`** Pydantic v1 contracts — extra=forbid, Literal profile `A`/`B`, exported from `aiflow.contracts`.
- **`PolicyEngine.pick_embedder(tenant_id, profile)`** — provider selection with `tenant_overrides['embedder_provider']`, alias registry includes `bge-m3`, `azure-openai`, `openai`; emits `policy_engine.embedder_selected` structlog event.
- **pgvector flex-dim strategy (Strategy B)** — `rag_chunks.embedding` widened to `vector` (unbounded dim); `rag_collections.embedding_dim` column records the collection's committed dim (default 1536). Ingest updates dim on empty collection, errors on non-empty mismatch.
- **Rag UI wiring** — `ChunkViewer.tsx` replaces inline `ChunksTab`; i18n keys for hu/en; row-click modal shows full chunk text + pretty-printed metadata.
- **Retrieval-quality gate** — live `test_retrieval_baseline.py` enforces MRR@5 ≥ 0.55 for both profiles against `tests/fixtures/rag/baseline_2026_04_25.json` (10 gold Q/A, hu+en, UUIDv5 ids).

## Key numbers (Sprint J tip)

```
27 service | 181 endpoint | 50 DB tabla | 42 Alembic migration (head: 042)
1994 unit PASS / 1 skip (1 xfail after S104 quarantine, still XPASS in isolation)
55+ integration PASS (incl. 5 rag_engine UC2 + 3 alembic 040/041/042)
413 E2E collected (+3 UC2 S102)
0 ruff error | 0 ts error | OpenAPI snapshot clean after S104 regen
Branch: feature/v1.4.6-rag-chat (9 commit ahead of main: 5 feat + 4 chore)
```

## What worked

- **Provider-registry opt-in switch (S101 `use_provider_registry=True`).** Keeping the legacy hardcoded `text-embedding-3-small` ingest path untouched while the new `Parser → Chunker → Embedder` path landed behind a kwarg meant we could merge 5 sessions without breaking the existing `query()` surface or any skill that still talks to the old embedder. Follow-up is needed to retire the old path, but the bridge was the right call for Sprint J scope.
- **`set_embedder_provider_override()` test hook (S101).** Unit + integration tests exercise the full flow with a fake 1536-dim embedder without requiring BGE-M3 weights (500MB) or Azure credits. Production code path is unchanged — the hook is a dev-only registry override, asserted off in live-baseline runs.
- **pgvector Strategy B (flex-dim, S103).** Rather than one collection-per-model, we widened the `vector` column and tracked dim per collection. Collection-scoped dim validation catches the 1024↔1536 mismatch at ingest time, and existing 1536-dim data keeps working (empty collections auto-adopt the ingest dim).
- **OpenAIEmbedder as Profile B surrogate (S103).** Azure OpenAI credits weren't available; rather than skip the baseline, we shipped a separate `OpenAIEmbedder` (same model, same 1536-dim, OAI endpoint) so the MRR@5 gate runs against a real embedding model. Azure variant remains the canonical Profile B — surrogate is for CI cost-gating.
- **Bilingual baseline corpus (S103).** hu+en gold Q/A with UUIDv5 ids → deterministic fixture, reproducible across runs. MRR@5 ≥ 0.55 is a conservative floor (both profiles cleared it comfortably).
- **ChunkViewer E2E uses `data-testid` (S102).** Playwright tests target `data-testid="chunk-viewer"` + `data-testid="chunk-row-{id}"` hooks, surviving visual redesign. Same pattern as Phase 1d adapter E2E.
- **PR-description-one-session-ahead pattern (from Phase 1d retro).** Session S103 left detailed commit-body notes that fed directly into S104's `docs/sprint_j_pr_description.md` without a second investigation pass.

## What surprised us

- **`sentence-transformers` was a non-trivial install (S103).** BGE-M3 weights are 3.7GB and the package pulls in CUDA-aware wheels; baseline CI will need a model cache volume or a `bootstrap_bge_m3.py` preload step (shipped). Added `.cache/` to `.gitignore` to prevent accidental commit.
- **`_rerank_cross_encoder` broke unrelated tier3 tests.** After installing sentence-transformers, the reranker eagerly tried to download a cross-encoder model at import time, failing with `OSError` in air-gapped CI. Fix: catch the `OSError` and fall back to the simple scoring path. Lesson: lazy model loads must have an exception-path fallback, not just a try/except wrapping.
- **`CollectionInfo` → OpenAPI drift that wasn't.** S103 added `embedding_dim` to the internal Pydantic model, but the admin-facing schema already projected this field as-is (pass-through in router), so no OpenAPI drift appeared — confirmed by S104 regen. Worth the regen anyway as belt-and-braces.
- **Resilience test flake surfaced in full-suite runs after Sprint I/J load increase.** `test_circuit_opens_on_failures` relies on a 50ms `circuit_recovery_timeout_seconds`; under heavy parallel test load the `utcnow()` drift occasionally tripped the recovery window mid-loop. Isolation PASS. Root cause: `ResilienceService` uses wall-clock `datetime.utcnow()` with unit-scale thresholds — fragile. Quarantined with `@pytest.mark.xfail(strict=False)` at S104; root-cause fix (Clock seam) queued for Sprint K.
- **`query()` did not adopt the provider registry.** S101's opt-in switch was ingest-only; the read path (`rag_engine.query()`) still instantiates the legacy `Embedder` class. Consequence: a 1024-dim BGE-M3 collection is ingestable but not currently query-able through the public API. Caught during retro review (not S103). Queued as follow-up.

## What we'd change

- **Land PII redaction earlier.** The replan §4 listed S102 as PII redaction; we re-prioritized toward the UI + retrieval baseline because without live MRR numbers the sprint couldn't prove UC2 was "usable" (per §8 criterion). PII gate slips to Sprint K (fold into UC3 since the redactor is shared).
- **`query()` should have been refactored in the same session as the ingest switch (S101).** Splitting read + write across sessions left a half-finished API surface (ingest provider-aware, query legacy-only). Lesson: when flipping a provider registry, do the round-trip in one session even if it stretches scope.
- **BGE-M3 bootstrap should run in CI, not at live-test time.** `scripts/bootstrap_bge_m3.py` pre-warms `.cache/models/bge-m3` but isn't a CI step yet — first CI run that tries the live baseline would cold-download 3.7GB. Add as a cached artifact in Sprint K CI config.
- **Reranker model preload missing.** Parallel to BGE-M3: the cross-encoder model also needs a `bootstrap_reranker.py` so the fallback path isn't the default.
- **Resilience wall-clock design.** Testing-rules policy says "never mock the DB," but the opposite mistake is using wall-clock time where a `Clock` seam would give deterministic tests. Clock abstraction should land in Sprint K as part of resilience fix.

## Decisions log

| # | Decision | Alternative considered | Rationale |
|---|---|---|---|
| SJ-1 | **pgvector Strategy B (flex-dim column) over Strategy A (one collection-per-model).** | Strategy A: separate `rag_chunks_1024` / `rag_chunks_1536` tables per dim. | Strategy B is one schema, one migration path, dim tracked per row via collection FK. Avoids fan-out in the ingest router and keeps cross-model retrieval possible later. |
| SJ-2 | **`OpenAIEmbedder` as Profile B surrogate, not a replacement.** | Skip Profile B baseline altogether until Azure credits land. | MRR@5 gate needed to pass; OAI endpoint uses the same `text-embedding-3-small` model + 1536-dim as Azure, making the baseline semantically equivalent. Azure stays canonical for tenant policy. |
| SJ-3 | **`sentence-transformers` as an optional `local-models` extra.** | Default install. | 3.7GB weights + CUDA wheels unsuitable for lean CI or Profile B-only tenants. Profile A users opt in via `uv sync --extra local-models` + `bootstrap_bge_m3.py`. |
| SJ-4 | **Provider-registry ingest behind `use_provider_registry=True` kwarg, not a hard swap.** | Delete legacy path in S101. | Allowed 5 sessions to merge without touching `query()` or external callers; technical debt is visible and tracked (see follow-ups). |
| SJ-5 | **Resilience flake quarantined with `xfail(strict=False)`, not deleted.** | Delete the test. | Test still exercises the circuit-opens semantic; xfail keeps run data flowing. Per `tests/CLAUDE.md`: never delete flaky tests, fix within 5 days. |

## Follow-up issues (filed into Sprint K backlog)

1. **`query()` collection-scoped embedder selection.** The read path still uses legacy `Embedder`; 1024-dim collections aren't queryable via the public API. Refactor `rag_engine.query()` to look up the collection's committed `embedding_dim`, fetch the matching provider via `PolicyEngine.pick_embedder()`, and embed the query with it. **Owner:** rag_engine. **Target:** Sprint K S105 or S107.
2. **Reranker model preload script + CI artifact.** Mirror `bootstrap_bge_m3.py` for the cross-encoder model so `_rerank_cross_encoder` is the default, not the OSError fallback. **Owner:** reranker.
3. **Azure OpenAI Profile B live test.** Replace OpenAI surrogate with Azure-credit live run once Azure credits are provisioned. No code change in `AzureOpenAIEmbedder` — just add `AIFLOW_AZURE_OPENAI__*` to the baseline env and assert MRR@5 ≥ 0.55.
4. **Resilience `Clock` seam + test quarantine removal.** Inject a `Clock` protocol (`time.monotonic` default) into `ResilienceService`; tests advance time deterministically; remove `xfail` on `test_circuit_opens_on_failures`. **Deadline:** 2026-04-30 (5-day quarantine policy).
5. **BGE-M3 weight cache as CI artifact.** Cache `.cache/models/bge-m3` across CI runs; add a `cache miss → run bootstrap_bge_m3.py` guard.
6. **PII redaction gate (deferred from S102).** Regex v0 between Chunker and Embedder, persist `PIIRedactionReport`. Fold into Sprint K UC3 since redactor is shared with email intent.
7. **Coverage uplift (issue #7, still open).** Phase 1d deferred 65.67% → 80%. Sprint J added ~1200 LOC of test code but overall coverage delta not yet measured. Measure at Sprint K start and plan the uplift trajectory per replan §7 target (≥70% by v1.4.5 end, ≥75% by v1.4.7 end).

## Process notes

- **Auto-sprint loop completed cleanly across S100 → S104**: each session closed with `/session-close`, NEXT.md regenerated, next session fired on `ScheduleWakeup ~90s`. No cap trips.
- **Session S103 used live baselines + cost-gated env var** (`AIFLOW_RUN_LIVE_RAG_BASELINE=1`): costs ~$0.001 per run on Profile B. Default CI skips live.
- **OpenAPI snapshot regen happened at S102 (drift landed) and S104 (belt-and-braces post-S103)** — zero drift at S104 confirms `CollectionInfo.embedding_dim` was already pass-through in the router.
