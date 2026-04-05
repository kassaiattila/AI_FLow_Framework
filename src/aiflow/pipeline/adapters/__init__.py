"""Pipeline adapters — auto-discovery of service adapter modules."""

from __future__ import annotations

import importlib
import pkgutil

import structlog

logger = structlog.get_logger(__name__)

_discovered = False


def discover_adapters() -> list[str]:
    """Import all adapter modules in this package for self-registration.

    Returns list of imported module names.
    """
    global _discovered  # noqa: PLW0603
    if _discovered:
        return []

    imported: list[str] = []
    package = importlib.import_module(__name__)
    for _importer, modname, _ispkg in pkgutil.iter_modules(
        package.__path__, prefix=f"{__name__}."
    ):
        if modname.endswith("_adapter"):
            try:
                importlib.import_module(modname)
                imported.append(modname)
            except Exception:
                logger.warning("adapter_import_failed", module=modname, exc_info=True)
    _discovered = True
    logger.info("adapters_discovered", count=len(imported), modules=imported)
    return imported
