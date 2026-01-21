---
name: meaning-update
description: Sync the semantic index with filesystem changes
argument-hint: "[--path PATH]"
user-invocable: true
allowed-tools: Read, Write, Edit, Glob, Grep
---

# Update Meaning Index

Sync the semantic index with filesystem changes. Reconciles the index with the actual filesystem state, marking new entries for review and flagging stale entries.

## Workflow

1. **Load current index**
   - Parse `.meaning/index.yaml`
   - Validate against schema

2. **Scan filesystem**
   - List all files (respecting config exclusions)
   - Compare against indexed paths

3. **Detect changes**
   - **New files**: Not in index
   - **Deleted files**: In index but not on disk
   - **Modified files**: mtime newer than `last_verified`

4. **Update index**
   - Add entries for new files with `needs_review: true`
   - Mark deleted files as `status: deprecated`
   - Set `needs_review: true` for modified files
   - Update `last_updated` timestamp

5. **Infer relationships** (for new files)
   - Parse imports/requires/uses
   - Add relationship entries

6. **Report changes**
   - List new entries
   - List deprecated entries
   - List entries needing review

## Arguments

| Argument | Description |
|----------|-------------|
| `--path PATH` | Target directory (default: current) |
| `--dry-run` | Show changes without writing |
| `--no-infer` | Skip relationship inference |

## Output

- Updates `.meaning/index.yaml`
- Reports summary of changes
- Lists entries needing manual review
