---
name: meaning-validate
description: Health check for the semantic index
argument-hint: "[--fix] [--strict]"
user-invocable: true
allowed-tools: Read, Glob, Grep
---

# Validate Meaning Index

Health check for the semantic index. Checks for inconsistencies, missing files, stale entries, and schema violations.

## Workflow

1. **Load and parse index**
   - Parse `.meaning/index.yaml`
   - Check YAML syntax validity

2. **Validate against schema**
   - Check all required fields present
   - Validate relationship types against schema
   - Validate tags against vocabulary

3. **Check file references**
   - Verify all indexed paths exist
   - Check relationship targets exist
   - Verify concept file lists

4. **Check freshness**
   - Flag entries older than 7 days as stale
   - Count entries with `needs_review: true`

5. **Check for orphans**
   - Find files on disk not in index
   - Find broken relationships

6. **Report findings**
   - Errors (must fix)
   - Warnings (should fix)
   - Info (optional improvements)

## Arguments

| Argument | Description |
|----------|-------------|
| `--path PATH` | Target directory (default: current) |
| `--fix` | Automatically fix simple issues |
| `--strict` | Treat warnings as errors |
| `--json` | Output as JSON for scripting |

## Validation Rules

| Rule | Severity | Auto-fixable |
|------|----------|--------------|
| Missing required field | Error | No |
| Unknown relationship type | Error | No |
| Invalid tag (not in vocabulary) | Warning | No |
| File not found | Error | Yes (remove) |
| Relationship target missing | Error | Yes (remove) |
| Entry stale (> 7 days) | Warning | No |
| Orphan file (not indexed) | Info | Yes (add) |

## Output

- Exit code 0: All checks pass
- Exit code 1: Errors found
- Human-readable report or JSON
