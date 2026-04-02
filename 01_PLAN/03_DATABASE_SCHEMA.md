# AIFlow - Database Schema (Konszolidalt)

## PostgreSQL Database: `aiflow`

**Teljes schema:** 41 tabla, 6 view, 60+ index, 25 Alembic migracio (001-025)
**Utolso frissites:** 2026-04-02 (v1.0.0-rc1 audit → v1.0.0 final)

> **Megjegyzes:** Az eredeti terv 36 tablat es 13 view-t tartalmazott.
> A vegleges schema 41 tabla (5 uj: api_keys, email_fetch_history, generated_diagrams, media_jobs, rpa_configs/rpa_execution_log)
> es 6 view (v_daily_team_costs, v_instance_stats, v_model_usage, v_monthly_budget, v_test_trends, v_workflow_metrics).
> Migraciok: 001-013 (Phase 1-7 framework), 014-025 (Fazis 0-5 service generalizacio + security fix).

---

## 1. Core Execution Tables

### workflow_runs

```sql
CREATE TABLE workflow_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_name VARCHAR(255) NOT NULL,
    workflow_version VARCHAR(50) NOT NULL,
    skill_name VARCHAR(255),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    input_data JSONB NOT NULL,
    output_data JSONB,
    error TEXT,
    error_type VARCHAR(100),
    trace_id VARCHAR(255),
    trace_url TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    total_duration_ms FLOAT,
    total_cost_usd DECIMAL(10,6) DEFAULT 0,
    sla_target_seconds INT,
    sla_met BOOLEAN,
    team_id UUID,  -- FK added in 005_add_security.py
    user_id UUID,  -- FK added in 005_add_security.py
    job_id VARCHAR(255),
    priority INT DEFAULT 3,
    instance_id UUID REFERENCES skill_instances(id) ON DELETE SET NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT chk_workflow_runs_status CHECK (
        status IN ('pending', 'running', 'completed', 'failed', 'paused', 'cancelled')
    )
);

CREATE INDEX idx_wr_workflow_name ON workflow_runs(workflow_name);
CREATE INDEX idx_wr_status ON workflow_runs(status);
CREATE INDEX idx_wr_team_id ON workflow_runs(team_id);
CREATE INDEX idx_wr_created_at ON workflow_runs(created_at DESC);
CREATE INDEX idx_wr_job_id ON workflow_runs(job_id);
CREATE INDEX idx_wr_skill_name ON workflow_runs(skill_name);
CREATE INDEX idx_wr_user_id ON workflow_runs(user_id);
CREATE INDEX idx_wr_instance_id ON workflow_runs(instance_id);
```

### step_runs

```sql
CREATE TABLE step_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_run_id UUID NOT NULL REFERENCES workflow_runs(id) ON DELETE CASCADE,
    step_name VARCHAR(255) NOT NULL,
    step_index INT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    input_data JSONB,
    output_data JSONB,
    error TEXT,
    error_type VARCHAR(100),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    duration_ms FLOAT,
    retry_count INT DEFAULT 0,
    max_retries INT DEFAULT 3,
    cost_usd DECIMAL(10,6) DEFAULT 0,
    model_used VARCHAR(100),
    input_tokens INT,
    output_tokens INT,
    scores JSONB DEFAULT '{}',
    quality_gate_passed BOOLEAN,
    checkpoint_data JSONB,
    checkpoint_version INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_sr_workflow_run_id ON step_runs(workflow_run_id);
CREATE INDEX idx_sr_step_name ON step_runs(step_name);
CREATE INDEX idx_sr_status ON step_runs(status);
```

---

## 2. Catalog Tables

### skills

```sql
CREATE TABLE skills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) UNIQUE NOT NULL,
    display_name VARCHAR(255),
    version VARCHAR(50) NOT NULL,
    skill_type VARCHAR(20) DEFAULT 'ai',  -- ai, rpa, hybrid
    description TEXT,
    author VARCHAR(255),
    manifest JSONB NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    installed_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### skill_instances

```sql
CREATE TABLE skill_instances (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instance_name VARCHAR(255) UNIQUE NOT NULL,
    display_name VARCHAR(500),
    skill_name VARCHAR(255) NOT NULL,
    skill_version VARCHAR(50) NOT NULL,
    customer_id VARCHAR(255) NOT NULL,
    config JSONB NOT NULL,
    prompt_namespace VARCHAR(255) NOT NULL,
    collection_name VARCHAR(255),
    status VARCHAR(20) DEFAULT 'active',
    budget_monthly_usd DECIMAL(10,2),
    budget_used_usd DECIMAL(10,2) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_si_skill ON skill_instances(skill_name);
CREATE INDEX idx_si_customer ON skill_instances(customer_id);
CREATE INDEX idx_si_status ON skill_instances(status);
```

### workflow_definitions

```sql
CREATE TABLE workflow_definitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) UNIQUE NOT NULL,
    skill_id UUID REFERENCES skills(id) ON DELETE SET NULL,
    version VARCHAR(50) NOT NULL,
    description TEXT,
    complexity VARCHAR(20) DEFAULT 'medium',
    dag_definition JSONB NOT NULL,
    step_definitions JSONB NOT NULL,
    metadata JSONB DEFAULT '{}',
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_wd_skill_id ON workflow_definitions(skill_id);
```

### skill_prompt_versions

```sql
CREATE TABLE skill_prompt_versions (
    skill_name VARCHAR(255) NOT NULL,
    skill_version VARCHAR(50) NOT NULL,
    prompt_name VARCHAR(255) NOT NULL,
    langfuse_version INT NOT NULL,
    validated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (skill_name, skill_version, prompt_name)
);
```

---

## 3. Security Tables

### teams

```sql
CREATE TABLE teams (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    budget_monthly_usd DECIMAL(10,2),
    budget_used_usd DECIMAL(10,2) DEFAULT 0,
    budget_reset_day INT DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### users

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    team_id UUID REFERENCES teams(id) ON DELETE SET NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'viewer',
    api_key_hash VARCHAR(255),
    api_key_prefix VARCHAR(10),
    is_active BOOLEAN DEFAULT TRUE,
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_users_team_id ON users(team_id);
CREATE INDEX idx_users_api_key_prefix ON users(api_key_prefix);
```

### audit_log

```sql
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    team_id UUID REFERENCES teams(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100),
    resource_id VARCHAR(255),
    details JSONB,
    ip_address VARCHAR(45),
    user_agent TEXT,
    duration_ms FLOAT
);

