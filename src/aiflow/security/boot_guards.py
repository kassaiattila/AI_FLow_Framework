"""Sprint W SW-4 (SM-FU-2) — boot-time security guards.

Refuses to start the FastAPI app if a misconfiguration would leak prod
secrets via dev-grade auth. Today the only guard is the **Vault root token
in production** check; future guards (e.g. CORS wildcard in prod, JWT
secret env-only in prod) plug into the same module.

Usage in :func:`aiflow.api.app.create_app` lifespan startup::

    from aiflow.security.boot_guards import enforce_boot_guards

    @asynccontextmanager
    async def lifespan(app):
        enforce_boot_guards()        # raises BootGuardError on violation
        ...

The guard reads :class:`AIFlowSettings` (already populated from env) so
operators can opt-out via the env override below — but every override
emits a structured warning so misuse is auditable.

Environment variables:

* ``AIFLOW_ENVIRONMENT``                            — values ``dev`` /
  ``test`` / ``staging`` / ``prod``. The guard fires only when this is
  ``prod``.
* ``AIFLOW_VAULT__ENABLED``                         — guard is a no-op
  unless Vault is enabled.
* ``AIFLOW_VAULT__TOKEN``                           — the token to vet.
* ``AIFLOW_VAULT__ALLOW_ROOT_TOKEN_IN_PROD``        — set to ``true`` to
  bypass the check (emergency restoration only). Logged at WARN.

Detection heuristic:

* Exact match against the dev seed token literal ``aiflow-dev-root``
  (set by ``scripts/seed_vault_dev.py``).
* Token starts with ``hvs.`` (Vault native root-token prefix; AppRole-
  derived tokens use ``hvs.CAES`` prefix that we explicitly *do* allow).

The latter is intentionally conservative — operators with a `hvs.` token
on prod are most likely using the dev root. AppRole-issued tokens have
the ``hvs.CAES`` shape AND are accompanied by ``role_id`` + ``secret_id``
on the settings; the guard uses the presence of those as a positive
signal.
"""

from __future__ import annotations

import structlog

from aiflow.core.config import AIFlowSettings, get_settings

__all__ = [
    "BootGuardError",
    "enforce_boot_guards",
    "vault_root_token_in_prod_violation",
]

logger = structlog.get_logger(__name__)

_DEV_ROOT_TOKEN_LITERAL = "aiflow-dev-root"


class BootGuardError(RuntimeError):
    """Raised when a boot guard refuses to let the app start."""


def vault_root_token_in_prod_violation(settings: AIFlowSettings) -> str | None:
    """Return a violation message if the prod-vs-vault-root combination is bad.

    Returns ``None`` when no violation is detected (also when the guard
    is opt-out via env).
    """
    import os

    if settings.environment != "prod":
        return None
    if not settings.vault.enabled:
        return None

    bypass = settings.vault.allow_root_token_in_prod or os.getenv(
        "AIFLOW_VAULT__ALLOW_ROOT_TOKEN_IN_PROD", ""
    ).lower() in ("1", "true", "yes")
    token_obj = settings.vault.token
    raw_token = token_obj.get_secret_value() if token_obj is not None else ""

    has_approle = bool(settings.vault.role_id and settings.vault.secret_id)

    looks_dev = raw_token == _DEV_ROOT_TOKEN_LITERAL
    looks_root_prefix = raw_token.startswith("hvs.") and not raw_token.startswith("hvs.CAES")

    if not (looks_dev or looks_root_prefix):
        return None

    if has_approle:
        return None  # operator passed AppRole creds — assume token is auxiliary

    if bypass:
        logger.warning(
            "boot_guards.vault_root_token_in_prod_bypass",
            reason="AIFLOW_VAULT__ALLOW_ROOT_TOKEN_IN_PROD=true",
        )
        return None

    if looks_dev:
        return (
            "AIFLOW_ENVIRONMENT=prod refuses to boot with the dev seed token "
            "AIFLOW_VAULT__TOKEN=aiflow-dev-root. Production deployments MUST "
            "use AppRole authentication (set AIFLOW_VAULT__ROLE_ID + "
            "AIFLOW_VAULT__SECRET_ID). See docs/runbooks/vault_approle_iac.md."
        )
    return (
        "AIFLOW_ENVIRONMENT=prod refuses to boot with a Vault root token "
        "(AIFLOW_VAULT__TOKEN=hvs.*). Production deployments MUST use AppRole "
        "authentication (set AIFLOW_VAULT__ROLE_ID + AIFLOW_VAULT__SECRET_ID). "
        "See docs/runbooks/vault_approle_iac.md."
    )


def enforce_boot_guards(settings: AIFlowSettings | None = None) -> None:
    """Run every boot guard. Raises :class:`BootGuardError` on first violation."""
    settings = settings or get_settings()

    violation = vault_root_token_in_prod_violation(settings)
    if violation:
        logger.error("boot_guards.violation", message=violation)
        raise BootGuardError(violation)

    logger.info("boot_guards.passed", environment=settings.environment)
