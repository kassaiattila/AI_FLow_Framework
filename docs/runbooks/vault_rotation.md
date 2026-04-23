# Vault Secret Rotation Runbook

> **Audience:** on-call engineers, platform ops, release managers.
> **Scope:** AIFlow v1.4.9+ deployments that have `AIFLOW_VAULT__ENABLED=true`.
> **Related:** `docs/secrets_inventory.md`, `docs/airgapped_deployment.md`, `docker-compose.vault.yml`, `scripts/seed_vault_dev.py`, `src/aiflow/security/vault_rotation.py`, `src/aiflow/security/secrets.py`.

AIFlow resolves every HIGH/MEDIUM criticality credential through the chain
`cache → Vault KV → env fallback → default`. This runbook covers what to rotate, how,
and how to verify consumers flipped without downtime.

---

## 1. Rotation classes

Two independent things rotate on different cadences. Do not conflate them.

| Class | What rotates | Who owns it | Typical cadence |
|---|---|---|---|
| **Vault token** | The AIFlow process's ability to *talk to Vault*. Renewable token (Token auth) or the short-lived token minted from `role_id + secret_id` (AppRole auth). | Platform / ops | Renewal every `token_ttl / 2` (automatic via `VaultTokenRotator`); re-login on failure. |
| **Business secret** | The value *stored in Vault* — LLM API keys, JWT keypair, webhook HMAC, DB DSN, Langfuse public/secret keypair. | Depends on secret (see §4–§6) | Per vendor policy. LLM keys: when compromise suspected. JWT: every 90 days. HMAC: every 180 days. Langfuse keypair: when Langfuse admin is rotated. |

A token rotation does **not** change any business secret. A business secret rotation does **not** require a Vault token rotation. Run them independently.

---

## 2. Dev environment rotation (no downtime, idempotent)

Dev uses the root token `aiflow-dev-root` against `aiflow-vault-dev` on `localhost:8210`.
Rotation in dev is a **re-seed** — destroys nothing, overwrites stale values.

```bash
# 1. Ensure vault dev is up
docker-compose -f docker-compose.vault.yml up -d
docker-compose -f docker-compose.vault.yml ps | grep aiflow-vault-dev

# 2. Re-seed all secrets from .env into Vault
.venv/Scripts/python.exe scripts/seed_vault_dev.py

# 3. Clear the resolver cache so the next request re-reads Vault
.venv/Scripts/python.exe -c "from aiflow.security.resolver import reset_secret_manager; reset_secret_manager()"

# 4. Smoke test
.venv/Scripts/python.exe -c "
import asyncio
from aiflow.security.resolver import get_secret_manager
sm = get_secret_manager()
print(asyncio.run(sm.get_secret('llm/openai#api_key', env_alias='OPENAI_API_KEY')) is not None)
"
```

If the `scripts/seed_vault_dev.py` output shows `wrote` (not `skip`) for a given secret, that secret was rotated.

---

## 3. Production token rotation — AppRole (recommended)

Use `VaultSettings.role_id` + `secret_id` instead of a long-lived token in prod. `VaultTokenRotator` handles the Vault-side renewal; rotation of the AppRole `secret_id` itself is the ops step.

### 3a. Automatic renewal (already running)

When `AIFLOW_VAULT__ENABLED=true` and `AIFLOW_VAULT__ROLE_ID` + `AIFLOW_VAULT__SECRET_ID` are set, `VaultTokenRotator` starts a daemon thread on boot:

- Renews the login-issued token at `token_ttl * renew_fraction` (default 0.5) intervals.
- On renewal failure, re-logs in with `(role_id, secret_id)`.
- Clean shutdown on `VaultTokenRotator.shutdown()` (called from FastAPI `app.on_event("shutdown")`).

Watch this in structlog via `event=vault.token.renewed` (success) and `event=vault.token.renew_failed` (error). Alert on the latter.

