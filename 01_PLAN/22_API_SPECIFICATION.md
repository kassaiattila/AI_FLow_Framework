# AIFlow Framework -- REST API Specification

> **Version:** 1.0.0
> **Framework:** FastAPI (Python 3.12+)
> **Utolso frissites:** 2026-03-28
> **Megjegyzes:** Ez a dokumentum az AIFlow framework teljes REST API specifikaciojat tartalmazza.

---

## 1. API Conventions (Altalanos konvenciok)

| Tetel | Ertek |
|---|---|
| **Base URL** | `https://{host}/api/v1/` |
| **Verziozas** | URI-prefix: `/api/v1/`, `/api/v2/` stb. |
| **Content-Type** | `application/json` (minden request es response) |
| **Datumformatum** | ISO 8601 -- `2026-03-28T14:30:00Z` |
| **Karakterkodolas** | UTF-8 |
| **Autentikacio** | Bearer JWT token VAGY `X-API-Key` header |

### 1.1 Paginacio (Cursor-based)

Minden lista endpoint tamogatja a cursor-alapu lapozast:

```
GET /api/v1/workflows?cursor=eyJpZCI6MTAwfQ&limit=25
```

**Response envelope:**
```json
{
  "data": [ ... ],
  "pagination": {
    "next_cursor": "eyJpZCI6MTI1fQ",
    "prev_cursor": "eyJpZCI6NzV9",
    "limit": 25,
    "total_count": 342
  }
}
```

### 1.2 Standard Error Response Format

Minden hiba egysegesen az alabbi formatumban jon vissza:

```json
{
  "error": {
    "error_code": "WORKFLOW_NOT_FOUND",
    "message": "A megadott workflow nem talalhato.",
    "details": {
      "workflow_name": "data-pipeline-v2",
      "suggestion": "Ellenorizze a nevet a GET /api/v1/workflows listaban."
    },
    "request_id": "req_abc123def456",
    "timestamp": "2026-03-28T14:30:00Z"
  }
}
```

### 1.3 Altalanos HTTP Status Code-ok

| Kod | Jelentese |
|---|---|
| `200` | Sikeres muvelet |
| `201` | Eroforras letrehozva |
| `202` | Elfogadva (async feldolgozas indult) |
| `204` | Sikeres torles, nincs body |
| `400` | Hibas request (validacios hiba) |
| `401` | Nincs autentikacio |
| `403` | Nincs jogosultsag (RBAC) |
| `404` | Eroforras nem talalhato |
| `409` | Konfliktus (pl. duplikat nev) |
| `422` | Feldolgozhatatlan entitas |
| `429` | Rate limit tullepve |
| `500` | Szerver oldali hiba |

---

## 2. Authentication Endpoints (Autentikacio)

### 2.1 POST /api/v1/auth/login

Bejelentkezes email + jelszo alapjan, JWT token prost kap vissza.

- **Auth required:** Nem
- **Status codes:** `200`, `401`, `422`

**Request:**
```json
{
  "email": "admin@aiflow.local",
  "password": "secureP@ss123"
}
```

