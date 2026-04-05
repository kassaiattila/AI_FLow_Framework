Generate a YAML pipeline definition for the AIFlow orchestration system.

## Input
$ARGUMENTS — natural language description of the pipeline (e.g., "email szamla feldolgozas")

## Steps

### 1. Discover Available Adapters
- Read `src/aiflow/pipeline/adapters/` directory
- List each adapter's `service_name`, `method_name`, `input_schema`, `output_schema`
- If the adapter directory does not exist yet, list planned adapters from `01_PLAN/48_ORCHESTRABLE_SERVICE_ARCHITECTURE.md`

### 2. Match Services to Description
- Identify required services for the described workflow
- Determine step order and dependencies (`depends_on`)
- Identify `for_each` needs (iteration over lists)
- Identify `condition` needs (branching)

### 3. Generate Pipeline YAML
Follow the schema from `01_PLAN/48_ORCHESTRABLE_SERVICE_ARCHITECTURE.md` Phase 2:

```yaml
name: <pipeline_name>
version: "1.0.0"
description: "<user description>"
trigger:
  type: manual
input_schema:
  <required_inputs>

steps:
  - name: <step_name>
    service: <service_name>
    method: <method_name>
    config:
      <jinja2_template_configs>
    depends_on: [<previous_steps>]
    for_each: "{{ <jinja2_expression> }}"  # if needed
    condition: "output.field op value"      # if needed
    retry:
      max_retries: 2                       # MANDATORY for external calls
```

### 4. Validate
- Check all `service` + `method` pairs exist in adapter registry
- Verify `depends_on` references are valid (no circular)
- Verify `for_each` expressions are valid Jinja2
- Verify `condition` expressions follow `output.field op value` format

### 5. Show & Save
- Show YAML to user for review
- On approval: save to `src/aiflow/pipeline/builtin_templates/<name>.yaml`
- Create test stub: `tests/pipeline/test_<name>.py`

## MANDATORY Rules
- EVERY step MUST reference an existing adapter (`service` + `method`)
- `for_each` MUST be valid Jinja2 returning a list
- `condition` MUST follow `output.field op value` format
- `retry` KOTELEZO minden kulso service hivasra (LLM, email, HTTP)
- Jinja2-ben TILOS: `__dunder__`, `callable`, `import`
- Input schema MUST define ALL required pipeline inputs
- Pipeline YAML-hoz KOTELEZO teszt: `tests/pipeline/test_<name>.py`
