---
description: >
  Autonomous AIFlow sprint loop — végigfut a NEXT.md sorbaállított
  S{N+1}_{task_id} session-jein /clear+/next nélkül. STOP feltételen
  vagy iteration cap-en megáll + log entry, normál session-close után
  ScheduleWakeup ~90s majd folytatja.
argument-hint: "[max_sessions=16] [notify=stop_only|all]"
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, ScheduleWakeup
---

# AIFlow Autonomous Sprint Loop

> **Egyetlen `/auto-sprint` indítás után végigfut a queue-olt session-eken.**
> `/clear`+`/next` nélkül iterál. STOP-on vagy cap-en megáll + log entry.

DOHA reference: `DOHA/01_PLAN/19_DOHA_AUTO_SPRINT_GUIDE.md` (Gmail variant).
AIFlow adaptáció: file-log only mode (`AIFLOW_AUTOSPRINT_NO_EMAIL=1`),
nincs RG boundary detection, nincs pending-email recovery.

## Notification mode

Default: file-log mód. A `scripts/send_notification.py` minden értesítést
appendel a `session_prompts/.notifications.log` fájlba (gitignored).

Tail-elheted másik terminálban: `tail -f session_prompts/.notifications.log`

A log entry formátum:
```
[2026-04-18T12:34:56Z] [DONE] S83 closed — iter 3/16
  Branch: feature/v1.4.3-phase-1d-adapter-orchestration
  Commit: 8f7d0c6 feat(phase_1d): G0.4 — Batch + Api adapter wiring
  Next queued: S84
---
```

Gmail integráció (Phase 2): nincs implementálva. A DOHA guide alapján
később hozzáadható, ha szükséges.

## A. State init

Parse args (defaults):
- `max_sessions=16` — iteration cap
- `notify=stop_only` — `stop_only` vagy `all` (utóbbi normál close után is logol)

```bash
STATE_FILE="session_prompts/.auto_sprint_state.json"
if [ -f "$STATE_FILE" ]; then
  cat "$STATE_FILE"
else
  echo '{"iteration": 0, "last_run_ts": null}'
fi
```

Ha a state fájl nem létezik → `iteration=0`, `last_run_ts=null`.

Olvasd be `session_prompts/NEXT.md`-t. Parse out `session_id`-t az első
`# AIFlow ... Session N Prompt (XYZ)` H1 sor `(XYZ)` vagy `S{N}` mintából.

Ha NEXT.md nem létezik:
→ Log entry: kind=stop, subject="auto-sprint halted — no NEXT.md".
→ Halt, no rearm.

## D. Iteration cap

Ha `iteration >= max_sessions`:
1. Render cap notification body:
   ```
   Auto-sprint cap reached.
   Ran {iteration}/{max_sessions} sessions on branch {branch}.
   Next queued session: {session_id}.
   Last commit: {sha}
   Resume: /auto-sprint max_sessions=N
   ```
2. Send (file-log):
   ```bash
   .venv/Scripts/python.exe scripts/send_notification.py \
     --kind cap \
     --subject "[AIFlow auto-sprint] cap reached — ${iteration} sessions completed" \
     --body "<rendered body>"
   ```
3. Halt, no rearm.

## E. Execute one session

Print banner:
```
[auto-sprint iter <N>/<M> session=<session_id> — Ctrl+C or any input pauses]
```

Behaviorally kövesd `.claude/commands/next.md` Step 2-3-at a jelenlegi NEXT.md ellen:

1. **Step 2 — Környezet ellenőrzés:**
   ```bash
   git branch --show-current
   git log --oneline -3
   git status --short
   ```
   + a NEXT.md "ELOFELTETELEK" szekciójának minden parancsát.
   Ha bármelyik FAIL → kezeld **error-recoverable STOP**-ként (lépj F-re).

2. **Step 3 — Feladat végrehajtás:** a NEXT.md "FELADATOK" szekciója szerint,
   CLAUDE.md + aktív skill-ek konvencióit követve.

**NE hívd** literál `/next`-et — Claude Code nem nest-eli a slash command-okat,
a behavior-t inline kell mirror-ölni.

## F. STOP-watch (model-driven)

