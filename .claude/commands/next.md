---
name: next
description: Load and execute the next session from session_prompts/NEXT.md
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, Agent
---

# /next — Következő session betöltése és indítása

## Folyamat

### 1. NEXT.md BEOLVASÁS

Olvasd be a `session_prompts/NEXT.md` fájlt.

**Ha NEM létezik:**
```
⚠️ Nincs session_prompts/NEXT.md fájl.
Használd: /status — a projekt áttekintéshez
Vagy: hozz létre manuálisan egy session promptot
```
STOP — ne csinálj semmit.

### 2. KÖRNYEZET ELLENŐRZÉS

A NEXT.md "KÖRNYEZET ELLENŐRZÉS" szekciójából futtasd az ellenőrző parancsokat:

```bash
# Mindig:
git branch --show-current
git log --oneline -3
git status --short
```

Ellenőrizd a session prompt "Előfeltételek" szekciójának minden pontját:
- Fájlok léteznek?
- Branch stimmel?
- Alembic migration rendben?
- Szükséges szolgáltatások futnak?

**Ha bármelyik HIÁNYZIK:** Kérdezd meg a usert: "Javítsam most, vagy ez a session feladata?"

### 3. SESSION INDÍTÁS

Kövesd a NEXT.md "FELADATOK" szekciójának lépéseit:
- Tartsd be a CLAUDE.md konvenciókat
- Tartsd be az aktív skill-ek szabályait
- Ha STOP FELTÉTEL lép fel → ÁLLJ meg, kérj iránymutatást

### 4. SESSION VÉGE

Amikor MINDEN elfogadási kritérium teljesül:
```
Futtasd: /session-close [session azonosító]
```

Ez automatikusan generálja a session_prompts/NEXT.md-t a következő session-höz.

```
Felhasználó: /clear → /next → folytatás
```
