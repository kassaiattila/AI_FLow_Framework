# AIFlow Secrets Inventory — Sprint M (v1.4.9) S115

> **Status:** Discovery baseline, 2026-04-24, branch `feature/v1.4.9-vault-langfuse`.
> **Scope:** Every location in `src/aiflow/` that reads a secret (or pseudo-secret config) today, with the Vault migration target.
> **Method:** `grep -rn "os.environ|os.getenv"` across `src/aiflow/` + read of `.env.example`, `docker-compose.yml`, `src/aiflow/core/config.py`, `src/aiflow/security/secrets.py`.

---

## 1. Current state (what is wired today)

- **Provider abstraction already exists:** `src/aiflow/security/secrets.py` defines `SecretProvider` (ABC), `EnvSecretProvider` (live), `VaultSecretProvider` (stub — `NotImplementedError` on every call), and `SecretManager` with `threading.Lock`-protected TTL cache (default 300 s). **No code path currently routes through `SecretManager` for production secrets** — every consumer reads env directly.
- **`hvac>=2.1`** is already declared as optional `vault` extra in `pyproject.toml:74`. No runtime import yet.
- **`AIFlowSettings` (core/config.py)** has nested models (`DatabaseSettings`, `SecuritySettings`, `LLMSettings`, `LangfuseSettings`, `BudgetSettings`) but **no `vault_*` field** and no hook that swaps an env value for a Vault lookup.
- **`docker-compose.yml`** has no Vault service; root password for Postgres is hardcoded (`aiflow_dev_password`) in both the compose file and the DSN in `.env.example`.

---

## 2. Secret inventory

**Criticality:**
- **HIGH** — leak compromises external LLM quotas, customer data, or signs auth tokens
- **MEDIUM** — leak compromises observability / internal audit trail or webhook replay protection
- **LOW** — path/flag-style vars, non-secret config (kept in env, out of Vault scope)

