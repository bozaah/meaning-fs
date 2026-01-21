# Changelog

All notable changes to the Meaning project will be documented in this file.

## [Unreleased]

### 2026-01-21 — Dog-fooding + Inference Planning

#### Added
- **Dog-fooding initialization** — Created `.meaning/` for the Meaning project itself
  - `index.yaml` with 9 core files documented
  - 3 concepts defined: `project-documentation`, `core-library`, `development-tooling`
  - 18 relationships captured (documents, implements, calls)
  
- **Schema evolution** — Added `doc_type` vocabulary category
  - Tags: `overview`, `spec`, `dev-guide`, `history`, `ai`
  - Added to both `.meaning/schema.yaml` and `templates/schema/python.yaml`
  - Discovered organically through dog-fooding validation

- **Agent session infrastructure** — `.agent-sessions/` directory
  - Session notes for AI agent continuity between sessions
  - `.agent-sessions/README.md` — Guide for documenting sessions
  - `.agent-sessions/2026-01-21-dogfooding-inference-plan.md` — First session summary
  - Documents pain points discovered during manual indexing
  - Prioritizes inference features based on real tedium
  - Tracks assumptions, wins, and blockages per project philosophy

- **AGENTS.md symlink** — Points to CLAUDE.md for other AI agents
  - Provides consistent entry point for all agents
  - Documented in `.meaning/index.yaml`

- **Validation script** — `scripts/validate-meaning.sh`
  - Bash script wrapper for index validation
  - Formatted output with emojis and section headers
  - Auto-activates virtual environment
  - Separates unindexed file warnings from errors

#### Validated
- All 54 core tests passing
- Index validates successfully (0 errors, 13 warnings for unindexed files)
- Manual creation workflow verified and documented
- Validation catches unknown tags, stale entries, syntax errors
- Agent session workflow established

#### Pain Points Identified (Inference Targets)
1. Writing intent descriptions is slow (read file, understand, summarize)
2. Identifying relationships is tedious (requires cross-file thinking)
3. Picking tags requires vocabulary knowledge (schema lookup friction)
4. Timestamps are manual (easy to forget/hardcode wrong)
5. Concepts require semantic grouping analysis (high cognitive load)

#### Next Phase
- **Phase 2: Inference Engine** ready to start
- Prioritized features: auto-timestamps, detect `documents` relationships, suggest tags, draft intents
- Goal: Measure time savings by re-running inference on this project

---

### 2026-01-21 — Initial Scaffolding

#### Added
- **Repository structure** organized per CLAUDE.md specification
  - `src/` — Core Python library (`meaning_core.py`)
  - `scripts/` — Hook scripts (`meaning-post-write.sh`, `meaning-validate.sh`)
  - `templates/` — Templates for target projects using Meaning
  - `tests/` — Test suite with fixtures directory

- **Claude Code integration** (`.claude/` directory)
  - `settings.json` — Project hooks configuration (PostToolUse, Stop events)
  - Skills converted to official `SKILL.md` format with YAML frontmatter:
    - `/meaning-init` — Bootstrap `.meaning/` for a project
    - `/meaning-update` — Sync index with filesystem
    - `/meaning-validate` — Health check for semantic index
    - `/meaning-review` — Interactive review of flagged entries

- **Schema templates** (`templates/schema/`)
  - `python.yaml` — Python project relationships and tag vocabulary
  - `node.yaml` — Node.js project relationships and tag vocabulary
  - `rust.yaml` — Rust project relationships and tag vocabulary
  - `docs.yaml` — Documentation project relationships and tag vocabulary

- **Test stubs**
  - `test_core.py` — Existing core tests
  - `test_inference.py` — Placeholder tests for inference engine
  - `tests/fixtures/` — Directory for test fixtures

- **Project configuration**
  - `.gitignore` — Standard Python ignores + `.claude/settings.local.json`
  - `pyproject.toml` — Python project configuration

#### Changed
- Updated `CLAUDE.md` to reflect new `.claude/` structure
- Updated `templates/hooks.json` to use new Claude Code hook format (event-based with matchers)

#### Technical Notes
- Skills use YAML frontmatter with `allowed-tools` restrictions
- Hooks use `$CLAUDE_PROJECT_DIR` environment variable for portability
- Templates in `templates/` are for target projects; `.claude/` is for developing Meaning itself