**Response (200):**
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJSUzI1NiIs...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "user": {
    "id": "usr_01HXYZ",
    "email": "admin@aiflow.local",
    "display_name": "Admin User",
    "role": "admin",
    "team_id": "team_01ABC"
  }
}
```

### 2.2 POST /api/v1/auth/refresh

Lejart access token megujitasa refresh token segitsegevel.

- **Auth required:** Nem (refresh token a body-ban)
- **Status codes:** `200`, `401`

**Request:**
```json
{
  "refresh_token": "eyJhbGciOiJSUzI1NiIs..."
}
```

**Response (200):**
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJSUzI1NiIs...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

### 2.3 GET /api/v1/auth/me

Az aktualis bejelentkezett felhasznalo adatai.

- **Auth required:** Igen (Bearer JWT)
- **Status codes:** `200`, `401`

**Response (200):**
```json
{
  "id": "usr_01HXYZ",
  "email": "admin@aiflow.local",
  "display_name": "Admin User",
  "role": "admin",
  "team_id": "team_01ABC",
  "permissions": ["workflows:read", "workflows:write", "admin:full"],
  "budget_remaining_usd": 150.00,
  "created_at": "2026-01-15T10:00:00Z",
  "last_login": "2026-03-28T08:00:00Z"
}
```

### 2.4 POST /api/v1/auth/api-keys

Uj API kulcs generalasa programozott hozzafereshez.

- **Auth required:** Igen (Bearer JWT, role: admin | developer)
- **Status codes:** `201`, `401`, `403`

**Request:**
```json
{
  "name": "ci-cd-pipeline-key",
  "scopes": ["workflows:read", "workflows:execute", "jobs:read"],
  "expires_in_days": 90
}
```

**Response (201):**
```json
{
  "id": "key_01XYZ",
  "name": "ci-cd-pipeline-key",
  "api_key": "aiflow_sk_live_abc123...xyz789",
  "scopes": ["workflows:read", "workflows:execute", "jobs:read"],
  "created_at": "2026-03-28T14:30:00Z",
  "expires_at": "2026-06-26T14:30:00Z"
}
```

> **Fontos:** Az `api_key` ertek csak egyszer jelenik meg, a response-ban. Utana mar nem kerdezheto le.

---

## 3. Workflow Endpoints

### 3.1 GET /api/v1/workflows

Az osszes regisztralt workflow listaja, szurheto.

- **Auth required:** Igen
- **Query params:** `skill` (string), `enabled` (bool), `cursor`, `limit`
- **Status codes:** `200`, `401`

**Response (200):**
```json
{
  "data": [
    {
      "name": "document-summarizer",
      "display_name": "Dokumentum Osszefoglalo",
      "description": "PDF/DOCX dokumentumok AI osszefoglalasa",
      "skill": "summarization",
      "enabled": true,
      "version": "2.1.0",
      "step_count": 4,
      "avg_duration_ms": 12500,
      "last_run_at": "2026-03-28T12:00:00Z",
      "created_at": "2026-02-01T09:00:00Z"
    }
  ],
  "pagination": { "next_cursor": null, "limit": 25, "total_count": 8 }
}
```

### 3.2 GET /api/v1/workflows/{name}

Egy konkret workflow reszletes definicioja, beleertve a DAG strukturat.

- **Auth required:** Igen
- **Path params:** `name` (string)
- **Status codes:** `200`, `401`, `404`

**Response (200):**
```json
{
  "name": "document-summarizer",
  "display_name": "Dokumentum Osszefoglalo",
  "description": "PDF/DOCX dokumentumok AI osszefoglalasa",
  "skill": "summarization",
  "enabled": true,
  "version": "2.1.0",
  "input_schema": {
    "type": "object",
    "properties": {
      "document_url": { "type": "string", "format": "uri" },
      "language": { "type": "string", "default": "hu" },
      "max_length": { "type": "integer", "default": 500 }
    },
    "required": ["document_url"]
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "summary": { "type": "string" },
      "key_points": { "type": "array", "items": { "type": "string" } }
    }
  },
  "dag": {
    "steps": [
      { "id": "parse", "skill": "doc-parser", "depends_on": [] },
      { "id": "chunk", "skill": "text-chunker", "depends_on": ["parse"] },
      { "id": "summarize", "skill": "llm-summarize", "depends_on": ["chunk"] },
      { "id": "format", "skill": "output-formatter", "depends_on": ["summarize"] }
    ],
    "edges": [
      { "from": "parse", "to": "chunk" },
      { "from": "chunk", "to": "summarize" },
      { "from": "summarize", "to": "format" }
    ]
  },
  "retry_policy": { "max_retries": 3, "backoff_seconds": [2, 5, 10] },
  "timeout_seconds": 120,
  "created_at": "2026-02-01T09:00:00Z",
  "updated_at": "2026-03-20T11:00:00Z"
}
```

### 3.3 POST /api/v1/workflows/{name}/run

Workflow futtatas inditasa -- szinkron vagy aszinkron modban.

- **Auth required:** Igen
- **Path params:** `name` (string)
- **Query params:** `mode` (`sync` | `async`, default: `async`)
- **Status codes:** `200` (sync), `202` (async), `400`, `401`, `404`

**Request:**
```json
{
  "input": {
    "document_url": "https://storage.aiflow.local/docs/report-2026-q1.pdf",
    "language": "hu",
    "max_length": 300
  },
  "config_overrides": {
    "model": "gpt-4o",
    "temperature": 0.3
  },
  "callback_url": "https://myapp.example.com/webhook/aiflow",
  "priority": "high",
  "tags": ["quarterly-report", "finance"]
}
```

**Response (202 -- async mod):**
```json
{
  "job_id": "job_01QABC123",
  "workflow_name": "document-summarizer",
  "status": "queued",
  "priority": "high",
  "created_at": "2026-03-28T14:30:00Z",
  "estimated_duration_ms": 15000,
  "poll_url": "/api/v1/jobs/job_01QABC123",
  "ws_url": "/ws/events?job_id=job_01QABC123"
}
```

**Response (200 -- sync mod):**
```json
{
  "job_id": "job_01QABC124",
  "workflow_name": "document-summarizer",
  "status": "completed",
  "result": {
    "summary": "A 2026 Q1 jelentes szerint...",
    "key_points": ["Bevetel 15%-kal nott", "Uj piacokra lepes"]
  },
  "duration_ms": 11230,
  "token_usage": { "prompt_tokens": 4200, "completion_tokens": 580, "total_cost_usd": 0.052 },
  "completed_at": "2026-03-28T14:30:11Z"
}
```

### 3.4 GET /api/v1/workflows/{name}/docs

Auto-generalt dokumentacio egy workflow-hoz (input/output schema, peldak).

- **Auth required:** Igen
- **Status codes:** `200`, `404`

**Response (200):**
```json
{
  "workflow_name": "document-summarizer",
  "description": "PDF/DOCX dokumentumok AI osszefoglalasa",
  "input_schema": { "...": "..." },
  "output_schema": { "...": "..." },
  "examples": [
    {
      "input": { "document_url": "https://example.com/sample.pdf" },
      "output": { "summary": "Minta osszefoglalas...", "key_points": ["Pont 1"] }
    }
  ],
  "changelog": [
    { "version": "2.1.0", "date": "2026-03-20", "changes": "Javitott chunk strategia" }
  ]
}
```

### 3.5 POST /api/v1/workflows/{name}/replay

Egy korabban futott workflow ujrainditasa egy adott leptol kezdve.

- **Auth required:** Igen
- **Status codes:** `202`, `400`, `404`

**Request:**
```json
{
  "source_job_id": "job_01QABC123",
  "from_step": "summarize",
  "config_overrides": {
    "model": "claude-sonnet-4-20250514",
    "temperature": 0.2
  }
}
```

**Response (202):**
```json
{
  "job_id": "job_01QABC200",
  "workflow_name": "document-summarizer",
  "replay_from_step": "summarize",
  "source_job_id": "job_01QABC123",
  "status": "queued",
  "created_at": "2026-03-28T14:35:00Z"
}
```

---

## 4. Job Endpoints

### 4.1 GET /api/v1/jobs

Futtatott job-ok listaja, szurheto.

- **Auth required:** Igen
- **Query params:** `status` (`queued|running|completed|failed|cancelled`), `workflow` (string), `cursor`, `limit`
- **Status codes:** `200`, `401`

**Response (200):**
```json
{
  "data": [
    {
      "id": "job_01QABC123",
      "workflow_name": "document-summarizer",
      "status": "completed",
      "priority": "high",
      "progress_pct": 100,
      "current_step": "format",
      "duration_ms": 11230,
      "created_at": "2026-03-28T14:30:00Z",
      "completed_at": "2026-03-28T14:30:11Z",
      "triggered_by": "usr_01HXYZ",
      "tags": ["quarterly-report"]
    }
  ],
  "pagination": { "next_cursor": null, "limit": 25, "total_count": 156 }
}
```

### 4.2 GET /api/v1/jobs/{id}

Egy job reszletes statusza es lepes-szintu progress.

- **Auth required:** Igen
- **Path params:** `id` (string)
- **Status codes:** `200`, `404`

**Response (200):**
```json
{
  "id": "job_01QABC123",
  "workflow_name": "document-summarizer",
  "status": "running",
  "progress_pct": 65,
  "current_step": "summarize",
  "steps": [
    { "id": "parse", "status": "completed", "duration_ms": 1200, "started_at": "2026-03-28T14:30:00Z" },
    { "id": "chunk", "status": "completed", "duration_ms": 800, "started_at": "2026-03-28T14:30:01Z" },
    { "id": "summarize", "status": "running", "duration_ms": null, "started_at": "2026-03-28T14:30:02Z" },
    { "id": "format", "status": "pending", "duration_ms": null, "started_at": null }
  ],
  "token_usage": { "prompt_tokens": 3100, "completion_tokens": 0, "total_cost_usd": 0.031 },
  "retry_count": 0,
  "created_at": "2026-03-28T14:30:00Z",
  "triggered_by": "usr_01HXYZ"
}
```

### 4.3 GET /api/v1/jobs/{id}/result

Befejezett job vegso kimenete.

- **Auth required:** Igen
- **Status codes:** `200`, `404`, `409` (ha meg fut)

**Response (200):**
```json
{
  "job_id": "job_01QABC123",
  "workflow_name": "document-summarizer",
  "status": "completed",
  "result": {
    "summary": "A 2026 Q1 jelentes szerint a vallalat bevetele 15%-kal novekedett...",
    "key_points": [
      "Bevetel 15%-kal nott az elozo negyedevhez kepest",
      "Harom uj piacon jelent meg a ceg",
      "Az AI alapu megoldasok reszaranya 40%-ra nott"
    ]
  },
  "token_usage": { "prompt_tokens": 4200, "completion_tokens": 580, "total_cost_usd": 0.052 },
  "duration_ms": 11230,
  "completed_at": "2026-03-28T14:30:11Z"
}
```

### 4.4 DELETE /api/v1/jobs/{id}

Futo job megszakitasa (cancel).

- **Auth required:** Igen
- **Status codes:** `204`, `404`, `409` (ha mar befejezodott)

**Response:** Nincs body (`204 No Content`).

### 4.5 GET /api/v1/jobs/dlq

Dead Letter Queue -- sikertelen, ujraprobalhatatlan job-ok.

- **Auth required:** Igen (role: admin | developer)
- **Query params:** `cursor`, `limit`
- **Status codes:** `200`, `401`, `403`

**Response (200):**
```json
{
  "data": [
    {
      "id": "dlq_01XYZ",
      "original_job_id": "job_01FAIL99",
      "workflow_name": "document-summarizer",
      "error_code": "LLM_TIMEOUT",
      "error_message": "Az LLM provider nem valaszolt 30 masodpercen belul.",
      "retry_count": 3,
      "last_attempt_at": "2026-03-27T22:15:00Z",
      "original_input": { "document_url": "https://..." },
      "created_at": "2026-03-27T22:00:00Z"
    }
  ],
  "pagination": { "next_cursor": null, "limit": 25, "total_count": 3 }
}
```

### 4.6 POST /api/v1/jobs/dlq/{id}/replay

DLQ-bol egy job ujraprobalkozasa.

- **Auth required:** Igen (role: admin | developer)
- **Path params:** `id` (string -- dlq entry ID)
- **Status codes:** `202`, `404`

**Request:**
```json
{
  "config_overrides": {
    "model": "gpt-4o-mini",
    "timeout_seconds": 60
  }
}
```

**Response (202):**
```json
{
  "job_id": "job_01RETRY50",
  "source_dlq_id": "dlq_01XYZ",
  "workflow_name": "document-summarizer",
  "status": "queued",
  "created_at": "2026-03-28T15:00:00Z"
}
```

### 4.7 DELETE /api/v1/jobs/dlq/{id}

Megoldott DLQ bejegyzes eltavolitasa.

- **Auth required:** Igen (role: operator+)
- **Path params:** `id` (string -- dlq entry ID)
- **Status codes:** `204`, `404`

**Response:** Nincs body (`204 No Content`).

---

## 5. Skill Endpoints

### 5.1 GET /api/v1/skills

Telepitett skill-ek listaja.

- **Auth required:** Igen
- **Query params:** `cursor`, `limit`
- **Status codes:** `200`, `401`

**Response (200):**
```json
{
  "data": [
    {
      "name": "llm-summarize",
      "version": "1.3.0",
      "description": "Szoveg osszefoglalasa LLM-mel",
      "author": "aiflow-team",
      "category": "nlp",
      "input_schema": { "type": "object", "properties": { "text": { "type": "string" } } },
      "output_schema": { "type": "object", "properties": { "summary": { "type": "string" } } },
      "installed_at": "2026-02-10T08:00:00Z",
      "used_in_workflows": ["document-summarizer", "email-digest"]
    }
  ],
  "pagination": { "next_cursor": null, "limit": 25, "total_count": 12 }
}
```

### 5.2 GET /api/v1/skills/{name}

Skill reszletes adatai es manifest.

- **Auth required:** Igen
- **Status codes:** `200`, `404`

**Response (200):**
```json
{
  "name": "llm-summarize",
  "version": "1.3.0",
  "description": "Szoveg osszefoglalasa LLM-mel",
  "author": "aiflow-team",
  "category": "nlp",
  "manifest": {
    "entry_point": "skills/llm_summarize/main.py",
    "dependencies": ["langchain>=0.2.0", "tiktoken"],
    "config_schema": {
      "model": { "type": "string", "default": "gpt-4o-mini" },
      "max_tokens": { "type": "integer", "default": 1024 }
    },
    "health_check": "/skills/llm-summarize/health"
  },
  "input_schema": { "type": "object", "properties": { "text": { "type": "string" } } },
  "output_schema": { "type": "object", "properties": { "summary": { "type": "string" } } },
  "installed_at": "2026-02-10T08:00:00Z"
}
```

### 5.3 POST /api/v1/skills/install

Uj skill telepitese fajlrendszerbol vagy registry-bol.

- **Auth required:** Igen (role: admin)
- **Status codes:** `201`, `400`, `403`, `409`

**Request:**
```json
{
  "source": "path",
  "path": "/opt/aiflow/custom-skills/sentiment-analyzer",
  "override_existing": false
}
```

**Response (201):**
```json
{
  "name": "sentiment-analyzer",
  "version": "1.0.0",
  "status": "installed",
  "installed_at": "2026-03-28T15:10:00Z",
  "message": "Skill sikeresen telepitve."
}
```

### 5.4 DELETE /api/v1/skills/{name}

Skill eltavolitasa. Nem torolheto, ha aktiv workflow hasznalja.

- **Auth required:** Igen (role: admin)
- **Status codes:** `204`, `403`, `404`, `409`

**Response (204):** Nincs body.

**Response (409 -- ha hasznalat alatt all):**
```json
{
  "error": {
    "error_code": "SKILL_IN_USE",
    "message": "A skill nem tavolthato el, mert aktiv workflow(k) hasznalja(k).",
    "details": { "used_by": ["document-summarizer", "email-digest"] }
  }
}
```

### 5.5 POST /api/v1/skills/{skill}/ingest

Dokumentum/adat betoltese egy skill szamara (pl. RAG knowledge base feltoltes).

- **Auth required:** Igen (role: developer+)
- **Content-Type:** `multipart/form-data`
- **Path params:** `skill` (string -- skill neve)
- **Status codes:** `202`, `400`, `403`, `404`

**Request (form fields):**

| Mezo | Tipus | Leiras |
|---|---|---|
| `file` | binary | A betoltendo fajl |
| `metadata` | JSON string | Egyedi metaadatok (pl. collection, language) |

**Response (202):**
```json
{
  "job_id": "job_01INGEST42",
  "status_url": "/api/v1/jobs/job_01INGEST42"
}
```

---

## 6. Prompt Endpoints

### 6.1 GET /api/v1/prompts

Osszes prompt sablon listaja.

- **Auth required:** Igen
- **Query params:** `label` (`latest|production|staging`), `cursor`, `limit`
- **Status codes:** `200`, `401`

**Response (200):**
```json
{
  "data": [
    {
      "name": "summarize-document",
      "current_version": 5,
      "labels": { "production": 4, "staging": 5, "latest": 5 },
      "language": "hu",
      "updated_at": "2026-03-25T10:00:00Z"
    }
  ],
  "pagination": { "next_cursor": null, "limit": 25, "total_count": 18 }
}
```

### 6.2 GET /api/v1/prompts/{name}

Egy prompt aktualis verzioja (label szerint).

- **Auth required:** Igen
- **Query params:** `label` (default: `production`), `version` (int, optional)
- **Status codes:** `200`, `404`

**Response (200):**
```json
{
  "name": "summarize-document",
  "version": 4,
  "label": "production",
  "template": "Foglald ossze az alabbi dokumentumot {{language}} nyelven, max {{max_length}} szoban:\n\n{{document_text}}",
  "variables": ["language", "max_length", "document_text"],
  "model_config": { "model": "gpt-4o", "temperature": 0.3, "max_tokens": 1024 },
  "metadata": { "author": "usr_01HXYZ", "description": "Altalanos dokumentum osszefoglalo prompt" },
  "created_at": "2026-03-10T09:00:00Z"
}
```

### 6.3 POST /api/v1/prompts/sync

YAML prompt definiciok szinkronizalasa Langfuse-ba.

- **Auth required:** Igen (role: admin | developer)
- **Status codes:** `200`, `400`, `403`

**Request:**
```json
{
  "source_path": "/opt/aiflow/prompts/",
  "dry_run": false
}
```

**Response (200):**
```json
{
  "synced": 12,
  "created": 2,
  "updated": 8,
  "unchanged": 2,
  "errors": [],
  "synced_at": "2026-03-28T15:20:00Z"
}
```

### 6.4 POST /api/v1/prompts/{name}/promote

Prompt verzio eloleptetese egyik label-rol a masikra (pl. staging -> production).

- **Auth required:** Igen (role: admin)
- **Status codes:** `200`, `400`, `403`, `404`

**Request:**
```json
{
  "from_label": "staging",
  "to_label": "production"
}
```

**Response (200):**
```json
{
  "name": "summarize-document",
  "promoted_version": 5,
  "from_label": "staging",
  "to_label": "production",
  "promoted_at": "2026-03-28T15:25:00Z",
  "promoted_by": "usr_01HXYZ"
}
```

### 6.5 POST /api/v1/prompts/{name}/rollback

Prompt visszaallitasa egy korabbi verziora.

- **Auth required:** Igen (role: admin)
- **Status codes:** `200`, `400`, `404`

**Request:**
```json
{
  "target_version": 3,
  "label": "production"
}
```

**Response (200):**
```json
{
  "name": "summarize-document",
  "rolled_back_to_version": 3,
  "label": "production",
  "previous_version": 5,
  "rolled_back_at": "2026-03-28T15:30:00Z"
}
```

### 6.6 POST /api/v1/prompts/{name}/test

Prompt teszteles promptfoo-val.

- **Auth required:** Igen (role: admin | developer)
- **Status codes:** `200`, `400`, `404`

**Request:**
```json
{
  "version": 5,
  "test_dataset": "summarize-golden-set",
  "assertions": ["contains-keywords", "max-length-check", "language-match"]
}
```

**Response (200):**
```json
{
  "name": "summarize-document",
  "version_tested": 5,
  "dataset": "summarize-golden-set",
  "results": {
    "total_cases": 20,
    "passed": 18,
    "failed": 2,
    "pass_rate": 0.90,
    "failures": [
      { "case_id": "tc_07", "assertion": "max-length-check", "expected": 300, "actual": 342 },
      { "case_id": "tc_14", "assertion": "language-match", "expected": "hu", "detected": "en" }
    ]
  },
  "duration_ms": 45000,
  "completed_at": "2026-03-28T15:35:00Z"
}
```

---

## 7. Evaluation Endpoints

### 7.1 POST /api/v1/evaluations/run

Kiertekelo suite futtatasa (pl. accuracy, latency, cost meresek).

- **Auth required:** Igen (role: admin | developer)
- **Status codes:** `202`, `400`, `403`

**Request:**
```json
{
  "workflow_name": "document-summarizer",
  "dataset": "summarize-golden-set",
  "metrics": ["bleu", "rouge-l", "latency_p95", "cost_per_run"],
  "model_variants": ["gpt-4o", "claude-sonnet-4-20250514", "gpt-4o-mini"],
  "concurrency": 5
}
```

**Response (202):**
```json
{
  "evaluation_id": "eval_01ABC",
  "workflow_name": "document-summarizer",
  "status": "running",
  "created_at": "2026-03-28T16:00:00Z",
  "estimated_duration_ms": 120000
}
```

### 7.2 GET /api/v1/evaluations/{id}/results

Kiertekeles eredmenyeinek lekerdezese.

- **Auth required:** Igen
- **Status codes:** `200`, `404`, `409` (ha meg fut)

**Response (200):**
```json
{
  "evaluation_id": "eval_01ABC",
  "workflow_name": "document-summarizer",
  "status": "completed",
  "results_by_model": {
    "gpt-4o": {
      "bleu": 0.72, "rouge_l": 0.81, "latency_p95_ms": 8500, "avg_cost_usd": 0.048
    },
    "claude-sonnet-4-20250514": {
      "bleu": 0.75, "rouge_l": 0.84, "latency_p95_ms": 7200, "avg_cost_usd": 0.039
    },
    "gpt-4o-mini": {
      "bleu": 0.65, "rouge_l": 0.73, "latency_p95_ms": 3100, "avg_cost_usd": 0.008
    }
  },
  "best_model": "claude-sonnet-4-20250514",
  "total_test_cases": 50,
  "duration_ms": 98000,
  "completed_at": "2026-03-28T16:01:38Z"
}
```

### 7.3 GET /api/v1/evaluations/datasets

Elerheto teszt adathalmazok listaja.

- **Auth required:** Igen
- **Status codes:** `200`

**Response (200):**
```json
{
  "data": [
    {
      "name": "summarize-golden-set",
      "description": "50 darab kezi validalt dokumentum-osszefoglalas par",
      "record_count": 50,
      "format": "jsonl",
      "workflow_name": "document-summarizer",
      "created_at": "2026-02-15T10:00:00Z",
      "updated_at": "2026-03-20T14:00:00Z"
    }
  ]
}
```

---

## 8. Schedule Endpoints (Utemezesek)

### 8.1 GET /api/v1/schedules

Osszes utemezett trigger listaja.

- **Auth required:** Igen
- **Status codes:** `200`, `401`

**Response (200):**
```json
{
  "data": [
    {
      "id": "sched_01ABC",
      "workflow_name": "daily-report",
      "trigger_type": "cron",
      "cron_expression": "0 8 * * 1-5",
      "enabled": true,
      "timezone": "Europe/Budapest",
      "next_run_at": "2026-03-31T08:00:00+02:00",
      "last_run_at": "2026-03-28T08:00:00+02:00",
      "created_at": "2026-01-20T10:00:00Z"
    },
    {
      "id": "sched_02DEF",
      "workflow_name": "slack-alert-handler",
      "trigger_type": "webhook",
      "webhook_path": "/hooks/slack-alert-handler/abc123secret",
      "enabled": true,
      "last_triggered_at": "2026-03-28T11:45:00Z",
      "created_at": "2026-02-05T14:00:00Z"
    },
    {
      "id": "sched_03GHI",
      "workflow_name": "new-ticket-classifier",
      "trigger_type": "event",
      "event_source": "jira",
      "event_type": "ticket.created",
      "filter_expression": "priority in ('high', 'critical')",
      "enabled": true,
      "created_at": "2026-03-01T09:00:00Z"
    }
  ]
}
```

### 8.2 POST /api/v1/schedules

Uj utemezett trigger letrehozasa.

- **Auth required:** Igen (role: admin | developer)
- **Status codes:** `201`, `400`, `403`

**Request (cron):**
```json
{
  "workflow_name": "daily-report",
  "trigger_type": "cron",
  "cron_expression": "0 8 * * 1-5",
  "timezone": "Europe/Budapest",
  "enabled": true,
  "input": { "report_type": "daily", "recipients": ["team@aiflow.local"] }
}
```

**Request (webhook):**
```json
{
  "workflow_name": "external-trigger-handler",
  "trigger_type": "webhook",
  "enabled": true,
  "webhook_secret": "whsec_mySecret123"
}
```

**Request (event):**
```json
{
  "workflow_name": "new-ticket-classifier",
  "trigger_type": "event",
  "event_source": "jira",
  "event_type": "ticket.created",
  "filter_expression": "priority in ('high', 'critical')",
  "enabled": true
}
```

**Response (201):**
```json
{
  "id": "sched_04JKL",
  "workflow_name": "daily-report",
  "trigger_type": "cron",
  "cron_expression": "0 8 * * 1-5",
  "enabled": true,
  "next_run_at": "2026-03-31T08:00:00+02:00",
  "created_at": "2026-03-28T16:00:00Z"
}
```

### 8.3 PUT /api/v1/schedules/{id}

Meglevo trigger modositasa.

- **Auth required:** Igen (role: admin | developer)
- **Status codes:** `200`, `400`, `404`

**Request:**
```json
{
  "cron_expression": "0 9 * * 1-5",
  "enabled": true
}
```

### 8.4 DELETE /api/v1/schedules/{id}

Trigger torlese.

- **Auth required:** Igen (role: admin)
- **Status codes:** `204`, `404`

---

## 9. Admin Endpoints

### 9.1 Users CRUD

| Method | Path | Leiras |
|---|---|---|
| `GET` | `/api/v1/admin/users` | Felhasznalok listaja |
| `POST` | `/api/v1/admin/users` | Uj felhasznalo letrehozasa |
| `GET` | `/api/v1/admin/users/{id}` | Felhasznalo reszletei |
| `PUT` | `/api/v1/admin/users/{id}` | Felhasznalo modositasa |
| `DELETE` | `/api/v1/admin/users/{id}` | Felhasznalo torlese (soft delete) |

**POST /api/v1/admin/users -- Request:**
```json
{
  "email": "newuser@aiflow.local",
  "display_name": "New User",
  "role": "viewer",
  "team_id": "team_01ABC",
  "monthly_budget_usd": 50.00
}
```

**Response (201):**
```json
{
  "id": "usr_02NEW",
  "email": "newuser@aiflow.local",
  "display_name": "New User",
  "role": "viewer",
  "team_id": "team_01ABC",
  "monthly_budget_usd": 50.00,
  "created_at": "2026-03-28T16:10:00Z"
}
```

- **Auth required:** Igen (role: admin)
- **Status codes:** `200`, `201`, `400`, `403`, `404`, `409`

### 9.2 Teams CRUD

| Method | Path | Leiras |
|---|---|---|
| `GET` | `/api/v1/admin/teams` | Csapatok listaja |
| `POST` | `/api/v1/admin/teams` | Uj csapat |
| `GET` | `/api/v1/admin/teams/{id}` | Csapat reszletei |
| `PUT` | `/api/v1/admin/teams/{id}` | Csapat modositasa |
| `DELETE` | `/api/v1/admin/teams/{id}` | Csapat torlese |

**POST /api/v1/admin/teams -- Request:**
```json
{
  "name": "data-science-team",
  "display_name": "Data Science Team",
  "monthly_budget_usd": 500.00,
  "allowed_models": ["gpt-4o", "claude-sonnet-4-20250514", "gpt-4o-mini"]
}
```

### 9.3 Budget Management

**GET /api/v1/admin/budgets -- Response (200):**
```json
{
  "data": [
    {
      "entity_type": "team",
      "entity_id": "team_01ABC",
      "entity_name": "Data Science Team",
      "monthly_budget_usd": 500.00,
      "used_this_month_usd": 312.45,
      "remaining_usd": 187.55,
      "usage_pct": 62.5,
      "alert_threshold_pct": 80,
      "period": "2026-03"
    }
  ]
}
```

**PUT /api/v1/admin/budgets/{entity_type}/{entity_id} -- Request:**
```json
{
  "monthly_budget_usd": 750.00,
  "alert_threshold_pct": 85
}
```

### 9.4 Metrics Endpoints

| Method | Path | Leiras |
|---|---|---|
| `GET` | `/api/v1/admin/metrics/overview` | Altalanos rendszer attekintes |
| `GET` | `/api/v1/admin/metrics/workflows` | Workflow-szintu metrikak |
| `GET` | `/api/v1/admin/metrics/teams` | Csapat-szintu koltsegek es hasznalat |
| `GET` | `/api/v1/admin/metrics/models` | Model-szintu token hasznalat es koltseg |
| `GET` | `/api/v1/admin/metrics/sla` | SLA teljesites metrikak |

Minden metrics endpoint tamogatja: `?from=2026-03-01T00:00:00Z&to=2026-03-28T23:59:59Z&granularity=day`

- **Auth required:** Igen (role: admin)

**GET /api/v1/admin/metrics/overview -- Response (200):**
```json
{
  "period": { "from": "2026-03-01T00:00:00Z", "to": "2026-03-28T23:59:59Z" },
  "total_jobs": 4521,
  "success_rate": 0.97,
  "avg_latency_ms": 8200,
  "p95_latency_ms": 22000,
  "total_cost_usd": 1245.67,
  "active_workflows": 8,
  "active_users": 23,
  "dlq_size": 3,
  "uptime_pct": 99.95
}
```

**GET /api/v1/admin/metrics/models -- Response (200):**
```json
{
  "data": [
    {
      "model": "gpt-4o",
      "total_requests": 2100,
      "total_prompt_tokens": 8400000,
      "total_completion_tokens": 2100000,
      "total_cost_usd": 630.00,
      "avg_latency_ms": 9500,
      "error_rate": 0.02
    },
    {
      "model": "claude-sonnet-4-20250514",
      "total_requests": 1800,
      "total_prompt_tokens": 7200000,
      "total_completion_tokens": 1800000,
      "total_cost_usd": 468.00,
      "avg_latency_ms": 7800,
      "error_rate": 0.01
    }
  ]
}
```

### 9.5 GET /api/v1/admin/audit

Szurheto audit log lekerdezese.

- **Auth required:** Igen (role: admin)
- **Query params:** `user_id`, `action`, `resource_type`, `from`, `to`, `cursor`, `limit`
- **Status codes:** `200`, `403`

**Response (200):**
```json
{
  "data": [
    {
      "id": "audit_01ABC",
      "timestamp": "2026-03-28T14:30:00Z",
      "user_id": "usr_01HXYZ",
      "user_email": "admin@aiflow.local",
      "action": "workflow.run",
      "resource_type": "workflow",
      "resource_id": "document-summarizer",
      "ip_address": "192.168.1.100",
      "user_agent": "AIFlow-CLI/1.2.0",
      "details": { "mode": "async", "priority": "high" }
    }
  ],
  "pagination": { "next_cursor": "eyJpZCI6MTAwfQ", "limit": 50, "total_count": 1205 }
}
```

### 9.6 POST /api/v1/admin/redact/{run_id}

GDPR PII eltavolitasa egy adott futtas eredmenyeibol.

- **Auth required:** Igen (role: admin)
- **Status codes:** `200`, `403`, `404`

**Request:**
```json
{
  "fields_to_redact": ["input.customer_name", "input.email", "result.personal_data"],
  "reason": "GDPR torlesi keres - ugyfel #12345"
}
```

**Response (200):**
```json
{
  "run_id": "job_01QABC123",
  "redacted_fields": 3,
  "redacted_at": "2026-03-28T16:30:00Z",
  "redacted_by": "usr_01HXYZ",
  "audit_log_id": "audit_02DEF"
}
```

### 9.7 DELETE /api/v1/users/{id}/data

GDPR Art.17 -- Felhasznalo adatainak torlese (right to erasure). Minden szemelyes adatot redaktal vagy torol a rendszerbol.

- **Auth required:** Igen (role: admin)
- **Path params:** `id` (string -- user ID)
- **Status codes:** `200`, `403`, `404`

**Response (200):**
```json
{
  "redacted_records": 47
}
```

### 9.8 GET /api/v1/users/{id}/export

GDPR Art.20 -- Felhasznalo osszes adatanak exportalasa (data portability). Teljes felhasznaloi adat export JSON formatumban.

- **Auth required:** Igen (role: admin)
- **Path params:** `id` (string -- user ID)
- **Response Content-Type:** `application/json`
- **Status codes:** `200`, `403`, `404`

**Response (200):**
```json
{
  "user": {
    "id": "usr_01HXYZ",
    "email": "user@aiflow.local",
    "display_name": "Example User",
    "role": "operator",
    "team_id": "team_01ABC",
    "created_at": "2026-01-15T10:00:00Z"
  },
  "workflow_runs": [ "..." ],
  "conversations": [ "..." ],
  "feedback": [ "..." ],
  "audit_entries": [ "..." ],
  "exported_at": "2026-03-28T17:00:00Z"
}
```

---

## 10. Document/RAG Endpoints

### 10.1 POST /api/v1/documents/upload

Dokumentum feltoltese es feldolgozasa (chunking + embedding).

- **Auth required:** Igen
- **Content-Type:** `multipart/form-data`
- **Status codes:** `202`, `400`, `413` (tul nagy fajl)

**Request (form fields):**

| Mezo | Tipus | Leiras |
|---|---|---|
| `file` | binary | A feltoltendo fajl (PDF, DOCX, TXT, MD) |
| `collection` | string | Cel kollekcio neve |
| `metadata` | JSON string | Egyedi metaadatok |
| `chunk_strategy` | string | `fixed` / `semantic` / `paragraph` (default: `semantic`) |
| `chunk_size` | integer | Max chunk meret tokenben (default: 512) |

**Response (202):**
```json
{
  "document_id": "doc_01ABC",
  "filename": "product-manual-v3.pdf",
  "collection": "product-docs",
  "status": "processing",
  "pages": 42,
  "estimated_chunks": 85,
  "processing_job_id": "job_01DOC50",
  "created_at": "2026-03-28T17:00:00Z"
}
```

### 10.2 GET /api/v1/documents

Dokumentumok listazasa kollekcio szerint.

- **Auth required:** Igen
- **Query params:** `collection` (required), `status`, `cursor`, `limit`
- **Status codes:** `200`, `401`

**Response (200):**
```json
{
  "data": [
    {
      "id": "doc_01ABC",
      "filename": "product-manual-v3.pdf",
      "collection": "product-docs",
      "status": "indexed",
      "chunk_count": 83,
      "file_size_bytes": 2456789,
      "mime_type": "application/pdf",
      "metadata": { "version": "3.0", "language": "hu" },
      "created_at": "2026-03-28T17:00:00Z",
      "indexed_at": "2026-03-28T17:02:30Z"
    }
  ],
  "pagination": { "next_cursor": null, "limit": 25, "total_count": 15 }
}
```

### 10.3 POST /api/v1/documents/search

Hibrid kereses (semantic + keyword) a dokumentum kollekciokon.

- **Auth required:** Igen
- **Status codes:** `200`, `400`

**Request:**
```json
{
  "query": "Hogyan kell a termeket karbantartani?",
  "collections": ["product-docs"],
  "top_k": 5,
  "search_type": "hybrid",
  "semantic_weight": 0.7,
  "keyword_weight": 0.3,
  "filters": {
    "metadata.language": "hu"
  },
  "rerank": true
}
```

**Response (200):**
```json
{
  "results": [
    {
      "chunk_id": "chunk_01XYZ",
      "document_id": "doc_01ABC",
      "document_name": "product-manual-v3.pdf",
      "content": "A termek karbantartasahoz havonta egyszer ellenorizze a szuroket...",
      "score": 0.92,
      "semantic_score": 0.95,
      "keyword_score": 0.85,
      "metadata": { "page": 15, "section": "Karbantartas" }
    }
  ],
  "total_results": 5,
  "search_duration_ms": 120
}
```

### 10.4 GET /api/v1/collections

Elerheto dokumentum kollekcio-k listaja.

- **Auth required:** Igen
- **Status codes:** `200`

**Response (200):**
```json
{
  "data": [
    {
      "name": "product-docs",
      "display_name": "Termek dokumentaciok",
      "document_count": 15,
      "total_chunks": 1250,
      "embedding_model": "text-embedding-3-small",
      "vector_dimensions": 1536,
      "created_at": "2026-01-10T09:00:00Z",
      "last_updated_at": "2026-03-28T17:02:30Z"
    }
  ]
}
```

### 10.5 GET /api/v1/conversations

Beszelgetesek listazasa skill es felhasznalo szerint.

- **Auth required:** Igen (role: operator+)
- **Query params:** `skill` (string), `limit` (int, default: 20), `cursor` (string)
- **Status codes:** `200`, `401`, `403`

**Response (200):**
```json
{
  "items": [
    {
      "id": "conv_01ABC",
      "title": "Termek karbantartas",
      "skill_name": "aszf_rag_chat",
      "message_count": 12,
      "last_message_at": "2026-03-28T17:15:00Z"
    }
  ],
  "cursor": "eyJpZCI6ImNvbnZfMDFBQkMifQ"
}
```

### 10.6 POST /api/v1/conversations/{id}/messages

Uj uzenet kuldese egy beszelgetesbe, streaming valasszal.

- **Auth required:** Igen (role: operator+)
- **Path params:** `id` (string)
- **Status codes:** `200` (streaming SSE), `401`, `403`, `404`

**Request:**
```json
{
  "content": "Mi a visszakuldesi hatarid?"
}
```

**Response:** Streaming (SSE) -- lasd [WS /ws/chat/{conversation_id}](#112-ws-wschatconversation_id) a reszletes streaming formatumert.

### 10.7 POST /api/v1/feedback

Felhasznaloi visszajelzes rogzitese egy beszelgetes uzenethez.

- **Auth required:** Igen (role: operator+)
- **Status codes:** `201`, `400`, `401`, `403`

**Request:**
```json
{
  "conversation_id": "conv_01ABC",
  "message_id": "msg_05XYZ",
  "feedback": "thumbs_up",
  "comment": "Pontos es hasznos valasz volt."
}
```

**Response (201):**
```json
{
  "id": "fb_01DEF"
}
```

> **Megjegyzes:** A `feedback` mezo ertekei: `"thumbs_up"` vagy `"thumbs_down"`. A `comment` mezo opcionalis.

---

## 11. WebSocket Endpoints

### 11.1 WS /ws/events

Valos ideju esemeny stream: job statusz valtozasok, rendszer alertek.

- **Auth:** JWT token query param-kent: `/ws/events?token=eyJ...`
- **Query params:** `job_id` (optional -- szures egyetlen job-ra)

**Server -> Client uzenet tipusok:**

```json
{
  "type": "job.status_changed",
  "timestamp": "2026-03-28T14:30:05Z",
  "payload": {
    "job_id": "job_01QABC123",
    "workflow_name": "document-summarizer",
    "old_status": "running",
    "new_status": "completed",
    "current_step": "format",
    "progress_pct": 100
  }
}
```

```json
{
  "type": "job.step_completed",
  "timestamp": "2026-03-28T14:30:03Z",
  "payload": {
    "job_id": "job_01QABC123",
    "step_id": "chunk",
    "duration_ms": 800,
    "next_step": "summarize"
  }
}
```

```json
{
  "type": "system.alert",
  "timestamp": "2026-03-28T14:30:10Z",
  "payload": {
    "severity": "warning",
    "alert_type": "budget_threshold",
    "message": "A Data Science Team elerte a havi koltsegvetes 80%-at.",
    "details": { "team_id": "team_01ABC", "usage_pct": 82.3 }
  }
}
```

**Client -> Server (ping/subscribe):**
```json
{
  "type": "subscribe",
  "channels": ["job.status_changed", "system.alert"]
}
```

### 11.2 WS /ws/chat/{conversation_id}

Streaming RAG chat -- valos ideju, chunk-onkenti valasz streameles.

- **Auth:** JWT token query param-kent
- **Path params:** `conversation_id` (string -- uj beszelgetes: `new`)

**Client -> Server:**
```json
{
  "type": "message",
  "content": "Mi a termek karbantartasi utmutatoja?",
  "collections": ["product-docs"],
  "model": "gpt-4o",
  "config": { "temperature": 0.3, "max_tokens": 1024 }
}
```

**Server -> Client (streaming chunks):**
```json
{ "type": "chat.sources", "payload": { "sources": [{ "document": "product-manual-v3.pdf", "page": 15, "score": 0.92 }] } }
{ "type": "chat.chunk", "payload": { "content": "A termek karban" } }
{ "type": "chat.chunk", "payload": { "content": "tartasahoz havonta " } }
{ "type": "chat.chunk", "payload": { "content": "egyszer ellenorizze..." } }
{ "type": "chat.done", "payload": { "conversation_id": "conv_01ABC", "token_usage": { "prompt_tokens": 2100, "completion_tokens": 350 } } }
```

### 11.3 WebSocket Reliability

A WebSocket kapcsolat megbizhatosaganak biztositasa:

**Server heartbeat:**
- A szerver 30 masodpercenkent ping frame-et kuld
- Ha a kliens 90 masodpercen belul nem valaszol pong-gal, a szerver bontja a kapcsolatot

**Client reconnection:**
- Exponential backoff strategia: 1s, 2s, 4s, 8s, max 30s
- Ujracsatlakozaskor a kliens `since_timestamp` parametert adhat at az elmulasztott esemenyek potlasara

```
WS /ws/events?token=eyJ...&since_timestamp=2026-03-28T14:30:00Z
```

**Event catch-up:**
- A szerver max 5 perc esemenytortenetet tart memoriaban
- Ujracsatlakozaskor a `since_timestamp` parameter alapjan visszakuldi az elmulasztott esemenyeket
- Ha a kliens tobb mint 5 perce szakadt le, `event_gap: true` flag-gel jelzi a hianyos idoszakot

**Fallback to REST polling:**
- Ha a WebSocket kapcsolat nem erheto el (pl. proxy/firewall korlatozas), a kliens REST polling-ra valt
- Polling intervallum: 2 masodperc aktiv job eseten, 10 masodperc egyebkent
- Endpoint: `GET /api/v1/jobs/{id}` a job statusz lekerdezeshez

---

## 12. Error Response Format (Reszletes hibakezelesi struktura)

Minden API hiba az alabbi egysegesi envelope-ban jon vissza:

```json
{
  "error": {
    "error_code": "string           -- gepi feldolgozhato hibakod",
    "message": "string              -- ember altal olvashato uzenet",
    "details": "object | null       -- kiegeszito informacio",
    "request_id": "string           -- egyedi request azonosito (naplozashoz)",
    "timestamp": "string            -- ISO 8601 idopont"
  }
}
```

### Definialt Error Code-ok

| error_code | HTTP | Leiras |
|---|---|---|
| `AUTH_INVALID_CREDENTIALS` | 401 | Hibas email vagy jelszo |
| `AUTH_TOKEN_EXPIRED` | 401 | Lejart JWT token |
| `AUTH_INSUFFICIENT_SCOPE` | 403 | API key scope nem elegendo |
| `RBAC_ACCESS_DENIED` | 403 | A felhasznalo role-ja nem engedelyezi |
| `RESOURCE_NOT_FOUND` | 404 | Keresett eroforras nem talalhato |
| `WORKFLOW_NOT_FOUND` | 404 | Workflow nev nem letezik |
| `WORKFLOW_DISABLED` | 400 | A workflow le van tiltva |
| `JOB_ALREADY_COMPLETED` | 409 | Befejezett job nem torolheto/modosithato |
| `SKILL_IN_USE` | 409 | Skill nem tavolthato el (aktiv workflow hasznalja) |
| `BUDGET_EXCEEDED` | 403 | Havi koltsegvetes kimerult |
| `RATE_LIMIT_EXCEEDED` | 429 | Tul sok keres |
| `VALIDATION_ERROR` | 422 | Input validacios hiba |
| `LLM_PROVIDER_ERROR` | 502 | Az LLM provider hibat adott |
| `LLM_TIMEOUT` | 504 | Az LLM provider nem valaszolt idoben |
| `INTERNAL_ERROR` | 500 | Belso szerver hiba |

---

## 13. Rate Limiting Headers

Minden API response tartalmazza az alabbi rate limit headerokat:

```
X-RateLimit-Limit: 1000          -- Max keresek szama az adott idoablakban
X-RateLimit-Remaining: 847       -- Hatralevo keresek szama
X-RateLimit-Reset: 1711641600    -- Unix timestamp, mikor resetelodik
X-RateLimit-Window: 3600         -- Idoablak masodpercben
X-RateLimit-Policy: per-user     -- Limiteles tipusa (per-user | per-team | per-api-key)
```

### Rate Limit szabalyok role szerint

| Role | Limit / ora | Burst limit (per sec) |
|---|---|---|
| `admin` | 10 000 | 50 |
| `developer` | 5 000 | 30 |
| `operator` | 2 000 | 20 |
| `viewer` | 1 000 | 10 |
| API Key | Egyedi konfig | Egyedi konfig |

**429 response pelda:**
```json
{
  "error": {
    "error_code": "RATE_LIMIT_EXCEEDED",
    "message": "Tullepte az oranke nti keresszam limitet.",
    "details": {
      "limit": 1000,
      "window_seconds": 3600,
      "retry_after_seconds": 234
    }
  }
}
```

A `Retry-After` header is beallitasra kerul (masodpercben).

---

## 14. RBAC Matrix (Szerepkor-alapu jogosultsagi matrix)

A rendszer 4 role-t definial: **admin**, **developer**, **operator**, **viewer**.

| Endpoint csoport | admin | developer | operator | viewer |
|---|---|---|---|---|
| **Auth** login/refresh/me | Y | Y | Y | Y |
| **Auth** api-keys create | Y | Y | - | - |
| **Workflows** list/get/docs | Y | Y | Y | Y |
| **Workflows** run | Y | Y | Y | - |
| **Workflows** replay | Y | Y | - | - |
| **Jobs** list/get/result | Y | Y | Y | Y |
| **Jobs** cancel | Y | Y | Y | - |
| **Jobs** dlq list | Y | Y | - | - |
| **Jobs** dlq replay | Y | Y | - | - |
| **Jobs** dlq delete | Y | Y | Y | - |
| **Skills** list/get | Y | Y | Y | Y |
| **Skills** install/uninstall | Y | - | - | - |
| **Skills** ingest | Y | Y | - | - |
| **Prompts** list/get | Y | Y | Y | Y |
| **Prompts** sync | Y | Y | - | - |
| **Prompts** promote/rollback | Y | - | - | - |
| **Prompts** test | Y | Y | - | - |
| **Evaluations** run | Y | Y | - | - |
| **Evaluations** results/datasets | Y | Y | Y | Y |
| **Schedules** list | Y | Y | Y | Y |
| **Schedules** create/update | Y | Y | - | - |
| **Schedules** delete | Y | - | - | - |
| **Admin** users CRUD | Y | - | - | - |
| **Admin** teams CRUD | Y | - | - | - |
| **Admin** budgets | Y | - | - | - |
| **Admin** metrics | Y | - | - | - |
| **Admin** audit | Y | - | - | - |
| **Admin** redact (GDPR) | Y | - | - | - |
| **Admin** user data erasure (GDPR Art.17) | Y | - | - | - |
| **Admin** user data export (GDPR Art.20) | Y | - | - | - |
| **Conversations** list | Y | Y | Y | - |
| **Conversations** send message | Y | Y | Y | - |
| **Feedback** submit | Y | Y | Y | - |
| **Documents** upload | Y | Y | Y | - |
| **Documents** list/search | Y | Y | Y | Y |
| **Collections** list | Y | Y | Y | Y |
| **WebSocket** events | Y | Y | Y | Y |
| **WebSocket** chat | Y | Y | Y | - |

**Jelmagyarazat:** Y = engedelyezett, - = tiltott (403 Forbidden)

> **Megjegyzes:** API key-eknel a scope-ok finomabb szabalyozast tesznek lehetove az RBAC role-on belul.
> Pl. egy `developer` role-u API key-nek nem kell minden developer jogosultsaggal rendelkeznie.

---

## 15. Idempotency (Idempotencia)

Nem-idempotenst POST endpoint-oknal az `X-Idempotency-Key` header biztositja, hogy ugyanaz a keres tobbszori kuldese eseten is csak egyszer hajtodik vegre.

### Mukodes

1. A kliens egyedi `X-Idempotency-Key` header-t kuld minden POST kereshez
2. A szerver Redis-ben tarolja a kulcsot es az eredmenyt 24 oras TTL-lel
3. Ha ugyanazzal a kulccsal erkezik ujabb keres a 24 oras ablakon belul, a szerver az eredeti valaszt adja vissza anelkul, hogy ujra vegrehajtana a muveletet

### Pelda

```
POST /api/v1/workflows/document-summarizer/run
X-Idempotency-Key: "idem_a1b2c3d4e5f6"
Content-Type: application/json

