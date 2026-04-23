"""Seed the dev Vault container with the S115 secret inventory.

Reads the project ``.env`` (or ambient env) and writes the 12 HIGH/MEDIUM
secrets listed in ``docs/secrets_inventory.md`` into the dev Vault mounted at
``VAULT_ADDR`` (default ``http://localhost:8210``). Idempotent — re-running
only updates values.

Usage::

    python scripts/seed_vault_dev.py                # read .env, use root token
    VAULT_ADDR=... VAULT_TOKEN=... python scripts/seed_vault_dev.py

Prints a table of (path, field, source, written?) for auditability.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import hvac
from dotenv import load_dotenv

_REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_REPO_ROOT / ".env")

VAULT_ADDR = os.environ.get("VAULT_ADDR", "http://localhost:8210")
VAULT_TOKEN = os.environ.get("VAULT_TOKEN", "aiflow-dev-root")
MOUNT = os.environ.get("AIFLOW_VAULT__MOUNT_POINT", "secret")
NAMESPACE = os.environ.get("AIFLOW_VAULT__KV_NAMESPACE", "aiflow")


SEED_MAP: list[tuple[str, str, list[str]]] = [
    # (vault_path, field, env_alias_candidates)
    ("llm/openai", "api_key", ["OPENAI_API_KEY"]),
    ("llm/anthropic", "api_key", ["ANTHROPIC_API_KEY"]),
    ("llm/azure_openai", "api_key", ["AIFLOW_AZURE_OPENAI__API_KEY"]),
    (
        "parsers/azure_doc_intel",
        "api_key",
        ["AZURE_DOC_INTEL_KEY", "AZURE_DI_API_KEY", "AZURE_DI_KEY"],
    ),
    ("db", "dsn", ["AIFLOW_DATABASE__URL"]),
    ("cache", "redis_url", ["AIFLOW_REDIS__URL"]),
    # `LANGFUSE_BOOTSTRAP_*` first so the output of `scripts/bootstrap_langfuse.py`
    # (the self-hosted S118 stack) wins over any stale cloud keypair in `.env`.
    ("langfuse", "public_key", ["LANGFUSE_BOOTSTRAP_PUBLIC_KEY", "AIFLOW_LANGFUSE__PUBLIC_KEY"]),
    ("langfuse", "secret_key", ["LANGFUSE_BOOTSTRAP_SECRET_KEY", "AIFLOW_LANGFUSE__SECRET_KEY"]),
    ("webhook", "hmac_secret", ["AIFLOW_WEBHOOK_HMAC_SECRET"]),
]


def _pick_value(aliases: list[str]) -> str | None:
    for alias in aliases:
        value = os.environ.get(alias)
        if value:
            return value
    return None


def _write_secret(client: hvac.Client, path: str, field: str, value: str) -> None:
    full_path = f"{NAMESPACE}/{path}" if NAMESPACE else path
    existing: dict[str, str] = {}
    try:
        resp = client.secrets.kv.v2.read_secret_version(
            mount_point=MOUNT, path=full_path, raise_on_deleted_version=True
        )
        existing = dict(resp["data"]["data"])
    except hvac.exceptions.InvalidPath:
        existing = {}
    existing[field] = value
    client.secrets.kv.v2.create_or_update_secret(mount_point=MOUNT, path=full_path, secret=existing)


def _maybe_seed_jwt(client: hvac.Client) -> list[tuple[str, str, str, bool]]:
    """Seed JWT PEMs from file paths if configured."""
    rows: list[tuple[str, str, str, bool]] = []
    for field, env_alias in (
        ("private_pem", "AIFLOW_JWT_PRIVATE_KEY_PATH"),
        ("public_pem", "AIFLOW_JWT_PUBLIC_KEY_PATH"),
    ):
        path = os.environ.get(env_alias, "")
        if not path:
            rows.append(("jwt", field, env_alias, False))
            continue
        pem_file = Path(path)
        if not pem_file.is_file():
            rows.append(("jwt", field, f"{env_alias}:MISSING", False))
            continue
        _write_secret(client, "jwt", field, pem_file.read_text(encoding="utf-8"))
        rows.append(("jwt", field, env_alias, True))
    return rows


def main() -> int:
    client = hvac.Client(url=VAULT_ADDR, token=VAULT_TOKEN)
    if not client.is_authenticated():
        print(f"FATAL: not authenticated against {VAULT_ADDR}", file=sys.stderr)
        return 1

    print(f"Seeding Vault at {VAULT_ADDR} mount={MOUNT} namespace={NAMESPACE}")
    print(f"{'path':<32}{'field':<14}{'source':<32}{'written'}")
    print("-" * 90)

    written = 0
    skipped = 0
    for path, field, aliases in SEED_MAP:
        value = _pick_value(aliases)
        if value is None:
            print(f"{path:<32}{field:<14}{'(no env set)':<32}SKIP")
            skipped += 1
            continue
        _write_secret(client, path, field, value)
        print(f"{path:<32}{field:<14}{aliases[0]:<32}OK")
        written += 1

    for path, field, source, ok in _maybe_seed_jwt(client):
        marker = "OK" if ok else "SKIP"
        print(f"{path:<32}{field:<14}{source:<32}{marker}")
        if ok:
            written += 1
        else:
            skipped += 1

    print("-" * 90)
    print(f"Seeded {written}, skipped {skipped}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