| # | Secret name | Current source (read path) | Consumer(s) | Criticality | Vault path target (v1.4.9) |
|---|---|---|---|---|---|
| 1 | `OPENAI_API_KEY` | env, bare (not `AIFLOW_`-prefixed) | `providers/embedder/openai.py:65`, `services/rag_engine/service.py` (via `OpenAI()` default), `engine/skill_runner.py` (LLM dispatch) | HIGH | `kv/aiflow/llm/openai#api_key` |
| 2 | `ANTHROPIC_API_KEY` | `.env.example` (commented) | Anticipated LLM router (Sprint N+) | HIGH | `kv/aiflow/llm/anthropic#api_key` |
| 3 | `AIFLOW_AZURE_OPENAI__API_KEY` | env, `AIFLOW_*__*` nested | `providers/embedder/azure_openai.py:63,112,163` | HIGH | `kv/aiflow/llm/azure_openai#api_key` |
| 4 | `AZURE_DOC_INTEL_KEY` | env, bare | `providers/parsers/azure_document_intelligence.py:79-189` | HIGH | `kv/aiflow/parsers/azure_doc_intel#api_key` |
| 5 | `AZURE_DI_API_KEY` / `AZURE_DI_KEY` | env, bare (two aliases) | `ingestion/parsers/docling_parser.py:228` | HIGH | `kv/aiflow/parsers/azure_doc_intel#api_key` (dedupe w/ #4) |
| 6 | `AIFLOW_DATABASE__URL` (contains password) | env, nested DSN | `api/deps.py:30,39`, `services/{health,audit,diagram,human_review,media,rpa_browser,rag_engine}/service.py` | HIGH | `kv/aiflow/db#dsn` (whole DSN; password-only option deferred) |
| 7 | `AIFLOW_REDIS__URL` | env | `api/middleware.py:198`, `services/health_monitor/service.py:153`, `api/v1/health.py:34` | MEDIUM | `kv/aiflow/cache#redis_url` (usually no auth in dev, but prod has TLS + ACL) |
| 8 | `AIFLOW_LANGFUSE__PUBLIC_KEY` | env, nested | `api/app.py:67`, `api/v1/health.py:199`, `observability/tracing` (implicit) | MEDIUM | `kv/aiflow/langfuse#public_key` |
| 9 | `AIFLOW_LANGFUSE__SECRET_KEY` | env, nested | `api/app.py:68`, Langfuse client init | HIGH | `kv/aiflow/langfuse#secret_key` |
| 10 | `AIFLOW_LANGFUSE__HOST` | env, nested | `api/app.py:69`, `api/v1/health.py` | LOW (will pivot to `http://langfuse:3000` after S118) | env only |
| 11 | `AIFLOW_SECURITY__JWT_PRIVATE_KEY_PATH` (file) | env → filesystem path | `security/auth.py:69-72` | HIGH (key material on disk) | `kv/aiflow/jwt#private_pem` (value, not path — resolver writes to tmpfs) |
| 12 | `AIFLOW_SECURITY__JWT_PUBLIC_KEY_PATH` (file) | env → filesystem path | `security/auth.py:72` | MEDIUM (public) | `kv/aiflow/jwt#public_pem` |
| 13 | `AIFLOW_WEBHOOK_HMAC_SECRET` | env | `api/v1/sources_webhook.py:82` | HIGH (replay protection) | `kv/aiflow/webhook#hmac_secret` |
| 14 | `POSTGRES_PASSWORD` (compose) | `docker-compose.yml:8` hardcoded `aiflow_dev_password` | Postgres container env | HIGH (dev only — prod uses external managed DB) | `kv/aiflow/db#password` (dev keeps hardcoded in compose) |
| 15 | `VAULT_DEV_ROOT_TOKEN_ID` | NEW (`docker-compose.vault.yml` S115) | Vault dev container | HIGH (bootstrap only — never used in prod) | N/A — prod uses AppRole |

**Non-secret env (not migrating, stays in env):** `AIFLOW_ENVIRONMENT`, `AIFLOW_DEBUG`, `AIFLOW_LOG_LEVEL`, `AIFLOW_CORS_ORIGINS`, `AIFLOW_UPLOAD_DIR`, `AIFLOW_EMAIL_UPLOAD_DIR`, `AIFLOW_EMAIL_DIR`, `AIFLOW_INTAKE_STORAGE`, `AIFLOW_POLICY_DIR`, `AIFLOW_MAX_UPLOAD_BYTES`, `AIFLOW_INTAKE_UPLOAD_ROOT`, `AIFLOW_INTAKE_UPLOAD_MAX_BYTES`, `AIFLOW_PROMPT_DIRS`, `AIFLOW_WEBHOOK_STORAGE_ROOT`, `AIFLOW_WEBHOOK_TENANT_ID`, `AIFLOW_WEBHOOK_MAX_BYTES`, `AIFLOW_WEBHOOK_MAX_CLOCK_SKEW_SECONDS`, `AIFLOW_BGE_M3__*`, `AIFLOW_AZURE_OPENAI__{ENDPOINT,API_VERSION,DEPLOYMENT}`, `AIFLOW_OPENAI__{EMBEDDING_MODEL,BASE_URL,EMBEDDING_DIM}`.

---

## 3. Vault KV layout (proposed, `secret/` mount, KV v2)

```
kv/aiflow/
  llm/
    openai           {api_key}
    anthropic        {api_key}
    azure_openai     {api_key}
  parsers/
    azure_doc_intel  {api_key, endpoint}
  db                 {dsn, password}
  cache              {redis_url}
  langfuse           {public_key, secret_key}
  jwt                {private_pem, public_pem}
  webhook            {hmac_secret}
```

Rationale: one namespace per backend category, multi-field entries for related creds so rotation is atomic (e.g., rotating Azure DI rotates key + endpoint together if endpoint is region-bound).

---

## 4. Resolver precedence (S116 target)

The Vault-backed resolver must fall back cleanly so local dev + CI stay on env:

```
settings.get_secret("openai.api_key")
  → 1. SecretManager cache (TTL 300s)
  → 2. VaultSecretProvider if Settings.vault.enabled and token valid
  → 3. EnvSecretProvider (legacy AIFLOW_SECRET_* or bare env)
  → 4. None  (caller decides whether this is a hard error)
```

`Settings.vault.enabled` gates the Vault lookup; in CI the gate is `false` by default, so unit tests never hit the network.

---

## 5. Open questions for S116 scope decision

1. **Bare env keys (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `AZURE_DOC_INTEL_KEY`):** Rename to `AIFLOW_*` prefix during S117 migration, or keep bare for SDK compat (OpenAI SDK auto-reads `OPENAI_API_KEY`)? **Recommendation:** keep bare (SDK ergonomics) but have the resolver *write them back* to `os.environ` on startup so SDK code paths stay untouched.
2. **JWT key material:** Current auth.py reads from file path. Moving the PEM into Vault means writing to `tmpfs` at bootstrap or swapping to in-memory PyJWT load. **Recommendation:** S117 change `auth.py` to accept `jwt_private_pem` directly (string) with fallback to path — path-only for dev, Vault-served PEM for prod.
3. **`VaultSecretProvider.list_keys()`:** Current stub is sync and raises. hvac v2.x client is sync → OK; but the rest of AIFlow is async. **Recommendation:** wrap hvac calls in `asyncio.to_thread()` inside a thin async adapter so the `SecretManager` stays non-blocking.
4. **Token rotation:** Vault tokens expire (default 32d). Need a scheduler that re-reads token from disk file (AppRole login flow) every ~20 d. **Recommendation:** APScheduler job in S116, logs via structlog.

---

## 6. Exit criteria for S115 inventory

- [x] All secrets reading sites listed with file:line.
- [x] Each gets a criticality + proposed Vault path.
- [x] Non-secret env explicitly excluded.
- [x] Open questions captured so S116 can start without re-discovery.

**Next:** `docker-compose.vault.yml` (dev container) + `docs/sprint_m_plan.md` (locked session queue).
