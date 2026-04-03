# AIFlow v1.2.0 — LLM Quality, Cost Optimization & Prompt Engineering

> **Szulo terv:** `48_ORCHESTRABLE_SERVICE_ARCHITECTURE.md`
> **Cel:** Megbizhato, koltseghatekony LLM hasznalat — prompt teszteles, minoseg monitoring, koltseg optimalizalas.

---

## 1. Jelenlegi Allapot

| Komponens | Allapot | Hianyzik |
|-----------|---------|----------|
| **EvalSuite** | 100% (core + scorers + datasets) | LLM rubric scoring (stub), CI/CD integracio |
| **Promptfoo** | 40% (1 skill config, manualis) | Automatizalt CI, cost tracking, tobb skill |
| **CostTracker** | 100% in-memory + PostgreSQL | Real-time alert, pre-exec budget check |
| **ModelCostCalculator** | 100% (pricing table) | Auto-update arfolyamok |
| **PromptManager** | 100% (YAML + cache) | Langfuse A/B testing, canary deploy |
| **Langfuse Tracing** | 5% (stub) | Valos integracio |
| **LLM Rubric Scoring** | 5% (stub, return 0.5) | Valos LLM-alapu ertekeles |

---

## 2. Prompt Engineering Pipeline

### 2.1 Prompt Lifecycle

```
1. DEVELOP   → Prompt YAML irasa (prompts/{service}/{name}.yaml)
2. TEST      → Promptfoo eval (automatikus CI/CD)
3. STAGE     → Langfuse label: "staging" → A/B test
4. DEPLOY    → Langfuse label: "production" → canary (10% → 50% → 100%)
5. MONITOR   → Cost + quality metrikkak → alert ha romlik
6. OPTIMIZE  → Olcsobb modellre migralás ha minoseg megmarad
```

### 2.2 Promptfoo Bovites

**Jelenlegi:** 1 skill, 7 test case, manualis futatas.
**Cel:** Minden skill, 100+ test case/skill, CI/CD automatizalt.

**Uj konfiguraciok:**
```
skills/
  aszf_rag_chat/tests/promptfooconfig.yaml          # MAR LETEZIK (7 case)
  email_intent_processor/tests/promptfooconfig.yaml  # UJ (intent classification)
  process_documentation/tests/promptfooconfig.yaml   # UJ (BPMN generation)
  invoice_processor/tests/promptfooconfig.yaml       # UJ (szamla kinyeres)
```

**Bovitett promptfoo_provider.py:**
```python
# Jelenlegi: 2 skill (hardcoded)
# Cel: Dinamikus skill discovery + pipeline execution

SUPPORTED_SKILLS = {
    "aszf_rag_chat": {"workflow": "query", "steps": [rewrite, search, build, generate, cite, halluc]},
    "email_intent_processor": {"workflow": "classify", "steps": [parse, classify, extract_entities]},
    "process_documentation": {"workflow": "generate", "steps": [classify, elaborate, extract, review, generate]},
    # Uj skill hozzaadasa: csak ide kell felvenni
}
```

**CI/CD integracio (GitHub Actions / pre-commit hook):**
```yaml
# .github/workflows/prompt-eval.yml
name: Prompt Evaluation
on: [pull_request]
jobs:
  eval:
    steps:
      - run: npx promptfoo eval -c skills/*/tests/promptfooconfig.yaml --output tests/artifacts/promptfoo/
      - run: python scripts/check_promptfoo_results.py --min-pass-rate 0.90
      # Ha pass rate < 90% → PR BLOCKED
```

### 2.3 LLM Rubric Scoring (a stub implementalasa)

```python
# src/aiflow/evaluation/scorers.py — llm_rubric implementacio
async def llm_rubric(
    actual: str,
    expected: str | None,
    rubric: str,
    model: str = "openai/gpt-4o-mini",
) -> tuple[float, bool]:
    """LLM-alapu minoseg ertekeles rubric alapjan.
    
    A rubric egy Jinja2 template ami megmondja az LLM-nek
    mit es hogyan ertekalje (1-5 skala).
    """
    # 1. Prompt osszeallit: system=rubric, user=actual+expected
    # 2. LLM hivas (gpt-4o-mini, olcso)
    # 3. Structured output: {"score": 1-5, "reasoning": "..."}
    # 4. Return (score/5.0, score >= 3)
```

**Beepitett rubricok:**
| Rubric | Mit mér | Mikor hasznald |
|--------|---------|----------------|
| `relevance` | Valasz mennyire releváns a kerdesre | RAG query |
| `faithfulness` | Valasz a forrasokbol szarmazik-e (hallucination check) | RAG query |
| `completeness` | Minden kerdes-reszt megvalaszol-e | RAG query |
| `extraction_accuracy` | Kinyert mezok helyessege | Document extraction |
| `intent_correctness` | Intent azonositas pontossaga | Email classification |
| `hungarian_quality` | Magyar nyelvi minoseg | Minden magyar output |

---

## 3. Cost Optimization

### 3.1 Model Tier System

```yaml
# Koltseg-alapu modell valasztas — YAML pipeline-ban konfiguralhato
model_tiers:
  cheap:                    # Tisztitas, metadata, intent screening
    model: openai/gpt-4o-mini
    cost: ~$0.15/1M input
    use_for: [data_cleaning, metadata_enrichment, intent_classification, notification_template]
    
  standard:                 # Altalanos feladatok
    model: openai/gpt-4o
    cost: ~$2.50/1M input
    use_for: [document_extraction, rag_answer, bpmn_generation]
    
  premium:                  # Kritikus, magas minoseg
    model: anthropic/claude-sonnet-4
    cost: ~$3.00/1M input
    use_for: [complex_reasoning, contract_analysis, quality_gate_review]
```

