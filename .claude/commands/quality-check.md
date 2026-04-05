Run LLM quality and cost analysis for a service or pipeline.

## Input
$ARGUMENTS — skill name, service name, or "all" for full report

## Steps

### 1. Run Promptfoo Evaluation
```bash
# Single skill:
npx promptfoo eval -c skills/$ARGUMENTS/tests/promptfooconfig.yaml \
  --output tests/artifacts/quality/

# All skills:
npx promptfoo eval -c skills/*/tests/promptfooconfig.yaml \
  --output tests/artifacts/quality/
```

### 2. Collect Cost Data
```bash
TOKEN=$(curl -sf -X POST http://localhost:8102/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin@bestix.hu","password":"admin"}' | python -c "import sys,json; print(json.load(sys.stdin)['token'])")

# Cost breakdown by model:
curl -sf -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8102/api/v1/costs/breakdown" | python -m json.tool

# Daily costs:
curl -sf -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8102/api/v1/costs/team-daily" | python -m json.tool
```

### 3. Calculate Metrics
- **Quality:** pass rate (target >= 90%), per-assertion scores
- **Cost:** total USD, per-model breakdown, cost per query average
- **Latency:** avg response time, P95

### 4. Compare with Previous
- Load previous results from `tests/artifacts/quality/` (if exists)
- Calculate delta: quality change, cost change
- Flag regressions: quality dropped > 5% or cost increased > 20%

### 5. Report
```
=== QUALITY & COST REPORT ===
Skill: $ARGUMENTS
Date: $(date)

QUALITY:
  Pass rate: XX% (target: 90%)
  Rubric scores: relevance=X.X, faithfulness=X.X, completeness=X.X

COST:
  Total: $X.XX
  By model:
    openai/gpt-4o-mini: $X.XX (N calls)
    openai/gpt-4o: $X.XX (N calls)
  Cost per query: $X.XXX avg

REGRESSIONS:
  [NONE | list of regressions]

RECOMMENDATIONS:
  [model downgrade opportunities, prompt optimization suggestions]
```

### 6. Save Results
- Save to `tests/artifacts/quality/{date}_{skill}.json`

## MANDATORY Rules
- VALOS LLM hivasok (Promptfoo), NEM mock
- Results saved to `tests/artifacts/quality/`
- Compare with baseline if available
- Flag ANY regression (quality drop > 5% or cost increase > 20%)
