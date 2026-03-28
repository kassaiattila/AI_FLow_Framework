# AIFlow - Hibakezelés és Hibakeresés

## 1. Strukturalt Hiba Tipusok

### 1.1 Exception Hierarchia

```python
class AIFlowError(Exception):
    """Minden AIFlow hiba ebbol szarmazik."""
    error_code: str           # Gep-olvashato: "STEP_TIMEOUT", "BUDGET_EXCEEDED"
    is_transient: bool        # Ujraprobalassal javithato?
    http_status: int = 500

class TransientError(AIFlowError):
    """Atmeneti hibak - ujraprobalhatok."""
    is_transient = True

class PermanentError(AIFlowError):
    """Vegleges hibak - emberi beavatkozas kell."""
    is_transient = False
```

### 1.2 Transient Hibak (Ujraprobalhatok)

| Hiba | Kod | HTTP | Tipikus ok |
|------|-----|------|------------|
| LLMTimeoutError | LLM_TIMEOUT | 504 | OpenAI tullterheltseg |
| LLMRateLimitError | LLM_RATE_LIMIT | 429 | Rate limit tullepes |
| ExternalServiceError | EXTERNAL_SERVICE | 502 | Kroki/Langfuse/Miro elerhetetlenr |
| ConnectionError | CONNECTION_ERROR | 502 | Halozati hiba |

### 1.3 Permanent Hibak (Nem ujraprobalhatok)

| Hiba | Kod | HTTP | Tipikus ok |
|------|-----|------|------------|
| BudgetExceededError | BUDGET_EXCEEDED | 402 | Team/workflow koltsegkeret kimerult |
| QualityGateFailedError | QUALITY_GATE_FAILED | 422 | Minosegi kapu nem ment at (max retry utan) |
| InvalidInputError | INVALID_INPUT | 400 | Ervenytelen bemenet |
| WorkflowNotFoundError | WORKFLOW_NOT_FOUND | 404 | Ismeretlen workflow nev |
| AuthorizationError | UNAUTHORIZED | 403 | Nincs jogosultsag |
| CircuitBreakerOpenError | CIRCUIT_OPEN | 503 | Aramkor nyitva (tul sok hiba) |
| HumanReviewRequiredError | HUMAN_REVIEW_REQUIRED | 202 | Emberi felulvizsgalat szukseges |

### 1.4 Hiba Propagacio

```
Step hiba
  |
  +-- is_transient == true?
  |     |-- Igen -> RetryPolicy (exponential backoff, max 3x)
  |     |     |-- Sikerult -> Folytatas
  |     |     |-- Nem sikerult -> Circuit breaker check
  |     |           |-- Nyitva -> CircuitBreakerOpenError
  |     |           |-- Zarva -> PermanentError-re konvertalas
  |     |
  |     +-- Nem -> PermanentError
  |           |-- QualityGateFailed -> on_fail action (retry/escalate/human_review)
  |           |-- BudgetExceeded -> Workflow leallitas
  |           |-- Mas -> Workflow hiba, DLQ-ba kerul
```

---

## 2. Hibakeresés (Debugging)

### 2.1 Trace Rekonstrukcio

Minden workflow futtatas Langfuse trace-t kap:

```
Langfuse Trace: "process-documentation run abc123"
  |
  +-- Span: classify (420ms, SUCCESS)
  |   +-- Generation: gpt-4o-mini (350ms, 120 tokens)
  |   +-- Score: accuracy=0.95
  |
  +-- Span: elaborate (1200ms, SUCCESS)
  |   +-- Generation: gpt-4o (1100ms, 800 tokens)
  |
  +-- Span: extract (2300ms, FAILED)  <-- ITT A HIBA
  |   +-- Generation: gpt-4o (2200ms, ERROR: timeout)
  |   +-- Error: LLMTimeoutError
  |   +-- Retry 1: gpt-4o (1800ms, SUCCESS)
  |   +-- Score: completeness=0.72  <-- ALACSONY
  |
  +-- Span: review (800ms, FAILED)
      +-- Quality Gate: FAILED (0.72 < 0.80 threshold)
```

**Eleres:**
- `workflow_runs.trace_url` -> kozvetlen link Langfuse-hoz
- `workflow_runs.trace_id` -> API-bol lekerdeheto

### 2.2 Step-szintu Replay (Ujrajátszás)

