# Session: Installer Module and Distribution Prep

**Date:** 2026-01-23
**Focus:** Creating installer module, simplifying distribution plan, preparing for PyPI

## Summary

Built a complete installer module (`installer.py`) that handles initialization of meaning in target projects. Discovered that vendoring `meaning_core.py` is unnecessary because hook scripts already use inline Python with only stdlib + pyyaml dependencies.

## Key Changes

### New Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `src/meaning/installer.py` | 512 | Complete installation logic |
| `src/meaning/templates/schema/mixed.yaml` | 137 | Generic schema for untyped projects |
| `src/meaning/templates/skills/` | — | Copied 5 skills from `.claude/skills/` |
| `tests/test_installer.py` | 515 | 50 comprehensive tests |

### Modified Files

- `src/meaning/__init__.py` — Added installer exports
- `src/meaning/meaning_core.py` — Updated init command to use installer
- `pyproject.toml` — Added `templates/**/*.md` to package-data
- `README.md` — Updated Quick Start section
- `QUICKSTART.md` — Added init flags documentation
- `CLAUDE.md` — Updated structure diagram
- `CHANGELOG.md` — Added entry for this work
- `DISTRIBUTION-PLAN.md` — Simplified (removed vendoring)

## Key Decisions

### No Vendoring Needed

The original distribution plan called for vendoring `meaning_core.py` into `.meaning/lib/` so hooks would work without pip install. Analysis of the actual hook scripts revealed:

- `meaning-post-write.sh` uses inline Python (~150 lines)
- Only dependencies: stdlib + pyyaml
- No imports from `meaning_core.py`

This means hooks are **already self-contained**. Eliminated:
- `.meaning/lib/` directory
- `meaning update --self` command
- PYTHONPATH manipulation in hooks
- Version drift concerns

### Installer Architecture

```python
install_meaning(project_root, options) -> InstallResult
├── Check preconditions (git warning, existing .meaning/)
├── Detect/validate project type
├── create_meaning_directory()
│   ├── Copy schema.yaml (by project type)
│   ├── Copy config.yaml
│   ├── Copy hooks.json
│   ├── Copy scripts/ (with +x permissions)
│   └── Create empty index.yaml
├── install_claude_hooks() (optional)
│   └── Create/merge .claude/settings.json
└── install_skills() (optional)
    └── Copy skills to .claude/skills/
```

### CLI Changes

New flags for `meaning init`:
- `--with-skills` — Install Claude Code skills
- `--skip-crawl` — Skip file scanning/inference
- `--install-hooks` — Install Claude hooks (existing)
- `--force-hooks` — Overwrite existing hooks (existing)

## Test Results

```
153 tests passed
├── 68 core tests
├── 35 inference tests
└── 50 installer tests
```

## Manual Testing

```bash
# Tested full workflow
cd /tmp && mkdir test-project && cd test-project
echo '{"name": "test"}' > package.json
meaning init --install-hooks --with-skills

# Output:
# ✓ Created .meaning/ with 6 files
# ✓ Installed Claude Code hooks
# ✓ Installed 5 skills
# ⚠️  Not a git repository...
# ✓ Indexed 4 files
```

## Remaining Work (Distribution)

From `DISTRIBUTION-PLAN.md`:

- [ ] Update `pyproject.toml` with final package name (`meaning-fs`)
- [ ] Test `pip install -e .` in fresh venv
- [ ] Create GitHub release workflow
- [ ] Publish to TestPyPI
- [ ] Publish to PyPI
- [ ] Test uvx/pipx workflows

## Files Structure After This Session

```
src/meaning/
├── __init__.py         # +installer exports
├── __main__.py
├── meaning_core.py     # +updated init command
├── meaning_inference.py
├── installer.py        # NEW
└── templates/
    ├── schema/
    │   ├── python.yaml
    │   ├── node.yaml
    │   ├── rust.yaml
    │   ├── docs.yaml
    │   └── mixed.yaml  # NEW
    ├── skills/         # NEW (copied from .claude/skills/)
    │   ├── meaning-init/
    │   ├── meaning-update/
    │   ├── meaning-validate/
    │   ├── meaning-query/
    │   └── meaning-review/
    ├── config.yaml
    ├── hooks.json
    └── scripts/
```

## Philosophy Notes

> "Do not write code before stating assumptions."

**Assumption stated:** Hook scripts need `meaning_core.py` to function.
**Assumption verified:** False. Hooks use inline Python.
**Result:** Simplified distribution plan significantly.

---

*Session duration: ~45 minutes*