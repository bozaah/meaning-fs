# 2026-01-22 - Markdown Intent Sanitization + Re-infer Cleanup

## Assumptions
- The meaning index should store clean, plain-text intents without markdown artifacts.
- Path-based intent inference should override markdown for agent sessions and audit notes.

## What Happened
- Fixed markdown intent sanitization and sentence extraction regex.
- Ensured docstring/markdown intents are cleaned of list markers, bold/italic, and inline code.
- Adjusted inference to prioritize path-based intents for `.agent-sessions/` and `audits/`.
- Re-inferred affected files to scrub existing markdown artifacts from `.meaning/index.yaml`.

## Wins
- Intents now read as plain text without `**`, backticks, or list markers.
- Review automation stays deterministic and yields cleaner metadata.

## Blockages
- Regex escaping initially broke intent inference; fixed and verified.

## Validation
- `python -m pytest tests/test_inference.py tests/test_core.py -v`
- `python -m meaning update --re-infer` followed by `python -m meaning validate`

## Next Steps
- Consider a dedicated `update --all --re-infer` option to avoid manual touch passes.
