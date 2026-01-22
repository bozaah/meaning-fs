# Meaning: Semantic File Index for AI Agents

## Implementation Plan v0.1

> A lean, text-based semantic layer that lives alongside your files, readable by any AI agent, requiring no external services or embeddings.

---

## 1. Problem Statement

AI agents operating on codebases lack semantic context. They see files as paths and text, not as purposeful artifacts with relationships. This causes:

- **Inefficient navigation**: grep/search instead of understanding
- **Missed dependencies**: changes break things the agent didn't know were connected
- **Lost context**: no persistent "mental model" between sessions
- **Poor onboarding**: new agents (or humans) can't quickly grasp project structure

### Goal

A lean, text-based semantic layer that any AI agent can read and maintain, requiring no external services or embeddings.

### Philosophy

```
Do not write code before stating assumptions.
Do not claim correctness you haven't verified.
Do not handle only the happy path.
Under what conditions does this work?
```

---

## 2. Core Assumptions

### 2.1 Environment Assumptions

- [ ] Projects are version-controlled with Git
- [ ] AI agent has filesystem read/write access
- [ ] AI agent supports hooks (Claude Code hook system)
- [ ] YAML is readable by all target AI agents
- [ ] Projects have < 10,000 files (single index file remains manageable)

### 2.2 Usage Assumptions

- [ ] Developers/agents will maintain semantic records (not write-only)
- [ ] Relationships change less frequently than file contents
- [ ] Natural language intent is more valuable than structured-only metadata
- [ ] Some manual curation is acceptable; full automation is not required

### 2.3 Failure Mode Assumptions

- [ ] Stale metadata is worse than missing metadata
- [ ] Conflicts in `.meaning/` should block commits (fail loud)
- [ ] Agent should degrade gracefully if `.meaning/` is missing or corrupt

### 2.4 Open Assumptions to Validate

- Monorepo strategy: One root index or federated per-package?
- Relationship inference accuracy: Is "good enough" acceptable with human review?

---

## 3. Architecture

### 3.1 File Structure

```
project/
├── .claude/
│   └── hooks.json              # Claude Code hook configuration
├── .meaning/
│   ├── index.yaml              # Semantic records for all tracked files
│   ├── schema.yaml             # Project-specific vocabulary + relationship types
│   ├── config.yaml             # Exclusions, settings, project type hints
│   └── scripts/
│       ├── meaning-post-write.sh   # Post file mutation hook
│       ├── meaning-validate.sh     # Stop hook for consistency check
│       └── lib/
│           └── meaning_core.py     # Shared logic (Python for YAML handling)
```

### 3.2 Design Decisions

