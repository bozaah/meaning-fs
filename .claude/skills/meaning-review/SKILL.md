---
name: meaning-review
description: Interactive review of files flagged with needs_review
argument-hint: "[--file PATH] [--all]"
user-invocable: true
allowed-tools: [read_file, write_file, terminal]
---

# Review Meaning Index Suggestions

Interactive workflow for reviewing files flagged with `needs_review: true`, accepting/rejecting inference suggestions, and refining semantic metadata.

## What This Does

Helps you review and refine semantic metadata by:
1. Finding files marked with `needs_review: true`
2. Running inference to show suggestions
3. Comparing suggestions with current metadata
4. Letting you accept, reject, or modify suggestions
5. Updating the index with your decisions

## Workflow

### 1. Pre-flight Checks

```python
from pathlib import Path
from meaning_core import meaning_dir_exists, load_index, load_schema, load_config

project_root = Path.cwd()

# Check if .meaning/ exists
if not meaning_dir_exists(project_root):
    print("❌ .meaning/ not found!")
    print("Run /meaning-init to create semantic index first")
    exit(1)

# Load index
index = load_index(project_root)
schema = load_schema(project_root)
config = load_config(project_root)

print(f"✓ Loaded index with {len(index.files)} files")
```

### 2. Find Files Needing Review

```python
needs_review = index.files_needing_review()

if not needs_review:
    print("✅ No files need review!")
    print("All entries have been reviewed and verified.")
    exit(0)

print(f"\n🔍 Found {len(needs_review)} files needing review:")
for i, entry in enumerate(needs_review[:10], 1):
    print(f"   {i}. {entry.path}")
if len(needs_review) > 10:
    print(f"   ... and {len(needs_review) - 10} more")
```

### 3. Review Each File

For each file needing review, show current metadata and suggestions:

```python
from meaning_inference import infer_file_metadata, infer_timestamps

for entry in needs_review:
    print("\n" + "="*70)
    print(f"📄 File: {entry.path}")
    print("="*70)
    
    # Show current metadata
    print("\n📋 CURRENT METADATA:")
    print(f"   Intent: {entry.intent}")
    print(f"   Tags: {', '.join(entry.tags)}")
    print(f"   Relationships: {len(entry.relationships)}")
    for rel in entry.relationships:
        print(f"      • {rel.type} → {rel.target}")
    print(f"   Status: {entry.status}")
    
    # Run inference to get suggestions
    print("\n💡 SUGGESTED CHANGES:")
    result = infer_file_metadata(entry.path, project_root, index, schema)
    
    # Show intent suggestion
    if result.intent:
        if result.intent.intent != entry.intent:
            print(f"\n   Intent (confidence: {result.intent.confidence:.2f}):")
            print(f"      Current: {entry.intent}")
            print(f"      Suggest: {result.intent.intent}")
            print(f"      Reason:  {result.intent.reason}")
        else:
            print(f"\n   Intent: ✓ No changes suggested")
    
    # Show tag suggestions
    current_tags = set(entry.tags)
    suggested_tags = {t.tag for t in result.tags if t.confidence >= 0.8}
    new_tags = suggested_tags - current_tags
    
    if new_tags:
        print(f"\n   Tags to add:")
        for tag in new_tags:
            tag_info = next(t for t in result.tags if t.tag == tag)
            print(f"      + {tag} (conf: {tag_info.confidence:.2f}) - {tag_info.reason}")
    else:
        print(f"\n   Tags: ✓ No changes suggested")
    
    # Show relationship suggestions
    current_rels = {(r.type, r.target) for r in entry.relationships}
    suggested_rels = {(r.relationship.type, r.relationship.target) 
                      for r in result.relationships if r.confidence >= 0.8}
    new_rels = suggested_rels - current_rels
    
    if new_rels:
        print(f"\n   Relationships to add:")
        for rel_type, target in new_rels:
            rel_info = next(r for r in result.relationships 
                           if r.relationship.type == rel_type and r.relationship.target == target)
            print(f"      + {rel_type} → {target}")
            print(f"        (conf: {rel_info.confidence:.2f}) - {rel_info.reason}")
    else:
        print(f"\n   Relationships: ✓ No changes suggested")
    
    # Show any errors or warnings
    if result.errors:
        print(f"\n   ⚠️  Inference Errors:")
        for error in result.errors:
            print(f"      • {error}")
    
    print("\n" + "-"*70)
```

### 4. Interactive Decision (User Input via Chat)

**Ask the user:**

```
What would you like to do with {entry.path}?

1. Accept all suggestions
2. Accept intent only
3. Accept tags only
4. Accept relationships only
5. Edit manually
6. Skip (review later)
7. Mark as reviewed (no changes)

Type the number of your choice:
```

### 5. Apply User's Decision

