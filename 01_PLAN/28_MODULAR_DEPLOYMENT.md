# AIFlow - Skill Instance / Multi-Customer / Modular Deployment

**Cel:** Egyetlen framework es skill codebase tobb ugyfelnel, tobb konfiguracioval hasznalhato legyen.
**Alapelv:** Skill = Template (kod), Instance = Futo peldany (konfig + adat).
**Stack:** Python 3.12+, FastAPI, PostgreSQL+pgvector, Redis, arq, Docker Compose (staging/prod), K8s kesobb.
**Jelenlegi fazis:** Docker Compose alapu staging/prod. K8s kesobb, amikor cluster elerheto.

### Ugyfel Attekintes

| Ugyfel | Kod | Skills | Megjegyzes |
|--------|-----|--------|------------|
| Allianz Hungaria | AZHU | aszf_rag_chat (RAG Chat), email_intent_processor (Intent), qbpp_test_automation (AutoTest) | Fo ugyfel, enterprise tier |
| NPRA | NPRA | aszf_rag_chat (RAG Chat), qbpp_test_automation (AutoTest) | Business tier |
| BestIxCom Kft | BESTIX | process_documentation (Diagram Gen), cubix_course_capture (RPA+Transcript), cfpb_complaint_router (ML), email_intent_processor, aszf_rag_chat - minden skill sajat hasznalatra | Belso hasznalat, teszteles, demo |

---

## 1. Alapelv: Skill = Template, Instance = Futo Peldany

### 1.1 Harom Retegu Modell

```
+-----------------------+     +-------------------------+     +------------------------+
|   SKILL TEMPLATE      |     |   INSTANCE CONFIG       |     |   INSTANCE RUNTIME     |
|   (Kod - Git)         |     |   (YAML - Git)          |     |   (DB + Langfuse)      |
+-----------------------+     +-------------------------+     +------------------------+
| - Python agents       |     | - instance_name         |     | - skill_instances tabla |
| - workflow DAG        | --> | - data_sources          | --> | - workflow_runs.inst_id |
| - base prompts        |     | - prompt overrides      |     | - Langfuse traces      |
| - tests               |     | - model selection       |     | - cost tracking        |
| - skill.yaml manifest |     | - SLA targets           |     | - runtime metrics      |
+-----------------------+     +-------------------------+     +------------------------+
```

**Docker Analogia:**
- Skill Template = **Docker Image** (egyszer megirva, tobb helyen futtatva)
- Instance Config = **docker run flags** (port, volume, env vars)
- Instance Runtime = **Running Container** (egyedi state, logok, metriak)

### 1.2 Peldak: Tobb Instance Egyetlen Template-bol

```
Skill Template: aszf_rag_chat
  |
  +-- Instance: azhu_aszf_rag          (AZHU ASZF dokumentumok, gpt-4o, SLA: 5s)
  +-- Instance: azhu_internal_rag      (AZHU belso szabalyzatok, gpt-4o-mini, SLA: 3s)
  +-- Instance: npra_faq_rag           (NPRA kurzus FAQ, gpt-4o-mini, SLA: 2s)
  +-- Instance: bestix_internal_rag    (BESTIX belso dokumentumok, gpt-4o, SLA: 3s)

Skill Template: email_intent_processor
  |
  +-- Instance: azhu_claims_email      (kar-bejelentes@allianz.hu, 12 intent)
  +-- Instance: azhu_info_email        (info@allianz.hu, 8 intent)
  +-- Instance: bestix_support_email   (support@bestix.hu, 6 intent)

Skill Template: cubix_course_capture
  |
  +-- Instance: npra_udemy_capture     (Udemy platform, video + SRT)
  +-- Instance: npra_coursera_capture  (Coursera platform, video + transcript)
  +-- Instance: bestix_cubix_capture   (Cubix AI/ML kurzusok, belso hasznalat)

Skill Template: qbpp_test_automation
  |
  +-- Instance: azhu_portal_test       (portal.allianz.hu, E2E tesztek)
  +-- Instance: npra_lms_test          (lms.npra.com, regression tesztek)

Skill Template: process_documentation
  |
  +-- Instance: bestix_process_docs    (BESTIX belso folyamatok, framework validacio)

Skill Template: cfpb_complaint_router
  |
  +-- Instance: bestix_cfpb_demo       (BESTIX ML demo, belso teszteles)
```

**Fontos:** A skill template **NEM** tartalmaz ugyfel-specifikus adatot. Az instance config tartalmazza
az osszes ugyfel-specifikus beallitast (data source, prompt override, model, budget).

---

## 2. Instance Konfiguracio Formatum

### 2.1 YAML Schema

```yaml
# Instance Config Schema
# Helye: deployments/{customer}/instances/{instance_name}.yaml

instance_name: string             # Unique ID (kebab-case, pl. "azhu-aszf-rag")
display_name: string              # UI-ban megjeleno nev (pl. "AZHU ASZF Chat")
skill_template: string            # Skill neve (skill.yaml name mezovel egyezik)
version: string                   # Skill template SemVer (pl. "1.2.0")
customer: string                  # Ugyfel azonosito (pl. "azhu", "npra")
enabled: bool                     # true/false - instance be/ki kapcsolas

# --- Adat forrasok (RAG skill-eknel) ---
data_sources:
  collections:                    # Melyik vector collection-okbol keres
    - name: string                # Collection nev (pl. "azhu-aszf-2024")
      priority: int               # Keresesi prioritas (1 = legmagasabb)
  document_filters:               # Automatikus szures minden keresesnel
    department: string | null
    document_type: string | null
    language: string              # Default: "hu"
  embedding_model: string         # Default: "text-embedding-3-small"

# --- Prompt konfiguracio ---
prompts:
  namespace: string               # Langfuse prompt prefix (pl. "azhu/aszf-rag")
  label: string                   # Langfuse label (dev/staging/prod)
  overrides:                      # Instance-specifikus prompt feluliras
    - prompt_name: string         # Base prompt neve (pl. "classifier")
      template: string | null     # Teljes feluliras (ritka)
      variables:                  # Template valtozo feluliras (gyakori)
        company_name: string
        tone: string
        max_response_length: int

# --- Model konfiguracio ---
models:
  default: string                 # Alap LLM (pl. "gpt-4o")
  fallback: string                # Fallback LLM (pl. "gpt-4o-mini")
  per_agent:                      # Agent-szintu model override
    classifier: string | null
    extractor: string | null

# --- Budget es SLA ---
budget:
  monthly_usd: float              # Havi koltseg limit USD-ben
  per_run_usd: float              # Egyetlen futtatas max koltseg
  alert_threshold: float          # Figyelmeztetes %-ban (pl. 0.8 = 80%)

sla:
  target_seconds: int             # Valaszido cel masodpercben
  p95_target_seconds: int         # p95 cel
  availability: float             # Elerhettoseg cel (pl. 0.995 = 99.5%)

# --- Intent konfiguracio (intent skill-eknel) ---
intents:                          # Csak email_intent_processor tipusu skill-eknel
  - name: string                  # Intent neve (pl. "claim_report")
    description: string           # Leiras (classifier szamara)
    handler: string               # Handler agent/workflow (pl. "extract_claim")
    priority: int                 # Routing prioritas
    auto_respond: bool            # Automatikus valasz kuldes

# --- Routing ---
routing:
  input_channel: string           # Honnan jon az input (api/email/webhook/queue)
  output_channel: string          # Hova megy az output (api/email/webhook/db)
  webhook_url: string | null      # Webhook callback URL
  queue_name: string | null       # Dedikalt queue nev (null = shared queue)
```

### 2.2 Pelda: RAG Chat - Ket Kulonbozo Instance

