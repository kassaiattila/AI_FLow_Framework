Update AIFlow plan documents with full consistency validation.

Arguments: $ARGUMENTS
(Describe what changed, e.g., "added new DB table: conversations" or "changed Phase 4 to 5 weeks")

This command ensures EVERY plan change is propagated to ALL affected documents
and validated for consistency. NO plan change should be made without this command.

## PHASE 1: IMPACT ANALYSIS

Before making any edit, identify ALL documents affected by the change.

1. Read `01_PLAN/CLAUDE.md` for the key numbers and conventions
2. Classify the change type:

| Change Type | Affected Documents (minimum) |
|-------------|------------------------------|
| DB table add/modify | 03_DATABASE_SCHEMA, AIFLOW_MASTER_PLAN, 00_EXECUTIVE_SUMMARY, CLAUDE.md (root), 01_PLAN/CLAUDE.md |
| Phase/week change | 04_IMPLEMENTATION_PHASES, IMPLEMENTATION_PLAN, AIFLOW_MASTER_PLAN, 00_EXECUTIVE_SUMMARY, 14_FRONTEND |
| New skill | 02_DIRECTORY_STRUCTURE, 04_IMPLEMENTATION_PHASES, IMPLEMENTATION_PLAN, AIFLOW_MASTER_PLAN, 11_REAL_WORLD_SKILLS, 24_TESTING_REGRESSION (suites) |
| Tech stack change | 05_TECH_STACK, 23_CONFIGURATION_REFERENCE, 21_DEPLOYMENT_OPERATIONS (Dockerfile), CLAUDE.md (root), 01_PLAN/CLAUDE.md |
| API endpoint add/modify | 22_API_SPECIFICATION, 01_ARCHITECTURE, 14_FRONTEND (if UI-visible) |
| Security change | 20_SECURITY_HARDENING, 23_CONFIGURATION_REFERENCE, 22_API_SPECIFICATION (RBAC matrix) |
| Test strategy change | 24_TESTING_REGRESSION_STRATEGY, 25_TEST_DIRECTORY_STRUCTURE, CLAUDE.md (root testing rules) |
| CLI command change | 02_DIRECTORY_STRUCTURE, 04_IMPLEMENTATION_PHASES, CLAUDE.md (root key commands) |
| Dev environment change | 27_DEVELOPMENT_ENVIRONMENT, 04_IMPLEMENTATION_PHASES, IMPLEMENTATION_PLAN, CLAUDE.md (root), .claude/commands/* |
| New plan document | 01_PLAN/CLAUDE.md (doc count, structure list), CLAUDE.md (root plan reference), 00_EXECUTIVE_SUMMARY |

3. List ALL files that need updating. Show the list to the user for confirmation.

## PHASE 2: EXECUTE CHANGES

For each affected file:
1. Read the file
2. Make the specific edit
3. Verify the edit is correct
4. Move to the next file

Track changes as a checklist:
```
[x] 03_DATABASE_SCHEMA.md - added conversations table
[x] AIFLOW_MASTER_PLAN.md - updated table count 33 -> 35
[ ] 00_EXECUTIVE_SUMMARY.md - update DB reference
...
```

## PHASE 3: FIRST VALIDATION PASS (Automated Checks)

After ALL edits are done, run these automated checks:

### 3.1 Key Numbers Check
Grep ALL .md files for these numbers and verify consistency:
```bash
# DB tables count (canonical: 48 tabla)
grep -rn "4[0-9] tabla\|4[0-9] table" 01_PLAN/*.md CLAUDE.md
# Views count (canonical: 6 view)
grep -rn "[0-9]* view" 01_PLAN/*.md CLAUDE.md
# Migration count (canonical: 31 migracio fajl, 001-031)
grep -rn "[0-9]* migra" 01_PLAN/*.md CLAUDE.md
# Week count (canonical: 22 het — framework Phase 1-7, KESZ)
grep -rn "22 het\|21 het\|22 week" 01_PLAN/*.md CLAUDE.md
# Skill count (canonical: 7 skill — process_docs, aszf_rag, email_intent, invoice_processor, invoice_finder, cubix, spec_writer)
grep -rn "7 skill\|5 skill\|6 skill" 01_PLAN/*.md CLAUDE.md
# Endpoint count (canonical: 175 endpoint, 27 router)
grep -rn "17[0-9] endpoint\|27 router" 01_PLAN/*.md CLAUDE.md
# Service count (canonical: 27 service)
grep -rn "2[0-9] service" 01_PLAN/*.md CLAUDE.md
# Phase week ranges (legacy framework Phase 1-7)
grep -rn "Het 10-1[0-9]\|Het 14-1[0-9]\|Het 17-1[0-9]\|Het 20-2[0-9]" 01_PLAN/*.md
# Fazis system (service gen F0-F5 vertikalis szeletek) — ne keveredjen Phase 1-7-tel
grep -rn "Fazis [0-4]" 01_PLAN/*.md CLAUDE.md
# Directory check — llm/ ne legyen (models/ a helyes), agents/ ne legyen (torolve)
grep -rn "llm/" 01_PLAN/*.md CLAUDE.md | grep -v "NOT\|models/\|LiteLLM\|litellm"
```

Any inconsistency -> fix immediately before proceeding.

### 3.2 Forbidden Patterns Check
Ensure old/wrong values are GONE:
```bash
# Must NOT appear in active docs (excluding validation report)
grep -rn "python-jose" 01_PLAN/*.md CLAUDE.md | grep -v VALIDATION_REPORT | grep -v "NOT python-jose"
grep -rn "passlib" 01_PLAN/*.md CLAUDE.md | grep -v VALIDATION_REPORT | grep -v "NOT passlib"
grep -rn "allkeys-lru" 01_PLAN/*.md CLAUDE.md | grep -v VALIDATION_REPORT | grep -v "NOT allkeys-lru"
grep -rn "jwt_secret" 01_PLAN/*.md CLAUDE.md | grep -v VALIDATION_REPORT
grep -rn '"af_sk' 01_PLAN/*.md CLAUDE.md | grep -v VALIDATION_REPORT | grep -v "NOT"
grep -rn '"aif_' 01_PLAN/*.md CLAUDE.md | grep -v VALIDATION_REPORT | grep -v "NOT"
grep -rn "plan/" 01_PLAN/*.md | grep -v VALIDATION_REPORT | grep -v GAPS_AND_FIXES
grep -rn "3\.11\+" 01_PLAN/*.md CLAUDE.md | grep -v VALIDATION_REPORT
```

Any hit (that's not in a "NOT X" warning context) -> fix immediately.

### 3.3 Cross-Reference Check
```bash
# All markdown links point to existing files
grep -ohP '\[.*?\]\(([\w_-]+\.md)\)' 01_PLAN/*.md | sort -u | while read link; do
    file=$(echo "$link" | grep -oP '\((\S+)\)' | tr -d '()')
    [ ! -f "01_PLAN/$file" ] && echo "BROKEN LINK: $file"
done
```

Report: "First validation pass: X checks, Y issues found" (or "all clear").

## PHASE 4: SECOND VALIDATION PASS (Semantic Review)

This is a MANUAL review. Read and verify:

1. **01_PLAN/CLAUDE.md** - Are ALL key numbers still correct?
   - DB tables, views, migrations, indexes
   - Weeks, phases, skills, documents
   - Tech conventions (uv, PyJWT, bcrypt, RS256, volatile-lru, aiflow_sk_)

2. **Root CLAUDE.md** - Do these sections still match the plan?
   - Tech Stack line
   - Development Environment section
   - Key Commands section
   - Coverage Gates table
   - Plan Reference list (doc count, section names)

3. **Slash commands** - Do any .claude/commands/*.md need updating?
   (Only if the change affects development workflow, CLI commands, or test structure)

Report: "Second validation pass: reviewed X sections, Y updates needed"

## PHASE 5: FINAL REPORT

Output a summary:
```
=== PLAN UPDATE REPORT ===
Change: {description}
Files modified: {count}
  - {file1}: {what changed}
  - {file2}: {what changed}
  ...
Validation Pass 1 (automated): {PASS/FAIL} ({details})
Validation Pass 2 (semantic): {PASS/FAIL} ({details})
Status: CONSISTENT / NEEDS_FIXES
```

If NEEDS_FIXES: list exactly what remains and fix it before finishing.
If CONSISTENT: the plan is ready to commit.

## RULES

- NEVER edit just one document if the change affects multiple documents
- ALWAYS run both validation passes - no shortcuts
- ALWAYS update 01_PLAN/CLAUDE.md key numbers if ANY number changed
- ALWAYS update root CLAUDE.md if tech stack, commands, or plan structure changed
- If adding a new plan document: update doc count in 01_PLAN/CLAUDE.md AND root CLAUDE.md Plan Reference
- Commit message format: `docs(plan): {what changed} - validated across {N} files`
