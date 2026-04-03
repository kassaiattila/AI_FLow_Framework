# AIFlow v1.2.0 — Claude Code Configuration & Control Plan

> **Szulo terv:** `48_ORCHESTRABLE_SERVICE_ARCHITECTURE.md`
> **Cel:** Claude Code iranyitas optimalizalasa az orchestration fejlesztes tamogatasahoz.

---

## 1. Jelenlegi Konfiguracio Osszefoglalas

| Elem | Darab | Allapot |
|------|-------|---------|
| CLAUDE.md fajlok | 6 | Root + src/aiflow + 01_PLAN + skills + tests + 2 skill ref |
| Slash commands | 18 | 6 generator, 3 phase, 3 test, 2 plan, 7 UI (HARD GATE) |
| Command sorok | 1,513 | .claude/commands/ mappaban |
| Permission rules | 30+ allow, 3 deny | .claude/settings.local.json |
| MCP kapcsolatok | 2 | Figma MCP, Playwright MCP |

---

## 2. CLAUDE.md Frissitesek

### 2.1 Root CLAUDE.md bovites

Az uj v1.2.0 fejleszteshez frissitendo szekciok:

```markdown
## Current Phase: Orchestrable Service Architecture (v1.1.4 → v1.2.0)
**Terv:** `01_PLAN/48_ORCHESTRABLE_SERVICE_ARCHITECTURE.md` + 6 reszletes terv (49-54)

Fo celok:
- **Pipeline orchestrator** — YAML-defined service chaining
- **Uj szolgaltatasok** — notification, data_router, advanced RAG services
- **LLM quality** — Promptfoo CI/CD, cost optimization, rubric scoring
- **Frontend** — Untitled UI 80+ component integration, chat UI modernization

**Fazisok:**
Tier 1 (Core): P1 Adapter → P2 Schema → P3 Runner+DB → P4 API → P5 UI
Tier 2 (Support): P6A Notification │ P6B Kafka │ P6C Service Mgr │ P6D Data Router
Tier 3 (RAG): P7A-7F (independent services)
Phase 8: Pipeline Templates
```

### 2.2 01_PLAN/CLAUDE.md szamok frissitese

```markdown
# Frissitett szamok:
- 41 DB tables + 6 new planned (47 total after v1.2.0)
- 26 Alembic migracio (001-026, mind letezik) + 3 tervezett (027-029)
- 112+ endpoints + 13 new pipeline endpoints planned
- 15 services + 10 new planned (25 total after v1.2.0)
- Plan documents: 48-54 (orchestrable service architecture)
```

---

## 3. Uj Slash Commands (v1.2.0)

### 3.1 /new-pipeline — Pipeline YAML generator

```markdown
# .claude/commands/new-pipeline.md

Generate a YAML pipeline definition for the AIFlow orchestration system.

## Input
$ARGUMENTS — natural language description of the pipeline (e.g., "email szamla feldolgozas")

## Steps
1. List available service adapters:
   - Read src/aiflow/pipeline/adapters/ directory
   - List each adapter's service_name, method_name, input/output schemas
   
2. Match user description to available services:
   - Identify required services for the described workflow
   - Determine step order and dependencies
   - Identify for_each and condition needs

3. Generate pipeline YAML:
   - Follow schema from 01_PLAN/48 Phase 2
   - Include: name, version, description, trigger, input_schema, steps
   - Use Jinja2 templates for cross-step references
   - Add retry policies for external service calls

4. Validate:
   - Check all service+method pairs exist in adapter registry
   - Verify depends_on references are valid
   - Ensure no circular dependencies

5. Show YAML to user for review
6. On approval: save to src/aiflow/pipeline/builtin_templates/ or register via API

## Rules
- EVERY step MUST reference an existing adapter (service + method)
- for_each expressions MUST be valid Jinja2
- condition expressions MUST follow the Condition format (output.field op value)
- Input schema MUST define all required pipeline inputs
- Include retry for external service calls (LLM, email fetch, etc.)
```

### 3.2 /pipeline-test — Pipeline end-to-end test

```markdown
# .claude/commands/pipeline-test.md

Test a pipeline definition end-to-end with real services.

## Input
$ARGUMENTS — pipeline name or YAML file path

## Steps
1. Load pipeline definition (from DB or YAML file)
2. Validate: compile to DAG, check adapter availability
3. Prepare test input data (ask user or use defaults)
4. Execute pipeline via PipelineRunner
5. Check results:
   - All steps completed?
   - workflow_runs row created?
   - step_runs rows for each step?
   - Cost recorded?
6. Report: step-by-step results, total cost, duration, any errors

## Rules
- VALOS futatas, NEM mock (same rule as /dev-step)
- Ha barmelyik step FAIL → report error, NEM "kesobb javitjuk"
- Cost tracking MUST work (check cost_records table)
```

### 3.3 /quality-check — LLM quality + cost report

```markdown
# .claude/commands/quality-check.md

Run quality and cost analysis for a service or pipeline.

## Steps
1. Run Promptfoo evaluation for the specified skill/service
2. Collect cost data from cost_records table
3. Calculate: pass rate, avg quality score, total cost, cost per query
4. Compare with previous run (if exists)
5. Report:
   - Quality: pass rate (target >= 90%), rubric scores
   - Cost: total USD, per-model breakdown, cost trend
   - Recommendations: model downgrade opportunities, prompt optimization
6. Flag regressions: if quality dropped or cost increased significantly

## Rules
- Real LLM calls (NOT mock)
- Save results to tests/artifacts/quality/
- Compare with baseline (if available)
```