**Instance 1: AZHU ASZF RAG Chat**
```yaml
# deployments/azhu/instances/azhu-aszf-rag.yaml
instance_name: azhu-aszf-rag
display_name: "AZHU ASZF Chatbot"
skill_template: aszf_rag_chat
version: "1.2.0"
customer: azhu
enabled: true

data_sources:
  collections:
    - name: azhu-aszf-2024
      priority: 1
    - name: azhu-aszf-2023
      priority: 2
  document_filters:
    document_type: aszf
    language: hu
  embedding_model: text-embedding-3-small

prompts:
  namespace: azhu/aszf-rag
  label: prod
  overrides:
    - prompt_name: system-prompt
      variables:
        company_name: "Allianz Hungaria Zrt."
        tone: "formal"
        max_response_length: 500
    - prompt_name: classifier
      variables:
        allowed_topics: "biztositas, karbejelentes, szerzodes, dijfizetes"

models:
  default: gpt-4o
  fallback: gpt-4o-mini
  per_agent:
    classifier: gpt-4o-mini

budget:
  monthly_usd: 500.00
  per_run_usd: 0.15
  alert_threshold: 0.8

sla:
  target_seconds: 5
  p95_target_seconds: 8
  availability: 0.995

routing:
  input_channel: api
  output_channel: api
  webhook_url: null
  queue_name: azhu-rag-queue
```

**Instance 2: AZHU Belso Szabalyzatok RAG**
```yaml
# deployments/azhu/instances/azhu-internal-rag.yaml
instance_name: azhu-internal-rag
display_name: "AZHU Belso Szabalyzat Kereses"
skill_template: aszf_rag_chat
version: "1.2.0"
customer: azhu
enabled: true

data_sources:
  collections:
    - name: azhu-hr-szabalyzat
      priority: 1
    - name: azhu-it-security-policy
      priority: 2
    - name: azhu-compliance-docs
      priority: 3
  document_filters:
    document_type: szabalyzat
    language: hu
  embedding_model: text-embedding-3-small

prompts:
  namespace: azhu/internal-rag
  label: prod
  overrides:
    - prompt_name: system-prompt
      variables:
        company_name: "Allianz Hungaria Zrt."
        tone: "professional"
        max_response_length: 800
    - prompt_name: classifier
      variables:
        allowed_topics: "hr, it-security, compliance, szabadsag, belepes"

models:
  default: gpt-4o-mini
  fallback: gpt-4o-mini
  per_agent:
    classifier: gpt-4o-mini

budget:
  monthly_usd: 200.00
  per_run_usd: 0.05
  alert_threshold: 0.8

sla:
  target_seconds: 3
  p95_target_seconds: 5
  availability: 0.99

routing:
  input_channel: api
  output_channel: api
  webhook_url: null
  queue_name: null
```

### 2.3 Pelda: Email Intent - Ket Kulonbozo Instance

```yaml
# deployments/azhu/instances/azhu-claims-email.yaml
instance_name: azhu-claims-email
display_name: "AZHU Karbejelentes Email Feldolgozo"
skill_template: email_intent_processor
version: "1.0.0"
customer: azhu
enabled: true

data_sources:
  collections: []
  document_filters: {}
  embedding_model: null

prompts:
  namespace: azhu/claims-email
  label: prod
  overrides:
    - prompt_name: system-prompt
      variables:
        company_name: "Allianz Hungaria Zrt."
        department: "Karbejelentes"

models:
  default: gpt-4o
  fallback: gpt-4o-mini

budget:
  monthly_usd: 1000.00
  per_run_usd: 0.25
  alert_threshold: 0.75

sla:
  target_seconds: 30
  p95_target_seconds: 60
  availability: 0.999

intents:
  - name: claim_report
    description: "Uj karbejelentes (baleset, lopas, termeszeti kar)"
    handler: extract_claim
    priority: 1
    auto_respond: false
  - name: claim_status
    description: "Meglevo kar statusz lekerdezes"
    handler: lookup_claim_status
    priority: 2
    auto_respond: true
  - name: policy_question
    description: "Biztositasi kotessel kapcsolatos kerdes"
    handler: rag_answer
    priority: 3
    auto_respond: true
  - name: complaint
    description: "Ugyfel panasz"
    handler: escalate_to_human
    priority: 1
    auto_respond: false

routing:
  input_channel: email
  output_channel: email
  webhook_url: https://crm.allianz.hu/api/webhook/email-processed
  queue_name: azhu-claims-email-queue
```

### 2.4 Pelda: Auto Test - Kulonbozo Test Targetek

```yaml
# deployments/azhu/instances/azhu-portal-test.yaml
instance_name: azhu-portal-test
display_name: "AZHU Portal E2E Tesztek"
skill_template: qbpp_test_automation
version: "1.0.0"
customer: azhu
enabled: true

data_sources:
  collections: []
  document_filters: {}
  embedding_model: null

prompts:
  namespace: azhu/portal-test
  label: prod
  overrides:
    - prompt_name: test-generator
      variables:
        target_app: "Allianz Online Portal"
        base_url: "https://portal.allianz.hu"
        auth_method: "oauth2"
        test_language: "hu"

models:
  default: gpt-4o
  fallback: gpt-4o-mini

budget:
  monthly_usd: 300.00
  per_run_usd: 1.00
  alert_threshold: 0.9

sla:
  target_seconds: 300
  p95_target_seconds: 600
  availability: 0.95

routing:
  input_channel: queue
  output_channel: webhook
  webhook_url: https://ci.allianz.hu/api/test-results
  queue_name: azhu-test-queue
```

### 2.5 Pelda: RPA - Kulonbozo Weboldalak

```yaml
# deployments/npra/instances/npra-udemy-capture.yaml
instance_name: npra-udemy-capture
display_name: "NPRA Udemy Kurzus Rogzites"
skill_template: cubix_course_capture
version: "1.0.0"
customer: npra
enabled: true

data_sources:
  collections: []
  document_filters: {}
  embedding_model: null

prompts:
  namespace: npra/udemy-capture
  label: prod
  overrides:
    - prompt_name: transcript-structurer
      variables:
        platform: "Udemy"
        output_format: "markdown"
        language: "en"

models:
  default: gpt-4o-mini
  fallback: gpt-4o-mini
  per_agent:
    transcript_structurer: gpt-4o

budget:
  monthly_usd: 150.00
  per_run_usd: 2.00
  alert_threshold: 0.8

sla:
  target_seconds: 3600
  p95_target_seconds: 7200
  availability: 0.90

routing:
  input_channel: api
  output_channel: webhook
  webhook_url: https://lms.npra.com/api/capture-complete
  queue_name: npra-rpa-queue
```

---

## 3. DB Schema: skill_instances Tabla

### 3.1 CREATE TABLE

