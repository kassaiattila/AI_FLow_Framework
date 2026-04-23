# AIFlow v1.4.9 Sprint M — Session 116 Prompt (Vault hvac impl + token rotation + resolver precedence)

> **Datum:** 2026-04-25
> **Branch:** `feature/v1.4.9-vault-langfuse` (HEAD `021db07` — S115 kickoff merged)
> **Port:** API 8102 | UI 5173 | Vault dev 8210 | Langfuse dev (S118) 3000
> **Plan:** `01_PLAN/110_USE_CASE_FIRST_REPLAN.md` §5 + `docs/sprint_m_plan.md` §3 (S116 row)
> **Session tipus:** IMPLEMENTATION (code + unit + integration tests against vault dev)

---

## KONTEXTUS

### Honnan jottunk (S115)
- Branch `feature/v1.4.9-vault-langfuse` cut from `main` @ `ab63c93` (v1.4.8 merged).
- `docker-compose.vault.yml` live, vault dev container on `http://localhost:8210`, root token `aiflow-dev-root`.
- `docs/secrets_inventory.md` cataloges 15 secrets (12 HIGH/MEDIUM → Vault, 3 non-secret stay env).
- `docs/sprint_m_plan.md` locks session queue S116-S119, rollback plan, out-of-scope list.
- Regression baseline S115: 2020 unit pass, ruff clean, 420 E2E collected, alembic head 044.

### Hova tartunk (S116)
Fill in the `VaultSecretProvider` stub in `src/aiflow/security/secrets.py` with a real `hvac` implementation, add a token-rotation scheduler, and wire the resolver precedence so `SecretManager.get_secret()` falls back cache → Vault → env → None.

**NO config migration yet** — S117 does that. S116 ships a working `VaultSecretProvider` + `SecretManager` resolver order, covered by unit + integration tests. Existing consumers stay on direct env reads.

### Jelenlegi allapot
```
27 service | 189 endpoint | 50 DB tabla | 44 Alembic migration (head: 044)
2020 unit | 420 E2E | 8 skill | 23 UI oldal
hvac>=2.1 optional extra in pyproject.toml (not yet synced)
```

---

## ELOFELTELEK

```bash
git branch --show-current                              # feature/v1.4.9-vault-langfuse
git log --oneline -3                                    # HEAD 021db07
docker ps --filter name=aiflow-vault-dev --format "{{.Names}} {{.Status}}"
curl -s http://localhost:8210/v1/sys/health | grep -o '"sealed":false'   # sealed false
uv sync --extra vault                                   # installs hvac into .venv
.venv/Scripts/python.exe -c "import hvac; print(hvac.__version__)"       # >= 2.1
.venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov 2>&1 | tail -1   # 2020 pass
```

**Ha vault container le van allitva:**
```bash
docker compose -f docker-compose.yml -f docker-compose.vault.yml up -d vault
```

---

## FELADATOK

### LEPES 1 — `VaultSecretProvider` impl (~45 min)

Fajl: `src/aiflow/security/secrets.py`

Cel: a NotImplementedError stubok helyere valo `hvac` hivasok + AppRole/Token bootstrap.

Skeleton:
```python
from hvac import Client
from hvac.exceptions import InvalidPath

class VaultSecretProvider(SecretProvider):
    def __init__(
        self,
        vault_url: str,
        token: str | None = None,
        role_id: str | None = None,
        secret_id: str | None = None,
        mount_point: str = "secret",
        kv_namespace: str = "aiflow",
    ) -> None:
        self._client = Client(url=vault_url)
        if token:
            self._client.token = token
        elif role_id and secret_id:
            login = self._client.auth.approle.login(role_id=role_id, secret_id=secret_id)
            self._client.token = login["auth"]["client_token"]
        else:
            raise ValueError("VaultSecretProvider requires either token or (role_id, secret_id)")
        self._mount = mount_point
        self._namespace = kv_namespace

    def get_secret(self, key: str) -> str | None:
        # key format: "llm/openai#api_key" → path="llm/openai", field="api_key"
        path, _, field = key.partition("#")
        try:
            resp = self._client.secrets.kv.v2.read_secret_version(
                mount_point=self._mount,
                path=f"{self._namespace}/{path}",
            )
        except InvalidPath:
            return None
        data = resp["data"]["data"]
        return data.get(field) if field else data.get("value")
    # set / delete / list analogous
```

Kiemelt szabalyok:
- `hvac` sync → `SecretManager.get_secret` is sync (cache layer). Ne async-ositsd S116-ban, az `SecretManager` konzisztencia miatt.
- Minden public fuggveny type-annotated (`aiflow/CLAUDE.md` rule).
- Structlog loggal (`vault_secret_get`, `vault_token_rotated`).
- `__all__` frissites.

