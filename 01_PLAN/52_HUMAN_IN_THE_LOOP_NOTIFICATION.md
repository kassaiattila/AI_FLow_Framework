# AIFlow v1.2.0 — Human-in-the-Loop & Notification Service

> **Szulo terv:** `48_ORCHESTRABLE_SERVICE_ARCHITECTURE.md` (Phase 6A + HITL bovites)
> **Cel:** Professzionalis review UI (verify/approve/reject) + multi-csatornas ertesitesek.

---

## 1. Jelenlegi Allapot

### Human Review

| Komponens | Allapot | Korlat |
|-----------|---------|--------|
| `HumanReviewService` | Mukodik (basic queue, `human_review_queue` tabla — migration 022) | Nincs prioritas-alapu SLA, nincs eszkalacio |

> **FONTOS:** Ket human review tabla letezik a DB-ben:
> - `human_reviews` (migration 008) — regi, workflow_run_id + step_name alapu → **DEPRECATED**
> - `human_review_queue` (migration 022) — uj, entity_type + entity_id alapu → **EZT BOVITJUK**
| `Reviews.tsx` | Mukodik (lista + approve/reject) | Nincs inline dokumentum megjelentes |
| `Verification.tsx` | Mukodik (split-screen PDF + editor) | Csak invoice tipusra, nincs altalanos review |
| API endpoints | 6 endpoint (CRUD + approve/reject) | Nincs bulk approve, nincs assign |

### Notification

| Komponens | Allapot |
|-----------|---------|
| Email kuldes | NINCS (csak email *fogadas* van az EmailConnectorService-ben) |
| Slack/Teams | NINCS |
| Webhook | NINCS |
| In-app ertesites | NINCS |

---

## 2. Human-in-the-Loop Bovites

### 2.1 Review Workflow (bovitett)

```
Dokumentum/Email/Szamla bekerkezik
         │
         ▼
┌─────────────────────┐
│ CONFIDENCE CHECK     │
│ conf >= 0.90 → AUTO │
│ 0.70-0.90 → REVIEW  │
│ conf < 0.70 → REJECT│
└────────┬────────────┘
         │ REVIEW
         ▼
┌─────────────────────────────────────────┐
│ REVIEW QUEUE                             │
│ ┌────────┐ ┌─────────┐ ┌──────────────┐│
│ │PENDING │→│ASSIGNED │→│IN_REVIEW     ││
│ └────────┘ └─────────┘ └──────┬───────┘│
│                                │        │
│                    ┌───────────┼────────┐│
│                    ▼           ▼        ▼│
│              ┌─────────┐ ┌────────┐ ┌────┐│
│              │APPROVED │ │REJECTED│ │REDO││
│              └─────────┘ └────────┘ └────┘│
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────┐
│ POST-REVIEW ACTIONS  │
│ • File route         │
│ • Notification       │
│ • Pipeline trigger   │
└─────────────────────┘
```

### 2.2 Bovitett HumanReviewService

```python
class HumanReviewService(BaseService):
    # Meglevo
    async def create_review(entity_type, entity_id, title, ...) -> HumanReviewItem
    async def list_pending(limit) -> list[HumanReviewItem]
    async def approve(review_id, reviewer, comment) -> HumanReviewItem
    async def reject(review_id, reviewer, comment) -> HumanReviewItem
    
    # UJ
    async def assign(review_id, assignee) -> HumanReviewItem
    async def reassign(review_id, new_assignee, reason) -> HumanReviewItem
    async def bulk_approve(review_ids, reviewer, comment) -> list[HumanReviewItem]
    async def bulk_reject(review_ids, reviewer, comment) -> list[HumanReviewItem]
    async def request_redo(review_id, reviewer, comment) -> HumanReviewItem
    async def get_stats(period) -> ReviewStats
    async def get_sla_status() -> SLAStatus
    async def escalate(review_id, reason) -> HumanReviewItem

class ReviewStats(BaseModel):
    total_pending: int
    total_reviewed_today: int
    avg_review_time_minutes: float
    approval_rate: float
    by_priority: dict[str, int]       # {"critical": 3, "high": 5, ...}
    by_entity_type: dict[str, int]    # {"invoice": 10, "contract": 3}

class SLAConfig(BaseModel):
    critical_max_hours: int = 2
    high_max_hours: int = 8
    normal_max_hours: int = 24
    low_max_hours: int = 72
    escalation_email: str | None = None
```

