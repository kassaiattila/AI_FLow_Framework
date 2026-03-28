Show the current implementation status of an AIFlow phase.

Arguments: $ARGUMENTS
(Phase number: 1-7, or "all" for overview)

Steps:
1. Read `01_PLAN/04_IMPLEMENTATION_PHASES.md` for the phase definition
2. Check which files from the phase's task list actually exist:
   ```bash
   # For each file listed in the phase, check if it exists
   ls -la src/aiflow/{module}/ 2>/dev/null
   ```
3. Check test status:
   ```bash
   # Count existing test files
   find tests/ -name "test_*.py" -type f | wc -l
   ```
4. Check coverage if tests exist:
   ```bash
   pytest tests/unit/ --cov=aiflow --cov-report=term 2>/dev/null
   ```

Report as a table:
| Task | File | Status | Tests | Coverage |
|------|------|--------|-------|----------|
| AIFlowSettings | src/aiflow/core/config.py | EXISTS/MISSING | 5/5 pass | 92% |

Summary:
- Phase {X}: {completed}/{total} tasks ({pct}%)
- Tests: {total} tests, {passing} passing
- Coverage: {pct}%
- Next task to implement: {description}

This helps track progress through the 22-week implementation plan.