```sql
-- Migration: 012_add_skill_instances.py
-- A skill_instances tabla tartja nyilvan az osszes futo instance konfigjat.
-- Egy skill (template) tobb instance-kent futhat kulonbozo ugyfeleknel.

CREATE TABLE skill_instances (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Azonositas
    instance_name VARCHAR(255) UNIQUE NOT NULL,      -- "azhu-aszf-rag" (kebab-case, globalis unique)
    display_name VARCHAR(255) NOT NULL,              -- "AZHU ASZF Chatbot"
    customer VARCHAR(100) NOT NULL,                  -- "azhu"

    -- Skill template hivatkozas
    skill_name VARCHAR(255) NOT NULL,                -- FK a skills.name-re (template)
    skill_version VARCHAR(50) NOT NULL,              -- Melyik template verzio (pl. "1.2.0")

    -- Teljes YAML konfig (a fenti schema szerint)
    config JSONB NOT NULL,                           -- Az egesz instance YAML -> JSONB

    -- Prompt namespace (Langfuse izolacio)
    prompt_namespace VARCHAR(255) NOT NULL,           -- "azhu/aszf-rag"
    prompt_label VARCHAR(50) DEFAULT 'prod',          -- dev/staging/prod

    -- Model konfiguracio (denormalizalt a gyors lekerdeshez)
    default_model VARCHAR(100) NOT NULL,              -- "gpt-4o"
    fallback_model VARCHAR(100),                      -- "gpt-4o-mini"

    -- Budget (denormalizalt)
    budget_monthly_usd DECIMAL(10,2),                 -- 500.00
    budget_used_usd DECIMAL(10,2) DEFAULT 0,          -- Aktualis honap felhasznalt
    budget_per_run_usd DECIMAL(10,4),                 -- 0.15
    budget_reset_day INT DEFAULT 1,                   -- Honap melyik napjan nullazodik

    -- SLA (denormalizalt)
    sla_target_seconds INT,                           -- 5
    sla_p95_target_seconds INT,                       -- 8

    -- Routing
    input_channel VARCHAR(50) DEFAULT 'api',          -- api/email/webhook/queue
    output_channel VARCHAR(50) DEFAULT 'api',
    queue_name VARCHAR(255),                          -- Dedikalt queue nev (null = shared)

    -- Allapot
    enabled BOOLEAN DEFAULT TRUE,
    status VARCHAR(20) DEFAULT 'active',              -- active/paused/deprecated/error
    last_run_at TIMESTAMPTZ,
    total_runs INT DEFAULT 0,
    total_cost_usd DECIMAL(10,4) DEFAULT 0,

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(255),
    updated_by VARCHAR(255),

    -- Constraints
    CONSTRAINT fk_si_skill_name FOREIGN KEY (skill_name) REFERENCES skills(name),
    CONSTRAINT chk_si_status CHECK (status IN ('active', 'paused', 'deprecated', 'error')),
    CONSTRAINT chk_si_input_channel CHECK (input_channel IN ('api', 'email', 'webhook', 'queue')),
    CONSTRAINT chk_si_output_channel CHECK (output_channel IN ('api', 'email', 'webhook', 'db'))
);
```

### 3.2 Indexek

```sql
-- Keresesi indexek
CREATE INDEX idx_si_customer ON skill_instances(customer);
CREATE INDEX idx_si_skill_name ON skill_instances(skill_name);
CREATE INDEX idx_si_enabled ON skill_instances(enabled) WHERE enabled = TRUE;
CREATE INDEX idx_si_status ON skill_instances(status);
CREATE INDEX idx_si_customer_skill ON skill_instances(customer, skill_name);
CREATE INDEX idx_si_prompt_namespace ON skill_instances(prompt_namespace);

-- JSONB config index (ha config-ban keresunk)
CREATE INDEX idx_si_config_gin ON skill_instances USING GIN (config jsonb_path_ops);
```

### 3.3 workflow_runs Bovites: instance_id FK

```sql
-- Bovites: workflow_runs tabla kap egy instance_id FK-t
-- Igy minden workflow run tudja, melyik instance-hoz tartozik

ALTER TABLE workflow_runs
    ADD COLUMN instance_id UUID REFERENCES skill_instances(id) ON DELETE SET NULL;

CREATE INDEX idx_wr_instance_id ON workflow_runs(instance_id);

-- View: instance-szintu statisztikak
CREATE OR REPLACE VIEW v_instance_stats AS
SELECT
    si.id AS instance_id,
    si.instance_name,
    si.customer,
    si.skill_name,
    si.display_name,
    si.enabled,
    si.status,
    COUNT(wr.id) AS total_runs,
    COUNT(wr.id) FILTER (WHERE wr.status = 'completed') AS completed_runs,
    COUNT(wr.id) FILTER (WHERE wr.status = 'failed') AS failed_runs,
    AVG(wr.total_duration_ms) FILTER (WHERE wr.status = 'completed') AS avg_duration_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY wr.total_duration_ms)
        FILTER (WHERE wr.status = 'completed') AS p95_duration_ms,
    SUM(wr.total_cost_usd) AS total_cost_usd,
    MAX(wr.created_at) AS last_run_at,
    AVG(CASE WHEN wr.sla_met THEN 1.0 ELSE 0.0 END) AS sla_met_ratio
FROM skill_instances si
LEFT JOIN workflow_runs wr ON wr.instance_id = si.id
GROUP BY si.id, si.instance_name, si.customer, si.skill_name,
         si.display_name, si.enabled, si.status;
```

### 3.4 Migracios Script

```python
# alembic/versions/012_add_skill_instances.py
"""Add skill_instances table and workflow_runs.instance_id FK.

Revision ID: 012
Revises: 011
Create Date: 2026-03-28
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "012"
down_revision = "011"

def upgrade() -> None:
    # 1. Uj tabla: skill_instances
    op.create_table(
        "skill_instances",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("instance_name", sa.String(255), unique=True, nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("customer", sa.String(100), nullable=False),
        sa.Column("skill_name", sa.String(255), nullable=False),
        sa.Column("skill_version", sa.String(50), nullable=False),
        sa.Column("config", postgresql.JSONB, nullable=False),
        sa.Column("prompt_namespace", sa.String(255), nullable=False),
        sa.Column("prompt_label", sa.String(50), server_default="prod"),
        sa.Column("default_model", sa.String(100), nullable=False),
        sa.Column("fallback_model", sa.String(100)),
        sa.Column("budget_monthly_usd", sa.Numeric(10, 2)),
        sa.Column("budget_used_usd", sa.Numeric(10, 2), server_default="0"),
        sa.Column("budget_per_run_usd", sa.Numeric(10, 4)),
        sa.Column("budget_reset_day", sa.Integer, server_default="1"),
        sa.Column("sla_target_seconds", sa.Integer),
        sa.Column("sla_p95_target_seconds", sa.Integer),
        sa.Column("input_channel", sa.String(50), server_default="api"),
        sa.Column("output_channel", sa.String(50), server_default="api"),
        sa.Column("queue_name", sa.String(255)),
        sa.Column("enabled", sa.Boolean, server_default="true"),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("last_run_at", sa.DateTime(timezone=True)),
        sa.Column("total_runs", sa.Integer, server_default="0"),
        sa.Column("total_cost_usd", sa.Numeric(10, 4), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("created_by", sa.String(255)),
        sa.Column("updated_by", sa.String(255)),
        sa.ForeignKeyConstraint(["skill_name"], ["skills.name"]),
        sa.CheckConstraint("status IN ('active','paused','deprecated','error')", name="chk_si_status"),
        sa.CheckConstraint("input_channel IN ('api','email','webhook','queue')", name="chk_si_input"),
        sa.CheckConstraint("output_channel IN ('api','email','webhook','db')", name="chk_si_output"),
    )

    # 2. Indexek
    op.create_index("idx_si_customer", "skill_instances", ["customer"])
    op.create_index("idx_si_skill_name", "skill_instances", ["skill_name"])
    op.create_index("idx_si_enabled", "skill_instances", ["enabled"],
                    postgresql_where=sa.text("enabled = TRUE"))
    op.create_index("idx_si_status", "skill_instances", ["status"])
    op.create_index("idx_si_customer_skill", "skill_instances", ["customer", "skill_name"])
    op.create_index("idx_si_prompt_namespace", "skill_instances", ["prompt_namespace"])
    op.create_index("idx_si_config_gin", "skill_instances", ["config"],
                    postgresql_using="gin", postgresql_ops={"config": "jsonb_path_ops"})

    # 3. workflow_runs bovites
    op.add_column("workflow_runs", sa.Column("instance_id", postgresql.UUID(as_uuid=True)))
    op.create_foreign_key("fk_wr_instance_id", "workflow_runs", "skill_instances",
                          ["instance_id"], ["id"], ondelete="SET NULL")
    op.create_index("idx_wr_instance_id", "workflow_runs", ["instance_id"])


def downgrade() -> None:
    op.drop_index("idx_wr_instance_id", "workflow_runs")
    op.drop_constraint("fk_wr_instance_id", "workflow_runs", type_="foreignkey")
    op.drop_column("workflow_runs", "instance_id")
    op.drop_table("skill_instances")
```

---

## 4. Ugyfel Deployment Profilok

### 4.1 deployment.yaml Schema

