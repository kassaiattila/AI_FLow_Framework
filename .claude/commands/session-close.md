---
name: session-close
description: KOTELEZO session lezaras — autonom validacio, commit, NEXT.md generalas (user kerdes nelkul ha minden PASS)
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

# Session Close — KÖTELEZŐ minden session végén

## Argumentum
$ARGUMENTS — Session azonosító (pl. "S44", "D0.1", "auto" ha az aktuális)

---

## AUTONOM DÖNTÉSI FOLYAMAT (ALAPÉRTELMEZETT)

> **A FOLYAMAT VÉGIGFUT USER KÉRDÉS NÉLKÜL, ha minden gate PASS és nincs STOP feltétel.**
> User csak akkor avatkozik közbe, ha:
>   - bármelyik validációs gate FAIL (és 2 próba után sem javítható), VAGY
>   - explicit STOP feltétel áll elő (lásd `STOP FELTÉTELEK` szekció)
>
> **NE kérdezz** "folytassam?", "commitoljam?", "generáljam a NEXT.md-t?" — egyszerűen csináld.

---

## FÁZIS 1: VALIDÁCIÓ (5 gate — BLOKKOLÓ)

Futtasd párhuzamosan ahol lehet. **Bármely FAIL → automatikus javítási kísérlet (max 2x), utána STOP.**

```bash
# Gate 1: Ruff lint (auto-fix elérhető)
.venv/Scripts/python.exe -m ruff check src/ tests/ --quiet && echo "PASS: lint" || { .venv/Scripts/python.exe -m ruff check src/ tests/ --fix --quiet; .venv/Scripts/python.exe -m ruff check src/ tests/ --quiet; }

# Gate 2: TypeScript (csak ha aiflow-admin/ érintett)
if git diff --cached --name-only HEAD 2>/dev/null | grep -q '^aiflow-admin/'; then
  cd aiflow-admin && npx tsc --noEmit && cd ..
fi

# Gate 3: Unit tesztek (BLOKKOLO)
.venv/Scripts/python.exe -m pytest tests/unit/ -x -q 2>&1 | tail -5

# Gate 4: E2E collect-only (szintaktikai)
.venv/Scripts/python.exe -m pytest tests/e2e/ --collect-only -q 2>&1 | tail -3

# Gate 5: Git status snapshot
git status --short

# Gate 6: Live E2E ha UI érintett (KÖTELEZŐ Playwright MCP futtatás)
UI_CHANGED=$(git diff --cached --name-only HEAD 2>/dev/null | grep -E '^aiflow-admin/src/(pages-new|components-new|layout)/' || true)
if [ -n "$UI_CHANGED" ]; then
  echo "UI változás — KÖTELEZŐ /live-test a modulokra:"
  echo "$UI_CHANGED" | sed -E 's|aiflow-admin/src/pages-new/([A-Z][a-z]+).*|  /live-test \L\1|;s|aiflow-admin/src/(components-new|layout)/.*||' | sort -u
  echo "Ha nem futtattad, ÁLLJ meg — running /live-test módon <modul>."
fi
```

**Gate értékelés:**
- MIND PASS → ugorj a FÁZIS 1b-re (commit), USER KÉRDÉS NÉLKÜL
- BÁRMELYIK FAIL → próbáld javítani (max 2 iteráció), ha még mindig FAIL → STOP, jelezz a usernek

---

## FÁZIS 1b: GIT COMMIT (autonom)

> **A `git commit` PreToolUse hook ujra futtatja a lint+unit teszteket — ha FAIL, blokkol.**
> Tehát biztonságos automatikusan futtatni.

```bash
# 1. Stage CSAK a session-ben módosított fájlok (SOHA git add -A!)
#    Olvasd ki a `git status --short`-ból a modositott / uj fajlokat es add hozzá:
git add <konkret_fajl_1> <konkret_fajl_2> ...

# TILOS: .env, credentials, *.key, *.pem, node_modules/, .venv/, __pycache__/

# 2. Conventional commit (HEREDOC formatban!)
git commit -m "$(cat <<'EOF'
<type>(<scope>): $ARGUMENTS — <rovid leiras>

- <reszlet 1>
- <reszlet 2>
- <reszlet 3>

Session: $ARGUMENTS | Sprint: <X> | Phase: <N>
Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"

# 3. Push (best-effort, offline OK)
git push 2>&1 | tail -3 || echo "WARN: push sikertelen (offline?) — manualis push kesobb"
```

**Commit típusok:** `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`

---

## FÁZIS 2: SESSION SUMMARY

Egy tömör blokk a usernek (NE kérdezz, csak írd ki):

```
=== SESSION SUMMARY ===
Session ID:    $ARGUMENTS
Sprint:        <azonosito>
Branch:        <git branch>
Duration:      ~N perc

Elvégezve:
- [x] feladat 1
- [x] feladat 2

Módosított fájlok:
- src/aiflow/... (N fájl)
- tests/... (N fájl)

Teszt státusz:
- Unit: N PASS / 0 FAIL
- Lint: PASS
- tsc: PASS / N/A

Git: <N> commit (HEAD: <hash>)
Alembic: migration <NNN> (ha új)
```

---

## FÁZIS 3: NEXT SESSION PROMPT GENERÁLÁS (autonom)