### 3b. AppRole `secret_id` rotation (blue/green pattern)

Prod `secret_id`s should rotate every 30–90 days. Do it without downtime:

```bash
# 1. Mint a new secret_id, keep the old one alive (Vault allows N active per role)
vault write -f auth/approle/role/aiflow/secret-id
# → outputs NEW_SECRET_ID and NEW_SECRET_ID_ACCESSOR

# 2. Push NEW_SECRET_ID into the deployment secret store (e.g. k8s Secret, systemd drop-in)
#    Do NOT destroy OLD_SECRET_ID yet.

# 3. Rolling-restart AIFlow consumers. The rotator re-logs in with NEW_SECRET_ID on boot.
kubectl rollout restart deployment/aiflow-api
kubectl rollout status deployment/aiflow-api --timeout=5m

# 4. Confirm every replica is on the new token
kubectl logs -l app=aiflow-api --tail=20 | grep 'vault.token.login_ok'

# 5. NOW destroy the old secret_id
vault write auth/approle/role/aiflow/secret-id-accessor/destroy accessor=<OLD_SECRET_ID_ACCESSOR>
```

If step 4 shows a replica still authenticating with the old id, abort step 5 — the deploy didn't fully roll.

### 3c. AppRole `role_id` rotation (rare, planned-maintenance window)

`role_id` is effectively an identity, not a secret. Rotate only on identity compromise. Requires destroy + re-create of the role:

```bash
vault delete auth/approle/role/aiflow
vault write auth/approle/role/aiflow token_policies=aiflow-read \
  token_ttl=1h token_max_ttl=4h secret_id_ttl=720h
vault read auth/approle/role/aiflow/role-id
# → NEW_ROLE_ID
vault write -f auth/approle/role/aiflow/secret-id
# → NEW_SECRET_ID
# Push both new values, rolling-restart. Same gates as §3b.
```

---

## 4. LLM API key rotation (OpenAI / Azure OpenAI)

When a vendor key is compromised or scheduled-rotated:

```bash
# 1. Revoke the old key in vendor dashboard FIRST (if compromise)
#    — OpenAI:  platform.openai.com → API keys → Revoke
#    — Azure:   portal.azure.com → Cognitive Services → Keys → Regenerate Key 1

# 2. Mint a NEW key in the same dashboard, copy it.

# 3. Write it to Vault (prod example, Token auth)
export VAULT_ADDR=https://vault.prod.internal
export VAULT_TOKEN=<ops-admin-token>
vault kv put kv/aiflow/llm/openai api_key='sk-...NEW...'
# or for Azure:
vault kv put kv/aiflow/llm/azure_openai api_key='...' endpoint='https://...'

# 4. Bust the resolver cache (no restart needed — TTL expires on next read)
#    Default positive TTL is 300s, so within 5min every consumer sees the new key.
#    Force-clear for impatience:
curl -X POST http://api.aiflow.internal:8102/admin/secrets/cache/clear \
  -H "Authorization: Bearer <api-key>"

# 5. Smoke-test an LLM call
.venv/Scripts/python.exe scripts/smoke_llm.py  # or trigger a known-good pipeline run
```

Watch `event=resolver.vault.hit path=llm/openai` in structlog — first read after cache expiry shows the new value was fetched.

### Dev equivalent

```bash
# Edit .env, then:
.venv/Scripts/python.exe scripts/seed_vault_dev.py
```

---

## 5. JWT signing keypair rotation

AIFlow signs its own JWTs with RS256 (`src/aiflow/security/auth.py`). The keypair lives at `kv/aiflow/auth/jwt#private_pem` + `kv/aiflow/auth/jwt#public_pem`. Rotation every 90 days is standard; on compromise, immediately.

Rotation **invalidates existing JWTs** — plan a short drain window.

