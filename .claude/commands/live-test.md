# /live-test — Live E2E browser journey via Playwright MCP

## Argumentum

```
/live-test <module>     # modul neve: emails, documents, rag, runs, costs, prompts, admin
/live-test all          # osszes modul egymas utan
/live-test <module> --report-only   # csak az utolso futtatas riportjat olvassa fel
```

## Cel

Futtass egy **valos elo** browser-alapu end-to-end tesztet a Playwright MCP
eszkozokon keresztul (`mcp__playwright__browser_*`). Az eredmeny egy
friss riport a `tests/ui-live/<module>.md` `## Utolso futtatas` szekciojaban.

Ez NEM helyettesiti a CI Playwright `.spec.ts` teszteket — **kiegesziti**
oket session-time debugging-re + usability auditing-re.

---

## 1. Elofeltetel-ellenorzes (KOTELEZO, nem atugorhato)

```bash
curl -sf http://127.0.0.1:8102/health || exit "API DOWN"
curl -sf http://127.0.0.1:5173 || exit "Vite DOWN"
docker ps --format "{{.Names}}" | grep -q 07_ai_flow_framwork-db-1 || exit "PG DOWN"
```

Ha barmelyik FAIL → jelezz a usernek. **Ne indits tesztet elavult stack-en.**

---

## 2. Journey betoltes

Olvasd be `tests/ui-live/<module>.md`-t. Ha nem letezik:

```
⚠️  tests/ui-live/<module>.md nem letezik.
Elerheto modulok: ls tests/ui-live/*.md
Uj modul hozzaadasaval: /ui-journey <module> → majd masold le emails.md-t.
```

---

## 3. Futtatas (Playwright MCP)

A journey "Journey" szekcioja sorrendben hajtod vegre:

### Alap eszkozok (ket MCP csomag, ugyanaz az API)

Elerheto ket Playwright MCP csomag — hasznald amelyik aktiv a session-ben.
Ha mindketto elerheto, **a plugin valtozatot valaszd** (frissebb, pontosabb
locator matching).

| Journey step | MCP tool (direkt) | MCP tool (plugin) |
|---|---|---|
| `navigate` | `mcp__playwright__browser_navigate` | `mcp__plugin_playwright_playwright__browser_navigate` |
| `fill`     | `mcp__playwright__browser_fill_form` | `mcp__plugin_playwright_playwright__browser_fill_form` |
| `click`    | `mcp__playwright__browser_click` | `mcp__plugin_playwright_playwright__browser_click` |
| `snapshot` | `mcp__playwright__browser_snapshot` | `mcp__plugin_playwright_playwright__browser_snapshot` |
| `wait`     | `mcp__playwright__browser_wait_for` | `mcp__plugin_playwright_playwright__browser_wait_for` |
| `screenshot` | `mcp__playwright__browser_take_screenshot` | `mcp__plugin_playwright_playwright__browser_take_screenshot` |
| `console`  | `mcp__playwright__browser_console_messages` | `mcp__plugin_playwright_playwright__browser_console_messages` |
| `network`  | `mcp__playwright__browser_network_requests` | `mcp__plugin_playwright_playwright__browser_network_requests` |
| `evaluate` | `mcp__playwright__browser_evaluate` | `mcp__plugin_playwright_playwright__browser_evaluate` |

**Protokoll:** a test elejen irj le melyik csomagot hasznalod, es azzal
menj vegig. Kozben NE valts — keverve hasznalva instance conflict lehet
(ketto parhuzamos browser session).

### Assertion protokoll MINDEN lepes utan

```
errors = browser_console_messages(level=error)
networks = browser_network_requests(filter=/api/)
assert len(errors) == 0, f"Console errors: {errors}"
assert all(r.status < 400 for r in networks), f"HTTP errors: {[r for r in networks if r.status >= 400]}"
```

### Screenshot politika

- Minden kulcs state-nel (login elott, lista betoltes, akcio elott, akcio utan, hiba eseten)
- Filename: `.playwright-mcp/<module>-<stepN>-<description>.png`
- `fullPage=true` csak a completion screenshot-oknal (tablak teljes lat)