### LEPES 2 — `vault_rotation.py` scheduler (~30 min)

Uj fajl: `src/aiflow/security/vault_rotation.py`

- APScheduler `BackgroundScheduler` (dep mar meglehet, ellenorizd), **egyetlen cron job**: 20 naponta `renew_token(increment=30*24*3600)` + ha 80% TTL alatt, re-login AppRole-lal.
- Indito fn: `start_token_rotation(provider: VaultSecretProvider) -> BackgroundScheduler`.
- Graceful shutdown: `scheduler.shutdown(wait=False)`.

### LEPES 3 — `SecretManager` resolver chain (~30 min)

Fajl: `src/aiflow/security/secrets.py`

Bovitsd `SecretManager`-t:

```python
class SecretManager:
    def __init__(
        self,
        primary: SecretProvider,                   # pl. VaultSecretProvider
        fallback: SecretProvider | None = None,    # EnvSecretProvider
        cache_ttl_seconds: float = 300.0,
    ) -> None: ...

    def get_secret(self, key: str) -> str | None:
        # 1. cache
        # 2. primary.get_secret (log miss)
        # 3. fallback.get_secret (log fallback_hit)
        # 4. None
```

Fontos: **cache negative lookups OWN TTL-lel** (60s), nehogy a Vault minden lookup-nal hit-et kapjon.

### LEPES 4 — Unit tesztek (~45 min)

Uj fajl: `tests/unit/security/test_vault_provider.py`

Cover:
- `get_secret` split `path#field` helyesen.
- `InvalidPath` → `None` (nem raise).
- `set_secret` → `read_secret_version` megtalal utana (mock hvac.Client).
- AppRole login path vs token path.
- `SecretManager` resolver: cache-hit / vault-hit / env-fallback-hit / all-miss.
- Negative cache: ismetelt miss ne hivja Vaultet `ttl` alatt.

Min. 20 test, mind GREEN. **hvac-ot mockoljuk unit szinten** (nem docker-dependent).

### LEPES 5 — Integration tesztek (~30 min)

Uj fajl: `tests/integration/test_vault_provider_live.py`

Cover (docker vault dev elleni, skip-elheto ha VAULT_ADDR nem elerheto):
- Round-trip: `set_secret("test/foo#bar", "baz")` → `get_secret("test/foo#bar") == "baz"`.
- Token renewal: `renew_self()` → new lease.
- AppRole login (seed role elott: `vault auth enable approle` + `vault write auth/approle/role/aiflow-test`).

Marker: `@pytest.mark.integration`, `@pytest.mark.skipif(not os.getenv("VAULT_ADDR"), reason="vault dev not running")`.

### LEPES 6 — Regression + session-close

```bash
.venv/Scripts/python.exe -m ruff check src/ tests/ --quiet
.venv/Scripts/python.exe -m ruff format --check src/ tests/
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov
VAULT_ADDR=http://localhost:8210 VAULT_TOKEN=aiflow-dev-root \
  PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/integration/test_vault_provider_live.py -q
/session-close S116
```

---

## STOP FELTETELEK

**HARD:**
1. `uv sync --extra vault` failed — hvac not installed → root-cause (mirror? lock conflict?) before retrying.
2. `docker ps` shows vault container unhealthy → `docker logs aiflow-vault-dev` elemzes.
3. hvac v2.x API-changes brake the skeleton above (pl. `kv.v2.read_secret_version` kwarg rename) → olvasd `hvac/docs/usage/secrets_engines/kv_v2.rst` vagy a nyilvanos README.
4. Integration test azt mutatja, hogy `set_secret` sikeres de `get_secret` None → **KV v2 mount path bug**, ellenorizd `vault secrets list`-tel hogy a dev mount `secret/` KV v2.

**SOFT:**
1. APScheduler mar nincs a fuggosegek kozt → `uv add apscheduler>=3.10` (S116 scope OK).
2. Integration teszt flaky a windows dockerrel → markold `flaky=True`, logold issue, ne blokkold a sprintet.

---

## NYITOTT (Sprint M mellek)
- `config/policies/` untracked — add `config/policies/intent_routing/*.yaml` a `.gitignore`-ba (1-soros PR a Sprint M kozeben).

---

## SESSION VEGEN

```
/session-close S116
```

Utana S117 inditas: `VaultSettings` nested config + consumer migration (LLM/Langfuse/JWT/webhook) a Vault-backed resolver-re.
