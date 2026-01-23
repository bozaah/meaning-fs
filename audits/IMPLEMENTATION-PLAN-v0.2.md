# Implementation Plan: Filename-Based Inference & Enhanced Tag Vocabulary

> Version 0.2 Enhancement — Based on Real-World Testing Feedback

**Date:** 2026-01-23  
**Priority:** P0 (Critical for usability)  
**Based on:** [audit-external-repo-2026-01-23.md](./audit-external-repo-2026-01-23.md)

---

## Executive Summary

Real-world testing revealed two critical gaps:
1. **0% auto-accept rate** because common files get no metadata
2. **53% of files tagged `x-needs-tags`** due to web-app-focused vocabulary

**Target:** ≥60% auto-accept rate, <10% files needing `x-needs-tags`

---

## Architecture Decision

### Rule Storage Strategy

**Chosen: Built-in defaults + config overrides**

| Approach | Pros | Cons |
|----------|------|------|
| Hardcode in Python | Fast, no I/O | Not customizable |
| Config-only | Fully customizable | Empty by default, poor DX |
| **Built-in + overrides** | Fast, customizable, good DX | Slightly more complex |

**Implementation:**
- `DEFAULT_INFERENCE_RULES` constant in `meaning_inference.py`
- Optional `inference_rules` section in `config.yaml` for overrides
- Project rules override built-in rules for same filename/pattern

### Inference Priority

```
1. Exact filename match (confidence: 0.95-1.0)
2. Path pattern match (confidence: 0.80-0.95)
3. Content analysis (confidence: varies) ← current behavior
4. Extension match (confidence: 0.50-0.85, fallback)
```

When `fallback_to_content: true`, merge rule-based tags with content-inferred intent.

---

## Phase 1: Core Infrastructure

### 1.1 Data Structures

Add to `meaning_inference.py`:

```python
@dataclass
class FilenameRule:
    """Rule for exact filename matching."""
    filename: str
    intent: str
    tags: list[str]
    confidence: float = 0.95

@dataclass
class PathPatternRule:
    """Rule for glob pattern matching on full path."""
    pattern: str  # glob pattern, e.g., "**/upload_*.sh"
    intent: str
    tags: list[str]
    confidence: float = 0.85
    fallback_to_content: bool = False

@dataclass  
class ExtensionRule:
    """Rule for file extension matching."""
    extension: str  # including dot, e.g., ".slurm"
    intent: str
    tags: list[str]
    confidence: float = 0.70
    fallback_to_content: bool = True

@dataclass
class InferenceRules:
    """Collection of all inference rules."""
    exact_filenames: list[FilenameRule]
    path_patterns: list[PathPatternRule]
    extension_rules: list[ExtensionRule]
```

### 1.2 Rule Evaluation Function

```python
def infer_from_rules(
    file_path: str,
    rules: InferenceRules,
) -> tuple[InferredIntent | None, list[InferredTag], bool]:
    """
    Apply inference rules to a file path.
    
    Returns:
        (intent, tags, should_fallback_to_content)
    """
```

### 1.3 Integration Point

Modify `infer_file_metadata()` to:
1. Load rules (built-in + config overrides)
2. Apply rule-based inference first
3. If `fallback_to_content=True` or no rule matched, continue with content analysis
4. Merge results

---

## Phase 2: Built-in Filename Rules

### Git/VCS Files
| Filename | Intent | Tags | Confidence |
|----------|--------|------|------------|
| `.gitignore` | Git version control ignore patterns | `[config, vcs, ignore]` | 1.0 |
| `.gitattributes` | Git file attributes configuration | `[config, vcs]` | 1.0 |
| `.gitmodules` | Git submodule configuration | `[config, vcs]` | 1.0 |

