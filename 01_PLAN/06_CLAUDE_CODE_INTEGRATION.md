# AIFlow - Claude Code Integracio

## Attekintes

A Claude Code az AIFlow keretrendszer szerves resze a teljes eletciklus soran:
fejlesztes, teszteles, uzemeltetes, karbantartas.

---

## 1. Fejlesztes (Development)

### 1.1 Uj Skill Letrehozas

```
User: "Keszits egy uj skill-t szamla-feldolgozasra"

Claude Code:
1. aiflow skill new invoice_processing --template medium_branching
2. skill.yaml manifest kitoltese
3. Agent implementaciok generalasa:
   - ClassifierAgent (szamla tipus felismeres)
   - ExtractorAgent (szamla adatok kinyerese)
   - ValidatorAgent (adatok ellenorzese)
   - RouterAgent (jovahagyas utvonal)
4. Prompt YAML-ok irasa (classifier, extractor, validator)
5. Pydantic modellek (InvoiceData, LineItem, etc.)
6. Workflow DAG definicio
7. 100+ teszt eset generalas
```

### 1.2 Workflow Fejlesztes

```
User: "Add hozza egy human review lepest az extractor utan"

Claude Code:
1. workflow.py-ban quality gate hozzaadasa az extract lepes utan
2. QualityGate definicio (threshold: 0.85, on_fail: "human_review")
3. HumanReviewRequest template keszitese
4. Teszt esetek frissitese
```

### 1.3 Prompt Engineering

```
User: "Az extractor nem ismeri fel jol a datumokat"

Claude Code:
1. Langfuse trace elemzes (hibas esetek keresese)
2. Prompt YAML frissitese (datum pelda hozzaadasa, format pontositas)
3. Promptfoo teszt eset hozzaadasa a datumokra
4. aiflow prompt sync --label dev
5. aiflow eval run --skill invoice_processing
6. Eredmenyek osszehasonlitasa
```

---

## 2. Teszteles (Testing)

### 2.1 Automatikus Teszt Generalas

```
User: "Generald le a teszt eseteket az uj classifier prompt-hoz"

Claude Code:
1. Meglevo prompt elemzese (classifier.yaml)
2. Edge case-ek azonositasa (hatar esetek, tobbertelmeu inputok)
3. 100+ teszt eset generalas:
   - 40% pozitiv esetek (helyes klasszifikacio)
   - 30% negativ esetek (elutasitando)
   - 20% hataresetek (bizonytalan)
   - 10% adverz esetek (prompt injection, irrelevans)
4. promptfooconfig.yaml frissitese
5. Tesztek futtatasa es eredmenyek elemzese
```

### 2.2 E2E Teszt Futtatás

```
User: "Futtasd le a teljes process-doc workflow tesztet"

Claude Code:
1. aiflow eval run --skill process_documentation
2. Eredmenyek elemzese:
   - Per-step accuracy
   - Teljes pipeline pass rate
   - Koltseg per teszt eset
   - Latency distribution
3. Hibas esetek reszletes elemzese
4. Javitasi javaslatok
```

### 2.3 Regresszios Teszteles

```
User: "A classifier prompt-ot frissitettem, ellenorizd hogy nem romlott-e"

Claude Code:
1. aiflow prompt diff (lokalis vs Langfuse osszehasonlitas)
2. aiflow prompt test (Promptfoo futtatas)
3. Eredmenyek osszehasonlitasa az elozo verzioval
4. Regresszio jelentes
```

---

## 3. Uzemeltetes (Operations)

### 3.1 Monitoring & Alerting

```
User: "Nezd meg mi tortent a tegnapi workflow hibakkal"

Claude Code:
1. Langfuse trace-ek lekerdezese (hibas workflow_runs)
2. Hiba tipusok csoportositasa
3. Root cause elemzes:
   - LLM timeout? -> model overload
   - Budget exceeded? -> cost spike
   - Quality gate failed? -> prompt degradation
4. Javitasi javaslatok
```

### 3.2 SLA Riport

```
User: "Keszits SLA riportot az elmult hetre"

Claude Code:
1. workflow_runs lekerdezes (elmult 7 nap)
2. Per-workflow metriak:
   - p50, p95, p99 latency
   - Success rate
   - SLA compliance %
3. Per-team koltseg osszesites
4. Trend elemzes (romlott/javult)
5. Strukturalt riport generalas
```

