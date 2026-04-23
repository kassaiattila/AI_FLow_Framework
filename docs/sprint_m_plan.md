# Sprint M Plan — v1.4.9 Vault + self-hosted Langfuse

> **Branch:** `feature/v1.4.9-vault-langfuse` — cut from `main` @ `ab63c93` (v1.4.8 merge commit).
> **Datum:** 2026-04-24.
> **Driver:** `01_PLAN/110_USE_CASE_FIRST_REPLAN.md` §5 — secrets + observability hardening pulled from v1.4.5 S94/S95.
> **Exit gate:** tag `v1.4.9` on squash merge into `main`; no plaintext prod secrets in repo or process env; Profile A E2E air-gapped (no outbound HTTP except Vault + Langfuse local).

---

## 1. Why this sprint, why now

Sprint L shipped monitoring + cost enforcement, but every HIGH-criticality credential still lives in `os.environ` at read time (LLM keys, JWT PEMs, webhook HMAC, Langfuse secret key). The replan deferred the Vault work twice already; with v1.4.8 stable on `main` and the provider-registry abstractions in place, S115-S119 can land without touching any pipeline behaviour.

Secondary goal: Profile A (BGE-M3 local) already requires no cloud LLM, so pairing a self-hosted Langfuse (S118) closes the loop for air-gapped customers.

## 2. Discovery outcome (S115)

Captured in `docs/secrets_inventory.md`. Key takeaways that shape the session queue:

- `src/aiflow/security/secrets.py` already ships `SecretProvider` / `SecretManager` with a TTL cache — S116 only needs to **implement** `VaultSecretProvider` (today it raises `NotImplementedError`), not invent the abstraction.
- `hvac>=2.1` is already an optional extra in `pyproject.toml` — S116 `uv sync --extra vault` is enough, no new dependency bump.
- `AIFlowSettings` has nested configs but **no `VaultSettings`** → S117 adds it.
- 15 discrete secrets catalogued; 12 HIGH/MEDIUM need Vault, 3 stay in env (non-secret paths).
- Vault dev container live on **port 8210** (8200 is taken by DOHA's vault on this host). `docker-compose.vault.yml` uses `${AIFLOW_VAULT_PORT:-8210}` so CI and teammates can override.

## 3. Session queue (locked)

| Session | Scope | Net-new code | Acceptance gate |
|---|---|---|---|
| **S115** ✅ | Kickoff: branch cut, discovery, inventory, vault dev container, this plan | `docker-compose.vault.yml`, `docs/secrets_inventory.md`, `docs/sprint_m_plan.md` | Branch green on main baseline; vault up; inventory merged |
| **S116** | `VaultSecretProvider` hvac impl + async adapter (`asyncio.to_thread`) + AppRole login flow + token-rotation scheduler (APScheduler) + resolver precedence (cache → Vault → env) | `src/aiflow/security/secrets.py` (fill stubs), `src/aiflow/security/vault_rotation.py` (new), 20+ unit tests for resolver precedence, 3+ integration tests against vault dev | Unit GREEN; integration against vault dev GREEN; rotation job logs every interval in structlog |
| **S117** | Introduce `VaultSettings` on `AIFlowSettings`; migrate `OPENAIKEY`, `AZURE_DOC_INTEL_KEY`, `AIFLOW_LANGFUSE__*`, `AIFLOW_WEBHOOK_HMAC_SECRET`, JWT PEMs to Vault-backed resolver; keep env fallback for local dev; `auth.py` accepts PEM-string directly. No Alembic. | `src/aiflow/core/config.py` (+VaultSettings), `src/aiflow/security/auth.py` (PEM via value), consumer-site refactors in ~8 files | Existing 2020 unit + cost_cap_enforcement + 420 E2E GREEN with Vault-backed creds; `AIFLOW_VAULT__ENABLED=false` fallback path also GREEN |
| **S118** | Self-hosted Langfuse: `docker-compose.langfuse.yml` (Langfuse v3 + its Postgres); `LANGFUSE_BASE_URL` env switch; Profile A air-gapped E2E proving no outbound HTTP except to `localhost:8210` (Vault) and `localhost:3000` (Langfuse) | `docker-compose.langfuse.yml`, `tests/e2e/test_airgapped_profile_a.py`, `docs/airgapped_deployment.md` | Network-policy E2E: pytest monkeypatches `httpx.AsyncClient` to block non-local → Profile A pipeline still green; Langfuse trace visible at local UI |
| **S119** | Sprint close: PR cut against `main`, `v1.4.9` tag queued, rotation runbook, CLAUDE.md bump | `docs/runbooks/vault_rotation.md`, `docs/sprint_m_pr_description.md`, `docs/sprint_m_retro.md`, CLAUDE.md edits, `/session-close S119` | PR #17 opened (or whatever number); tag `v1.4.9` queued at merge commit; runbook merged |

## 4. Dependencies + blockers

- **None hard-blocking.** hvac already available, vault dev reachable, Sprint L merged clean.
- **Soft:** Langfuse self-hosted image (`langfuse/langfuse:3`) requires an outbound pull the first time — offline installers should pre-pull. Capture in the S118 runbook.
- **Soft:** `OpenAIEmbedder` Profile B surrogate still reads `OPENAI_API_KEY` directly — S117 refactor touches that line, no new risk.

## 5. STOP conditions (hard)

1. S116 hvac integration test against vault dev fails repeatedly → stop, root-cause, do **not** paper over by skipping.
2. S117 resolver refactor breaks any existing unit test → revert that specific consumer migration and keep env path alive; ship the resolver itself, migrate remaining consumers in S118/S119.
3. Any hardcoded production secret discovered in repo → spawn `security-reviewer` agent, open a hotfix PR against `main` **before** continuing Sprint M.

## 6. Out of scope (explicit)

- PII redaction gate — deferred to a future sprint (see replan §7).
- Multi-tenant Vault namespaces (Vault Enterprise) — we use the OSS `kv/aiflow/*` path.
- Reranker model preload script — Sprint K follow-up, not Vault-related.
- Coverage uplift to 80% — tracked in issue #7, not a Sprint M gate.

## 7. Rollback plan

Each session is a standalone commit. If S117 blows up in CI:

```
git revert <S117 merge commit>
```

…leaves `VaultSecretProvider` implemented (S116) but unused — costs nothing, keeps env path live. S118/S119 can still run to completion against env-mode secrets if we absolutely must ship the Langfuse piece independently.

## 8. Success metric (post-merge)

```
rg -n 'os\.environ\[.*KEY\]|os\.getenv.*SECRET' src/aiflow/
```

returns only the resolver itself (`secrets.py`) and env-fallback paths that explicitly mark `_env_fallback=True`. Every other caller goes through `settings.get_secret()`.
