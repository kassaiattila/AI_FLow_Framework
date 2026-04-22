# UC2 RAG — User Journey (Sprint J / S102)

> **Status:** Active  
> **Audience:** Admin users of the AIFlow dashboard  
> **Pages:** `aiflow-admin/src/pages-new/Rag.tsx`, `aiflow-admin/src/pages-new/RagDetail.tsx`  
> **Component:** `aiflow-admin/src/components/rag/ChunkViewer.tsx`

---

## 1. Entry points

- Sidebar → **"RAG"** → `/rag`.
- Post-create redirect → `/rag/:id`.

## 2. Primary flow (golden path)

| Step | User action | UI surface | API call |
|------|-------------|------------|----------|
| 1 | Open RAG menu | `Rag.tsx` — collections list (DataTable) | `GET /api/v1/rag/collections` |
| 2 | Click **"New Collection"** | Modal dialog: name*, description, language (hu/en) | — |
| 3 | Submit form | Dialog closes, auto-navigate to detail | `POST /api/v1/rag/collections` → `201` |
| 4 | View collection header | KPI cards (docs, chunks, queries, avg time, feedback) | `GET /api/v1/rag/collections/{id}` + `/stats` |
| 5 | **Ingest** tab — drag/drop PDF/DOCX/TXT/MD | Dropzone + per-file pipeline progress (upload→parse→chunk→embed→store) | `POST /api/v1/rag/collections/{id}/ingest-stream` (SSE) |
| 6 | **Chat** tab — enter question | Answer + sources accordion | `POST /api/v1/rag/collections/{id}/query` |
| 7 | 👍 / 👎 feedback | Toast confirmation | `POST /api/v1/rag/collections/{id}/feedback` |
| 8 | **Chunks** tab — browse | `ChunkViewer`: table (chunk_index, document, content excerpt, token_count, embedding_dim badge) + row-click modal with full text + metadata JSON | `GET /api/v1/rag/collections/{id}/chunks?limit&offset&q&document_name` |

## 3. Secondary flows

- **Delete collection** → row action → confirm dialog → `DELETE /collections/{id}` → list refetch.
- **Bulk delete** (checkboxes) → `POST /collections/delete-bulk`.
- **Delete document** (Ingest tab list) → `DELETE /collections/{id}/documents/{doc_name}` (or bulk: `documents/delete-bulk`).
- **Filter chunks** — search input + document filter in Chunks tab.

## 4. Live/Demo tag

Every API response carries `source: "backend"` (live). `PageLayout` surfaces this via `source` prop on the header — never silent mock (`feedback_no_silent_mock`).

## 5. Empty / error states

- **Empty collections** → EmptyState CTA "Create your first collection".
- **Empty chunks** → `aiflow.rag.noChunks` message.
- **Ingest error** (per-file) → red badge on `FileProgressRow`, error array rendered in summary.
- **Collection not found** → detail page `ErrorState` → back to list.

## 6. Acceptance criteria

- [x] Collection list renders with live `source` badge.
- [x] "New Collection" CTA creates a real DB row and navigates to detail.
- [x] Ingest SSE stream drives the per-file pipeline UI without blocking.
- [x] Chat tab produces LLM answer with sources.
- [x] Chunks tab pagination + search + document filter.
- [x] `ChunkViewer`: `embedding_dim` + `chunk_index` + `token_count` visible.
- [x] Row-click opens modal with full chunk + metadata JSON.
- [x] Feedback POST returns `{success: true}`.
- [x] Playwright E2E covers: login → list → create → header render → delete.

## 7. Out of scope (deferred)

- Retrieval baseline validation (`tests/fixtures/rag/baseline_*.json`) — deferred to S103.
- BGE-M3 Profile A UI (requires `vector(1024)` support in `rag_chunks.embedding`) — S103+.
- pgvector flex-dim column — S103+ alembic migration.

## 8. References

- Plan: `01_PLAN/110_USE_CASE_FIRST_REPLAN.md` §4 Sprint J.
- S101 migration: `alembic/versions/041_rag_chunks_embedding_dim.py`.
- Backend router: `src/aiflow/api/v1/rag_engine.py`.
