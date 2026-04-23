# AIFlow v1.4.9 Sprint M — Session 118 Prompt (Self-hosted Langfuse + air-gapped Profile A E2E)

> **Datum:** 2026-04-25
> **Branch:** `feature/v1.4.9-vault-langfuse`
> **HEAD:** `80465dc` (feat(security): S117 — VaultSettings + SecretManager resolver + 7 consumer migrations)
> **Port:** API 8102 | UI 5173 | Vault dev 8210 | Langfuse dev (S118) 3000 | Langfuse Postgres (S118) 5434
> **Elozo session:** S117 — `VaultSettings` wired on `AIFlowSettings`, `aiflow.security.resolver` singleton with Vault+env fallback, `SecretManager.get_secret(env_alias=...)` namespace mapping, 7 consumer migrations (OpenAI/AzureOpenAI embedders, AzureDI parser + docling 3-alias path, Langfuse, webhook HMAC, JWT PEMs, DB DSN). 13 new unit + 4 live integration tests. 2073 pass / 1 skip / 1 xpass. `.gitignore` now excludes `config/policies/`.
> **Terv:** `01_PLAN/110_USE_CASE_FIRST_REPLAN.md` §5 + `docs/sprint_m_plan.md` §3 (S118 row)
> **Session tipus:** IMPLEMENTATION — docker-compose + E2E air-gap harness (no Alembic, no pipeline code change beyond Langfuse base URL plumbing)

---

## KONTEXTUS

### Honnan jottunk (S117)
- `get_secret_manager()` is now the canonical secret entry point; every HIGH/MEDIUM consumer reads through it with `env_alias=` for legacy env fallback.
- `.env`-only mode stays the default (`AIFLOW_VAULT__ENABLED=false`); the 2073 unit + 420 E2E suites are identical to S116.
- Vault-enabled mode verified end-to-end against `aiflow-vault-dev` (4 new live tests).
- Commit `80465dc`, pushed. Sprint M plan §3 now has S116+S117 greened.

### Hova tartunk (S118)
Ship a **self-hosted Langfuse v3** docker compose overlay and prove **air-gapped Profile A** (BGE-M3 local embedder) runs without touching any host other than `localhost:8210` (Vault) and `localhost:3000` (Langfuse). Deliverables:

1. `docker-compose.langfuse.yml` — Langfuse v3 + its own Postgres (port 5434 to avoid clash with AIFlow Postgres on 5433). Bootstrap admin user + org + project via Langfuse init one-shot container.
2. `AIFLOW_LANGFUSE__HOST` env switch so the tracer honours `http://localhost:3000` when set. Already wired through S117 resolver — only need the compose file + docs + make sure `aiflow.observability.tracing.LangfuseTracer` passes host through the SDK.
3. `tests/e2e/test_airgapped_profile_a.py` — pytest monkeypatch on `socket.getaddrinfo` that blocks every non-`localhost` / non-`127.0.0.1` / non-`host.docker.internal` hostname, then runs the UC2 RAG ingest + query with Profile A BGE-M3 embedder. Confirms the tracer pushes a span to the local Langfuse and the `scripts/smoke_test.sh` still passes.
4. `docs/airgapped_deployment.md` — operator runbook covering dev + prod, image pre-pull, secret seeding (`scripts/seed_vault_dev.py`), smoke checklist.

### Jelenlegi allapot
```
27 service | 189 endpoint | 50 DB tabla | 44 Alembic migration (head: 044)
2073 unit (13 uj S117: VaultSettings + resolver) | 13 vault-related integration (9 vault-provider + 4 resolver-live)
420 E2E collected | 8 skill | 23 UI oldal
hvac 2.4.0 | langfuse >= 2.29 (pinned in pyproject) | APScheduler 4.0.0a6 (idle)
Vault dev: aiflow-vault-dev@:8210 (root token aiflow-dev-root, unsealed)
```

---

## ELOFELTELEK

