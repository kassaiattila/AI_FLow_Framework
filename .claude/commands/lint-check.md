Run full codebase lint and type check with summary report.

Arguments: $ARGUMENTS
(Optional: `--fix` to auto-fix safe issues, `--scope src|tests|skills|admin|all` to limit scope)

## Steps

### 1. Ruff Lint Check
Run ruff check on each area separately and collect statistics:

```bash
cd "$PROJECT_ROOT"
echo "=== src/aiflow/ ==="
.venv/Scripts/python.exe -m ruff check src/aiflow/ --statistics 2>&1
echo "=== tests/ ==="
.venv/Scripts/python.exe -m ruff check tests/ --statistics 2>&1
echo "=== skills/ ==="
.venv/Scripts/python.exe -m ruff check skills/ --statistics 2>&1
```
(On Unix use `.venv/bin/python`)

### 2. Ruff Format Check
```bash
.venv/Scripts/python.exe -m ruff format --check src/ tests/ skills/ 2>&1
```

### 3. TypeScript Check (aiflow-admin)
```bash
cd aiflow-admin && npx tsc --noEmit 2>&1
```

### 4. Summary Report
Present results as:

```
=== LINT CHECK SUMMARY ===

| Area          | Errors | Auto-fixable | Manual | Format |
|---------------|--------|-------------|--------|--------|
| src/aiflow/   |   XXX  |     XXX     |   XXX  |   OK   |
| tests/        |   XXX  |     XXX     |   XXX  |   OK   |
| skills/       |   XXX  |     XXX     |   XXX  |   OK   |
| aiflow-admin/ |   N/A  |     N/A     |   N/A  |  tsc:X |
| TOTAL         |   XXX  |     XXX     |   XXX  |        |

Top 5 rules: E501 (XX), I001 (XX), F401 (XX), ...
```

### 5. If `--fix` flag is provided
Run auto-fix in safe order (lowest risk first):
```bash
# Step 1: Import sorting (zero risk)
.venv/Scripts/python.exe -m ruff check src/ tests/ skills/ --fix --select I001
# Step 2: Unused f-strings, type annotation modernization (low risk)
.venv/Scripts/python.exe -m ruff check src/ tests/ skills/ --fix --select F541,UP017,UP035,UP041,UP045
# Step 3: Unused imports in tests (low risk, not re-exports)
.venv/Scripts/python.exe -m ruff check tests/ --fix --select F401
# Step 4: Format
.venv/Scripts/python.exe -m ruff format src/ tests/ skills/
```

After `--fix`:
1. Re-run the full check to report remaining errors
2. Run `pytest tests/unit/ -q --tb=line` to verify no regression
3. Report: "Fixed XXX errors. XXX remaining (manual fix needed)."

### IMPORTANT
- NEVER auto-fix F401 in `src/aiflow/*/__init__.py` — those may be intentional re-exports
- NEVER auto-fix N806/N803 in skills/ — domain naming conventions (DataFrame, BPMN)
- If `--fix` changes break tests, REVERT and report which rules caused the issue
- ruff format is SAFE to run — it only changes whitespace and quotes