CREATE INDEX idx_al_timestamp ON audit_log(timestamp DESC);
CREATE INDEX idx_al_user_id ON audit_log(user_id);
CREATE INDEX idx_al_action ON audit_log(action);
CREATE INDEX idx_al_resource ON audit_log(resource_type, resource_id);
CREATE INDEX idx_al_team_id ON audit_log(team_id);
```

---

## 4. Cost Tracking

### cost_records

```sql
CREATE TABLE cost_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_run_id UUID REFERENCES workflow_runs(id) ON DELETE CASCADE,
    step_name VARCHAR(255),
    model VARCHAR(255) NOT NULL,
    provider VARCHAR(100),
    input_tokens INT NOT NULL DEFAULT 0,
    output_tokens INT NOT NULL DEFAULT 0,
    cost_usd DECIMAL(10,6) NOT NULL,
    team_id UUID REFERENCES teams(id) ON DELETE SET NULL,
    recorded_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_cr_workflow_run_id ON cost_records(workflow_run_id);
CREATE INDEX idx_cr_team_id ON cost_records(team_id);
CREATE INDEX idx_cr_model ON cost_records(model);
CREATE INDEX idx_cr_recorded_at ON cost_records(recorded_at DESC);
```

### Cost Views

```sql
CREATE VIEW v_daily_team_costs AS
SELECT
    team_id,
    DATE(recorded_at) as day,
    model,
    COUNT(*) as call_count,
    SUM(input_tokens) as total_input_tokens,
    SUM(output_tokens) as total_output_tokens,
    SUM(cost_usd) as total_cost_usd
FROM cost_records
GROUP BY team_id, DATE(recorded_at), model;

CREATE VIEW v_monthly_budget AS
SELECT
    t.id as team_id,
    t.name as team_name,
    t.budget_monthly_usd,
    COALESCE(SUM(cr.cost_usd), 0) as used_usd,
    t.budget_monthly_usd - COALESCE(SUM(cr.cost_usd), 0) as remaining_usd,
    ROUND(COALESCE(SUM(cr.cost_usd), 0) / NULLIF(t.budget_monthly_usd, 0) * 100, 1) as usage_pct
FROM teams t
LEFT JOIN cost_records cr ON cr.team_id = t.id
    AND cr.recorded_at >= DATE_TRUNC('month', NOW())
GROUP BY t.id, t.name, t.budget_monthly_usd;
```

---

## 5. Scheduling

### schedules

```sql
CREATE TABLE schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) UNIQUE NOT NULL,
    workflow_name VARCHAR(255) NOT NULL,
    trigger_type VARCHAR(20) NOT NULL,
    cron_expression VARCHAR(100),
    event_pattern VARCHAR(255),
    webhook_path VARCHAR(255),
    input_data JSONB DEFAULT '{}',
    priority INT DEFAULT 3,
    enabled BOOLEAN DEFAULT TRUE,
    team_id UUID REFERENCES teams(id) ON DELETE SET NULL,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    last_run_at TIMESTAMPTZ,
    last_run_status VARCHAR(20),
    next_run_at TIMESTAMPTZ,
    run_count INT DEFAULT 0,
    error_count INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_sched_team_id ON schedules(team_id);
CREATE INDEX idx_sched_enabled ON schedules(enabled);
```

---

## 6. Human-in-the-Loop

### human_reviews

```sql
CREATE TABLE human_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_run_id UUID NOT NULL REFERENCES workflow_runs(id),
    step_name VARCHAR(255) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    question TEXT NOT NULL,
    context JSONB,
    options JSONB,
    priority VARCHAR(20) DEFAULT 'medium',
    deadline TIMESTAMPTZ,
    decision TEXT,
    feedback TEXT,
    reviewer_id UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);

CREATE INDEX idx_hr_status ON human_reviews(status);
CREATE INDEX idx_hr_workflow_run_id ON human_reviews(workflow_run_id);
CREATE INDEX idx_hr_reviewer_id ON human_reviews(reviewer_id);
```

---

## 7. A/B Testing

### ab_experiments, ab_assignments, ab_outcomes

```sql
CREATE TABLE ab_experiments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) UNIQUE NOT NULL,
    prompt_name VARCHAR(255) NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    variants JSONB NOT NULL,
    traffic_split JSONB NOT NULL,
    metrics JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ
);

CREATE TABLE ab_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id UUID REFERENCES ab_experiments(id) ON DELETE CASCADE,
    user_id VARCHAR(255) NOT NULL,
    variant VARCHAR(100) NOT NULL,
    assigned_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE ab_outcomes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id UUID REFERENCES ab_experiments(id) ON DELETE CASCADE,
    assignment_id UUID REFERENCES ab_assignments(id) ON DELETE CASCADE,
    workflow_run_id UUID REFERENCES workflow_runs(id) ON DELETE SET NULL,
    variant VARCHAR(100) NOT NULL,
    metrics JSONB NOT NULL,
    recorded_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_aba_experiment_id ON ab_assignments(experiment_id);
