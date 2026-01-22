# 2026-01-22 - Temp Dir CLI Smoke Test

## Assumptions
- Using a temporary directory under `/tmp` is acceptable for a quick CLI smoke test.
- Minimal files (`README.md`, `src/app.py`) are enough to exercise `init/status/validate`.

## What Happened
- Created `/tmp/meaning-test-I7e97f` with a tiny Python-like structure.
- Ran `python -m meaning init /tmp/meaning-test-I7e97f --type python`.
- Ran `python -m meaning status /tmp/meaning-test-I7e97f`.
- Ran `python -m meaning validate /tmp/meaning-test-I7e97f`.
- Ran `python -m meaning review /tmp/meaning-test-I7e97f` and manually updated intents in the temp index.

## Wins
- Init/status/validate all ran without errors.
- Validation warnings correctly flagged missing intents for both files.

## Blockages
- None.

## Validation
- CLI outputs showed init success, 2 files indexed, 2 needing review, and validation passed with warnings.
- After intent updates, validation passed with no warnings.

## Next Steps
- Optionally run `python -m meaning review /tmp/meaning-test-I7e97f` to fill intents.
- Remove the temp directory when no longer needed.