```python
from meaning_core import Relationship

# Based on user's choice, update the entry
choice = user_input  # Get from chat

if choice == "1":  # Accept all
    if result.intent:
        entry.intent = result.intent.intent
    
    # Add new tags
    for tag in new_tags:
        if tag not in entry.tags:
            entry.tags.append(tag)
    
    # Add new relationships
    for rel_type, target in new_rels:
        entry.relationships.append(Relationship(type=rel_type, target=target))
    
    entry.needs_review = False
    entry.last_verified = infer_timestamps()
    print(f"   ✓ Applied all suggestions to {entry.path}")

elif choice == "2":  # Accept intent only
    if result.intent:
        entry.intent = result.intent.intent
        entry.needs_review = False
        entry.last_verified = infer_timestamps()
    print(f"   ✓ Updated intent for {entry.path}")

elif choice == "3":  # Accept tags only
    for tag in new_tags:
        if tag not in entry.tags:
            entry.tags.append(tag)
    entry.needs_review = False
    entry.last_verified = infer_timestamps()
    print(f"   ✓ Updated tags for {entry.path}")

elif choice == "4":  # Accept relationships only
    for rel_type, target in new_rels:
        entry.relationships.append(Relationship(type=rel_type, target=target))
    entry.needs_review = False
    entry.last_verified = infer_timestamps()
    print(f"   ✓ Updated relationships for {entry.path}")

elif choice == "5":  # Edit manually
    print(f"   → Open .meaning/index.yaml and edit entry for {entry.path}")
    print(f"   → Set needs_review: false when done")
    # Don't modify, let user edit manually

elif choice == "6":  # Skip
    print(f"   → Skipped {entry.path} (still needs review)")
    # Don't modify, keep needs_review: true

elif choice == "7":  # Mark as reviewed (no changes)
    entry.needs_review = False
    entry.last_verified = infer_timestamps()
    print(f"   ✓ Marked {entry.path} as reviewed")
```

### 6. Save and Report

```python
from meaning_core import save_index, validate_index

# Update index timestamp
index.last_updated = infer_timestamps()

# Save
save_index(index, project_root)
print(f"\n✓ Saved updated index.yaml")

# Validate
validation = validate_index(index, schema, config, project_root)

print("\n" + "="*70)
print("📋 REVIEW COMPLETE")
print("="*70)
print(f"✓ Files reviewed: {len(needs_review)}")
print(f"⚠️  Files still needing review: {len(index.files_needing_review())}")
print(f"✓ Validation: {validation.is_valid}")

if validation.errors:
    print(f"\n❌ Validation errors: {len(validation.errors)}")
    for e in validation.errors[:3]:
        print(f"   • {e}")

print("\n" + "="*70)
print("Next steps:")
if index.files_needing_review():
    print("• Run /meaning-review again to review remaining files")
print("• Run /meaning-validate to check for issues")
print("• Commit updated .meaning/ to git")
print("="*70)
```

## Arguments

- `--file PATH` - Review specific file only
- `--all` - Review all files needing review (batch mode)
- `--accept-high-confidence` - Auto-accept suggestions with confidence > 0.9
- `--dry-run` - Show what would change without saving

## Example Session

```
✓ Loaded index with 57 files

🔍 Found 3 files needing review:
   1. src/new_feature.py
   2. tests/test_new_feature.py
   3. docs/guide.md

======================================================================
📄 File: src/new_feature.py
======================================================================

📋 CURRENT METADATA:
   Intent: [REVIEW NEEDED] src/new_feature.py
   Tags: x-needs-tags
   Relationships: 0
   Status: active

💡 SUGGESTED CHANGES:

   Intent (confidence: 0.82):
      Current: [REVIEW NEEDED] src/new_feature.py
      Suggest: New feature implementation for advanced parsing with caching support
      Reason:  Extracted from module docstring

   Tags to add:
      + module (conf: 0.90) - Python file
      + parsing (conf: 0.85) - Parser/parsing in name
      + core (conf: 0.80) - Main/core file name

   Relationships to add:
      + imports → src/api/client.py
        (conf: 0.95) - From import: from api.client import APIClient

----------------------------------------------------------------------
What would you like to do with src/new_feature.py?

1. Accept all suggestions
2. Accept intent only
3. Accept tags only
4. Accept relationships only
5. Edit manually
6. Skip (review later)
7. Mark as reviewed (no changes)

[User chooses: 1]

   ✓ Applied all suggestions to src/new_feature.py

[... continues for remaining files ...]

✓ Saved updated index.yaml

======================================================================
📋 REVIEW COMPLETE
======================================================================
✓ Files reviewed: 3
⚠️  Files still needing review: 0
✓ Validation: True

======================================================================
Next steps:
• Run /meaning-validate to check for issues
• Commit updated .meaning/ to git
======================================================================
```

## Use Cases

| Scenario | Command |
|----------|---------|
| Review after init | `/meaning-review --all` |
| Review specific file | `/meaning-review --file src/module.py` |
| Quick review (high confidence) | `/meaning-review --accept-high-confidence` |
| Check what would change | `/meaning-review --dry-run` |

## Tips

1. **Start with high-confidence files** - Accept suggestions with confidence > 0.9
2. **Review intent carefully** - It's the most visible field, make it descriptive
3. **Tags are flexible** - You can always add custom tags with `x-` prefix
4. **Relationships matter** - They enable powerful queries and navigation
5. **Batch similar files** - Review all tests together, all docs together, etc.

## Notes

- **Interactive** - Designed for conversation with Claude
- **Non-destructive** - Changes only apply when you confirm
- **Iterative** - Review a few files, commit, review more
- **Learning** - See inference reasoning to understand the system
- **Transparent** - All suggestions show confidence and reasoning

## Philosophy

```
Do not write code before stating assumptions.
Do not claim correctness you haven't verified.
Do not handle only the happy path.
Under what conditions does this work?
```

This skill:
- ✓ Shows all suggestions with reasoning (transparency)
- ✓ Lets user decide what to accept (user control)
- ✓ Validates after changes (ensures correctness)
- ✓ Provides escape hatches (skip, edit manually)