### Python Project Files
| Filename | Intent | Tags | Confidence |
|----------|--------|------|------------|
| `requirements.txt` | Python package dependencies (pip) | `[config, dependencies]` | 1.0 |
| `requirements-dev.txt` | Python development dependencies | `[config, dependencies, dev]` | 1.0 |
| `setup.py` | Python package setup script | `[config, packaging]` | 1.0 |
| `setup.cfg` | Python package configuration | `[config, packaging]` | 1.0 |
| `pyproject.toml` | Python project configuration (PEP 518) | `[config, packaging]` | 1.0 |
| `MANIFEST.in` | Python package manifest | `[config, packaging]` | 0.95 |
| `pytest.ini` | Pytest configuration | `[config, test]` | 1.0 |
| `conftest.py` | Pytest fixtures and configuration | `[test, fixture]` | 0.95 |
| `.python-version` | Python version specification | `[config]` | 1.0 |

### Node/JavaScript Files
| Filename | Intent | Tags | Confidence |
|----------|--------|------|------------|
| `package.json` | Node.js package manifest | `[config, dependencies, packaging]` | 1.0 |
| `package-lock.json` | Node.js dependency lock file | `[config, dependencies, generated]` | 1.0 |
| `yarn.lock` | Yarn dependency lock file | `[config, dependencies, generated]` | 1.0 |
| `pnpm-lock.yaml` | pnpm dependency lock file | `[config, dependencies, generated]` | 1.0 |
| `tsconfig.json` | TypeScript configuration | `[config]` | 1.0 |
| `.nvmrc` | Node version specification | `[config]` | 1.0 |

### Documentation Files
| Filename | Intent | Tags | Confidence |
|----------|--------|------|------------|
| `README.md` | Project overview and documentation | `[doc, overview]` | 1.0 |
| `README` | Project overview and documentation | `[doc, overview]` | 1.0 |
| `CHANGELOG.md` | Project change history and release notes | `[doc, history]` | 1.0 |
| `HISTORY.md` | Project history | `[doc, history]` | 1.0 |
| `CONTRIBUTING.md` | Contribution guidelines | `[doc, dev-guide]` | 1.0 |
| `CODE_OF_CONDUCT.md` | Community code of conduct | `[doc]` | 1.0 |
| `LICENSE` | Project license | `[doc, legal]` | 1.0 |
| `LICENSE.md` | Project license | `[doc, legal]` | 1.0 |
| `LICENSE.txt` | Project license | `[doc, legal]` | 1.0 |
| `AUTHORS` | Project authors list | `[doc]` | 0.95 |
| `SECURITY.md` | Security policy and reporting | `[doc, security]` | 1.0 |

### AI Agent Context Files
| Filename | Intent | Tags | Confidence |
|----------|--------|------|------------|
| `CLAUDE.md` | Claude AI agent project context and directives | `[doc, ai, agent-context]` | 1.0 |
| `GEMINI.md` | Google Gemini agent project context | `[doc, ai, agent-context]` | 1.0 |
| `AGENTS.md` | AI agent project context | `[doc, ai, agent-context]` | 1.0 |
| `WARP.md` | AI/Warp agent project context | `[doc, ai, agent-context]` | 1.0 |
| `COPILOT.md` | GitHub Copilot context | `[doc, ai, agent-context]` | 1.0 |
| `.cursorrules` | Cursor AI editor rules | `[config, ai, agent-context]` | 1.0 |
| `.aider.conf.yml` | Aider AI assistant configuration | `[config, ai]` | 1.0 |

### System/Generated Files
| Filename | Intent | Tags | Confidence |
|----------|--------|------|------------|
| `.DS_Store` | macOS Finder metadata (should be git-ignored) | `[system, generated]` | 1.0 |
| `Thumbs.db` | Windows thumbnail cache (should be git-ignored) | `[system, generated]` | 1.0 |
| `.editorconfig` | Editor configuration | `[config]` | 1.0 |

### CI/CD Files
| Filename | Intent | Tags | Confidence |
|----------|--------|------|------------|
| `Makefile` | Build automation rules | `[config, build]` | 0.95 |
| `Dockerfile` | Docker container definition | `[config, container]` | 1.0 |
| `docker-compose.yml` | Docker Compose service definitions | `[config, container, orchestration]` | 1.0 |
| `docker-compose.yaml` | Docker Compose service definitions | `[config, container, orchestration]` | 1.0 |
| `.dockerignore` | Docker build ignore patterns | `[config, container, ignore]` | 1.0 |

