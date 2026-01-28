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

**v0.2 — Modular Architecture** ✅

- ✅ **Modular codebase** - 8 specialized modules (constants, models, index_io, validation, project, index_ops, query, cli)
- ✅ **Inference engine** (`meaning_inference.py`) - 1,222 lines with **80+ built-in rules**
- ✅ **Rule-based inference** - Automatic metadata for common files (`.gitignore`, `CLAUDE.md`, `*.slurm`)
- ✅ **Enhanced tag vocabulary** - 7 categories (HPC, AI agents, scientific computing, data ops)
- ✅ **Status command** - Instant project overview with concepts, health metrics, and recent activity
- ✅ **Query engine** - Natural language semantic search (6 query types, <50ms response)
- ✅ Five Claude Code skills (`/meaning-init`, `/meaning-update`, `/meaning-validate`, `/meaning-review`, `/meaning-query`)
- ✅ Hook scripts for automatic tracking
- ✅ Dog-fooded on itself (75 files indexed, 190 tests passing)

**Next:** PyPI release, real-world validation testing

## Quick Start

### Installation

```bash
# Install from source (PyPI coming soon)
pip install git+https://github.com/bozaah/meaning-fs.git

# Or for development
git clone https://github.com/bozaah/meaning-fs.git
cd meaning-fs
uv venv && uv pip install -e ".[dev]"
```

### Initialize a Project

```bash
# Basic initialization (auto-detects project type)
meaning init

# With Claude Code integration
meaning init --install-hooks --with-skills

# Skip file scanning (just setup the structure)
meaning init --skip-crawl
```

### With Claude Code Skills

```bash
# In your project directory with Claude Code
/meaning-init              # Bootstrap .meaning/ with intelligent inference
/meaning-review            # Review and approve suggested metadata
/meaning-validate          # Check index health

# During development
/meaning-update            # Sync with filesystem changes
/meaning-query             # Semantic search
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
- **Rule-Based Inference** - 80+ built-in rules for automatic metadata on common files
  - Filename rules: `.gitignore`, `requirements.txt`, `CLAUDE.md`, `Dockerfile`, etc.
  - Path patterns: `**/test_*.py`, `.github/workflows/*.yml`, `**/prompts/**/*.md`
  - Extension rules: `.slurm`, `.pbs`, `.env` for domain-specific files
- **Intent Extraction** - Docstrings, markdown summaries, and leading comment blocks for scripts
- **AI Agent Context Recognition** - Automatic detection of `CLAUDE.md`, `GEMINI.md`, `WARP.md`, `.cursorrules`
- **Enhanced Tag Vocabulary** - 7 domain-specific categories:
  - `vcs` (git, ignore, hooks)
  - `ai_context` (agent-context, llm-prompt)
  - `scientific_domain` (data-processing, ml, climate, bioinformatics)
  - `infrastructure` (hpc, cloud, container, ci-cd)
  - `data_ops` (etl, batch, sync, upload)
  - `compute` (slurm, pbs, spark, dask)
  - `packaging` (dependencies, dev)
- **60%+ Auto-Accept Rate** - Most common files get high-confidence metadata automatically
- **Git-Friendly** - Human-readable YAML files that diff and merge cleanly
- **Zero Dependencies** - Works offline, no external services or embeddings
- **Batch Review** - Efficient workflows for reviewing many files at once
- **Claude Code Integration** - Automatic tracking via hooks on file changes
- **Transparent** - All suggestions show confidence levels and reasoning
- **Non-Destructive** - Human reviews and approves all changes
- **Exclusion-Aware Updates** - `meaning update` drops index entries matching exclude patterns

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

### Rule-Based Inference

Common files are automatically recognized with high confidence:

```yaml
# .gitignore → confidence: 1.0
- path: .gitignore
  intent: "Git version control ignore patterns"
  tags: [config, vcs, ignore]

# CLAUDE.md → confidence: 1.0  
- path: CLAUDE.md
  intent: "Claude AI agent project context and directives"
  tags: [doc, ai, agent-context]

# jobs/run.slurm → confidence: 0.95
- path: jobs/run.slurm
  intent: "SLURM batch job submission script"
  tags: [script, hpc, slurm, batch]
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
├── .agent-sessions/            # AI agent session notes
├── .claude/                    # Claude Code configuration
│   ├── settings.json           # Project hooks and permissions
│   └── skills/                 # Skill definitions
│       ├── meaning-init/
│       ├── meaning-query/
│       ├── meaning-review/
│       ├── meaning-update/
│       └── meaning-validate/
├── .meaning/                   # Dog-fooding: our own semantic index
├── src/
│   └── meaning/
│       ├── __init__.py         # Public API exports
│       ├── __main__.py         # CLI entry point
│       ├── meaning_core.py     # Core library
│       ├── meaning_inference.py # Inference engine
│       ├── installer.py        # Installation logic
│       └── templates/          # Project templates
│           ├── schema/         # Project-type schemas (python, node, rust, docs, mixed)
│           ├── skills/         # Claude Code skill templates
│           ├── config.yaml     # Default config
│           ├── hooks.json      # Claude hooks template
│           └── scripts/        # Hook scripts for target projects
├── scripts/
│   ├── meaning-post-write.sh   # Post-mutation hook
│   ├── meaning-validate.sh     # Session-end hook
│   ├── run-inference.py        # Inference runner script
│   └── validate-meaning.sh     # Validate this project's index
└── tests/
    ├── fixtures/               # Test fixtures
    ├── test_core.py            # Core library tests
    ├── test_inference.py       # Inference engine tests
    └── test_installer.py       # Installer tests
```

## Documentation

- **[Quick Start Guide](QUICKSTART.md)** — Get started in 5 minutes
- [Implementation Plan](IMPLEMENTATION-PLAN.md) — Full specification
- [CLAUDE.md](CLAUDE.md) / [AGENTS.md](AGENTS.md) — Guide for AI agents working on this project
- [Agent Sessions](.agent-sessions/) — Session notes documenting project evolution
- [Audits](audits/) — Real-world testing feedback and implementation plans

## Supported File Types

Meaning includes built-in recognition for:

| Category | Files |
|----------|-------|
| **Git/VCS** | `.gitignore`, `.gitattributes`, `.gitmodules` |
| **Python** | `requirements.txt`, `pyproject.toml`, `setup.py`, `conftest.py` |
| **Node.js** | `package.json`, `yarn.lock`, `tsconfig.json` |
| **Rust** | `Cargo.toml`, `Cargo.lock` |
| **Documentation** | `README.md`, `CHANGELOG.md`, `LICENSE`, `CONTRIBUTING.md` |
| **AI Agents** | `CLAUDE.md`, `GEMINI.md`, `WARP.md`, `AGENTS.md`, `.cursorrules` |
| **CI/CD** | `Dockerfile`, `docker-compose.yml`, GitHub workflows |
| **HPC/Scientific** | `.slurm`, `.pbs`, `.sge` batch scripts |
| **Data Ops** | `upload_*.sh`, `download_*.sh`, `sync_*.sh` patterns |

## License

MIT
