---
name: session-close
description: KOTELEZO session lezaras — validacio, commit, kovetkezo session prompt generalas
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

# Session Close — KÖTELEZŐ minden session végén

## Argumentum
$ARGUMENTS — Session azonosító (pl. "S44", "D0.1")

---

## FÁZIS 1: VALIDÁCIÓ (5 gate — BLOKKOLÓ)

Futtasd sorban. **Ha BÁRMELY gate FAIL → NE zárd le a session-t! Javítsd először.**

```bash
# Gate 1: Ruff lint
python -m ruff check src/ tests/

# Gate 2: TypeScript (ha UI változás volt)
cd aiflow-admin && npx tsc --noEmit

# Gate 3: Unit tesztek
python -m pytest tests/unit/ -x -q

# Gate 4: E2E collect-only (szintaktikai ellenőrzés)
python -m pytest tests/e2e/ --collect-only -q

# Gate 5: Git status — nincs staged credentials
git status
```

---

## FÁZIS 1b: GIT COMMIT (kötelező)

```bash
# Stage CSAK a módosított fájlokat (SOHA NEM git add -A!)
git add src/<affected> tests/<affected> [egyéb érintett fájlok]

# Conventional commit + session ID
git commit -m "feat/fix/refactor(<scope>): $ARGUMENTS — [rövid leírás]

- [részlet 1]
- [részlet 2]
- [részlet 3]

Session: $ARGUMENTS | Sprint: [X] | Phase: [N]
Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## FÁZIS 2: SESSION SUMMARY

Írj egy tömör összefoglalót a usernek:

```
=== SESSION SUMMARY ===
Session ID:    $ARGUMENTS
Sprint:        [sprint azonosító]
Branch:        [git branch]
Duration:      ~N perc

Elvégezve:
- [x] feladat 1
- [x] feladat 2

Módosított fájlok:
- src/aiflow/... (N fájl)
- tests/... (N fájl)

Teszt státusz:
- Unit: N PASS / M FAIL
- Lint: PASS/FAIL
- tsc: PASS/FAIL

Git: N commit (HEAD: [hash])
Alembic: migration NNN (ha új)
```

---

## FÁZIS 3: NEXT SESSION PROMPT GENERÁLÁS (KRITIKUS!)

### 3.1 Kontextus gyűjtés

Olvasd be a következő információkat:

```bash
# Git állapot
git branch --show-current
git log --oneline -5
git diff --stat HEAD~1

# Teszt számok
python -m pytest tests/unit/ --collect-only -q 2>&1 | tail -1
python -m pytest tests/e2e/ --collect-only -q 2>&1 | tail -1

# Alembic
PYTHONPATH=src alembic current 2>&1 | tail -1

# Aktuális terv — a következő feladat meghatározásához
# Olvasd el az aktuális sprint plan-t a CLAUDE.md-ből
```

### 3.2 Következő feladat meghatározás

Olvasd el az aktuális sprint/phase terv dokumentumot (CLAUDE.md-ben hivatkozott), és határozd meg:
- Mi a KÖVETKEZŐ logikai lépés a tervben?
- Milyen fájlokat kell majd érinteni?
- Milyen előfeltételek vannak?

### 3.3 Session prompt generálás — KÉT MÁSOLAT

**SABLON:**

```markdown
# AIFlow [Sprint X] — Session [N+1] Prompt ([next task ID])

> **Datum:** [YYYY-MM-DD]
> **Branch:** `[jelenlegi branch]`
> **HEAD:** `[commit hash]`
> **Port:** API 8102 (dev), Frontend 5174 (dev)
> **Elozo session:** [jelen session] — [mi készült el, 1-2 mondat]
> **Terv:** `01_PLAN/[aktualis terv].md` (Section [X])
> **Session tipus:** [IMPLEMENTATION / TESTING / HARDENING / KICKOFF]
> **Workflow:** [fő lépések felsorolása]

---

## KONTEXTUS

### Honnan jöttünk
[Sprint és session összefoglaló — mi készült el eddig]

### Hova tartunk
[Mi a következő milestone, terv referencia]

### Jelenlegi állapot
```
[szolgáltatás számok] service | [endpoint számok] endpoint | [tábla számok] DB tábla | [migration számok] Alembic migration
[unit teszt] unit test | [e2e teszt] E2E | [skill számok] skill | [ui oldal] UI oldal
```

---

## ELŐFELTÉTELEK (ELLENŐRIZNI ELŐSZÖR!)

```bash
# Branch ellenőrzés
git branch --show-current  # Expected: [branch]
git log --oneline -3       # Expected: HEAD = [hash]

# Baseline smoke
python -m pytest tests/unit/ -x -q          # [N]+ PASS
python -m ruff check src/ tests/             # 0 error
cd aiflow-admin && npx tsc --noEmit          # 0 error
```

---

## FELADATOK

### LÉPÉS 1: [Első feladat neve]
```
Cél: [mit kell elérni]
Fájlok: [érintett fájlok listája]
Forrás: [terv dokumentum referencia]
```

### LÉPÉS 2: [Második feladat neve]
[...]

### LÉPÉS N: Lint + Regresszió + Commit
```bash
python -m ruff check src/[érintett]/ tests/[érintett]/
python -m pytest tests/unit/ -x -q
```

---

## KÓD REFERENCIÁK

```
# OLVASD! — Ezeket a dokumentumokat KELL elolvasni:
01_PLAN/[terv dokumentum]    — Section [X]
src/aiflow/[modul]/          — [leírás]
```

---

## STOP FELTÉTELEK

Ha BÁRMELYIK bekövetkezik → ÁLLJ meg és kérj iránymutatást:
- Architektúra döntés szükséges (→ `/review` előbb)
- Külső függőség hiányzik vagy nem elérhető
- Teszt FAIL amit 2 próba után sem sikerül javítani
- Scope jelentősen nőtt a tervhez képest
- Security concern (PII, auth, injection)

---

## SESSION VÉGÉN

```
1. /session-close [session ID]    — validáció + commit + NEXT.md generálás
```

---

*[Sprint azonosító] session: S[N+1] = [task ID]*
```

### 3.4 Fájl mentés (KÉT MÁSOLAT!)

```bash
# 1. Archív másolat (session ID-vel a fájlnévben, SOHA nem íródik felül)
write "session_prompts/S{next_session_num}_{next_id}_prompt.md"

# 2. Aktív pointer (MINDIG felülíródik — /next ezt olvassa!)
write "session_prompts/NEXT.md"
```

**KRITIKUS:** A `session_prompts/NEXT.md` a session pointer. A `/next` parancs EZT olvassa be.
Mindkét fájl AZONOS tartalommal.

---

## FÁZIS 4: USER UTASÍTÁSOK

```
=== SESSION LEZÁRVA ===

Következő session prompt generálva:
  session_prompts/NEXT.md
  session_prompts/S{N+1}_{id}_prompt.md

Következő lépések:
  1. /clear                    ← kontextus törlés
  2. /next                     ← új session AUTOMATIKUSAN indul!

Vagy ha döntés/hiba miatt meg kell állni:
  → Olvasd el: session_prompts/NEXT.md
  → Adj iránymutatást mielőtt /next-et futtatod!
```

---

## STOP FELTÉTELEK (NE zárd le a session-t!)

- Architektúra döntés szükséges (→ `/review` előbb)
- Lint FAIL (2 próba után sem javítható)
- Security concern (PII, auth, injection)
- Scope jelentősen nőtt (→ tervezés kell)
- Külső függőség hiányzik
