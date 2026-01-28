Filename-Based Inference + Domain-Specific Tag Vocabularies

## Summary
Real-world testing revealed two critical gaps in `meaning-fs`:
1. **No filename-based inference** → Common files like `.gitignore`, `requirements.txt` get no metadata
2. **Generic tag vocabulary** → Missing domain-specific tags for HPC, AI agents, data science, etc.

Result: **0% auto-accept rate** in `/meaning-review`, defeating the purpose of automated indexing.

## Problem 1: Missing Filename Inference

**Current Behavior:**
- Only content analysis works (reading file contents)
- Common config/utility files get placeholder: `[NEEDS REVIEW] .gitignore`
- Agent context files (GEMINI.md, WARP.md) not recognized
- Auto-accept rate: **0%** even with lowered threshold

**Test Results:**
```
OK Loaded 34 files
QUERY 20 files need review (59%)

SUMMARY Categorizing...
   • 0 high-confidence (auto-accept)
   • 20 need manual review
```

| File | Current | Expected |
|------|---------|----------|
| `.gitignore` | `[NEEDS REVIEW]` | "Git ignore patterns" (conf: 1.0) |
| `requirements.txt` | `[NEEDS REVIEW]` | "Python dependencies" (conf: 1.0) |
| `GEMINI.md` | Intent from content | "Gemini agent context" (conf: 1.0) |
| `*.slurm` | `[NEEDS REVIEW]` | "SLURM job script" (conf: 0.95) |

## Problem 2: Limited Tag Vocabulary

**Current Tag Usage:**
```
x-needs-tags: 18  ← 53% of files have placeholder tag!
doc: 13
module: 4
config: 1
```

**Schema has 50+ tags but only 6 are used** because:
- Vocabulary is web-app focused (`api`, `auth`, `middleware`)
- Missing scientific computing tags (`hpc`, `slurm`, `data-processing`)
- Missing AI/agent tags (`agent-context`, `llm-prompt`)
- Missing data ops tags (`upload`, `sync`, `etl`)

---

## Solution Part 1: Filename-Based Inference Rules

Add `inference_rules` to config:

```yaml
version: "0.1"

inference_rules:
  # Exact filename matches (highest confidence)
  exact_filenames:
    # Git/VCS
    - filename: ".gitignore"
      intent: "Git version control ignore patterns"
      tags: [config, vcs, ignore]
      confidence: 1.0

    # Python dependencies
    - filename: "requirements.txt"
      intent: "Python package dependencies (pip)"
      tags: [config, dependencies]
      confidence: 1.0

    # Agent context files (NEW!)
    - filename: "GEMINI.md"
      intent: "Google Gemini agent project context and directives"
      tags: [doc, ai, agent-context]
      confidence: 1.0

    - filename: "WARP.md"
      intent: "AI agent project context and overview"
      tags: [doc, ai, agent-context]
      confidence: 1.0

    - filename: "CLAUDE.md"
      intent: "Claude AI agent project context and directives"
      tags: [doc, ai, agent-context]
      confidence: 1.0

    # System files
    - filename: ".DS_Store"
      intent: "macOS Finder metadata (should be git-ignored)"
      tags: [system, generated]
      confidence: 1.0

  # Path patterns
  path_patterns:
    - pattern: "**/upload_*.sh"
      intent: "Data upload script"
      tags: [script, upload, deployment]
      confidence: 0.85

    - pattern: "**/compute_*.py"
      intent: "Computational data processing module"
      tags: [module, script, data-processing]
      confidence: 0.8
      fallback_to_content: true

  # Extension rules (fallback)
  extension_rules:
    - extension: ".slurm"
      intent: "SLURM batch job submission script"
      tags: [script, hpc, slurm, batch]
      confidence: 0.95

    - extension: ".md"
      intent: "Markdown documentation"
      tags: [doc]
      confidence: 0.6
      fallback_to_content: true
```

### Inference Priority
1. Exact filename (conf: 0.95-1.0)
2. Path pattern (conf: 0.8-0.95)
3. Content analysis (conf: varies) ← current
4. Extension (conf: 0.5-0.85, fallback)

---

## Solution Part 2: Enhanced Tag Vocabulary

Add domain-specific categories to `schema.yaml`:

```yaml
tag_vocabulary:
  # Existing (keep all)
  domain: [api, auth, database, ui, cli, config, utils, ...]
  concern: [parsing, validation, error-handling, ...]
  layer: [controller, service, repository, ...]
  doc_type: [overview, spec, dev-guide, history, ai]
  file_type: [module, package, script, test, config, ...]

  # NEW: Scientific/Data domains
  scientific_domain:
    - data-processing    # Data transformation/analysis
    - ml                 # Machine learning
    - ai                 # AI/LLM-related
    - climate            # Climate science
    - geospatial         # GIS/spatial data
    - bioinformatics
    - visualization
    - statistics

  # NEW: Infrastructure
  infrastructure:
    - hpc                # High-performance computing
    - cloud              # AWS, Azure, GCP
    - container          # Docker, Kubernetes
    - orchestration      # Workflow orchestration
    - ci-cd
    - deployment

  # NEW: Data operations
  data_ops:
    - etl
    - ingestion
    - aggregation
    - batch
    - sync
    - upload
    - download

  # NEW: Compute platforms
  compute:
    - slurm              # SLURM workload manager
    - pbs                # PBS/Torque
    - spark
    - dask
    - parallel
    - distributed
    - job-array

  # NEW: AI/Agent context
  ai_context:
    - agent-context      # AI agent project context files
    - llm-prompt         # LLM prompt templates
    - agent-directive    # Agent instructions
    - context-doc        # Context documentation for AI

  # NEW: Version control
  vcs:
    - git
    - ignore             # Ignore patterns
    - hooks              # Git hooks
```

