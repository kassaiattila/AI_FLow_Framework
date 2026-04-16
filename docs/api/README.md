# AIFlow API — OpenAPI Documentation

This directory contains the generated OpenAPI specification for the AIFlow FastAPI application.

- `openapi.json` — machine-readable spec (FastAPI source of truth mirror).
- `openapi.yaml` — human-readable spec.

## Regen workflow

Run from the repo root:

```bash
python scripts/export_openapi.py
```

The script boots `create_app()`, calls `app.openapi()`, and writes both files.

## Drift enforcement

CI job `openapi-drift` (`.github/workflows/ci-framework.yml`) regenerates the spec and fails the build if the checked-in files diverge from the live app. After any change to API routes, request/response models, or tags, regenerate and commit both files in the same PR.
