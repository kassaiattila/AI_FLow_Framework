# AIFlow v1.4.9 Sprint M — Session 117 Prompt (VaultSettings + consumer migration)

> **Datum:** 2026-04-25
> **Branch:** `feature/v1.4.9-vault-langfuse`
> **HEAD:** `aed33bf` (feat(security): S116 — Vault hvac impl + token rotation + SecretManager resolver chain)
> **Port:** API 8102 | UI 5173 | Vault dev 8210 | Langfuse dev (S118) 3000
> **Elozo session:** S116 — `VaultSecretProvider` live against Vault KV v2 (path#field keys, token + AppRole auth, `renew_token`/`token_ttl`), `VaultTokenRotator` daemon thread, `SecretManager` gets `fallback` provider + negative cache. 22 new unit tests + 10 live integration tests (1 dev-root-token skip). Full unit regression: 2060 pass / 1 skip / 1 xpass.
> **Terv:** `01_PLAN/110_USE_CASE_FIRST_REPLAN.md` §5 + `docs/sprint_m_plan.md` §3 (S117 row)
> **Session tipus:** IMPLEMENTATION — config wiring + consumer migration (no Alembic, no pipeline behaviour change)

---

## KONTEXTUS

### Honnan jottunk (S116)
- `VaultSecretProvider` no longer a stub — real `hvac` KV v2 CRUD, auth via token **or** AppRole, token lifecycle via `renew_token(increment)` / `token_ttl()`.
- `SecretManager(provider, fallback=..., cache_ttl_seconds=..., negative_cache_ttl_seconds=...)` implements resolver chain **cache → primary → fallback → None**. Backward compatible with existing `provider=` kwarg.
- `aiflow.security.vault_rotation.VaultTokenRotator` — plain daemon thread using `threading.Event` (chosen over APScheduler 4.x alpha currently pinned); `check_once()` renews when TTL < 20% of `renew_increment`.
- All commits on `feature/v1.4.9-vault-langfuse`, pushed. `config/policies/` still untracked carry-over — Sprint M mellek (S119 cleanup).

### Hova tartunk (S117)
Add `VaultSettings` to `AIFlowSettings`, build a singleton `resolve_secret_manager()` helper that returns a `SecretManager` with (Vault primary, Env fallback) **when `AIFLOW_VAULT__ENABLED=true`** and (Env only) otherwise, then migrate the 12 HIGH/MEDIUM consumers enumerated in `docs/secrets_inventory.md`:

1. `providers/embedder/openai.py` — `OPENAI_API_KEY` → `kv/aiflow/llm/openai#api_key`
2. `providers/embedder/azure_openai.py` — `AIFLOW_AZURE_OPENAI__API_KEY` → `kv/aiflow/llm/azure_openai#api_key`
3. `providers/parsers/azure_document_intelligence.py` + `ingestion/parsers/docling_parser.py` — `AZURE_DOC_INTEL_KEY` / aliases → `kv/aiflow/parsers/azure_doc_intel#api_key`
4. `api/deps.py` (pool DSN) — `AIFLOW_DATABASE__URL` → `kv/aiflow/db#dsn`
5. `api/app.py` + `api/v1/health.py` Langfuse block — `AIFLOW_LANGFUSE__{PUBLIC,SECRET}_KEY` → `kv/aiflow/langfuse#{public_key,secret_key}`
6. `security/auth.py` — `AIFLOW_SECURITY__JWT_{PRIVATE,PUBLIC}_KEY_PATH` → `kv/aiflow/jwt#{private_pem,public_pem}` (**value**, not path — auth.py must accept PEM string directly)
7. `api/v1/sources_webhook.py` — `AIFLOW_WEBHOOK_HMAC_SECRET` → `kv/aiflow/webhook#hmac_secret`

Keep the env fallback intact so existing 2020 unit + 420 E2E stay GREEN with `AIFLOW_VAULT__ENABLED=false`.

### Jelenlegi allapot
```
27 service | 189 endpoint | 50 DB tabla | 44 Alembic migration (head: 044)
2060 unit (22 uj: Vault + rotator + resolver) | 10 integration (uj, live Vault)
420 E2E collected | 8 skill | 23 UI oldal
hvac 2.4.0 + APScheduler 4.0.0a6 (alpha — NEM hasznalja a rotator)
```

---

## ELOFELTELEK

```bash
git branch --show-current                                  # feature/v1.4.9-vault-langfuse
git log --oneline -3                                       # HEAD aed33bf
docker ps --filter name=aiflow-vault-dev --format "{{.Names}}"
curl -s http://localhost:8210/v1/sys/health | grep -o '"sealed":false'
.venv/Scripts/python.exe -c "import hvac; print('hvac OK')"
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/security/ -q --no-cov 2>&1 | tail -1   # 64 pass
```

**Ha vault container nincs fent:**
```bash
docker compose -f docker-compose.yml -f docker-compose.vault.yml up -d vault
```

**Baseline regresszio (elotte):**
```bash
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov 2>&1 | tail -1   # 2060 pass
```

---

## FELADATOK

### LEPES 1 — `VaultSettings` nested config (~30 min)

Fajl: `src/aiflow/core/config.py`

```python
class VaultSettings(BaseSettings):
    """Vault integration for production secret resolution."""
    enabled: bool = False
    url: str = "http://localhost:8210"
    token: SecretStr | None = None
    role_id: str | None = None
    secret_id: SecretStr | None = None
    mount_point: str = "secret"
    kv_namespace: str = "aiflow"
    cache_ttl_seconds: float = 300.0
    negative_cache_ttl_seconds: float = 60.0

    model_config = SettingsConfigDict(env_prefix="AIFLOW_VAULT__")
```

Add `vault: VaultSettings = VaultSettings()` on `AIFlowSettings`. Unit: 1-2 tests in `tests/unit/core/test_config.py` confirming defaults + env override.

### LEPES 2 — `resolve_secret_manager()` singleton (~30 min)

Uj fajl: `src/aiflow/security/resolver.py`

```python
def build_secret_manager(settings: AIFlowSettings) -> SecretManager:
    """Cache → (Vault if enabled) → Env → None."""
    env = EnvSecretProvider()
    if not settings.vault.enabled:
        return SecretManager(provider=env, cache_ttl_seconds=settings.vault.cache_ttl_seconds)
    vault = VaultSecretProvider(
        vault_url=settings.vault.url,
        token=settings.vault.token.get_secret_value() if settings.vault.token else None,
        role_id=settings.vault.role_id,
        secret_id=settings.vault.secret_id.get_secret_value() if settings.vault.secret_id else None,
        mount_point=settings.vault.mount_point,
        kv_namespace=settings.vault.kv_namespace,
    )
    return SecretManager(
        provider=vault,
        fallback=env,
        cache_ttl_seconds=settings.vault.cache_ttl_seconds,
        negative_cache_ttl_seconds=settings.vault.negative_cache_ttl_seconds,
    )

@lru_cache(maxsize=1)
def get_secret_manager() -> SecretManager: ...
```

DI-style — every consumer calls `get_secret_manager().get_secret("llm/openai#api_key")`, with a second positional arg naming the env fallback key (e.g. `get_secret("llm/openai#api_key", env_alias="OPENAI_API_KEY")`) so the fallback chain can map between namespaces. **Add that `env_alias` parameter to `SecretManager.get_secret`** — backward compat: if not given, primary and fallback see the same key.

Unit: 6+ tests (`tests/unit/security/test_resolver.py`) — disabled branch, enabled with token, enabled with AppRole, env_alias fallback.

### LEPES 3 — Consumer migration (~90 min — batch per seciton)

Migrate consumers in this order so each sub-commit is green in isolation:

**3a. LLM keys** — `providers/embedder/openai.py`, `providers/embedder/azure_openai.py`
**3b. Parser keys** — `providers/parsers/azure_document_intelligence.py`, `ingestion/parsers/docling_parser.py` (collapse 3 aliases)
**3c. Langfuse** — `api/app.py:67-70`, `api/v1/health.py` block
**3d. Webhook HMAC** — `api/v1/sources_webhook.py:82`
**3e. JWT PEMs** — `security/auth.py:69-72` — refactor to accept `private_pem`/`public_pem` **value** strings; when Vault mode, resolver pulls raw PEM; when env mode, reader opens the path as today.
**3f. DB DSN** — `api/deps.py:30,39`. Lowest-risk last because every test fixture hits it.

Pattern for every migration:
```python
from aiflow.security.resolver import get_secret_manager

mgr = get_secret_manager()
api_key = mgr.get_secret("llm/openai#api_key", env_alias="OPENAI_API_KEY")
if not api_key:
    raise ConfigError("OPENAI_API_KEY missing in both Vault and env")
```

### LEPES 4 — Unit + integration coverage (~60 min)

- `tests/unit/core/test_config.py` — VaultSettings defaults + env override (2 tests).
- `tests/unit/security/test_resolver.py` — 6+ tests.
- `tests/integration/test_resolver_live.py` — disabled mode returns env, enabled mode pulls from live Vault dev (3+ tests, `VAULT_ADDR` skipif).
- Existing suites must stay GREEN **with `AIFLOW_VAULT__ENABLED=false`** (default).

### LEPES 5 — Dual-mode regression

```bash
# Env-only path (default) — MUST be identical to S116 baseline
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov 2>&1 | tail -1   # 2060+ pass
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/e2e/ --collect-only -q 2>&1 | tail -1   # 420 collected

# Vault-enabled path — seed secrets then run targeted consumer tests
python scripts/seed_vault_dev.py   # new helper; writes the 12 catalogued secrets from .env into vault
AIFLOW_VAULT__ENABLED=true AIFLOW_VAULT__TOKEN=aiflow-dev-root \
  PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/integration/test_resolver_live.py tests/integration/test_vault_provider_live.py -q --no-cov
```

(`scripts/seed_vault_dev.py` is **net-new** this session — Python wrapper around `vault kv put`, not a pipeline change.)

### LEPES 6 — Regression + session-close

```bash
.venv/Scripts/python.exe -m ruff check src/ tests/
.venv/Scripts/python.exe -m ruff format --check src/ tests/
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov
VAULT_ADDR=http://localhost:8210 VAULT_TOKEN=aiflow-dev-root \
  PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/integration/test_resolver_live.py -q --no-cov
/session-close S117
```

---

## STOP FELTETELEK

**HARD (hand back to user):**
1. Any existing unit test fails in env-only mode (`AIFLOW_VAULT__ENABLED=false`) — revert that specific consumer migration (§7 rollback per `docs/sprint_m_plan.md`).
2. JWT PEM refactor breaks `security/auth.py` token signing/verification — the consumer order deliberately places JWT at 3e so you can revert 3e alone.
3. `api/deps.py` DSN migration triggers pool/event-loop crash in integration tests — re-read memory `feedback_asyncpg_pool_event_loop.md` before retrying; may need deferral to S119.
4. Hardcoded production secret discovered in-repo → spawn `security-reviewer` agent, open hotfix PR against `main` **before** continuing Sprint M (per `docs/sprint_m_plan.md` §5.3).

**SOFT (proceed with note):**
1. Docling parser has three env var aliases (`AZURE_DI_API_KEY`, `AZURE_DI_KEY`, `AZURE_DOC_INTEL_KEY`) — collapse to the single Vault key but preserve **all three** env fallbacks via multiple `env_alias` lookups; issue created for S119 cleanup.
2. AppRole live test requires `vault auth enable approle` + role creation — add to `scripts/seed_vault_dev.py` and skip the AppRole integration test if setup fails (don't block).

---

## NYITOTT (Sprint M mellek)
- `config/policies/` untracked carry-over from S115 — single-liner `.gitignore` PR anywhere mid-sprint (S117 ideal since we're already touching config).
- `accelerate` package dist-info corruption surfaced during S116; fixed with `pip install --force-reinstall --no-deps accelerate`. If it resurfaces on another box, same command works; don't re-run full `uv sync` on OneDrive-mounted workdirs.

---

## SESSION VEGEN

```
/session-close S117
```

Utana S118 inditas: self-hosted Langfuse docker compose + air-gapped Profile A E2E.
