# AIFlow v1.0.0 Session Prompt

> **Masold be ezt uj Claude Code session elejen a teljes kontextus betoltesehez.**

---

```
Kontextus: AIFlow v1.0.0-rc1 → v1.0.0 final release javitasok.

Projekt: Enterprise AI Automation Framework (Python 3.12, FastAPI, PostgreSQL+pgvector, Redis, React Admin+MUI).
Allapot: F0-F5 service generalizacio BEFEJEZVE, v1.0.0-rc1 tag-elve (2026-04-02).

Szamok: 180 Python modul, 114 API endpoint (19 router), 49 DB tabla (24 Alembic migracio), 15 service, 18 admin UI oldal, teljes HU/EN i18n.

Audit: 01_PLAN/AUDIT_REPORT_v1.0.0-rc1.md — teljes terv/kod/API/security audit eredmeny.
Feladatterv: 01_PLAN/AUDIT_FIX_PLAN.md — 13 task, 4 sprint, ~28 ora.

KRITIKUS javitasok (Sprint 1, T1-T4):
- T1: Hardcoded credentials torlese (auth.py:18-22) → bcrypt + DB users tabla
- T2: JWT default secret → production-ben REQUIRED
- T3: CORS allow_origins=["*"] → whitelist
- T4: Error traceback exposure → production-ben elrejteni

MAGAS prioritas (Sprint 2, T5-T7):
- T5: Auth middleware minden /api/v1/* endpoint-ra (jelenleg legtobb nyitott)
- T6: Connection pooling (jelenleg endpointonkent uj connection)
- T7: API key endpoint konszolidacio (auth.py in-memory vs admin.py DB)

Szervek: PostgreSQL @ localhost:5433, Redis, FastAPI @ localhost:8101, Vite @ localhost:5174 (proxy → 8101)

Olvasd el: CLAUDE.md (projekt szabalyok), 01_PLAN/AUDIT_FIX_PLAN.md (reszletes feladatok), src/aiflow/api/v1/auth.py (fo security fajl).
```
