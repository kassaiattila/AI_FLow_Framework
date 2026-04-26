"""DocTypeRegistry — Sprint V SV-1 skeleton.

YAML-driven doc-type catalog with per-tenant override support.

Bootstrap descriptors are loaded from ``data/doctypes/<name>.yaml``;
per-tenant overrides from ``data/doctypes/_tenant/<tenant_id>/<name>.yaml``.
When a tenant override exists it fully replaces the bootstrap descriptor for
that tenant (no merge). Operators can ``register_doctype(...)`` at runtime
for testing; the in-memory registry takes precedence over disk.

Invalid YAML or Pydantic parse error → log warning + skip + continue.
The service must keep working even if a single descriptor is malformed.

SV-2 fills in real descriptors at ``data/doctypes/hu_invoice.yaml`` etc.
SV-1 only ships the loader skeleton + tests on synthetic descriptors.
"""

from __future__ import annotations

from pathlib import Path
from threading import RLock
from typing import Any

import structlog
import yaml
from pydantic import ValidationError

from aiflow.contracts.doc_recognition import DocTypeDescriptor

__all__ = ["DocTypeRegistry"]

logger = structlog.get_logger(__name__)


class DocTypeRegistry:
    """Tenant-aware registry for :class:`DocTypeDescriptor`."""

    def __init__(
        self,
        bootstrap_dir: Path,
        tenant_overrides_dir: Path | None = None,
    ) -> None:
        self._bootstrap_dir = Path(bootstrap_dir)
        self._tenant_overrides_dir = (
            Path(tenant_overrides_dir) if tenant_overrides_dir is not None else None
        )
        self._lock = RLock()
        self._bootstrap_cache: dict[str, DocTypeDescriptor] | None = None
        # tenant_id -> {name -> descriptor}
        self._tenant_cache: dict[str, dict[str, DocTypeDescriptor]] = {}
        # In-memory registrations (highest precedence). tenant_id None == global.
        self._runtime_overrides: dict[tuple[str | None, str], DocTypeDescriptor] = {}

    # ------------------------------------------------------------------
    # Loading helpers
    # ------------------------------------------------------------------

    def _load_yaml_file(self, path: Path) -> DocTypeDescriptor | None:
        """Load + Pydantic-validate a single YAML descriptor.

        Returns ``None`` on any failure (logs a warning). Never raises.
        """
        try:
            text = path.read_text(encoding="utf-8")
            payload = yaml.safe_load(text)
        except (OSError, yaml.YAMLError) as exc:
            logger.warning(
                "doctype_registry.yaml_parse_failed",
                path=str(path),
                error=str(exc)[:200],
            )
            return None

        if not isinstance(payload, dict):
            logger.warning(
                "doctype_registry.yaml_not_a_mapping",
                path=str(path),
                got_type=type(payload).__name__,
            )
            return None

        try:
            descriptor = DocTypeDescriptor.model_validate(payload)
        except ValidationError as exc:
            logger.warning(
                "doctype_registry.descriptor_validation_failed",
                path=str(path),
                errors=exc.errors()[:5],
            )
            return None

        return descriptor

    def _load_dir(self, directory: Path) -> dict[str, DocTypeDescriptor]:
        """Load every ``*.yaml`` in ``directory`` (non-recursive). Skips ``_*``."""
        out: dict[str, DocTypeDescriptor] = {}
        if not directory.exists() or not directory.is_dir():
            return out
        for yaml_path in sorted(directory.glob("*.yaml")):
            if yaml_path.name.startswith("_"):
                continue
            descriptor = self._load_yaml_file(yaml_path)
            if descriptor is None:
                continue
            if descriptor.name in out:
                logger.warning(
                    "doctype_registry.duplicate_name_in_dir",
                    name=descriptor.name,
                    path=str(yaml_path),
                )
            out[descriptor.name] = descriptor
        return out

    def _ensure_bootstrap(self) -> dict[str, DocTypeDescriptor]:
        if self._bootstrap_cache is None:
            with self._lock:
                if self._bootstrap_cache is None:
                    self._bootstrap_cache = self._load_dir(self._bootstrap_dir)
                    logger.info(
                        "doctype_registry.bootstrap_loaded",
                        count=len(self._bootstrap_cache),
                        dir=str(self._bootstrap_dir),
                    )
        return self._bootstrap_cache

    def _ensure_tenant(self, tenant_id: str) -> dict[str, DocTypeDescriptor]:
        if self._tenant_overrides_dir is None:
            return {}
        if tenant_id not in self._tenant_cache:
            with self._lock:
                if tenant_id not in self._tenant_cache:
                    tenant_dir = self._tenant_overrides_dir / tenant_id
                    self._tenant_cache[tenant_id] = self._load_dir(tenant_dir)
                    logger.debug(
                        "doctype_registry.tenant_loaded",
                        tenant_id=tenant_id,
                        count=len(self._tenant_cache[tenant_id]),
                    )
        return self._tenant_cache[tenant_id]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def list_doctypes(self, tenant_id: str | None = None) -> list[DocTypeDescriptor]:
        """Return the set of doc-types visible to ``tenant_id``.

        Resolution order (highest precedence first):
            1. Runtime ``register_doctype`` (per-tenant or global).
            2. Tenant overrides directory (if ``tenant_id`` supplied).
            3. Bootstrap directory.
        """
        merged: dict[str, DocTypeDescriptor] = {}
        merged.update(self._ensure_bootstrap())
        if tenant_id is not None:
            merged.update(self._ensure_tenant(tenant_id))
        # Runtime overrides last (highest precedence).
        for (scope_tenant, name), descriptor in self._runtime_overrides.items():
            if scope_tenant is None or scope_tenant == tenant_id:
                merged[name] = descriptor
        return sorted(merged.values(), key=lambda d: d.name)

    def get_doctype(self, name: str, tenant_id: str | None = None) -> DocTypeDescriptor | None:
        """Return a single descriptor or ``None``.

        Resolution: runtime override > tenant override > bootstrap.
        """
        # Runtime tenant-scoped first
        if tenant_id is not None and (tenant_id, name) in self._runtime_overrides:
            return self._runtime_overrides[(tenant_id, name)]
        # Runtime global
        if (None, name) in self._runtime_overrides:
            return self._runtime_overrides[(None, name)]
        if tenant_id is not None:
            tenant = self._ensure_tenant(tenant_id)
            if name in tenant:
                return tenant[name]
        bootstrap = self._ensure_bootstrap()
        return bootstrap.get(name)

    def register_doctype(self, descriptor: DocTypeDescriptor, tenant_id: str | None = None) -> None:
        """In-memory registration. Highest precedence over disk."""
        with self._lock:
            self._runtime_overrides[(tenant_id, descriptor.name)] = descriptor
        logger.info(
            "doctype_registry.registered",
            name=descriptor.name,
            tenant_id=tenant_id,
            scope="tenant" if tenant_id else "global",
        )

    def invalidate_cache(self) -> None:
        """Drop bootstrap + tenant caches so the next read re-loads from disk."""
        with self._lock:
            self._bootstrap_cache = None
            self._tenant_cache.clear()
        logger.info("doctype_registry.cache_invalidated")

    def to_summary(self, tenant_id: str | None = None) -> dict[str, Any]:
        """Return a small JSON-able summary for /api/v1/document-recognizer/doctypes."""
        descriptors = self.list_doctypes(tenant_id=tenant_id)
        return {
            "count": len(descriptors),
            "items": [
                {
                    "name": d.name,
                    "display_name": d.display_name,
                    "language": d.language,
                    "category": d.category,
                    "version": d.version,
                    "pii_level": d.pii_level,
                    "field_count": len(d.extraction.fields),
                }
                for d in descriptors
            ],
        }
