# Air-gapped AIFlow deployment — Vault + self-hosted Langfuse + Profile A

> Sprint M (v1.4.9) S118 runbook. Covers dev and prod layering, image pre-pull,
> secret seeding, and the smoke checklist that proves no external DNS is
> touched once the stack is running.

## 1. Why air-gap

Customers running AIFlow on-prem or under compliance boundaries (healthcare,
public sector, regulated banking) frequently require that no outbound traffic
leaves the cluster except through a vetted egress proxy. The combination of
**Vault** (S116/S117) + **self-hosted Langfuse** (S118) + **Profile A
embedder** (BGE-M3, local weights from S103) is the first fully-offline path
through the platform:

- LLM calls — still need an external endpoint, but are routed through the
  operator-supplied Azure OpenAI / private OpenAI gateway (Profile B).
- Embeddings — Profile A uses `BAAI/bge-m3` weights on disk, no network.
- Secrets — resolved through Vault (`aiflow.security.resolver`), never hit the
  filesystem unencrypted.
- Observability — traces land in the local Langfuse web+Postgres pair, not
  `cloud.langfuse.com`.

## 2. Image set

Three images must be pre-staged on the target host. Sizes are approximate
(compressed + extracted):

| Image                     | Purpose                      | Size  |
|--------------------------|------------------------------|-------|
| `hashicorp/vault:1.15`   | Secret store (dev / prod)    | ~200 MB |
| `langfuse/langfuse:3`    | Observability web + worker   | ~1.2 GB |
| `postgres:16-alpine`     | Langfuse backing DB          | ~110 MB |

The AIFlow API itself still runs from `.venv` on the host in dev; prod builds
use the existing `docker-compose.prod.yml` app image.

### Pre-pull on an internet-connected jumpbox

```bash
docker pull hashicorp/vault:1.15
docker pull langfuse/langfuse:3
docker pull postgres:16-alpine

docker save \
  hashicorp/vault:1.15 \
  langfuse/langfuse:3 \
  postgres:16-alpine \
  | gzip > aiflow-airgap-images.tgz
```

### Load on the air-gapped target

```bash
gunzip -c aiflow-airgap-images.tgz | docker load
docker image ls | grep -E "vault|langfuse|postgres"
```

## 3. Bring-up sequence

### 3.1 Vault dev (S115)

```bash
docker compose -f docker-compose.yml -f docker-compose.vault.yml up -d vault
export VAULT_ADDR=http://localhost:8210
export VAULT_TOKEN=aiflow-dev-root
curl -s "$VAULT_ADDR/v1/sys/health" | jq .
```

> Dev mode uses an in-memory backend with the deterministic root token
> `aiflow-dev-root`. Production brings its own cluster + AppRole auth —
> swap `VAULT_TOKEN` for the AppRole login response.

### 3.2 Langfuse (S118)

```bash
# Self-hosted Langfuse vars now live in .env (consolidated — see .env.example).
# Generate persistent secrets ONCE — rotating them invalidates every session + API key:
#   NEXTAUTH_SECRET=$(openssl rand -hex 32)
#   LANGFUSE_SALT=$(openssl rand -hex 32)
# Paste both values into .env (NEXTAUTH_SECRET=..., LANGFUSE_SALT=...).

docker compose -f docker-compose.langfuse.yml \
  up -d langfuse-postgres langfuse-web

# Wait for the web UI to respond:
until curl -sf http://localhost:3000/api/public/health >/dev/null; do sleep 2; done
```

### 3.3 Bootstrap + seed Vault

```bash
docker compose -f docker-compose.langfuse.yml \
  --profile bootstrap run --rm langfuse-init > out/langfuse_keys.env

# Feed the keypair into Vault. The script honours LANGFUSE_BOOTSTRAP_*
# ahead of legacy AIFLOW_LANGFUSE__*_KEY env aliases, so the self-hosted
# keypair always wins even when `.env` still has cloud values.
set -a && source out/langfuse_keys.env && set +a
python scripts/seed_vault_dev.py
```

For operators that want the keypair **pinned** across Langfuse restarts (so
the Vault entry does not drift): paste the values into `.env` as
`LANGFUSE_INIT_PROJECT_PUBLIC_KEY=` / `LANGFUSE_INIT_PROJECT_SECRET_KEY=` and
restart `langfuse-web`. Subsequent `langfuse-init` runs will then short-circuit
on the `LANGFUSE_SEEDED_*` probe.

