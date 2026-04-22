# Flaky Test Quarantine Log

Per `tests/CLAUDE.md`: flaky tests are quarantined, fixed within 5 days, never deleted.
Each entry lists the test, quarantine date, owner, root-cause hypothesis, and fix deadline.

## Active quarantine

### `tests/unit/services/test_resilience_service.py::TestResilienceService::test_circuit_opens_on_failures`

- **Quarantined:** 2026-04-25 (Session S104, Sprint J close)
- **HEAD at quarantine:** `5ec83e2` (feature/v1.4.6-rag-chat)
- **Owner:** resilience-service (unassigned; pick up in Sprint K)
- **Fix deadline:** 2026-04-30 (5 days per policy)
- **Marker:** `@pytest.mark.xfail(strict=False, reason="...")` — runs, reports XFAIL on flake, XPASS on success, never fails the suite.
- **Symptom:** intermittent FAIL in full-suite runs; PASS in isolation. Loop uses 3 `fail_func` exhaustions to hit `circuit_failure_threshold=3` against a 50ms `circuit_recovery_timeout_seconds`; under heavy test-suite load the `utcnow()` tick drift occasionally opens a half-open window mid-loop and short-circuits the expected `ValueError` path with `CircuitBreakerOpenError`.
- **Root-cause hypothesis:** time-sensitive circuit-breaker state machine keyed on wall-clock `datetime.utcnow()` with a 50ms recovery window — unfit for a unit-test timescale. Options:
  1. Inject a `clock` seam (`time.monotonic` or a `Clock` protocol) into `ResilienceService` so the test can advance time deterministically.
  2. Widen `circuit_recovery_timeout_seconds` to e.g. 500ms in the fixture (trades test speed for stability).
  3. Move the scenario to `tests/integration/` with freeze-time control.
- **Recommended fix:** option (1) — adds a Clock seam, deterministic, keeps unit-speed. Track as follow-up issue in Sprint J retro.
- **Re-enable command:** remove the `@pytest.mark.xfail(...)` decorator once the root-cause fix lands.

## Resolved quarantine

_(none)_