```bash
# 1. Generate new keypair
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out /tmp/jwt_new_private.pem
openssl rsa -pubout -in /tmp/jwt_new_private.pem -out /tmp/jwt_new_public.pem

# 2. Write to Vault
vault kv put kv/aiflow/auth/jwt \
  private_pem=@/tmp/jwt_new_private.pem \
  public_pem=@/tmp/jwt_new_public.pem

# 3. Rolling-restart API (the PEM strings are read on process start; no hot-reload)
kubectl rollout restart deployment/aiflow-api

# 4. Shred the old PEMs
shred -u /tmp/jwt_new_*.pem
```

Post-rotation, all clients must re-login (existing access tokens fail verification). Notify downstream.

---

## 6. Webhook HMAC secret rotation

The webhook HMAC signs incoming source webhooks (`src/aiflow/api/v1/sources_webhook.py`). Path: `kv/aiflow/auth/webhook_hmac#secret`.

```bash
# 1. Generate new secret
NEW_HMAC=$(openssl rand -hex 32)

# 2. Write to Vault, short positive TTL for faster cutover
vault kv put kv/aiflow/auth/webhook_hmac secret=$NEW_HMAC

# 3. Rotate in the webhook caller (source system) — BEFORE cache expires.
#    If the caller uses the old HMAC during the window, the webhook 401s.
#    Coordinate the source-system rotation with an ops ticket.

# 4. Clear resolver cache once the source system is confirmed to be on NEW_HMAC.
curl -X POST http://api.aiflow.internal:8102/admin/secrets/cache/clear -H "..."
```

**Gotcha:** HMAC rotation requires coordination with the caller. Unlike LLM keys (which are per-process and flip silently), HMAC rotation breaks any unrotated caller. Run §4's steps 1–3 as a **blue/green** — caller sends both old + new HMAC for the overlap window, then drops old.

---

## 7. Langfuse keypair rotation (self-hosted)

Langfuse v3 issues project-scoped `LANGFUSE_PUBLIC_KEY` + `LANGFUSE_SECRET_KEY`. Rotation is needed on Langfuse admin account rotation or on suspected compromise.

### 7a. Generate new keypair

Log into the self-hosted Langfuse UI (`http://langfuse.internal:3000`) → Project → Settings → API Keys → Revoke old, Create new.

### 7b. Alternative: re-run bootstrap

```bash
# 1. Re-run bootstrap script — it will detect existing keypair, return current values.
#    To force NEW keys, delete the project API key in UI first, then:
.venv/Scripts/python.exe scripts/bootstrap_langfuse.py
# → emits LANGFUSE_BOOTSTRAP_PUBLIC_KEY=... LANGFUSE_BOOTSTRAP_SECRET_KEY=...

# 2. Export them
export LANGFUSE_BOOTSTRAP_PUBLIC_KEY=pk-lf-...
export LANGFUSE_BOOTSTRAP_SECRET_KEY=sk-lf-...

# 3. Re-seed Vault (LANGFUSE_BOOTSTRAP_* wins over .env in SEED_MAP)
.venv/Scripts/python.exe scripts/seed_vault_dev.py

# 4. Clear resolver cache — Langfuse tracer picks up new key on next trace
.venv/Scripts/python.exe -c "from aiflow.security.resolver import reset_secret_manager; reset_secret_manager()"
```

### 7c. Verify

```bash
# Trigger a known-good pipeline run, then confirm a trace landed in Langfuse UI
# Filter by timestamp > rotation_time.
```

---

## 8. Emergency token / secret revocation

If a Vault token or a business secret is suspected compromised:

