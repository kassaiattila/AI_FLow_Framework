Generate a FastAPI endpoint that the AIFlow admin UI will consume.

## Context
The backend API is at `src/aiflow/api/v1/` using FastAPI.
The admin UI (`aiflow-admin/`) calls these via Vite proxy: `/api` → `localhost:8102`.
Data provider: `aiflow-admin/src/dataProvider.ts` maps resources to API endpoints.
Existing routers: health, auth, workflows, chat_completions, feedback, runs, costs,
skills_api, documents, emails, process_docs, cubix (12 router files).

## Ask me for:
1. Endpoint path (e.g., `/api/v1/services/rag/collections`, `/api/v1/runs/{id}/cancel`)
2. HTTP method (GET/POST/PUT/DELETE)
3. Request/response models (Pydantic)
4. Data source (database query, service call, file-based)
5. Whether it's a new service endpoint (check existing routers in `src/aiflow/api/v1/`)

## Rules:
- Use FastAPI router pattern (match existing endpoints in api/v1/)
- Pydantic models for request and response
- Async handlers (async def)
- structlog for logging
- Register router in app.py
- **Response MUST include `source: "backend"|"demo"` field**
- **Route ordering: specific routes BEFORE catch-all `/{path:path}` routes!**
- **Blocking I/O (Docling, fitz) MUST use `asyncio.to_thread()`**
- **SSE endpoints: use StreamingResponse with Cache-Control: no-cache headers**
- Update `aiflow-admin/src/dataProvider.ts` RESOURCE_MAP if new resource

## Generate:
1. FastAPI endpoint file (`src/aiflow/api/v1/{name}.py`)
2. dataProvider RESOURCE_MAP entry if needed
3. **curl test command** to verify the endpoint returns real data

## Verification:
- [ ] `curl` test returns real data (NOT stub/placeholder)
- [ ] Response has `source` field
- [ ] Route registered in app.py
- [ ] No route ordering conflict with catch-all routes

## VALOS teszteles (SOHA ne mock/fake!):
- **curl hivás KOTELEZO** — NEM csak `200 OK`, hanem a valasz TARTALMAT ellenorizd!
  ```bash
  curl -s http://localhost:8102/api/v1/{endpoint} | python -m json.tool
  ```
- **source mezo:** A valasz `"source": "backend"` kell legyen — ha `"demo"` jon, az NEM elfogadhato
- **Ha DB-t hasznal:** valos PostgreSQL query, valos adat a valaszban
- **Ha mas service-t hiv:** valos service hivas (NEM hardcoded response)
- **Az endpoint CSAK AKKOR "KESZ" ha valos adatot ad vissza curl tesztnel**

ARGUMENTS: $ARGUMENTS
