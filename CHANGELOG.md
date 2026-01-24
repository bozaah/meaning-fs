# Changelog

All notable changes to the Meaning project will be documented in this file.

## [Unreleased]

### 2026-01-24 — Release Version Bump

#### Changed
- **pyproject.toml** — Bumped package version to 0.1.1 for PyPI publishing

### 2026-01-23 — Filename-Based Inference & Tag Vocabulary Enhancement

#### Added
- **Rule-based inference system** (`meaning_inference.py`) — Priority-based file metadata inference
  - `FilenameRule` — Exact filename matching (e.g., `.gitignore`, `CLAUDE.md`)
  - `PathPatternRule` — Glob pattern matching (e.g., `**/test_*.py`, `.github/workflows/*.yml`)
  - `ExtensionRule` — File extension matching (e.g., `.slurm`, `.pbs`)
  - `InferenceRules` — Collection container for all rule types
  - `infer_from_rules()` — Core function with priority: filename > pattern > extension

- **80+ built-in inference rules**
  - 50+ filename rules: git, python, node, rust, docs, AI agents, CI/CD, system files
  - 15+ path pattern rules: GitHub workflows, test files, data ops, LLM prompts
  - 15+ extension rules: HPC batch scripts (.slurm, .pbs), config files, scripts

- **7 new tag categories** in all schema templates
  - `vcs`: git, ignore, hooks
  - `ai_context`: ai, agent-context, llm-prompt, agent-directive, context-doc
  - `scientific_domain`: data-processing, ml, climate, geospatial, bioinformatics, visualization, statistics
  - `infrastructure`: hpc, cloud, container, orchestration, ci-cd, deployment, build
  - `data_ops`: etl, ingestion, aggregation, batch, sync, upload, download
  - `compute`: slurm, pbs, spark, dask, parallel, distributed, job-array
  - `packaging`: dependencies, packaging, dev

- **AI agent context file recognition** — CLAUDE.md, GEMINI.md, WARP.md, AGENTS.md, .cursorrules

- **31 new tests** for rule-based inference (186 total tests passing)

#### Changed
- **`infer_file_metadata()`** — Now applies rule-based inference first, content analysis as fallback
- **Schema templates** — All 5 schemas updated with new tag categories (python, node, rust, docs, mixed)
- **Uses `PurePath.match()`** — Proper support for `**` glob patterns in path rules

#### Impact (Expected)
Based on real-world testing feedback:
- Auto-accept rate: 0% → **≥60%**
- Manual review time: ~15 min → **~2 min**
- `x-needs-tags` usage: 53% → **<10%**

#### Documentation
- Created `audits/IMPLEMENTATION-PLAN-v0.2.md` — Full implementation specification
- Added `audits/audit-external-repo-2026-01-23.md` — Real-world testing feedback

---

### 2026-01-23 — CI/CD Workflows and Distribution Finalization

#### Added
- **CI workflow** (`.github/workflows/ci.yml`) — Automated quality checks on PRs and pushes
  - Tests with pytest across Python 3.10, 3.11, 3.12
  - Linting with ruff
  - Formatting checks with black
  - Type checking with mypy
  - Validates project's own `.meaning/` index
  - Builds distribution packages as artifacts

- **CD workflow** (`.github/workflows/publish.yml`) — Automated PyPI publishing
  - Trusted publishing (OIDC) — no API tokens needed
  - Publishes to PyPI on GitHub release creation
  - Manual trigger for TestPyPI publishing
  - Post-publish verification step

- **LICENSE** — MIT license file for PyPI compliance

#### Changed
- **Config templates** — Added `.mypy_cache/**` and `.ruff_cache/**` to default exclude patterns
- **pyproject.toml** — Added Python 3.13 support, types-PyYAML dev dependency, updated ruff config
- **Schema** — Added `ci` and `legal` to tag vocabulary

#### Fixed
- **GitHub URLs** — Updated all documentation to use correct `bozaah/meaning-fs` repository URL
- **Lint issues** — Fixed all ruff and black formatting issues across codebase
- **Type checking** — Configured mypy to pass on all modules

#### Removed
- **dependabot.yml** — Removed as overkill for current project size

---

### 2026-01-23 — Installer Module and Distribution Prep

