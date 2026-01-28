# Session Summary: Dog-fooding + Inference Plan
**Date:** 2026-01-21  
**Focus:** Initialize `.meaning/` for the Meaning project itself

---

## Philosophy Check

```
Do not write code before stating assumptions.
Do not claim correctness you haven't verified.
Do not handle only the happy path.
Under what conditions does this work?
```

**Assumptions Stated:**
- We're dog-fooding on the Meaning project itself
- Using `python.yaml` schema (Python project)
- Manually documenting 5 initial files to feel the pain
- All file paths relative to project root
- Must validate after creation to verify correctness

**Conditions for success:**
- YAML must be syntactically valid
- Relationship types must exist in schema
- Tags must be in vocabulary or use custom prefix
- Intent descriptions ≤ 280 characters
- Referenced files must exist in index

---

## What Happened

### 1. Environment Setup OK
- Created virtual environment using `uv venv`
- Installed dependencies with `uv pip install -e ".[dev]"`
- All 54 core tests passing

### 2. Dog-fooding Initialization OK
- Created `.meaning/` directory in the Meaning repo itself
- Copied `schema.yaml` from `templates/schema/python.yaml`
- Copied `config.yaml` from `templates/config.yaml`
- Manually created `index.yaml` with 5 core files:
  - `README.md` - Project overview
  - `CLAUDE.md` - AI agent development guide
  - `IMPLEMENTATION-PLAN.md` - Technical specification
  - `CHANGELOG.md` - Project history
  - `src/meaning_core.py` - Core library implementation

### 3. Validation Discovery QUERY
Ran validation and discovered:
- **Tag vocabulary gap**: Used semantic tags (`overview`, `spec`, `dev-guide`, `history`, `ai`) that weren't in schema
- **Solution**: Added new `doc_type` vocabulary category to schema
- **Updated**: Both `.meaning/schema.yaml` and `templates/schema/python.yaml`

### 4. Final State OK
- Index validates successfully: `Valid: True, Errors: 0, Warnings: 13`
- 13 warnings are unindexed files (expected - only documented 5 files so far)
- No errors, no unknown tags, no stale entries

---

## Wins WIN

1. **Phase 1 Complete**: All 54 core tests passing, data structures solid
2. **Successful dog-fooding**: Created valid `.meaning/` for our own project
3. **Schema evolution**: Discovered need for `doc_type` tags organically through use
4. **Validation works**: Caught timestamp issues, unknown tags, verified correctness
5. **Manual process documented**: Now we know exactly what's tedious to automate

---

## Blockages & Pain Points IN PROGRESS

### Manual Pain Points (Inference Targets)

1. **Writing intents is slow**
   - Had to read each file to understand purpose
   - Intent must be concise (≤280 chars) but descriptive
   - **Inference opportunity**: Generate draft intents from file structure, imports, docstrings

2. **Identifying relationships is tedious**
   - Had to think: "Does CLAUDE.md document meaning_core.py? Yes."
   - Had to remember: "README documents both IMPLEMENTATION-PLAN and meaning_core.py"
   - **Inference opportunity**: Detect `documents` relationships from file references in markdown

3. **Picking tags requires vocabulary knowledge**
   - Initially used intuitive tags that weren't in schema
   - Had to check schema vocabulary repeatedly
   - **Inference opportunity**: Suggest tags based on:
     - File path patterns (`test_*.py` → `test`)
     - File extensions (`.md` → `doc`)
     - Common naming conventions

4. **Timestamps are manual**
   - Had to use `now()` function to get current time
   - Easy to forget or hardcode wrong dates
   - **Inference opportunity**: Auto-set `generated_at`, `last_updated`, `last_verified`

5. **Concepts require cross-file thinking**
   - Had to step back and think: "What are the semantic groupings?"
   - Named concepts (`project-documentation`, `core-library`)
   - Picked entry points manually
   - **Inference opportunity**: Suggest concepts from:
     - Directory structure
     - Import clusters
     - Related file groups

---

## Technical Blockers

**None encountered** - Core infrastructure works as designed.

---

## Next Steps: Inference Engine

Based on pain points, prioritize these inference features:

### High Priority
1. **Auto-generate timestamps** - Trivial, removes annoyance
2. **Detect `documents` relationships** - Parse markdown for file references
3. **Suggest tags from file paths** - Pattern matching on paths/names
4. **Draft intent descriptions** - Use first docstring/comment + file purpose

### Medium Priority
5. **Detect Python imports** - Parse `import`/`from` statements for `imports` relationships
6. **Suggest concepts** - Cluster files by directory + imports
7. **Validate relationship consistency** - Warn about missing bidirectional relationships

### Low Priority (Future)
8. **Detect test relationships** - Match `test_*.py` to `*.py`
9. **Detect inheritance** - Parse `class X(Y)` for `extends` relationships
10. **Suggest deprecation** - Find TODO/DEPRECATED comments

---

## Architecture Decisions Made

1. **Added `doc_type` vocabulary category** to Python schema
   - Contains: `overview`, `spec`, `dev-guide`, `history`, `ai`
   - Rationale: Documentation files need semantic classification beyond `doc` tag
   - Impact: More precise querying ("show me dev guides" vs "show me all docs")

2. **Manual creation first, then automate**
   - Validates the "feel the pain" philosophy
   - Now we have concrete pain points to solve
   - Avoids premature abstraction

---

## Validation Results

```
OK Valid: True
  Errors: 0
  Warnings: 13 (all unindexed files - expected)
```

**Files documented:** 5/22 project files  
**Concepts defined:** 2 (`project-documentation`, `core-library`)  
**Relationships captured:** 7 (all `documents` or `implements` types)

---

## Status Update

- **Phase 1: Core Data Structures** OK Complete (54/54 tests passing)
- **Phase 2: Inference Engine** IN PROGRESS Ready to start (pain points identified)
- **Phase 3: Skills** ⏸️ Blocked on inference
- **Phase 4: Hooks** ⏸️ Blocked on skills

**Current focus:** Build inference features to solve documented pain points

---

## Files Changed

- Created: `.meaning/index.yaml`
- Created: `.meaning/schema.yaml` (copied + modified)
- Created: `.meaning/config.yaml` (copied)
- Modified: `templates/schema/python.yaml` (added `doc_type` vocabulary)

---

## Lessons Learned

1. **Dog-fooding reveals real problems** - We immediately found schema gaps
2. **Validation is essential** - Caught 4 unknown tags before we noticed manually
3. **Good tags are worth expanding vocabulary** - Don't force users into bad semantics
4. **Manual work clarifies automation needs** - Now we know exactly what to build

---

## Open Questions for Next Session

1. Should inference be mandatory or optional during init?
2. How confident should inference be before auto-applying (vs suggesting)?
3. Should we build inference CLI first, or integrate into skills?
4. Do we need a "review mode" for bulk-accepting inferred relationships?

---

**Next Session Goal:** Implement top 4 inference features and re-run on this project to measure time savings.