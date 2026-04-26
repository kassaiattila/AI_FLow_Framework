# Runbook — Vault AppRole provisioning for AIFlow prod

Sprint W SW-4 (SM-FU-2) added a boot guard that **refuses to start the
FastAPI app in `AIFLOW_ENVIRONMENT=prod` with a Vault root token**. Prod
deployments must use AppRole authentication. This runbook walks through
provisioning the AppRole role + secret_id for an AIFlow tenant.

## Prerequisites

* Vault server reachable from the AIFlow API host
* Vault CLI (`vault`) on the operator workstation
* Vault root token (or any policy with `auth/approle/role/*` write
  permission) for the bootstrap step — used **once** to create the role
* Access to AIFlow's secret manager prefix: `secret/aiflow/*`

## 1. Enable AppRole auth (one-time per Vault cluster)

```bash
vault auth enable approle
```

If already enabled, this is a no-op.

## 2. Define the AIFlow policy

Save as `aiflow-policy.hcl`:

```hcl
path "secret/data/aiflow/*" {
  capabilities = ["read"]
}
path "secret/metadata/aiflow/*" {
  capabilities = ["list"]
}
```

Apply:

```bash
vault policy write aiflow-prod aiflow-policy.hcl
```

## 3. Create the AppRole role

```bash
vault write auth/approle/role/aiflow-prod \
  policies="aiflow-prod" \
  token_ttl=1h \
  token_max_ttl=24h \
  secret_id_ttl=720h \
  secret_id_num_uses=0
```

* `token_ttl=1h` — every API token expires after one hour; the
  `VaultTokenRotator` (Sprint M S116) renews it before expiry.
* `secret_id_ttl=720h` (30 days) — the secret_id rotates on this
  cadence; operator schedules the rotation as a separate runbook
  (`vault_rotation.md`).
* `secret_id_num_uses=0` — unlimited uses within the TTL.

## 4. Read the role_id (stable per role)

```bash
vault read -field=role_id auth/approle/role/aiflow-prod/role-id
```

This is **not** a secret — it's the public identifier of the role. Save
it as the AIFlow env:

```bash
export AIFLOW_VAULT__ROLE_ID="<role_id>"
```

## 5. Mint a secret_id (rotate every 30 days)

```bash
vault write -field=secret_id -f auth/approle/role/aiflow-prod/secret-id
```

Save the result somewhere AIFlow can read it (e.g., another secret
manager, a sealed Kubernetes secret, or a file mounted with mode 0400):

```bash
export AIFLOW_VAULT__SECRET_ID="<secret_id>"
```

## 6. Wire AIFlow

Set on the API host (or in your secret-injection pipeline):

```bash
AIFLOW_ENVIRONMENT=prod
AIFLOW_VAULT__ENABLED=true
AIFLOW_VAULT__URL=https://vault.example.com
AIFLOW_VAULT__ROLE_ID=<role_id>
AIFLOW_VAULT__SECRET_ID=<secret_id>
# AIFLOW_VAULT__TOKEN — DO NOT SET in prod
```

The `VaultProvider` (Sprint M S116) detects `role_id + secret_id` and
authenticates via AppRole instead of the dev token path.

## 7. Boot validation

Start the API:

```bash
make api
```

Expected log line on success:

```
boot_guards.passed environment=prod
```

Expected log line on misconfiguration (e.g., a stray
`AIFLOW_VAULT__TOKEN=hvs.*` in env):

```
boot_guards.violation message="AIFLOW_ENVIRONMENT=prod refuses to boot with a Vault root token..."
```

The process exits non-zero. Fix the env and restart.

## 8. Emergency bypass

If a disaster requires you to boot prod with a root/dev token (e.g.,
Vault is down and you need to fail over to env-only secrets), set:

```bash
AIFLOW_VAULT__ALLOW_ROOT_TOKEN_IN_PROD=true
```

The boot guard logs a structured WARN (`boot_guards.vault_root_token_in_prod_bypass`)
on every startup until the env is removed. Audit logs surface this so
the bypass cannot stay live silently.

## 9. Terraform reference

```hcl
resource "vault_approle_auth_backend_role" "aiflow_prod" {
  backend         = "approle"
  role_name       = "aiflow-prod"
  token_policies  = ["aiflow-prod"]
  token_ttl       = 3600
  token_max_ttl   = 86400
  secret_id_ttl   = 2592000
  secret_id_num_uses = 0
}

resource "vault_approle_auth_backend_role_secret_id" "aiflow_prod" {
  backend   = "approle"
  role_name = vault_approle_auth_backend_role.aiflow_prod.role_name
}
```

The `role_id` is exposed as `vault_approle_auth_backend_role.aiflow_prod.role_id`;
the `secret_id` is in the resource's `secret_id` attribute (sensitive).
Store both in the deployment's secret-injection pipeline; do not commit
them to source control.

## See also

* `docs/runbooks/vault_rotation.md` — token + secret_id rotation cadence
* `src/aiflow/security/boot_guards.py` — the prod-vs-root-token guard
* `src/aiflow/security/secrets.py` — `VaultSecretProvider` AppRole path
