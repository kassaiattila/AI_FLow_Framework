# AIFlow - Git Kezelesi Szabalyok

## 1. Branching Strategia

```
main                              # MINDIG deployolhato. Vedett branch.
  |                               # PR + review + CI zold KOTELEZO merge-hoz
  |
  +-- feature/AIFLOW-{ticket}-{leiras}     # Framework fejlesztes
  |   Pelda: feature/AIFLOW-42-add-retry-policy
  |
  +-- skill/{skill-nev}/{leiras}           # Skill fejlesztes
  |   Pelda: skill/process-doc/add-quality-gate
  |
  +-- prompt/{skill-nev}/{leiras}          # Prompt-only valtozas
  |   Pelda: prompt/aszf-rag/improve-classifier-v6
  |
  +-- fix/{ticket-vagy-leiras}             # Bug fix
  |   Pelda: fix/AIFLOW-55-retry-backoff-overflow
  |
  +-- hotfix/{leiras}                      # Production hotfix (bypass release train)
      Pelda: hotfix/circuit-breaker-redis-timeout

# NEM hasznalunk:
# - release/* branch-eket (continuous deploy skill-ekre)
# - develop branch-et (main = develop, nincs kulon)
```

## 2. CODEOWNERS

```
# .github/CODEOWNERS
/src/aiflow/              @bestixcom/framework-team
/src/aiflow/ui/           @bestixcom/frontend-team
/skills/process_documentation/  @bestixcom/process-doc-team
/skills/aszf_rag_chat/         @bestixcom/legal-tech-team
/skills/email_intent_processor/ @bestixcom/customer-service-team
/k8s/                     @bestixcom/devops-team
/.github/                 @bestixcom/devops-team
/01_PLAN/                 @bestixcom/framework-team
```

## 3. Commit Konvenciok

### Conventional Commits (kotelezo)

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
Co-Authored-By: Claude Code <noreply@anthropic.com>
```

### Tipusok

| Tipus | Mikor | Pelda |
|-------|-------|-------|
| feat | Uj funkcionalitas | `feat(engine): add DAG topological sort` |
| fix | Hibajavitas | `fix(retry): handle timeout in backoff calculation` |
| refactor | Kod atszervezes (nem uj feature, nem fix) | `refactor(agents): extract quality gate logic` |
| test | Teszt hozzaadas/javitas | `test(classifier): add 50 edge case test` |
| docs | Dokumentacio | `docs(plan): update master plan with ML integration` |
| chore | Build, CI, dependency | `chore(deps): update litellm to 1.45` |
| prompt | Prompt valtozas | `prompt(aszf/classifier): improve Hungarian date handling` |
| skill | Skill-specifikus | `skill(email-intent): add order extraction agent` |

### Scope-ok

| Scope | Mire vonatkozik |
|-------|-----------------|
| engine | src/aiflow/engine/ |
| agents | src/aiflow/agents/ |
| prompts | src/aiflow/prompts/ |
| api | src/aiflow/api/ |
| cli | src/aiflow/cli/ |
| state | src/aiflow/state/ |
| models | src/aiflow/models/ |
| vectorstore | src/aiflow/vectorstore/ |
| security | src/aiflow/security/ |
| ui | src/aiflow/ui/ |
| skill-name | skills/<nev>/ |

### Szabalyok
- **MINDEN commit** Conventional Commits formatumu (pre-commit hook ellenorzi)
- **Claude Code Co-Author** jeloles ha AI segitseg volt
- **Referenciak:** `Refs: AIFLOW-42` vagy `Closes: AIFLOW-42` a footer-ben
- **Breaking change:** `feat(engine)!: change Step decorator signature` (! jel)
  + `BREAKING CHANGE: @step now requires output_types parameter` a body-ban

## 4. PR Szabalyok

### PR Cim
Ugyan Conventional Commits formatumban: `feat(engine): add retry policy with jitter`

### PR Template

```markdown
## Summary
<!-- 1-3 bullet pont mit csinal ez a PR -->

## Type
- [ ] Framework change (src/aiflow/)
- [ ] Skill change (skills/)
- [ ] Prompt change (prompts only)
- [ ] Bug fix
- [ ] Documentation

## Checklist
- [ ] Unit tesztek irva/frissitve
- [ ] Integration tesztek (ha API/DB valtozas)
- [ ] Promptfoo tesztek (ha prompt valtozas)
- [ ] Dokumentacio frissitve (ha publikus API valtozas)
- [ ] CLAUDE.md frissitve (ha uj konvencio vagy pattern)
- [ ] Nincs .env, credentials, API key a commitban