{"input": {"document_url": "https://..."}}
```

### Idempotenst vs nem-idempotenst muveletek

| Muvelet | Idempotenst alapbol? | X-Idempotency-Key szukseges? |
|---|---|---|
| `GET` (barmely) | Igen | Nem |
| `DELETE` (barmely) | Igen | Nem |
| `PUT` (barmely) | Igen | Nem |
| `POST /workflows/{name}/run` | Nem | Igen (ajanlott) |
| `POST /workflows/{name}/replay` | Nem | Igen (ajanlott) |
| `POST /jobs/dlq/{id}/replay` | Nem | Igen (ajanlott) |
| `POST /conversations/{id}/messages` | Nem | Igen (ajanlott) |
| `POST /feedback` | Nem | Igen (ajanlott) |

### Implementacios reszletek

- **Tarolas:** Redis, `SETEX idempotency:{key} 86400 {response_json}`
- **Dedup ablak:** 24 ora (konfiguralhato)
- **Kulcs formatum:** Barmilyen UTF-8 string, max 256 karakter
- **Duplikat keres eseten:** `200` az eredeti valasszal + `X-Idempotent-Replayed: true` header

---

## 16. API Versioning Policy (API Verziozasi Iranyelvek)

### Mikor szukseges uj fo verzio (v2)?

- Breaking response schema valtozas (mezo atnevezes, tipusvaltas, eltavolitas)
- Breaking request schema valtozas (kotelezo uj mezo, mezo eltavolitas)
- Szemantikai valtozas (meglevo mezo jelentesenek modosulasa)
- Autentikacio/authorizacio modell valtozas

**Nem igenyel uj fo verziot:**
- Uj opcionalis mezo hozzaadasa response-ban
- Uj opcionalis query parameter
- Uj endpoint hozzaadasa
- Bug fix, ami az eredeti specifikacio szerinti viselkedest allitja helyre

### Parhuzamos verzio tamogatas

- **v1 fenntartas:** v2 GA (General Availability) utani 12 honapig tamogatott
- **Sunset idoszak:** Az utolso 3 honapban a v1 response-ok `Sunset` es `Deprecation` header-eket tartalmaznak

```
Sunset: Sat, 28 Mar 2028 00:00:00 GMT
Deprecation: true
Link: </api/v2/workflows>; rel="successor-version"
```

### Deprecation folyamat

1. **Bejelentes:** Minimum 6 honappal a sunset datum elott
2. **Deprecation header:** Bekapcsolas a v1 valaszokban
3. **Migracios utmutato:** Kozzetetel a developer portal-on
4. **Monitoring:** v1 hasznalat figyelese, aktiv kliensek ertesitese
5. **Sunset:** v1 endpoint-ok `410 Gone` valasszal ternek vissza

### API Changelog

Minden API valtozas dokumentalva a kovetkezo helyen:
- **Endpoint:** `GET /api/v1/changelog`
- **Formatum:** JSON, verzioszam + datum + valtozasok listaja
- **Ertesites:** Webhook vagy email a regisztralt fejlesztoknek uj verzio eseten

---

*Dokumentum vege -- AIFlow REST API v1.0.0*
