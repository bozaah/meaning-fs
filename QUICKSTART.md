# Meaning Quick Start Guide

> Get up and running with Meaning in 5 minutes

## What is Meaning?

**Meaning** is a semantic file index for AI agents. It creates a `.meaning/` directory in your project containing:
- **Intent**: What each file does (in plain English)
- **Tags**: Semantic categories (api, test, config, etc.)
- **Relationships**: How files connect (tests, documents, imports)
- **Concepts**: Logical groupings of related files

Think of it as a **README for every file** that AI agents can read and maintain.

---

## Installation

### Option 1: pip install (Coming Soon)

```bash
# PyPI (coming soon)
pip install meaning-fs

# Or from GitHub
pip install git+https://github.com/your-org/meaning.git
```

### Option 2: Clone and Install (Development)

```bash
# Clone the repository
git clone https://github.com/your-org/meaning.git
cd meaning

# Create virtual environment
uv venv
uv pip install -e ".[dev]"

# Verify installation
python -m pytest tests/ -v  # All 153 tests should pass
python -m meaning status    # Should show project status
```

---

## Getting Started

### 1. Initialize Your Project

Navigate to your project directory and initialize meaning:

```bash
cd /path/to/your/project

# Basic initialization (auto-detects project type)
meaning init

# With Claude Code hooks (recommended)
meaning init --install-hooks

# Full setup with hooks and skills
meaning init --install-hooks --with-skills

# Just setup structure, skip file scanning
meaning init --skip-crawl
```

**Init Options:**
| Flag | Purpose |
|------|---------|
| `--type TYPE` | Force project type (python, node, rust, docs, mixed) |
| `--limit N` | Process first N files (default: 50) |
| `--skip-crawl` | Don't auto-index files |
| `--install-hooks` | Install Claude Code hooks |
| `--force-hooks` | Overwrite existing hooks |
| `--with-skills` | Install Claude Code skills |

This will:
- Create `.meaning/` directory with config, schema, scripts
- Detect project type (Python, Node, Rust, docs, or mixed)
- Optionally install Claude Code hooks (`.claude/settings.json`)
- Optionally install Claude Code skills (`.claude/skills/`)
- Generate initial index with inference
- Flag low-confidence files for review

**Output:**
```
✓ Created .meaning/ with 6 files
✓ Installed Claude Code hooks
✓ Installed 5 skills
⚠️  Not a git repository. Consider initializing git before meaning.
✓ Indexed 47 files
⚠️  Files needing review: 12
✓ Validation: True
```

### 2. Review Suggestions

Review and accept inference suggestions:

```bash
# With Claude Code (recommended)
/meaning-review

# Or via CLI
python -m meaning review
```

This will **automatically accept** high-confidence suggestions (≥0.8) and only prompt for low-confidence files.
If a file has no docstring/markdown summary or known filename pattern, intent inference may be skipped and the file can remain `needs_review`.
Interactive review now shows a diff-style preview of intent/tags/relationships before you accept changes.

**Output:**
```
📊 Categorizing...
   • 42 high-confidence (auto-accept)
   • 5 need manual review

🤖 Auto-accepting 42 files...
   ✓ src/api.py (updated intent, added 2 relationships)
   ✓ tests/test_api.py (added 1 relationship)
   ...

✅ Review complete in 0.8s
```

### 3. Explore Your Project

Now you can query your project semantically:

```bash
# Get instant overview
python -m meaning status

# Or with Claude Code
/meaning-query what tests the API?
```

---

## Key Features

### 🔍 Instant Discovery

```bash
# Get project overview
python -m meaning status

# Output:
📊 Meaning Index Status

CONCEPTS (3)
  api-layer (5 files)
    └─ src/api/client.py
       "HTTP client for external API communication"

HEALTH
  ✅ 47 files indexed
  ✅ 0 need review
  ✅ 0 validation errors
```

### 🔎 Semantic Search

