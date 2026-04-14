# AIFlow Sprint B — Session 23 Prompt (B2.1: Core Infra Service Tesztek)

> **Datum:** 2026-04-06
> **Branch:** `feature/v1.3.0-service-excellence` | **HEAD:** `d9df3ca`
> **Port:** API 8102, Frontend 5174
> **Elozo session:** S22 — B1.2 DONE (5 guardrails.yaml + PIIMaskingMode + 31 teszt)
> **Terv:** `01_PLAN/58_POST_SPRINT_HARDENING_PLAN.md` (B2 szekció, sor 886+)

---

## KONTEXTUS

### B1 Eredmenyek (S20-S22 — DONE)

- B1.1: 4 LLM guardrail prompt + llm_guards.py + 27 promptfoo (commit f6670a1)
- B1.2: 5 per-skill guardrails.yaml + PIIMaskingMode enum + 31 teszt (commit 7cec90b)
- Sprint B Fazis 1 (Alapok) TELJES

### Infrastruktura (v1.3.0)

- 26 service | 165 API endpoint (25 router) | 46 DB tabla | 29 migracio
- 18 adapter | 6 template | 5 skill | 22 UI oldal
- 1195 unit test | 129 guardrail teszt | 97 security teszt | 54 promptfoo teszt
- Guardrail: A5 rule-based + B1.1 LLM fallback + B1.2 per-skill config

### Jelenlegi Service Teszt Allapot

A 26 service-bol CSAK nehanynak van dedikalt unit teszt:
- `rate_limiter` → tests/unit/execution/test_rate_limiter.py (letezik)
- `audit` → tests/unit/security/test_audit.py (letezik)
- `notification` → tests/unit/pipeline/test_notification_service.py (letezik)
- `health_monitor` → tests/unit/api/test_health.py (letezik)
- A tobbi 9 Tier 1 service-nek NINCS dedikalt unit tesztje!

---

## B2.1 FELADAT: Core Infra Service Tesztek (13 service, 65 test)

> **Gate:** 65 uj unit test PASS a `tests/unit/services/` konyvtarban
> **Eszkozok:** `/dev-step` (service-enkent), `/regression`
> **Pattern:** Minden service-hez 5 unit teszt, mock-olhato fuggosegekkel

### 13 Tier 1 Service + Tesztelesi Terv

Minden service-hez **5 unit teszt** kell. Az alabbi tablazat mutatja a service-t, a fosztaly nevet, a fuggosegeket es a tesztelendo metodusokat.

#### 1. cache — `CacheService` (Redis)

```
Fajl: src/aiflow/services/cache/service.py
Dep: Redis (asyncio)
Tesztek:
  test_get_embedding_cache_hit()     — set + get embedding → match
  test_get_embedding_cache_miss()    — get non-existent → None
  test_llm_response_cache()          — set + get LLM response → match
  test_invalidate_collection()       — invalidate → empty
  test_get_stats()                   — stats dict tartalmazza: hit_count, miss_count
```

#### 2. rate_limiter — `RateLimiterService` (Redis)

```
Fajl: src/aiflow/services/rate_limiter/service.py
Dep: Redis (sorted sets)
Tesztek:
  test_allow_under_limit()           — allow → True ha limit alatt
  test_allow_over_limit()            — allow → False ha limit felett (429 trigger)
  test_get_remaining()               — remaining dict helyes szamokkal
  test_reset_clears_counter()        — reset → allow ujra True
  test_add_rule_runtime()            — uj rule hozzaadas → mukodik
```

#### 3. resilience — `ResilienceService` (in-memory)

```
Fajl: src/aiflow/services/resilience/service.py
Dep: nincs kulso (in-memory circuit breaker)
Tesztek:
  test_execute_success()             — sikeres fuggveny → eredmeny
  test_execute_retry_on_failure()    — transient hiba → retry → siker
  test_circuit_opens_on_failures()   — N hiba → circuit OPEN → exception
  test_circuit_half_open_recovery()  — timeout utan → half-open → siker → CLOSED
  test_get_circuit_state()           — state dict: state, failure_count, threshold
```

#### 4. health_monitor — `HealthMonitorService` (PostgreSQL, Redis)

```
Fajl: src/aiflow/services/health_monitor/service.py
Dep: PostgreSQL + Redis
Tesztek:
  test_check_all_returns_list()      — check_all → ServiceHealth lista
  test_get_service_health()          — specific service health lekerdezese
  test_get_metrics_aggregation()     — metrics: avg/p95 latency, success_rate
  test_unknown_service_returns_none() — nemletezo service → None
  test_health_check_logging()        — health check loggol DB-be
```

