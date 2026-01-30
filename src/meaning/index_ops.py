"""
Meaning: Index operations.

This module handles index manipulation operations like finding files,
pruning entries, creating skeleton entries, and applying inference.
"""

from __future__ import annotations

import copy
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from meaning.constants import (
    CONFIG_FILENAME,
    MEANING_DIR,
    SCHEMA_FILENAME,
    VERSION,
)
from meaning.models import (
    FileEntry,
    MeaningConfig,
    MeaningIndex,
    MeaningSchema,
    Relationship,
)
from meaning.project import detect_project_type, meaning_dir_exists, scan_project_files


def create_skeleton_entry(path: str) -> FileEntry:
    """Create a skeleton file entry for a new/modified file."""
    return FileEntry(
        path=path,
        intent="[NEEDS REVIEW] Created/modified by agent",
        status="active",
        needs_review=True,
        last_verified=datetime.now(timezone.utc),
        tags=[],
        relationships=[],
    )


def create_meaning_dir(project_root: Path) -> Path:
    """Create the .meaning directory structure."""
    meaning_path = project_root / MEANING_DIR
    meaning_path.mkdir(exist_ok=True)
    return meaning_path


def resolve_template_dir(template_dir: Path | None) -> Path:
    """Resolve the template directory for schema/config/hooks."""
    if template_dir is not None:
        return template_dir

    package_templates = Path(__file__).parent / "templates"
    if package_templates.exists():
        return package_templates

    repo_templates = Path(__file__).parent.parent.parent / "templates"
    if repo_templates.exists():
        return repo_templates

    raise FileNotFoundError("Template directory not found")


def copy_template_file(src: Path, dest: Path) -> bool:
    """Copy a template file if it exists. Returns True on success."""
    if not src.exists():
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return True


def prune_excluded_entries(index: MeaningIndex, config: MeaningConfig) -> list[str]:
    """
    Remove index entries that are now excluded by config.

    Returns:
        List of removed file paths.
    """
    removed = [entry.path for entry in index.files if config.is_excluded(entry.path)]
    if not removed:
        return []

    removed_set = set(removed)
    index.files = [entry for entry in index.files if entry.path not in removed_set]

    # Remove references from concepts
    for concept in index.concepts:
        if concept.files:
            concept.files = [path for path in concept.files if path not in removed_set]
        if concept.entry_point in removed_set:
            concept.entry_point = None

    # Remove relationships pointing to excluded files
    for entry in index.files:
        if entry.relationships:
            entry.relationships = [
                rel
                for rel in entry.relationships
                if (rel.target is None or rel.target not in removed_set)
                and (rel.source is None or rel.source not in removed_set)
            ]

    return removed


def find_unindexed_files(
    project_root: Path, index: MeaningIndex, config: MeaningConfig
) -> list[str]:
    """
    Find files that exist but aren't in the index.

    Args:
        project_root: Project root directory
        index: Current meaning index
        config: Configuration with exclusion patterns

    Returns:
        List of unindexed file paths
    """
    all_files = scan_project_files(project_root, config)
    indexed_paths = {entry.path for entry in index.files}
    return [f for f in all_files if f not in indexed_paths and not index.is_collected(f)]


def find_deleted_files(project_root: Path, index: MeaningIndex) -> list[str]:
    """
    Find files in index that no longer exist on filesystem.

    Args:
        project_root: Project root directory
        index: Current meaning index

    Returns:
        List of deleted file paths
    """
    deleted = []
    for entry in index.files:
        full_path = project_root / entry.path
        if not full_path.exists():
            deleted.append(entry.path)
    return deleted


def find_modified_files(project_root: Path, index: MeaningIndex) -> list[str]:
    """
    Find files that have been modified since last verification.

    Uses file modification time vs last_verified timestamp.

    Args:
        project_root: Project root directory
        index: Current meaning index

    Returns:
        List of modified file paths
    """
    modified = []
    for entry in index.files:
        full_path = project_root / entry.path
        if full_path.exists():
            mtime = datetime.fromtimestamp(full_path.stat().st_mtime, tz=timezone.utc)
            if mtime > entry.last_verified:
                modified.append(entry.path)
    return modified