CREATE INDEX idx_abo_experiment_id ON ab_outcomes(experiment_id);
```

---

## 8. ML Model Registry (UJ - 15_ML_MODEL_INTEGRATION)

### model_registry

```sql
CREATE TABLE model_registry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) UNIQUE NOT NULL,
    model_type VARCHAR(50) NOT NULL,
    provider VARCHAR(100) NOT NULL,
    version VARCHAR(100) NOT NULL,
    lifecycle VARCHAR(50) DEFAULT 'registered',
    serving_mode VARCHAR(50) NOT NULL,
    endpoint_url TEXT,
    model_path TEXT,
    capabilities JSONB DEFAULT '[]',
    pricing_model VARCHAR(50) DEFAULT 'per_token',
    cost_per_input_token DECIMAL(12,8) DEFAULT 0,
    cost_per_output_token DECIMAL(12,8) DEFAULT 0,
    cost_per_request DECIMAL(10,6) DEFAULT 0,
    priority INT DEFAULT 100,
    fallback_model VARCHAR(255),
    avg_latency_ms FLOAT,
    tags JSONB DEFAULT '[]',
    config JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT chk_model_type CHECK (
        model_type IN ('llm', 'embedding', 'classification', 'extraction', 'vision', 'speech_to_text', 'custom')
    ),
    CONSTRAINT chk_lifecycle CHECK (
        lifecycle IN ('registered', 'tested', 'staging', 'production', 'deprecated', 'retired')
    ),
    CONSTRAINT chk_serving_mode CHECK (
        serving_mode IN ('api', 'local', 'server', 'sidecar')
    )
);

CREATE INDEX idx_mr_model_type ON model_registry(model_type);
CREATE INDEX idx_mr_lifecycle ON model_registry(lifecycle);
CREATE INDEX idx_mr_provider ON model_registry(provider);
```

### embedding_models

```sql
CREATE TABLE embedding_models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id UUID REFERENCES model_registry(id),
    name VARCHAR(255) UNIQUE NOT NULL,
    dimensions INT NOT NULL,
    max_input_tokens INT NOT NULL DEFAULT 8192,
    supports_batch BOOLEAN DEFAULT TRUE,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_em_model_id ON embedding_models(model_id);
```

---

## 9. Vector Store & Documents (UJ - 16_RAG_VECTORSTORE)

### collections

```sql
CREATE TABLE collections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    skill_name VARCHAR(255) NOT NULL,
    embedding_model_id UUID REFERENCES embedding_models(id) ON DELETE SET NULL,
    document_count INT DEFAULT 0,
    chunk_count INT DEFAULT 0,
    is_shared BOOLEAN DEFAULT FALSE,
    chunking_config JSONB DEFAULT '{}',
    search_config JSONB DEFAULT '{}',
    team_id UUID REFERENCES teams(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(name, skill_name)
);
```

### documents

```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    filename VARCHAR(500) NOT NULL,
    file_type VARCHAR(20) NOT NULL,
    file_hash_sha256 VARCHAR(64) NOT NULL,
    document_type VARCHAR(100) NOT NULL,
    department VARCHAR(100),
    language VARCHAR(10) DEFAULT 'hu',
    status VARCHAR(20) DEFAULT 'draft',
    effective_from DATE,
    effective_until DATE,
    version_number INT DEFAULT 1,
    supersedes_id UUID REFERENCES documents(id) ON DELETE SET NULL,
    skill_name VARCHAR(255) NOT NULL,
    collection_name VARCHAR(255) NOT NULL,
    chunk_count INT DEFAULT 0,
    embedding_model VARCHAR(100),
    ingestion_status VARCHAR(20) DEFAULT 'pending',
    source_type VARCHAR(50),
    source_uri TEXT,
    storage_path TEXT NOT NULL,
    last_ingested_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT chk_doc_status CHECK (
        status IN ('draft', 'active', 'superseded', 'revoked', 'archived')
    ),
    CONSTRAINT chk_ingestion_status CHECK (
        ingestion_status IN ('pending', 'processing', 'completed', 'failed', 'stale')
    )
);

CREATE INDEX idx_doc_skill ON documents(skill_name, collection_name);
CREATE INDEX idx_doc_status ON documents(status);
CREATE INDEX idx_doc_hash ON documents(file_hash_sha256);
CREATE INDEX idx_doc_supersedes ON documents(supersedes_id);
```

### chunks (pgvector)

```sql
-- Elofeltetel: CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    token_count INT NOT NULL,
    chunk_index INT NOT NULL,
    page_start INT,
    page_end INT,
    section_title VARCHAR(500),
    section_hierarchy JSONB,
    parent_chunk_id UUID REFERENCES chunks(id) ON DELETE SET NULL,
    embedding vector(1536),
    embedding_model VARCHAR(100) NOT NULL,
    content_tsv tsvector,
    skill_name VARCHAR(255) NOT NULL,
    collection_name VARCHAR(255) NOT NULL,
    document_title VARCHAR(500),
    document_status VARCHAR(20),
    effective_from DATE,
    effective_until DATE,
    language VARCHAR(10),
    department VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_chunks_embedding ON chunks
    USING hnsw (embedding vector_cosine_ops) WITH (m=16, ef_construction=64);
CREATE INDEX idx_chunks_tsv ON chunks USING GIN (content_tsv);
CREATE INDEX idx_chunks_skill_coll ON chunks(skill_name, collection_name);
CREATE INDEX idx_chunks_status ON chunks(document_status);
CREATE INDEX idx_chunks_document_id ON chunks(document_id);
```

### document_sync_schedules

```sql
CREATE TABLE document_sync_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) UNIQUE NOT NULL,
    collection_id UUID REFERENCES collections(id),
    source_type VARCHAR(50) NOT NULL,
    source_config JSONB NOT NULL,
    sync_cron VARCHAR(100) NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    last_sync_at TIMESTAMPTZ,
    last_sync_status VARCHAR(20),
    last_sync_error TEXT,
    files_synced INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 10. Test Data Management (UJ - 18_TESTING_AUTOMATION)

