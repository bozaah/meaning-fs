# Meaning

> Semantic File Index for AI Agents

A lean, text-based semantic layer that lives alongside your files, readable by any AI agent, requiring no external services or embeddings.

## The Problem

AI agents operating on codebases lack semantic context. They see files as paths and text, not as purposeful artifacts with relationships. This causes inefficient navigation, missed dependencies, and lost context between sessions.

## The Solution

**Meaning** adds a `.meaning/` directory to your project containing:

- `index.yaml` — Semantic records for all files (intent, tags, relationships)
- `schema.yaml` — Project-specific vocabulary and relationship types
- `config.yaml` — Exclusion patterns and settings

When you say "update how API responses are parsed," your AI agent can read the index and know exactly which files to touch.

---

**👉 [Get Started in 5 Minutes](QUICKSTART.md) 👈**

---

## Status

**Phase 5 Complete** — Status overview and semantic query ✅

- ✅ Core library (`meaning_core.py`) - 1,100+ lines, 54+ tests passing
- ✅ Inference engine (`meaning_inference.py`) - 612 lines, 32 tests passing
- ✅ **Status command** - Instant project overview with concepts, health metrics, and recent activity
- ✅ **Query engine** - Natural language semantic search (6 query types, <50ms response)
- ✅ Five Claude Code skills (`/meaning-init`, `/meaning-update`, `/meaning-validate`, `/meaning-review`, `/meaning-query`)
- ✅ Hook scripts for automatic tracking
- ✅ Dog-fooded on itself (33+ files indexed, 0 validation errors)

**Next:** External project testing, query enhancements, PyPI packaging

## Quick Start

### With Claude Code

```bash
# In your project directory with Claude Code
/meaning-init              # Bootstrap .meaning/ with intelligent inference
/meaning-review            # Review and approve suggested metadata
/meaning-validate          # Check index health

# During development
/meaning-update            # Sync with filesystem changes
```

### Manual Usage

```bash
# Install dependencies
uv venv && uv pip install -e ".[dev]"

# Validate this project's index
./scripts/validate-meaning.sh
```

## Discovering Your Project

Once initialized, instantly understand your codebase with zero latency:

```bash
# Get instant overview (concepts, health, recent activity)
python -m meaning status

# Natural language semantic search
python -m meaning query "what tests the core?"
python -m meaning query "show me all config files"
python -m meaning query "files that do parsing"
python -m meaning query "what needs review?"
python -m meaning query "what changed recently?"
```

**Example output:**
```
🔍 Query Results: Files that tests src/meaning/meaning_core.py
   Type: relationship

  Found 1 file (showing 1):

  1.   tests/test_core.py
      "Comprehensive test suite for core data structures..."
      Tags: test, module
      Relationships: tests(1), imports(1)
```

Or use the skill in Claude Code:
```bash
/meaning-query what tests the inference engine?
```

**6 Query Types Supported:**
- **Status**: "what needs review?", "what is stale?"
- **Tag**: "show me all test files", "find config files"
- **Relationship**: "what tests X?", "what documents Y?"
- **Intent**: "files that do parsing", "files about auth"
- **Temporal**: "what changed recently?"
- **Concept**: "show me the core library"

## Features

- **Instant Discovery** - `status` command shows project overview in <50ms
- **Semantic Query** - Natural language search across 6 query types (status, tag, relationship, intent, temporal, concept)
- **Intelligent Inference** - Automatically suggests tags, intents, and relationships with confidence scores
- **85-90% Time Savings** - Review AI suggestions instead of writing metadata from scratch
- **Git-Friendly** - Human-readable YAML files that diff and merge cleanly
- **Zero Dependencies** - Works offline, no external services or embeddings
- **Batch Review** - Efficient workflows for reviewing many files at once
- **Claude Code Integration** - Automatic tracking via hooks on file changes
- **Transparent** - All suggestions show confidence levels and reasoning
- **Non-Destructive** - Human reviews and approves all changes

Note: intent auto-accept uses Python module docstrings, markdown first paragraphs, and known filename/path patterns (README/CHANGELOG, templates, agent session notes). Files without these signals may remain `needs_review`.

## How It Works

### File Entries

Each file gets a semantic record:

```yaml
- path: src/api/parser.py
  intent: "Transforms raw API JSON responses into domain models"
  tags: [api, parsing, transforms]
  status: active
  relationships:
    - type: transforms
      source: src/api/client.py
      target: src/models/api_models.py
```

### Concepts

Related files are grouped into concepts:

```yaml
concepts:
  - name: api-parsing
    description: "External API response handling"
    files:
      - src/api/client.py
      - src/api/parser.py
      - src/models/api_models.py
    entry_point: src/api/parser.py
```

### Claude Code Integration

Meaning includes hooks for Claude Code that automatically track file changes:

```json
{
  "hooks": [
    {
      "matcher": { "type": "PostToolUse", "tool_name": ["write_file"] },
      "script": ".meaning/scripts/meaning-post-write.sh"
    }
  ]
}
```

Install hooks with:

```bash
python -m meaning init --install-hooks
```

## Philosophy

```
Do not write code before stating assumptions.
Do not claim correctness you haven't verified.
Do not handle only the happy path.
Under what conditions does this work?
```

## Project Structure

```
meaning/
├── .agent-sessions/        # AI agent session notes
├── .meaning/               # Dog-fooding: our own semantic index
├── src/
│   └── meaning/
│       ├── meaning_core.py     # Core library
│       └── templates/          # Project templates
│           ├── schema/         # Project-type schemas
│           ├── config.yaml     # Default config
│           ├── hooks.json      # Claude hooks template
│           └── scripts/        # Hook scripts for target projects
├── scripts/
│   ├── meaning-post-write.sh
│   ├── meaning-validate.sh
│   └── validate-meaning.sh # Validate this project's index
└── tests/
```

## Documentation

- **[Quick Start Guide](QUICKSTART.md)** — Get started in 5 minutes
- [Implementation Plan](IMPLEMENTATION-PLAN.md) — Full specification
- [CLAUDE.md](CLAUDE.md) / [AGENTS.md](AGENTS.md) — Guide for AI agents working on this project
- [Agent Sessions](.agent-sessions/) — Session notes documenting project evolution

## License

MIT