#### 5. audit — `AuditTrailService` (PostgreSQL)

```
Fajl: src/aiflow/services/audit/service.py
Dep: PostgreSQL
Tesztek:
  test_log_creates_entry()           — log → AuditEntry letrejott
  test_list_entries_filter()         — filter by action/entity_type → helyes eredmeny
  test_get_entry_by_id()             — get existing → AuditEntry
  test_get_entry_not_found()         — get non-existent → None
  test_log_immutable()               — egyszer letrehozva, nem modosithato
```

#### 6. schema_registry — `SchemaRegistryService` (filesystem)

```
Fajl: src/aiflow/services/schema_registry/service.py
Dep: filesystem (skills/*/schemas/)
Tesztek:
  test_load_schema_existing()        — load existing schema → dict
  test_load_schema_not_found()       — non-existent skill → hiba/None
  test_list_versions()               — list versions → string lista
  test_list_schema_types()           — list types → string lista
  test_invalidate_cache()            — invalidate → kovetkezo load friss
```

#### 7. notification — `NotificationService` (PostgreSQL, SMTP)

```
Fajl: src/aiflow/services/notification/service.py
Dep: PostgreSQL + SMTP + HTTP
Tesztek:
  test_send_email_template()         — send email channel → NotificationResult
  test_send_batch()                  — batch send → lista eredmeny
  test_list_channels()               — list → ChannelConfig lista
  test_create_channel()              — create → persisted ChannelConfig
  test_delete_channel()              — delete → True, list-bol eltunt
```

#### 8. human_review — `HumanReviewService` (PostgreSQL)

```
Fajl: src/aiflow/services/human_review/service.py
Dep: PostgreSQL
Tesztek:
  test_create_review()               — create → HumanReviewItem (pending)
  test_approve_review()              — approve → status=approved, reviewer set
  test_reject_review()               — reject → status=rejected
  test_list_pending_priority_order() — priority sorrend: critical > high > normal
  test_check_sla_deadlines()         — overdue items → escalation lista
```

#### 9. media_processor — `MediaProcessorService` (PostgreSQL, ffmpeg)

```
Fajl: src/aiflow/services/media_processor/service.py
Dep: PostgreSQL + external STT workflow
Tesztek:
  test_process_media_creates_job()   — process → MediaJobRecord (status=running/completed)
  test_list_jobs_pagination()        — list with limit/offset → helyes eredmeny
  test_get_job_existing()            — get by id → MediaJobRecord
  test_get_job_not_found()           — get non-existent → None
  test_delete_job()                  — delete → True, get → None
```

#### 10. diagram_generator — `DiagramGeneratorService` (PostgreSQL, Kroki)

```
Fajl: src/aiflow/services/diagram_generator/service.py
Dep: PostgreSQL + Kroki renderer + process_documentation skill
Tesztek:
  test_generate_creates_record()     — generate → DiagramRecord
  test_list_diagrams_pagination()    — list with limit/offset
  test_get_diagram_existing()        — get by id → DiagramRecord
  test_export_diagram_svg()          — export → SVG string
  test_delete_diagram()              — delete → True
```

#### 11. rpa_browser — `RPABrowserService` (PostgreSQL, YAML)

```
Fajl: src/aiflow/services/rpa_browser/service.py
Dep: PostgreSQL + YAML step parser
Tesztek:
  test_create_config()               — create → RPAConfigRecord
  test_list_configs()                — list → RPAConfigRecord lista
  test_get_config()                  — get by id → RPAConfigRecord
  test_execute_logs_result()         — execute → RPAExecutionRecord
  test_delete_config()               — delete → True
```

#### 12. classifier — `ClassifierService` (optional LLM)

```
Fajl: src/aiflow/services/classifier/service.py
Dep: optional LLM (models_client)
Tesztek:
  test_classify_keywords_strategy()  — classify with keywords → ClassificationResult
  test_classify_confidence_above()   — confidence >= threshold → accepted
  test_classify_confidence_below()   — confidence < threshold → fallback triggered
  test_classify_ensemble()           — ensemble strategy → weighted merge
  test_health_check()                — health_check → True
```

#### 13. email_connector — `EmailConnectorService` (PostgreSQL, IMAP)

```
Fajl: src/aiflow/services/email_connector/service.py
Dep: PostgreSQL + IMAP/O365
Tesztek:
  test_create_config()               — create → config dict
  test_list_configs()                — list → config lista
  test_get_config()                  — get by id → config dict
  test_update_config()               — update → modified config
  test_delete_config()               — delete → True
```