**A legfontosabb debugging kepesseg!**

```bash
# Egyetlen step ujrafuttatasa az eredeti inputtal
aiflow workflow replay --run-id abc123 --from-step extract

# Mi tortenik:
# 1. Betolti a workflow_run-t PostgreSQL-bol
# 2. Betolti az "extract" elotti step checkpoint-jat
# 3. Ujrafuttatja extract-tol elore az eredeti input-tal
# 4. Uj workflow_run rekord, metadata.replayed_from = abc123
```

**Miert mukodik?** Mert minden step utan `step_runs.checkpoint_data` JSONB-ben
el van mentve az aktualis allapot. A `WorkflowRunner.resume()` innen folytut.

### 2.3 Input/Output Inspekció Per Lépés

```bash
# CLI-bol
aiflow workflow inspect --run-id abc123

# Kimenet:
Workflow: process-documentation v2.0.0
Status: FAILED
Duration: 4720ms
Cost: $0.042
Trace: https://langfuse.com/trace/abc123

Steps:
  1. classify    [SUCCESS]  420ms  $0.002
     Input:  {"message": "Szabadsag igenylesi folyamat..."}
     Output: {"category": "process", "confidence": 0.95}

  2. elaborate   [SUCCESS]  1200ms  $0.015
     Input:  {"text": "Szabadsag igenylesi..."}
     Output: {"elaborated": "A szabadsag igenyles folyamata..."}

  3. extract     [FAILED->RETRIED->SUCCESS]  4100ms  $0.020
     Input:  {"text": "A szabadsag igenyles..."}
     Output: {"steps": [...], "actors": [...]}
     Scores: {"completeness": 0.72}
     Retries: 1 (LLMTimeoutError)

  4. review      [FAILED]  800ms  $0.005
     Quality Gate: FAILED (completeness 0.72 < 0.80)
     Action: human_review
```

### 2.4 Strukturalt Logging (JSON)

```json
{
  "timestamp": "2026-03-27T10:15:30Z",
  "level": "error",
  "event": "step_failed",
  "run_id": "abc123",
  "step": "extract",
  "skill": "process_documentation",
  "error_type": "LLMTimeoutError",
  "error_code": "LLM_TIMEOUT",
  "is_transient": true,
  "model": "gpt-4o",
  "duration_ms": 30000,
  "retry_count": 0,
  "team_id": "finance",
  "user_id": "user@company.com"
}
```

**Kereshetoseg:** `run_id`-vel barmely log aggregatorban (ELK, Loki, CloudWatch)
szurheto az adott workflow futtatas OSSZES log sora.

---

## 3. Dead Letter Queue (DLQ)

### 3.1 DLQ Feldolgozasi Folyamat

```
Workflow run FAILED (retry-k kimerultek)
  |
  +-- Automatikus klasszifikacio:
  |     |-- Transient hiba? -> Kesleltett ujraprobas (exp. backoff, max 24 ora)
  |     |-- Permanent hiba? -> Alert + manualis felulvizsgalat
  |
  +-- Alert kuldes (Slack/email):
  |     "Workflow 'process-doc' failed: LLM_TIMEOUT
  |      Run ID: abc123
  |      Trace: https://langfuse.com/trace/abc123
  |      Team: finance
  |      Error: 3x timeout on extract step"
  |
  +-- Admin UI / API:
        GET /api/v1/jobs/dlq            # DLQ lista
        GET /api/v1/jobs/dlq?error_type=LLM_TIMEOUT  # Szures
        POST /api/v1/jobs/dlq/{id}/replay  # Ujrasorolas
        DELETE /api/v1/jobs/dlq/{id}       # Torles (megoldott)
```

### 3.2 Alerting Szintek

| Szint | Feltetel | Csatorna | Valaszido |
|-------|----------|----------|-----------|
| P1 CRITICAL | Success rate < 90% (5 perc) | PagerDuty + Slack #critical | 15 perc |
| P2 HIGH | Success rate < 95% (30 perc) | Slack #alerts | 1 ora |
| P3 MEDIUM | DLQ melyseg > 50 | Slack #alerts | 4 ora |
| P4 LOW | Egyedi workflow hiba | Skill team Slack channel | Kovetkezo munkanap |

---

## 4. Hibakezelesi Mintak Workflow-kban