```yaml
# deployments/{customer}/deployment.yaml
# Egyetlen file leirja az ugyfel teljes deployment profiljat.

customer:
  name: string                    # Ugyfel azonosito (kebab-case)
  display_name: string            # Teljes nev
  contact_email: string
  tier: string                    # free/starter/business/enterprise

framework:
  version: string                 # Keretrendszer verzio (pl. "1.2.0")
  image_variant: string           # base | base-rpa (l. 5. szekció)

skill_templates:                  # Melyik skill template-eket tartalmazza az ugyfel image
  - name: string
    version: string

instances:                        # Instance config file-ok referenciaja
  - file: string                  # Relative path: instances/{name}.yaml

infrastructure:
  docker_compose_project: string   # Docker Compose projekt nev (pl. "aiflow-azhu")
  k8s_namespace: string | null    # K8s namespace nev (Phase 2 - K8s cluster elerhetosegekor)
  database:
    host: string
    name: string                  # Dedikalt DB nev (pl. "aiflow_azhu")
    schema: string | null         # Vagy dedikalt schema (pl. "azhu")
  redis:
    db: int                       # Redis DB index (0-15)
    prefix: string                # Key prefix (pl. "azhu:")
  langfuse:
    project: string               # Langfuse projekt nev
    prompt_label_prefix: string   # Prompt label prefix (pl. "azhu-prod")
  resources:
    api_replicas: int
    worker_replicas: int
    rpa_worker_replicas: int      # 0 ha nincs RPA skill
    memory_limit: string          # pl. "2Gi"
    cpu_limit: string             # pl. "1000m"
```

### 4.2 Konyvtar Struktura

```
deployments/
|
|-- azhu/
|   |-- deployment.yaml              # Ugyfel profil (skills, infra, general config)
|   |-- docker-compose.yml           # Per-customer Docker Compose (staging/prod)
|   |-- instances/
|   |   |-- azhu-aszf-rag.yaml
|   |   |-- azhu-internal-rag.yaml
|   |   |-- azhu-claims-email.yaml
|   |   |-- azhu-portal-test.yaml
|   |-- k8s/                         # Phase 2 - K8s cluster elerhetosegekor
|   |   |-- namespace.yaml
|   |   |-- configmap.yaml
|   |   |-- secrets.yaml             # Sealed Secrets / External Secrets ref
|   |   |-- api-deployment.yaml
|   |   |-- worker-deployment.yaml
|   |   |-- ingress.yaml
|   |   |-- hpa.yaml                 # Horizontal Pod Autoscaler
|
|-- npra/
|   |-- deployment.yaml
|   |-- docker-compose.yml           # Per-customer Docker Compose (staging/prod)
|   |-- instances/
|   |   |-- npra-udemy-capture.yaml
|   |   |-- npra-coursera-capture.yaml
|   |   |-- npra-faq-rag.yaml
|   |-- k8s/                         # Phase 2 - K8s cluster elerhetosegekor
|       |-- namespace.yaml
|       |-- configmap.yaml
|       |-- secrets.yaml
|       |-- api-deployment.yaml
|       |-- worker-deployment.yaml
|       |-- rpa-worker-deployment.yaml  # NPRA-nak kell RPA worker
|       |-- ingress.yaml
|
|-- bestix/
|   |-- deployment.yaml
|   |-- docker-compose.yml           # Per-customer Docker Compose (staging/prod)
|   |-- instances/
|   |   |-- bestix-internal-rag.yaml
|   |   |-- bestix-process-docs.yaml
|   |   |-- bestix-cubix-capture.yaml
|   |   |-- bestix-cfpb-demo.yaml
|   |   |-- bestix-support-email.yaml
|   |-- k8s/                         # Phase 2 - K8s cluster elerhetosegekor
|       |-- namespace.yaml
|       |-- configmap.yaml
|       |-- secrets.yaml
|       |-- api-deployment.yaml
|       |-- worker-deployment.yaml
|       |-- rpa-worker-deployment.yaml  # BESTIX-nek kell RPA worker (cubix_course_capture)
|       |-- ingress.yaml
```

### 4.3 Pelda: AZHU Deployment (4 Instance)

```yaml
# deployments/azhu/deployment.yaml
customer:
  name: azhu
  display_name: "Allianz Hungaria Zrt."
  contact_email: it-ops@allianz.hu
  tier: enterprise

framework:
  version: "1.2.0"
  image_variant: base            # Nincs RPA skill, eleg a base image

skill_templates:
  - name: aszf_rag_chat
    version: "1.2.0"
  - name: email_intent_processor
    version: "1.0.0"
  - name: qbpp_test_automation
    version: "1.0.0"

instances:
  - file: instances/azhu-aszf-rag.yaml
  - file: instances/azhu-internal-rag.yaml
  - file: instances/azhu-claims-email.yaml
  - file: instances/azhu-portal-test.yaml

infrastructure:
  docker_compose_project: aiflow-azhu
  k8s_namespace: aiflow-azhu     # Phase 2 - K8s cluster elerhetosegekor
  database:
    host: pg-cluster.internal
    name: aiflow_azhu
    schema: null
  redis:
    db: 1
    prefix: "azhu:"
  langfuse:
    project: azhu-aiflow
    prompt_label_prefix: "azhu"
  resources:
    api_replicas: 2
    worker_replicas: 3
    rpa_worker_replicas: 0
    memory_limit: "2Gi"
    cpu_limit: "1000m"
```

### 4.4 Pelda: NPRA Deployment (3 Instance)

```yaml
# deployments/npra/deployment.yaml
customer:
  name: npra
  display_name: "NPRA"
  contact_email: dev@npra.com
  tier: business

framework:
  version: "1.2.0"
  image_variant: base-rpa        # RPA skill van, kell Playwright + ffmpeg

skill_templates:
  - name: cubix_course_capture
    version: "1.0.0"
  - name: aszf_rag_chat
    version: "1.2.0"

instances:
  - file: instances/npra-udemy-capture.yaml
  - file: instances/npra-coursera-capture.yaml
  - file: instances/npra-faq-rag.yaml

infrastructure:
  docker_compose_project: aiflow-npra
  k8s_namespace: aiflow-npra     # Phase 2 - K8s cluster elerhetosegekor
  database:
    host: pg-cluster.internal
    name: aiflow_npra
    schema: null
  redis:
    db: 2
    prefix: "npra:"
  langfuse:
    project: npra-aiflow
    prompt_label_prefix: "npra"
  resources:
    api_replicas: 1
    worker_replicas: 2
    rpa_worker_replicas: 2       # RPA workerek Playwright-tel
    memory_limit: "4Gi"          # Nagyobb, mert video feldolgozas
    cpu_limit: "2000m"
```

### 4.5 Pelda: BESTIX Deployment (5 Instance - Minden Skill)

```yaml
# deployments/bestix/deployment.yaml
customer:
  name: bestix
  display_name: "BestIxCom Kft"
  contact_email: dev@bestix.hu
  tier: enterprise

framework:
  version: "1.2.0"
  image_variant: base-rpa        # RPA skill van (cubix_course_capture), kell Playwright + ffmpeg

skill_templates:                  # MINDEN skill - belso hasznalat, teszteles, demo
  - name: process_documentation
    version: "2.0.0"
  - name: aszf_rag_chat
    version: "1.2.0"
  - name: cubix_course_capture
    version: "1.0.0"
  - name: cfpb_complaint_router
    version: "1.0.0"
  - name: email_intent_processor
    version: "1.0.0"
  - name: qbpp_test_automation
    version: "1.0.0"

instances:
  - file: instances/bestix-internal-rag.yaml
  - file: instances/bestix-process-docs.yaml
  - file: instances/bestix-cubix-capture.yaml
  - file: instances/bestix-cfpb-demo.yaml
  - file: instances/bestix-support-email.yaml

infrastructure:
  docker_compose_project: aiflow-bestix
  k8s_namespace: aiflow-bestix   # Phase 2 - K8s cluster elerhetosegekor
  database:
    host: pg-cluster.internal
    name: aiflow_bestix
    schema: null
  redis:
    db: 3
    prefix: "bestix:"
  langfuse:
    project: bestix-aiflow
    prompt_label_prefix: "bestix"
  resources:
    api_replicas: 1
    worker_replicas: 2
    rpa_worker_replicas: 1       # RPA worker cubix_course_capture-hoz
    memory_limit: "4Gi"
    cpu_limit: "2000m"
```