### test_datasets

```sql
CREATE TABLE test_datasets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) UNIQUE NOT NULL,
    skill_name VARCHAR(255),
    test_type VARCHAR(50) NOT NULL,
    description TEXT,
    tags JSONB DEFAULT '[]',
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT chk_test_type CHECK (
        test_type IN ('prompt', 'api', 'e2e', 'ui', 'unit', 'integration', 'rag')
    )
);

CREATE INDEX idx_tds_created_by ON test_datasets(created_by);
```

### test_cases

```sql
CREATE TABLE test_cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id UUID NOT NULL REFERENCES test_datasets(id) ON DELETE CASCADE,
    name VARCHAR(500) NOT NULL,
    category VARCHAR(100),
    input_data JSONB NOT NULL,
    expected_output JSONB,
    assertions JSONB DEFAULT '[]',
    tags JSONB DEFAULT '[]',
    priority INT DEFAULT 3,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_tc_dataset_id ON test_cases(dataset_id);
CREATE INDEX idx_tc_category ON test_cases(category);
```

### test_results

```sql
CREATE TABLE test_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    test_case_id UUID NOT NULL REFERENCES test_cases(id),
    run_id VARCHAR(255) NOT NULL,
    passed BOOLEAN NOT NULL,
    actual_output JSONB,
    scores JSONB DEFAULT '{}',
    error TEXT,
    duration_ms FLOAT,
    cost_usd DECIMAL(10,6),
    model_used VARCHAR(100),
    prompt_version INT,
    executed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_tr_test_case_id ON test_results(test_case_id);
CREATE INDEX idx_tr_run_id ON test_results(run_id);
CREATE INDEX idx_tr_executed_at ON test_results(executed_at DESC);
```

---

## 11. Osszes Monitoring View

```sql
-- Workflow hasznalat es sikeresseg
CREATE VIEW v_workflow_metrics AS
SELECT
    workflow_name,
    DATE(created_at) as day,
    COUNT(*) as total_runs,
    COUNT(*) FILTER (WHERE status = 'completed') as successful,
    COUNT(*) FILTER (WHERE status = 'failed') as failed,
    ROUND(COUNT(*) FILTER (WHERE status = 'completed')::decimal /
        NULLIF(COUNT(*), 0) * 100, 1) as success_rate,
    ROUND(AVG(total_duration_ms)) as avg_duration_ms,
    ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP
        (ORDER BY total_duration_ms)) as p95_duration_ms,
    ROUND(SUM(total_cost_usd)::numeric, 2) as total_cost_usd,
    ROUND(COUNT(*) FILTER (WHERE sla_met)::decimal /
        NULLIF(COUNT(*), 0) * 100, 1) as sla_pct
FROM workflow_runs
GROUP BY workflow_name, DATE(created_at);

-- Team budget hasznalat
CREATE VIEW v_team_budget AS
SELECT
    t.name as team_name,
    t.budget_monthly_usd,
    COALESCE(SUM(cr.cost_usd), 0) as used_usd,
    ROUND(COALESCE(SUM(cr.cost_usd), 0) /
        NULLIF(t.budget_monthly_usd, 0) * 100, 1) as usage_pct
FROM teams t
LEFT JOIN cost_records cr ON cr.team_id = t.id
    AND cr.recorded_at >= DATE_TRUNC('month', NOW())
GROUP BY t.name, t.budget_monthly_usd;

-- Modell hasznalat
CREATE VIEW v_model_usage AS
SELECT
    model,
    DATE(recorded_at) as day,
    COUNT(*) as call_count,
    SUM(input_tokens) as input_tokens,
    SUM(output_tokens) as output_tokens,
    ROUND(SUM(cost_usd)::numeric, 4) as total_cost_usd
FROM cost_records
GROUP BY model, DATE(recorded_at);

-- Collection egeszseg (RAG)
CREATE VIEW v_collection_health AS
SELECT
    c.name, c.skill_name, c.chunk_count,
    COUNT(DISTINCT d.id) FILTER (WHERE d.status = 'active') as active_docs,
    COUNT(ch.id) FILTER (WHERE ch.embedding IS NULL) as missing_embeddings,
    MAX(d.last_ingested_at) as last_ingestion
FROM collections c
LEFT JOIN documents d ON d.collection_name = c.name AND d.skill_name = c.skill_name
LEFT JOIN chunks ch ON ch.document_id = d.id
GROUP BY c.id, c.name, c.skill_name, c.chunk_count;

-- Dokumentum frissesseg (RAG)
CREATE VIEW v_document_freshness AS
SELECT
    d.id, d.title, d.status, d.skill_name, d.collection_name,
    d.effective_from, d.effective_until,
    CASE
        WHEN d.effective_until < CURRENT_DATE THEN 'expired'
        WHEN d.effective_from > CURRENT_DATE THEN 'future'
        WHEN d.status = 'active' THEN 'current'
        ELSE d.status
    END as freshness_status
FROM documents d;

-- Teszt eredmeny trendek
CREATE VIEW v_test_trends AS
SELECT
    td.name as dataset_name,
    td.skill_name,
    DATE(tr.executed_at) as day,
    COUNT(*) as total_tests,
    COUNT(*) FILTER (WHERE tr.passed) as passed,
    ROUND(COUNT(*) FILTER (WHERE tr.passed)::decimal / NULLIF(COUNT(*), 0) * 100, 1) as pass_rate,
    AVG(tr.duration_ms) as avg_duration_ms,
    SUM(tr.cost_usd) as total_cost_usd
FROM test_results tr
JOIN test_cases tc ON tc.id = tr.test_case_id
JOIN test_datasets td ON td.id = tc.dataset_id
GROUP BY td.name, td.skill_name, DATE(tr.executed_at);
```