### 2.3 Review UI Tervek

**Celpont: Professzionalis review felhasznaloi elmeny**

**Review Queue Page (bovitett Reviews.tsx):**
- Prioritas szerinti rendezés (critical piros, high narancssarga)
- SLA countdown (hany ora van hatra)
- Assignee oszlop + assign-to-me gomb
- Bulk select + bulk approve/reject
- Szurok: entity_type, priority, assignee, date range
- Statisztikak: pending count, avg review time, approval rate

**Universal Review Detail Page (UJ):**
- **Bal oldal (60%):** Dokumentum megjelenitese (tipus-fuggoen):
  - Invoice → PDF + bounding box overlay (meglevo Verification minta)
  - Email → HTML body + csatolmanyok
  - RAG chunk → szoveg + metadata + relevancia score
  - General → JSON viewer + raw text
- **Jobb oldal (40%):** Review panel:
  - Kinyert adatok (szerkesztheeto formban)
  - Konfidencia score vizualizacio
  - Validacios hibak listaja
  - Elozmenyek (korabbi review-k ugyanazon entity-re)
  - Approve / Reject / Request Redo gombok
  - Comment mezo
- **Also sav:** Navigacio elozo/kovetkezo review item-re (keyboard shortcut: J/K)

**Keyboard shortcutok:**
- `A` = Approve
- `R` = Reject
- `E` = Edit mode
- `J/K` = Elozo/Kovetkezo item
- `Ctrl+Enter` = Submit decision

---

## 3. Notification Service

### 3.1 Architektura

```python
class NotificationService(BaseService):
    """Multi-channel notification service."""
    
    async def send(
        self,
        channel: str,           # "email", "slack", "teams", "webhook", "in_app"
        template: str,          # Jinja2 template vagy template nev
        data: dict,             # Template valtozok
        recipients: list[str],  # Email ciimek / Slack channel-ek / webhook URL-ek
        config_name: str | None = None  # Elore konfiguralt csatorna nev
    ) -> NotificationResult:
        ...

    async def send_batch(
        self,
        notifications: list[NotificationRequest]
    ) -> list[NotificationResult]:
        ...

    # Csatorna CRUD
    async def list_channels() -> list[ChannelConfig]
    async def create_channel(config: ChannelConfig) -> ChannelConfig
    async def update_channel(channel_id, config: ChannelConfig) -> ChannelConfig
    async def delete_channel(channel_id) -> bool
    async def test_channel(channel_id) -> bool

class NotificationResult(BaseModel):
    channel: str
    sent: bool
    message_id: str | None
    recipient: str
    error: str | None
    sent_at: datetime
```

### 3.2 Csatorna Implementaciok

| Csatorna | Backend | Fuggoseg | Config |
|----------|---------|----------|--------|
| **email** | SMTP (aiosmtplib) | `pip install aiosmtplib` | host, port, from, credentials |
| **slack** | Webhook URL (httpx) | Mar van (httpx) | webhook_url |
| **teams** | Webhook URL (httpx) | Mar van | webhook_url |
| **webhook** | HTTP POST (httpx) | Mar van | url, headers, auth_type |
| **in_app** | PostgreSQL tabla | Mar van | — (belso) |

### 3.3 Template Rendszer

```yaml
# prompts/notifications/invoice_processed.yaml
name: invoice_processed
channel: email
subject: "AIFlow: {{ count }} szamla feldolgozva"
body: |
  Tisztelt {{ recipient_name }}!
  
  Az alabbi szamlak automatikusan feldolgozasra kerultek:
  
  {% for inv in invoices %}
  - {{ inv.vendor_name }}: {{ inv.total_amount }} {{ inv.currency }}
    Allapot: {{ inv.status }}
    Konfidencia: {{ "%.0f"|format(inv.confidence * 100) }}%
  {% endfor %}
  
  {% if review_needed > 0 %}
  {{ review_needed }} szamla emberi review-ra var: {{ review_url }}
  {% endif %}
  
  Udvozlettel,
  AIFlow Automatizacio
```

