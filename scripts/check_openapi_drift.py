"""Detect OpenAPI drift between the committed spec and the live in-process app.

Sprint O FU (Sprint N carry promoted) — addresses the SO-6 hot-reload-stale
uvicorn regression where the running API serves an older response model
than the source tree. This script:

1. Imports ``create_app()`` from the current source tree and dumps its
   OpenAPI spec to memory.
2. Loads the committed snapshot at ``docs/api/openapi.json``.
3. Diffs:
   - paths set (added / removed)
   - tags set (added / removed)
   - schemas set (added / removed)
   - per-schema property set for a configurable watchlist of "important"
     response models (default: ``EmailDetailResponse``,
     ``BudgetView``, ``ClassificationResult``).
4. Prints a structured report and exits non-zero on any drift.

Intended use:

- Local: ``.venv/Scripts/python.exe scripts/check_openapi_drift.py``
  before committing API changes — catches forgotten ``docs/api/openapi.json``
  refresh.
- CI: same command in a ``lint`` / ``check`` step.

Usage::

    .venv/Scripts/python.exe scripts/check_openapi_drift.py            # default watchlist
    .venv/Scripts/python.exe scripts/check_openapi_drift.py --update   # rewrite docs/api/openapi.json from current source

The ``--update`` flag is the operator's "yes I changed the API on purpose,
refresh the snapshot" lever — equivalent to ``black --write`` for OpenAPI.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

SNAPSHOT_PATH = REPO_ROOT / "docs" / "api" / "openapi.json"

# Response models worth a stricter property-level diff. Add to this when a
# schema becomes consumer-facing enough that silent additions / removals
# hurt downstream clients (UI types, partner integrations, etc.).
WATCHED_SCHEMAS: tuple[str, ...] = (
    "EmailDetailResponse",
    "BudgetView",
    "ClassificationResult",
    "TenantBudgetGetResponse",
)


def _live_spec() -> dict:
    """Build the OpenAPI spec by importing the live app from source."""
    from aiflow.api.app import create_app

    app = create_app()
    return app.openapi()


def _snapshot_spec() -> dict:
    return json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))


def _paths(spec: dict) -> set[str]:
    return set(spec.get("paths", {}).keys())


def _tags(spec: dict) -> set[str]:
    out: set[str] = set()
    for path_item in spec.get("paths", {}).values():
        for op in path_item.values():
            if isinstance(op, dict):
                out.update(op.get("tags", []))
    return out


def _schemas(spec: dict) -> set[str]:
    # FastAPI 0.115+ generates "-Input" and "-Output" suffix variants for a
    # Pydantic model when its serialised shape differs between request body
    # and response. Whether the split happens depends on the Pydantic minor
    # version installed (e.g. Linux CI may resolve a different patch than
    # Windows local dev), so we normalise: strip both suffixes and dedupe.
    # The drift gate still catches genuine schema additions/removals.
    raw = set(spec.get("components", {}).get("schemas", {}).keys())
    out: set[str] = set()
    for name in raw:
        if name.endswith("-Input"):
            out.add(name[: -len("-Input")])
        elif name.endswith("-Output"):
            out.add(name[: -len("-Output")])
        else:
            out.add(name)
    return out


def _schema_properties(spec: dict, name: str) -> set[str]:
    schema = spec.get("components", {}).get("schemas", {}).get(name) or {}
    return set((schema.get("properties") or {}).keys())


def _diff(label: str, snap: set, live: set) -> tuple[set, set]:
    added = live - snap
    removed = snap - live
    if added or removed:
        print(f"\n[{label}]")
        if added:
            print(f"  + added ({len(added)}): {sorted(added)}")
        if removed:
            print(f"  - removed ({len(removed)}): {sorted(removed)}")
    return added, removed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--update",
        action="store_true",
        help="Overwrite docs/api/openapi.json with the live spec.",
    )
    args = parser.parse_args(argv)

    live = _live_spec()

    if args.update:
        SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
        SNAPSHOT_PATH.write_text(json.dumps(live, indent=2, sort_keys=True), encoding="utf-8")
        print(f"[updated] {SNAPSHOT_PATH.relative_to(REPO_ROOT)}")
        return 0

    if not SNAPSHOT_PATH.exists():
        print(
            f"[error] no committed snapshot at {SNAPSHOT_PATH} — run with --update", file=sys.stderr
        )
        return 2

    snapshot = _snapshot_spec()

    drift = False

    p_added, p_removed = _diff("paths", _paths(snapshot), _paths(live))
    drift = drift or bool(p_added or p_removed)

    t_added, t_removed = _diff("tags", _tags(snapshot), _tags(live))
    drift = drift or bool(t_added or t_removed)

    s_added, s_removed = _diff("schemas", _schemas(snapshot), _schemas(live))
    drift = drift or bool(s_added or s_removed)

    for name in WATCHED_SCHEMAS:
        snap_props = _schema_properties(snapshot, name)
        live_props = _schema_properties(live, name)
        if snap_props or live_props:
            added, removed = _diff(f"schema {name}", snap_props, live_props)
            drift = drift or bool(added or removed)

    if drift:
        print(
            "\n[drift] OpenAPI spec drifted from docs/api/openapi.json.\n"
            "If the change is intentional, refresh the snapshot:\n"
            "    .venv/Scripts/python.exe scripts/check_openapi_drift.py --update",
            file=sys.stderr,
        )
        return 1

    print(
        "[ok] OpenAPI spec matches docs/api/openapi.json (paths / tags / schemas / watched models)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