## Test plan
<!-- Hogyan teszteled? Mi a teszt parancs? -->
```

### Review Szabalyok
- **Framework PR:** Min 1 framework-team review
- **Skill PR:** Min 1 skill-team review
- **Prompt PR:** Promptfoo CI zold KOTELEZO
- **Hotfix PR:** 1 review barkitol + manualis merge jovahagyas
- **CI MUST pass** minden PR-nal (lint + tesztek + skill compat)

## 5. Branch Protection (main)

```yaml
# Ezek KOTELESEK merge elott:
require_pull_request: true
required_reviews: 1
require_status_checks:
  - lint                    # ruff + black + mypy
  - unit-tests              # pytest tests/unit/
  - integration-tests       # pytest tests/integration/ (ha releváns)
  - skill-compat            # Framework PR: MINDEN skill tesztje
  - promptfoo               # Prompt PR: promptfoo eval
require_linear_history: true  # Squash merge
dismiss_stale_reviews: true
require_conversation_resolution: true
```

## 6. Merge Strategia

- **Squash merge** az alapertelmezett (tiszta main history)
- Minden PR -> egyetlen commit main-re
- A squash commit uzenet = PR cim (Conventional Commits)
- **NEM** rebase merge (bonyolult history)
- **NEM** merge commit (zajos history)

## 7. Tag-eles es Release

### Framework Release
```bash
# Havi release train (elso hetfo)
git tag -a v1.2.0 -m "Release v1.2.0: retry policies, checkpoint support"
git push origin v1.2.0
# -> CI/CD deploy-staging pipeline triggerelodik
```

### Skill Release
```bash
# Continuous - PR merge utan
git tag -a skill/process-doc/v2.1.0 -m "Skill: process-doc v2.1.0"
git push origin skill/process-doc/v2.1.0
# -> CI/CD deploy pipeline triggerelodik
```

### Tag Konvencio
- Framework: `v{major}.{minor}.{patch}` (pl. `v1.2.0`)
- Skill: `skill/{nev}/v{major}.{minor}.{patch}` (pl. `skill/process-doc/v2.1.0`)
- Hotfix: `v{major}.{minor}.{patch+1}` (pl. `v1.2.1`)

## 8. .gitignore Szabalyok

```gitignore
# Secrets - SOHA ne commitoljuk
.env
.env.*
!.env.example
**/credentials.json
**/secrets.yaml

# Python
__pycache__/
*.pyc
.venv/
*.egg-info/

# IDE
.vscode/
.idea/
*.swp

# Build
dist/
build/
node_modules/        # Frontend (Next.js esetben)
.next/

# Data
data/
outputs/
test_runs/
*.sqlite

# OS
.DS_Store
Thumbs.db
```

## 9. Pre-Commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: conventional-commits
        name: Conventional Commits check
        entry: python scripts/check_commit_msg.py
        language: python
        stages: [commit-msg]

      - id: no-secrets
        name: Check for secrets
        entry: detect-secrets-hook
        language: python
        stages: [commit]

      - id: ruff-check
        name: Ruff lint
        entry: ruff check --fix
        language: python
        types: [python]

      - id: ruff-format
        name: Ruff format
        entry: ruff format
        language: python
        types: [python]

      - id: mypy
        name: Type check
        entry: mypy src/aiflow/
        language: python
        types: [python]
        pass_filenames: false
```

## 10. Claude Code Git Hasznalat

### Commit Keszites
```
User: "Commitold a valtozasokat"
Claude Code:
1. git status -> attekintes
2. git diff -> valtozas elemzes
3. Conventional Commit uzenet generalas (feat/fix/test/...)
4. Co-Authored-By header hozzaadasa
5. Specifikus fajlok stage-elese (NEM git add -A!)
6. Commit
```

### PR Keszites
```
User: "Keszits PR-t"
Claude Code:
1. git log main..HEAD -> commit-ok attekintese
2. PR template kitoltese (summary, type, checklist)
3. gh pr create --title "..." --body "..."
4. Reviewer javaslat CODEOWNERS alapjan
```

### TILOS Muveletek (Claude Code NEM csinalja jovahagyas nelkul)
- `git push --force` (soha main-re!)
- `git reset --hard`
- `git checkout .` (uncommitted valtozasok elvesznek)
- `git branch -D` (branch torles)
- `git rebase -i` (interactive rebase)
- Commit `.env` vagy credentials fajlt