### 3.2 Koltseg Monitoring Bovites

**Jelenlegi:** cost_records tabla + napi/havi aggregacio.
**Bovites:**

```python
# Real-time cost alerting
class CostAlertService:
    async def check_and_alert(self, team_id: str) -> BudgetAlert:
        """Pipeline/workflow vegrehajtas ELOTT es KOZBEN ellenorzi a koltsegveteset."""
        status = await self.cost_tracker.check_budget(team_id, budget_limit)
        if status.alert == BudgetAlert.WARNING:
            await self.notification_service.send("slack", "Budget 80%: {{ team_name }}", ...)
        elif status.alert == BudgetAlert.EXCEEDED:
            raise BudgetExceededError(f"Team {team_id} budget exceeded")
        return status.alert

    async def pre_execution_estimate(self, pipeline_def: PipelineDefinition, input_data: dict) -> float:
        """Pipeline futtas ELOTT becsuli a koltsegeet (step-enkent)."""
        total = 0.0
        for step in pipeline_def.steps:
            model = step.config.get("model", "openai/gpt-4o-mini")
            est_tokens = self._estimate_tokens(step, input_data)
            total += self.cost_calculator.estimate_cost(model, est_tokens, est_tokens // 4)
        return total
```

### 3.3 Prompt Koltseg Optimalizalas

| Technika | Megtakaritas | Pelda |
|----------|-------------|-------|
| **Model downgrade** | 50-90% | gpt-4o → gpt-4o-mini (ha minoseg megmarad) |
| **Prompt rohvidites** | 10-30% | Felesleges pelda eltavolitas, tomor utasitasok |
| **Cache** | 90%+ (cache hit) | Ugyanaz a keres → cached valasz (Redis TTL) |
| **Batch** | 20-40% | Batch API hivas (50 szamla → 1 hivas) |
| **Structured output** | 10-20% | JSON schema → kevesebb output token |

**Automatikus model selection:**
```python
# Pipeline step config-ban:
config:
  model: auto  # → CostOptimizer valaszt:
               #   1. Probald gpt-4o-mini-vel
               #   2. Ha minoseg < threshold → gpt-4o-ra emelj
               #   3. Logold mindkettot Langfuse-ba
```

---

## 4. Quality Tracking Dashboard

### 4.1 Uj API endpointok

```
GET /api/v1/quality/overview          — Osszes skill minoseg osszefoglalas
GET /api/v1/quality/skill/{name}      — Skill-szintu minoseg (pass rate, avg score, cost)
GET /api/v1/quality/prompts           — Prompt verziok + teljesitmeny osszehasonlitas
GET /api/v1/quality/cost-vs-quality   — Koltseg vs. minoseg scatter plot adat
POST /api/v1/quality/evaluate         — Ad-hoc evaluation futatas
```

### 4.2 UI oldal: Quality & Cost Dashboard

**Uj oldal: `aiflow-admin/src/pages-new/Quality.tsx`**

- KPI kartyak: Total cost (today/month), Avg quality score, Pass rate, Model breakdown
- Koltseg vs. minoseg graf (scatter plot, modell-enkent szinezve)
- Prompt verzio osszehasonlitas tabla (v1 vs v2: minoseg, koltseg, latency)
- Skill-szintu bontas: melyik skill mennyit kolt es milyen minoesegben
- Alert lista: budget warning-ok, minoseg-romlasok

---

## 5. Gotenberg PDF Service (kiegeszito)

**Mi ez:** Docker-alapu PDF generálo service (HTML/DOCX → PDF).
**Mire jo:** Report export, szamla PDF generalas, BPMN diagram PDF.
**NEM PDF kinyeresre** — arra Docling/Unstructured van.

```bash
# Docker:
docker run --rm -p 3000:3000 gotenberg/gotenberg:8

# Hasznalat:
curl -X POST http://localhost:3000/forms/chromium/convert/html \
  -F files=@report.html -o report.pdf

curl -X POST http://localhost:3000/forms/libreoffice/convert \
  -F files=@invoice.docx -o invoice.pdf
```

**Integracio:** `docker-compose.yaml`-hoz hozzaadni mint optional service.
**Pipeline hasznalat:**
```yaml
- name: export_pdf
  service: gotenberg
  method: convert_html
  config:
    template: "templates/invoice_report.html"
    data: "{{ extract_data.output }}"
```

---

## 6. Fejlesztesi Fazisok

| Fazis | Feladat | Prioritas |
|-------|---------|-----------|
| **1** | Promptfoo CI/CD (pre-commit + GitHub Actions) | MAGAS |
| **2** | LLM rubric scoring implementacio (6 rubric) | MAGAS |
| **3** | Pre-execution cost estimation + budget alerts | KOZEP |
| **4** | Langfuse valos integracio (tracing + prompt A/B) | KOZEP |
| **5** | Quality & Cost dashboard UI | ALACSONY (Tier 2 utan) |
| **6** | Auto model selection (cost optimizer) | ALACSONY |
| **7** | Gotenberg integracio (PDF export) | ALACSONY |

---

## 7. Verifikacio

```bash
# Promptfoo CI teszt:
npx promptfoo eval -c skills/aszf_rag_chat/tests/promptfooconfig.yaml
# Pass rate >= 90%?

# Cost tracking:
curl /api/v1/costs/breakdown  # Valos koltseg adatok model-enkent

# LLM rubric:
python -c "from aiflow.evaluation.scorers import llm_rubric; ..."
# Score returned (not 0.5 placeholder)

# Budget alert:
# Set team budget to $0.01, run pipeline → BudgetExceededError
```