---

## 5. Docker Image Strategia

### 5.1 Image Hierarchia

```
ghcr.io/bestixcom/aiflow-base:v1.2.0          # (1) Framework only
    |
    +-- ghcr.io/bestixcom/aiflow-base-rpa:v1.2.0   # (2) Framework + Playwright + ffmpeg
    |
    +-- ghcr.io/bestixcom/aiflow-azhu:v1.2.0        # (3) Customer: base + 3 skill
    +-- ghcr.io/bestixcom/aiflow-npra:v1.2.0         # (3) Customer: base-rpa + 2 skill
    +-- ghcr.io/bestixcom/aiflow-bestix:v1.2.0       # (3) Customer: base-rpa + 6 skill (minden)
```

### 5.2 Base Image (Framework Only)

```dockerfile
# Dockerfile.base
FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv pip install --system --no-cache -r pyproject.toml
COPY src/aiflow/ src/aiflow/

FROM python:3.12-slim AS runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl tini \
    && rm -rf /var/lib/apt/lists/*
RUN groupadd -r aiflow && useradd -r -g aiflow -d /app aiflow
WORKDIR /app

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /build/src/aiflow/ src/aiflow/
COPY alembic/ alembic/
COPY alembic.ini .

RUN chown -R aiflow:aiflow /app
USER aiflow

# Nincs skill ebben az image-ben - csak a keretrendszer
LABEL org.opencontainers.image.title="AIFlow Base"
LABEL org.opencontainers.image.version="${FRAMEWORK_VERSION}"
```

### 5.3 Base+RPA Image (Framework + Playwright + ffmpeg)

```dockerfile
# Dockerfile.base-rpa
FROM ghcr.io/bestixcom/aiflow-base:${FRAMEWORK_VERSION} AS base

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    xvfb libnss3 libatk-bridge2.0-0 libdrm2 libxkbcommon0 libgbm1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*
RUN pip install playwright && playwright install chromium --with-deps
USER aiflow

LABEL org.opencontainers.image.title="AIFlow Base + RPA"
```

### 5.4 Customer Image (Base + Selected Skills)

```dockerfile
# Dockerfile.customer (generalt - l. select_skills.py)
ARG BASE_IMAGE=ghcr.io/bestixcom/aiflow-base:v1.2.0
FROM ${BASE_IMAGE}

# Csak a deployment.yaml-ban meghatarozott skill-ek masolasa
COPY skills/aszf_rag_chat/ /app/skills/aszf_rag_chat/
COPY skills/email_intent_processor/ /app/skills/email_intent_processor/
COPY skills/qbpp_test_automation/ /app/skills/qbpp_test_automation/

# Instance konfigok masolasa
COPY deployments/azhu/instances/ /app/config/instances/
COPY deployments/azhu/deployment.yaml /app/config/deployment.yaml

LABEL org.opencontainers.image.title="AIFlow - AZHU"
```

### 5.5 scripts/select_skills.py

```python
#!/usr/bin/env python3
"""Build-time skill selection: deployment.yaml alapjan generalja a customer Dockerfile-t.

Hasznalat:
    python scripts/select_skills.py deployments/azhu/deployment.yaml
    -> Kimenet: deployments/azhu/Dockerfile (generalt)

Ez biztositja, hogy az ugyfel image CSAK a szukseges skill-eket tartalmazza,
csokkentve az image meretet es a tamadasi feluletet.
"""

import sys
from pathlib import Path
import yaml

def generate_customer_dockerfile(deployment_path: str) -> str:
    deployment = yaml.safe_load(Path(deployment_path).read_text())

    customer = deployment["customer"]["name"]
    framework_version = deployment["framework"]["version"]
    image_variant = deployment["framework"]["image_variant"]

    # Base image valasztas
    if image_variant == "base-rpa":
        base_image = f"ghcr.io/bestixcom/aiflow-base-rpa:v{framework_version}"
    else:
        base_image = f"ghcr.io/bestixcom/aiflow-base:v{framework_version}"

    # Skill COPY utasitasok generalasa
    skill_copies = []
    for skill in deployment["skill_templates"]:
        name = skill["name"]
        skill_copies.append(f"COPY skills/{name}/ /app/skills/{name}/")

    # Instance konfigok
    instance_copies = [
        f"COPY deployments/{customer}/instances/ /app/config/instances/",
        f"COPY deployments/{customer}/deployment.yaml /app/config/deployment.yaml",
    ]

    # Dockerfile generalas
    lines = [
        f"# AUTO-GENERATED by select_skills.py - DO NOT EDIT",
        f"# Customer: {customer} | Framework: v{framework_version}",
        f"ARG BASE_IMAGE={base_image}",
        f"FROM ${{BASE_IMAGE}}",
        "",
        "# Selected skills",
        *skill_copies,
        "",
        "# Instance configs",
        *instance_copies,
        "",
        f'LABEL org.opencontainers.image.title="AIFlow - {customer}"',
    ]

    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/select_skills.py deployments/<customer>/deployment.yaml")
        sys.exit(1)

    deployment_path = sys.argv[1]
    dockerfile_content = generate_customer_dockerfile(deployment_path)

    output_path = Path(deployment_path).parent / "Dockerfile"
    output_path.write_text(dockerfile_content)
    print(f"Generated: {output_path}")
```

---

## 6. Git Branch Strategia (Bovitett)

### 6.1 Uj Branch Prefixek

Az alabbi uj prefixek egeszitik ki a 17_GIT_RULES.md-ben levo meglevo strategiat:

```
Meglevo prefixek (valtozatlan):
  feature/AIFLOW-{ticket}-{leiras}     # Framework fejlesztes
  skill/{skill-nev}/{leiras}           # Skill template fejlesztes
  prompt/{skill-nev}/{leiras}          # Prompt-only valtozas
  fix/{ticket-vagy-leiras}             # Bug fix
  hotfix/{leiras}                      # Production hotfix

UJ prefixek:
  instance/{customer}/{instance}/{leiras}    # Instance konfig valtozas
  |   Pelda: instance/azhu/aszf-rag/update-prompt-v3
  |   Pelda: instance/npra/udemy-capture/add-subtitle-support
  |
  deploy/{customer}/{leiras}                 # Customer deployment valtozas
      Pelda: deploy/azhu/add-portal-test-instance
      Pelda: deploy/npra/upgrade-framework-1.3
```

### 6.2 Tag Strategia

```
Framework tag:
  framework/v1.0.0
  framework/v1.1.0
  framework/v1.2.0

Skill template tag:
  skill/aszf-rag-chat/v1.0.0
  skill/aszf-rag-chat/v1.1.0
  skill/email-intent/v1.0.0

Customer deployment tag:
  deploy/azhu/v2026.03.28              # Datum-alapu (napi deploy lehetseges)
  deploy/azhu/v2026.03.28-hotfix1      # Hotfix a napi deploy-ra
  deploy/npra/v2026.04.01
  deploy/bestix/v2026.03.28            # BESTIX belso deploy
```

### 6.3 CI Pipeline D: Customer Deployment Validacio