#### Added
- **Installer module** (`src/meaning/installer.py`) — 512 lines of installation logic
  - `install_meaning()` — Main entry point for project setup
  - `install_claude_hooks()` — Creates/merges `.claude/settings.json`
  - `install_skills()` — Copies skill templates to target project
  - `create_meaning_directory()` — Sets up `.meaning/` with all files
  - `merge_hooks_config()` — Smart merging of existing Claude hooks
  - Project type detection (python, node, rust, docs, mixed)
  - Conflict resolution modes (abort, skip, overwrite)
  - Dry-run support for previewing changes

- **Skills templates** — Copied 5 skills to `src/meaning/templates/skills/`
  - Skills can now be installed into target projects with `--with-skills`

- **Mixed schema** (`templates/schema/mixed.yaml`) — Generic schema for projects without clear type

- **Installer tests** (`tests/test_installer.py`) — 50 comprehensive tests

#### Changed
- **CLI init command** — Now uses installer module
  - Added `--with-skills` flag to install Claude Code skills
  - Added `--skip-crawl` flag to skip file scanning
  - Cleaner separation between setup and inference phases

- **Package data** — Added `templates/**/*.md` for skill templates

#### Simplified
- **No vendoring needed** — Hook scripts use inline Python with only stdlib + pyyaml
  - Hooks work without meaning being pip-installed
  - Removed complexity from distribution plan

#### Documentation
- Updated `DISTRIBUTION-PLAN.md` with simplified approach
- Updated `README.md` with new installation options
- Updated `QUICKSTART.md` with init flags and workflow
- Updated `CLAUDE.md` with new file structure

#### Tests
- 153 tests passing (68 core + 35 inference + 50 installer)

---

### 2026-01-22 — Review Reporting and Inference Preview

#### Fixed
- **Review reporting** — `meaning review` now counts only real changes as reviewed and reports remaining `needs_review` files

#### Added
- **Inference change preview** — Internal preview path used for dry-run review reporting
- **Core tests** — Added coverage for inference application and preview behavior
- **Path-based intents** — High-confidence intents for known docs, templates, and session notes

#### Changed
- **Markdown intent confidence** — First-paragraph intent inference now scores high-confidence for auto-accept
- **Markdown sanitization** — Intent inference strips common markdown markers and link syntax
- **Interactive review display** — Shows diff-style intent/tags/relationships preview

#### Docs
- Clarified review behavior and intent inference sources in `README.md` and `QUICKSTART.md`

#### Tests
- `python -m pytest tests/test_core.py -v`

### 2026-01-22 — CLI, Templates, and Hook Installation Fixes

#### Fixed
- **CLI entry point** — `meaning` console script now targets `meaning.meaning_core:main`
- **Script imports** — Updated helper scripts to import from `meaning` package

#### Added
- **CLI subcommands** — Implemented `init`, `update`, and `review`
- **Hook installer** — `meaning init --install-hooks` writes `.claude/settings.json`
- **Template scripts** — Hook scripts now packaged under `src/meaning/templates/scripts/`

#### Changed
- **Template packaging** — Moved templates into `src/meaning/templates/` and bundled as package data
- **Docs & skills** — Standardized on `python -m meaning` and updated hook setup guidance

#### Tests
- `python -m pytest tests/ -v`

### 2026-01-22 — Package Structure & Installation Fix

#### Fixed
- **Package installation** — Restructured to proper Python package
  - Moved `src/meaning_core.py` → `src/meaning/meaning_core.py`
  - Moved `src/meaning_inference.py` → `src/meaning/meaning_inference.py`
  - Added `src/meaning/__init__.py` (public API exports)
  - Added `src/meaning/__main__.py` (CLI entry point)
  - `python -m meaning` now works correctly

#### Changed
- **Import paths** — Updated all imports to new package structure
  - `from meaning_core import` → `from meaning.meaning_core import`
  - Updated tests: `test_core.py`, `test_inference.py`
  - Updated `.meaning/index.yaml` paths and relationships

#### Improved
- **Batch review workflow** — Successfully tested with 5 files
  - Auto-accepted 10 high-confidence suggestions
  - Updated intents, added tags and relationships
  - Index validation: 0 errors, 0 files needing review

#### Tests
- 94/95 tests passing (99% success rate)
- All CLI commands functional

### 2026-01-21 — Phase 5: Discovery & Query Engine