---

## 12. Migration Strategy (Javitott Sorrend)

```
alembic/versions/
    001_initial_core.py           # Phase 1: workflow_runs, step_runs
    002_add_catalog.py            # Phase 2: skills, workflow_definitions, skill_prompt_versions
    003_add_model_registry.py     # Phase 2: model_registry, embedding_models
    004_add_vectorstore.py        # Phase 2: collections, documents, chunks, document_sync_schedules
    005_add_security.py           # Phase 5: teams, users, audit_log + ALTER workflow_runs ADD FK(team_id, user_id)
    006_add_cost_tracking.py      # Phase 6: cost_records, cost views
    007_add_scheduling.py         # Phase 7: schedules
    008_add_human_reviews.py      # Phase 7: human_reviews
    009_add_ab_testing.py         # Phase 7: ab_experiments, ab_assignments, ab_outcomes
    010_add_test_management.py    # Phase 7: test_datasets, test_cases, test_results
    011_add_monitoring_views.py   # Phase 7: v_workflow_metrics, v_team_budget, stb.
    012_add_skill_instances.py    # Phase 2+: skill_instances + ALTER workflow_runs ADD instance_id
    ...                           # Phase 1+: test tracking tablak (013-019)
    020_add_conversations.py      # Phase 2+: conversations, conversation_messages
```

---

## 13. Tabla Osszesito

| Tabla | Becsult Rekordok/Nap | Fo Hasznalat | Phase |
|-------|---------------------|-------------|-------|
| workflow_runs | ~450 | Workflow futtatas tracking | 1 |
| step_runs | ~2,500 | Step szintu tracking + checkpoint | 1 |
| skills | ~10-50 (statikus) | Telepitett skill-ek | 2 |
| workflow_definitions | ~20-100 (statikus) | DAG definiciok | 2 |
| skill_prompt_versions | ~50-200 (statikus) | Prompt verzio mapping | 2 |
| model_registry | ~20-50 (statikus) | ML/LLM modellek | 2 |
| embedding_models | ~5-10 (statikus) | Embedding config | 2 |
| collections | ~5-20 (statikus) | RAG chunk csoportok | 2 |
| documents | ~100-1,000 (lassan no) | RAG forras dokumentumok | 2 |
| chunks | ~10,000-100,000 (lassan no) | Vector embedding chunks | 2 |
| document_sync_schedules | ~5-20 (statikus) | Kulso sync config | 7 |
| teams | ~5-20 (statikus) | Csapatok + budget | 5 |
| users | ~20-100 (statikus) | Felhasznalok + RBAC | 5 |
| audit_log | ~1,000 | Audit trail | 5 |
| cost_records | ~5,000 | Per-model hivas koltseg | 6 |
| schedules | ~10-50 (statikus) | Cron/event triggerek | 7 |
| human_reviews | ~10-50 | HITL dontes rekordok | 7 |
| ab_experiments | ~2-5 aktiv | Prompt A/B tesztek | 7 |
| ab_assignments | ~100-1,000 | A/B kiosztasok | 7 |
| ab_outcomes | ~100-1,000 | A/B eredmenyek | 7 |
| test_datasets | ~20-50 (statikus) | Teszt adat csoportok | 7 |
| test_cases | ~5,000-50,000 (lassan no) | Centralizalt teszt esetek | 7 |
| test_results | ~10,000 | Teszt eredmenyek tortenete | 7 |

---

## 14. Development Step Tracking (24_TESTING_REGRESSION_STRATEGY)

### development_steps

```sql
CREATE TABLE development_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    step_code VARCHAR(50) UNIQUE NOT NULL,
    phase INT NOT NULL,
    developer VARCHAR(255) NOT NULL,
    ai_assisted BOOLEAN DEFAULT FALSE,
    step_type VARCHAR(50) NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    files_changed JSONB NOT NULL DEFAULT '[]',
    commit_hash VARCHAR(40),
    pr_number INT,
    branch_name VARCHAR(255),
    new_tests_added INT DEFAULT 0,
    regression_level VARCHAR(5),
    regression_run_id UUID,
    regression_result VARCHAR(20),
    total_tests_run INT DEFAULT 0,
    tests_passed INT DEFAULT 0,
    tests_failed INT DEFAULT 0,
    tests_skipped INT DEFAULT 0,
    coverage_before DECIMAL(5,2),
    coverage_after DECIMAL(5,2),
    test_duration_seconds FLOAT,
    reviewed_by VARCHAR(255),
    reviewed_at TIMESTAMPTZ,
    merged_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_ds_phase ON development_steps(phase);
CREATE INDEX idx_ds_developer ON development_steps(developer);
CREATE INDEX idx_ds_created_at ON development_steps(created_at DESC);
```

---

## 15. Test Suites & Regression Tracking

### test_suites

```sql
CREATE TABLE test_suites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    path VARCHAR(500) NOT NULL,
    suite_type VARCHAR(50) NOT NULL,
    priority VARCHAR(20) DEFAULT 'medium',
    max_duration_seconds INT,
    coverage_target DECIMAL(5,2),
    requires_services JSONB DEFAULT '[]',
    run_on JSONB DEFAULT '["pr", "merge"]',
    skill_name VARCHAR(255),
    cost_usd_estimated DECIMAL(10,4) DEFAULT 0,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### test_suite_components

```sql
CREATE TABLE test_suite_components (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    suite_id UUID NOT NULL REFERENCES test_suites(id) ON DELETE CASCADE,
    component_pattern VARCHAR(500) NOT NULL,
    source_files JSONB DEFAULT '[]',
    UNIQUE(suite_id, component_pattern)
);

