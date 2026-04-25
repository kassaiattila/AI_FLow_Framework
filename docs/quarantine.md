# Flaky Test Quarantine Log

Per `tests/CLAUDE.md`: flaky tests are quarantined, fixed within 5 days, never deleted.
Each entry lists the test, quarantine date, owner, root-cause hypothesis, and fix deadline.

## Active quarantine

_(none)_

## Resolved quarantine

### `tests/unit/services/test_resilience_service.py::TestResilienceService::test_circuit_opens_on_failures`

- **Quarantined:** 2026-04-25 (Session S104, Sprint J close)
- **HEAD at quarantine:** `5ec83e2` (feature/v1.4.6-rag-chat)
- **Resolved:** 2026-05-04 (Sprint O FU-5; deadline 2026-04-30 was 4 days past)
- **Resolved by:** `Clock` seam injected via `ResilienceService(clock=...)` →
  `_CircuitBreaker(rule, *, clock=None)`. Defaults to `time.monotonic`; tests
  pin a constant clock to make the OPEN→HALF_OPEN recovery deterministic.
- **Original symptom:** intermittent FAIL in full-suite runs; PASS in
  isolation. Loop uses 3 `fail_func` exhaustions to hit
  `circuit_failure_threshold=3` against a 50 ms
  `circuit_recovery_timeout_seconds`; under heavy test-suite load the
  `time.monotonic` tick drift occasionally elapsed the 50 ms recovery
  window mid-loop and let the 4th call short-circuit through HALF_OPEN
  instead of raising `CircuitBreakerOpenError`. (The original quarantine
  note attributed this to `datetime.utcnow()` — actual call site was
  already `time.monotonic`; the underlying time-sensitivity diagnosis
  was correct, the API pointer wasn't.)
- **Fix:** option (1) from the original options list — Clock seam.
  `_CircuitBreaker.__init__(rule, *, clock=None)` accepts an injectable
  clock; `ResilienceService.__init__(config, *, clock=None)` plumbs it
  through to every breaker it spawns. Pre-existing call sites are
  unchanged (default behaviour identical).
- **Verification:** `pytest tests/unit/services/test_resilience_service.py -v`
  → 5/5 PASS deterministic; the prior `@pytest.mark.xfail` decorator was
  removed.

## Conditional skips (intentional, not flake)

These tests skip themselves unless an environment is provisioned. They
are NOT flake-quarantine entries — the skip is a feature, not a regression.

### `tests/unit/providers/embedder/test_azure_openai.py::test_azure_openai_embed_real_api`

- **Skip condition:** `AIFLOW_AZURE_OPENAI__ENDPOINT` AND
  `AIFLOW_AZURE_OPENAI__API_KEY` env vars unset.
- **Why:** Profile B (Azure OpenAI) live round-trip against the real
  Azure endpoint. Provisioning + billable Azure credit is operator-level;
  the test runs only when the operator explicitly enables it.
- **Tracker ID:** `SS-SKIP-2` (Sprint S retro carry-forward; lifts when
  Azure credit lands).
- **Local effect:** `pytest tests/unit/` reports `2379 passed, 1 skipped`
  on developer workstations + CI without Azure creds. This is the
  expected steady state, not a regression.
- **Audit history:** S147 LEPES 1b inventoried this skip on 2026-04-25
  to reconcile the CLAUDE.md "1 skipped" count with the absent flake
  registry.
