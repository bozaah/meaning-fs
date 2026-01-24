# Refactor Plan: Modularize meaning_core and CLI

**Date:** 2026-01-24  
**Author:** Codex (GPT-5)  
**Status:** Proposed

## Assumptions

1. Public API stability matters (`from meaning import ...` should keep working).
2. CLI behavior and output should remain deterministic and backward compatible.
3. Tests are the primary safety net; we will update them only where necessary.
4. The refactor should not change the on-disk `.meaning/` format.

## Goals

- Reduce the size and responsibility load of `meaning_core.py`.
- Separate CLI parsing from library logic.
- Make inference, query, validation, and IO easier to reason about and test.
- Preserve the existing public API and CLI entry points.

## Non-Goals

- No change to index schema or file formats.
- No behavior changes unless explicitly documented.
- No external dependencies added.

## Proposed Module Split

**1) `meaning/cli.py`**  
Owns `argparse` setup and command routing. Calls into library modules.

**2) `meaning/index_io.py`**  
`load_index`, `save_index`, `load_schema`, `save_schema`, `load_config`, `save_config`, `load_yaml`, `save_yaml`.

**3) `meaning/validation.py`**  
`validate_index`, `ValidationResult`.

**4) `meaning/query.py`**  
`query_index`, `QueryResult`, `display_query_results`.

**5) `meaning/project.py`**  
`detect_project_type`, `is_git_repo`, file scanning utilities.

**6) `meaning/models.py`**  
Core dataclasses: `FileEntry`, `Concept`, `MeaningIndex`, `Relationship`, `MeaningSchema`, `MeaningConfig`, `RelationshipType`.

**7) `meaning/index_ops.py`**  
`find_unindexed_files`, `find_deleted_files`, `find_modified_files`, `prune_excluded_entries`, `create_skeleton_entry`.

`meaning_inference.py` remains its own module but can later be split into `inference/rules.py`, `inference/intent.py`, etc.

## Compatibility Strategy

- Keep `meaning_core.py` as a thin facade that re-exports and delegates to the new modules.
- Update `meaning/__init__.py` to import from the new modules (preserving names).
- Keep `meaning.__main__` pointing to the CLI entry point.

## Migration Steps (Incremental)

1. **Move CLI**: Create `meaning/cli.py`, move `main()` and CLI parsing there.  
   - Keep `meaning_core.main()` as a wrapper calling `cli.main()`.
2. **Extract IO**: Move YAML read/write + index/config/schema load/save to `index_io.py`.  
3. **Extract Validation**: Move validation logic to `validation.py`.  
4. **Extract Query**: Move query functions + renderers to `query.py`.  
5. **Extract Models**: Move dataclasses to `models.py`.  
6. **Extract Index Ops**: Move file scanning + indexing helpers to `index_ops.py`.  
7. **Update Imports**: Adjust internal imports and tests.  
8. **Audit for Cycles**: Ensure no circular imports (especially `models` vs `query`/`validation`).  
9. **Update Docs**: Note module structure in README/CLAUDE.

## Risks / Edge Cases

- Circular imports if models and helpers are not layered correctly.
- CLI output diffs if formatting is changed unintentionally.
- External users importing from `meaning.meaning_core` directly (mitigated by facade).

## Validation Plan

- Run `python -m pytest tests/ -v`.
- Run `python -m meaning status`, `query`, `init`, `update`, `review`, `validate` against `/tmp/meaning-test-I7e97f`.
- Confirm `meaning` console script still works.

## Next Steps

1. Agree on module split and naming.
2. Implement Step 1 (CLI extraction) as a low-risk starting point.
3. Proceed in order with tests after each step.