```bash
git branch --show-current                                  # feature/v1.4.9-vault-langfuse
git log --oneline -3                                       # HEAD 80465dc
docker ps --filter name=aiflow-vault-dev --format "{{.Names}}"   # running
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov 2>&1 | tail -1   # 2073 pass
.venv/Scripts/python.exe -c "import langfuse; print(langfuse.__version__)"
docker image ls langfuse/langfuse 2>&1 | head -3           # may be empty — pull in LEPES 1
```

**Ha Langfuse image nincs meg (offline):**
```bash
docker pull langfuse/langfuse:3
docker pull postgres:16-alpine
```

---

## FELADATOK

### LEPES 1 — `docker-compose.langfuse.yml` (~40 min)

Uj fajl a repo gyokerben. Szolgaltatasok:

- `langfuse-postgres` — Postgres 16, host port `5434` → container `5432`, sajat volume `langfuse_pg_data`, env `POSTGRES_PASSWORD=langfuse_dev_password`.
- `langfuse-web` — `langfuse/langfuse:3`, dep on `langfuse-postgres`, ports `3000:3000`, env `DATABASE_URL=postgres://postgres:langfuse_dev_password@langfuse-postgres:5432/postgres`, `NEXTAUTH_URL=http://localhost:3000`, `NEXTAUTH_SECRET=$(openssl rand -hex 32)` (read from `.env.langfuse`, gitignored), `SALT=$(openssl rand -hex 32)`, `TELEMETRY_ENABLED=false`.
- `langfuse-init` (one-shot, `profiles: [bootstrap]`) — small Python container that runs `scripts/bootstrap_langfuse.py` (new) against the REST API to create org `aiflow-dev`, project `aiflow-dev`, and prints the `pk-...` / `sk-...` keypair. Those keys go into Vault via `scripts/seed_vault_dev.py`.

Egyuttmukodes a `docker-compose.vault.yml`-lel: kozos external bridge `aiflow-dev-net`, hogy a `vault` + `langfuse-web` ugyanabban a halozatban legyen. `--project-name aiflow-dev` prefixel mindent.

### LEPES 2 — Bootstrap script + seed extension (~30 min)

`scripts/bootstrap_langfuse.py` — minimalista `requests`-alapu client (nem kell uj dep), idempotens: POST `/api/public/projects` utan ha 409, olvassa a meglevo kulcsokat. Kimenet stdout-ra: `LANGFUSE_BOOTSTRAP_PUBLIC_KEY=...` / `LANGFUSE_BOOTSTRAP_SECRET_KEY=...`.

Extend `scripts/seed_vault_dev.py` SEED_MAP-jat, hogy a bootstrap kimenetebol olvasott keypair (env `LANGFUSE_BOOTSTRAP_PUBLIC_KEY` / `LANGFUSE_BOOTSTRAP_SECRET_KEY`) felulirja a `langfuse#public_key` / `#secret_key` mezot a Vault-ban.

### LEPES 3 — Langfuse host wiring (~20 min)

A S117 refactor utan `api/app.py` + `api/v1/health.py` mar a resolveren at kap `langfuse#public_key` / `#secret_key`-t. Meg kell ellenorizni:

- `aiflow.observability.tracing.LangfuseTracer` konstruktora kezeli-e a `host=` paramot es tovabbitja-e a Langfuse SDK-nak (v2 API: `host=`, v3 API: `base_url=`). Ha nem, egy sor fix kell.
- `.env.example`-be:

```
# Self-hosted Langfuse (air-gapped); cloud alapertelmezett
AIFLOW_LANGFUSE__HOST=http://localhost:3000
AIFLOW_LANGFUSE__ENABLED=true
```

### LEPES 4 — Air-gap E2E test (~60 min)

Uj fajl: `tests/e2e/test_airgapped_profile_a.py`

Szemantika egy `socket.getaddrinfo` monkeypatch fixture-vel:

```python
@pytest.fixture
def airgap_guard(monkeypatch):
    import socket
    original = socket.getaddrinfo
    ALLOWED_EXACT = {"localhost", "127.0.0.1", "::1", "host.docker.internal"}

    def guarded(host, *args, **kwargs):
        if host in ALLOWED_EXACT or host.endswith(".localhost"):
            return original(host, *args, **kwargs)
        raise RuntimeError(f"air-gap violation: getaddrinfo({host!r})")

    monkeypatch.setattr(socket, "getaddrinfo", guarded)
```