### 3.4 Point AIFlow at the local Langfuse

Edit `.env` (or the env-manager of choice) and set:

```
AIFLOW_LANGFUSE__HOST=http://localhost:3000
AIFLOW_LANGFUSE__ENABLED=true
AIFLOW_VAULT__ENABLED=true
AIFLOW_VAULT__URL=http://localhost:8210
```

The resolver will pick up `langfuse#public_key` / `langfuse#secret_key` from
Vault; the env aliases stay as fallback for environments that have not yet
migrated.

## 4. Network policy

The per-environment allow-list below is what the air-gap E2E fixture enforces
in `tests/e2e/test_airgapped_profile_a.py` (via a `socket.getaddrinfo`
monkeypatch). Mirror it in the operator firewall.

| Environment | Allowed hosts                                                   | Langfuse host                    |
|-------------|-----------------------------------------------------------------|----------------------------------|
| dev         | `localhost`, `127.0.0.1`, `::1`, `host.docker.internal`         | `http://localhost:3000`          |
| staging     | internal cluster DNS + egress proxy VIP                          | `http://langfuse.internal:3000`  |
| prod        | internal cluster DNS only                                        | `https://langfuse.<tenant>.svc`  |
| cloud       | public internet (legacy)                                         | `https://cloud.langfuse.com`     |

## 5. Smoke checklist

Run these after every bring-up. All must pass before declaring the stack
ready for a workload.

1. **Vault unsealed**
   ```bash
   curl -s http://localhost:8210/v1/sys/health | jq .sealed    # false
   ```
2. **Secrets readable**
   ```bash
   python -c "from aiflow.security.resolver import get_secret_manager as g; \
     print(bool(g().get_secret('langfuse#public_key')))"        # True
   ```
3. **Langfuse healthy**
   ```bash
   curl -sf http://localhost:3000/api/public/health             # 200 OK
   ```
4. **API boot → first trace**
   ```bash
   uvicorn aiflow.api.app:app --port 8102 &
   scripts/smoke_test.sh                                        # existing smoke
   ```
5. **Air-gap E2E** — proves no external DNS is reached during a tracer
   round-trip + (optionally) a BGE-M3 encode:
   ```bash
   AIFLOW_LANGFUSE__HOST=http://localhost:3000 \
   AIFLOW_LANGFUSE__ENABLED=true \
   PYTHONPATH="src;." .venv/Scripts/python.exe \
     -m pytest tests/e2e/test_airgapped_profile_a.py -v --no-cov
   ```
   The second test skips unless `AIFLOW_BGE_M3_WEIGHTS_READY=1` is set; set
   that flag after running `scripts/bootstrap_bge_m3.py` on a machine that
   still has internet access, then `docker cp` or rsync the resulting
   `~/.cache/huggingface/` tree into the target host.

## 6. Rotation & recovery

- **Langfuse keypair rotation**: delete the API key via the Langfuse UI →
  re-run `--profile bootstrap run --rm langfuse-init` → re-run
  `scripts/seed_vault_dev.py`. API restart required so the tracer reloads
  the secret.
- **Vault re-seed**: the dev Vault is in-memory — every restart wipes KVs.
  Always re-run `scripts/seed_vault_dev.py` after bouncing `aiflow-vault-dev`.
- **Langfuse Postgres volume**: `aiflow_langfuse_pg_data`. Snapshot with
  `docker run --rm -v aiflow_langfuse_pg_data:/data alpine tar czf - /data >
  langfuse_pg_backup.tgz`.

## 7. Known limitations

- **Langfuse SDK v4**: the repo currently ships `langfuse==4.x`. `LangfuseTracer`
  (see `src/aiflow/observability/tracing.py`) already uses the v4 surface
  (`start_observation` + `trace_context`). If a future SDK bump breaks that,
  pin `langfuse<4.x` in `pyproject.toml`.
- **BGE-M3 weight size**: ~2 GB first download. Cache under
  `$SENTENCE_TRANSFORMERS_HOME` or `AIFLOW_BGE_M3__CACHE_FOLDER` and ship as a
  CI/release artifact.
- **Playwright air-gap**: `/live-test` still uses Chromium with a default
  network namespace. A `--network=none` overlay for the UI live journey is
  planned post-S118.
