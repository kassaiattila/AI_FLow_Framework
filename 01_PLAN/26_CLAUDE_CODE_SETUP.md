# AIFlow - Claude Code Fejlesztesi Kornyezet Konfiguracio

## 1. Fajl Terkep

```
aiflow/                                    # Projekt root
|
|-- CLAUDE.md                              # FO KONTEXTUS - Claude Code mindig beolvassa
|                                          # Tartalom: architektura, tech stack, coding conventions,
|                                          # MANDATORY testing rules, git conventions, plan reference
|
|-- .claude/
|   |-- settings.local.json                # Jogosultsagi beallitasok (allow/deny patterns)
|   |-- commands/                          # Egyedi slash commands
|       |-- new-step.md                    # /new-step - Uj Step generalas
|       |-- new-skill.md                   # /new-skill - Uj Skill scaffold
|       |-- new-test.md                    # /new-test - Teszt generalas forrasfajlhoz
|       |-- new-prompt.md                  # /new-prompt - Prompt YAML generalas
|       |-- new-module.md                  # /new-module - Uj framework modul
|       |-- regression.md                  # /regression - Regresszios teszt futtatas
|       |-- dev-step.md                    # /dev-step - Fejlesztesi lepes lezarasa
|       |-- phase-status.md               # /phase-status - Fazis elorehaldas
|       |-- validate-plan.md              # /validate-plan - Terv validacio
|
|-- 01_PLAN/
|   |-- CLAUDE.md                          # PLAN KONTEXTUS - amikor a 01_PLAN/-ban dolgozunk
|
|-- src/aiflow/                            # (letrehozando Phase 1-ben)
|   |-- CLAUDE.md                          # FRAMEWORK KONTEXTUS (Phase 1-ben letrehozni!)
|
|-- skills/                                # (letrehozando Phase 4-ben)
|   |-- CLAUDE.md                          # SKILL KONTEXTUS (Phase 4-ben letrehozni!)
|
|-- tests/                                 # (letrehozando Phase 1-ben)
    |-- CLAUDE.md                          # TEST KONTEXTUS (Phase 1-ben letrehozni!)
```

---

## 2. Slash Commands Reszletes Leirasa

### /new-step
**Mikor:** Uj Step hozzaadasa egy workflow-hoz
**Mit csinal:** Generálja a step fuggvenyt (@step decorator), Pydantic I/O modelleket, teszteket, es opcionálisan prompt YAML-t
**Output:** 2-3 fajl (step.py, test_step.py, opcionálisan prompt.yaml)

### /new-skill
**Mikor:** Teljesen uj Skill inditas
**Mit csinal:** Teljes skill konyvtar scaffold (skill.yaml, workflow.py, agents/, models/, prompts/, tests/)
**Output:** 15-20 fajl a skill konyvtar-strukturaval

### /new-test
**Mikor:** Meglevo kodhoz teszteket kell irni
**Mit csinal:** Beolvassa a forrasfajlt, azonositja a publikus API-t, general teszteket @test_registry fejleccel
**Output:** 1 teszt fajl minimum 5 teszttel

### /new-prompt
**Mikor:** Uj LLM prompt kell egy skill-hez
**Mit csinal:** Prompt YAML + Promptfoo teszt esetek generalasa
**Output:** 1 prompt YAML + promptfooconfig.yaml bovites

### /new-module
**Mikor:** Uj framework modul (src/aiflow/**/*.py)
**Mit csinal:** Modul fajl + teszt fajl + test_suites.yaml es regression_matrix.yaml frissites
**Output:** 2 fajl + 2 YAML frissites

### /regression
**Mikor:** MINDIG, commit elott (KOTELEZO!)
**Mit csinal:** Git diff -> regression_matrix.yaml -> erintett suite-ok futtatasa -> eredmeny riport
**Output:** Konzol riport (pass/fail tabla, coverage)

### /dev-step
**Mikor:** Egy fejlesztesi lepes befejezese utan, commit ELOTT
**Mit csinal:** Azonositja a valtozasokat, futtat regressziot, general dev step record-ot, javasolja a commit uzenetet
**Output:** Dev step riport + commit javaslat

### /phase-status
**Mikor:** Fazis elorehaldas ellenorzese
**Mit csinal:** Osszeveti a fazis feladatlistat a letezo fajlokkal/tesztekkel
**Output:** Statusz tabla (letezik/hianyzik, teszt szam, coverage)

### /validate-plan
**Mikor:** Terv dokumentumok modositasa utan
**Mit csinal:** Kereszthivatkozas konzisztencia, DB tabla nevek, phase szamok, API endpointok ellenorzese
**Output:** Validacios riport (CRITICAL/HIGH/MEDIUM/LOW talaltok)

---

## 3. Sub-Directory CLAUDE.md Tartalmak (Letrehozando)

### src/aiflow/CLAUDE.md (Phase 1-ben letrehozni)

```markdown
# AIFlow Framework Source Code

## Module Map
- core/ - Kernel (config, context, errors, events, DI)
- engine/ - Workflow execution (step, dag, workflow, runner)
- agents/ - 2-level agent system
- models/ - ML model abstraction (LLM, embedding, classify)
- prompts/ - Langfuse SSOT prompt management
- execution/ - Async queue (arq), worker, scheduler
- state/ - PostgreSQL ORM, Alembic migrations
- ...

## Rules
- Every public function MUST have type annotations
- Every module MUST have __all__ exports
- Use structlog: `logger = structlog.get_logger(__name__)`
- Errors MUST subclass AIFlowError
- I/O operations MUST be async
- Config via DI (never import settings directly in business logic)
```