---

## 4. CLAUDE.md Pipeline-Specifikus Szabalyok

Az alabbiakat HOZZAADNI a root CLAUDE.md-hez:

```markdown
## MANDATORY Pipeline Development Rules

### Pipeline YAML Rules
- MINDEN pipeline YAML a `src/aiflow/pipeline/builtin_templates/` mappaban
- MINDEN step KOTELEZO: service + method (adapter registry-ben LETEZIK)
- for_each: CSAK Jinja2 expression ami list-et ad vissza
- condition: CSAK "output.field op value" formatum
- retry: KOTELEZO minden kulso service hivasra (LLM, email, HTTP)
- Jinja2 template-ekben NEM hasznalhato: __dunder__, callable, import

### Pipeline Testing Rules
- MINDEN pipeline YAML-hoz KOTELEZO teszt (tests/pipeline/test_{name}.py)
- Teszt: compile → validate → run with test data → check DB rows
- Cost tracking: MINDEN pipeline futtas KOTELEZO cost_records-ba logolni
- Smoke test: pipeline lista API 200 OK

### Adapter Development Rules
- Adapter = thin wrapper, NEM modositja az eredeti service-t
- Adapter file: src/aiflow/pipeline/adapters/{service}_adapter.py
- KOTELEZO: input_schema, output_schema (Pydantic), execute() method
- for_each: adapter belul kezeli asyncio.Semaphore-ral (concurrency limit)
- MINDEN adapter-hez unit test (tests/unit/pipeline/test_{service}_adapter.py)
```

---

## 5. MCP Kapcsolatok

### 5.1 Jelenlegi MCP-k

| MCP | Hasznalat | Allapot |
|-----|-----------|---------|
| **Figma MCP** (official HTTP) | UI design — frame letrehozas, auto-layout, PAGE_SPECS.md | Aktiv, `hq5dlkhu` channel |
| **Playwright MCP** | E2E teszteles — navigate, snapshot, click, screenshot | Aktiv |

### 5.2 Tervezett MCP bovitesek

| MCP | Cel | Mikor |
|-----|-----|-------|
| **Figma MCP** (meglevo) | Untitled UI komponens hasznalat a designban | Tier 1 Phase 5 |
| **Playwright MCP** (meglevo) | Pipeline UI E2E tesztek | Tier 1 Phase 5 |
| **PostgreSQL MCP** (uj, optional) | Kozvetlen DB lekerdezes debug-hoz | Ha szukseges |

> **Megjegyzes:** Nem szukseges tobb MCP — a jelenlegi Figma + Playwright lefedjak a UI tervezes + teszteles igenyeket. A backend teszteles curl + pytest-tel tortenik.

---

## 6. Permission Rules Bovites

### 6.1 Uj engedelyek (.claude/settings.local.json)

```json
{
  "permissions": {
    "allow": [
      // ... meglevo ...
      // Pipeline development
      "Bash(npx untitledui*)",           // Untitled UI CLI
      "Bash(curl -s*localhost:8102*)",    // API teszteles
      "Bash(curl -sf*localhost:8102*)",   // Silent API test
      "Bash(python -c*)",                // Python one-liners
      // Gotenberg (ha hozzaadjuk)
      "Bash(docker compose*gotenberg*)"
    ]
  }
}
```

---

## 7. Session Restart Prompt Frissites

A `.claude/commands/session-restart-prompt.md` frissitendo v1.2.0-ra:

```markdown
# AIFlow v1.2.0 Session Restart

## Allapot
- **v1.1.4 COMMITTED** (3 commit: session 4 + orchestration plan + detailed plans)
- **v1.2.0 TERVEZES KESZ** (48-56 plan documents)
- **Kovetkezo:** Tier 1 Phase 1 (Service Adapter Layer) implementacio

## Tervek
- Fo terv: `01_PLAN/48_ORCHESTRABLE_SERVICE_ARCHITECTURE.md`
- Reszletes: 49 (stability), 50 (RAG), 51 (doc extraction), 52 (HITL), 53 (frontend), 54 (LLM quality), 55 (Claude config), 56 (execution)

## Elso Teendo
1. `01_PLAN/56_EXECUTION_PLAN.md` — hol tartunk a vegrehajtasban?
2. Phase 1 implementacio inditas: adapter_base.py + 6 adapter
```

---

## 8. Fejlesztesi Ciklus Claude Code Hasznalat

### Tipikus fejlesztesi session:

```
1. Session inditas:
   → Olvasd el: 01_PLAN/56_EXECUTION_PLAN.md (hol tartunk?)
   → Olvasd el: a kovetkezo ciklus tervet
   
2. Implementacio:
   → /dev-step — fejlesztes + valos teszt + hard gates
   → Adapter/service irasa → unit test → curl API test
   
3. Validacio:
   → /regression — erintett tesztek PASS?
   → /service-test — vertikalis szelet E2E
   → /quality-check — LLM minoseg + koltseg
   
4. Lezaras:
   → git commit (conventional commits)
   → /update-plan — terv frissites (progress, szamok)
   → Session prompt frissites (kovetkezo session kontextus)
```
