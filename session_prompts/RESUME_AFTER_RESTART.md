# Resume notes — 2026-04-23

## Allapot ujrainditas elott

**Branch:** `feature/v1.4.7-email-intent`
**HEAD:** `e75a42d feat(ui): S108a — Emails.tsx baseline hardening`
**Remote:** in sync (mindent pusholtunk)
**Uncommitted:** csak 2 idegen script (`scripts/alina_md_to_docx.py`, `scripts/extract_alina_kepek.py`) — nem Sprint K artifact, ignorald

## Mi van kesz

Sprint K v1.4.7:
- S106 ✅ scan_and_classify orchestrator + POST /emails/scan/{config_id}
- S107 ✅ IntentRoutingPolicy + routing wiring + 4-way integration test
- S108a ✅ Emails.tsx baseline hardening (cost preview + batch cap 25 + Megszakitas + ETA + label fallback)
- S108b ⌛ 3-way UI split (Connectors / Daily Inbox / Intent Rules) — NEXT, tempodban egyutt
- S109 ⌛ Prompts.tsx v2 Langfuse edit
- S110 ⌛ Playwright E2E + PR + tag v1.4.7

## Ujrainditas utan — hogy inditsd be a stack-et

```bash
# 1. Docker (AIFlow PG + Redis)
cd /c/00_DEV_LOCAL/07_AI_Flow_Framwork
docker compose up -d db redis

# 2. FastAPI (port 8102)
PYTHONUNBUFFERED=1 PYTHONPATH="src;." .venv/Scripts/python.exe -u -m uvicorn aiflow.api.app:create_app --factory --port 8102 --host 127.0.0.1

# 3. Vite dev (port 5173) — uj terminalban
cd aiflow-admin && npm run dev
```

## URLs + login

- UI: http://localhost:5173
- API health: http://127.0.0.1:8102/health
- Swagger: http://127.0.0.1:8102/docs
- Login: `admin@aiflow.local` / `AiFlowDev2026` (nem bestix!)

## Amit tesztelhetsz ujrainditas utan

1. `/emails` oldal — 171 email lista (a 3 mar feldolgozott lathato)
2. Egyedi `Process` gomb soron — ~60s, OpenAI LLM hivas, intent+routing persist
3. `Process All (168)` — cost modal ~$0.13 / ~2h 48m → Megse vagy Inditas → Megszakitas bármikor

## Kovetkezo session indulasa

```
/status      (ellenorizd hol tartunk)
/next        (NEXT.md-bol S108 prompt — megj.: S108a mar kesz, S108b kell)
```

Vagy kozvetlenul: **"folytassuk S108b-vel: UI 3-way split (Connectors / Daily / Intent Rules)"**.

## Memoria flash

- UI hard gate doctrine: Journey → Figma → UI. NEM ugorhato gate autonomousan.
- S108b-hez keszites Figma fajlt vagy hasznaljuk a frontend-design skillt code-only design-hoz.
- Playwright MCP es frontend-design skill mindketto elerheto, user-vezérelt design session kell.