CREATE INDEX idx_tsc_suite_id ON test_suite_components(suite_id);
```

### regression_runs

```sql
CREATE TABLE regression_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_code VARCHAR(50) UNIQUE NOT NULL,
    trigger_type VARCHAR(50) NOT NULL,
    trigger_ref VARCHAR(255),
    regression_level VARCHAR(5) NOT NULL,
    development_step_id UUID REFERENCES development_steps(id),
    suites_run INT DEFAULT 0,
    suites_passed INT DEFAULT 0,
    suites_failed INT DEFAULT 0,
    total_tests INT DEFAULT 0,
    tests_passed INT DEFAULT 0,
    tests_failed INT DEFAULT 0,
    tests_skipped INT DEFAULT 0,
    tests_error INT DEFAULT 0,
    new_tests INT DEFAULT 0,
    removed_tests INT DEFAULT 0,
    regressions_detected INT DEFAULT 0,
    new_failures INT DEFAULT 0,
    flaky_detected INT DEFAULT 0,
    coverage_total DECIMAL(5,2),
    coverage_changed DECIMAL(5,2),
    coverage_gate_passed BOOLEAN,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    duration_seconds FLOAT,
    cost_usd DECIMAL(10,4) DEFAULT 0,
    overall_result VARCHAR(20) NOT NULL,
    gate_decision VARCHAR(20),
    previous_run_id UUID REFERENCES regression_runs(id),
    artifacts_path TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_rr_created_at ON regression_runs(created_at DESC);
CREATE INDEX idx_rr_overall_result ON regression_runs(overall_result);
CREATE INDEX idx_rr_dev_step ON regression_runs(development_step_id);
```

### regression_suite_results

```sql
CREATE TABLE regression_suite_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    regression_run_id UUID NOT NULL REFERENCES regression_runs(id) ON DELETE CASCADE,
    suite_id UUID NOT NULL REFERENCES test_suites(id),
    suite_name VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL,
    tests_total INT DEFAULT 0,
    tests_passed INT DEFAULT 0,
    tests_failed INT DEFAULT 0,
    tests_skipped INT DEFAULT 0,
    tests_error INT DEFAULT 0,
    regressions INT DEFAULT 0,
    coverage_pct DECIMAL(5,2),
    coverage_target DECIMAL(5,2),
    coverage_gate_passed BOOLEAN,
    duration_ms FLOAT,
    cost_usd DECIMAL(10,4) DEFAULT 0,
    failure_details JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_rsr_run_id ON regression_suite_results(regression_run_id);
CREATE INDEX idx_rsr_status ON regression_suite_results(status);
```

### regression_test_results

```sql
CREATE TABLE regression_test_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    regression_run_id UUID NOT NULL REFERENCES regression_runs(id) ON DELETE CASCADE,
    suite_result_id UUID REFERENCES regression_suite_results(id) ON DELETE CASCADE,
    test_path VARCHAR(500) NOT NULL,
    test_name VARCHAR(255) NOT NULL,
    suite_name VARCHAR(255) NOT NULL,
    component VARCHAR(255),
    status VARCHAR(20) NOT NULL,
    previous_status VARCHAR(20),
    is_regression BOOLEAN DEFAULT FALSE,
    is_new_test BOOLEAN DEFAULT FALSE,
    error_message TEXT,
    error_traceback TEXT,
    error_type VARCHAR(255),
    duration_ms FLOAT,
    tags JSONB DEFAULT '[]',
    introduced_by_commit VARCHAR(40),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_rtr_run_id ON regression_test_results(regression_run_id);
CREATE INDEX idx_rtr_is_regression ON regression_test_results(is_regression);
```

---

## 16. Coverage Tracking

### coverage_snapshots

```sql
CREATE TABLE coverage_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    regression_run_id UUID NOT NULL REFERENCES regression_runs(id) ON DELETE CASCADE,
    total_statements INT,
    covered_statements INT,
    total_branches INT,
    covered_branches INT,
    total_coverage_pct DECIMAL(5,2),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_cs_run_id ON coverage_snapshots(regression_run_id);
```

### coverage_module_details

```sql
CREATE TABLE coverage_module_details (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    snapshot_id UUID NOT NULL REFERENCES coverage_snapshots(id) ON DELETE CASCADE,
    module_path VARCHAR(500) NOT NULL,
    component VARCHAR(255),
    statements INT,
    covered INT,
    coverage_pct DECIMAL(5,2),
    missing_lines JSONB,
    target_pct DECIMAL(5,2),
    gate_passed BOOLEAN
);

