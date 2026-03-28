"""DrawIO stencil catalog loader.

Loads the stencil_catalog.json which contains 3423 shapes
across 52 namespaces, encoded as deflate+base64 SVG definitions.
Used as fallback when native mxgraph references don't render in CLI export.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

__all__ = ["load_stencil_catalog", "get_stencil"]

_CATALOG_PATH = Path(__file__).parent / "stencil_catalog.json"
_catalog: dict[str, dict[str, Any]] | None = None


def load_stencil_catalog() -> dict[str, dict[str, Any]]:
    """Load the stencil catalog from JSON. Cached after first load."""
    global _catalog
    if _catalog is None:
        if not _CATALOG_PATH.exists():
            return {}
        with open(_CATALOG_PATH, encoding="utf-8") as f:
            _catalog = json.load(f)
    return _catalog


def get_stencil(namespace: str, shape_name: str) -> dict[str, Any] | None:
    """Get a specific stencil shape definition.

    Args:
        namespace: e.g. "mxgraph.networks"
        shape_name: e.g. "server"

    Returns:
        Dict with 'w', 'h', 'b64' keys or None if not found.
    """
    catalog = load_stencil_catalog()
    ns_shapes = catalog.get(namespace, {})
    return ns_shapes.get(shape_name)


def list_namespaces() -> list[str]:
    """List all available stencil namespaces."""
    return sorted(load_stencil_catalog().keys())


def list_shapes(namespace: str) -> list[str]:
    """List all shapes in a namespace."""
    catalog = load_stencil_catalog()
    return sorted(catalog.get(namespace, {}).keys())
