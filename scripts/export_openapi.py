#!/usr/bin/env python
"""Export OpenAPI schema from the AIFlow FastAPI application.

Usage:
    python scripts/export_openapi.py

Outputs:
    docs/api/openapi.json
    docs/api/openapi.yaml (if pyyaml installed)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

from aiflow.api.app import create_app  # noqa: E402


def main() -> None:
    app = create_app()
    schema = app.openapi()

    output_dir = project_root / "docs" / "api"
    output_dir.mkdir(parents=True, exist_ok=True)

    # JSON export
    json_path = output_dir / "openapi.json"
    json_path.write_text(json.dumps(schema, indent=2, ensure_ascii=False))
    endpoint_count = sum(
        len(methods) for path_item in schema.get("paths", {}).values() for methods in [path_item]
    )
    print(f"OpenAPI JSON exported: {json_path} ({endpoint_count} paths)")

    # YAML export (optional)
    try:
        import yaml

        yaml_path = output_dir / "openapi.yaml"
        yaml_path.write_text(yaml.dump(schema, allow_unicode=True, default_flow_style=False))
        print(f"OpenAPI YAML exported: {yaml_path}")
    except ImportError:
        print("pyyaml not installed — YAML export skipped")


if __name__ == "__main__":
    main()
