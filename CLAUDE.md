# CLAUDE.md — Meaning Project

> Semantic File Index for AI Agents

## Project Overview

**Meaning** is a lean, text-based semantic layer that lives alongside project files. It provides AI agents with semantic context—file purposes, relationships, and concept groupings—without requiring external services or embeddings.

The goal: When you say "update how API responses are parsed," Claude should know exactly which files to touch and why.

## Philosophy

```
Do not write code before stating assumptions.
Do not claim correctness you haven't verified.
Do not handle only the happy path.
Under what conditions does this work?
```

**Lean by design**: YAML files, bash scripts, one Python module. No databases, no vector stores, no external APIs.

**Deterministic over probabilistic**: Hooks are scripts, not prompts. Behavior must be identical across runs.

## Repository Structure

```
meaning/
├── .agent-sessions/            # AI agent session notes and context
│   ├── README.md               # Session documentation guide
│   └── YYYY-MM-DD-*.md         # Individual session summaries
├── .claude/                    # Claude Code configuration
│   ├── settings.json           # Project hooks and permissions
│   └── skills/                 # Skill definitions (SKILL.md format)
│       ├── meaning-init/
│       ├── meaning-update/
│       ├── meaning-validate/
│       └── meaning-review/
├── .meaning/                   # Dog-fooding: Meaning's own semantic index
│   ├── index.yaml              # Semantic records for this project
│   ├── schema.yaml             # Python project schema
│   └── config.yaml             # Configuration
├── AGENTS.md -> CLAUDE.md      # Symlink for other AI agents
├── CLAUDE.md                   # You are here
├── IMPLEMENTATION-PLAN.md      # Detailed spec and design decisions
├── src/
│   └── meaning_core.py         # Core Python library
├── templates/                  # Templates for target projects
│   ├── schema/                 # Project-type specific schemas
│   │   ├── python.yaml
│   │   ├── node.yaml
│   │   ├── rust.yaml
│   │   └── docs.yaml
│   ├── config.yaml             # Default config template
│   └── hooks.json              # Claude hooks for target projects
├── scripts/
│   ├── meaning-post-write.sh   # Post-mutation hook
│   ├── meaning-validate.sh     # Session-end hook
│   └── validate-meaning.sh     # Validate this project's .meaning/
└── tests/
    ├── test_core.py
    ├── test_inference.py
    └── fixtures/
```

## Key Files

| File | Purpose |
|------|---------|
| `IMPLEMENTATION-PLAN.md` | Full specification—read this first for any design questions |
| `src/meaning_core.py` | All YAML parsing, validation, inference logic |
| `scripts/*.sh` | Deterministic hook scripts called by Claude Code |
| `templates/schema/*.yaml` | Project-type specific relationship types and tag vocabularies |
| `.claude/skills/*/SKILL.md` | Claude skill definitions for initialization, update, validation |
| `.claude/settings.json` | Claude Code hooks and permissions for this project |
| `.agent-sessions/*.md` | Session notes documenting project evolution and decisions |
| `.meaning/` | This project's own semantic index (dog-fooding!) |
</text>

## Session Continuity

**For AI agents working across sessions:**

1. **Check `.agent-sessions/`** - Read the most recent session note to understand current state
2. **Review `.meaning/index.yaml`** - See which files are already documented
3. **Run validation** - `./scripts/validate-meaning.sh` to check index health
4. **Document your session** - Create a new session note following the format in `.agent-sessions/README.md`

This ensures continuity and prevents repeated discovery of the same issues.

## Development Commands

- Use `uv` to create and manage the environment.

```bash
# Setup environment
uv venv
uv pip install -e ".[dev]"

# Run tests
python -m pytest tests/ -v

# Validate this project's .meaning/ index
./scripts/validate-meaning.sh

# Validate a meaning index (once implemented)
python -m meaning validate /path/to/project

# Initialize meaning for a project (once implemented)
python -m meaning init /path/to/project --type python
```

## Architecture Decisions

### Why YAML?
- Human-readable without tooling
- Native parsing in Python, readable by any LLM
- Git-friendly (line-based diffs)
- No schema enforcement required