---

## Phase 3: Enhanced Tag Vocabulary

Add to all `schema/*.yaml` files:

```yaml
tag_vocabulary:
  # === EXISTING (keep all) ===
  domain:
    - api
    - auth
    - database
    - ui
    - cli
    - config
    - utils
    - external
    - core
    - models

  concern:
    - parsing
    - validation
    - error-handling
    - logging
    - caching
    - security
    - transforms
    - serialization
    - async
    - concurrency

  layer:
    - controller
    - service
    - repository
    - model
    - schema
    - util
    - test
    - fixture
    - doc
    - config
    - middleware
    - decorator

  doc_type:
    - overview
    - spec
    - dev-guide
    - history
    - ai
    - legal          # NEW

  file_type:
    - module
    - package
    - script
    - test
    - config
    - migration
    - fixture
    - generated      # NEW

  # === NEW CATEGORIES ===

  # Version Control
  vcs:
    - git
    - ignore
    - hooks

  # AI/Agent Context
  ai_context:
    - ai
    - agent-context
    - llm-prompt
    - agent-directive
    - context-doc

  # Scientific/Data Domains
  scientific_domain:
    - data-processing
    - ml
    - climate
    - geospatial
    - bioinformatics
    - visualization
    - statistics

  # Infrastructure
  infrastructure:
    - hpc
    - cloud
    - container
    - orchestration
    - ci-cd
    - deployment
    - build

  # Data Operations
  data_ops:
    - etl
    - ingestion
    - aggregation
    - batch
    - sync
    - upload
    - download

  # Compute Platforms
  compute:
    - slurm
    - pbs
    - spark
    - dask
    - parallel
    - distributed
    - job-array

  # Package Management
  packaging:
    - dependencies
    - packaging
    - dev
```

---

## Phase 4: Extension Rules

### Scientific/HPC Extensions
| Extension | Intent | Tags | Confidence |
|-----------|--------|------|------------|
| `.slurm` | SLURM batch job submission script | `[script, hpc, slurm, batch]` | 0.95 |
| `.sbatch` | SLURM batch script | `[script, hpc, slurm, batch]` | 0.95 |
| `.pbs` | PBS/Torque batch script | `[script, hpc, pbs, batch]` | 0.95 |
| `.sge` | Sun Grid Engine batch script | `[script, hpc, batch]` | 0.95 |

### Data/Config Extensions
| Extension | Intent | Tags | Confidence |
|-----------|--------|------|------------|
| `.yaml` | YAML configuration or data | `[config]` | 0.50 |
| `.yml` | YAML configuration or data | `[config]` | 0.50 |
| `.toml` | TOML configuration | `[config]` | 0.60 |
| `.json` | JSON data or configuration | `[config]` | 0.50 |
| `.ini` | INI configuration file | `[config]` | 0.60 |
| `.env` | Environment variables file | `[config, security]` | 0.80 |
| `.env.example` | Environment variables template | `[config, doc]` | 0.90 |

### Script Extensions
| Extension | Intent | Tags | Confidence |
|-----------|--------|------|------------|
| `.sh` | Shell script | `[script]` | 0.60 |
| `.bash` | Bash script | `[script]` | 0.65 |
| `.zsh` | Zsh script | `[script]` | 0.65 |

**Note:** Low confidence for generic extensions — `fallback_to_content: true`

---

## Phase 5: Path Pattern Rules

### Scientific Computing Patterns
| Pattern | Intent | Tags | Confidence |
|---------|--------|------|------------|
| `**/compute_*.py` | Computational data processing module | `[module, data-processing]` | 0.80 |
| `**/process_*.py` | Data processing module | `[module, data-processing]` | 0.80 |
| `**/analyze_*.py` | Data analysis module | `[module, data-processing, statistics]` | 0.80 |

### Data Operations Patterns
| Pattern | Intent | Tags | Confidence |
|---------|--------|------|------------|
| `**/upload_*.sh` | Data upload script | `[script, upload, deployment]` | 0.85 |
| `**/download_*.sh` | Data download script | `[script, download]` | 0.85 |
| `**/sync_*.sh` | Data synchronization script | `[script, sync]` | 0.85 |

