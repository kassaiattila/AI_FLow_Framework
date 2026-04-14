---
name: aiflow-observability
description: AIFlow megfigyelhetoseg — metrikak, logok, trace-ek, SLO, alerting. Hasznald amikor observability kodot irsz, Langfuse-t konfiguralsz, vagy monitoring dashboard-ot epitesz.
allowed-tools: Read, Write, Edit, Grep, Glob, Bash
---

# AIFlow Observability Skill

## Stack
- **Metrikak:** Prometheus (ha konfiguralt) + belso cost_tracker
- **Logok:** structlog JSON → konzol (dev) / OpenSearch (prod)
- **Trace-ek:** Langfuse (self-hosted vagy cloud) + OpenTelemetry
- **Alerting:** Langfuse dashboard + belso notification service

## Logging Szabalyok

### KOTELEZO
- **MINDIG** `structlog` — SOHA `print()`, SOHA `logging.info()`
- **Format:** `logger.info("event_name", key=value, key2=value2)`
- **Minden service-nek:** `logger = structlog.get_logger(__name__)`
- **Trace context:** `trace_id`, `span_id` automatikus (Langfuse)

### PII TILTOTT a logokban
- Nev, email, telefon, lakcim
- Jelszó, token, API kulcs
- Biometrikus adat
- Bankszamlaszam, kartyaszam
- **Kivétel:** user_id UUID-kent megengedett

### Log szintek
- `debug` — fejlesztoi info (nem prod)
- `info` — normal mukodes (service_started, request_processed)
- `warning` — figyelmeztetes (rate_limit_approaching, retry_attempt)
- `error` — hiba (request_failed, connection_lost)
- `critical` — sulyos hiba (data_corruption, security_breach)

## Langfuse Integracio

### Trace-ek
- Minden pipeline futtas = 1 trace
- Minden step = 1 span (generation vagy span)
- Prompt verzio tracking: dev → prod label swap
- Cost tracking: per-span es per-trace koltseg

### Prompt Management
- YAML-bol toltott prompt-ok Langfuse-ba szinkronizalva
- `dev` label: fejlesztes alatt
- `prod` label: produktiv hasznalat
- Cache invalidation: `POST /api/v1/prompts/cache/invalidate`

## Metrikak (Prometheus-kompatibilis)

### RED Method (minden service-re)
- `aiflow_{service}_requests_total{method, status}`
- `aiflow_{service}_request_duration_seconds{method}`
- `aiflow_{service}_errors_total{method, error_type}`

### v2 Specifikus
- `aiflow_capacity_docs_per_day{tenant_id, profile}`
- `aiflow_cost_usd_total{tenant_id, provider}`
- `aiflow_hitl_tasks_pending{priority, tenant_id}`
- `aiflow_hitl_sla_breach_total{priority}`
- `aiflow_routing_decision_total{provider, signal_type}`

## Cost Tracking

### Koltseg API
- `GET /api/v1/costs/` — osszesitett koltseg
- `GET /api/v1/costs/breakdown` — provider/service/skill bontasban
- `GET /api/v1/costs/daily` — napi trend

### v2 Cost Cap Policy
- Per-decision: $0.50
- Per-package: $5.00
- Per-tenant daily: $100.00
- Feature flag: `AIFLOW_FEATURE_COST_CAP_ENABLED`

## TILTOTT
- `print()` barhol — hasznalj structlog-ot
- PII a log event-ekben
- Hardcoded Langfuse credentials
- Cost tracking nelkuli LLM hivas
