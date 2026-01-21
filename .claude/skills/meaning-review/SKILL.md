---
name: meaning-review
description: Interactive review of flagged index entries
argument-hint: "[--limit N]"
user-invocable: true
allowed-tools: Read, Write, Edit, Glob
---

# Review Meaning Entries

Guide through reviewing entries marked with `needs_review: true`. Presents each flagged entry and helps refine intent descriptions, tags, and relationships.

## Workflow

1. **Load index and find flagged entries**
   - Parse `.meaning/index.yaml`
   - Filter entries where `needs_review: true`
   - Sort by priority (new files first, then modified)

2. **For each entry, present context**
   - Show file path and current metadata
   - Display file preview (first 50 lines or summary)
   - Show existing relationships

3. **Prompt for review**
   - Confirm or edit intent description
   - Add/remove tags
   - Add/remove relationships
   - Mark as reviewed or skip

4. **Update entry**
   - Apply changes
   - Set `needs_review: false`
   - Update `last_verified` timestamp

5. **Continue or exit**
   - Move to next flagged entry
   - Allow early exit with progress saved

## Arguments

| Argument | Description |
|----------|-------------|
| `--path PATH` | Target directory (default: current) |
| `--limit N` | Maximum entries to review (default: 10) |
| `--concept NAME` | Only review files in specific concept |
| `--tag TAG` | Only review files with specific tag |

## Interactive Flow

For each entry needing review:

```
File: src/api/parser.py
Intent: "Transforms raw API JSON responses into domain models"
Tags: [api, parsing, transforms]
Status: active

Preview:
─────────────────────────────────────
class APIParser:
    def parse_response(self, data: dict) -> APIModel:
        ...
─────────────────────────────────────
```

Ask user to confirm, edit intent, modify tags, add relationships, skip, or quit.

## Output

- Updates `.meaning/index.yaml` with reviewed entries
- Reports count of entries reviewed
- Lists remaining entries needing review
