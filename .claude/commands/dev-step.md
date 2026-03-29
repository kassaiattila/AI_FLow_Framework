Record a completed development step and run the full validation sequence.

Arguments: $ARGUMENTS
(Optional: step title)

## PRE-IMPLEMENTATION CHECKS (before writing any code!):

1. **Read the relevant plan document** in `01_PLAN/`:
   - `IMPLEMENTATION_PLAN.md` - current phase and task list
   - `30_RAG_PRODUCTION_PLAN.md` - for RAG features (check Cubix tananyag checklist!)
   - `29_OPTIMIZATION_PLAN.md` - for framework changes
2. **Check reference materials** - `skills/*/reference/` if relevant
3. **Check existing pilot code** - never reinvent what already works
4. **If DB change needed**: create Alembic migration FIRST, run `alembic upgrade head`
5. **If new skill**: use `/new-skill` command which enforces all conventions

## POST-IMPLEMENTATION (this is the main validation):

Sequence:
1. **Identify changes**: `git diff --name-only` + `git diff --staged --name-only`
2. **Check no untracked files** that should be in git
3. **Run unit tests**: `pytest tests/unit/ skills/*/tests/ -q`
4. **Verify ALL PASS** - zero failures
5. **Check Alembic**: if any .py migration changed, run `alembic upgrade head`
6. **Generate step record + suggest commit message**

## CRITICAL RULES:

- NEVER commit with failing tests
- NEVER create DB tables without Alembic
- NEVER skip reading the plan document
- NEVER hardcode prompts in Python (use YAML)
- ALWAYS run `git status` to check for untracked files
- ALWAYS use conventional commits (feat/fix/docs/refactor)