---

## 4. Hiba eseten

Ha BARMELY assertion FAIL:

1. **Rogzits evidence-t**:
   - `browser_take_screenshot(fullPage=true)` — teljes oldal
   - `browser_console_messages(level=error)` — osszes hiba
   - `browser_network_requests(filter=/api/)` — osszes hivas
2. **Diagnosztikai lepes**:
   - Ha 500 → backend log: `tail -50 <uvicorn_output>`
   - Ha CORS → `Grep("CORSMiddleware", src/aiflow/api/app.py)` + `router prefix` check
   - Ha 404 → endpoint existens: `curl -s http://127.0.0.1:8102/openapi.json | jq '.paths | keys'`
3. **Javits** (ha trivialis — <10 soros fix), VAGY jelents a usernek STOP-kent
4. **Irj riportot a rogzitett modulra** `## Utolso futtatas` szekcio folott:
   ```markdown
   ### <YYYY-MM-DD HH:MM> — FAIL
   - Lepes <N>: <leiras>
   - Error: <pontos hiba>
   - Evidence: <screenshot path>
   - Action: <fix commit hash | STOP>
   ```

---

## 5. Sikeres futtatas utan

### Riport generalas

Sorold fel a PASS/FAIL eredmenyt, ehhez a formatumhoz:

```markdown
### <YYYY-MM-DD HH:MM> — <PASS | PARTIAL | FAIL>
- Lepes 1 (Login): PASS / hiba leiras
- Lepes 2 (...): PASS / ...
- ...
- **Findings (usability):** <megjegyzesek UX-rol>
- **Commits ha volt fix:** <hash>
- **Ossz ido:** <elapsed seconds>
```

### A modul `.md` fajl frissitese

Irjd be a riport-ot a `## Utolso futtatas` szekcio tetejere:

```python
# Pseudo:
content = Read("tests/ui-live/<module>.md")
section_start = content.find("## Utolso futtatas")
new_report = build_report(...)
Edit(content after section_start: insert new_report)
```

### Browser lezaras (opcionalis)

```
browser_close()  # csak ha a test vegen vagyunk + nincs mas teszt hatra
```

---

## 6. Integracio a session workflow-ba

- **A `session-close` parancsnak ELLENORIZNIE kell**: ha a session UI fajlt modositott
  (`git diff --cached --name-only HEAD | grep '^aiflow-admin/'`), akkor **a releváns
  modul(ok) live-test-je MANDATORY** a commit elott. Ha nem futott, blokkold a session-close-t.

- **A `status` parancsnak LISTAZNIA kell** az aktualis live-test healt-ot:
  utolso futtatas dátuma + status minden modulra.

---

## 7. Restrikciok

- Browser session **PERSISTALT** a `/live-test` futasok kozott (login cookie meghagyva) —
  NE futtass `browser_close()`-t automatikusan.
- Ne fizessun LLM koltseget meglevo adaton kivul — pl. `Process All (168)` helyett egy
  soron nyomj `Process`-t. Ha szukseges bulk teszt, hasznalj max 3 emailt.
- **Ne modositsd** a `tests/ui-live/<module>.md` Journey szekciojat — csak a `## Utolso
  futtatas` szekciot. A Journey szerkesztese kulon PR.

---

## Pelda futtatasi flow

```
User: /live-test emails

Claude:
1. Preflight checks... PASS (API/Vite/PG up)
2. Journey load: tests/ui-live/emails.md (8 lepes)
3. Login... (browser_navigate + fill + click) → PASS
4. Navigate /emails... (browser_navigate + snapshot) → PASS
5. Cost modal test... PASS
6. Single email process... (wait 60s) → PASS, intent=marketing
7. Cancel test... PASS, 0 errors
8. CSV Export... PASS
9. Report:
   - Ossz 8/8 lepes PASS
   - 0 console error, 0 network 5xx
   - Ossz ido: 87s
   - Findings: "ETA kezdetben statikus becsles"
10. Edit tests/ui-live/emails.md — uj ## Utolso futtatas riport
```
