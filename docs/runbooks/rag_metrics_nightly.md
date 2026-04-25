# Runbook — Nightly RAG retrieval-quality metrics

> Sprint S / S145 (SS-FU-3). Closes the loop between Sprint J UC2 retrieval
> baselines (`MRR@5 ≥ 0.55`) and Sprint S multi-tenant collections — gives
> on-call a recurring measurement + Grafana visibility, so a future change
> that regresses retrieval quality is caught the next morning rather than
> at the next quarterly review.

## 1. Components

| Path | Purpose |
|---|---|
| `src/aiflow/services/rag_metrics/` | Pure-Python harness (no pg / openai imports until call time) |
| `scripts/run_nightly_rag_metrics.py` | CLI runner — `--collection-id X --query-set Y --output {jsonl,table}` |
| `data/fixtures/rag_metrics/uc2_aszf_query_set.json` | 20-item HU query corpus over `aszf_rag_chat` |
| `docs/grafana/rag_collection_metrics_panel.json` | Importable Grafana dashboard |
| `tests/integration/services/rag_metrics/test_harness_real.py` | Boundary-shape gate; gated by `AIFLOW_RUN_NIGHTLY_RAG_METRICS=1` |

## 2. One-shot run

```bash
PYTHONPATH="src" .venv/Scripts/python.exe scripts/run_nightly_rag_metrics.py \
  --collection-id <UUID-of-aszf_rag_chat> \
  --query-set data/fixtures/rag_metrics/uc2_aszf_query_set.json \
  --output jsonl \
  | tee -a out/rag_collection_metrics.jsonl
```

The script writes one JSON line per invocation to stdout. It does NOT
write to the database — keeping persistence external preserves an
air-gap-safe path.

## 3. Persistence (operator-provisioned)

The Grafana panel queries a table called `rag_collection_metrics_jsonl`
that the operator must create alongside the cron entry — it is *not* an
Alembic migration in the AIFlow repo, because retention policy / index
strategy / partitioning are operator-owned decisions:

```sql
CREATE TABLE rag_collection_metrics_jsonl (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    collection_id   text NOT NULL,
    mrr5            double precision NOT NULL,
    p95_latency_ms  double precision NOT NULL,
    query_count     integer NOT NULL,
    harness_version text NOT NULL,
    measured_at     timestamptz NOT NULL,
    raw_jsonl       jsonb NOT NULL
);

CREATE INDEX ix_rag_metrics_collection_measured
  ON rag_collection_metrics_jsonl (collection_id, measured_at DESC);
```

Wire-up the cron entry to pipe stdout through a `psql` ingest:

```bash
0 2 * * * cd /opt/aiflow && \
  .venv/Scripts/python.exe scripts/run_nightly_rag_metrics.py \
    --collection-id $UC2_COLLECTION_ID \
    --query-set data/fixtures/rag_metrics/uc2_aszf_query_set.json \
    --output jsonl | \
  jq -c . | \
  while read line; do \
    psql "$AIFLOW_DATABASE__URL" -c "INSERT INTO rag_collection_metrics_jsonl (collection_id, mrr5, p95_latency_ms, query_count, harness_version, measured_at, raw_jsonl) VALUES ('$(echo $line | jq -r .collection_id)', $(echo $line | jq -r .mrr5), $(echo $line | jq -r .p95_latency_ms), $(echo $line | jq -r .query_count), '$(echo $line | jq -r .harness_version)', '$(echo $line | jq -r .measured_at)', '$line'::jsonb)"; \
  done
```

> **Note:** The CLI does not embed the persistence step on purpose. If
> your environment has APScheduler running inside the AIFlow API, point
> it at the harness directly instead of cron. See SS-FU-followup-1 in
> the S145 retro for the in-process path.

## 4. Grafana panel

Import `docs/grafana/rag_collection_metrics_panel.json` via Grafana UI:
**Dashboards → New → Import → paste JSON**. Replace the
`${DS_AIFLOW_PG}` template variable with the operator's PostgreSQL
datasource UID before saving.

The dashboard exposes four panels:
1. **MRR@5 — per collection (nightly)** time-series with thresholds at
   0.35 / 0.45 / 0.55 (red / orange / yellow / green).
2. **p95 query latency (ms)** time-series with thresholds at
   1500 / 3000 ms.
3. **Latest MRR@5 — last 24h** stat panel for at-a-glance status.
4. **Latest run per collection** table with full row context.

## 5. Alert thresholds (placeholder)

The thresholds below are **placeholders** until 2–3 nights of real data
exist. Re-baseline with the operator after the first week.

| Threshold | Severity | Condition |
|---|---|---|
| `MRR@5 < 0.55` for a single night | INFO | Sprint J baseline floor — investigate whichever collection regressed |
| `MRR@5 < 0.45` for two consecutive nights | WARN | Likely signal — page on-call |
| `MRR@5 < 0.35` for any single night | PAGE | Hard floor — model-tier regression or corrupt data |
| `p95_latency_ms > 3000` for any single night | WARN | Investigate pgvector / reranker / query-embedder warmup |

Tune downward (toward stricter) once a stable baseline is established.

## 6. Smoke / regression

```bash
# Unit (no services) — must pass before nightly is enabled
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest \
  tests/unit/services/rag_metrics/ -q --no-cov

# Integration — gated; run on-demand after collection seeding
AIFLOW_RUN_NIGHTLY_RAG_METRICS=1 \
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest \
  tests/integration/services/rag_metrics/ -q --no-cov
```

## 7. Disabling

Comment-out the cron entry. The harness module + dashboard JSON stay
inert — they are pure inputs that nothing else in the AIFlow runtime
imports. There is no rollback migration to run.
