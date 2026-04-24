# AIFlow v1.5.2 Sprint S — Functional vector DB teljes kör

> **Status:** KICKOFF on 2026-05-15 (S143).
> **Branch:** `feature/s-s{N}-*` (each session its own branch → PR → squash-merge).
> **Parent plan:** `01_PLAN/114_CAPABILITY_ROADMAP_Q_R_S.md` §4.
> **Predecessor:** v1.5.1 Sprint R (PromptWorkflow foundation MERGED `ffd7618`, tag `v1.5.1`).
> **Target tag (post-merge):** `v1.5.2`.

---

## 1. Goal

Zárd le a Sprint J legrégebbi carry-forwardját: a `RagEngineService.query()` ma hardcoded `self._embedder`-rel dolgozik, ezért az 1024-dim BGE-M3 Profile A kollekciók ingestálhatóak, de **query-n keresztül nem elérhetőek**. Sprint S a query-path-ot ProviderRegistry-alapúvá teszi, feloldja az 1024-dim kollekciók lekérdezhetőségét, bevezet egy per-tenant kollekció-regisztert (`rag_collections.tenant_id` + `embedder_profile_id`), és felépít egy heti MRR@5 dashboard-ot, hogy a retrieval minőség regresszió látható legyen CI-szinten.

## 2. Sessions

### S143 — Query-path ProviderRegistry refactor + Alembic 046 (THIS SESSION)
**Scope.** Alembic 046 additív: `rag_collections.tenant_id TEXT NOT NULL DEFAULT 'default'` + `rag_collections.embedder_profile_id TEXT NULL` + `ix_rag_collections_tenant_id`. `RagEngineService.query()` új `_resolve_query_embedder(coll)` helper-t kap: NULL profile → `self._embedder` fallback (backward-compat), regisztrált profile → `ProviderRegistry.get_embedder(profile_id)`, ismeretlen profile → `UnknownEmbedderProfile` (`AIFlowError`, `is_transient=False`) → `QueryResult.answer` hibaüzenettel tér vissza (nem dobás, meglévő `try/except` mintával). 2 Alembic integration + 1 live-stack integration (1024-dim queryability, BGE-M3 weight skip-guard-dal) + 8-12 unit teszt.

### S144 — Admin UI `/rag/collections` per-tenant lista
**Scope.** `ui-journey → ui-api-endpoint → ui-design → ui-page` 7 gate. Új page `aiflow-admin/src/pages/rag-collections/` — table: collection name, tenant_id, embedder_profile_id, chunk_count, embedding_dim, updated_at. Per-tenant filter (`?tenant=` deep-link). 3 GET endpoint (`/api/v1/rag/collections`, `/api/v1/rag/collections/{id}`, `/api/v1/rag/collections/{id}/set-profile`). EN+HU locale. 1 Playwright E2E live-stack-en. 0 Alembic.

### S145 — Scheduled nightly MRR@5 job + Grafana panel
**Scope.** `scripts/measure_mrr_at_5.py` — pick up all collections tagged `embedder_profile_id IS NOT NULL`, run fixture query corpus, emit `rag.mrr_at_5{profile=...}` Prometheus metric. APScheduler 4.x job in `src/aiflow/execution/scheduler.py`, default 03:00 local. `docs/rag_mrr_at_5_dashboard.md` + Grafana panel JSON export. CI weekly matrix (GitHub Action cron) — alert ha MRR@5 < 0.55 egy sprinten át.

### S146 — Sprint S close
**Scope.** `docs/sprint_s_retro.md`, `docs/sprint_s_pr_description.md`, CLAUDE.md bump, PR + tag `v1.5.2`. Explicit skipped-items list (S143 pytest.skip BGE-M3 gate, Profile B credit-pending).

## 3. Success metrics

| Metric | Target |
|---|---|
| 1024-dim BGE-M3 Profile A kollekció end-to-end queryable | ✅ integration test (S143, skip-guard-dal) |
| Sprint J UC2 MRR@5 Profile A baseline | ≥ 0.55 **változatlan** |
| MRR@5 Profile B (Azure OpenAI) | mérés, nem gate — credit függő |
| UC2 `aszf_rag_chat` golden-path | zöld (baseline + mentor + expert role) |
| Új integration teszt | ≥ 4 (S143 3 db + S144 1 db live-stack Playwright) |
| Új unit teszt | ≥ 25 (S143 ~12 + S144 ~8 + S145 ~5) |
| Új Alembic migráció | 1 (046, additív) |
| Új endpoint / router | 3 / 1 (S144) |

## 4. STOP conditions (HARD)

1. UC2 MRR@5 Profile A < 0.55 bármelyik session végén → halt + rollback.
2. Sprint K UC3 golden-path 4/4 regresszió (BGE-M3 weight share-elés miatt) → halt.
3. `alembic upgrade head` vagy `downgrade -1` failel 046-on → halt.
4. `ProviderRegistry.get_embedder` ABC kontraktusa instabil (runtime TypeError) → halt + refactor önálló sprintbe.
5. `gh pr create` credentials hiány autonomous loop-ban → halt, user beavatkozás.

## 5. Rollback

- 046 additív — `alembic downgrade -1` egy lépés, 2 oszlop + index drop.
- `query()` refactor **flag-mentes**, de **NULL fallback**-del kompatibilis → meglévő kollekciók (nincs `embedder_profile_id`) 100% változatlanul viselkednek.
- S144 UI flag-mentes, de önálló page — revert egyetlen commit-on.
- S145 scheduled job opt-in config (`AIFLOW_MRR_SCHEDULER__ENABLED=false` default) — zero-impact disable.

## 6. Out of scope

- Hybrid search weighting tuning (külön sprint).
- Reranker modell csere (Sprint J carry: reranker preload script — külön follow-up).
- Multi-dim collection join / cross-collection query.
- Azure OpenAI Profile B live IaC — credit függő, S145 csak a mérési infrát építi.
- S141-FU-1/2/3 skill migrációk (PromptWorkflow) — független follow-up track, Sprint S után ütemezve.

## 7. Carry forward (Sprint J → Sprint S close)

Sprint J retro (`docs/sprint_j_retro.md`) open follow-ups közül:
- **FU-1 query-path provider registry** → **S143-ban zárul**.
- BGE-M3 weight cache as CI artifact → **S145 CI weekly matrix feltétele**, explicit skipped-item S143-ban.
- Azure OpenAI Profile B live → **S145 mérés, nem gate** (credit blokkolt).
- Reranker model preload script → **out of scope**, következő sprint U.
- Resilience `Clock` seam (quarantine fix deadline 2026-04-30, **15 nap túllépett**) → Sprint U hardening sprintbe átütemezve.

## 8. Skipped items tracker (S143 → S146)

Session-close minden session-ben köteles enumerálni + explicit unskip-feltétel:

| ID | Session | Item | Unskip feltétel |
|---|---|---|---|
| SS-SKIP-1 | S143 | 1024-dim BGE-M3 integration test `pytest.skip` ha weight nincs helyi cache-ben | Weight preload CI step landol (Sprint J FU carry → S145) |
| SS-SKIP-2 | S143 | Profile B (Azure OpenAI) MRR@5 mérés | Azure OpenAI credit elérhető |
| *TBD* | S144+ | *(append during execution)* | — |
