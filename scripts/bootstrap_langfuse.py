"""Bootstrap a self-hosted Langfuse project and print its API keypair.

Designed for the S118 air-gapped dev stack (`docker-compose.langfuse.yml`). The
one-shot `langfuse-init` container runs this script after `langfuse-web` boots;
the keypair it emits on stdout is consumed by ``scripts/seed_vault_dev.py`` to
populate ``langfuse/public_key`` and ``langfuse/secret_key`` in Vault.

Environment:
    LANGFUSE_HOST             Default ``http://langfuse-web:3000`` inside compose,
                              or ``http://localhost:3000`` when run on the host.
    LANGFUSE_ADMIN_EMAIL      Admin user email (matches ``LANGFUSE_INIT_USER_EMAIL``).
    LANGFUSE_ADMIN_PASSWORD   Admin user password (matches ``LANGFUSE_INIT_USER_PASSWORD``).
    LANGFUSE_ORG_ID           Organization slug to (re)use. Default ``aiflow-dev``.
    LANGFUSE_PROJECT_ID       Project slug to (re)use. Default ``aiflow-dev``.
    LANGFUSE_SEEDED_PUBLIC_KEY  Optional pre-seeded public key (echoed through when
    LANGFUSE_SEEDED_SECRET_KEY  both are set — lets the compose env pin the keypair
                                so restarts don't invalidate Vault entries).

Usage (inside compose)::

    docker compose -f docker-compose.langfuse.yml --env-file .env.langfuse \\
        --profile bootstrap run --rm langfuse-init

Usage (host)::

    LANGFUSE_HOST=http://localhost:3000 \\
    LANGFUSE_ADMIN_EMAIL=admin@aiflow.dev \\
    LANGFUSE_ADMIN_PASSWORD=aiflow-dev-password \\
    python scripts/bootstrap_langfuse.py
"""

from __future__ import annotations

import os
import sys
import time
from typing import Any

import requests

HOST = os.environ.get("LANGFUSE_HOST", "http://localhost:3000").rstrip("/")
EMAIL = os.environ.get("LANGFUSE_ADMIN_EMAIL", "admin@aiflow.dev")
PASSWORD = os.environ.get("LANGFUSE_ADMIN_PASSWORD", "aiflow-dev-password")
ORG_ID = os.environ.get("LANGFUSE_ORG_ID", "aiflow-dev")
PROJECT_ID = os.environ.get("LANGFUSE_PROJECT_ID", "aiflow-dev")
SEEDED_PUBLIC = os.environ.get("LANGFUSE_SEEDED_PUBLIC_KEY", "")
SEEDED_SECRET = os.environ.get("LANGFUSE_SEEDED_SECRET_KEY", "")

READY_TIMEOUT_S = 120
READY_POLL_S = 2


def _log(msg: str) -> None:
    sys.stderr.write(f"[bootstrap_langfuse] {msg}\n")
    sys.stderr.flush()


def _wait_for_ready(session: requests.Session) -> None:
    deadline = time.monotonic() + READY_TIMEOUT_S
    last_err: Exception | None = None
    while time.monotonic() < deadline:
        try:
            resp = session.get(f"{HOST}/api/public/health", timeout=5)
            if resp.status_code == 200:
                return
            last_err = RuntimeError(f"health returned {resp.status_code}")
        except requests.RequestException as exc:
            last_err = exc
        time.sleep(READY_POLL_S)
    raise SystemExit(f"Langfuse not ready at {HOST} after {READY_TIMEOUT_S}s: {last_err!r}")


def _sign_in(session: requests.Session) -> bool:
    """Attempt sign-in via Langfuse's credential provider. Returns True on success."""
    # Langfuse uses NextAuth credentials provider. We bypass CSRF by using the
    # callback endpoint directly — acceptable for the dev bootstrap container.
    try:
        csrf = session.get(f"{HOST}/api/auth/csrf", timeout=10).json().get("csrfToken", "")
    except (requests.RequestException, ValueError) as exc:
        _log(f"csrf fetch failed: {exc!r}")
        return False
    resp = session.post(
        f"{HOST}/api/auth/callback/credentials",
        data={"email": EMAIL, "password": PASSWORD, "csrfToken": csrf, "json": "true"},
        timeout=15,
        allow_redirects=False,
    )
    ok = resp.status_code in (200, 302) and any(
        c.name.startswith("next-auth") for c in session.cookies
    )
    if not ok:
        _log(f"sign-in failed (status={resp.status_code}, cookies={list(session.cookies.keys())})")
    return ok