### 4.1 Graceful Degradation (Kecses Leromlás)

```python
@step(
    name="elaborate",
    timeout=30,
    retry=RetryPolicy(max_retries=2),
)
async def elaborate(input_data: ElaborateInput, ctx: ExecutionContext, llm: LLMClient):
    try:
        result = await llm.generate(...)
        return ElaborateOutput(text=result.elaborated, improved=True)
    except (LLMTimeoutError, LLMRateLimitError):
        # Fallback: eredeti szoveg hasznalata javitas nelkul
        return ElaborateOutput(text=input_data.original_text, improved=False)
```

### 4.2 Quality Gate Hibakezelés

```python
@workflow(name="process-documentation")
def process_doc(wf: WorkflowBuilder):
    wf.step(extract)
    wf.quality_gate(
        after="extract",
        gate=QualityGate(
            metric="completeness",
            threshold=0.80,
            on_fail="refine",       # Automatikus javitas
            max_iterations=3,        # Max 3 iteracio
            on_exhausted="human_review",  # Ha 3 iteracio sem eleg -> ember
        )
    )
    wf.step(refine, depends_on=["extract"])
    wf.edge("refine", "extract")  # Loop back
```

### 4.3 Circuit Breaker

```
Allapotok:
  CLOSED (normal) -> 5 hiba 1 percen belul -> OPEN
  OPEN (blokkol) -> 60 mp varakozas -> HALF_OPEN
  HALF_OPEN (teszteles) -> 3 sikeres -> CLOSED
                        -> 1 hiba -> OPEN

Tarolás: Redis (elosztott, tobbszor peldany eseten is konzisztens)
Scope: Per-model (pl. gpt-4o circuit breaker kulon a gpt-4o-mini-tol)
```

---

## 5. Koltseg-alapu Hibavedelem

```python
# Budget ellenorzes minden LLM hivas elott
async def _check_budget(ctx: ExecutionContext, estimated_cost: float):
    if ctx.budget_remaining_usd < estimated_cost:
        raise BudgetExceededError(
            f"Budget remaining: ${ctx.budget_remaining_usd:.4f}, "
            f"estimated cost: ${estimated_cost:.4f}"
        )

# Team budget ellenorzes
async def _check_team_budget(team_id: str, estimated_cost: float):
    budget = await cost_tracker.get_team_budget_status(team_id)
    if budget.usage_pct >= 100:
        raise BudgetExceededError(f"Team '{team_id}' monthly budget exhausted")
    if budget.usage_pct >= 80:
        await alert("budget_warning", team_id=team_id, usage_pct=budget.usage_pct)
```

---

## 6. Crash Recovery Protocol

### Mi tortenik ha egy worker processz osszezomlik futas kozben?

**Detektalas:**
1. Worker heartbeat timeout (30 masodperc)
   - Minden worker 10 masodpercenkent heartbeat-et kuld Redis-be
   - Ha 3 egymast koveto heartbeat elmarad -> worker halottnak tekintett
2. arq job timeout (configurable per workflow)
   - Ha a job nem fejezodik be az eloirt idon belul -> timeout

**Automatikus Recovery:**
1. Orphan run detektalas:
   ```sql
   SELECT id FROM workflow_runs
   WHERE status = 'running'
     AND updated_at < NOW() - INTERVAL '5 minutes'
     AND job_id NOT IN (SELECT job_id FROM active_workers);
   ```
2. Re-queue:
   - Checkpoint letezik? -> resume from checkpoint (WorkflowRunner.resume())
   - Nincs checkpoint? -> restart from beginning, metadata.restarted=true
3. Max restart limit: 3 (utana DLQ-ba kerul)

**Atomicitasi garanciak:**
- Step completion + checkpoint write = egyetlen DB tranzakcio
- Ha a tranzakcio nem commitolodik -> a step nem szamit befejezettnek
- Resume mindig az utolso SIKERESEN COMMITOLT checkpoint-tol indul

**LLM reszleges valasz:**
- Ha az LLM valasz megerkezett de a feldolgozas nem fejezodott be:
  - A valasz NINCS mentve (nem commitolt tranzakcio)
  - Resume ujra hivja az LLM-et (at-least-once semantika)
  - Koltseg: dupla LLM hivas (elfogadhato a megbizhato recovery erdekeben)