def initialize_meaning(
    project_root: Path,
    project_type: str | None = None,
    template_dir: Path | None = None,
) -> tuple[MeaningIndex, MeaningSchema, MeaningConfig]:
    """
    Initialize .meaning/ directory with templates.

    Args:
        project_root: Project root directory
        project_type: Project type (python, node, rust, docs) or None to detect
        template_dir: Directory containing templates (default: package templates/)

    Returns:
        Tuple of (index, schema, config)

    Raises:
        FileExistsError: If .meaning/ already exists
        ValueError: If project_type is invalid
    """
    # Import here to avoid circular imports
    from meaning.index_io import load_config, load_schema

    if meaning_dir_exists(project_root):
        raise FileExistsError(f".meaning/ already exists in {project_root}")

    # Detect project type if not provided
    if project_type is None:
        project_type = detect_project_type(project_root)

    # Resolve template directory
    template_dir = resolve_template_dir(template_dir)

    # Validate project type
    schema_file = template_dir / "schema" / f"{project_type}.yaml"
    if not schema_file.exists():
        raise ValueError(f"Unknown project type: {project_type}")

    # Create .meaning/ directory
    meaning_path = create_meaning_dir(project_root)

    # Copy schema template
    schema_content = schema_file.read_text()
    (meaning_path / SCHEMA_FILENAME).write_text(schema_content)

    # Copy config template
    config_template = template_dir / CONFIG_FILENAME
    config_content = config_template.read_text()
    (meaning_path / CONFIG_FILENAME).write_text(config_content)

    # Copy hooks and hook scripts (optional)
    copy_template_file(template_dir / "hooks.json", meaning_path / "hooks.json")
    copy_template_file(
        template_dir / "scripts" / "meaning-post-write.sh",
        meaning_path / "scripts" / "meaning-post-write.sh",
    )
    copy_template_file(
        template_dir / "scripts" / "meaning-validate.sh",
        meaning_path / "scripts" / "meaning-validate.sh",
    )

    # Create empty index
    now = datetime.now(timezone.utc)
    index = MeaningIndex(
        version=VERSION,
        generated_at=now,
        last_updated=now,
        concepts=[],
        files=[],
    )

    # Load the schemas we just created
    schema = load_schema(project_root)
    config = load_config(project_root)

    return index, schema, config


def install_claude_hooks(
    project_root: Path, template_dir: Path | None = None, force: bool = False
) -> tuple[bool, str]:
    """Install Claude Code hooks into .claude/settings.json."""
    try:
        template_dir = resolve_template_dir(template_dir)
    except FileNotFoundError as e:
        return False, str(e)
    hooks_template = template_dir / "hooks.json"
    if not hooks_template.exists():
        return False, "Hooks template not found"

    claude_dir = project_root / ".claude"
    settings_path = claude_dir / "settings.json"

    if settings_path.exists() and not force:
        return False, f"{settings_path} already exists (use --force to overwrite)"

    claude_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(hooks_template, settings_path)
    return True, f"Installed hooks to {settings_path}"


def entry_from_inference(
    file_path: str,
    result: Any,
    threshold: float,
    now: datetime,
) -> FileEntry:
    """Create a new FileEntry from inference results."""
    high_conf_tags = [t.tag for t in result.tags if t.confidence >= threshold]
    high_conf_rels = [r.relationship for r in result.relationships if r.confidence >= threshold]

    if result.intent and result.intent.confidence >= threshold:
        intent = result.intent.intent
        intent_confident = True
    else:
        intent = f"[NEEDS REVIEW] {file_path}"
        intent_confident = False

    needs_review = bool(result.errors) or not intent_confident or not high_conf_tags
    tags = high_conf_tags if high_conf_tags else ["x-needs-tags"]

    return FileEntry(
        path=file_path,
        intent=intent,
        status="active",
        needs_review=needs_review,
        last_verified=now,
        tags=tags,
        relationships=high_conf_rels,
    )