```bash
# Natural language queries
python -m meaning query "what tests the API?"
python -m meaning query "show me all config files"
python -m meaning query "files that do parsing"
python -m meaning query "what needs review?"
python -m meaning query "what changed recently?"

# Or with Claude Code
/meaning-query what tests the authentication?
```

**6 Query Types:**
- **Status**: "what needs review?"
- **Tag**: "show me test files"
- **Relationship**: "what tests X?"
- **Intent**: "files that do parsing"
- **Temporal**: "what changed recently?"
- **Concept**: "show me the API layer"

### 🤖 Intelligent Inference

Meaning automatically suggests:
- **Intents** from docstrings/markdown headers (70-80% confidence)
- **Tags** from file patterns (80-95% confidence)
- **Relationships** from imports/links (85-95% confidence)
- **Timestamps** (100% confidence)

**Time savings:** 85-90% reduction in manual indexing work

### 🔄 Automatic Sync

```bash
# Detect new/modified/deleted files
/meaning-update

# Output:
📊 Changes detected:
   • New files: 3
   • Modified files: 2
   • Deleted files: 1

✨ Adding 3 new files...
🔄 Flagging 2 modified files for review...
🗑️  Removing 1 deleted file...

✅ Index updated
```

---

## Suggested Workflow

### Daily Development

```bash
# 1. Start your session
python -m meaning status          # See project state

# 2. Find files you need
/meaning-query "what handles user auth?"

# 3. Make changes to files
# (hooks auto-flag modified files)

# 4. End your session
/meaning-update                        # Sync changes
/meaning-review                        # Accept suggestions (auto)
git add .meaning/
git commit -m "Update semantic index"
```

### After git pull

```bash
# Sync index with new changes
/meaning-update
/meaning-review

# Commit if needed
git add .meaning/
git commit -m "Sync meaning index"
```

### Weekly Maintenance

```bash
# Check for stale or unindexed files
/meaning-validate

# Review any issues
/meaning-review
```

---

## Commands Reference

### With Claude Code (Recommended)

| Command | Purpose |
|---------|---------|
| `/meaning-init` | Bootstrap `.meaning/` for new project |
| `/meaning-status` | Show project overview (or use CLI) |
| `/meaning-query "<question>"` | Semantic search |
| `/meaning-update` | Sync with filesystem changes |
| `/meaning-review` | Auto-accept high-confidence suggestions |
| `/meaning-validate` | Health check |

### CLI Commands

| Command | Purpose |
|---------|---------|
| `python -m meaning status` | Project overview |
| `python -m meaning query "<question>"` | Semantic search |
| `python -m meaning validate` | Health check |
| `python -m meaning init` | Initialize project |
| `python -m meaning update` | Sync changes |
| `python -m meaning review` | Review suggestions |

---

## Configuration

### Exclude Files

Edit `.meaning/config.yaml`:

```yaml
exclude_patterns:
  - "**/__pycache__/**"
  - "**/node_modules/**"
  - "**/.venv/**"
  - "**/dist/**"
  - "**/*.pyc"
  - "**/.git/**"

  # Add your custom exclusions
  - "**/build/**"
  - "**/tmp/**"
```

### Custom Tags

Edit `.meaning/schema.yaml`:

```yaml
tag_vocabulary:
  file_type:
    - api
    - test
    - config
    - doc

  feature:
    - auth          # Authentication files
    - parsing       # Parsing logic
    - validation    # Validation logic

  custom:
    - x-experimental   # Experimental features
    - x-deprecated     # Deprecated code
```

Tags starting with `x-` are custom and won't be validated.

---

## Claude Code Integration

### Automatic Hooks