### 3.1 Kontextus gyűjtés (párhuzamosan)

```bash
git branch --show-current
git log --oneline -5
git diff --stat HEAD~1
.venv/Scripts/python.exe -m pytest tests/unit/ --collect-only -q 2>&1 | tail -1
.venv/Scripts/python.exe -m pytest tests/e2e/ --collect-only -q 2>&1 | tail -1
PYTHONPATH=src .venv/Scripts/python.exe -m alembic current 2>&1 | tail -1
```

### 3.2 Következő feladat meghatározás (autonom)

Olvasd el az aktuális sprint tervet (CLAUDE.md → `01_PLAN/106_*` vagy aktuális). Határozd meg:
- Mi a következő logikai session a tervben?
- Milyen fájlokat érint?
- Milyen előfeltételek vannak?

**Ne kérdezz a usertől** ha a terv egyértelmű. Ha a terv elágazik vagy döntés kell → **csak akkor** kérdezz.

### 3.3 Két fájl mentése (KÖTELEZŐ!)

```
session_prompts/S{N+1}_{next_task_id}_prompt.md   ← archív (sosem írod felül)
session_prompts/NEXT.md                            ← pointer (mindig felülíródik)
```

**Mindkét fájl AZONOS tartalommal.** A `/next` parancs a `NEXT.md`-t olvassa.

### 3.4 SABLON

```markdown
# AIFlow [Sprint X] — Session [N+1] Prompt ([next task ID])

> **Datum:** [YYYY-MM-DD]
> **Branch:** `[branch]`
> **HEAD:** `[hash]` ([rovid leiras])
> **Port:** API 8102 | Frontend 5174
> **Elozo session:** [jelen ID] — [mi készült el, 1-2 mondat]
> **Terv:** `01_PLAN/[terv].md` (Section [X])
> **Session tipus:** [IMPLEMENTATION / TESTING / HARDENING / KICKOFF]

---

## KONTEXTUS

### Honnan jöttünk
[2-3 sor — előző session eredménye]

### Hova tartunk
[Következő milestone, terv referencia]

### Jelenlegi állapot
```
[N] service | [M] endpoint | [K] DB tábla | [L] Alembic migration
[X] unit | [Y] E2E | [Z] skill | [W] UI oldal
```

---

## ELŐFELTÉTELEK

```bash
git branch --show-current        # Expected: [branch]
git log --oneline -3             # HEAD: [hash]
.venv/Scripts/python.exe -m pytest tests/unit/ -x -q       # [N]+ PASS
.venv/Scripts/python.exe -m ruff check src/ tests/         # 0 error
```

---

## FELADATOK

### LÉPÉS 1: [név]
```
Cél:    [mit elérni]
Fájlok: [érintett fájlok]
Forrás: [terv referencia]
```

### LÉPÉS 2: [név]
[...]

### LÉPÉS N: Validáció + commit
```bash
.venv/Scripts/python.exe -m ruff check src/[mod]/ tests/[mod]/
.venv/Scripts/python.exe -m pytest tests/unit/ -x -q
/session-close [next ID]
```

---

## STOP FELTÉTELEK

ÁLLJ MEG és kérj iránymutatást, ha:
- Architektúra döntés szükséges
- Külső függőség nem elérhető (LLM, DB, Redis nem indítható)
- Teszt FAIL amit 2 próba után sem sikerül javítani
- Scope >2x az eredeti becslés
- Security concern (PII, auth, injection)
- Schema breaking change (nem additive Alembic)

---

## SESSION VÉGÉN

```
/session-close [session ID]    ← autonom validacio + commit + NEXT.md
```
```

---

## FÁZIS 4: USER UTASÍTÁSOK (záró blokk)

Kiírod a usernek (ne kérdezz, csak közöld):

```
=== SESSION LEZÁRVA ===

Validáció:    PASS (lint, unit, tsc, e2e collect)
Commit:       <hash> "<rövid msg>"
Push:         <PASS / WARN: offline>

Következő session prompt:
  session_prompts/NEXT.md
  session_prompts/S{N+1}_{id}_prompt.md

Folytatás:
  /clear → /next
```

---

## STOP FELTÉTELEK (ekkor NE zárd le autonóman, kérdezz!)

User közbeavatkozás KELL, ha bármelyik:

1. **Lint FAIL** auto-fix után is (2 próba)
2. **Unit teszt FAIL** és nem triviális javítás
3. **TypeScript hiba** aiflow-admin/ módosításnál
4. **Alembic migration** új és nem futott `upgrade head` ellen
5. **Architektúra döntés** szükséges (új abstraction, contract change)
6. **Security concern** (új auth flow, PII handling, secret management)
7. **Scope drift** — a session jelentősen túlnőtt az eredeti tervezetten
8. **Külső dependency** hiányzik (LLM API down, Vault unreachable)
9. **Branch protection** — main/master érintett (sose commitolj rá direktben)
10. **Sprint-vége regresszió** szükséges és nem futott le sikeresen

Ezekben az esetekben:
```
=== SESSION NEM ZÁRHATÓ AUTONÓMAN ===
Ok: <konkrét leírás>
Szükséges user akció: <mit kérünk a usertől>
TILOS: automatikusan tovább lépni!
```