### CI/CD Patterns
| Pattern | Intent | Tags | Confidence |
|---------|--------|------|------------|
| `.github/workflows/*.yml` | GitHub Actions workflow | `[config, ci-cd]` | 0.95 |
| `.github/workflows/*.yaml` | GitHub Actions workflow | `[config, ci-cd]` | 0.95 |
| `.gitlab-ci.yml` | GitLab CI configuration | `[config, ci-cd]` | 1.0 |
| `.circleci/config.yml` | CircleCI configuration | `[config, ci-cd]` | 1.0 |

### Test Patterns
| Pattern | Intent | Tags | Confidence |
|---------|--------|------|------------|
| `**/test_*.py` | Python test module | `[test]` | 0.90 |
| `**/*_test.py` | Python test module | `[test]` | 0.90 |
| `**/tests/**/*.py` | Python test module | `[test]` | 0.85 |

### Prompt/AI Patterns
| Pattern | Intent | Tags | Confidence |
|---------|--------|------|------------|
| `**/prompts/**/*.md` | LLM prompt template | `[doc, ai, llm-prompt]` | 0.85 |
| `**/prompts/**/*.txt` | LLM prompt template | `[doc, ai, llm-prompt]` | 0.85 |

---

## Implementation Order

### Sprint 1: Core Infrastructure (Days 1-2) ✅ COMPLETE
1. [x] Add data structures to `meaning_inference.py`
   - `FilenameRule`, `PathPatternRule`, `ExtensionRule`, `InferenceRules`
2. [x] Implement `DEFAULT_INFERENCE_RULES` constant
   - 50+ filename rules (git, python, node, rust, docs, AI agents, CI/CD)
   - 15+ path pattern rules (workflows, tests, data ops, prompts)
   - 15+ extension rules (HPC, config, scripts, docs)
3. [x] Implement `infer_from_rules()` function
   - Priority: filename > path pattern > extension
   - Uses `PurePath.match()` for proper `**` glob support
4. [x] Modify `infer_file_metadata()` to use rules
   - Rule-based inference runs first
   - Content-based inference as fallback (when `fallback_to_content=True`)
   - Tags merged without duplicates
5. [x] Add tests for rule evaluation
   - 31 new tests covering all rule types and priorities
   - 186 total tests passing

### Sprint 2: Filename Rules (Days 2-3) ✅ COMPLETE (merged into Sprint 1)
1. [x] Add all filename rules from Phase 2
2. [ ] Test against real-world project (cmip6_workflow_hpc) — pending
3. [x] Verify confidence thresholds

### Sprint 3: Tag Vocabulary (Day 3) ✅ COMPLETE
1. [x] Update `python.yaml` schema
2. [x] Update `node.yaml` schema
3. [x] Update `rust.yaml` schema
4. [x] Update `docs.yaml` schema
5. [x] Update `mixed.yaml` schema
6. [x] Update `.meaning/schema.yaml` (dogfooding)

New tag categories added to all schemas:
- `vcs`: git, ignore, hooks
- `ai_context`: ai, agent-context, llm-prompt, agent-directive, context-doc
- `scientific_domain`: data-processing, ml, climate, geospatial, bioinformatics, visualization, statistics
- `infrastructure`: hpc, cloud, container, orchestration, ci-cd, deployment, build
- `data_ops`: etl, ingestion, aggregation, batch, sync, upload, download
- `compute`: slurm, pbs, spark, dask, parallel, distributed, job-array
- `packaging`: dependencies, packaging, dev

### Sprint 4: Extension & Pattern Rules (Days 4-5) ✅ COMPLETE (merged into Sprint 1)
1. [x] Add extension rules from Phase 4
2. [x] Add path pattern rules from Phase 5
3. [x] Implement glob pattern matching (using `PurePath.match()`)
4. [ ] Full integration testing — pending real-world validation