Iterációd során **bármikor** ha egy megfigyelt állapot megfeleltethető a NEXT.md
"STOP FELTETELEK" valamelyik klauzulájának:

| STOP type | Trigger |
|---|---|
| **decision-required** | Architekturalis döntés, új interface, security concern (PII/auth/crypto), Alembic non-additive migráció, schema breaking change |
| **error-recoverable** | Teszt FAIL amit 2 próbából nem tudsz javítani, lint FAIL auto-fix után, commit-hook DENY másodszor is |
| **scope** | Session scope lényegesen nagyobb mint becsült, external dependency hiányzik (LLM down, DB nem indítható), main branch érintve |

Action:
1. Render STOP body:
   ```
   Auto-sprint halted.
   Session: {session_id}
   STOP type: {stop_type}
   Branch: {branch}
   Last commit: {sha} {commit_subject}
   Iteration: {iteration}/{max_sessions}

   Trigger (verbatim from NEXT.md "STOP FELTETELEK"):
   {matched_stop_clause}

   Evidence:
   {evidence_block}

   Suggested options:
   1. Resolve manually, edit NEXT.md, restart with /auto-sprint
   2. Skip this session — overwrite NEXT.md with the next planned S{N+1}
   3. Escalate to architect/security-reviewer subagent
   ```

2. Send (file-log):
   ```bash
   .venv/Scripts/python.exe scripts/send_notification.py \
     --kind stop \
     --subject "[AIFlow STOP] ${session_id} — ${stop_type}" \
     --body-file session_prompts/.notifications_body.md
   ```
   (írd a body-t fájlba ha többsoros, hogy a shell quoting ne tegyen kárt benne)

3. Update `.auto_sprint_state.json` with `last_stop: {session_id, stop_type, timestamp}`.

4. **NE futtasd `/session-close`-t** — STOP esetén NEXT.md regenerálás TILOS!
5. Terminate, no rearm.

## G. Close session (normál happy path)

Behaviorally kövesd `.claude/commands/session-close.md` FÁZIS 1, 1b, 3-at:

1. **FÁZIS 1 — Validáció gate (5 gate, BLOKKOLO):**
   ```bash
   .venv/Scripts/python.exe -m ruff check src/ tests/ --quiet
   # tsc csak ha aiflow-admin/ érintett
   .venv/Scripts/python.exe -m pytest tests/unit/ -x -q
   .venv/Scripts/python.exe -m pytest tests/e2e/ --collect-only -q
   git status --short
   ```

2. **FÁZIS 1b — Git commit + push:**
   ```bash
   git add <konkret_fajlok>  # SOHA git add -A
   git commit -m "$(cat <<'EOF'
   <type>(<scope>): <session_id> — <rovid leiras>

   - reszlet 1
   - reszlet 2

   Session: <session_id> | Sprint: <X> | Phase: <N>
   Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
   EOF
   )"
   git push 2>&1 | tail -3
   ```

3. **FÁZIS 3 — NEXT.md regen:** olvasd az aktuális sprint terv (CLAUDE.md →
   `01_PLAN/session_S{##}_*.md`) → következő logikai session →
   write `session_prompts/S{N+1}_{next_id}_prompt.md` + `session_prompts/NEXT.md`
   (azonos tartalom).

**Retry policy:**
- Ruff auto-fix után FAIL → max 1 retry → second fail → **error-recoverable STOP** (F).
- Commit-hook DENY (lint vagy unit FAIL) → fix + retry → second DENY → **error-recoverable STOP**.
- Push fail (non-fast-forward, valaki közben pusholt) → `git pull --rebase` + 1 retry → second fail → STOP. **SOHA `git push --force`!** (A pre-hook is blokkolja.)

## H. Optional done notification

Ha `notify=all`:
1. Render done body:
   ```
   Session {session_id} closed cleanly.
   Iteration: {iteration}/{max_sessions}
   Branch: {branch}
   Commit: {sha}
   Next queued: {next_session_id}
   ```
2. Send (file-log):
   ```bash
   .venv/Scripts/python.exe scripts/send_notification.py \
     --kind done \
     --subject "[AIFlow auto-sprint] ${session_id} closed — iter ${iteration}/${max_sessions}" \
     --body "<rendered body>"
   ```
