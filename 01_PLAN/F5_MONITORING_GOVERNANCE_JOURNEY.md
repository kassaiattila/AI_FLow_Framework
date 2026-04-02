# F5 Monitoring + Governance — User Journey

> **Fazis:** F5 (Monitoring + Governance)
> **Elozo fazisok:** F0-F4 TELJES (v0.12.0-complete-services)
> **Uj szolgaltatasok:** HealthMonitorService, AuditTrailService, AdminService
> **Tag:** `v1.0.0-rc1`

---

## F5a: Health Monitoring Journey

### Actor
**DevOps mernok / Rendszergazda** — az osszes szolgaltatas allapotat figyeli, riasztasokat kap leallaskor.

### Goal
Szolgaltatas-szintu health check → aggregalt dashboard → riasztasok.

### Steps
1. Monitoring Dashboard oldal megnyitasa (`/admin/monitoring`)
2. Szolgaltatasok allapotanak megtekintese (zold/sarga/piros)
3. Egyedi szolgaltatas reszletek (latency, success rate, uptime)
4. Riasztasi szabalyok konfiguracio

### API Endpoints (F5a)
| # | Method | Path | Purpose |
|---|--------|------|---------|
| 1 | GET | `/api/v1/admin/health` | Aggregalt health status (osszes service) |
| 2 | GET | `/api/v1/admin/health/{service}` | Egyedi service health (DB, Redis, LLM, stb.) |
| 3 | GET | `/api/v1/admin/metrics` | Service metrikak (p50, p95, success_rate) |

### UI Pages (F5a)
| Oldal | Route | Komponens | Fo funkcio |
|-------|-------|-----------|------------|
| Monitoring | `/admin/monitoring` | `MonitoringDashboard.tsx` | Health cards + metrikak |

### Success Criteria (F5a)
1. Minden F0-F4 service health check mukodik
2. DB + Redis + LLM status ellenorzes valos
3. Dashboard mutatja az osszes szolgaltatast szinekkel
4. Metrikak valos adatokkal (latency, success rate)
5. HU/EN nyelv valtas
6. Playwright E2E PASS

---

## F5b: Audit Trail Journey

### Actor
**Compliance officer / Vezeto** — minden AI muvelet nyomonkovetese, GDPR compliance.

### Goal
Immutable audit log → szures/export → adattorles (GDPR).

### Steps
1. Audit Log oldal megnyitasa (`/admin/audit`)
2. Muveletek szurese (idoszak, tipus, felhasznalo)
3. Reszletek megtekintese
4. Export (CSV/JSON)

### API Endpoints (F5b)
| # | Method | Path | Purpose |
|---|--------|------|---------|
| 1 | GET | `/api/v1/admin/audit` | Audit log lista (szurheto) |
| 2 | GET | `/api/v1/admin/audit/{id}` | Egyedi audit entry |
| 3 | POST | `/api/v1/admin/audit/export` | Export CSV/JSON |

### UI Pages (F5b)
| Oldal | Route | Komponens | Fo funkcio |
|-------|-------|-----------|------------|
| Audit Log | `/admin/audit` | `AuditLog.tsx` | Log tabla + szurok + export |

### Success Criteria (F5b)
1. Audit rekordok automatikusan keletkeznek API hivasoknal
2. Szures idoszak, tipus, felhasznalo szerint
3. Export CSV es JSON formatumban
4. HU/EN nyelv valtas
5. Playwright E2E PASS

---

## F5c: Admin API Journey

### Actor
**Adminisztrator** — felhasznalok, csapatok, API kulcsok kezelese.

### Goal
User/Team/API key CRUD → admin feluletrol.

### Steps
1. Admin Users oldal megnyitasa (`/admin/users`)
2. Felhasznalok letrehozasa/szerkesztese/torlese
3. API kulcsok generalasa es kezelese

### API Endpoints (F5c)
| # | Method | Path | Purpose |
|---|--------|------|---------|
| 1 | GET | `/api/v1/admin/users` | Felhasznalo lista |
| 2 | POST | `/api/v1/admin/users` | Felhasznalo letrehozas |
| 3 | GET | `/api/v1/admin/api-keys` | API kulcs lista |
| 4 | POST | `/api/v1/admin/api-keys` | API kulcs generalas |
| 5 | DELETE | `/api/v1/admin/api-keys/{id}` | API kulcs torles |

### Success Criteria (F5c)
1. User CRUD valos PostgreSQL-lel
2. API key generalas "aiflow_sk_" prefix-szel
3. Admin UI mukodik
4. Playwright E2E PASS

---

## Error Scenarios (F5 osszes)

| Hiba | UI viselkedes |
|------|--------------|
| Service unreachable | Piros statusz + "Service unavailable" |
| DB connection lost | Health check FAIL, banner |
| Redis timeout | Cache degraded warning |
| Audit write fail | Retry + alert admin |
| Invalid API key | 401 + "Invalid or expired API key" |