```yaml
# .github/workflows/pipeline-d-deploy-validate.yml
name: "Pipeline D: Customer Deployment Validation"

on:
  pull_request:
    paths:
      - "deployments/**"
      - "skills/**/skill.yaml"

jobs:
  validate-deployment:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        customer: [azhu, npra, bestix]       # 3 ugyfel
    steps:
      - uses: actions/checkout@v4

      - name: Validate deployment.yaml schema
        run: |
          python scripts/validate_deployment.py \
            deployments/${{ matrix.customer }}/deployment.yaml

      - name: Validate all instance configs
        run: |
          for f in deployments/${{ matrix.customer }}/instances/*.yaml; do
            python scripts/validate_instance.py "$f"
          done

      - name: Check skill template version exists
        run: |
          python scripts/check_skill_versions.py \
            deployments/${{ matrix.customer }}/deployment.yaml

      - name: Generate customer Dockerfile (dry-run)
        run: |
          python scripts/select_skills.py \
            deployments/${{ matrix.customer }}/deployment.yaml

      - name: Build customer image (test)
        run: |
          docker build \
            -f deployments/${{ matrix.customer }}/Dockerfile \
            -t aiflow-${{ matrix.customer }}:test \
            --target runtime \
            .
```

### 6.4 Commit Konvenciok Bovites

| Tipus | Mikor | Pelda |
|-------|-------|-------|
| instance | Instance konfig valtozas | `instance(azhu/aszf-rag): update classifier prompt to v3` |
| deploy | Deployment profil valtozas | `deploy(azhu): add portal-test instance` |

Scope formatum: `{customer}/{instance}` vagy `{customer}`.

---

## 7. Kornyezeti Strategia

### 7.1 Dev (Lokalis Docker)

```
Kornyezet: Fejlesztoi gep (Docker Compose)
Skill-ek: OSSZES skill template betoltve
Instances: Test instance-ek (fixtures)
Database: Egyetlen lokalis PostgreSQL (aiflow_dev)
Redis: Egyetlen lokalis Redis (db 0)
Langfuse: Shared dev Langfuse projekt
Prompt label: "dev"
```

```yaml
# docker-compose.dev-instances.yml (kiegeszito)
services:
  instance-loader:
    build:
      context: .
      target: worker
    command: >
      python -m aiflow.cli.instance_loader
        --config deployments/_dev/deployment.yaml
        --env dev
    depends_on:
      postgres:
        condition: service_healthy
```

### 7.2 CI (Ephemeral)

```
Kornyezet: GitHub Actions runner
Skill-ek: CSAK a valtoztatas altal erintett skill template-ek
Instances: Ephemeral test instance-ek (fixture-bol generalva)
Database: Ephemeral PostgreSQL (service container)
Redis: Ephemeral Redis (service container)
Langfuse: Mock (tests/mocks/langfuse_mock.py)
Prompt label: "test"
```

CI intelligens szures: ha csak `deployments/azhu/` valtozik, csak az AZHU-specifikus
teszteket futtatja. Ha `src/aiflow/` valtozik, minden ugyfel tesztje fut.

### 7.3 Staging (Per-Customer Docker Compose)

> **Jelenlegi fazis: Docker Compose alapu staging/prod. K8s kesobb, amikor cluster elerheto.**

```
Kornyezet: Docker Compose per customer (staging)
Compose project: aiflow-{customer}-staging (pl. aiflow-azhu-staging)
Skill-ek: A customer deployment.yaml szerinti skill-ek
Instances: A customer instance YAML-ek (staging label-lel)
Database: Dedikalt DB (pl. aiflow_azhu_staging)
Redis: Dedikalt DB index (pl. db 11)
Langfuse: Ugyfel-specifikus projekt, "staging" label
Prompt label: "{customer}-staging"
```

**Docker Compose staging pelda:**
```yaml
# deployments/azhu/docker-compose.yml (staging profile)
# Hasznalat: docker compose -f deployments/azhu/docker-compose.yml --profile staging up -d

services:
  api:
    image: ghcr.io/bestixcom/aiflow-azhu:v1.2.0
    profiles: [staging, prod]
    environment:
      - AIFLOW_ENV=staging
      - AIFLOW_DB_NAME=aiflow_azhu_staging
      - AIFLOW_REDIS_DB=11
      - AIFLOW_CUSTOMER=azhu
    env_file: .env.staging
    ports:
      - "8001:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  worker:
    image: ghcr.io/bestixcom/aiflow-azhu:v1.2.0
    profiles: [staging, prod]
    command: ["python", "-m", "aiflow.execution.worker"]
    environment:
      - AIFLOW_ENV=staging
      - AIFLOW_DB_NAME=aiflow_azhu_staging
      - AIFLOW_REDIS_DB=11
      - AIFLOW_CUSTOMER=azhu
    env_file: .env.staging
    deploy:
      replicas: 2

  postgres:
    image: pgvector/pgvector:pg16
    profiles: [staging, prod]
    volumes:
      - azhu_pg_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=aiflow_azhu_staging
    healthcheck:
      test: ["CMD-SHELL", "pg_isready"]

  redis:
    image: redis:7-alpine
    profiles: [staging, prod]
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]

volumes:
  azhu_pg_data:
```

### 7.4 Prod (Per-Customer Docker Compose)

```
Kornyezet: Docker Compose per customer (production)
Compose project: aiflow-{customer} (pl. aiflow-azhu)
Skill-ek: A customer deployment.yaml szerinti skill-ek
Instances: A customer instance YAML-ek (prod label-lel)
Database: Dedikalt DB (pl. aiflow_azhu)
Redis: Dedikalt DB index (pl. db 1)
Langfuse: Ugyfel-specifikus projekt, "prod" label
Prompt label: "{customer}-prod"
```

### 7.4.1 Phase 2 - K8s cluster elerhetosegekor

> A K8s szekciok a jovobeli migraciohoz dokumentalva maradnak. Amikor K8s cluster
> elerheto lesz, a Docker Compose deployment atmigralhato K8s-re a meglevo k8s/
> konyvtarakban talalhato manifest-ek alapjan.

```
Kornyezet: Kubernetes cluster (production) - KESOBB
Namespace: aiflow-{customer} (pl. aiflow-azhu)
Skill-ek: A customer deployment.yaml szerinti skill-ek
Instances: A customer instance YAML-ek (prod label-lel)
Database: Managed DB (pl. aiflow_azhu)
Redis: Managed Redis cluster
```

### 7.5 Langfuse Izolacio

```
Langfuse projektek:
  |-- aiflow-dev                          # Fejlesztoi kozos
  |-- azhu-aiflow                         # AZHU production
  |   |-- Prompt: azhu/aszf-rag/system-prompt (label: azhu-prod)
  |   |-- Prompt: azhu/aszf-rag/classifier   (label: azhu-prod)
  |   |-- Prompt: azhu/claims-email/system-prompt (label: azhu-prod)
  |   |-- Trace-ek: instance_name tag-gel szurve
  |
  |-- npra-aiflow                         # NPRA production
  |   |-- Prompt: npra/udemy-capture/transcript-structurer (label: npra-prod)
  |   |-- Prompt: npra/faq-rag/system-prompt (label: npra-prod)
  |
  |-- bestix-aiflow                       # BESTIX production (belso hasznalat + demo)
      |-- Prompt: bestix/internal-rag/system-prompt (label: bestix-prod)
      |-- Prompt: bestix/process-docs/classifier (label: bestix-prod)
      |-- Prompt: bestix/cfpb-demo/classifier (label: bestix-prod)
      |-- Prompt: bestix/support-email/system-prompt (label: bestix-prod)
```

**ExecutionContext bovites:**
```python
class ExecutionContext(BaseModel):
    # ... meglevo mezok ...
    instance_id: str | None = None         # Skill instance ID
    instance_name: str | None = None       # "azhu-aszf-rag"
    customer: str | None = None            # "azhu"
    prompt_namespace: str | None = None    # "azhu/aszf-rag"
```

### 7.6 Database Izolacio

**Strategia: Per-Customer Database** (ajanlott production-re)