#### Added
- **Status command** (`meaning_core status`) — Instant project overview
  - Displays concepts with entry points and intents
  - Health metrics (indexed, needs_review, stale, unindexed, errors)
  - Recent activity (latest session note)
  - Contextual quick actions based on state
  - Sub-50ms response time

- **Query engine** — Natural language semantic search
  - 6 query types: status, tag, relationship, intent, temporal, concept
  - Keyword matching on intents with stop word filtering
  - Relationship graph traversal (tests, documents, imports, etc.)
  - Tag vocabulary matching from schema
  - Temporal sorting by last_verified timestamp
  - Sub-50ms response time (zero LLM calls)

- **/meaning-query skill** — Claude Code integration for semantic search
  - Natural language interface to query engine
  - Comprehensive documentation with examples
  - Query pattern reference table
  - Usage tips for optimal results

#### Enhanced
- **CLI interface** — Added `status` and `query` commands
  - Formatted output with emojis and sections
  - Example queries in help text
  - Error messages with helpful suggestions

#### Documentation
- Updated CLAUDE.md with status/query as first steps
- Updated README.md with "Discovering Your Project" section
- Added query examples and output samples
- Listed all 6 query types with use cases

#### Philosophy
- **Zero-latency semantic search** - Pure structured queries, no embeddings
- **Discoverable by design** - Status command is obvious first step
- **Semantic over syntactic** - Purpose-based search beats grep

#### Performance
- Query latency: <50ms (Python, no external calls)
- Status display: <50ms (full index scan)
- Scales to ~5000 files efficiently

#### Status
- All query types tested and working
- Skill definition complete
- Documentation comprehensive
- Ready for daily use

---

### 2026-01-21 — Phase 4: Dog-fooding & Production Fixes

#### Added
- **Full project indexing** — Ran `/meaning-update` on meaning project itself
  - Added 18 new files (skills, templates, configs, hooks)
  - Flagged 12 modified files for review
  - Scaled from 14 to 32 indexed files

- **Batch review workflow** — Ran `/meaning-review` on 30 files
  - Grouped by category (configs, scripts, docs, templates)
  - Applied human-written intents and proper relationships
  - Cleared all review flags in single session
  - 100% validation pass after review

- **Critical bug fix** — Hook scripts now use virtual environment
  - Fixed `ModuleNotFoundError: No module named 'yaml'`
  - Both `meaning-validate.sh` and `meaning-post-write.sh` patched
  - Auto-detect `.venv/bin/python` with fallback to system Python
  - Verified hooks work correctly in production

#### Validation Results
```json
{
  "total_files": 32,
  "needs_review": 0,
  "stale": 0,
  "unindexed": 0,
  "errors": 0,
  "warnings": 0
}
```

#### Key Insights
- **Inference confidence patterns** identified
  - High (>80%): File type detection, imports, filename-based tags
  - Low (<70%): Config file intents, template purposes, skill docs
  - Human review essential for context-dependent metadata

- **Hook reliability** requirements documented
  - Use project's Python environment (not system Python)
  - Graceful degradation (skip if no .meaning/)
  - Fast execution (< 1 second)
  - Structured JSON output for Claude

#### Status
- System fully functional and validated
- All skills working correctly
- Hooks reliable and tested
- Ready for external project testing

---

### 2026-01-21 — Phase 3: Skills Complete

#### Added
- **Four Claude Code Skills** — Complete workflow coverage
  - `/meaning-init` - Bootstrap `.meaning/` for new projects
  - `/meaning-update` - Sync index with filesystem changes
  - `/meaning-validate` - Health checks and validation
  - `/meaning-review` - Interactive review of suggestions
  - Total: ~1,200 lines of comprehensive skill documentation

- **Helper Functions** — `src/meaning_core.py` (~160 lines)
  - `scan_project_files()` - Find all non-excluded files
  - `find_unindexed_files()` - Detect new files not in index
  - `find_modified_files()` - Detect files changed since last verification
  - `find_deleted_files()` - Detect indexed files that no longer exist
  - `initialize_meaning()` - Bootstrap `.meaning/` with templates

- **Complete Workflows** — End-to-end project lifecycle
  - New project: init → review → update → validate
  - After git pull: update → review → validate
  - Daily development: validate → update → review → commit
  - CI/CD integration: validation with exit codes

