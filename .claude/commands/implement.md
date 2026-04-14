---
name: implement
description: 5-fazisu feature implementacio — discover, plan, code, test, summarize
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

# Implement — 5 fazisu feature fejlesztes

## Argumentum
$ARGUMENTS — Feature leiras (pl. "intake package upload endpoint", "HITL bulk review UI")

## 5 Fazis

### Fazis 1: DISCOVER (felterkepez)
1. Olvasd el a relevas terveket (01_PLAN/10X_*.md, 65_*.md)
2. Azonositsd az erintett fajlokat (service, API, UI, test)
3. Ellenorizd: van-e mar reszleges implementacio?
4. Listazd a fuggosegeket (DB migration, uj endpoint, UI oldal)

### Fazis 2: PLAN (tervez)
1. Hatarozd meg a lepesek sorrendjet
2. DB migration kell? → Alembic eloszor (aiflow-database skill)
3. Uj API endpoint kell? → Backend eloszor
4. UI valtozas kell? → 7 HARD GATE pipeline (aiflow-ui-pipeline skill)
5. Feature flag szukseges? → `AIFLOW_FEATURE_*` env var

### Fazis 3: CODE (implemental)
1. Irj kodot a terv szerint
2. Kovetsd a service architecture-t (aiflow-services skill)
3. Minden I/O async
4. Pydantic modellek a data layer-en
5. structlog minden logolashoz

### Fazis 4: TEST (tesztel)
1. Unit tesztek (min. 5 per modul, 70%+ coverage)
2. Integration teszt (valos DB, valos Redis)
3. API teszt (curl, source: "backend" ellenorzes)
4. E2E teszt (ha UI valtozas — Playwright)
5. Prompt teszt (ha LLM hivas — Promptfoo)
6. **SOHA ne mock/fake!** (aiflow-testing skill)

### Fazis 5: SUMMARIZE (osszegez)
1. Listazd a modositott fajlokat
2. Futtasd a lint + type check-et
3. Futtasd az erintett teszteket
4. Keszitsd elo a commit uzenetet

## Output

```
## Implement: $ARGUMENTS

### Modositott fajlok
| Fajl | Tipus | Valtozas |
|------|-------|---------|

### Tesztek
| Suite | Count | Status |
|-------|-------|--------|

### Kovetkezo lepes
[Mi kell meg, ha van]
```

## FONTOS
- Ha architektura dontes kell → `/review` elobb
- Ha UI kell → 7 HARD GATE pipeline (SOHA ne ugord at!)
- Ha DB schema kell → Alembic migration ELOSZOR
- Egy session = egy feature (ne keverd!)
