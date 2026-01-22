# 2026-01-22 - Intent Inference Expansion + Interactive Review Diff

## Assumptions
- Heavier automation should prioritize deterministic heuristics over probabilistic guesses.
- Auto-accept needs high-confidence intent signals; markdown and known file/path patterns are safe sources.

## What Happened
- Increased markdown intent confidence to auto-accept first-paragraph summaries by default.
- Added path-based intent inference for common docs, templates, scripts, audits, and agent session notes.
- Enhanced interactive review to show diff-style previews of intent/tags/relationships and needs_review changes.
- Updated README/QUICKSTART guidance and changelog entry for these behaviors.

## Wins
- More docs and template files can be auto-accepted without manual intent edits.
- Review prompts now show clear additions/changes instead of just raw suggestions.

## Blockages
- None.

## Validation
- Added/updated inference tests for path-based intents and markdown confidence.
- (Run tests after code changes.)

## Next Steps
- Run full test suite and `meaning update/review` to confirm reduced `needs_review` count.
- Consider adding additional safe filename patterns if any still remain manual.
