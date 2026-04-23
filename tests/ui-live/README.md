# AIFlow Live E2E — session-time browser journeys

> **Cel:** minden UI modul egy **valos elo** browser-session alatt
> vegigfutott journey-vel rendelkezzen, amit Claude a **Playwright MCP**-n
> keresztul interaktivan futtat a fejlesztes kozben. NEM helyettesiti a
> CI Playwright `.spec.ts` teszteket — kiegesziti oket: gyorsabb visszajelzes,
> console + network errorok rogzitese, user journey usability auditing.

## Miben kulonbozik a CI Playwright-tol?

| Szempont | CI `.spec.ts` (aiflow-admin/tests/e2e/) | Live E2E (`tests/ui-live/`) |
|---|---|---|
| **Futtato** | `npx playwright test` (npm script) | Claude Playwright MCP-n keresztul |
| **Cel** | regressziovedelem | session-time usability + live debugging |
| **Formatum** | TypeScript spec | Markdown jatekterv (Claude parse-olja) |
| **Adat** | kontrollalt fixture | LIVE backend, valodi DB, valodi LLM hivas |
| **Mikor** | CI (merge elott) | **session kozben, UI valtozas utan** |
| **Outputok** | pass/fail, trace.zip | markdown riport + screenshotok + console/network log |

## Futtatasi protokoll

**Alaparmetereket a `/live-test <module>` slash command definial.**

Kezzel is vegigmehetsz rajtuk — nyisd meg a `tests/ui-live/<module>.md`-t
es kovesd a lepeseket a Playwright MCP eszkoeokkel.

## Elofeltetelek (MINDEN live-test elott)

```bash
curl -sf http://127.0.0.1:8102/health || echo "API DOWN — indits backendet"
curl -sf http://127.0.0.1:5173 || echo "Vite DOWN — indits frontendet"
docker ps --format "{{.Names}}" | grep -q 07_ai_flow_framwork-db-1 || echo "PG DOWN"
```

## Kozos lepesek minden journey-nek

1. **Login** — `admin@aiflow.local` / `AiFlowDev2026` (dev env)
2. **Hibafigyeles** — minden lepes utan `browser_console_messages(level=error)` + `browser_network_requests()` (filter: `/api/`)
3. **Screenshot** — minden kulcs state-nel (kezdoallapot, akcio utan, befejezes)
4. **Teljesitmeny** — `elapsed_ms` jelolese a hosszu actions-nel (pl. LLM call)

## Sikerkriteriumok (PASS feltetelek)

Egy live-test PASS akkor, ha MINDEN teljesul:

- Minden navigacios lepes utan **0 error** a browser console-ban (CORS, 500, null reference, etc.)
- Minden `/api/*` response 2xx VAGY dokumentaltan 4xx (pl. auth hiba teszt)
- Nincsen `ErrorState` komponens renderelve a user-visible panel-en (kiveve ha pont ez teszteljuk)
- Az osszes elvart UI elem megtalalhato a snapshot-ban (osszehasonlitott ref-ekkel)
- A journey veget jelzo allapot elerheto (pl. "email processed", "document uploaded")

## Riport formatum (minden test utan)

```markdown
## Live E2E Report: <module> — <YYYY-MM-DD HH:MM>

| Lepes | Elvart | Tenyleges | Allapot |
|-------|--------|-----------|---------|
| 1 Login | /#/ redirect | OK | PASS |
| 2 Lista betoltes | 171 email | 171 email | PASS |
| 3 Process single | intent=marketing | intent=marketing | PASS |

Console errors: 0
Network errors: 0
Ossz ido: 74s
Findings: <usability megjegyzesek>
Commit (ha volt fix): <hash>
```

A riport a modul `.md` fajl vegen az `## Utolso futtatas` szekcio ala kerul.

## Catalog

| Modul | Fajl | Status |
|-------|------|--------|
| Emails | [emails.md](./emails.md) | Active |
| Intent Rules | [intent-rules.md](./intent-rules.md) | Active |
| Prompts | [prompts.md](./prompts.md) | Active |
| Documents | _todo_ | — |
| RAG | _todo_ | — |
| Runs | _todo_ | — |
| Costs | _todo_ | — |
| Prompts | _todo_ | — |
| Admin | _todo_ | — |

## Uj modul hozzaadasa

1. Masold le az `emails.md`-t `<new-module>.md` nevvel.
2. Cserel ki a journey-t a modul specifikus flow-ra.
3. Add hozza ehhez a README-hez a Catalog tabla sorat.
4. Futtasd `/live-test <new-module>` a commit elott.
