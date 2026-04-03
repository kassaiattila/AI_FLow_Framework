# AIFlow v1.2.0 — Session 6 Prompt (C0 Ciklus Inditas)

> **Datum:** 2026-04-03 (5. session utan)
> **Elozo session:** v1.2.0 teljes tervezes — 9 terv dok (48-56), 3x validacio, Claude Code config frissites
> **Branch:** main
> **Port:** API 8102, Frontend 5173 (Vite proxy → 8102)
> **Utolso commit:** 7 commit a session-ben (session 4 munkak + 6 terv commit)

---

## ALLAPOT

### v1.2.0 Tervezes: KESZ (3x validalva, 0 HIGH issue)

| Dokumentum | Tartalom | Allapot |
|------------|----------|---------|
| `01_PLAN/48_ORCHESTRABLE_SERVICE_ARCHITECTURE.md` | Fo terv — Pipeline as Code, Tier 1-3 | KESZ |
| `01_PLAN/49_STABILITY_REGRESSION.md` | API compat, DB safety, L0-L4 tesztek | KESZ |
| `01_PLAN/50_RAG_VECTOR_CONTEXT_SERVICE.md` | RAG: OCR, chunking, reranking, VectorOps | KESZ |
| `01_PLAN/51_DOCUMENT_EXTRACTION_INTENT.md` | Param. doc tipusok, intent, szamla use case | KESZ |
| `01_PLAN/52_HUMAN_IN_THE_LOOP_NOTIFICATION.md` | HITL review + notification (email/Slack) | KESZ |
| `01_PLAN/53_FRONTEND_DESIGN_SYSTEM.md` | Untitled UI 80+ komp., chat UI, journey, PWA | KESZ |
| `01_PLAN/54_LLM_QUALITY_COST_OPTIMIZATION.md` | Promptfoo CI, rubric, koltseg, Gotenberg | KESZ |
| `01_PLAN/55_CLAUDE_CODE_CONFIGURATION.md` | Claude iranyitas: CLAUDE.md, commands, MCP | KESZ |
| `01_PLAN/56_EXECUTION_PLAN.md` | 21 ciklus (C0-C20), session sablon | KESZ |

### Claude Code Config: FRISSITVE v1.2.0-ra

- Root CLAUDE.md: v1.2.0 szabalyok (API compat, DB safety, service isolation, pipeline/adapter rules)
- 21 slash command (18 meglevo + 3 uj: `/new-pipeline`, `/pipeline-test`, `/quality-check`)
- `/dev-step` bovitve: L0 smoke test pre+post, v1.2.0 plan references
- `scripts/smoke_test.sh` letrehozva (L0, <30s)

### Technologiai Dontesek (VEGLEGES)

| Tema | Valasztas | Kihagyva |
|------|-----------|----------|
| Reranker | bge-reranker-v2-m3 + FlashRank | — |
| Chunking | Sajat 6 strategia + Chonkie | LangChain, LlamaIndex |
| Parser | Docling → Unstructured → Tesseract → Azure DI | LlamaParse |
| GraphRAG | MS GraphRAG + LazyGraphRAG | Neo4j |
| UI | Untitled UI (80+ free, copy-paste CLI) | MUI, Storybook |
| Chat | react-markdown + Shiki | — |
| PWA | C20 ciklusban | — |
| Kafka | HALASZTVA post-v1.2.0 | — |

---

## KOVETKEZO FELADAT: C0 Ciklus (Elokeszites)

### Lepesek:

```bash
# 1. L0 smoke test — meglevo rendszer OK?
bash scripts/smoke_test.sh

# 2. Untitled UI init
cd aiflow-admin && npx untitledui@latest add button input select textarea modal tabs badges alerts

# 3. TypeScript + lint check
cd aiflow-admin && npx tsc --noEmit
ruff check src/ skills/

# 4. 56_EXECUTION_PLAN.md progress frissites: C0 → DONE

# 5. Commit
git commit -m "chore: C0 preparation — smoke test verified, Untitled UI components added"
```

### C0 UTAN → C1 (Adapter Layer):

```
Cel: src/aiflow/pipeline/ mappa, adapter_base.py + 6 adapter
Terv: 01_PLAN/48 Phase 1
Teszt: unit test minden adapterre + L0 smoke PASS
```

---

## SZERVER INDITAS

```bash
.venv\Scripts\python.exe -B -m uvicorn aiflow.api.app:create_app --factory --port 8102
cd aiflow-admin && npm run dev
```

---

## FEJLESZTESI CIKLUS (MINDEN session-ben kotelezoen)

```
1. TERVEZES    — 56 → hanyadik ciklus? Terv olvasas.
2. FEJLESZTES  — kod iras
3. TESZTELES   — unit + curl + E2E (VALOS, NEM mock!)
4. DOKUMENTALAS — commit, terv frissites
5. FINOMHANGOLAS — review, bug fix
6. SESSION PROMPT — kovetkezo session kontextus
```

**L0 smoke test: MINDIG session elejen ES vegen!**

---

## VEGREHAJTASI TERV

```
C0:     Elokeszites ── KOVETKEZO
C1-C5:  Tier 1 Core ── 3-4 session
C6:     Invoice v1 ─── 1 session ← ITT MAR HASZNALHATO
C7-C10: Tier 2 ─────── 2-3 session
C11-16: Tier 3 RAG ─── 3-4 session
C17-20: Tier 4 Polish── 1-2 session
                        ~12-15 session
```

---

## INFRASTRUKTURA

- PostgreSQL 5433, Redis 6379 (Docker)
- Auth: admin@bestix.hu / admin
- 26 Alembic migracio, 41 DB tabla, 112+ endpoint, 19 router, 17 UI oldal, 15 service

---

## FONTOS SZABALYOK

- **API Compatibility:** Meglevo endpointok FROZEN, uj mezo MINDIG optional
- **Service Isolation:** Meglevo service-ek KIZAROLAG bugfix, adapter NEM modositja az eredetit
- **DB Migration:** nullable=True, ON DELETE SET NULL, CREATE INDEX CONCURRENTLY
- **Pipeline as Code:** YAML + Claude Code, NEM drag-and-drop
- **Valos Teszteles:** SOHA NE mock/fake! Playwright E2E KOTELEZO UI-hoz
- **7 HARD GATE:** Journey → API → Figma → UI → E2E → Regression → Tag
- **L0 Smoke Test:** `bash scripts/smoke_test.sh` (session elejen + vegen)
