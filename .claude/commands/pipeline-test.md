Test a pipeline definition end-to-end with REAL services (SOHA NE mock/fake!).

## Input
$ARGUMENTS — pipeline name or YAML file path

## Steps

### 1. Load Pipeline
- If name: load from DB via `GET /api/v1/pipelines/{name}`
- If file path: read YAML from file
- Show pipeline summary (steps, services, trigger)

### 2. Validate
- Compile to DAG via `PipelineCompiler`
- Check adapter availability for EVERY step
- Report any missing adapters

### 3. Prepare Test Input
- Show required input schema
- Ask user for test input data (or use defaults from pipeline YAML)

### 4. Execute Pipeline
```bash
# Via API:
TOKEN=$(curl -sf -X POST http://localhost:8102/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin@bestix.hu","password":"admin"}' | python -c "import sys,json; print(json.load(sys.stdin)['token'])")

curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  "http://localhost:8102/api/v1/pipelines/{id}/run" \
  -d '{"input_data": {...}}'
```

### 5. Verify Results
Check ALL of these (MINDEN KOTELEZO):
- [ ] Pipeline run status = "completed" (nem "failed")
- [ ] `workflow_runs` row created with `pipeline_id` FK
- [ ] `step_runs` rows for EVERY step in pipeline
- [ ] `cost_records` entries for LLM-using steps
- [ ] No Python exceptions in API logs
- [ ] Output data is valid (not empty, not error)

### 6. Report
- Step-by-step results table (name, status, duration_ms, cost_usd)
- Total pipeline duration and cost
- Any errors or warnings
- PASS/FAIL verdict

## MANDATORY Rules
- VALOS futatas, NEM mock — same rule as /dev-step
- Ha barmelyik step FAIL → report error, NEM "kesobb javitjuk"
- Cost tracking MUST work — check cost_records table
- L0 smoke test MUST pass BEFORE pipeline test
