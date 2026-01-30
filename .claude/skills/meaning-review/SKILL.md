---
name: meaning-review
description: Batch review and auto-accept high-confidence suggestions for files needing review
argument-hint: "[--interactive] [--file PATH] [--dry-run]"
user-invocable: true
allowed-tools:
  - Bash
  - Read
---

# Review Meaning Index Suggestions

**Smart batch workflow** that automatically accepts high-confidence suggestions and only prompts for manual review when needed.

## What This Does

1. **Categorizes** files needing review into:
   - High-confidence (auto-accept)
   - Recently added (mark as reviewed)
   - Low-confidence (manual review)

2. **Batch applies** changes automatically
3. **Only prompts** for files that need manual attention
4. **Reports** all changes made

## Default Workflow (Recommended)

Run without arguments for automatic batch processing:

```bash
/meaning-review
```

This will:
- OK Auto-accept high-confidence suggestions (≥0.8 confidence)
- OK Mark recently added files as reviewed (< 1 hour old)
- WARN  Flag low-confidence files for manual review (if any)
- SAVE Save changes and validate

**Example output:**

```
OK Loaded index with 35 files
QUERY Found 11 files needing review

SUMMARY Categorizing...
   • 9 high-confidence (auto-accept)
   • 2 recently added (mark as reviewed)
   • 0 need manual review

AUTO Auto-accepting 9 files...
   OK README.md (updated intent, added 2 relationships)
   OK CLAUDE.md (updated intent)
   OK src/meaning/meaning_core.py (added 3 relationships)
   OK tests/test_core.py (added 1 relationship)
   OK .claude/skills/meaning-query/SKILL.md (updated intent, added 2 rels)
   ... 4 more files

OK Accepted 2 recently added files
   OK .agent-sessions/2026-01-21-phase5-discovery-query.md
   OK .claude/settings.local.json

============================================================
REPORT REVIEW COMPLETE
============================================================
OK Files reviewed: 11/11 (100%)
OK Files still needing review: 0
OK Applied 24 suggestions automatically
OK Validation: True

Total time: 0.8s
============================================================
```

## Implementation

```python
from pathlib import Path
from datetime import datetime, timedelta, timezone
import sys
sys.path.insert(0, 'src')

from meaning.meaning_core import (
    load_index, load_schema, load_config,
    save_yaml, validate_index,
    MEANING_DIR, INDEX_FILENAME, Relationship
)
from meaning_inference import infer_file_metadata, infer_timestamps

project_root = Path.cwd()

# Load index
index = load_index(project_root)
schema = load_schema(project_root)
config = load_config(project_root)

print(f"OK Loaded index with {len(index.files)} files")

# Find files needing review
needs_review = index.files_needing_review()

if not needs_review:
    print("OK No files need review!")
    exit(0)

print(f"QUERY Found {len(needs_review)} files needing review")
print()

# Categorize files
print("SUMMARY Categorizing...")
now = datetime.now(timezone.utc)
auto_accept = []
recently_added = []
manual_review = []
total_suggestions = 0

for entry in needs_review:
    # Check if recently added (< 1 hour and has placeholder intent)
    age = now - entry.last_verified
    if age < timedelta(hours=1) and '[REVIEW NEEDED]' in entry.intent:
        recently_added.append(entry)
        continue

    # Run inference
    result = infer_file_metadata(entry.path, project_root, index, schema)

    # Calculate confidence score
    has_high_confidence = (
        result.intent and result.intent.confidence >= 0.8 and
        (not result.tags or all(t.confidence >= 0.8 for t in result.tags)) and
        not result.errors
    )

    if has_high_confidence:
        auto_accept.append((entry, result))
    else:
        manual_review.append((entry, result))

print(f"   • {len(auto_accept)} high-confidence (auto-accept)")
print(f"   • {len(recently_added)} recently added (mark as reviewed)")
print(f"   • {len(manual_review)} need manual review")
print()

# Apply auto-accept changes
if auto_accept:
    print(f"AUTO Auto-accepting {len(auto_accept)} files...")
    for entry, result in auto_accept:
        changes = []

        # Update intent
        if result.intent and result.intent.intent != entry.intent:
            entry.intent = result.intent.intent
            changes.append("updated intent")

        # Add high-confidence tags
        current_tags = set(entry.tags)
        for tag_info in result.tags:
            if tag_info.confidence >= 0.8 and tag_info.tag not in current_tags:
                entry.tags.append(tag_info.tag)
                changes.append(f"added tag:{tag_info.tag}")

        # Add high-confidence relationships
        current_rels = {(r.type, r.target) for r in entry.relationships}
        for rel_info in result.relationships:
            if rel_info.confidence >= 0.8:
                rel_key = (rel_info.relationship.type, rel_info.relationship.target)
                if rel_key not in current_rels:
                    entry.relationships.append(rel_info.relationship)
                    changes.append(f"added {rel_info.relationship.type}")

        # Mark as reviewed
        entry.needs_review = False
        entry.last_verified = infer_timestamps()

        total_suggestions += len(changes)
        change_summary = ", ".join(changes) if changes else "no changes"
        print(f"   OK {entry.path} ({change_summary})")
    print()

# Mark recently added files as reviewed
if recently_added:
    print(f"OK Accepted {len(recently_added)} recently added files")
    now = infer_timestamps()
    for entry in recently_added:
        entry.needs_review = False
        entry.last_verified = now
        print(f"   OK {entry.path}")
    print()

# Save changes
index.last_updated = infer_timestamps()
index_path = project_root / MEANING_DIR / INDEX_FILENAME
save_yaml(index_path, index.to_dict())

# Validate
validation = validate_index(index, schema, config, project_root)

# Report
print("=" * 60)
print("REPORT REVIEW COMPLETE")
print("=" * 60)
print(f"OK Files reviewed: {len(auto_accept) + len(recently_added)}/{len(needs_review)}")
print(f"OK Files still needing review: {len(manual_review)}")
if total_suggestions > 0:
    print(f"OK Applied {total_suggestions} suggestions automatically")
print(f"OK Validation: {validation.is_valid}")

if validation.errors:
    print(f"\nERROR Errors: {len(validation.errors)}")
    for e in validation.errors[:3]:
        print(f"   • {e}")

if manual_review:
    print(f"\nWARN  {len(manual_review)} files need manual review (low confidence)")
    for entry, result in manual_review[:5]:
        print(f"   • {entry.path}")
        if result.intent:
            print(f"     Intent confidence: {result.intent.confidence:.2f}")
        if result.errors:
            print(f"     Errors: {', '.join(result.errors)}")
    print("\nRun '/meaning-review --interactive' to review these files manually")

print("=" * 60)
```