---

## Expected Impact

### Before
```
Auto-accept rate: 0% (0/20)
Manual review: ~15 minutes
Tag coverage: 41% (14/34)
Most common tag: x-needs-tags (53%)
```

### After
```
Auto-accept rate: 75%+ (15-17/20)
Manual review: ~2 minutes
Tag coverage: 85%+ (29-31/34)
Proper domain tags applied automatically

Auto-accepted files:
  OK .gitignore → [config, vcs, ignore]
  OK requirements.txt → [config, dependencies]
  OK GEMINI.md → [doc, ai, agent-context]
  OK WARP.md → [doc, ai, agent-context]
  OK 10 × *.slurm → [script, hpc, slurm, batch]
  OK upload_*.sh → [script, upload, deployment]
  OK compute_*.py → [module, data-processing]
```

**Metrics:**
- Auto-accept: 0% → **75%+**
- Review time: 15 min → **2 min**
- Tag coverage: 41% → **85%+**

---

## Implementation Checklist

### Phase 1: Core Infrastructure (P0)
- [ ] Define `inference_rules` schema structure
- [ ] Implement filename/path/extension pattern matching
- [ ] Implement priority-based rule evaluation
- [ ] Result merging with `fallback_to_content`

### Phase 2: Common Patterns (P0)
**Filename rules:**
- [ ] Git: `.gitignore`, `.gitattributes`
- [ ] Python: `requirements.txt`, `setup.py`, `pyproject.toml`
- [ ] Node: `package.json`, `package-lock.json`
- [ ] System: `.DS_Store`, `Thumbs.db`
- [ ] Docs: `README.md`, `LICENSE`, `CHANGELOG.md`
- [ ] Agent context: `GEMINI.md`, `WARP.md`, `CLAUDE.md`, `AGENTS.md`

### Phase 3: Enhanced Tag Vocabulary (P0)
- [ ] Add `ai_context` category
- [ ] Add `infrastructure` category (with `hpc`, `slurm`)
- [ ] Add `data_ops` category
- [ ] Add `compute` category
- [ ] Add `scientific_domain` category
- [ ] Add `vcs` category

### Phase 4: Domain-Specific Rules (P1)
**HPC/Scientific:**
- [ ] `.slurm`, `.pbs`, `.sge` extensions
- [ ] `compute_*.py`, `process_*.py` patterns
- [ ] `upload_*.sh`, `sync_*.sh` patterns
- [ ] `snakefile`, `nextflow.config`

**AI/Agent:**
- [ ] Content pattern: "# .* Agent Context"
- [ ] Path pattern: `**/prompts/**/*.md`
- [ ] `.cursorrules`, `.aider*` files

### Phase 5: Extended Domains (P2)
- [ ] Web dev tags: `react`, `vue`, `frontend`, `backend`
- [ ] DevOps tags: `terraform`, `ansible`, `kubernetes`
- [ ] Mobile tags: `android`, `ios`, `flutter`
- [ ] Data science tags: `jupyter`, `notebook`, `experiment`

---

## Acceptance Criteria

**Inference:**
- [ ] Auto-accept rate ≥ 60% on standard projects
- [ ] Exact filename rules: confidence ≥ 0.95
- [ ] Agent context files auto-detected
- [ ] Zero false positives

**Tag Vocabulary:**
- [ ] ≥ 80% files have appropriate domain tags
- [ ] < 10% files need `x-needs-tags`
- [ ] Schema documented with examples per category
- [ ] HPC/scientific projects properly tagged

**Performance:**
- [ ] `/meaning-review` completes in < 2 seconds for 100 files

---

## Real-World Test Case

**Project:** `cmip6_workflow_hpc` (Python HPC/climate science)
- 34 files indexed
- **Current:** 0% auto-accept, 59% need review
- **Expected:** 75%+ auto-accept, 15% need review

**File breakdown:**
- 10 SLURM scripts → `[script, hpc, slurm, batch]`
- 4 shell scripts → `[script, upload/sync, deployment]`
- 2 agent context → `[doc, ai, agent-context]`
- 4 Python modules → `[module, data-processing]` + content
- 2 config files → `[config, dependencies/vcs]`
- 8 docs → `[doc, ...]`

---

## Additional Context

### Why This Matters

1. **Developer Experience:** Automated indexing should work out-of-the-box
2. **AI Agents:** Need to discover project context files automatically
3. **Domain Diversity:** Not all projects are web apps
4. **Real-World Usage:** First external test revealed these gaps

### Alternative Approaches Considered

ERROR **Hardcode in Python:** Not user-customizable
ERROR **AI-only inference:** Slow, expensive, unpredictable
OK **Default rules + overrides:** Fast, deterministic, customizable

### Migration Strategy

**Backward compatible:**
- New projects get rules by default
- Existing projects inherit built-in rules
- Can override with `.meaning/inference_rules.yaml`

---

## Related Files

Full technical analysis available:
- `meaning-fs-diagnosis-and-proposal.md` - Detailed inference design
- `meaning-fs-tag-vocabulary-enhancement.md` - Complete tag vocabulary proposal
- `meaning-fs-issue-report.md` - Original issue discovery

---

**Testing Date:** 2026-01-23
**Package:** `meaning-fs` (external release)
**First Real-World Test:** OK
**Priority:** P0 (Critical for usability)
**Labels:** enhancement, inference, dx, vocabulary
**Milestone:** v0.2
