# AIFlow - Uzleti Dokumentacio es Audit

## 1. Auto-Generalt Dokumentacio

### 1.1 Workflow DAG -> Uzleti Leiras

Minden workflow DAG-jabol automatikusan generalhato:

```bash
# Mermaid diagram a workflow-bol
aiflow workflow docs --name process-documentation --format mermaid

# Uzleti leiras Markdown-ban
aiflow workflow docs --name process-documentation --format markdown

# Teljes dokumentacio (diagram + leiras + adat-flow + koltseg becslest)
aiflow workflow docs --name process-documentation --format full
```

**Generalt kimenet pelda:**

```markdown
# Process Documentation Workflow

## Attekintes
A "Process Documentation" workflow termeszetes nyelvu folyamat-leirasokat
alakit at strukturalt dokumentaciova, BPMN-kompatibilis diagramokka.

## Lepesek

| # | Lepes | Leiras | AI Model | Atlagos Koltseg |
|---|-------|--------|----------|-----------------|
| 1 | Classify Intent | Bemenet klasszifikacioja | GPT-4o-mini | $0.002 |
| 2 | Elaborate | Szoveg kibovitese BPMN terminologiaval | GPT-4o | $0.015 |
| 3 | Extract | Strukturalt adat kinyeres | GPT-4o | $0.020 |
| 4 | Review | Minosegi ellenorzes (score >= 8/10) | GPT-4o | $0.005 |
| 5 | Generate | Diagram es tabla generalas | GPT-4o-mini | $0.003 |

## Folyamat Diagram
[Mermaid diagram automatikusan renderelve]

## Minosegi Kapuk
- Extract utan: completeness >= 0.80 (ha nem -> Refine, max 3x)
- Review utan: score >= 8/10 (ha nem -> Human Review)

## Becsult Koltseg: $0.045-0.065 per futtatas
## Becsult Ido: 8-15 masodperc
```

### 1.2 Data Flow Dokumentacio

```bash
aiflow workflow docs --name process-documentation --format data-flow
```

**Kimenet:**

```
classify_intent:
  INPUT:  ClassifyInput {message: str}
  OUTPUT: ClassifyOutput {category: "process"|"greeting"|"off_topic", confidence: float}

elaborate:
  INPUT:  ElaborateInput {text: str}
  OUTPUT: ElaborateOutput {elaborated: str, improved: bool}

extract:
  INPUT:  ExtractInput {text: str}
  OUTPUT: ProcessExtraction {title: str, steps: list[ProcessStep], actors: list[str]}

review:
  INPUT:  ReviewInput {extraction: ProcessExtraction, original_text: str}
  OUTPUT: ReviewOutput {score: float, issues: list[str], suggestions: list[str]}
```

### 1.3 Dokumentacio Szinkronban Tartasa

**CI validacio:**

```yaml
# .github/workflows/ci-skill.yml
jobs:
  docs-check:
    - aiflow workflow docs --name <name> --format markdown --check
    # Generaija a dok-ot az aktualis kodbol
    # Osszeveti a commitolt docs/-szal
    # Ha kulonbozik -> CI FAIL: "Docs out of sync"
```

**Prompt changelog:**

```
# skills/process_documentation/PROMPT_CHANGELOG.md (auto-generalt)

## 2026-03-27: process-doc/classifier v6
- Synced by: user@company.com
- Label: dev -> test
- Valtozas: Magyar datum-formatum peldak hozzaadva

## 2026-03-25: process-doc/extractor v8
- Synced by: user@company.com
- Label: test -> prod
- Valtozas: Donesi pont (gateway) felismeres javitasa
```

---

## 2. Audit Trail

### 2.1 Mit Rogzit a Rendszer

Minden szignifikans muvelet az `audit_log` tablaba kerul:

| Muvelet | Rogzitett adatok |
|---------|-----------------|
| workflow.run | Ki futtatta, milyen workflow-t, milyen inputtal, mennyi koltseg, mennyi ido |
| workflow.create | Ki hozta letre, milyen config-gal |
| skill.install | Ki telepitette, melyik verziot |
| prompt.sync | Ki szinkronizalta, melyik prompt-ot, melyik Langfuse label-re |
| prompt.promote | Ki leptetette elo (dev->test->staging->prod) |
| user.login | Ki lepett be, honnan |
| user.role_change | Kinek valtoztatta meg a szerepkoret, ki |
| budget.change | Ki modositotta a team koltsegkeretet |
| human_review.decision | Ki hozta a dontest, mi volt a dontes |

### 2.2 Audit Rekord Pelda

```json
{
  "id": "audit-456",
  "timestamp": "2026-03-27T10:15:30Z",
  "user_id": "user@company.com",
  "team_id": "finance",
  "action": "workflow.run",
  "resource_type": "workflow",
  "resource_id": "invoice-processing",
  "details": {
    "workflow_version": "2.1.0",
    "run_id": "run-abc123",
    "input_summary": "Invoice from Supplier X, amount: 150,000 HUF",
    "model_used": "gpt-4o",
    "prompt_versions": {
      "invoice/classifier": 3,
      "invoice/extractor": 5
    },
    "cost_usd": 0.058,
    "duration_ms": 12340,
    "status": "completed",
    "quality_scores": {
      "extraction_accuracy": 0.92,
      "review_score": 0.88
    }
  },
  "ip_address": "192.168.1.100"
}
```

### 2.3 Audit Lekerdezesek

```bash
# Ki futtatott workflow-t a mult heten?
GET /api/v1/admin/audit?action=workflow.run&from=2026-03-20&to=2026-03-27

# Milyen prompt valtozasok tortentek?
GET /api/v1/admin/audit?action=prompt.*&team=finance

# Teljes audit trail egy workflow run-hoz
GET /api/v1/admin/audit?resource_id=run-abc123
```

