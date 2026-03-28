Generate a new AIFlow Step implementation.

Ask me for:
1. Step name (snake_case)
2. Which skill it belongs to (or "framework" if core)
3. Brief description of what it does
4. Input fields (name: type pairs)
5. Output fields (name: type pairs)
6. Which LLM model to use (or "none" if not LLM-based)

Then generate:
1. The step function with `@step` decorator, `output_types`, `RetryPolicy`, timeout
2. Pydantic `Input` and `Output` models (BaseModel subclasses)
3. Proper DI injection (ctx: ExecutionContext, models: ModelClient, prompts: PromptManager)
4. A corresponding test file with `@test_registry` header containing minimum 5 tests:
   - Happy path test
   - Invalid input test
   - Edge case test (empty/null fields)
   - Timeout handling test
   - If LLM-based: mock LLM response test

Follow ALL rules from CLAUDE.md:
- Async-first (async def)
- Typed Pydantic I/O
- structlog logging (never print)
- Prompt from YAML via PromptManager (never hardcode)

If LLM-based, also generate a prompt YAML file in the skill's prompts/ directory.
