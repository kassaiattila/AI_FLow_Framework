"""Background token rotation for :class:`VaultSecretProvider`.

A lean daemon-thread rotator that periodically checks the token TTL and
calls ``renew_token`` when the remaining lease drops below a configurable
fraction of the renewal increment. Uses :class:`threading.Event` for both
pacing and clean shutdown, which keeps the rotation loop deterministic for
unit tests and avoids pinning to the APScheduler 4.x alpha API currently
installed.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any

import structlog

from aiflow.security.secrets import VaultSecretProvider

__all__ = ["VaultTokenRotator", "start_token_rotation"]

logger = structlog.get_logger(__name__)

_DEFAULT_CHECK_INTERVAL: float = 3600.0
_DEFAULT_RENEW_INCREMENT: int = 30 * 24 * 3600
_DEFAULT_RENEW_AT_FRACTION: float = 0.2


class VaultTokenRotator:
    """Daemon-thread token rotator.

    Every ``check_interval`` seconds the rotator asks the provider for the
    current token TTL. When that TTL falls below
    ``renew_increment * renew_at_fraction`` the provider's
    ``renew_token(increment=renew_increment)`` is invoked.
    """

    def __init__(
        self,
        provider: VaultSecretProvider,
        check_interval: float = _DEFAULT_CHECK_INTERVAL,
        renew_increment: int = _DEFAULT_RENEW_INCREMENT,
        renew_at_fraction: float = _DEFAULT_RENEW_AT_FRACTION,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if check_interval <= 0:
            raise ValueError("check_interval must be > 0")
        if renew_increment <= 0:
            raise ValueError("renew_increment must be > 0")
        if not 0 < renew_at_fraction < 1:
            raise ValueError("renew_at_fraction must be in the open interval (0, 1)")

        self._provider = provider
        self._check_interval = check_interval
        self._renew_increment = renew_increment
        self._renew_at_fraction = renew_at_fraction
        self._clock = clock
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    # -- Lifecycle ---------------------------------------------------------

    def start(self) -> None:
        """Spawn the daemon thread if not already running."""
        if self._thread is not None and self._thread.is_alive():
            logger.warning("vault_token_rotator_already_running")
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._loop,
            name="vault-token-rotator",
            daemon=True,
        )
        self._thread.start()
        logger.info(
            "vault_token_rotator_started",
            check_interval_seconds=self._check_interval,
            renew_increment_seconds=self._renew_increment,
            renew_at_fraction=self._renew_at_fraction,
        )

    def stop(self, timeout: float | None = 5.0) -> None:
        """Signal the daemon to exit and join."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)
            self._thread = None
        logger.info("vault_token_rotator_stopped")

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    # -- Single cycle (public for unit tests) ------------------------------

    def check_once(self) -> bool:
        """Run one TTL check; renew if under threshold. Returns True on renew."""
        ttl = self._provider.token_ttl()
        if ttl is None:
            logger.warning("vault_token_rotator_ttl_unavailable")
            return False

        threshold = self._renew_increment * self._renew_at_fraction
        if ttl < threshold:
            logger.info(
                "vault_token_renew_triggered",
                current_ttl_seconds=ttl,
                threshold_seconds=int(threshold),
            )
            self._provider.renew_token(increment=self._renew_increment)
            return True

        logger.debug(
            "vault_token_renew_skipped",
            current_ttl_seconds=ttl,
            threshold_seconds=int(threshold),
        )
        return False

    # -- Loop --------------------------------------------------------------

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.check_once()
            except Exception as exc:  # noqa: BLE001
                logger.error("vault_token_rotator_error", error=str(exc))
            # Event.wait returns True as soon as stop() is called → prompt shutdown.
            self._stop_event.wait(timeout=self._check_interval)


def start_token_rotation(
    provider: VaultSecretProvider,
    **kwargs: Any,
) -> VaultTokenRotator:
    """Build a :class:`VaultTokenRotator`, start it, return the handle."""
    rotator = VaultTokenRotator(provider=provider, **kwargs)
    rotator.start()
    return rotator