Scenario (aszof_rag_chat, 2-3 doksi, Profile A BGE-M3):
1. Pipeline start via API → ingest 2 fixture PDFs (mar elerheto `tests/fixtures/aszf_rag/` alatt).
2. Query → top-1 chunk relevancia >= a Sprint J MRR baseline.
3. Langfuse REST GET `http://localhost:3000/api/public/traces?limit=1` → legutobbi trace `name` match.
4. Semmi kulso DNS: a fixture dob, ha `cloud.langfuse.com` / `api.openai.com` / `api.anthropic.com` felbukkan.

Skip logika: `pytest.importorskip("langfuse")` + `httpx`-es skipif arra, hogy `http://localhost:3000/api/public/health` elerheto.

Uj `@test_registry` header (`suite: e2e-airgap`, `phase: 8`).

### LEPES 5 — Runbook (~30 min)

`docs/airgapped_deployment.md`:
- Overview: vault dev + langfuse dev compose layering, minimum image set (`langfuse/langfuse:3`, `postgres:16-alpine`, `hashicorp/vault:1.18`), `docker save`/`docker load` workflow.
- Secret seeding recipe: `scripts/bootstrap_langfuse.py` → `scripts/seed_vault_dev.py` → API restart.
- Network policy: allowed hosts per env, `AIFLOW_LANGFUSE__HOST` values (dev vs. prod vs. cloud fallback).
- Smoke checklist referencing `tests/e2e/test_airgapped_profile_a.py` + `scripts/smoke_test.sh`.

### LEPES 6 — Regression + session-close

```bash
.venv/Scripts/python.exe -m ruff check src/ tests/ scripts/
.venv/Scripts/python.exe -m ruff format --check src/ tests/ scripts/
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov
VAULT_ADDR=http://localhost:8210 VAULT_TOKEN=aiflow-dev-root \
  PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/integration/test_resolver_live.py -q --no-cov
AIFLOW_LANGFUSE__HOST=http://localhost:3000 AIFLOW_LANGFUSE__ENABLED=true \
  PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/e2e/test_airgapped_profile_a.py -v --no-cov
/session-close S118
```

---

## STOP FELTETELEK

**HARD (hand back to user):**
1. `langfuse/langfuse:3` image nem elerheto es a kornyezet nem enged kulso kimenoket. Kerdezd meg hogy `langfuse/langfuse:2` fallback elfogadott-e, vagy pre-pullt kell kerni.
2. `socket.getaddrinfo` monkeypatch falloozza a testcontainers-t vagy a helyi Postgres fixture-t — meg kell engedni `127.0.0.1` + `host.docker.internal`-t, de `langfuse.com` / `cloud.langfuse.com` / `api.openai.com` blokkolt marad.
3. `NEXTAUTH_SECRET` rotacio elrontja a local Langfuse admin authet es a bootstrap script 401-re fut — `.env.langfuse` perzisztalja, ne per-run generalj.

**SOFT (proceed with note):**
1. Langfuse v3 Python SDK breaking change a `langfuse.get_client()`-en → pin `langfuse<3.2` a `pyproject.toml`-ban, issue a Sprint M retroba.
2. BGE-M3 sulyok elso E2E futasanal letoltodnek (~1-2 GB). Dokumentald a runbookban, CI-ben preload cache artifact.
3. Air-gap teszt nem futtat Playwright browser UI-t — a `/live-test` eszlelhetoseg kulon sprint (Playwright container `--network=none` variansa jovobeli munka).

---

## NYITOTT (Sprint M mellek)
- S119 (Sprint close) sorakozik utana: PR cut `main`-re, `v1.4.9` tag, `docs/runbooks/vault_rotation.md`, CLAUDE.md szamfrissites (+13 unit / +4 integration S117-bol, Langfuse self-host szovegek).
- `pyproject.toml` lockfile frissites hvac / langfuse fo verzio pinre, ha S118 eros verzio pint igenyel.

---

## SESSION VEGEN

```
/session-close S118
```

Utana S119: PR + tag + retro + rotation runbook.
