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

## Quick Start

```bash
# Install
pip install -e .

# Initialize meaning for your project
cd your-project
meaning init

# Validate the index
meaning validate
```

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
│   └── meaning_core.py     # Core library
├── templates/
│   ├── schema/             # Project-type schemas
│   └── config.yaml         # Default config
├── scripts/
│   ├── meaning-post-write.sh
│   ├── meaning-validate.sh
│   └── validate-meaning.sh # Validate this project's index
└── tests/
```

## Documentation

- [Implementation Plan](IMPLEMENTATION-PLAN.md) — Full specification
- [CLAUDE.md](CLAUDE.md) / [AGENTS.md](AGENTS.md) — Guide for AI agents working on this project
- [Agent Sessions](.agent-sessions/) — Session notes documenting project evolution

## License

MIT
