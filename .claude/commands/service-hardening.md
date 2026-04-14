Run the 10-point production checklist audit for an AIFlow skill or service.

Arguments: $ARGUMENTS
(Required: skill or service name, e.g. "aszf_rag_chat", "email_connector", "all")

## 10-Point Production Checklist

For the given skill/service, check EACH point and report PASS/FAIL:

### 1. UNIT TESZT
- Minimum 5 unit test letezik
- Coverage >= 70% az adott modulon
- `pytest tests/unit/{module}/ -v --cov`

### 2. INTEGRACIO
- Legalabb 1 teszt valos DB-vel fut (ha DB-t hasznal)
- Docker PostgreSQL + Redis szukseges

### 3. API TESZT
- Minden kapcsolodo endpoint curl-lel tesztelve
- `curl -s http://localhost:8102/api/v1/{endpoint}` → 200 OK
- Response tartalmazza: `"source": "backend"` (NEM "demo")

### 4. PROMPT TESZT (ha LLM-et hasznal)
- Promptfoo konfiguracio letezik: `skills/{name}/tests/promptfooconfig.yaml`
- `npx promptfoo eval` → >= 95% pass rate
- Ha nincs LLM: N/A

### 5. ERROR HANDLING
- Minden exception AIFlowError leszarmazott
- `is_transient` flag beallitva (retry logika)
- Nincs csupasz `except Exception` a kodban

### 6. LOGGING
- structlog hasznalat (NEM print(), NEM logging.info())
- `logger.info("event_name", key=value)` formatum
- Nincs PII a log uzenetekben

### 7. DOKUMENTACIO
- Fo osztaly: docstring (cel, hasznalat, peldak)
- Publikus metodusok: docstring (parameterek, return)
- README.md a modul mappaban (opcionalis de ajanlott)

### 8. UI
- Kapcsolodo oldal mukodik (ha van UI)
- Source badge lathato ("Backend" / "Demo")
- 0 console error Playwright-ban

### 9. INPUT GUARDRAIL
- Injection vedelem aktiv (InputGuard)
- PII masking helyes (per-skill config!):
  - aszf_rag: ON | email_intent: PARTIAL | invoice: OFF | process_docs: ON | cubix: ON | invoice_finder: OFF | spec_writer: ON

### 10. OUTPUT GUARDRAIL
- Hallucination check (OutputGuard)
- Scope check (ScopeGuard — in/out/dangerous)
- PII leak check (response-ban nincs varatlan PII)

## Output Formatum

```
=== SERVICE HARDENING: {name} ===

| # | Check | Status | Details |
|---|-------|--------|---------|
| 1 | Unit test | PASS/FAIL | X tests, Y% coverage |
| 2 | Integration | PASS/FAIL/N/A | |
| 3 | API test | PASS/FAIL | X endpoints tested |
| 4 | Prompt test | PASS/FAIL/N/A | X% pass rate |
| 5 | Error handling | PASS/FAIL | |
| 6 | Logging | PASS/FAIL | |
| 7 | Documentation | PASS/FAIL | |
| 8 | UI | PASS/FAIL/N/A | |
| 9 | Input guardrail | PASS/FAIL | |
| 10 | Output guardrail | PASS/FAIL | |

SCORE: X/10
VERDICT: PRODUCTION-READY / NEEDS WORK (lista)
```

Ha "all": futtasd mind a 7 skill-re + az infrastruktura service-ekre.
