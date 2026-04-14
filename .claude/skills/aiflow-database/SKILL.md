---
name: aiflow-database
description: AIFlow adatbazis migracio, zero-downtime, DWH szabalyok. Hasznald amikor Alembic migraciot irsz, DB schemat modositasz, vagy adatbazis tervezessel foglalkozol.
allowed-tools: Read, Write, Edit, Grep, Glob, Bash
---

# AIFlow Database Skill

## Alembic Migration Szabalyok

### KOTELEZO (minden schema valtozasra)
1. **MINDEN** schema valtozas Alembic-en keresztul — SOHA ne hasznalj raw DDL-t
2. Uj oszlopok: `nullable=True` VAGY `server_default=...`
3. MINDEN migration-nak kell `downgrade()` fuggveny
4. Migration szam: folytatolagos (jelenlegi: 001-031, v2: 032-036)
5. `created_at TIMESTAMPTZ` + `updated_at` MINDEN tablara
6. UUID primary key: `gen_random_uuid()`

### Zero-Downtime Migration Minta (DOHA)
```
Release N:   ADD uj oszlop (nullable)                ← Alembic
Release N:   DEPLOY kod MINDKETTOBE ir (regi+uj)     ← App
Release N:   BACKFILL uj oszlop                       ← Migration
Release N+1: DEPLOY kod UJBOL olvas                   ← App
Release N+2: DROP regi oszlop (opcionalis)            ← Alembic
```

### v2 Migration Szekvencia (030-036)
- 030: `intake_packages`, `intake_files`, `intake_descriptions`
- 031: `policy_overrides`
- 032: `routing_decisions`
- 033: `extraction_results` bovites (package_id, field_confidences)
- 034-036: archival, lineage, embedding, provenance tablak

### Backward Compatibility Shim Layer
- Legacy `email_adapter` YAML → auto-upgrade `intake_normalize`-re
- Regi `extract(file_path)` API → single-file package wrapper
- Meglevo pipeline template-ek valtozatlanul mukodnek

## TILTOTT
- `DROP TABLE` / `DROP COLUMN` kozvetlenul — MINDIG Alembic-en at
- Raw SQL az alkalmazas kodban — hasznalj SQLAlchemy ORM-et
- `SELECT *` — mindig explicit oszlopnev lista
- Downgrade() hianya — MINDEN migracionak kell
- PII adat indexelesben — SOHA

## Parancsok
```bash
alembic revision --autogenerate -m "leir as"
alembic upgrade head
alembic downgrade -1    # egy lepessel vissza
alembic history         # teljes tortenet
```

## Kulcs Szamok
- 48 DB tabla | 31 Alembic migration (001-031)
- v2 tervezett: +6 tabla (030-036)
- PostgreSQL 15+ | pgvector v0.8.1 | Redis 7.0+