3. Continue regardless of exit code (done log nem kritikus).

Ha `notify=stop_only` → kihagyod ezt a lépést.

## I. Re-arm

1. Increment `iteration`, persist state (UTF-8 explicit — Windows cp1252 trap):
   ```bash
   .venv/Scripts/python.exe -c "
   import json, sys
   from datetime import datetime, timezone
   state = {
     'iteration': $((<N> + 1)),
     'last_run_ts': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
     'max_sessions': <M>,
     'notify': '<X>'
   }
   open('session_prompts/.auto_sprint_state.json', 'w', encoding='utf-8').write(json.dumps(state))
   "
   ```

2. Call `ScheduleWakeup`:
   - `delaySeconds: 90` (cache-warm window: 60-270s; 90s = git push + disk sync-re bőven elég)
   - `prompt: "/auto-sprint max_sessions=<M> notify=<X>"` (verbatim args — a wakeup re-enter-eli a loop-ot)
   - `reason: "auto-sprint iter <N+1>/<M> — next is <upcoming_session_id>"`

3. Halt this turn (wakeup majd tüzel).

## J. Termination summary

| Branch | Action |
|---|---|
| STOP fired | log entry + halt (no rearm, no NEXT.md regen) |
| Iteration cap | log entry + halt (no rearm) |
| Session-close fatal fail | log entry + halt (no rearm) — kezeld error-recoverable STOP-ként |
| Normal close | optional log entry (notify=all) + rearm (ScheduleWakeup 90s) + halt this turn |

---

## Failure mode matrix

| Scenario | Behaviour |
|---|---|
| ScheduleWakeup nem tűz (process killed) | `.auto_sprint_state.json` durable handoff. User `/auto-sprint` → resume. |
| `/session-close` gate FAIL (smoke FAIL → commit hook DENY) | 1x retry; második fail → error-recoverable STOP, evidence = failing test output. |
| Push fail (non-fast-forward) | `git pull --rebase` + 1x retry; második fail → STOP. **Soha force-push.** |
| Két STOP gyors egymásutánban | Iterációnként max 1 STOP — halt megakadályozza. Resume után új iteráció új STOP-ot indíthat. |
| User input mid-loop | Claude Code megszakítja a wakeup turn-t. State on disk → user `/clear`-rel abortálhat vagy `/auto-sprint`-tel folytathat. |
| Log fájl write fail | `send_notification.py` exit 2 → loop log warning-ot ír stdout-ra, de NE STOP-ol — a log nem kritikus, a state.json a forrás. |

---

## Risks (user tudjon róluk)

1. **Runaway iteration ha STOP detection misfires** → `max_sessions=16` cap + commit-hook smoke gate (második egymásutáni DENY → STOP). Havi subscription esetén a valódi korlát a Claude 5-órás token rate window, nem a session szám.
2. **Cache-miss tax hosszú iterációkon** → 90s wakeup cache-warm window-ban marad <~4 perc iterációkig. Phase 1+ session-ek hosszabbak lehetnek.
3. **`.auto_sprint_state.json` accidental commit** → `.gitignore` fedezi. Session-close SOHA `git add .`.
4. **Windows path quoting** (`OneDrive - BestIxCom Kft` space-t tartalmaz) → quote-old `$PROJECT_DIR`-t minden Bash blokkban.
5. **Nincs külső watchdog** — ha `claude` process crash-el, semmi nem restart-ol. Acceptable 6-session burst-re, nem unattended overnight-ra. Terminál legyen látható.
6. **PostToolUse hook (ruff format)** elnyomhatja a frissen hozzáadott Python importot ha a kód nem hivatkozza még — figyeld az utolsó Edit utáni "stale-file" warning-ot (G0.3 tapasztalat: az `IntakePackageSink` import törlődött, mert csak később jelent meg a hivatkozása).

---

## Out of scope

- Gmail OAuth integráció — Phase 2, külön session.
- Phase-merge / tag-cut hard boundary regex — most csak STOP feltételek + cap.
- Auto-merge PR-be — most NEM, mindig user.
- Multiple parallel worktree-k — most single branch.
- Slack/Telegram notify — most csak file-log.
- Külső cron orchestrator — most single interactive session.

$ARGUMENTS
