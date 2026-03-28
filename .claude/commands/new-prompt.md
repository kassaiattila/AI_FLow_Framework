Generate a new prompt YAML file for an AIFlow skill.

Ask me for:
1. Skill name (which skill this prompt belongs to)
2. Prompt name (e.g., "classifier", "extractor")
3. Purpose (what the LLM should do)
4. Input variables (template variables the prompt needs)
5. Expected output format (JSON schema, free text, etc.)
6. Model (gpt-4o, gpt-4o-mini, etc.)
7. Language (hu, en, or both)

Generate:
1. **Prompt YAML** at `skills/{skill}/prompts/{name}.yaml`:
   ```yaml
   name: {skill}/{name}
   version: 1
   description: "{purpose}"
   system: |
     {system prompt}
   user: |
     {user template with {{ variables }}}
   config:
     model: {model}
     temperature: 0.1
     max_tokens: {appropriate}
     response_format: {"type": "json_object"}  # if JSON output
   metadata:
     language: {lang}
     tags: [{tags}]
   examples:
     - user: "{example input}"
       assistant: '{example output}'
   langfuse:
     sync: true
     labels: [dev, test]
   ```

2. **Promptfoo test cases** (minimum 10) added to `skills/{skill}/tests/promptfooconfig.yaml`:
   - 4 positive cases (correct classification/extraction)
   - 2 negative cases (should be rejected/off-topic)
   - 2 edge cases (boundary, ambiguous)
   - 1 adversarial (prompt injection attempt)
   - 1 language variant (if multilingual)

Rules:
- NEVER hardcode prompt text in Python code
- Temperature should be LOW (0.1-0.3) for classification/extraction
- ALWAYS include examples in the YAML
- JSON output MUST use response_format: {"type": "json_object"}