```bash
# 1. Revoke the Vault token immediately (token auth)
vault token revoke <COMPROMISED_TOKEN>
# OR revoke all tokens for an AppRole secret_id:
vault write auth/approle/role/aiflow/secret-id-accessor/destroy accessor=<ACCESSOR>

# 2. Generate & deploy a replacement per §3 or §4–§7 as appropriate.

# 3. For LLM keys: revoke in vendor dashboard IMMEDIATELY — Vault revocation does not
#    invalidate the key at the vendor. Anyone with the leaked value can still use it
#    against the vendor API until vendor-side revocation.

# 4. Export Vault audit log for the compromise window (requires audit device enabled)
vault audit list
vault read sys/audit/file   # path to audit log
tail -n 10000 /var/log/vault_audit.log | grep -B2 -A2 '<COMPROMISED_TOKEN_PREFIX>'

# 5. Post-incident: file an entry in docs/security_incidents.md (create if missing).
```

---

## 9. Observability — what to watch

### 9a. structlog events (required)

| Event | Meaning | Alert? |
|---|---|---|
| `vault.token.renewed` | Automatic token renewal succeeded. | No — info-level expected every `token_ttl/2`. |
| `vault.token.renew_failed` | Renewal failed; rotator will attempt re-login. | **Yes** — page if >3 in 5min. |
| `vault.token.login_ok` | AppRole login succeeded (boot or after renew_failed). | No — info. |
| `vault.token.login_failed` | AppRole login failed; consumer will fall back to env. | **Yes** — page immediately. |
| `resolver.vault.hit` | Secret read from Vault (positive cache miss). | No — expected on rotation. |
| `resolver.vault.miss` | Secret not in Vault; fell back to env / default. | Yes if path is expected to be in Vault — may indicate Vault is out of sync with deployment. |
| `resolver.vault.error` | Vault responded with error (not 404). | **Yes** — page if >5 in 5min. |

### 9b. Langfuse traces during rotation

- Rotation should produce a brief cluster of `resolver.vault.hit` spans (one per consumer waking up with fresh TTL).
- Absence of `resolver.vault.hit` after `reset_secret_manager()` → resolver didn't clear. Check `get_secret_manager()` wiring.
- `langfuse.tracer.export_failed` → new Langfuse keypair hasn't propagated yet (or is wrong). Fall back to §7c verify.

### 9c. Metrics (if Prometheus enabled)

```
resolver_vault_duration_seconds{path="..."}      # P99 < 50ms healthy, > 500ms degraded
resolver_vault_errors_total{reason="..."}        # Non-zero = investigate per reason
vault_token_ttl_seconds                          # Should stay > token_ttl/2; dropping = renew stuck
```

---

## 10. Post-rotation checklist (copy-paste)

After any §3–§7 rotation, walk this list:

- [ ] `scripts/seed_vault_dev.py` (dev) OR `vault kv put` (prod) wrote the new value — confirmed via `vault kv get kv/aiflow/<path>`.
- [ ] `reset_secret_manager()` called OR positive cache TTL elapsed.
- [ ] Smoke test exercised the rotated secret (LLM call / JWT decode / webhook HMAC / Langfuse trace).
- [ ] structlog shows `resolver.vault.hit path=<path>` after rotation time.
- [ ] No `vault.token.renew_failed` in the 10min post-rotation.
- [ ] (If blue/green caller rotation) Old HMAC / old LLM key destroyed at vendor / in Vault.
- [ ] (If §8 emergency) Audit log exported + incident documented.

---

## 11. References

- `src/aiflow/security/vault_rotation.py` — `VaultTokenRotator` source.
- `src/aiflow/security/secrets.py` — `VaultSecretProvider`, `SecretManager`, negative-cache.
- `src/aiflow/security/resolver.py` — `get_secret_manager()` singleton + `reset_secret_manager()`.
- `scripts/seed_vault_dev.py` — dev idempotent seeder.
- `scripts/bootstrap_langfuse.py` — Langfuse keypair discovery / mint.
- `docs/secrets_inventory.md` — all 15 cataloged secrets with Vault paths.
- `docs/airgapped_deployment.md` — bring-up sequence for Vault + Langfuse in air-gapped deploys.
- `docker-compose.vault.yml`, `docker-compose.langfuse.yml` — dev / self-host stacks.
