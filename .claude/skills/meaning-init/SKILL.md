---
name: meaning-init
description: Bootstrap .meaning/ directory for a project
argument-hint: "[--type python|node|rust|docs]"
user-invocable: true
allowed-tools: Read, Write, Bash, Glob, Grep
---

# Initialize Meaning Semantic Index

Bootstrap the `.meaning/` directory for a project with semantic file indexing.

## Workflow

1. **Detect project type** (if not specified via argument)
   - Check for `pyproject.toml`, `setup.py` → python
   - Check for `package.json` → node
   - Check for `Cargo.toml` → rust
   - Check for `mkdocs.yml`, `docusaurus.config.js` → docs

2. **Create directory structure**
   ```
   .meaning/
   ├── index.yaml
   ├── schema.yaml
   ├── config.yaml
   └── scripts/
       ├── meaning-post-write.sh
       └── meaning-validate.sh
   ```

3. **Copy appropriate schema template** based on detected/specified project type

4. **Generate initial index.yaml**
   - Scan project files (respecting config exclusions)
   - Generate placeholder entries with `needs_review: true`
   - Infer basic relationships from imports

5. **Configure Claude Code hooks** (optional)
   - Add hook configuration to project's `.claude/settings.json`

## Arguments

| Argument | Description |
|----------|-------------|
| `--type TYPE` | Project type: python, node, rust, docs |
| `--path PATH` | Target directory (default: current) |
| `--no-hooks` | Skip Claude Code hook configuration |
| `--dry-run` | Show what would be created without writing |

## Output

- Creates `.meaning/` directory with all necessary files
- Reports count of files indexed
- Lists files excluded by config
- Notes any detection ambiguities