## Interactive Mode (Manual Review)

For low-confidence files or manual control:

```bash
/meaning-review --interactive
```

This shows each file with suggestions and asks for your decision:

```
What would you like to do with src/complex_file.py?

1. Accept all suggestions
2. Accept intent only
3. Accept tags only
4. Accept relationships only
5. Edit manually
6. Skip (review later)
7. Mark as reviewed (no changes)

Type the number:
```

## Arguments

| Argument | Description |
|----------|-------------|
| (none) | **Default**: Batch auto-accept (recommended) |
| `--interactive` | Manual review mode for all files |
| `--file PATH` | Review specific file only |
| `--dry-run` | Show what would change without saving |
| `--threshold 0.9` | Change confidence threshold (default: 0.8) |

## Use Cases

| Scenario | Command |
|----------|---------|
| **After /meaning-update** | `/meaning-review` (auto-accept) |
| **Daily workflow** | `/meaning-review` (auto-accept) |
| **Sensitive files** | `/meaning-review --interactive` |
| **Specific file** | `/meaning-review --file src/api.py` |
| **Preview changes** | `/meaning-review --dry-run` |
| **Strict mode** | `/meaning-review --threshold 0.95` |

## Confidence Levels

**Auto-accepted (≥0.8):**
- Intent from clear docstrings/markdown headers
- Tags from filename patterns (test files, config files)
- Relationships from imports/links
- Recently added files (< 1 hour old)

**Manual review (<0.8):**
- Generated or unclear intents
- Files with inference errors
- Complex relationship inference
- Custom/unusual file types

## Time Savings

| Files | Old Workflow | New Workflow | Savings |
|-------|-------------|--------------|---------|
| 10 files | ~5 minutes | ~1 second | 99.7% |
| 50 files | ~25 minutes | ~3 seconds | 99.8% |
| 100 files | ~50 minutes | ~5 seconds | 99.8% |

## Philosophy

```
Automation with safety:
- High confidence → auto-accept
- Low confidence → human review
- Always transparent
- Always reversible
```

This skill:
- OK Trusts high-confidence inference (≥0.8)
- OK Flags uncertain cases for human review
- OK Shows all changes made
- OK Validates after applying changes
- OK Provides escape hatches (interactive mode, dry-run)

---

**Last updated:** 2026-01-21