| Decision | Choice | Rationale | Tradeoffs |
|----------|--------|-----------|-----------|
| Single vs distributed index | Single `index.yaml` | Simpler mental model, atomic updates, easy to read | Merge conflicts on large teams, file size |
| Storage format | YAML | Human-readable, good AI parsing, no tooling needed | Verbose, merge conflicts possible |
| Relationship direction | Explicit source/target | Enables traversal in both directions | More verbose than implicit |
| Schema enforcement | Soft (warn, don't block) | Allows evolution, reduces friction | Vocabulary drift over time |
| Hook type | Deterministic scripts | Consistent, fast, auditable, testable | Requires maintenance |

#### Why Deterministic Scripts Over Prompts

| Aspect | Prompt-based | Script-based |
|--------|--------------|--------------|
| Consistency | May vary between runs | Identical behavior always |
| Speed | LLM inference time | Milliseconds |
| Auditability | Opaque | Git-trackable logic |
| Failure modes | Silent drift | Explicit errors |
| Testing | Difficult | Standard unit tests |

Scripts handle mechanical bookkeeping. The LLM focuses on semantic understanding during explicit review cycles.

---

## 4. File Specifications

### 4.1 index.yaml

The core semantic index containing all file metadata.

```yaml
version: "0.1"
generated_at: 2025-01-21T10:00:00Z
last_updated: 2025-01-21T14:30:00Z

# Cross-file semantic groupings
concepts:
  - name: authentication
    description: "User authentication and session management"
    files:
      - src/auth/login.py
      - src/auth/session.py
      - src/middleware/auth_middleware.py
      - src/models/user.py
      - tests/test_auth.py
    entry_point: src/auth/login.py

  - name: api-parsing
    description: "External API response handling and transformation"
    files:
      - src/api/client.py
      - src/api/parsers/response_parser.py
      - src/models/api_models.py
    entry_point: src/api/parsers/response_parser.py

# Individual file records
files:
  - path: src/api/client.py
    intent: "HTTP client that fetches raw responses from external APIs"
    tags: [api, http, external]
    status: active
    needs_review: false
    last_verified: 2025-01-21T10:00:00Z
    relationships:
      - type: calls
        target: src/api/endpoints.py

  - path: src/api/parsers/response_parser.py
    intent: "Transforms raw API JSON responses into domain models"
    tags: [api, parsing, transforms]
    status: active
    needs_review: false
    last_verified: 2025-01-21T10:00:00Z
    relationships:
      - type: transforms
        source: src/api/client.py
        target: src/models/api_models.py
      - type: validates
        target: src/api/schemas/response_schema.py

  - path: src/models/api_models.py
    intent: "Domain models representing parsed API data"
    tags: [models, api, domain]
    status: active
    needs_review: false
    last_verified: 2025-01-21T10:00:00Z
    relationships:
      - type: documents
        source: docs/api-models.md
      - type: tests
        source: tests/test_api_models.py
```

#### Field Specifications

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `path` | Yes | string | Relative path from project root |
| `intent` | Yes | string | 1-2 sentence natural language description (max 280 chars) |
| `tags` | No | list | From `schema.yaml` vocabulary |
| `status` | Yes | enum | `active`, `draft`, `deprecated`, `generated` |
| `needs_review` | Yes | bool | Flag for entries needing human/AI review |
| `last_verified` | Yes | ISO date | When accuracy was last confirmed |
| `relationships` | No | list | Connections to other files |

### 4.2 schema.yaml

Project-specific vocabulary and relationship definitions.

```yaml
version: "0.1"
project_type: api  # api | library | application | documentation | mixed

relationship_types:
  # Code structure
  - name: imports
    description: "Source file imports/depends on target"
    direction: source_to_target
    
  - name: implements
    description: "Source implements interface/contract defined in target"
    direction: source_to_target
    
  - name: extends
    description: "Source extends/inherits from target"
    direction: source_to_target

  # Data flow
  - name: calls
    description: "Source calls functions/methods in target"
    direction: source_to_target
    
  - name: transforms
    description: "Source transforms data and passes to target"
    direction: source_to_target
    
  - name: validates
    description: "Source validates data for/from target"
    direction: bidirectional

  # Documentation & testing
  - name: documents
    description: "Source documents target"
    direction: source_to_target
    
  - name: tests
    description: "Source tests target"
    direction: source_to_target

  # Lifecycle
  - name: supersedes
    description: "Source replaces deprecated target"
    direction: source_to_target
    
  - name: configures
    description: "Source provides configuration for target"
    direction: source_to_target

tag_vocabulary:
  domain:
    - api
    - auth
    - database
    - ui
    - config
    - utils
    - external
    
  concern:
    - parsing
    - validation
    - error-handling
    - logging
    - caching
    - security
    - transforms
    
  layer:
    - controller
    - service
    - model
    - util
    - test
    - doc
    - config
    - middleware

# Allow custom tags with prefix
custom_prefix: "x-"

statuses:
  - active      # Normal, maintained
  - draft       # Work in progress
  - deprecated  # Superseded, will be removed
  - generated   # Auto-generated, don't edit directly
```

### 4.3 config.yaml

Project settings and exclusion patterns.

```yaml
version: "0.1"

# Files to exclude from indexing
exclude:
  patterns:
    - "*.pyc"
    - "*.pyo"
    - "__pycache__/**"
    - "*.egg-info/**"
    - "node_modules/**"
    - ".git/**"
    - ".meaning/**"
    - "*.lock"
    - "*.log"
    - ".env*"
    - "dist/**"
    - "build/**"
    - "*.min.js"
    - "*.min.css"
    
  paths:
    - vendor/
    - .venv/
    - venv/
    - coverage/

# Files to include even if they match exclude patterns
include:
  paths: []

# Behavior settings
settings:
  require_intent: true          # Every file must have intent
  require_tags: false           # Tags optional
  warn_on_unknown_tags: true    # Warn but don't fail on unknown tags
  max_intent_length: 280        # Characters (tweet-length)
  stale_threshold_days: 7       # Flag records older than this
  auto_flag_modified: true      # Auto-set needs_review on file changes
```

---

## 5. Operations

### 5.1 Initialize (`/skill:meaning-init`)

**Purpose**: Bootstrap `.meaning/` for a new or existing project.

**Preconditions**:
- Current directory is a git repository root
- `.meaning/` does not exist OR user confirms overwrite

**Steps**:

1. **Detect project type**
   - Scan for: `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, etc.
   - Set `project_type` in schema accordingly

2. **Generate configuration files**
   - `schema.yaml` with sensible defaults for detected project type
   - `config.yaml` with standard exclusions

3. **Crawl non-excluded files**
   - Respect patterns in `config.yaml`
   - Track total count for progress

4. **For each file, infer metadata**:
   - `intent`: From docstrings, file headers, comments, filename patterns
   - `tags`: From path patterns (`/api/` → api tag), content analysis
   - `relationships`: From import/require statements
   - `status`: Default `active`, flag generated files as `generated`
   - `needs_review`: Set `true` for low-confidence inferences

5. **Detect concepts**
   - Group files by common path prefixes and tag clusters
   - Suggest concept groupings for user review

6. **Write files**
   - `index.yaml` with all entries
   - Hook scripts to `.meaning/scripts/`
   - Hook configuration to `.claude/hooks.json`

7. **Prompt user to review**
   - List files marked `needs_review: true`
   - Suggest running `/skill:meaning-review`

**Failure Modes**:

| Scenario | Behavior |
|----------|----------|
| Not a git repo | Error with instructions to run `git init` |
| `.meaning/` exists | Prompt: overwrite, merge, or abort |
| File read errors | Skip file, log warning, continue |
| Low inference confidence | Mark `needs_review: true` |
| Binary files | Skip or index with minimal metadata |

**Output**:
```
✓ Initialized .meaning/ for python project
  - 127 files indexed
  - 12 files need review
  - 34 files excluded
  - 3 concepts detected

Run `/skill:meaning-review` to refine entries marked for review.
```

### 5.2 Update (`/skill:meaning-update`)

**Purpose**: Sync index with filesystem changes.

**Preconditions**:
- `.meaning/` exists and is valid

**Steps**:

1. Load current `index.yaml`
2. Scan filesystem for changes:
   - **New files**: In filesystem, not in index
   - **Deleted files**: In index, not in filesystem
   - **Modified files**: mtime changed since `last_verified`
3. For new files: Infer metadata (same as init)
4. For deleted files: Remove from index, check for dangling relationships
5. For modified files: Flag `needs_review: true`, update `last_verified`
6. Update concept memberships if file paths changed
7. Write updated `index.yaml`

**Failure Modes**:

| Scenario | Behavior |
|----------|----------|
| Index corrupt | Backup to `.meaning/index.yaml.bak`, offer rebuild |
| Schema missing | Use permissive defaults, warn |
| Circular relationships | Warn but allow (can be valid) |

### 5.3 Validate (`/skill:meaning-validate`)

**Purpose**: Check index health and find drift.

**Checks**:
- [ ] All indexed files exist on disk
- [ ] All non-excluded files are indexed
- [ ] No unknown tags (unless `x-` prefixed)
- [ ] No unknown relationship types
- [ ] No dangling relationship targets
- [ ] No entries past `stale_threshold_days` (7 days)
- [ ] YAML is valid and parseable
- [ ] All required fields present

**Output**:
```
Meaning Index Health Report
===========================
✓ 127 files indexed
✓ All files exist on disk
✓ No orphaned entries

⚠ Warnings:
  - 3 files have stale entries (>7 days)
  - 1 unknown tag: "x-legacy" (custom tags allowed)

✗ Errors:
  - 2 dangling relationships:
    - src/api/old_parser.py (referenced by src/api/client.py)
    - tests/test_removed.py (referenced by src/models/user.py)

Suggested fixes:
  1. Run `/skill:meaning-update` to sync deleted files
  2. Review stale entries: src/auth/login.py, src/api/client.py, src/models/user.py
```

### 5.4 Review (`/skill:meaning-review`)

**Purpose**: Interactive review of entries needing attention.

**Behavior**:

1. Find all entries with `needs_review: true`
2. For each entry, present to user:
   - Current inferred metadata
   - File content summary
   - Suggested improvements
3. User can: approve, edit, or skip
4. Update entries and clear `needs_review` flag

### 5.5 Query (Agent Runtime)

**Purpose**: How agents use the index during normal operation.

**On Session Start**:
1. Read `.meaning/index.yaml`
2. Build mental model of project structure
3. Note `needs_review` entries and `deprecated` status

**When Asked to Make Changes** (e.g., "update how API responses are parsed"):
1. Parse request for intent keywords
2. Search index:
   - Match against `concepts[].name` and `concepts[].description`
   - Match against `files[].intent`
   - Match against `files[].tags`
   - Trace `relationships` for dependencies
3. Report relevant files with reasoning
4. After changes, hooks auto-flag modified files

**When Creating New Files**:
- Hooks auto-add skeleton entry
- Agent should update `intent` and `relationships` before session end

**When Deleting Files**:
- Hooks detect missing file on validate
- Agent should check for dangling relationships

---

## 6. Hooks (Deterministic Scripts)

### 6.1 Hook Configuration

**`.claude/hooks.json`**:
```json
{
  "hooks": [
    {
      "matcher": {
        "type": "PostToolUse",
        "tool_name": [
          "write_file",
          "create_file",
          "str_replace_editor",
          "edit_file",
          "Write",
          "Edit"
        ]
      },
      "script": ".meaning/scripts/meaning-post-write.sh",
      "timeout_ms": 5000
    },
    {
      "matcher": {
        "type": "Stop"
      },
      "script": ".meaning/scripts/meaning-validate.sh",
      "timeout_ms": 10000
    }
  ]
}
```

### 6.2 Post-Write Hook

**File**: `.meaning/scripts/meaning-post-write.sh`

**Trigger**: `PostToolUse` on file write/create/edit operations

**Input** (stdin JSON):
```json
{
  "session_id": "abc123",
  "tool_name": "write_file",
  "tool_input": {
    "path": "src/api/parser.py",
    "content": "..."
  },
  "tool_output": {
    "success": true
  }
}
```

**Behavior**:
1. Extract `path` from `tool_input`
2. Resolve to relative path from project root
3. Check against `config.yaml` exclusions → if excluded, exit early
4. Load `index.yaml`
5. Find existing entry OR create skeleton:
   ```yaml
   - path: src/api/parser.py
     intent: "[NEEDS REVIEW] Created/modified by agent"
     tags: []
     relationships: []
     status: active
     needs_review: true
     last_verified: 2025-01-21T10:00:00Z
   ```
6. If existing: set `needs_review: true`, update timestamp
7. Write `index.yaml`
8. Return success

**Output** (stdout JSON):
```json
{
  "status": "ok",
  "message": "Flagged src/api/parser.py for semantic review"
}
```

**Failure Handling**:
- `index.yaml` missing → Create minimal one, warn
- `index.yaml` corrupt → Backup, create fresh
- Write permission error → Return error status, don't block agent

### 6.3 Validate Hook

**File**: `.meaning/scripts/meaning-validate.sh`

**Trigger**: `Stop` (end of Claude session)

**Behavior**:
1. Load `index.yaml`
2. Run validation checks (see 5.3)
3. Generate summary report

**Output**:
```json
{
  "status": "ok",
  "summary": {
    "total_files": 127,
    "needs_review": 3,
    "stale": 2,
    "errors": 0
  },
  "warnings": [
    "3 files modified this session need semantic review",
    "1 new file added without relationships"
  ],
  "files_needing_review": [
    "src/api/parser.py",
    "src/models/response.py",
    "tests/test_parser.py"
  ]
}
```

This prompts Claude to ask:
> "I modified 3 files this session. Would you like me to update their semantic metadata now?"

---

## 7. Edge Cases and Failure Handling

| Scenario | Behavior |
|----------|----------|
| File renamed | Detected as delete + create; loses relationship history. Mitigation: Git rename detection in update. |
| Binary files | Excluded by default; can index with minimal metadata if explicitly included |
| Symlinks | Follow once, don't index target twice |
| Very large files | Index metadata only, skip content inference |
| Merge conflict in index.yaml | Fail pre-commit, require manual resolution |
| index.yaml deleted | Rebuild from scratch on next init, warn loudly |
| Circular relationships | Allow with warning (A transforms B, B validates A is valid) |
| Monorepo | Phase 5: Per-package `.meaning/` with optional root rollup |
| Empty project | Create minimal structure, no file entries |

---

## 8. What This Does NOT Do

Explicit non-goals to prevent scope creep:

- **Not a search engine**: No full-text indexing, no fuzzy matching
- **Not a knowledge graph DB**: No query language, no traversal algorithms built-in
- **Not auto-sync**: Requires hook trigger or explicit update
- **Not embeddings**: No vector similarity, pure text/structure matching
- **Not cross-repo**: Scoped to single repository
- **Not access control**: All metadata is plaintext, visible to all
- **Not a replacement for documentation**: Complements, doesn't replace READMEs

---

## 9. Implementation Phases

### Phase 1: Core Data Structures
- [ ] `schema.yaml` templates for: python, node, rust, go, docs
- [ ] `config.yaml` with standard exclusions per project type
- [ ] `index.yaml` parser/validator (Python module: `meaning_core.py`)
- [ ] Unit tests for YAML handling edge cases
- [ ] Basic CLI for testing: `python -m meaning validate`

### Phase 2: Inference Engine
- [ ] Intent inference from:
  - Docstrings (Python, JS, Rust, Go)
  - File headers / comments
  - Filename patterns (test_, _test, spec, etc.)
  - README proximity
- [ ] Relationship inference from:
  - Import statements (Python, JS, TS, Go, Rust)
  - Require/include patterns
  - Type references
- [ ] Concept detection from:
  - Path clustering
  - Tag co-occurrence
  - Import graphs
- [ ] Confidence scoring for inferred metadata

### Phase 3: Skills
- [ ] `/skill:meaning-init` — Full initialization flow
- [ ] `/skill:meaning-update` — Manual refresh  
- [ ] `/skill:meaning-validate` — Health check
- [ ] `/skill:meaning-review` — Interactive review of flagged items

### Phase 4: Hooks
- [ ] `meaning-post-write.sh` — Post-mutation tracking
- [ ] `meaning-validate.sh` — Session-end consistency
- [ ] `meaning_core.py` — Shared Python library
- [ ] `.claude/hooks.json` template
- [ ] Integration tests with mock Claude sessions

### Phase 5: Polish & Scale
- [ ] Monorepo support (federated indexes with root rollup)
- [ ] Schema evolution / migrations
- [ ] Mermaid diagram generation from relationships
- [ ] Stale entry detection and notifications
- [ ] Git pre-commit hook (optional strict mode)
- [ ] VS Code extension for visualization (stretch)

---

## 10. Success Criteria

This implementation is successful if:

1. **Queryable**: An AI agent can read `.meaning/` and accurately answer "which files handle X?"

2. **Low maintenance**: Index stays in sync with < 5 min/week manual effort

3. **Zero dependencies**: No external services, databases, or embeddings required

4. **Scalable**: Works for projects from 10 to 5,000 files

5. **Onboarding accelerator**: New team members (human or AI) build mental model 2x faster

6. **Deterministic**: Hook behavior is identical across runs, auditable, testable

---

## 11. Open Questions (To Resolve)

1. **Monorepo strategy**: One root index with package prefixes, or federated per-package indexes with optional rollup?
   - Leaning: Federated with rollup

2. **Git rename detection**: Worth the complexity to preserve relationship history?
   - Leaning: Phase 5, not MVP

3. **Conflict resolution**: Auto-merge strategies for `index.yaml` or always manual?
   - Leaning: Always manual, it's metadata worth reviewing

4. **Concept auto-detection**: How aggressive? Risk of noisy suggestions.
   - Leaning: Conservative, user-curated preferred

---

## 12. Appendix: Example Query Resolution

**User prompt**: "update how API responses are parsed"

**Agent process**:

1. **Load index**, scan concepts:
   ```yaml
   concepts:
     - name: api-parsing
       description: "External API response handling and transformation"
       entry_point: src/api/parsers/response_parser.py
   ```
   → Match on "api-parsing"

2. **Get concept files**:
   - `src/api/client.py`
   - `src/api/parsers/response_parser.py`
   - `src/models/api_models.py`

3. **Check relationships** from entry point:
   ```yaml
   - type: transforms
     source: src/api/client.py
     target: src/models/api_models.py
   - type: validates
     target: src/api/schemas/response_schema.py
   ```

4. **Expand to related files**:
   - `src/api/schemas/response_schema.py` (validation)
   - `tests/test_response_parser.py` (testing)

5. **Report to user**:
   > "For updating API response parsing, I identified these files:
   > - `response_parser.py` (main parsing logic)
   > - `api_models.py` (output models)
   > - `response_schema.py` (validation schema)
   > - `test_response_parser.py` (tests to update)
   > 
   > Should I start with `response_parser.py`?"

---

## 13. Future Enhancements (Post-v0.1)

### 13.1 Query Engine Improvements

**Completed in Phase 5:**
- ✅ Natural language query engine with 6 query types
- ✅ Status command for instant project overview
- ✅ Sub-50ms response time with zero LLM calls
- ✅ Relationship graph traversal
- ✅ Tag vocabulary matching
- ✅ Intent keyword search

**Future Enhancements:**

#### 13.1.1 Fuzzy Matching
- **Goal**: Handle typos and partial file names in queries
- **Example**: "what tests api" matches `src/api.py` despite missing `.py`
- **Implementation**: Levenshtein distance on file paths, threshold-based matching
- **Priority**: Medium

#### 13.1.2 Query Result Ranking
- **Goal**: Sort results by relevance score
- **Metrics**: Confidence scores, relationship depth, tag matches, intent keyword density
- **Example**: Files with multiple tag matches rank higher
- **Priority**: Medium

#### 13.1.3 Multi-Query Support
- **Goal**: Combine queries with AND/OR logic
- **Example**: "test files AND parsing files" → intersection of results
- **Syntax**: Natural language (`"test files that do parsing"`) or explicit operators
- **Priority**: Low

#### 13.1.4 Query History & Suggestions
- **Goal**: Remember recent queries, suggest related ones
- **Storage**: `.meaning/query_history.yaml` (last 100 queries)
- **Feature**: "Similar queries: ...", "Users also searched: ..."
- **Priority**: Low

#### 13.1.5 Export Results
- **Goal**: Export query results to various formats
- **Formats**: JSON, CSV, Markdown table, file list
- **Use case**: Integration with other tools, reports
- **Example**: `python -m meaning query "test files" --format json`
- **Priority**: Low

#### 13.1.6 Query Syntax Extensions
- **Goal**: More expressive query language
- **Features**:
  - Negation: "test files NOT parsing"
  - Wildcards: "files in src/api/*"
  - Date ranges: "files changed after 2026-01-15"
  - Tag combinations: "files tagged (api AND core) OR parsing"
- **Priority**: Low

### 13.2 Visualization

#### 13.2.1 Relationship Graph Export
- **Goal**: Export relationship graph for visualization tools
- **Format**: GraphViz DOT, Mermaid diagram, D3.js JSON
- **Use case**: Understand architecture visually
- **Priority**: Medium

#### 13.2.2 Concept Map
- **Goal**: Visual representation of concepts and their relationships
- **Output**: SVG/PNG diagram showing concept hierarchy
- **Priority**: Low

### 13.3 Advanced Inference

#### 13.3.1 Cross-File Analysis
- **Goal**: Infer relationships by analyzing multiple files together
- **Example**: Detect architectural patterns (repository pattern, factory pattern)
- **Implementation**: Multi-pass inference with pattern matching
- **Priority**: Low

#### 13.3.2 Historical Analysis
- **Goal**: Use git history to improve inference
- **Example**: Files often changed together likely have relationships
- **Data source**: `git log --name-only` analysis
- **Priority**: Low

### 13.4 Integration

#### 13.4.1 IDE Plugins
- **Goal**: VSCode/JetBrains integration
- **Features**: Hover tooltips show file intent, jump to related files, query sidebar
- **Priority**: Medium

#### 13.4.2 CI/CD Integration
- **Goal**: Automated validation in CI pipeline
- **Check**: Index is up-to-date, no validation errors, coverage thresholds
- **Exit codes**: Fail build if index is stale or invalid
- **Priority**: High

#### 13.4.3 LLM-Powered Query
- **Goal**: Use LLM for complex semantic understanding
- **When**: Fall back to LLM when structured queries fail
- **Example**: "Find files related to user authentication but not login UI"
- **Trade-off**: Slower but more flexible
- **Priority**: Low

---

*Document version: 0.1*
*Last updated: 2026-01-21*
