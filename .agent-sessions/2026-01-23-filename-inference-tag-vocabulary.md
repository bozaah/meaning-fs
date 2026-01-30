# Session: Filename-Based Inference & Tag Vocabulary Enhancement

**Date:** 2026-01-23
**Agent:** Claude (Opus 4.5)
**Focus:** Implementing rule-based inference and expanding tag vocabulary based on real-world feedback

## Context

A colleague tested `meaning-fs` on an external HPC/climate science project (`cmip6_workflow_hpc`) and discovered critical usability gaps:
- **0% auto-accept rate** in `/meaning-review`
- **53% of files** tagged with placeholder `x-needs-tags`
- Common files like `.gitignore`, `requirements.txt` got no metadata
- AI agent context files (`GEMINI.md`, `WARP.md`) not recognized
- HPC-specific files (`.slurm`) not understood

The feedback was documented in `audits/audit-external-repo-2026-01-23.md`.

## Assumptions

1. Filename-based rules would provide high confidence (0.95-1.0) for well-known files
2. Path patterns with glob matching would handle common conventions (`**/test_*.py`)
3. Extension rules would serve as fallback for domain-specific files (`.slurm`, `.pbs`)
4. New tag categories would cover scientific computing, HPC, and AI agent domains
5. Built-in rules should work out-of-the-box without configuration

## What Was Implemented

### Phase 1: Core Infrastructure OK

Added to `meaning_inference.py`:

**Data Structures:**
- `FilenameRule` — Exact filename matching with intent, tags, confidence
- `PathPatternRule` — Glob pattern matching with `fallback_to_content` option
- `ExtensionRule` — File extension matching for domain-specific files
- `InferenceRules` — Collection container for all rule types

**Default Rules (80+ total):**
- 50+ filename rules (git, python, node, rust, docs, AI agents, CI/CD, system files)
- 15+ path pattern rules (GitHub workflows, test files, data ops, prompts)
- 15+ extension rules (HPC batch scripts, config files, scripts, docs)

**Core Function:**
- `infer_from_rules()` — Priority-based rule evaluation
  - Priority: filename > path pattern > extension
  - Uses `PurePath.match()` for proper `**` glob support
  - Returns (intent, tags, should_fallback_to_content)

**Integration:**
- Modified `infer_file_metadata()` to apply rules first, then content analysis
- Tags are merged without duplicates
- Content analysis only runs when `fallback_to_content=True` or no rule matched

### Phase 3: Tag Vocabulary OK

Added 7 new tag categories to all schema templates:

| Category | Tags |
|----------|------|
| `vcs` | git, ignore, hooks |
| `ai_context` | ai, agent-context, llm-prompt, agent-directive, context-doc |
| `scientific_domain` | data-processing, ml, climate, geospatial, bioinformatics, visualization, statistics |
| `infrastructure` | hpc, cloud, container, orchestration, ci-cd, deployment, build |
| `data_ops` | etl, ingestion, aggregation, batch, sync, upload, download |
| `compute` | slurm, pbs, spark, dask, parallel, distributed, job-array |
| `packaging` | dependencies, packaging, dev |

Updated files:
- `src/meaning/templates/schema/python.yaml`
- `src/meaning/templates/schema/node.yaml`
- `src/meaning/templates/schema/rust.yaml`
- `src/meaning/templates/schema/docs.yaml`
- `src/meaning/templates/schema/mixed.yaml`
- `.meaning/schema.yaml` (dogfooding)

## Test Results

**New Tests Added:** 31 tests for rule-based inference
- `TestInferenceRuleDataStructures` — 4 tests
- `TestGetDefaultRules` — 5 tests
- `TestInferFromRulesFilename` — 9 tests
- `TestInferFromRulesPathPattern` — 5 tests
- `TestInferFromRulesExtension` — 5 tests
- `TestInferFromRulesPriority` — 3 tests
- `TestInferFromRulesCustomRules` — 2 tests

**Total:** 186 tests passing

## Files Changed

| File | Lines | Change |
|------|-------|--------|
| `src/meaning/meaning_inference.py` | +340 | Rule data structures, default rules, `infer_from_rules()` |
| `src/meaning/__init__.py` | +12 | Export new types and functions |
| `tests/test_inference.py` | +340 | 31 new tests |
| `src/meaning/templates/schema/*.yaml` | +60 each | New tag categories |
| `.meaning/schema.yaml` | +60 | Dogfooding updates |
| `.meaning/index.yaml` | +26 | Added audit files |
| `audits/IMPLEMENTATION-PLAN-v0.2.md` | +570 | Full implementation plan |

## Wins

1. **Clean architecture** — Rules are data-driven, not hardcoded logic
2. **Extensible** — Easy to add new rules without code changes
3. **Testable** — Each rule type has comprehensive test coverage
4. **Backward compatible** — Existing content-based inference still works
5. **Fast** — No file I/O for rule-based inference, just string matching

## Key Design Decisions

1. **Built-in rules over config-only** — Works out-of-the-box, config overrides deferred
2. **PurePath.match() over fnmatch** — Proper support for `**` glob patterns
3. **Priority-based evaluation** — Filename > pattern > extension ensures specificity
4. **fallback_to_content flag** — Low-confidence rules can still benefit from content analysis
5. **Separate tag categories** — Domain-specific vocabularies don't pollute generic tags

## What Was Deferred

- **Config-based rule overrides** — Sprint 5 deferred to future release
- **Real-world validation** — Need to test against `cmip6_workflow_hpc` project

## Expected Impact

Based on the audit analysis:

| Metric | Before | After (Expected) |
|--------|--------|------------------|
| Auto-accept rate | 0% | ≥60% |
| Manual review time | ~15 min | ~2 min |
| `x-needs-tags` usage | 53% | <10% |

## Next Steps

1. **Test on external project** — Validate against `cmip6_workflow_hpc`
2. **Config override support** — Allow project-specific rules in `config.yaml`
3. **Additional rules** — Add rules based on real-world feedback
4. **Performance benchmarking** — Verify <1ms per file rule evaluation

## Validation

```bash
# All tests pass
python -m pytest tests/ -q
# 186 passed in 0.10s

# All linting passes
python -m ruff check src/ tests/
# All checks passed!

# Type checking passes
python -m mypy src/meaning/ --ignore-missing-imports
# Success: no issues found in 5 source files

# Index validation passes
./scripts/validate-meaning.sh
# OK Index is valid!
```

## Status

**Phases 1, 3, 4 Complete** — Rule-based inference and tag vocabulary implemented
**Phase 5 Deferred** — Config override support for future release
**Ready for:** Real-world validation testing

---

*Session documented following Meaning project philosophy: assumptions stated, work verified, next steps clear.*