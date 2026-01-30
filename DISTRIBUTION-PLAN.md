# Distribution Implementation Plan

## Goal

Enable frictionless adoption of meaning with a single command:

```bash
pip install meaning-fs && meaning init
```

After init, the target project is **self-contained**—hooks work without meaning being globally installed because they use inline Python with only stdlib + pyyaml.

---

## 1. Package Structure

```
meaning/
├── src/meaning/
│   ├── __init__.py           # Public API exports
│   ├── __main__.py           # CLI entry point
│   ├── meaning_core.py       # Core library
│   ├── meaning_inference.py  # Inference engine
│   ├── installer.py          # Installation logic OK
│   └── templates/
│       ├── schema/           # Project-type schemas
│       │   ├── python.yaml
│       │   ├── node.yaml
│       │   ├── rust.yaml
│       │   ├── docs.yaml
│       │   └── mixed.yaml    # Generic fallback
│       ├── config.yaml       # Default config
│       ├── hooks.json        # Claude hooks template
│       ├── scripts/          # Self-contained hook scripts
│       │   ├── meaning-post-write.sh
│       │   └── meaning-validate.sh
│       └── skills/           # Claude Code skills OK
│           ├── meaning-init/
│           ├── meaning-update/
│           ├── meaning-validate/
│           ├── meaning-query/
│           └── meaning-review/
```

---

## 2. What `meaning init` Does

### Command Options

```bash
meaning init [project_root]
    --type TYPE        # Force project type (python, node, rust, docs, mixed)
    --limit N          # Process first N files (default: 50)
    --skip-crawl       # Don't auto-index files
    --install-hooks    # Install Claude Code hooks
    --force-hooks      # Overwrite existing .claude/settings.json
    --with-skills      # Install Claude Code skills
```

### Step-by-step:

1. **Check preconditions**
   - Is this a git repo? (warn if not, continue)
   - Does `.meaning/` exist? (error: use `meaning update` instead)

2. **Detect project type**
   - Scan for markers: pyproject.toml, package.json, Cargo.toml, etc.
   - Default to "mixed" if unclear

3. **Create `.meaning/` structure**
   ```
   .meaning/
   ├── index.yaml          # Created empty
   ├── schema.yaml         # Copied from templates/{project_type}.yaml
   ├── config.yaml         # Copied from templates/config.yaml
   ├── hooks.json          # Copied from templates/hooks.json
   └── scripts/
       ├── meaning-post-write.sh
       └── meaning-validate.sh
   ```

4. **Setup Claude Code integration** (if requested)
   - `--install-hooks`: Create/merge `.claude/settings.json`
   - `--with-skills`: Copy skills to `.claude/skills/`

5. **Run initial crawl** (unless `--skip-crawl`)
   - Use inference engine to populate `index.yaml`
   - Mark low-confidence entries as `needs_review: true`

6. **Report summary**
   ```
   OK Created .meaning/ with 6 files
   OK Installed Claude Code hooks
   OK Installed 5 skills
   WARN  Not a git repository. Consider initializing git before meaning.
   OK Indexed 47 files
   WARN  Files needing review: 12
   OK Validation: True
   ```

---

## 3. Self-Containment Strategy

### Why no vendoring needed?

The hook scripts (`meaning-post-write.sh`, `meaning-validate.sh`) use **inline Python** with only:
- Standard library (`json`, `os`, `sys`, `datetime`, `fnmatch`)
- PyYAML (very common, often already installed)

They do NOT import from `meaning_core.py`. This means:
- OK Hooks work without meaning being pip-installed
- OK No version drift concerns
- OK No PYTHONPATH manipulation needed
- OK Simpler maintenance

### What the hooks actually do:

**Post-write hook:**
- Reads tool input JSON from stdin
- Extracts file path
- Updates index.yaml: marks file as `needs_review: true`
- All in ~150 lines of inline Python

**Validate hook:**
- Loads index.yaml
- Checks for basic issues (stale entries, etc.)
- Reports summary
- All in ~50 lines of inline Python

---

## 4. CLI Commands

### Post-init commands (work without pip install)

