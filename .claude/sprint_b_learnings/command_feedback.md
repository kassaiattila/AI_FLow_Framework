# Sprint B — Command Feedback Log

> Minden session vegen: melyik command-ot hivtuk, hogyan teljesitett.
> Ha FAIL vagy PARTIAL → azonnali javitas a command fajlban.

## Formatum

```
## /command-nev — Session SXX, B-fazis
Hivva: YYYY-MM-DD, kontextus
Eredmeny: PASS / PARTIAL / FAIL
Problema: (ha nem PASS) Mi nem mukodott
Javitas: (ha szukseges) Mit valtoztattunk
Tanulsag: Amit a jovo session-okban figyelembe kell venni
```

---

## Session 20 (B0 — Sprint B Kickoff)

### /dev-step — S20, B0
Hivva: 2026-04-04, B0 foundations (5-layer arch, qbpp delete, prompt API, OpenAPI)
Eredmeny: NEM HASZNALVA (inline vegezve)
Problema: A munka command hivatkozas nelkul, inline tortent
Tanulsag: Kovetkezo session-ben (S21) TENYLEGESEN kell meghivni

### PostToolUse hook (ruff auto-lint) — S20
Hivva: 2026-04-04, automatikus — prompts.py irasanal triggerelt
Eredmeny: PASS — automatikusan lefutott, lint hibakat azonnal javitotta
Tanulsag: Determinisztikus, megbizhato. Nincs teendo.

### PreToolUse hook (.env deny) — S20
Hivva: 2026-04-04
Eredmeny: NEM TESZTELVE (nem probaltunk .env-t irni)
Tanulsag: Kovetkezo alkalommal explicit tesztelni kell

### /update-plan — S20
Hivva: NEM HIVVA
Eredmeny: SKIP — session vegen nem futott le
Problema: Szamok (165 endpoint, 46 tabla) nem propagalodtak a command-okba
Tanulsag: MINDIG lefuttatni session vegen!

---

## Session 21 (B1.1 — LLM Guardrail Promptok)

_(Kitoltendo a session vegen)_