Meaning integrates with Claude Code via hooks in `.claude/settings.json`:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [{
          "type": "command",
            "command": ".meaning/scripts/meaning-post-write.sh"
        }]
      }
    ],
    "Stop": [
      {
        "hooks": [{
          "type": "command",
            "command": ".meaning/scripts/meaning-validate.sh"
        }]
      }
    ]
  }
}
```

**What this does:**
- **PostToolUse**: Flags modified files for review when you edit them
- **Stop**: Validates index when session ends

### Setup

Install hooks and skills into your project:

```bash
# Hooks only
meaning init --install-hooks

# Hooks + skills (recommended for Claude Code users)
meaning init --install-hooks --with-skills

# Add to existing project (merge with existing settings.json)
meaning init --install-hooks --force-hooks
```

The `--with-skills` flag installs 5 Claude Code skills:
- `/meaning-init` — Bootstrap `.meaning/` for a project
- `/meaning-update` — Sync index with filesystem changes
- `/meaning-validate` — Health check
- `/meaning-query` — Semantic search
- `/meaning-review` — Review flagged entries

---

## Tips & Best Practices

### 1. Start with Status

Always begin with:
```bash
python -m meaning status
```

This shows you:
- Project structure (concepts)
- Health metrics
- What needs attention

### 2. Trust High-Confidence Inference

Suggestions with ≥0.8 confidence are typically accurate:
- Tags from filenames (95%+ accurate)
- Imports (95%+ accurate)
- Test relationships (90%+ accurate)

### 3. Review Intents Carefully

Intent descriptions are the most visible metadata. Take time to:
- Make them descriptive (not just filename)
- Explain **why** the file exists, not **what** it contains
- Keep them under 280 characters

### 4. Use Concepts for Navigation

Group related files into concepts:
```yaml
concepts:
  - name: authentication
    description: "User authentication and authorization"
    files:
      - src/auth/login.py
      - src/auth/tokens.py
      - tests/test_auth.py
    entry_point: src/auth/login.py
```

### 5. Commit .meaning/ to Git

The semantic index should be version controlled:
```bash
git add .meaning/
git commit -m "Update semantic index"
```

This ensures all team members and AI agents have the same understanding.

---

## Troubleshooting

### "No .meaning/ directory found"

Run `/meaning-init` or `python -m meaning init` first.

### "Module not found: yaml"

Install dependencies:
```bash
pip install pyyaml
# or
uv pip install pyyaml
```

### "Validation errors"

Run validation to see specific issues:
```bash
python -m meaning validate
```

Common issues:
- **Dangling relationships**: Target file doesn't exist
- **Unknown tags**: Tag not in schema vocabulary (use `x-` prefix for custom tags)
- **Missing files**: Indexed file was deleted (run `/meaning-update`)

### "Hooks not working"

1. Check hook scripts have execute permission:
   ```bash
   chmod +x scripts/meaning-*.sh
   ```

2. Verify scripts use project's Python:
   ```bash
   # Should detect .venv/bin/python
   cat scripts/meaning-post-write.sh
   ```

3. Check Claude Code settings:
   ```bash
   cat .claude/settings.json
   ```

---

## Next Steps

1. **Initialize your project**: `/meaning-init`
2. **Review suggestions**: `/meaning-review`
3. **Try semantic queries**: `/meaning-query "what tests X?"`
4. **Read full docs**: [IMPLEMENTATION-PLAN.md](IMPLEMENTATION-PLAN.md)
5. **Join discussions**: [GitHub Discussions](https://github.com/your-org/meaning/discussions)

---

## Philosophy

```
Do not write code before stating assumptions.
Do not claim correctness you haven't verified.
Do not handle only the happy path.
Under what conditions does this work?
```

Meaning is built to be:
- **Transparent**: See exactly what's indexed and why
- **Deterministic**: Same inputs = same outputs
- **Offline**: No external services or embeddings
- **Git-friendly**: Human-readable YAML that diffs cleanly
- **Agent-agnostic**: Works with any AI agent that can read files

---

**Questions?** Check [CLAUDE.md](CLAUDE.md) for development guide or open an issue on GitHub.

---

*Last updated: 2026-01-23*