```
pg-cluster.internal
  |-- aiflow_dev           # Dev (osszes skill, osszes test instance)
  |-- aiflow_azhu          # AZHU production
  |-- aiflow_azhu_stg      # AZHU staging
  |-- aiflow_npra          # NPRA production
  |-- aiflow_npra_stg      # NPRA staging
  |-- aiflow_bestix        # BESTIX production (belso hasznalat, demo, teszteles)
  |-- aiflow_bestix_stg    # BESTIX staging
```

Elonyok:
- Teljes izolacio (nincs ugyfel-kozi data leak lehetoseg)
- Onallo backup es restore per ugyfel
- Per-ugyfel connection pool meret
- GDPR compliance: ugyfel adat torles = DB drop

Alternativa (kisebb ugyfeleknel): Shared DB, per-customer schema (`SET search_path TO azhu`).

---

## 8. Karbantartas es Frissites

### 8.1 Framework Update Process

```
Framework v1.2.0 -> v1.3.0 (MINOR, backward compat)

1. framework/v1.3.0 tag keszites
2. Uj base image build: ghcr.io/bestixcom/aiflow-base:v1.3.0
3. Minden ugyfel deployment.yaml-ban framework.version -> "1.3.0"
4. Per-ugyfel CI futtat: Pipeline D validate
5. Per-ugyfel staging deploy + automated test
6. Fokozatos prod rollout: BESTIX eloszor (belso), majd AZHU (nagyobb), NPRA utana

Idobecslés: 1-2 nap (automatizalt pipeline-okon)
```

**Breaking change eseten (v1.x -> v2.0):**
```
1. Deprecation window: v1.9.0-ban DeprecationWarning minden elavult API-ra
2. Compatibility shim: src/aiflow/engine/compat.py (6 honapos tamogatas)
3. Per-ugyfel migracio: aiflow skill migrate --to 2.0.0
4. Ugyfelek egyenkent migralva (staging eloszor, prod utana)
5. Compatibility shim eltavolitasa v2.1.0-ban
```

### 8.2 Skill Template Update

```
Skill aszf_rag_chat v1.2.0 -> v1.3.0 (uj feature: multi-language)

1. skill/aszf-rag-chat/v1.3.0 tag keszites
2. MINDEN ugyfel aki hasznalja az aszf_rag_chat-ot:
   - deployment.yaml: skill_templates[].version -> "1.3.0"
   - Instance YAML-ek: version -> "1.3.0"
3. Per-ugyfel staging deploy + instance-specifikus tesztek
4. Per-ugyfel prod rollout

FONTOS: Ugyfelek NEM KOTELEZEK azonnal frissiteni!
AZHU maradhat v1.2.0-n, mig NPRA mar v1.3.0-t hasznal.
```

### 8.3 Instance Config Update (Zero-Deploy for Prompts)

```
Prompt valtozas (NEM igenyel deploy-t):
  1. Langfuse UI-ban uj prompt verzio keszites
  2. Label athelyezes: "azhu-staging" -> teszteles
  3. Label athelyezes: "azhu-prod" -> eles
  4. Prompt cache TTL lejar (300s) -> uj verzio automatikusan betoltodik
  -> NINCS restart, NINCS deploy, NINCS image build

Instance config valtozas (deploy igenyel):
  1. Instance YAML modositas (pl. uj collection, SLA valtozas)
  2. PR + review + Pipeline D
  3. Merge -> staging deploy (automatikus)
  4. Manualis prod deploy (vagy auto ha staging tesztek sikeresek)
```

### 8.4 Hotfix Strategia

```
Szint 1: PROMPT HOTFIX (percek)
  Problema: Rossz valasz minoseg
  Megoldas: Langfuse-ban prompt rollback (regi verzio label-re allitas)
  Deploy: NEM kell (TTL lejar)
  Idobecslés: 5 perc

Szint 2: INSTANCE CONFIG HOTFIX (orak)
  Problema: Rossz SLA, rossz model, rossz routing
  Megoldas: Instance YAML modositas + fast-track PR
  Deploy: Staging -> Prod (automatizalt pipeline)
  Idobecslés: 1-2 ora

Szint 3: SKILL TEMPLATE HOTFIX (orak)
  Problema: Agent logika hiba, DAG hiba
  Megoldas: hotfix/{skill-nev}/{leiras} branch, javitas, uj skill patch verzio
  Deploy: Erintett ugyfelek ujra-build + deploy
  Idobecslés: 2-4 ora

Szint 4: FRAMEWORK HOTFIX (orak - 1 nap)
  Problema: Engine bug, security vulnerability
  Megoldas: hotfix/{leiras} branch, javitas, uj framework patch verzio
  Deploy: OSSZES ugyfel base image ujra-build + deploy
  Idobecslés: 4-8 ora (automatizalt) / 1 nap (manualis validacio)
```

---

## 9. Megvalositasi Fazisok

### Phase A: Instance Infrastructure (1-2 het)

**Cel:** A skill_instances tabla es az instance loading mechanizmus.

| # | Feladat | File(ok) |
|---|---------|----------|
| A1 | skill_instances tabla migracio | `alembic/versions/012_add_skill_instances.py` |
| A2 | workflow_runs.instance_id bovites | Ugyanaz a migracio |
| A3 | SkillInstance Pydantic model | `src/aiflow/skills/instance.py` |
| A4 | Instance YAML loader/validator | `src/aiflow/skills/instance_loader.py` |
| A5 | Instance registry (memory + DB) | `src/aiflow/skills/instance_registry.py` |
| A6 | ExecutionContext bovites (instance_id, customer, prompt_namespace) | `src/aiflow/core/context.py` |
| A7 | v_instance_stats view | Migracios script-ben |
| A8 | Unit tesztek | `tests/unit/skills/test_instance.py` |

**Kimenetek:** `aiflow skill instance list`, `aiflow skill instance load <yaml>`, DB tabla mukodik.

### Phase B: Framework Placeholder Completion (2-3 het)

**Cel:** Instance-aware framework komponensek.

| # | Feladat | File(ok) |
|---|---------|----------|
| B1 | PromptManager: namespace-aware prompt betoltes | `src/aiflow/prompts/manager.py` |
| B2 | ModelRouter: instance-szintu model override | `src/aiflow/models/router.py` |
| B3 | CostTracker: per-instance budget tracking | `src/aiflow/observability/cost.py` |
| B4 | WorkflowRunner: instance_id propagalas | `src/aiflow/engine/runner.py` |
| B5 | JobQueue: instance-specifikus queue routing | `src/aiflow/execution/queue.py` |
| B6 | API: instance CRUD endpoints | `src/aiflow/api/v1/instances.py` |
| B7 | API: instance-szures a workflow run endpoint-okon | `src/aiflow/api/v1/workflows.py` |
| B8 | Integration tesztek | `tests/integration/test_instance_lifecycle.py` |

**Kimenetek:** Teljes instance lifecycle (create -> config -> run -> monitor -> update -> disable).

### Phase C: Elso Valos Skill - ASZF RAG Chat (3-4 het)

**Cel:** Elso skill template ami tenylegesen tobb instance-kent fut.

| # | Feladat | File(ok) |
|---|---------|----------|
| C1 | aszf_rag_chat skill template veglegesites | `skills/aszf_rag_chat/` |
| C2 | AZHU ASZF instance konfig | `deployments/azhu/instances/azhu-aszf-rag.yaml` |
| C3 | AZHU belso instance konfig | `deployments/azhu/instances/azhu-internal-rag.yaml` |
| C4 | NPRA FAQ instance konfig | `deployments/npra/instances/npra-faq-rag.yaml` |
| C5 | Langfuse namespace setup (3 kulon prompt set) | Langfuse UI + sync script |
| C6 | Per-instance evaluation (promptfoo) | `skills/aszf_rag_chat/tests/instance_eval/` |
| C7 | Per-instance load test | `tests/performance/test_rag_instances.py` |
| C8 | Dokumentacio | `skills/aszf_rag_chat/README.md` bovites |

**Kimenetek:** 3 RAG Chat instance fut parhuzamosan, kulon promptokkal, kulon data source-okkal.

