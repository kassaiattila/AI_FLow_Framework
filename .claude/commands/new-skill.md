Generate a complete new AIFlow Skill scaffold.

Ask me for:
1. Skill name (snake_case)
2. Display name
3. Skill type: ai / rpa / hybrid
4. Brief description
5. Required LLM models
6. Agent names and their responsibilities (max 6!)
7. Workflow complexity: small_linear / medium_branching / large_orchestrated

Then generate the FULL skill directory structure:

```
skills/{name}/
    skill.yaml            # Manifest with all metadata
    __init__.py
    workflow.py            # Workflow DAG definition
    agents/
        __init__.py
        {agent_name}.py    # For each agent (with @step decorator)
    models/
        __init__.py
        {domain}.py        # Pydantic models for step I/O
    prompts/
        {agent_name}.yaml  # Prompt YAML for each LLM agent
    tools/                 # Only if needed
    tests/
        conftest.py
        promptfooconfig.yaml
        test_workflow.py
        test_{agent_name}.py  # For each agent
        datasets/
            test_cases.json   # Minimum 100 test cases skeleton
```

ENFORCE these rules:
- Max 6 specialist agents
- skill.yaml MUST include: framework_requires, required_models, workflows, agent_types, prompts, estimated_cost_per_run
- All agents MUST be stateless
- All I/O MUST be Pydantic BaseModel
- Test files MUST have @test_registry headers
- Prompt YAML MUST follow the standard format (name, version, system, user, config, examples, langfuse)
- Generate at least 10 test case skeletons per agent in the datasets/ JSON

Reference: 01_PLAN/SKILL_DEVELOPMENT.md for complete guidelines.
