---
name: session-close
description: KOTELEZO session lezaras — validacio, commit, kovetkezo session prompt generalas
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

# Session Close — KOTELEZO minden session vegen

## Argumentum
$ARGUMENTS — Session azonosito (pl. "S44", "D0.1")

## Folyamat

### 1. VALIDACIO (5 gate)

```bash
# Gate 1: Ruff lint
python -m ruff check src/ tests/

# Gate 2: TypeScript (ha UI valtozas)
cd aiflow-admin && npx tsc --noEmit

# Gate 3: Unit tesztek
python -m pytest tests/unit/ -x -q

# Gate 4: E2E collect-only (szintaktikai ellenorzes)
python -m pytest tests/e2e/ --collect-only -q

# Gate 5: Git status — nincs staged credentials
git status
```

**Ha BARMELY gate FAIL:** NE zarj le a session-t! Javitsd elobb.

### 2. COMMIT

```bash
git add [valtoztatott fajlok — NEM git add -A!]
git commit -m "feat/fix/refactor: Sprint X $ARGUMENTS — [rovid leiras]

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

### 3. KOVETKEZO SESSION PROMPT

Generald a kovetkezo session promptot `01_PLAN/session_{next_num}_{next_id}_{topic}.md` formatumban:

```markdown
# AIFlow Sprint [X] — Session [N+1] Prompt ([next task ID])

> **Datum:** [mai datum]
> **Branch:** `[jelenlegi branch]` | **HEAD:** `[uj commit hash]`
> **Elozo session:** [jelen session] — [mi keszult el]
> **Terv:** `01_PLAN/[aktualis terv].md`

## KONTEXTUS
[Mi keszult el eddig, mi a kovetkezo lepes]

## FELADATOK
[Reszletes lepesek a kovetkezo session-hoz]

## KORNYEZET ELLENORZES
[Bash parancsok a kezdoallapot ellenorzesere]
```

### 4. OUTPUT

Mondd a usernek:
```
Session $ARGUMENTS LEZARVA.
Commit: [hash]
Kovetkezo session prompt: 01_PLAN/session_[N+1]_[id].md

Kovetkezo alkalommal:
1. /clear
2. Told be a session promptot
```

## STOP FELTETELEK (NE zard le a session-t!)

- Architektura dontes szukseges (→ `/review` elobb)
- Lint FAIL (2 proba utan sem javithato)
- Security concern (PII, auth, injection)
- Scope jelentosen nott (→ tervezes kell)
- Kulso fuggoseg hianyzik
