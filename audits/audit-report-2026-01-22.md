# Audit Report - 2026-01-22

## Assumptions
- Audited the current working tree as-is; did not attempt a clean checkout or installation in a fresh environment.
- “Use in another directory” is interpreted as installing the package and/or running its CLI/scripts against a different project root.
- Claude Code skills are evaluated as written (static review) and were not executed end-to-end.

## Scope
- In scope:
  - Package CLI entry points and module layout
  - Initialization/templating logic for new projects
  - Scripted utilities and hook scripts
  - Skill documentation references needed to operate in other directories
  - CLI status/query output (as a “view of the project”)
- Out of scope:
  - Inference accuracy and heuristics
  - Performance benchmarking
  - Security of external dependencies (no third-party audit)

## Verification Status
- Commands run:
  - `python -m meaning status`
  - `python -m meaning query "what needs review?"`
  - `./scripts/validate-meaning.sh` (failed with ModuleNotFoundError)
- Static review of repo files only; no packaged install or external project initialization executed.

## Findings
### Critical
- None found.

### High
- **Installed CLI entry point points at a non-existent module** (Area: Bug)
  - Evidence: `pyproject.toml:39` declares `meaning = "meaning_core:main"`, but the module is `meaning.meaning_core` under `src/meaning/`.
  - Impact: `meaning` console script will fail when installed in another environment, blocking CLI usage in other directories.
  - Conditions/Works when: Works only if a top-level `meaning_core` module exists on `PYTHONPATH` (it doesn’t in this repo or installed package).
  - Non-happy-path cases: Fresh `pip install meaning` then running `meaning status` will raise `ModuleNotFoundError`.
  - Verification status: Static review only.
  - Recommendation: Change entry point to `meaning.meaning_core:main` and add a smoke test that runs the installed CLI.

- **Initialization uses a template path that doesn’t exist in-package** (Area: Bug)
  - Evidence: `src/meaning/meaning_core.py:781-787` sets `template_dir = Path(__file__).parent.parent / "templates"` and reads `templates/schema/<type>.yaml`.
  - Impact: `initialize_meaning()` fails to find templates in a packaged install (and even in this repo, because `templates/` is not under `src/`). This blocks initializing a new project in another directory.
  - Conditions/Works when: Works only if callers pass a valid `template_dir` explicitly or if templates are relocated/packaged under `src/templates`.
  - Non-happy-path cases: Calling `initialize_meaning()` without `template_dir` in another project raises `ValueError` for missing schema files.
  - Verification status: Static review only.
  - Recommendation: Package templates as package data and update `template_dir` discovery (e.g., `importlib.resources`).

### Medium
- **CLI output and docs reference commands that are not implemented** (Area: Bug / UX)
  - Evidence: `src/meaning/meaning_core.py:1136-1143` and `src/meaning/meaning_core.py:1182-1184` advertise `python -m meaning review/update/init`, but `main()` only supports `status|query|validate|detect` (`src/meaning/meaning_core.py:1147-1215`).
  - Impact: Users in another directory are told to run commands that do not exist, blocking initialization/review flows without Claude Code skills.
  - Conditions/Works when: Works only if users rely on Claude Code skills (and those skills are installed in the target project).
  - Non-happy-path cases: Running `python -m meaning init` yields “Unknown command” even though docs/CLI suggest it.
  - Verification status: Static review only.
  - Recommendation: Implement `init/update/review` CLI subcommands or remove the guidance until they exist.

- **Project scripts import non-existent top-level modules** (Area: Bug)
  - Evidence: `scripts/validate-meaning.sh:16-18` imports `meaning_core`; `scripts/run-inference.py:16-17` imports `meaning_core` and `meaning_inference`.
  - Impact: Scripts fail when run from repo root or another directory unless a top-level module is manually provided.
  - Conditions/Works when: Works only if `meaning_core.py` and `meaning_inference.py` are importable as top-level modules (they aren’t).
  - Non-happy-path cases: `./scripts/validate-meaning.sh` fails with `ModuleNotFoundError` (observed).
  - Verification status: Command execution + static review.
  - Recommendation: Update imports to `meaning.meaning_core` / `meaning.meaning_inference` and/or set `PYTHONPATH` appropriately.

- **Skills/documentation reference the wrong module/CLI name** (Area: Bug / UX)
  - Evidence: README and QUICKSTART use `python -m meaning_core` (`README.md:69-78`, `QUICKSTART.md:31-33, 113-116, 147-153`); skills reference `from meaning_core import ...` (`.claude/skills/meaning-init/SKILL.md:29-50`, `.claude/skills/meaning-update/SKILL.md:28-49`, `.claude/skills/meaning-validate/SKILL.md:31-63`).
  - Impact: Following docs or skill snippets in another project leads to import failures. Also conflicts with `.claude/settings.json` permissions (only allow `python -m meaning`).
  - Conditions/Works when: Works only if a top-level `meaning_core` module exists or if users manually adjust import paths.
  - Non-happy-path cases: `python -m meaning_core status` fails; skill snippets error when run as-is.
  - Verification status: Static review only.
  - Recommendation: Standardize on `meaning` module name and update all docs/skills accordingly.

- **Hook installation is not wired for external projects** (Area: UX / Functional gap)
  - Evidence: Templates provide `templates/hooks.json` with `.meaning/scripts/...` paths, but `initialize_meaning()` only copies schema/config (`src/meaning/meaning_core.py:790-800`). Skills also omit copying hook scripts.
  - Impact: In another directory, automatic tracking hooks will not be installed unless users manually copy scripts and hook config.
  - Conditions/Works when: Works only if users manually install scripts into `.meaning/scripts` and wire hooks.
  - Non-happy-path cases: No automatic `needs_review` updates after file edits in new projects.
  - Verification status: Static review only.
  - Recommendation: Add a scripted install step (CLI or skill) that copies hook scripts + hook config into the target project.

### Low
- None found.

## UI/UX Opportunities
- Clarify the “single source of truth” CLI name (`meaning` vs `meaning_core`) and ensure all docs, skill snippets, and CLI help align.
- Consider adding `meaning --help` with subcommand descriptions and examples, plus a short “setup for new projects” path.

## Unverified / Needs Follow-up
- Validate a clean `pip install .` and `meaning status` in a separate temp directory.
- Run `/meaning-init` skill in a new project to confirm template/copy behavior.
- Confirm whether templates are intended to be packaged as data files for distribution.

## Next Steps
- Fix entry point/module name mismatches and update scripts/docs/skills to use `meaning.meaning_core` and `python -m meaning` consistently.
- Package templates and add a CLI/skill installer that provisions `.meaning/` plus hook scripts in external projects.
- Add a minimal smoke test (install + `meaning status`) to prevent regressions.