### Teszt Fajl Struktura

```
tests/unit/services/           ← UJ KONYVTAR
  __init__.py
  test_cache_service.py        — 5 test (CacheService)
  test_rate_limiter_service.py — 5 test (RateLimiterService)
  test_resilience_service.py   — 5 test (ResilienceService)
  test_health_monitor_service.py — 5 test (HealthMonitorService)
  test_audit_service.py        — 5 test (AuditTrailService)
  test_schema_registry_service.py — 5 test (SchemaRegistryService)
  test_notification_service.py — 5 test (NotificationService)
  test_human_review_service.py — 5 test (HumanReviewService)
  test_media_processor_service.py — 5 test (MediaProcessorService)
  test_diagram_generator_service.py — 5 test (DiagramGeneratorService)
  test_rpa_browser_service.py  — 5 test (RPABrowserService)
  test_classifier_service.py   — 5 test (ClassifierService)
  test_email_connector_service.py — 5 test (EmailConnectorService)
```

### Tesztelesi Szabalyok

1. **Async tesztek** — minden teszt `async def test_*` + `@pytest.mark.asyncio`
2. **DB-fugg szolgaltatasok** — `asyncpg` mock-olas (`AsyncMock` pool/connection)
3. **Redis-fugg szolgaltatasok** — `fakeredis.aioredis` VAGY `AsyncMock` Redis client
4. **LLM-fugg szolgaltatasok** — `_call_llm` / `models_client.generate` patch
5. **Filesystem-fugg** — `tmp_path` fixture + test schema fajlok
6. **Minden teszt fajlhoz `@test_registry` header** a projekt konvencio szerint
7. **Nincs valos external service** — ez unit teszt, nem integration teszt!
8. **FONTOS:** A `tests/unit/services/` konyvtar UJ — eloszor `__init__.py` kell

### Mock Strategia (service tipusonkent)

```python
# PostgreSQL mock pattern (audit, human_review, notification, stb.)
@pytest.fixture
def mock_pool():
    pool = AsyncMock()
    conn = AsyncMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
    return pool, conn

# Redis mock pattern (cache, rate_limiter)
@pytest.fixture
def mock_redis():
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    return redis

# Filesystem mock pattern (schema_registry)
@pytest.fixture
def schema_dir(tmp_path):
    skill_dir = tmp_path / "skills" / "test_skill" / "schemas" / "v1"
    skill_dir.mkdir(parents=True)
    (skill_dir / "input.json").write_text('{"type": "object"}')
    return tmp_path
```

---

## VEGREHAJTAS SORRENDJE

```
--- LEPES 1: Konyvtar + infra ---
/dev-step "B2.1.0 — tests/unit/services/ konyvtar + conftest + mock fixtures"
  - tests/unit/services/__init__.py
  - tests/unit/services/conftest.py (mock_pool, mock_redis, mock_conn fixtures)

--- LEPES 2: In-memory service-ek (nincs external dep) ---
/dev-step "B2.1.1 — resilience + schema_registry + classifier tesztek (15 test)"
  - Ezek egyszeruek: nincs DB, nincs Redis (vagy csak filesystem)
  - 3 fajl × 5 teszt = 15 teszt

--- LEPES 3: Redis-fuggo service-ek ---
/dev-step "B2.1.2 — cache + rate_limiter tesztek (10 test)"
  - Redis mock/fakeredis
  - 2 fajl × 5 teszt = 10 teszt

--- LEPES 4: PostgreSQL-fuggo service-ek (CRUD) ---
/dev-step "B2.1.3 — audit + human_review + rpa_browser + email_connector tesztek (20 test)"
  - asyncpg mock pool pattern
  - 4 fajl × 5 teszt = 20 teszt

--- LEPES 5: Komplex service-ek (DB + external) ---
/dev-step "B2.1.4 — notification + health_monitor + media_processor + diagram_generator tesztek (20 test)"
  - Tobb dependency → tobb mock
  - 4 fajl × 5 teszt = 20 teszt

--- SESSION LEZARAS ---
/lint-check → 0 error
/regression → ALL PASS (1195 + 65 = 1260 unit test)
/update-plan → 58 progress B2.1 DONE
```

---

## KORNYEZET ELLENORZES

