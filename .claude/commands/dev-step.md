Record a completed development step and run the full validation sequence.

Arguments: $ARGUMENTS
(Optional: step title)

This command is used AFTER implementing a change and writing tests, BEFORE committing.

Prerequisites: .venv must exist (created by `uv venv && uv pip install -e ".[dev]"`).
Docker services must be running (`make dev`) for integration tests.
Environment spec: 01_PLAN/27_DEVELOPMENT_ENVIRONMENT.md

Sequence:
1. **Identify changes**: `git diff --name-only` + `git diff --staged --name-only`
2. **Classify step type**: feature / fix / refactor / prompt / skill / dependency / config
3. **Run regression** (same as /regression command):
   - Determine affected suites from regression_matrix.yaml
   - Run all affected suites
   - Verify coverage didn't decrease
4. **If ALL PASS**:
   - Generate development step record:
     ```
     Step: DS-{YYYY}-{MMDD}-{NNN}
     Type: {type}
     Title: {title}
     Files: {changed_files}
     New tests: {count}
     Regression: L{X}, {total} tests, ALL PASS
     Coverage: {before}% -> {after}%
     ```
   - Suggest commit message (Conventional Commits format)
   - Ask: "Ready to commit? (y/n)"
5. **If ANY FAIL**:
   - Show failures
   - DO NOT suggest committing
   - Suggest fixes

This is the PRIMARY workflow command. Use it for every development cycle.
