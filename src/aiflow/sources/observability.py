"""Canonical observability events for source adapters (Phase 1c Day 3 — C4).

Every source adapter emits its own historical per-adapter event name
(`file_adapter_acknowledged`, `folder_adapter_rejected`, ...). Dashboards
and alerts therefore cannot pivot by source uniformly. This module defines
a single canonical emitter that every adapter now additionally calls at
the enqueue / acknowledge / reject transitions.

Canonical event names:
    source.package_received  — adapter has taken ownership of a package
                               (enqueue for push adapters, acknowledge for
                               pull adapters).
    source.package_rejected  — adapter has terminated a package with a
                               reason (size guard, parse failure,
                               signature mismatch, explicit reject call).

Stable log-record shape (consumer contract):
    event:        "source.package_received" | "source.package_rejected"
    package_id:   str (UUID)
    tenant_id:    str
    source_type:  "file" | "folder" | "batch" | "api" | "email"
    **extra:      aggregate, NON-PII context only (reason codes, counts).

PII tilalom — the helper deliberately accepts only `**extra`, never the
raw package payload. Callers MUST NOT pass "password", "hmac_secret",
raw "signature", email "body", or file content. Reason codes
(e.g. `reason="signature_invalid"`) are allowed; the offending value is not.

Deprecation timeline:
    v1.4.2   — canonical events introduced alongside legacy per-adapter
               names (both emitted).
    v1.5.x   — legacy per-adapter events (`<kind>_adapter_acknowledged`,
               `<kind>_adapter_rejected`) are removed; dashboards must
               have migrated to `source.package_(received|rejected)` by
               then. Tracked in `01_PLAN/session_S73_v1_4_2_phase_1c_kickoff.md`
               Day 3 / architect condition C4.
"""

from __future__ import annotations

from typing import Any, Literal

import structlog

from aiflow.intake.package import IntakePackage

__all__ = [
    "CanonicalSourceEvent",
    "emit_package_event",
]

logger = structlog.get_logger(__name__)


CanonicalSourceEvent = Literal["source.package_received", "source.package_rejected"]


def emit_package_event(
    event: CanonicalSourceEvent,
    package: IntakePackage,
    source_type: str,
    **extra: Any,
) -> None:
    """Emit the canonical source-adapter package event.

    Args:
        event: One of the canonical event names
            (`source.package_received`, `source.package_rejected`).
        package: The IntakePackage that just transitioned.
        source_type: Short source identifier
            (`file`, `folder`, `batch`, `api`, `email`).
        **extra: Non-PII context (reason codes, counts). MUST NOT contain
            raw payload, credentials, or signatures — see module docstring.
    """
    logger.info(
        event,
        package_id=str(package.package_id),
        tenant_id=package.tenant_id,
        source_type=source_type,
        **extra,
    )
