# AIFlow v1.4.8 Sprint L — Session 113 Prompt (S113 — Cross-UC regression pack + v1.4.8 tag)

> **Datum:** 2026-04-24 (folytatas)
> **Branch:** `feature/v1.4.8-monitoring-cost` — folytatas S112 commit `58251de` utan.
> **HEAD prereq:** `58251de feat(policy): S112 — PolicyEngine.cost_cap enforcement + Costs cap banner`.
> **Port:** API 8102 | Frontend Vite 5173
> **Plan:** `01_PLAN/110_USE_CASE_FIRST_REPLAN.md` §4 Sprint L (S113 — cross-UC CI regression + PR + tag).
> **Session tipus:** REGRESSION + RELEASE. Code risk: LOW (test/config only). Process risk: MEDIUM (PR + tag touches main).

---

## KONTEXTUS

### Honnan jottunk (S112 DONE)

- S112 DONE `58251de` — PolicyEngine.cost_cap + Costs cap banner + Alembic 043.
- `cost_records.tenant_id` + `idx_cost_records_tenant_recorded` index live (head 043).
- `GET /api/v1/costs/cap-status` endpoint shipping (189 API endpoints total).
- `CostCapBreached` HTTP 429 mapped via FastAPI exception handler.
- Integration test `test_cost_cap_enforcement.py` 3/3 green.
- Costs.tsx now renders a 4-level alert banner (ok / warning / critical / exceeded).

### Hova tartunk — S113 scope

Cel: **Sprint L lezarasa** — cross-UC CI profile zold <10 perc alatt, PR cut + tag `v1.4.8`.

| Session | Scope | Acceptance |
|---|---|---|
| **S113 (this)** | Cross-UC regression pack: UC1 (Invoice) + UC2 (RAG) + UC3 (Email intent) + UC4-slices (Monitoring/Costs). CI profil <10 min. PR + tag. | CI profil GREEN; PR opened against `main`; tag `v1.4.8` queued. |

### Jelenlegi allapot (feature/v1.4.8-monitoring-cost @ 58251de)

```
27 service | 189 endpoint | 50 DB tabla | 43 Alembic migration (head: 043)
1995 unit | 75+ integration (S112 cost_cap_enforcement: 3) | 420 E2E
8 skill | 24+ UI oldal (Costs cap banner)
Sprint L S111 DONE | S112 DONE | S113 START (cross-UC regression + release)
```

---

## ELOFELTELEK

```bash
git branch --show-current            # feature/v1.4.8-monitoring-cost
git log --oneline -3                 # 58251de S112 elso sor
.venv/Scripts/python.exe -m ruff check src/ tests/ --quiet
cd aiflow-admin && npx tsc --noEmit && cd ..
PYTHONPATH="src;." .venv/Scripts/python.exe -m alembic current    # 043 (head)
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov    # 1995 pass
```

---

## FELADATOK

### LEPES 1 — Discovery (readonly ~10 min)

```bash
ls tests/regression_matrix.yaml tests/test_suites.yaml 2>&1
grep -rn "ci_profile\|cross_uc\|make ci" Makefile .github/ tests/ 2>&1 | head -20
ls .github/workflows/ 2>&1
```

Kerdesek:
- Van-e mar `ci_profile` a `tests/test_suites.yaml`-ban vagy kulon `make ci` target?
- A `regression_matrix.yaml` lefedi-e az uj `cost_cap` modosult fileokat (policy/, contracts/, state/cost_repository.py)?
- Megvan-e a 4 UC smoke suite (invoice_finder, aszf_rag_chat, email_intent_processor, monitoring)?

### LEPES 2 — Cross-UC CI profile osszeallitas

Uj/bovitett `tests/test_suites.yaml` bejegyzes:

```yaml
ci_cross_uc:
  description: "Sprint L CI gate — 4 UC smoke <10 min"
  target_duration_sec: 600
  includes:
    - tests/integration/services/invoice_finder/test_uc1_golden_path.py
    - tests/integration/services/rag_engine/test_ingest_uc2.py
    - tests/integration/services/email_connector/test_scan_and_classify.py
    - tests/integration/services/email_connector/test_intent_routing.py
    - tests/integration/test_cost_cap_enforcement.py
    - tests/integration/api/test_runs_trace.py
  excludes:
    - tests/integration/**/test_*_slow.py
```

Futtass egy teljes `ci_cross_uc` korr-t es meri a wall-clock-ot:

```bash
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest \
  tests/integration/services/invoice_finder/ \
  tests/integration/services/rag_engine/test_ingest_uc2.py \
  tests/integration/services/email_connector/ \
  tests/integration/test_cost_cap_enforcement.py \
  tests/integration/api/test_runs_trace.py \
  -q --no-cov 2>&1 | tail -10
```

Cel: `<10 min` wall-clock, 0 FAIL.

### LEPES 3 — `regression_matrix.yaml` frissites

Add hozza a mapping-et: `src/aiflow/policy/**`, `src/aiflow/state/cost_repository.py`, `src/aiflow/contracts/cost_attribution.py` → `ci_cross_uc` suite.

### LEPES 4 — PR + tag elokeszites

```bash
# PR description draft
cat > docs/sprint_l_pr_description.md <<'EOF'
# Sprint L — v1.4.8 Monitoring + Cost Enforcement

## Scope delivered (S111 + S112 + S113)
- S111: Langfuse trace drill-down + span-metrics API + TraceTree UI
- S112: PolicyEngine.cost_cap + CostAttribution contract + Alembic 043 + Costs cap banner
- S113: Cross-UC CI profile <10 min + regression matrix update

## Acceptance
- 1995 unit PASS
- ci_cross_uc profile <10 min GREEN (UC1 + UC2 + UC3 + UC4-slice)
- 3/3 cost_cap_enforcement integration PASS
- 5/5 S111 trace+span-metrics integration PASS

## Breaking changes
NONE — additive only (new column, new endpoint, new contract).

## Migration
alembic upgrade head  # 042 → 043 (tenant_id column + index)
EOF

# PR cut + tag queue
git push -u origin feature/v1.4.8-monitoring-cost
gh pr create --base main --title "v1.4.8 Sprint L — Monitoring + Cost Enforcement" \
  --body-file docs/sprint_l_pr_description.md
git tag -a v1.4.8 -m "v1.4.8 Sprint L — Monitoring + Cost Enforcement (S111-S113)"
git push origin v1.4.8
```

### LEPES 5 — Regression + session-close

```bash
.venv/Scripts/python.exe -m ruff check src/ tests/ --quiet
.venv/Scripts/python.exe -m ruff format --check src/ tests/
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov
# CLAUDE.md: bump Sprint L to DONE + tag v1.4.8 ref.
/session-close S113
```

---

## STOP FELTETELEK

**HARD:**
1. `ci_cross_uc` wall-clock >10 min → szuksegesek selektorok / xdist / testcontainers reuse.
2. Invoice UC1 teszt hianyzik vagy piros → kulon S113b ticket, ne kesleltesd a PR-t uj featureekkel.
3. PR review comment architekturat erinto — architect agent.

**SOFT:**
1. `tag v1.4.8` push sikertelen (perms) → manualis user akcio, PR review inditas onnallo.
2. Langfuse live trace verifikacio — env-fuggo, elegendo mock szelessag a suite-on belul.

---

## SESSION VEGEN

```
/session-close S113
```

Utana Sprint L ZARVA — a kovetkezo sprint kezdes uj branch-en a `main` merge utan.