def _relationship_key(rel: Relationship) -> tuple[str, str | None, str | None]:
    return (rel.type, rel.target, rel.source)


def _review_snapshot(
    entry: FileEntry,
) -> tuple[str, tuple[str, ...], tuple[tuple[str, str | None, str | None], ...], bool]:
    return (
        entry.intent,
        tuple(entry.tags),
        tuple(_relationship_key(r) for r in entry.relationships),
        entry.needs_review,
    )


def _intent_has_markdown(intent: str) -> bool:
    stripped = intent.lstrip()
    return "`" in intent or "**" in intent or stripped.startswith(("- ", "* ", "> "))


def apply_inference_to_entry(
    entry: FileEntry,
    result: Any,
    threshold: float,
    config: MeaningConfig,
    now: datetime,
) -> bool:
    """Apply high-confidence inference results to an existing entry."""
    before = _review_snapshot(entry)
    if result.intent and result.intent.confidence >= threshold:
        if (
            not entry.intent
            or entry.intent.startswith("[NEEDS REVIEW]")
            or _intent_has_markdown(entry.intent)
        ):
            entry.intent = result.intent.intent

    for tag in (t.tag for t in result.tags if t.confidence >= threshold):
        if tag not in entry.tags:
            entry.tags.append(tag)

    existing_rels = {_relationship_key(r) for r in entry.relationships}
    for rel in (r.relationship for r in result.relationships if r.confidence >= threshold):
        if _relationship_key(rel) not in existing_rels:
            entry.relationships.append(rel)
            existing_rels.add(_relationship_key(rel))

    entry.last_verified = now

    needs_review = bool(result.errors)
    if config.require_intent and (not entry.intent or entry.intent.startswith("[NEEDS REVIEW]")):
        needs_review = True
    if config.require_tags and not entry.tags:
        needs_review = True

    entry.needs_review = needs_review
    return before != _review_snapshot(entry)


def preview_inference_changes(
    entry: FileEntry,
    result: Any,
    threshold: float,
    config: MeaningConfig,
    now: datetime,
) -> bool:
    """Preview whether inference would change an entry without mutating it."""
    entry_copy = copy.deepcopy(entry)
    return apply_inference_to_entry(entry_copy, result, threshold, config, now)


def preview_inference_diff(
    entry: FileEntry,
    result: Any,
    threshold: float,
    config: MeaningConfig,
    now: datetime,
) -> dict[str, Any]:
    """Preview inference changes without mutating the entry."""
    entry_copy = copy.deepcopy(entry)
    apply_inference_to_entry(entry_copy, result, threshold, config, now)

    intent_change = None
    if entry.intent != entry_copy.intent:
        intent_change = (entry.intent, entry_copy.intent)

    tags_added = [t for t in entry_copy.tags if t not in entry.tags]
    tags_removed = [t for t in entry.tags if t not in entry_copy.tags]

    existing_rels = {_relationship_key(r) for r in entry.relationships}
    new_rels = {_relationship_key(r) for r in entry_copy.relationships}
    rels_added = [r for r in entry_copy.relationships if _relationship_key(r) not in existing_rels]
    rels_removed = [r for r in entry.relationships if _relationship_key(r) not in new_rels]

    needs_review_change = None
    if entry.needs_review != entry_copy.needs_review:
        needs_review_change = (entry.needs_review, entry_copy.needs_review)

    return {
        "intent": intent_change,
        "tags_added": tags_added,
        "tags_removed": tags_removed,
        "rels_added": rels_added,
        "rels_removed": rels_removed,
        "needs_review": needs_review_change,
    }