The hooks handle automatic tracking. For manual operations, the user can:
- Edit `.meaning/index.yaml` directly (it's human-readable YAML)
- Use Claude Code skills if installed

### Commands requiring pip install

```bash
meaning init                  # Initialize meaning in current project
meaning init --type python    # Force project type
meaning init --skip-crawl     # Don't auto-index files
meaning init --install-hooks  # Install Claude Code hooks
meaning init --with-skills    # Also install Claude skills

meaning update                # Sync index with filesystem changes
meaning update --new          # Only add new files
meaning update --modified     # Only update modified files
meaning update --re-infer     # Re-run inference on modified files

meaning review                # Review needs_review entries
meaning review --interactive  # Prompt for each file
meaning review --file PATH    # Review specific file

meaning validate              # Check index health
meaning query "api parsing"   # Find relevant files
meaning status                # Show project overview
meaning detect                # Show detected project type
```

---

## 5. Claude Code Integration

### Hooks (with `--install-hooks`)

Creates/merges `.claude/settings.json`:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.meaning/scripts/meaning-post-write.sh",
            "timeout": 5
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.meaning/scripts/meaning-validate.sh",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

### Skills (with `--with-skills`)

Copies skill definitions to `.claude/skills/`:

```
.claude/skills/
├── meaning-init/SKILL.md
├── meaning-update/SKILL.md
├── meaning-validate/SKILL.md
├── meaning-query/SKILL.md
└── meaning-review/SKILL.md
```

These allow Claude to run meaning operations conversationally:
```
User: "Which files handle authentication?"
Claude: [uses meaning-query skill]
```

---

## 6. PyPI Publication

### Package name

`meaning-fs` (since `meaning` is likely taken)

### pyproject.toml updates needed

```toml
[project]
name = "meaning-fs"
version = "0.2.0"
description = "Semantic File Index for AI Agents"
authors = [{name = "Your Name", email = "you@example.com"}]
readme = "README.md"
license = {text = "MIT"}
requires-python = ">=3.10"
keywords = ["ai", "semantic", "index", "agents", "llm", "claude"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
]

dependencies = ["pyyaml>=6.0"]

[project.scripts]
meaning = "meaning.meaning_core:main"

[project.urls]
Homepage = "https://github.com/bozaah/meaning-fs"
Documentation = "https://github.com/bozaah/meaning-fs#readme"
Repository = "https://github.com/bozaah/meaning-fs"

[tool.setuptools.package-data]
meaning = [
    "templates/**/*.yaml",
    "templates/**/*.json", 
    "templates/**/*.sh",
    "templates/**/*.md"
]
```

### Publishing workflow

```bash
# One-time setup
pip install build twine

# Build
python -m build

# Test on TestPyPI first
twine upload --repository testpypi dist/*
pip install --index-url https://test.pypi.org/simple/ meaning-fs

# Publish to PyPI
twine upload dist/*
```

---

## 7. Alternative Installation Methods

### uvx (recommended for try-before-install)

```bash
uvx meaning-fs init
```

Works because uvx creates a temporary venv, installs meaning-fs, runs it.

### pipx (for global CLI install)

```bash
pipx install meaning-fs
meaning init
```

### Direct from GitHub

```bash
pip install git+https://github.com/bozaah/meaning-fs.git
```

---

## 8. Implementation Status

### OK Completed

- [x] `installer.py` — File copying, hook installation, skills installation
- [x] Skills copied to `templates/skills/`
- [x] `mixed.yaml` schema for generic projects
- [x] CLI `init` command updated with `--with-skills`, `--skip-crawl`
- [x] Tests for installer (50 tests passing)
- [x] Empty `index.yaml` creation during install

### Remaining

- [ ] Update `pyproject.toml` with final package name and metadata
- [ ] Test `pip install -e .` in fresh venv
- [ ] Create GitHub release workflow
- [ ] Publish to TestPyPI
- [ ] Publish to PyPI
- [ ] Update README with installation instructions
- [ ] Test uvx/pipx workflows

---

## 9. Success Criteria

1. **Zero to working in one command**:
   ```bash
   pip install meaning-fs && meaning init
   ```

2. **Self-contained after init**: Hooks work without global install OK

3. **Claude Code integration works**: Hooks fire, skills available OK

4. **Multiple install paths**: pip, uvx, pipx all work

5. **Clean upgrade path**: `pip install --upgrade meaning-fs`

---

## 10. Testing Checklist

Before publishing:

```bash
# Fresh venv test
python -m venv /tmp/test-venv
source /tmp/test-venv/bin/activate
pip install -e .
cd /tmp && mkdir test-project && cd test-project
echo '{"name": "test"}' > package.json
meaning init --install-hooks --with-skills
cat .meaning/index.yaml
ls -la .claude/

# Verify hooks work (in Claude Code)
# 1. Open test-project in Claude Code
# 2. Create a file
# 3. Check that .meaning/index.yaml is updated

# Clean up
deactivate
rm -rf /tmp/test-venv /tmp/test-project
```
