Generate a FastAPI endpoint that the AIFlow UI will consume.

## Context
The backend API is at `src/aiflow/api/v1/` using FastAPI.
The UI (Next.js) calls these endpoints via `aiflow-ui/src/lib/api.ts`.
Existing endpoints: health.py, chat_completions.py, feedback.py, workflows.py.

## Ask me for:
1. Endpoint path (e.g., `/api/v1/runs`, `/api/v1/costs/summary`)
2. HTTP method (GET/POST)
3. Request/response models (Pydantic)
4. Data source (database query, in-memory, file-based)

## Rules:
- Use FastAPI router pattern (match existing endpoints in api/v1/)
- Pydantic models for request and response
- Async handlers (async def)
- structlog for logging
- Register router in app.py
- Add corresponding TypeScript types in `aiflow-ui/src/lib/types.ts`
- Add fetch function in `aiflow-ui/src/lib/api.ts`

## Generate:
1. FastAPI endpoint file (`src/aiflow/api/v1/{name}.py`)
2. TypeScript types update
3. API client function update

ARGUMENTS: $ARGUMENTS
