# 2026-01-22 - Review Reporting Fix + Fixture Smoke Tests

## Assumptions
- It's acceptable to keep a persistent CLI fixture at `/tmp/meaning-test-I7e97f`.
- `meaning review` should only report files as reviewed when high-confidence inference actually changes entries.
- Intent inference sources are limited to module docstrings and markdown first paragraphs.

## What Happened
- Investigated why `meaning review` reported files as reviewed without intent changes.
- Updated review workflow to count only real changes and report remaining `needs_review` files.
- Added inference change preview helper and tests for apply/preview behavior.
- Ran fixture smoke tests using `/tmp/meaning-test-I7e97f` and a temporary `/tmp/meaning-test-RrFH4f` project.
- Documented review behavior and fixture details in `CLAUDE.md`, `README.md`, and `QUICKSTART.md`.
- Added changelog entry for review reporting improvements and tests.

## Wins
- Review output now reflects actual changes; no more false "Reviewed" counts.
- Tests cover inference application and preview behavior.
- Smoke tests confirmed threshold-based intent inference and review messaging.

## Blockages
- None.

## Validation
- `python -m pytest tests/test_core.py -v`
- CLI smoke tests:
  - `meaning update --re-infer --threshold 0.7` cleared review flags after docstrings/paragraphs
  - `meaning review` reported remaining `needs_review` accurately

## Next Steps
- Keep `/tmp/meaning-test-I7e97f` for future CLI smoke testing.
- Consider adding a dedicated fixture under `tests/fixtures/` if we want a repo-tracked smoke project.