def _emit_keypair(public_key: str, secret_key: str, source: str) -> None:
    # stdout: machine-parseable KEY=VALUE lines consumed by seed_vault_dev.py
    sys.stdout.write(f"LANGFUSE_BOOTSTRAP_PUBLIC_KEY={public_key}\n")
    sys.stdout.write(f"LANGFUSE_BOOTSTRAP_SECRET_KEY={secret_key}\n")
    sys.stdout.flush()
    _log(f"emitted keypair from {source} (public={public_key[:10]}..., secret=sk-***)")


def _probe_seeded_keys() -> tuple[str, str] | None:
    """If the compose env pre-seeded a keypair, smoke-test it against the API."""
    if not (SEEDED_PUBLIC and SEEDED_SECRET):
        return None
    resp = requests.get(
        f"{HOST}/api/public/projects",
        auth=(SEEDED_PUBLIC, SEEDED_SECRET),
        timeout=10,
    )
    if resp.status_code == 200:
        return (SEEDED_PUBLIC, SEEDED_SECRET)
    _log(f"seeded keypair rejected (status={resp.status_code}); falling back to discovery")
    return None


def _list_api_keys_via_session(session: requests.Session) -> list[dict[str, Any]]:
    """Discover API keys for the bootstrap project via the authenticated TRPC surface."""
    # Langfuse exposes project API-key management under /api/trpc/projectApiKeys.all
    # (batched TRPC). We query via GET with input json payload.
    params = {
        "batch": "1",
        "input": '{"0":{"json":{"projectId":"' + PROJECT_ID + '"}}}',
    }
    resp = session.get(f"{HOST}/api/trpc/projectApiKeys.all", params=params, timeout=15)
    if resp.status_code != 200:
        _log(f"projectApiKeys.all failed: status={resp.status_code} body={resp.text[:200]}")
        return []
    try:
        payload = resp.json()
        return payload[0]["result"]["data"]["json"] or []
    except (KeyError, IndexError, ValueError) as exc:
        _log(f"projectApiKeys.all parse failed: {exc!r}")
        return []


def _create_api_key_via_session(session: requests.Session) -> tuple[str, str] | None:
    """Create a new API key via the authenticated TRPC endpoint."""
    body = {"0": {"json": {"projectId": PROJECT_ID, "note": "bootstrap"}}}
    resp = session.post(
        f"{HOST}/api/trpc/projectApiKeys.create?batch=1",
        json=body,
        timeout=15,
    )
    if resp.status_code != 200:
        _log(f"projectApiKeys.create failed: status={resp.status_code} body={resp.text[:200]}")
        return None
    try:
        payload = resp.json()
        data = payload[0]["result"]["data"]["json"]
        return (data["publicKey"], data["secretKey"])
    except (KeyError, IndexError, ValueError) as exc:
        _log(f"projectApiKeys.create parse failed: {exc!r}")
        return None


def main() -> int:
    session = requests.Session()
    _log(f"waiting for {HOST}/api/public/health ...")
    _wait_for_ready(session)
    _log("langfuse is ready")

    # Preferred path: the compose env pinned the keypair. Trust + echo if it works.
    seeded = _probe_seeded_keys()
    if seeded is not None:
        _emit_keypair(seeded[0], seeded[1], "LANGFUSE_SEEDED_*")
        return 0

    # Fallback path: sign in as admin, reuse existing key if one exists, else create.
    if not _sign_in(session):
        _log(
            "could not sign in as admin. Either run the Langfuse UI once to create "
            f"user {EMAIL!r}, or set LANGFUSE_SEEDED_PUBLIC_KEY + "
            "LANGFUSE_SEEDED_SECRET_KEY in .env.langfuse."
        )
        return 2

    keys = _list_api_keys_via_session(session)
    if keys:
        # Existing keys — only publicKey is returned by `all`; we cannot recover the
        # secret. Instruct operator to set LANGFUSE_SEEDED_* or rotate via the UI.
        public_only = keys[0].get("publicKey", "")
        _log(
            f"existing API key found (publicKey={public_only}); secretKey not recoverable. "
            "Either paste the matching secret into LANGFUSE_SEEDED_SECRET_KEY + "
            "LANGFUSE_SEEDED_PUBLIC_KEY, or delete it via the Langfuse UI and re-run."
        )
        return 3

    created = _create_api_key_via_session(session)
    if created is None:
        return 4
    _emit_keypair(created[0], created[1], "projectApiKeys.create")
    return 0


if __name__ == "__main__":
    sys.exit(main())