### Why single index.yaml?
- One source of truth
- Atomic updates
- Easy to grep/search
- Tradeoff: merge conflicts on large teams (acceptable for v0.1)

### Why deterministic scripts over prompt-based hooks?
- Consistent behavior across runs
- Milliseconds vs LLM inference time
- Auditable and testable
- Git-trackable logic

### Why no embeddings?
- Zero external dependencies
- Works offline
- Transparent (you can read the index)
- Good enough for < 5000 files with structured metadata

## Conventions

### Code Style
- Python: Follow PEP 8, type hints required
- Bash: Use `set -euo pipefail`, quote variables
- YAML: 2-space indentation, explicit quotes for strings with special chars

### Naming
- Files: `snake_case.py`, `kebab-case.sh`, `kebab-case.yaml`
- Python functions: `snake_case`
- YAML keys: `snake_case`
- Tags: `kebab-case`

### Error Handling
- Never silently fail
- Return structured errors, not exceptions where possible
- Log warnings for recoverable issues
- Fail loudly for data corruption

### Testing
- Every function in `meaning_core.py` needs unit tests
- Use fixtures for YAML parsing tests
- Test edge cases: empty files, corrupt YAML, missing fields

## Working with This Project

### Before Writing Code
1. Check `IMPLEMENTATION-PLAN.md` for the relevant section
2. Identify assumptions being made
3. Consider failure modes
4. Write tests first if adding new functionality

### When Adding Features
1. Update `IMPLEMENTATION-PLAN.md` if design changes
2. Add to appropriate phase in implementation plan
3. Update this file if new conventions needed

### When Fixing Bugs
1. Add regression test first
2. Document the edge case that was missed
3. Consider if other similar edge cases exist

## Current Phase

**Phase 1: Core Data Structures**

Focus areas:
- [ ] `meaning_core.py` — YAML parsing, validation
- [ ] Schema templates for python, node, rust, docs
- [ ] Config template with standard exclusions
- [ ] Basic CLI for testing

Not yet implementing:
- Inference engine (Phase 2)
- Skills (Phase 3)
- Hooks (Phase 4)

## Key Types

```python
# Core data structures (to be implemented in meaning_core.py)

@dataclass
class Relationship:
    type: str           # From schema.yaml relationship_types
    target: str         # Path to related file
    source: str | None  # Optional source path (for bidirectional)

@dataclass  
class FileEntry:
    path: str
    intent: str
    tags: list[str]
    status: str         # active | draft | deprecated | generated
    needs_review: bool
    last_verified: datetime
    relationships: list[Relationship]

@dataclass
class Concept:
    name: str
    description: str
    files: list[str]
    entry_point: str

@dataclass
class MeaningIndex:
    version: str
    generated_at: datetime
    last_updated: datetime
    concepts: list[Concept]
    files: list[FileEntry]
```

## Integration Points

### Claude Code Hooks

The project uses Claude Code's hook system via `.claude/settings.json`:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/scripts/meaning-post-write.sh"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/scripts/meaning-validate.sh"
          }
        ]
      }
    ]
  }
}
```

### Skills

Skills are defined in `.claude/skills/<name>/SKILL.md` with YAML frontmatter:

- `/meaning-init` — Bootstrap `.meaning/` for a project
- `/meaning-update` — Sync index with filesystem
- `/meaning-validate` — Health check
- `/meaning-review` — Interactive review of flagged entries

## Glossary

| Term | Definition |
|------|------------|
| **Intent** | Natural language description of what a file does (max 280 chars) |
| **Concept** | A cross-file semantic grouping (e.g., "authentication", "api-parsing") |
| **Relationship** | A typed connection between two files (imports, tests, documents, etc.) |
| **Entry point** | The primary file for a concept—where to start reading |
| **Stale** | An entry not verified in > 7 days |
| **Needs review** | Flag indicating entry was auto-generated or file was modified |

## Questions?

Check `IMPLEMENTATION-PLAN.md` for detailed specifications. If something isn't covered there, it's an open question—document your assumption and proceed.

---

*Last updated: 2026-01-21*