### Sprint 5: Config Override Support (Day 5) — DEFERRED
1. [ ] Add `inference_rules` section to config schema
2. [ ] Implement rule loading from config
3. [ ] Implement merge strategy (project overrides built-in)
4. [ ] Update config template

---

## Testing Strategy

### Unit Tests
```python
def test_filename_rule_exact_match():
    """Test exact filename matching."""
    
def test_filename_rule_case_sensitivity():
    """Test case-sensitive vs case-insensitive matching."""
    
def test_path_pattern_glob():
    """Test glob pattern matching."""
    
def test_extension_rule():
    """Test extension-based matching."""
    
def test_rule_priority():
    """Test that filename > pattern > extension."""
    
def test_fallback_to_content():
    """Test content analysis fallback."""
    
def test_config_override():
    """Test project rules override built-in."""
```

### Integration Tests
```python
def test_real_world_project():
    """Test against cmip6_workflow_hpc fixture."""
    # Expect: ≥60% auto-accept rate
    
def test_dogfooding():
    """Test against meaning project itself."""
    # All files should have appropriate tags
```

---

## Acceptance Criteria

### Inference
- [ ] Auto-accept rate ≥ 60% on standard projects
- [ ] Exact filename rules: confidence ≥ 0.95
- [ ] Agent context files auto-detected with confidence 1.0
- [ ] Zero false positives for exact filename matches
- [ ] `.gitignore` → `[config, vcs, ignore]` automatically

### Tag Vocabulary
- [ ] ≥ 80% files have appropriate domain tags (not `x-needs-tags`)
- [ ] < 10% files need `x-needs-tags` placeholder
- [ ] All new tag categories documented in schema
- [ ] HPC/scientific projects properly tagged

### Performance
- [ ] Rule evaluation < 1ms per file
- [ ] `/meaning-review` completes in < 2 seconds for 100 files
- [ ] No additional file I/O for rule-based inference

### Backward Compatibility
- [ ] Existing indexes continue to work
- [ ] Content-based inference still available
- [ ] No breaking changes to public API

---

## File Changes Summary

| File | Change Type | Description |
|------|-------------|-------------|
| `src/meaning/meaning_inference.py` | Major | Add rule-based inference |
| `src/meaning/meaning_core.py` | Minor | Load inference_rules from config |
| `src/meaning/templates/config.yaml` | Minor | Add inference_rules section |
| `src/meaning/templates/schema/python.yaml` | Minor | Add new tag categories |
| `src/meaning/templates/schema/node.yaml` | Minor | Add new tag categories |
| `src/meaning/templates/schema/rust.yaml` | Minor | Add new tag categories |
| `src/meaning/templates/schema/docs.yaml` | Minor | Add new tag categories |
| `src/meaning/templates/schema/mixed.yaml` | Minor | Add new tag categories |
| `.meaning/schema.yaml` | Minor | Add new tag categories (dogfooding) |
| `.meaning/config.yaml` | Minor | Add inference_rules section |
| `tests/test_inference.py` | Major | Add rule-based inference tests |
| `tests/fixtures/` | New | Add test fixtures for rule testing |

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| False positives | Low | High | Conservative confidence scores, extensive testing |
| Performance regression | Low | Medium | Rule evaluation is O(n) string matching, no I/O |
| Breaking existing indexes | Low | High | Rules only affect new/updated entries |
| Scope creep (too many rules) | Medium | Low | Start with common patterns, expand based on feedback |

---

## Success Metrics

**Before (v0.1):**
- Auto-accept rate: 0%
- Manual review time: ~15 minutes per project
- `x-needs-tags` usage: 53%

**After (v0.2):**
- Auto-accept rate: ≥60% (target: 75%)
- Manual review time: ~2 minutes per project
- `x-needs-tags` usage: <10%

---

## References

- [audit-external-repo-2026-01-23.md](./audit-external-repo-2026-01-23.md) — Original audit
- [IMPLEMENTATION-PLAN.md](../IMPLEMENTATION-PLAN.md) — Original project spec
- [meaning_inference.py](../src/meaning/meaning_inference.py) — Current inference engine

---

**Author:** AI Agent  
**Status:** Draft  
**Version:** 0.2.0-plan