CREATE INDEX idx_cmd_snapshot_id ON coverage_module_details(snapshot_id);
CREATE INDEX idx_cmd_component ON coverage_module_details(component);
```

---

## 17. Flaky Test Tracking

```sql
CREATE TABLE flaky_test_tracking (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    test_path VARCHAR(500) NOT NULL,
    suite_name VARCHAR(255) NOT NULL,
    component VARCHAR(255),
    first_detected_at TIMESTAMPTZ NOT NULL,
    last_seen_at TIMESTAMPTZ,
    flaky_count INT DEFAULT 0,
    total_runs INT DEFAULT 0,
    flaky_rate DECIMAL(5,2),
    status VARCHAR(20) DEFAULT 'detected',
    root_cause TEXT,
    fix_commit VARCHAR(40),
    assigned_to VARCHAR(255),
    resolved_at TIMESTAMPTZ,
    quarantined_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_ftt_status ON flaky_test_tracking(status);
CREATE INDEX idx_ftt_test_path ON flaky_test_tracking(test_path);
```

---

## 18. Regression Matrix Rules (DB-backed)

```sql
CREATE TABLE regression_matrix_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_pattern VARCHAR(500) NOT NULL,
    target_suite_id UUID NOT NULL REFERENCES test_suites(id),
    is_full_regression BOOLEAN DEFAULT FALSE,
    reason TEXT,
    priority INT DEFAULT 100,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_rmr_source ON regression_matrix_rules(source_pattern);
```

---

## 19. Test & Regression Monitoring Views

```sql
CREATE VIEW v_weekly_regression_summary AS
SELECT
    DATE_TRUNC('week', rr.created_at) as week,
    COUNT(*) as total_runs,
    COUNT(*) FILTER (WHERE overall_result = 'ALL_PASS') as passed,
    COUNT(*) FILTER (WHERE overall_result = 'FAILED') as failed,
    SUM(regressions_detected) as total_regressions,
    SUM(new_tests) as new_tests_added,
    AVG(duration_seconds) as avg_duration_s,
    SUM(cost_usd) as total_cost_usd,
    AVG(coverage_total) as avg_coverage
FROM regression_runs rr
GROUP BY DATE_TRUNC('week', rr.created_at)
ORDER BY week DESC;

CREATE VIEW v_dev_steps_by_phase AS
SELECT
    phase,
    COUNT(*) as total_steps,
    SUM(new_tests_added) as total_new_tests,
    COUNT(*) FILTER (WHERE regression_result = 'ALL_PASS') as steps_all_pass,
    COUNT(*) FILTER (WHERE regression_result = 'FAILED') as steps_with_failures,
    AVG(coverage_after) as avg_coverage
FROM development_steps
GROUP BY phase ORDER BY phase;

CREATE VIEW v_component_coverage_trend AS
SELECT
    cmd.component,
    DATE(cs.created_at) as day,
    AVG(cmd.coverage_pct) as avg_coverage,
    MAX(cmd.target_pct) as target,
    BOOL_AND(cmd.gate_passed) as all_gates_passed
FROM coverage_module_details cmd
JOIN coverage_snapshots cs ON cs.id = cmd.snapshot_id
GROUP BY cmd.component, DATE(cs.created_at)
ORDER BY day DESC, cmd.component;

CREATE VIEW v_flaky_report AS
SELECT
    test_path, suite_name, status, flaky_count,
    total_runs, flaky_rate, assigned_to,
    EXTRACT(days FROM NOW() - first_detected_at) as days_open
FROM flaky_test_tracking
WHERE status != 'resolved'
ORDER BY flaky_rate DESC;

CREATE VIEW v_regression_fix_speed AS
SELECT
    DATE_TRUNC('week', rtr.created_at) as week,
    COUNT(*) as regressions,
    AVG(EXTRACT(epoch FROM (ds2.created_at - rtr.created_at)) / 3600) as avg_fix_hours
FROM regression_test_results rtr
LEFT JOIN development_steps ds2 ON ds2.commit_hash = rtr.introduced_by_commit
WHERE rtr.is_regression = TRUE
GROUP BY DATE_TRUNC('week', rtr.created_at)
ORDER BY week DESC;
```

---

## 20. Chat Conversations

### conversations

```sql
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    team_id UUID REFERENCES teams(id) ON DELETE SET NULL,
    skill_name VARCHAR(255) NOT NULL,
    title VARCHAR(500),
    message_count INT DEFAULT 0,
    last_message_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE conversation_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,  -- user, assistant, system
    content TEXT NOT NULL,
    citations JSONB,
    feedback VARCHAR(20),  -- thumbs_up, thumbs_down, null
    workflow_run_id UUID REFERENCES workflow_runs(id) ON DELETE SET NULL,
    tokens_used INT,
    cost_usd DECIMAL(10,6),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_conv_user ON conversations(user_id);
CREATE INDEX idx_conv_skill ON conversations(skill_name);
CREATE INDEX idx_cm_conv_id ON conversation_messages(conversation_id);
```

---

## 21. Teljes Migration Strategy (Konszolidalt)

```
alembic/versions/
    001_initial_core.py                # Phase 1: workflow_runs, step_runs
    002_add_catalog.py                 # Phase 2: skills, workflow_definitions, skill_prompt_versions
    003_add_model_registry.py          # Phase 2: model_registry, embedding_models
    004_add_vectorstore.py             # Phase 2: collections, documents, chunks, document_sync_schedules
    005_add_security.py                # Phase 5: teams, users, audit_log + ALTER workflow_runs ADD FK(team_id, user_id)
    006_add_cost_tracking.py           # Phase 6: cost_records, cost views
    007_add_scheduling.py              # Phase 7: schedules
    008_add_human_reviews.py           # Phase 7: human_reviews
    009_add_ab_testing.py              # Phase 7: ab_experiments, ab_assignments, ab_outcomes
    010_add_test_management.py         # Phase 7: test_datasets, test_cases, test_results
    011_add_monitoring_views.py        # Phase 7: v_workflow_metrics, v_team_budget, stb.
    012_add_skill_instances.py         # Phase 2+: skill_instances + ALTER workflow_runs ADD instance_id
    013_add_dev_step_tracking.py       # Phase 1+: development_steps
    014_add_test_suites.py             # Phase 1+: test_suites, test_suite_components
    015_add_regression_tracking.py     # Phase 1+: regression_runs, regression_suite_results, regression_test_results
    016_add_coverage_tracking.py       # Phase 1+: coverage_snapshots, coverage_module_details
    017_add_flaky_tracking.py          # Phase 1+: flaky_test_tracking
    018_add_regression_matrix.py       # Phase 1+: regression_matrix_rules
    019_add_test_regression_views.py   # Phase 1+: v_weekly_regression_summary stb.
    020_add_conversations.py           # Phase 2+: conversations, conversation_messages
```

---

## 22. Tabla Osszesito (Teljes)

| # | Tabla | Becsult rekordok | Fo hasznalat | Phase |
|---|-------|-----------------|-------------|-------|
| 1 | workflow_runs | ~450/nap | Workflow futtatas tracking | 1 |
| 2 | step_runs | ~2,500/nap | Step szintu tracking + checkpoint | 1 |
| 3 | skills | ~10-50 | Telepitett skill-ek | 2 |
| 3b | skill_instances | ~50-200 | Skill peldanyok per ugyfel | 2+ |
| 4 | workflow_definitions | ~20-100 | DAG definiciok | 2 |
| 5 | skill_prompt_versions | ~50-200 | Prompt verzio mapping | 2 |
| 6 | model_registry | ~20-50 | ML/LLM modellek | 2 |
| 7 | embedding_models | ~5-10 | Embedding config | 2 |
| 8 | collections | ~5-20 | RAG chunk csoportok | 2 |
| 9 | documents | ~100-1,000 | RAG forras dokumentumok | 2 |
| 10 | chunks | ~10,000-100,000 | Vector embedding chunks | 2 |
| 11 | document_sync_schedules | ~5-20 | Kulso sync config | 7 |
| 12 | teams | ~5-20 | Csapatok + budget | 5 |
| 13 | users | ~20-100 | Felhasznalok + RBAC | 5 |
| 14 | audit_log | ~1,000/nap | Audit trail | 5 |
| 15 | cost_records | ~5,000/nap | Per-model hivas koltseg | 6 |
| 16 | schedules | ~10-50 | Cron/event triggerek | 7 |
| 17 | human_reviews | ~10-50/nap | HITL dontes rekordok | 7 |
| 18 | ab_experiments | ~2-5 aktiv | Prompt A/B tesztek | 7 |
| 19 | ab_assignments | ~100-1,000 | A/B kiosztasok | 7 |
| 20 | ab_outcomes | ~100-1,000 | A/B eredmenyek | 7 |
| 21 | test_datasets | ~20-50 | Teszt adat csoportok | 7 |
| 22 | test_cases | ~5,000-50,000 | Centralizalt teszt esetek | 7 |
| 23 | test_results | ~10,000/nap | Teszt eredmenyek tortenete | 7 |
| 24 | development_steps | ~15-30/het | Fejlesztesi lepes nyilvantartas | 1+ |
| 25 | test_suites | ~20-50 | Suite definiciok | 1+ |
| 26 | test_suite_components | ~100-300 | Suite-komponens mapping | 1+ |
| 27 | regression_runs | ~40-80/het | Regresszios futtas rekordok | 1+ |
| 28 | regression_suite_results | ~400-800/het | Per-suite eredmenyek | 1+ |
| 29 | regression_test_results | ~50-200/het | Bukott/regresszios tesztek | 1+ |
| 30 | coverage_snapshots | ~40-80/het | Coverage pillanatkepek | 1+ |
| 31 | coverage_module_details | ~2,000-4,000/het | Per-modul coverage | 1+ |
| 32 | flaky_test_tracking | ~5-20 | Flaky teszt kovetes | 1+ |
| 33 | regression_matrix_rules | ~50-100 | Matrix szabalyok | 1+ |
| 34 | conversations | ~100-500/nap | RAG chat beszelgetesek | 2+ |
| 35 | conversation_messages | ~500-5,000/nap | Chat uzenetek + citations | 2+ |

**Osszes tabla:** 41 (v1.0.0 final, introspect alapjan)
**Osszes view:** 6 (v_daily_team_costs, v_instance_stats, v_model_usage, v_monthly_budget, v_test_trends, v_workflow_metrics)
**Osszes index:** 60+
**Osszes migracio:** 25 (001-025, mind fizikailag letezik az `alembic/versions/`-ben)
  - 001-013: Framework mag (Phase 1-7)
  - 014-024: Service generalizacio (Fazis 0-5)
  - 025: Security fix (password_hash column)

---

## 23. Karbantartasi Javaslatok

### Table Partitioning

A `audit_log` es `cost_records` tablak napi/heti rekordszama miatt havonta particionald (monthly range partitioning):

```sql
-- Pelda: audit_log particionalsas havi bontasban
CREATE TABLE audit_log (
    ...
) PARTITION BY RANGE (timestamp);

CREATE TABLE audit_log_2026_01 PARTITION OF audit_log
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
CREATE TABLE audit_log_2026_02 PARTITION OF audit_log
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
-- stb. automatizalva pg_partman extension-nel
```

Ugyanigy a `cost_records` tabla `recorded_at` oszlop alapjan.

### Autovacuum Tuning

Magas irasi terhelesu tablaknal (workflow_runs, step_runs, audit_log, cost_records, test_results) agresszivebb autovacuum beallitas javasolt:

```sql
ALTER TABLE workflow_runs SET (
    autovacuum_vacuum_scale_factor = 0.05,
    autovacuum_analyze_scale_factor = 0.02
);
ALTER TABLE audit_log SET (
    autovacuum_vacuum_scale_factor = 0.05,
    autovacuum_analyze_scale_factor = 0.02
);
```

### pg_stat_statements Extension

Query performance monitoring-hoz a `pg_stat_statements` extension hasznalata javasolt:

```sql
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Top 10 leglassabb query lekerese
SELECT query, calls, mean_exec_time, total_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

### Partial Index Pelda

Aktiv workflow_runs-ra partial index a gyakori statusszuro lekerdezesekhez:

```sql
CREATE INDEX idx_wr_active ON workflow_runs(status, created_at DESC)
    WHERE status IN ('pending', 'running', 'paused');
```