### 3.3 Incident Investigation

```
User: "A contract-review workflow 30%-ban hibazik reggel ota"

Claude Code:
1. Friss workflow_runs lekerdezes (status=failed)
2. Kozos hibamintak keresese
3. Langfuse trace elemzes a hibas futasokra
4. Lehetseges okok:
   - OpenAI rate limit? -> rate_limiter config
   - Prompt regreszio? -> prompt version ellenorzes
   - Input mintavaltozas? -> input elemzes
5. Azonnali mitigation javaslat
6. Hosszu tavu fix terv
```

---

## 4. Karbantartas (Maintenance)

### 4.1 Dependency Update

```
User: "Frissitsd a fuggosegeket"

Claude Code:
1. pyproject.toml es requirements elemzes
2. Elerheto frissitesek azonositasa
3. Breaking change-ek ellenorzese (changelog review)
4. Fuggosegek frissitese
5. pytest futtatás
6. Regresszio ellenorzes
```

### 4.2 Refactoring

```
User: "A process_documentation skill tul bonyolult lett"

Claude Code:
1. Skill elemzes (file count, LOC, complexity)
2. Refactoring javaslatok:
   - Sub-skill-ekre bontas?
   - Kozos lepesek kiszervezese a step library-ba?
   - Prompt egyszerusites?
3. Refactoring vegrehajtasa tesztekkel
```

### 4.3 Dokumentacio Frissites

```
User: "Frissitsd a dokumentaciot az uj feature-okkel"

Claude Code:
1. Git diff elemzes (mi valtozott)
2. docs/ frissitese az uj funkciokkal
3. API reference frissitese (uj endpoint-ok)
4. README frissitese
```

---

## 5. Claude Code CLAUDE.md Minta

Az AIFlow projekt CLAUDE.md fajlja a Claude Code-nak:

```markdown
# AIFlow Project

## Project Overview
Enterprise AI Automation Framework for building, deploying, and operating
AI-powered automation workflows at scale.

## Tech Stack
- Python 3.12+, FastAPI, arq, Redis, PostgreSQL
- LiteLLM (LLM), Langfuse (observability), Promptfoo (testing)

## Key Commands
- `make dev` - Start development environment
- `make test` - Run all tests
- `make lint` - Lint + format
- `aiflow workflow list` - List workflows
- `aiflow workflow run <name> --input '{}'` - Run a workflow
- `aiflow prompt sync --label dev` - Sync prompts to Langfuse
- `aiflow eval run --skill <name>` - Run evaluation suite

## Architecture
- `src/aiflow/engine/` - Workflow engine (DAG-based)
- `src/aiflow/agents/` - 2-level agent system (max 6 specialists)
- `src/aiflow/skills/` - Domain knowledge packages
- `src/aiflow/prompts/` - Langfuse SSOT prompt management
- `skills/` - Installed skill packages

## Conventions
- Every step MUST have typed Pydantic input/output
- Max 6 specialist agent types per orchestrator
- Specialists MUST be stateless
- Prompts MUST be in YAML, synced to Langfuse
- Every skill MUST have 100+ test cases
- structlog for logging (never print())
```

---

## 6. MCP Server Integracio

Az AIFlow API-ja MCP server-kent is elerheto Claude Code szamara:

```json
{
  "mcpServers": {
    "aiflow": {
      "command": "python",
      "args": ["-m", "aiflow.contrib.mcp_server"],
      "env": {
        "AIFLOW_API_URL": "http://localhost:8000"
      }
    }
  }
}
```

**Elerheto MCP tool-ok:**
- `aiflow_workflow_list` - Workflow-k listazasa
- `aiflow_workflow_run` - Workflow futtatás
- `aiflow_job_status` - Job statusz
- `aiflow_skill_list` - Skill-ek listazasa
- `aiflow_prompt_get` - Prompt lekeres
- `aiflow_eval_run` - Evaluation futtatas
- `aiflow_cost_report` - Koltseg riport

Ezzel a Claude Code kozvetlenul tudja hasznalni az AIFlow API-t
anelkul, hogy az usernek kezzel kellene API hivasokat irnia.