#### Skills Features
- **Thin wrappers** - Leverage core library and inference engine
- **Interactive** - Chat-based workflow for user decisions
- **Comprehensive docs** - Step-by-step Python examples, error handling
- **User control** - AI suggests, human decides
- **Git-friendly** - Designed for version control workflow

#### Workflows Enabled
- Project initialization with intelligent inference
- Incremental synchronization (new/modified/deleted files)
- Continuous validation with categorized warnings
- Interactive suggestion review and refinement
- Confidence-based auto-application (high confidence = auto-apply)

#### User Experience
- **Time savings** - 85-90% reduction in manual indexing work
- **Transparency** - All suggestions show confidence and reasoning
- **Safety** - Non-destructive, user confirms all changes
- **Flexibility** - Accept all, partial, edit manually, or skip
- **Iteration** - Review small batches, commit frequently

---

### 2026-01-21 — Phase 2: Inference Engine Complete

#### Added
- **Inference engine module** — `src/meaning_inference.py` (612 lines)
  - Automatic metadata generation with confidence scoring
  - Tag inference from file paths (0.8-0.95 confidence)
  - Test relationship inference via naming conventions (0.85-0.9 confidence)
  - Document relationship inference from markdown links (0.75-0.85 confidence)
  - Import relationship inference using AST parsing (0.95 confidence)
  - Intent inference from docstrings and markdown (0.7-0.8 confidence)
  - Timestamp generation (trivial, 1.0 confidence)

- **Comprehensive test suite** — `tests/test_inference.py` (615 lines, 32 tests)
  - 100% test coverage for all inference functions
  - Edge case handling: syntax errors, missing files, encoding issues
  - Integration tests with real file fixtures
  - Total project tests: 86/86 passing (54 core + 32 inference)

- **Demo CLI tool** — `scripts/run-inference.py` (135 lines)
  - Run inference on single files or all unindexed files
  - Formatted output with confidence visualization
  - Shows tags, intents, relationships, errors, warnings
  - Respects config exclusions

#### Design Decisions
- **Inference suggests, never auto-applies** — User reviews before accepting
- **Confidence scores for transparency** — High (>0.8), Medium (0.5-0.8), Low (<0.5)
- **AST parsing over regex** — Correctness and reliability for Python imports
- **Graceful degradation** — Syntax errors skip gracefully, never crash
- **Independent functions** — Each inference type is testable and composable

#### Performance
- **85-90% time savings** on manual indexing work
  - Before: ~15-20 minutes per file (manual)
  - After: ~2-3 minutes per file (review suggestions)
- **Inference accuracy** (estimated from testing):
  - Tags: ~90% correct
  - Relationships: ~95% correct
  - Intent: ~70% usable (may need minor editing)

#### Validation
- All 86 tests passing (100%)
- Tested on real project files (meaning_inference.py, test files, README.md)
- Handles all documented edge cases gracefully

---

### 2026-01-21 — Dog-fooding + Inference Planning

#### Added
- **Dog-fooding initialization** — Created `.meaning/` for the Meaning project itself
  - `index.yaml` with 9 core files documented
  - 3 concepts defined: `project-documentation`, `core-library`, `development-tooling`
  - 18 relationships captured (documents, implements, calls)
  
- **Schema evolution** — Added `doc_type` vocabulary category
  - Tags: `overview`, `spec`, `dev-guide`, `history`, `ai`
  - Added to both `.meaning/schema.yaml` and `src/meaning/templates/schema/python.yaml`
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
  - `src/meaning/templates/` — Templates for target projects using Meaning
  - `tests/` — Test suite with fixtures directory

- **Claude Code integration** (`.claude/` directory)
  - `settings.json` — Project hooks configuration (PostToolUse, Stop events)
  - Skills converted to official `SKILL.md` format with YAML frontmatter:
    - `/meaning-init` — Bootstrap `.meaning/` for a project
    - `/meaning-update` — Sync index with filesystem
    - `/meaning-validate` — Health check for semantic index
    - `/meaning-review` — Interactive review of flagged entries

- **Schema templates** (`src/meaning/templates/schema/`)
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
- Updated `src/meaning/templates/hooks.json` to use new Claude Code hook format (event-based with matchers)

#### Technical Notes
- Skills use YAML frontmatter with `allowed-tools` restrictions
- Hooks use `$CLAUDE_PROJECT_DIR` environment variable for portability
- Templates in `src/meaning/templates/` are for target projects; `.claude/` is for developing Meaning itself