### Phase D: Masodik Valos Skill - Cubix Course Capture (4-5 het)

**Cel:** RPA skill multi-instance mukodes.

| # | Feladat | File(ok) |
|---|---------|----------|
| D1 | cubix_course_capture skill template veglegesites | `skills/cubix_course_capture/` |
| D2 | Udemy instance konfig | `deployments/npra/instances/npra-udemy-capture.yaml` |
| D3 | Coursera instance konfig | `deployments/npra/instances/npra-coursera-capture.yaml` |
| D4 | RPA worker instance-aware routing | `src/aiflow/rpa/worker.py` |
| D5 | RPA worker Dockerfile.base-rpa | `Dockerfile.base-rpa` |
| D6 | Platform-specifikus prompt overrides | Langfuse namespace setup |
| D7 | Per-instance E2E tesztek | `skills/cubix_course_capture/tests/instance_eval/` |
| D8 | Operatori HITL instance context | `src/aiflow/agents/human_loop.py` bovites |

**Kimenetek:** 2 Course Capture instance (Udemy, Coursera), kulon konfigokkal.

### Phase E: Customer Deployment Infrastructure (2-3 het)

**Cel:** Teljes ugyfel deploy pipeline.

| # | Feladat | File(ok) |
|---|---------|----------|
| E1 | deployment.yaml schema + validator | `scripts/validate_deployment.py` |
| E2 | Instance YAML validator | `scripts/validate_instance.py` |
| E3 | select_skills.py (Dockerfile generator) | `scripts/select_skills.py` |
| E4 | Pipeline D: CI workflow | `.github/workflows/pipeline-d-deploy-validate.yml` |
| E5 | AZHU deployment profil | `deployments/azhu/` |
| E6 | NPRA deployment profil | `deployments/npra/` |
| E7 | Per-customer Docker Compose config (K8s kesobb) | `deployments/{customer}/docker-compose.yml` |
| E8 | K8s manifest templates (Phase 2 - K8s cluster elerhetosegekor) | `deployments/_templates/k8s/` |
| E9 | Staging deploy script | `scripts/deploy_staging.sh` |
| E10 | Prod deploy script (manual approval) | `scripts/deploy_prod.sh` |
| E11 | End-to-end deploy test (staging) | `tests/e2e/test_customer_deploy.py` |

**Kimenetek:** `make deploy-staging customer=azhu`, `make deploy-prod customer=azhu`.

### Osszesitett Idovonal

```
Het 1-2:   Phase A - Instance infrastructure
Het 3-5:   Phase B - Framework instance-aware bovites
Het 5-8:   Phase C - Elso valos skill (ASZF RAG Chat, 3 instance)
Het 8-12:  Phase D - Masodik valos skill (Course Capture, 2 instance)
Het 12-14: Phase E - Customer deployment pipeline

Osszes: ~14 het
Parhuzamositas lehetoseg: Phase C es D reszben atfedheto Phase B vegezetevel.
Realisztikus becslés: 10-12 het (2 fejlesztovel).
```

---

## 10. Kapcsolodo Dokumentumok Modositasi Lista

A 28_MODULAR_DEPLOYMENT.md bevezetesekor az alabbi meglevo dokumentumokat kell frissiteni:

| Dokumentum | Modositas | Prioritas |
|------------|-----------|-----------|
| [03_DATABASE_SCHEMA.md](03_DATABASE_SCHEMA.md) | Uj tabla: skill_instances + workflow_runs.instance_id FK + v_instance_stats view. Tabla szam: 35 -> 36, view szam: 13 -> 14, migracio: 19 -> 20. | **P1** |
| [01_ARCHITECTURE.md](01_ARCHITECTURE.md) | ExecutionContext bovites (instance_id, customer, prompt_namespace). Rendszer attekintes diagramon instance layer hozzaadasa. | **P1** |
| [02_DIRECTORY_STRUCTURE.md](02_DIRECTORY_STRUCTURE.md) | Uj konyvtar: `deployments/` hierarchia (customer/instances/*.yaml, customer/k8s/). Uj scripts: validate_deployment.py, validate_instance.py, select_skills.py. | **P1** |
| [04_IMPLEMENTATION_PHASES.md](04_IMPLEMENTATION_PHASES.md) | Uj fazisok (A-E) hozzaadasa, vagy Phase 7 utani bovites. Idovonal novelese. | **P1** |
| [07_VERSION_LIFECYCLE.md](07_VERSION_LIFECYCLE.md) | Instance config verziozas strategia. Customer deployment tag strategia. | **P2** |
| [12_SKILL_INTEGRATION.md](12_SKILL_INTEGRATION.md) | `aiflow skill install` bovites instance-aware regisztracival. Uj parancs: `aiflow skill instance load`. | **P2** |
| [17_GIT_RULES.md](17_GIT_RULES.md) | Uj branch prefixek: instance/, deploy/. Uj commit tipusok: instance, deploy. CODEOWNERS bovites: deployments/{customer}/ ugyfel-teamhez. | **P2** |
| [21_DEPLOYMENT_OPERATIONS.md](21_DEPLOYMENT_OPERATIONS.md) | Docker image hierarchia (base, base-rpa, customer). K8s namespace strategia per-customer. CI Pipeline D. | **P2** |
| [22_API_SPECIFICATION.md](22_API_SPECIFICATION.md) | Uj endpoint-ok: /api/v1/instances CRUD, /api/v1/instances/{id}/stats. Meglevo endpoint-ok instance_id szuresi lehetoseg. | **P2** |
| [23_CONFIGURATION_REFERENCE.md](23_CONFIGURATION_REFERENCE.md) | Instance YAML config schema dokumentalas. Deployment.yaml schema. | **P2** |
| [AIFLOW_MASTER_PLAN.md](AIFLOW_MASTER_PLAN.md) | Multi-customer architektura szekció hozzaadasa. Instance model osszefoglalo. | **P3** |
| [00_EXECUTIVE_SUMMARY.md](00_EXECUTIVE_SUMMARY.md) | "Multi-customer / modular deployment" kepesseg hozzaadasa. | **P3** |
| [16_RAG_VECTORSTORE.md](16_RAG_VECTORSTORE.md) | Collection per-instance izolacio megerosites. Instance-szintu embedding config. | **P3** |
| [19_RPA_AUTOMATION.md](19_RPA_AUTOMATION.md) | RPA worker instance-aware routing. Base-rpa image referencia. | **P3** |
| [20_SECURITY_HARDENING.md](20_SECURITY_HARDENING.md) | Per-customer database izolacio. GDPR: ugyfel adat torles = DB drop. | **P3** |
| [CLAUDE.md](CLAUDE.md) | Frissitett szamok: 36 tabla, 14 view, 20 migracio. Uj dokumentum referencia: 28_MODULAR_DEPLOYMENT.md. deployments/ konyvtar hozzaadasa a kontextushoz. | **P1** |

**Osszesen:** 16 dokumentum modositando (4 P1, 7 P2, 5 P3).

---

## Osszefoglalas

Ez a dokumentum a **Skill Instance / Multi-Customer / Modular Deployment** architektura teljes referencija.

A harom retegu modell (Template -> Config -> Runtime) lehetove teszi, hogy:
- **Egyetlen skill codebase** tobb ugyfelnel, tobb konfiguracioval fusson
- **Ugyfel izolacio** (DB, Redis, Langfuse, K8s namespace) szinten biztositott legyen
- **Prompt valtoztatasok** deploy nelkul, percek alatt elessithetok legyenek
- **Framework es skill frissitesek** ugyfelenkent, fokozatosan vezethetoek be
- **Uj ugyfel** felvitele: deployment.yaml + instance YAML-ek + K8s overlay = kesz

A megvalositasi fazisok (A-E, ~14 het) a meglevo 22 hetes implementation plan utani bovites,
vagy reszben parhuzamositva a Phase 6-7 idoszakkal.