### skills/CLAUDE.md (Phase 4-ben letrehozni)

```markdown
# AIFlow Skills Directory

## Skill Structure
Every skill MUST have: skill.yaml, workflow.py, agents/, prompts/, tests/
See: 01_PLAN/SKILL_DEVELOPMENT.md for complete guide.

## Rules
- Max 6 specialist agents per skill
- All agents MUST be stateless
- Prompts in YAML only (never hardcode in Python)
- Minimum 100 test cases per skill
- @test_registry header on every test file
- skill.yaml MUST include framework_requires
```

### tests/CLAUDE.md (Phase 1-ben letrehozni)

```markdown
# AIFlow Test Suite

## Test Types
- tests/unit/ - Mock-based, no external services, <30s
- tests/integration/ - Real PostgreSQL + Redis (testcontainers), 2-5 min
- tests/e2e/ - Full pipeline, all services running
- tests/ui/ - Playwright GUI tests (Page Object Model)
- skills/*/tests/ - Per-skill tests + Promptfoo

## MANDATORY Rules
- @test_registry header on EVERY test file
- Regression MUST run before every commit (/regression command)
- Coverage MUST NOT decrease (80% global minimum)
- Flaky tests -> quarantine, fix within 5 days
- Full details: 01_PLAN/24_TESTING_REGRESSION_STRATEGY.md

## Key Files
- tests/conftest.py - Global fixtures (mock_ctx, mock_llm)
- tests/test_suites.yaml - Suite definitions
- tests/regression_matrix.yaml - Change -> suite mapping
- tests/artifacts/ - Saved test run results (gitignored)
```

---

## 4. Hooks (Jovobeli Bovites)

A Claude Code hooks rendszere a `.claude/hooks/` mappaban konfiguralhato.
AIFlow-ban tervezett hook-ok:

### Pre-Commit Hook Terv
```yaml
# .claude/hooks/pre-commit.yaml (jovobeli)
trigger: before_commit
actions:
  - validate_test_registry    # Minden teszt fajlnak van @test_registry?
  - check_coverage_gate       # Coverage nem csokken?
  - check_no_secrets          # Nincs .env, API key?
  - conventional_commit_check # Commit uzenet formatuma helyes?
```

### Post-Edit Hook Terv
```yaml
# .claude/hooks/post-edit.yaml (jovobeli)
trigger: after_file_edit
conditions:
  - file_pattern: "src/aiflow/**/*.py"
actions:
  - remind: "Don't forget to run /regression before committing!"
  - remind: "New code needs tests. Use /new-test if needed."
```

**Megjegyzes:** Ezek meg nem implementaltak, a Claude Code hooks
feature fejlodeset kovetjuk. Addig a slash commands es CLAUDE.md
szabalyok biztositjak a workflow-t.

---

## 5. MCP Server Integracio (Phase 5+)

Az AIFlow API sajat MCP server-kent is elerheto lesz:

```json
// .mcp.json (Phase 5-ben letrehozni, amikor az API mukodik)
{
  "mcpServers": {
    "aiflow": {
      "command": "python",
      "args": ["-m", "aiflow.contrib.mcp_server"],
      "env": {
        "AIFLOW_API_URL": "http://localhost:8000",
        "AIFLOW_API_KEY": "${AIFLOW_DEV_API_KEY}"
      }
    }
  }
}
```

**Elerheto MCP tool-ok (Phase 5+ utan):**
- `aiflow_workflow_list` - Workflow-k listazasa
- `aiflow_workflow_run` - Workflow futtatás
- `aiflow_job_status` - Job statusz
- `aiflow_skill_list` - Skill-ek listazasa
- `aiflow_eval_run` - Evaluation futtatás
- `aiflow_cost_report` - Koltseg riport

---

## 6. IDE Integracio (.vscode/) (Phase 1-ben letrehozni)

```json
// .vscode/settings.json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/Scripts/python.exe",
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests/"],
  "editor.formatOnSave": true,
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.codeActionsOnSave": {
      "source.fixAll.ruff": "explicit",
      "source.organizeImports.ruff": "explicit"
    }
  },
  "files.exclude": {
    "**/__pycache__": true,
    "**/*.pyc": true,
    "tests/artifacts": true
  }
}
```

```json
// .vscode/extensions.json
{
  "recommendations": [
    "charliermarsh.ruff",
    "ms-python.python",
    "ms-python.mypy-type-checker",
    "ms-toolsai.jupyter",
    "redhat.vscode-yaml",
    "ms-azuretools.vscode-docker"
  ]
}
```

---

## 7. Implementacios Sorrend

| Mikor | Mit letrehozni |
|-------|---------------|
| **MOST (tervezes)** | CLAUDE.md (KESZ), .claude/commands/ (KESZ), 01_PLAN/CLAUDE.md (KESZ) |
| **Phase 1, Het 1** | src/aiflow/CLAUDE.md, tests/CLAUDE.md, .vscode/, .editorconfig |
| **Phase 4, Het 10** | skills/CLAUDE.md |
| **Phase 5, Het 15** | .mcp.json (AIFlow MCP server) |
| **Folyamatosan** | Uj /commands ha ismetlodo feladatok merulnek fel |