---

## 3. Compliance Riportok

### 3.1 AI Governance Riport

```bash
aiflow report compliance --period 2026-Q1 --format pdf
```

**Tartalom:**

```
=== AIFlow AI Governance Riport - 2026 Q1 ===

1. AI Hasznalat Attekintes
   - Osszes workflow futtatas: 12,456
   - Osszes LLM hivas: 67,890
   - Osszes koltseg: $3,456.78
   - Hasznalt modellek: GPT-4o (62%), GPT-4o-mini (38%)

2. Minosegi Metriak
   - Atlagos quality gate pass rate: 94.2%
   - Human review-k szama: 234 (1.9% osszes futtatasbol)
   - Human review doontesek: 89% approved, 8% rejected, 3% modified

3. SLA Teljesites
   - p95 latency: 12.3s (cel: 15s) -> MEGFELEL
   - Success rate: 97.8% (cel: 95%) -> MEGFELEL
   - Availability: 99.95% (cel: 99.9%) -> MEGFELEL

4. Biztonsagi Esemenyek
   - Sikertelen authentikacio: 12 (mind blokkolt)
   - Budget tullepes kiserlet: 3 (mind megakadalyozva)
   - Nem jogosult hozzaferes: 0

5. Prompt Verziok
   - Aktiv prompt-ok szama: 23
   - Prompt frissitesek szama: 45
   - Regresszio esetek: 2 (mindketto CI-ban elkapat)
```

### 3.2 GDPR Compliance

```python
class GDPRReporter:
    async def data_processing_report(self, period):
        """Milyen workflow-k dolgoznak szemelyes adattal."""
        ...

    async def data_retention_report(self, period):
        """Meddig tarolunk adatot, mi torlodott."""
        ...

    async def redact_pii(self, run_id):
        """PII torles egy adott workflow run input/output adataibol."""
        # workflow_runs.input_data es output_data JSONB-ben
        # a PII mezok NULL-ra allitasa, audit_log bejegyzessel
        ...
```

```bash
# PII torles (GDPR "right to be forgotten")
aiflow admin redact --run-id abc123
# -> input_data es output_data PII mezoi torolve
# -> audit_log bejegyzes: "data.redacted by admin@company.com"
# -> Langfuse trace metadata frissitve
```

### 3.3 SOC2 Type II

```
Automatikusan elerheto adatok SOC2 audithoz:

CC6.1 - Hozzaferes kontroll:
  - audit_log (user.login, user.role_change)
  - RBAC config (roles, permissions)

CC7.2 - Rendszer monitorozas:
  - SLA riportok (v_workflow_metrics)
  - Alerting konfig es historikus alertek

CC8.1 - Valtozas kezeles:
  - Git commit history
  - Prompt verziok (Langfuse)
  - Deployment history (CI/CD pipeline)
  - audit_log (workflow.create, prompt.sync, skill.install)
```

---

## 4. Executive Dashboard

### 4.1 SQL View-k (Grafana adatforrasok)

```sql
-- Workflow hasznalat es sikeresseg
CREATE VIEW v_workflow_metrics AS
SELECT
    workflow_name,
    DATE(created_at) as day,
    COUNT(*) as total_runs,
    COUNT(*) FILTER (WHERE status = 'completed') as successful,
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
```

### 4.2 Dashboard Szintek

| Dashboard | Celkozonseg | Tartalom |
|-----------|------------|----------|
| **Executive** | Vezerigazgato, CFO | Osszes workflow, koltseg, ROI, trend |
| **Operations** | DevOps, SRE | Queue depth, worker utilization, SLA, alertek |
| **Team** | Team lead | Sajat team workflow-jai, koltseg, budget |
| **LLM** | AI engineer | Langfuse nativ: prompt performance, token usage |
| **Audit** | Auditor, compliance | Audit log, compliance metriak, hozzaferes |

### 4.3 API Endpoint-ok a Dashboard-okhoz

```
GET /api/v1/admin/metrics/overview          # Executive attekintes
GET /api/v1/admin/metrics/workflows         # Workflow metriak (szurheto)
GET /api/v1/admin/metrics/teams             # Team koltseg es budget
GET /api/v1/admin/metrics/models            # Modell hasznalat
GET /api/v1/admin/metrics/sla              # SLA riport
GET /api/v1/admin/audit                    # Audit log (szurheto, lapozható)
```

---

## 5. Dokumentum Tipusok Osszefoglalo

| Dokumentum tipus | Ki szamara | Generalas | Forras |
|------------------|-----------|-----------|--------|
| Workflow DAG diagram | Mindenki | Auto (aiflow workflow docs) | Kod |
| Uzleti leiras | Business | Auto (aiflow workflow docs) | Kod + metadata |
| Data flow | Fejleszto, auditor | Auto (aiflow workflow docs) | Pydantic modellek |
| API referencia | Fejleszto | Auto (FastAPI /docs) | Route definiciok |
| Audit trail | Auditor | Auto (API lekerdezesek) | audit_log tabla |
| Compliance riport | Auditor, compliance | Felautomata (aiflow report) | DB view-k + metriak |
| Koltseg riport | CFO, team lead | Auto (API/Grafana) | cost_records |
| SLA riport | Operations | Auto (API/Grafana) | workflow_runs |
| Prompt changelog | Fejleszto, auditor | Auto (sync soran) | Langfuse + YAML diff |
| Skill leiras | Mindenki | Felautomata (skill.yaml + kod) | Skill manifest |