```bash
git branch --show-current                                    # → feature/v1.3.0-service-excellence
git log --oneline -3                                         # → d9df3ca, 7cec90b, 4b0d995
python -m pytest tests/unit/ -q --co 2>&1 | tail -1          # → ~1195 tests collected
.venv/Scripts/ruff check src/ tests/ 2>&1 | tail -1          # → All checks passed!
ls src/aiflow/services/ | wc -l                              # → 28+ (26 service + __init__.py + base stb.)
ls tests/unit/services/ 2>/dev/null                          # → NINCS MEG (B2.1 feladat!)
ls skills/*/guardrails.yaml                                  # → 5 fajl (B1.2 DONE)
```

---

## S22 TANULSAGAI (alkalmazando S23-ban!)

1. **Overlapping PII patterns** — `123-456-789` matchel `hu_taj` ES `phone`-ra is. A partial mode overlap-aware filtering-et igenyel. **Tanulsag:** regex pattern-ek atfedeseit mindig kezelni kell!
2. **`str(Enum)` vs `.value`** — `str(PIIMaskingMode.PARTIAL)` → `"PIIMaskingMode.PARTIAL"`, NEM `"partial"`. Mindig `.value`-t vagy `hasattr(x, "value")` check-et hasznalj!
3. **PostToolUse ruff hook** — az `import enum`-ot eltavolitja ha nincs felhasznalva. Az importot ES a hasznalatat EGYSZERRE kell hozzaadni!
4. **tier3_services.py crash** — `unstructured` library Windows access violation. ISMERT hiba, nem a mi kodunk. `--ignore` flag-gel kizarhato.
5. **Teszt strukturalas:** 31 tesztet 10 osztalyba szerveztuk — atlathatobb mint flat fuggvenyek. Service teszteknel is kovesd ezt a mintat!
6. **`_normalize_pii_masking` helper** — YAML loader-ben a normalizalas kulon helper fuggvenyben legyen, ne a `load_guardrail_config`-ban inline. Tesztelhetobb!

---

## SPRINT B UTEMTERV

```
S19: B0   — DONE (4b09aad) — 5-layer arch + qbpp + prompt API + OpenAPI
S20: B1.1 — DONE (f6670a1) — 4 LLM guardrail prompt + llm_guards.py + 27 promptfoo
S21: B1.2 — DONE (7cec90b) — 5 guardrails.yaml + PIIMaskingMode + 31 teszt
S22: B2.1 ← JELEN SESSION — Core infra service tesztek (65 test, Tier 1)
S23: B2.2 — v1.2.0 service tesztek (65 test, Tier 2)
S24: B3.1 — Invoice Finder: pipeline design + email + doc acquisition
S25: B3.2 — Invoice Finder: extract + report + notification (valos adat!)
S26: B3.5 — Konfidencia scoring hardening + confidence→review routing
S27: B4.1 — Skill hardening: aszf_rag + email_intent
S28: B4.2 — Skill hardening: process_docs + invoice + cubix + diagram
S29: B5   — Spec writer + diagram pipeline + koltseg baseline
S30: B6   — UI Journey audit + 4 journey tervezes + navigacio redesign
S31: B7   — Verification Page v2 (bounding box, diff, per-field confidence szin)
S32: B8   — UI Journey implementacio (top 3 journey + dark mode)
S33: B9   — Docker containerization + UI pipeline trigger + deploy teszt
S34: B10  — POST-AUDIT + javitasok
S35: B11  — v1.3.0 tag + merge
```

---

## FONTOS SZABALYOK (emlekeztetok)

- **`/dev-step` HASZNALANDÓ** — minden service-csoport kulon dev-step
- **Unit test = mock** — ez NEM integration test! Ne inditsd el a PostgreSQL/Redis-t, mockold.
- **Async pattern** — `@pytest.mark.asyncio` + `async def test_*()` — MINDEN tesztben
- **`@test_registry` header** — MINDEN teszt fajl elejen (projekt konvencio)
- **Fajlnev konvencio:** `test_{service_name}_service.py`
- **Kulon conftest.py** a `tests/unit/services/` konyvtarban — kozos mock fixtures
- **Ne duplikald** a meglevo teszteket (rate_limiter, audit, notification, health mar letezik mashol)
- **Feedback:** Session vegen command_feedback.md KOTELEZO

---

## B2 GATE CHECKLIST (B2.1 vegen)

```
[ ] tests/unit/services/ konyvtar letrehozva
[ ] conftest.py kozos mock fixtures (pool, redis, conn)
[ ] 13 service × 5 teszt = 65 teszt PASS
[ ] Minden teszt fajlban @test_registry header
[ ] /lint-check → 0 error
[ ] /regression → ALL PASS (1260+ unit test)
[ ] Nincs regresszio a meglevo tesztekben
```