### 3.4 DB (Alembic 028)

```sql
-- Notification csatornak konfiguracioja
CREATE TABLE notification_channels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    channel_type VARCHAR(50) NOT NULL,
    config JSONB NOT NULL,            -- encrypted credentials
    enabled BOOLEAN DEFAULT true,
    team_id UUID REFERENCES teams(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Notification log (audit trail)
CREATE TABLE notification_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel_id UUID REFERENCES notification_channels(id),
    channel_type VARCHAR(50) NOT NULL,
    recipient VARCHAR(500) NOT NULL,
    template_name VARCHAR(255),
    subject VARCHAR(500),
    status VARCHAR(20) NOT NULL,       -- sent, failed, pending
    error TEXT,
    pipeline_run_id UUID REFERENCES workflow_runs(id),
    sent_at TIMESTAMPTZ DEFAULT NOW()
);

-- In-app notifications
CREATE TABLE in_app_notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    title VARCHAR(500) NOT NULL,
    body TEXT,
    link VARCHAR(500),
    read BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 4. Pipeline Integracio

### 4.1 Review mint Pipeline Step

```yaml
# Pipeline-ban hasznalhato HITL step
- name: human_review
  service: human_review
  method: create_and_wait     # Letrehozza es VARJA a dontest
  depends_on: [extract_data]
  condition: "output.confidence < 0.90"
  config:
    entity_type: invoice
    entity_id: "{{ extract_data.output.db_id }}"
    title: "Szamla review: {{ extract_data.output.vendor_name }}"
    priority: "{{ 'critical' if extract_data.output.total_amount > 500000 else 'normal' }}"
    timeout_hours: 24
    on_timeout: auto_approve   # vagy: reject, escalate
```

### 4.2 Notification mint Pipeline Step

```yaml
- name: notify_team
  service: notification
  method: send
  depends_on: [validate_and_route]
  config:
    channel: email
    config_name: bestix_smtp     # Elore konfiguralt csatorna
    template: invoice_processed  # Template nev
    data:
      invoices: "{{ validate_and_route.output.results }}"
      review_needed: "{{ validate_and_route.output.review_count }}"
      review_url: "https://admin.bestix.hu/reviews"
    recipients: ["konyvelo@bestix.hu"]
```

---

## 5. Fejlesztesi Fazisok

| Fazis | Feladat | Becsult meret |
|-------|---------|---------------|
| **1** | NotificationService core (send + channel CRUD) | ~300 sor |
| **2** | Email csatorna (aiosmtplib) + Slack webhook | ~200 sor |
| **3** | Notification template rendszer (YAML + Jinja2) | ~150 sor |
| **4** | HumanReviewService bovites (assign, bulk, SLA, stats) | ~300 sor |
| **5** | Review Detail UI (universal, split-screen) | ~500 sor |
| **6** | Pipeline adapter-ek (notification + human_review) | ~200 sor |
| **7** | DB migraciok (028: channels + log + in-app) | ~50 sor |

---

## 6. Verifikacio

### Notification teszt:
```bash
# Email kuldes teszt
curl -X POST /api/v1/notifications/test \
  -d '{"channel_id": "...", "recipient": "test@bestix.hu"}'

# Pipeline-bol:
# invoice pipeline → notification step → email megjelenik a postafiokban
```

### HITL teszt:
```bash
# Review letrehozas
curl -X POST /api/v1/reviews \
  -d '{"entity_type": "invoice", "entity_id": "...", "title": "Test", "priority": "high"}'

# Playwright E2E:
# Navigate → Reviews → approve gomb → status valtozik
# Navigate → Review Detail → split-screen → edit → approve → file moved
```
