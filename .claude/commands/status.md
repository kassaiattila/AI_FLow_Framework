---
name: status
description: Projekt status osszefoglalo — git, tesztek, migraciok, sprint allapot
allowed-tools: Bash, Read, Grep, Glob
---

# Project Status

## Folyamat

### 1. Git allapot
```bash
git branch --show-current
git log --oneline -5
git status --short
git stash list
```

### 2. Teszt szamok
```bash
# Unit
python -m pytest tests/unit/ --collect-only -q 2>&1 | tail -1

# E2E
python -m pytest tests/e2e/ --collect-only -q 2>&1 | tail -1

# Journey
python -m pytest tests/e2e/test_journey_*.py --collect-only -q 2>&1 | tail -1
```

### 3. Alembic migracio
```bash
PYTHONPATH=src .venv/Scripts/python -m alembic current 2>&1 | tail -3
PYTHONPATH=src .venv/Scripts/python -m alembic heads 2>&1 | tail -3
```

### 4. Service allapot
```bash
# Docker services
docker ps --format "table {{.Names}}\t{{.Status}}" 2>&1 | head -10

# API health
curl -s http://localhost:8102/health 2>&1

# Frontend
curl -s -o /dev/null -w "%{http_code}" http://localhost:5174 2>&1
```

### 5. Version
```bash
grep 'version' pyproject.toml | head -1
```

### 6. Meglevo sprint tervek
```bash
ls -la 01_PLAN/session_*.md 2>&1 | tail -5
```

## Output

```
## AIFlow Project Status

| Metric | Value |
|--------|-------|
| Branch | ... |
| Version | ... |
| HEAD | ... |
| Uncommitted | ... |
| Unit tests | ... collected |
| E2E tests | ... collected |
| Journey tests | ... collected |
| Alembic | ... |
| Docker services | ... running |
| API health | ready/down |
| Frontend | up/down |

### Recent Commits
[5 legutobbi commit]

### Recommendation
[Mi a kovetkezo lepes: /implement, /review, /session-close, stb.]
```
