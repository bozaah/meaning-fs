"""
Meaning Installer

Handles installation of meaning into target projects:
- Creates .meaning/ directory with templates
- Installs Claude Code hooks
- Optionally installs skills for Claude Code users

This module focuses on file copying and setup logic,
separate from the core semantic index functionality.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

# =============================================================================
# Constants
# =============================================================================

MEANING_DIR = ".meaning"
CLAUDE_DIR = ".claude"
SETTINGS_JSON = "settings.json"
SKILLS_DIR = "skills"
INDEX_FILENAME = "index.yaml"
VERSION = "0.1"

# Files to copy to .meaning/
MEANING_FILES = [
    "config.yaml",
    "hooks.json",
]

MEANING_SCRIPTS = [
    "scripts/meaning-post-write.sh",
    "scripts/meaning-validate.sh",
]

# Skill directories to copy (each contains SKILL.md)
SKILL_NAMES = [
    "meaning-init",
    "meaning-update",
    "meaning-validate",
    "meaning-query",
    "meaning-review",
]


# =============================================================================
# Data Classes
# =============================================================================


class ConflictResolution(Enum):
    """How to handle existing files/directories."""

    ABORT = "abort"
    OVERWRITE = "overwrite"
    MERGE = "merge"
    SKIP = "skip"


@dataclass
class InstallOptions:
    """Options for meaning installation."""

    project_type: str | None = None  # None = auto-detect
    install_hooks: bool = True
    install_skills: bool = False
    force_hooks: bool = False  # Overwrite existing .claude/settings.json
    conflict_resolution: ConflictResolution = ConflictResolution.ABORT
    dry_run: bool = False


@dataclass
class InstallResult:
    """Result of an installation attempt."""

    success: bool
    meaning_dir_created: bool = False
    files_copied: list[str] = field(default_factory=list)
    hooks_installed: bool = False
    skills_installed: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)
        self.success = False


# =============================================================================
# Template Resolution
# =============================================================================


def get_package_template_dir() -> Path:
    """Get the templates directory from the installed package."""
    # Templates are in the same package, under templates/
    package_dir = Path(__file__).parent
    template_dir = package_dir / "templates"

    if not template_dir.exists():
        raise FileNotFoundError(f"Templates directory not found: {template_dir}")

    return template_dir


def get_schema_path(template_dir: Path, project_type: str) -> Path:
    """Get path to schema template for a project type."""
    schema_path = template_dir / "schema" / f"{project_type}.yaml"
    if not schema_path.exists():
        available = [f.stem for f in (template_dir / "schema").glob("*.yaml")]
        raise ValueError(f"Unknown project type: {project_type}. Available: {', '.join(available)}")
    return schema_path


# =============================================================================
# Project Detection
# =============================================================================


def detect_project_type(project_root: Path) -> str:
    """
    Detect project type based on marker files.

    Returns: python, node, rust, docs, or mixed
    """
    markers = {
        "python": ["pyproject.toml", "setup.py", "requirements.txt", "Pipfile"],
        "node": ["package.json", "tsconfig.json"],
        "rust": ["Cargo.toml"],
        "docs": ["mkdocs.yml", "docusaurus.config.js", "_config.yml"],
    }

    detected = []
    for project_type, files in markers.items():
        for marker in files:
            if (project_root / marker).exists():
                detected.append(project_type)
                break

    if len(detected) == 0:
        return "mixed"
    elif len(detected) == 1:
        return detected[0]
    else:
        # Multiple types detected, prioritize
        priority = ["python", "node", "rust", "docs"]
        for ptype in priority:
            if ptype in detected:
                return ptype
        return "mixed"


def is_git_repo(project_root: Path) -> bool:
    """Check if the project is a git repository."""
    return (project_root / ".git").is_dir()


def meaning_dir_exists(project_root: Path) -> bool:
    """Check if .meaning/ directory already exists."""
    return (project_root / MEANING_DIR).is_dir()


# =============================================================================
# Installation Functions
# =============================================================================


def create_meaning_directory(
    project_root: Path,
    project_type: str,
    template_dir: Path,
    dry_run: bool = False,
) -> list[str]:
    """
    Create .meaning/ directory with all necessary files.

    Returns list of files created.
    """
    meaning_path = project_root / MEANING_DIR
    files_created = []

    if not dry_run:
        meaning_path.mkdir(parents=True, exist_ok=True)

    # Copy schema for project type
    schema_src = get_schema_path(template_dir, project_type)
    schema_dst = meaning_path / "schema.yaml"
    if not dry_run:
        shutil.copy2(schema_src, schema_dst)
    files_created.append(str(schema_dst.relative_to(project_root)))

    # Copy config and other files
    for filename in MEANING_FILES:
        src = template_dir / filename
        dst = meaning_path / filename
        if src.exists():
            if not dry_run:
                shutil.copy2(src, dst)
            files_created.append(str(dst.relative_to(project_root)))

    # Copy scripts (creating scripts/ subdirectory)
    for script_path in MEANING_SCRIPTS:
        src = template_dir / script_path
        dst = meaning_path / script_path
        if src.exists():
            if not dry_run:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                # Make scripts executable
                dst.chmod(dst.stat().st_mode | 0o111)
            files_created.append(str(dst.relative_to(project_root)))

    # Create empty index.yaml
    index_dst = meaning_path / INDEX_FILENAME
    if not dry_run:
        now = datetime.now(timezone.utc)
        empty_index = {
            "version": VERSION,
            "generated_at": now.isoformat(),
            "last_updated": now.isoformat(),
            "concepts": [],
            "files": [],
        }
        with open(index_dst, "w") as f:
            yaml.dump(empty_index, f, default_flow_style=False, sort_keys=False)
    files_created.append(str(index_dst.relative_to(project_root)))

    return files_created


def install_claude_hooks(
    project_root: Path,
    template_dir: Path,
    force: bool = False,
    dry_run: bool = False,
) -> tuple[bool, str]:
    """
    Install Claude Code hooks into .claude/settings.json.

    If settings.json exists:
    - Without force: return False with message
    - With force: merge hooks into existing settings

    Returns (success, message).
    """
    hooks_template = template_dir / "hooks.json"
    if not hooks_template.exists():
        return False, "Hooks template not found in package"

    claude_dir = project_root / CLAUDE_DIR
    settings_path = claude_dir / SETTINGS_JSON

    # Load the hooks template
    with open(hooks_template) as f:
        hooks_config = json.load(f)

    if settings_path.exists():
        if not force:
            return False, f"{settings_path} exists (use --force-hooks to merge)"

        # Merge: load existing and add our hooks
        with open(settings_path) as f:
            existing = json.load(f)

        merged = merge_hooks_config(existing, hooks_config)

        if not dry_run:
            with open(settings_path, "w") as f:
                json.dump(merged, f, indent=2)
                f.write("\n")

        return True, f"Merged hooks into existing {settings_path}"

    # Create new settings.json
    if not dry_run:
        claude_dir.mkdir(parents=True, exist_ok=True)
        with open(settings_path, "w") as f:
            json.dump(hooks_config, f, indent=2)
            f.write("\n")

    return True, f"Created {settings_path} with hooks"


def merge_hooks_config(existing: dict[str, Any], new_hooks: dict[str, Any]) -> dict[str, Any]:
    """
    Merge new hooks into existing Claude settings.

    Strategy:
    - Preserve all existing settings
    - Add new hooks that don't conflict
    - Warn about conflicts (same matcher pattern)
    """
    result = existing.copy()

    if "hooks" not in result:
        result["hooks"] = {}

    existing_hooks = result["hooks"]
    new_hooks_section = new_hooks.get("hooks", {})

    for event_type, hook_list in new_hooks_section.items():
        if event_type not in existing_hooks:
            existing_hooks[event_type] = hook_list
        else:
            # Merge hook lists, avoiding duplicates
            existing_matchers = set()
            for hook in existing_hooks[event_type]:
                matcher = hook.get("matcher", "")
                existing_matchers.add(matcher)

            for hook in hook_list:
                matcher = hook.get("matcher", "")
                if matcher not in existing_matchers:
                    existing_hooks[event_type].append(hook)

    return result


def install_skills(
    project_root: Path,
    template_dir: Path,
    dry_run: bool = False,
) -> tuple[list[str], list[str]]:
    """
    Install meaning skills to .claude/skills/.

    Returns (installed_skills, warnings).
    """
    skills_src = template_dir / SKILLS_DIR
    if not skills_src.exists():
        return [], [f"Skills directory not found: {skills_src}"]

    skills_dst = project_root / CLAUDE_DIR / SKILLS_DIR
    installed = []
    warnings = []

    for skill_name in SKILL_NAMES:
        src_skill = skills_src / skill_name
        if not src_skill.exists():
            warnings.append(f"Skill not found: {skill_name}")
            continue

        dst_skill = skills_dst / skill_name

        if dst_skill.exists():
            warnings.append(f"Skill already exists, skipping: {skill_name}")
            continue

        if not dry_run:
            dst_skill.mkdir(parents=True, exist_ok=True)
            # Copy all files in the skill directory
            for src_file in src_skill.iterdir():
                if src_file.is_file():
                    shutil.copy2(src_file, dst_skill / src_file.name)

        installed.append(skill_name)

    return installed, warnings


# =============================================================================
# Main Installation Entry Point
# =============================================================================


def install_meaning(
    project_root: Path,
    options: InstallOptions | None = None,
) -> InstallResult:
    """
    Install meaning into a target project.

    This is the main entry point for the installer.

    Steps:
    1. Check preconditions (git repo warning, existing .meaning/)
    2. Detect or validate project type
    3. Create .meaning/ directory with templates
    4. Optionally install Claude hooks
    5. Optionally install skills

    Args:
        project_root: Path to the target project
        options: Installation options (defaults used if None)

    Returns:
        InstallResult with details of what was done
    """
    if options is None:
        options = InstallOptions()

    result = InstallResult(success=True)

    # Resolve project root
    project_root = project_root.resolve()

    # Check if it's a git repo (warning only)
    if not is_git_repo(project_root):
        result.add_warning("Not a git repository. Consider initializing git before meaning.")

    # Check for existing .meaning/
    if meaning_dir_exists(project_root):
        if options.conflict_resolution == ConflictResolution.ABORT:
            result.add_error(
                f".meaning/ already exists in {project_root}. "
                "Use 'meaning update' to sync, or remove it first."
            )
            return result
        elif options.conflict_resolution == ConflictResolution.SKIP:
            result.add_warning(".meaning/ exists, skipping directory creation")
        elif options.conflict_resolution == ConflictResolution.OVERWRITE:
            if not options.dry_run:
                shutil.rmtree(project_root / MEANING_DIR)
            result.add_warning(".meaning/ removed for fresh installation")

    # Detect or validate project type
    if options.project_type:
        project_type = options.project_type
    else:
        project_type = detect_project_type(project_root)

    # Get template directory
    try:
        template_dir = get_package_template_dir()
    except FileNotFoundError as e:
        result.add_error(str(e))
        return result

    # Validate project type has a schema
    try:
        get_schema_path(template_dir, project_type)
    except ValueError as e:
        result.add_error(str(e))
        return result

    # Create .meaning/ directory
    if not meaning_dir_exists(project_root) or options.conflict_resolution in (
        ConflictResolution.OVERWRITE,
        ConflictResolution.MERGE,
    ):
        try:
            files = create_meaning_directory(
                project_root,
                project_type,
                template_dir,
                dry_run=options.dry_run,
            )
            result.meaning_dir_created = True
            result.files_copied.extend(files)
        except Exception as e:
            result.add_error(f"Failed to create .meaning/: {e}")
            return result

    # Install Claude hooks
    if options.install_hooks:
        ok, msg = install_claude_hooks(
            project_root,
            template_dir,
            force=options.force_hooks,
            dry_run=options.dry_run,
        )
        if ok:
            result.hooks_installed = True
        else:
            result.add_warning(f"Hooks: {msg}")

    # Install skills
    if options.install_skills:
        installed, warnings = install_skills(
            project_root,
            template_dir,
            dry_run=options.dry_run,
        )
        result.skills_installed = installed
        for w in warnings:
            result.add_warning(f"Skills: {w}")

    return result


def format_install_result(result: InstallResult, project_type: str) -> str:
    """Format installation result for display."""
    lines = []

    if result.success:
        lines.append(f"✓ Initialized meaning for {project_type} project")
    else:
        lines.append("❌ Installation failed")

    if result.meaning_dir_created:
        lines.append(f"  • Created .meaning/ with {len(result.files_copied)} files")

    if result.hooks_installed:
        lines.append("  • Installed Claude Code hooks")

    if result.skills_installed:
        lines.append(f"  • Installed {len(result.skills_installed)} skills")

    if result.warnings:
        lines.append("")
        lines.append("Warnings:")
        for w in result.warnings:
            lines.append(f"  ⚠️  {w}")

    if result.errors:
        lines.append("")
        lines.append("Errors:")
        for e in result.errors:
            lines.append(f"  ❌ {e}")

    if result.success:
        lines.append("")
        lines.append("Next steps:")
        lines.append("  1. Run 'meaning init' to scan and index files")
        lines.append("  2. Run 'meaning review' to refine auto-generated entries")
        lines.append("  3. Commit .meaning/ to git")

    return "\n".join(lines)
