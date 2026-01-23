"""
Meaning: Semantic File Index for AI Agents

Core library for parsing, validating, and manipulating .meaning/ indexes.
"""

from __future__ import annotations

import copy
import fnmatch
import os
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

# =============================================================================
# Constants
# =============================================================================

VERSION = "0.1"
INDEX_FILENAME = "index.yaml"
SCHEMA_FILENAME = "schema.yaml"
CONFIG_FILENAME = "config.yaml"
MEANING_DIR = ".meaning"

DEFAULT_STALE_THRESHOLD_DAYS = 7
DEFAULT_MAX_INTENT_LENGTH = 280
DEFAULT_REVIEW_THRESHOLD = 0.8

VALID_STATUSES = {"active", "draft", "deprecated", "generated"}


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class Relationship:
    """A typed connection between two files."""

    type: str
    target: str | None = None
    source: str | None = None

    def __post_init__(self) -> None:
        if not self.target and not self.source:
            raise ValueError("Relationship must have either target or source")

    def to_dict(self) -> dict[str, str]:
        d = {"type": self.type}
        if self.target:
            d["target"] = self.target
        if self.source:
            d["source"] = self.source
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Relationship:
        return cls(
            type=data["type"],
            target=data.get("target"),
            source=data.get("source"),
        )


@dataclass
class FileEntry:
    """Semantic metadata for a single file."""

    path: str
    intent: str
    status: str = "active"
    needs_review: bool = False
    last_verified: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tags: list[str] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.status not in VALID_STATUSES:
            raise ValueError(f"Invalid status: {self.status}. Must be one of {VALID_STATUSES}")

    def to_dict(self) -> dict[str, Any]:
        d = {
            "path": self.path,
            "intent": self.intent,
            "status": self.status,
            "needs_review": self.needs_review,
            "last_verified": self.last_verified.isoformat(),
        }
        if self.tags:
            d["tags"] = self.tags
        if self.relationships:
            d["relationships"] = [r.to_dict() for r in self.relationships]
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FileEntry:
        last_verified = data.get("last_verified")
        if isinstance(last_verified, str):
            last_verified = datetime.fromisoformat(last_verified)
        elif last_verified is None:
            last_verified = datetime.now(timezone.utc)

        relationships = [Relationship.from_dict(r) for r in data.get("relationships", [])]

        return cls(
            path=data["path"],
            intent=data.get("intent", "[NEEDS REVIEW] No intent specified"),
            status=data.get("status", "active"),
            needs_review=data.get("needs_review", False),
            last_verified=last_verified,
            tags=data.get("tags", []),
            relationships=relationships,
        )

    def is_stale(self, threshold_days: int = DEFAULT_STALE_THRESHOLD_DAYS) -> bool:
        """Check if entry hasn't been verified within threshold."""
        now = datetime.now(timezone.utc)
        if self.last_verified.tzinfo is None:
            last = self.last_verified.replace(tzinfo=timezone.utc)
        else:
            last = self.last_verified
        delta = now - last
        return delta.days > threshold_days


@dataclass
class Concept:
    """A cross-file semantic grouping."""

    name: str
    description: str
    files: list[str] = field(default_factory=list)
    entry_point: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = {
            "name": self.name,
            "description": self.description,
            "files": self.files,
        }
        if self.entry_point:
            d["entry_point"] = self.entry_point
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Concept:
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            files=data.get("files", []),
            entry_point=data.get("entry_point"),
        )


@dataclass
class MeaningIndex:
    """The complete semantic index for a project."""

    version: str = VERSION
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    concepts: list[Concept] = field(default_factory=list)
    files: list[FileEntry] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "generated_at": self.generated_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "concepts": [c.to_dict() for c in self.concepts],
            "files": [f.to_dict() for f in self.files],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MeaningIndex:
        generated_at = data.get("generated_at")
        if isinstance(generated_at, str):
            generated_at = datetime.fromisoformat(generated_at)
        elif generated_at is None:
            generated_at = datetime.now(timezone.utc)

        last_updated = data.get("last_updated")
        if isinstance(last_updated, str):
            last_updated = datetime.fromisoformat(last_updated)
        elif last_updated is None:
            last_updated = datetime.now(timezone.utc)

        concepts = [Concept.from_dict(c) for c in data.get("concepts", [])]
        files = [FileEntry.from_dict(f) for f in data.get("files", [])]

        return cls(
            version=data.get("version", VERSION),
            generated_at=generated_at,
            last_updated=last_updated,
            concepts=concepts,
            files=files,
        )

    def get_file(self, path: str) -> FileEntry | None:
        """Find a file entry by path."""
        for f in self.files:
            if f.path == path:
                return f
        return None

    def add_file(self, entry: FileEntry) -> None:
        """Add or update a file entry."""
        existing = self.get_file(entry.path)
        if existing:
            self.files.remove(existing)
        self.files.append(entry)
        self.last_updated = datetime.now(timezone.utc)

    def remove_file(self, path: str) -> bool:
        """Remove a file entry. Returns True if found and removed."""
        entry = self.get_file(path)
        if entry:
            self.files.remove(entry)
            self.last_updated = datetime.now(timezone.utc)
            return True
        return False

    def get_concept(self, name: str) -> Concept | None:
        """Find a concept by name."""
        for c in self.concepts:
            if c.name == name:
                return c
        return None

    def files_needing_review(self) -> list[FileEntry]:
        """Get all files flagged for review."""
        return [f for f in self.files if f.needs_review]

    def stale_files(self, threshold_days: int = DEFAULT_STALE_THRESHOLD_DAYS) -> list[FileEntry]:
        """Get all files past the staleness threshold."""
        return [f for f in self.files if f.is_stale(threshold_days)]

    def find_by_tags(self, tags: list[str], match_all: bool = False) -> list[FileEntry]:
        """Find files matching given tags."""
        results = []
        for f in self.files:
            if match_all:
                if all(t in f.tags for t in tags):
                    results.append(f)
            else:
                if any(t in f.tags for t in tags):
                    results.append(f)
        return results

    def find_by_intent(self, keywords: list[str]) -> list[FileEntry]:
        """Find files whose intent contains any of the keywords."""
        results = []
        for f in self.files:
            intent_lower = f.intent.lower()
            if any(kw.lower() in intent_lower for kw in keywords):
                results.append(f)
        return results

    def find_related(
        self, path: str, relationship_types: list[str] | None = None
    ) -> list[tuple[str, FileEntry]]:
        """
        Find files related to the given path.
        Returns list of (relationship_type, file_entry) tuples.
        """
        results = []
        for f in self.files:
            for rel in f.relationships:
                if relationship_types and rel.type not in relationship_types:
                    continue
                if rel.target == path or rel.source == path:
                    results.append((rel.type, f))
                elif f.path == path:
                    target_path = rel.target or rel.source
                    if target_path:
                        target_entry = self.get_file(target_path)
                        if target_entry:
                            results.append((rel.type, target_entry))
        return results


@dataclass
class RelationshipType:
    """Definition of a relationship type from schema."""

    name: str
    description: str
    direction: str = "source_to_target"  # source_to_target | target_to_source | bidirectional

    def to_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "description": self.description,
            "direction": self.direction,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RelationshipType:
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            direction=data.get("direction", "source_to_target"),
        )


@dataclass
class MeaningSchema:
    """Project-specific vocabulary and relationship definitions."""

    version: str = VERSION
    project_type: str = "mixed"
    relationship_types: list[RelationshipType] = field(default_factory=list)
    tag_vocabulary: dict[str, list[str]] = field(default_factory=dict)
    custom_prefix: str = "x-"
    statuses: list[str] = field(default_factory=lambda: list(VALID_STATUSES))

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "project_type": self.project_type,
            "relationship_types": [r.to_dict() for r in self.relationship_types],
            "tag_vocabulary": self.tag_vocabulary,
            "custom_prefix": self.custom_prefix,
            "statuses": self.statuses,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MeaningSchema:
        relationship_types = [
            RelationshipType.from_dict(r) for r in data.get("relationship_types", [])
        ]
        return cls(
            version=data.get("version", VERSION),
            project_type=data.get("project_type", "mixed"),
            relationship_types=relationship_types,
            tag_vocabulary=data.get("tag_vocabulary", {}),
            custom_prefix=data.get("custom_prefix", "x-"),
            statuses=data.get("statuses", list(VALID_STATUSES)),
        )

    def is_valid_relationship_type(self, type_name: str) -> bool:
        """Check if relationship type is defined."""
        return any(r.name == type_name for r in self.relationship_types)

    def is_valid_tag(self, tag: str) -> bool:
        """Check if tag is in vocabulary or is a custom tag."""
        if tag.startswith(self.custom_prefix):
            return True
        for category_tags in self.tag_vocabulary.values():
            if tag in category_tags:
                return True
        return False

    def all_tags(self) -> list[str]:
        """Get flattened list of all valid tags."""
        tags = []
        for category_tags in self.tag_vocabulary.values():
            tags.extend(category_tags)
        return tags


@dataclass
class MeaningConfig:
    """Project settings and exclusion patterns."""

    version: str = VERSION
    exclude_patterns: list[str] = field(default_factory=list)
    exclude_paths: list[str] = field(default_factory=list)
    include_paths: list[str] = field(default_factory=list)
    require_intent: bool = True
    require_tags: bool = False
    warn_on_unknown_tags: bool = True
    max_intent_length: int = DEFAULT_MAX_INTENT_LENGTH
    stale_threshold_days: int = DEFAULT_STALE_THRESHOLD_DAYS
    auto_flag_modified: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "exclude": {
                "patterns": self.exclude_patterns,
                "paths": self.exclude_paths,
            },
            "include": {
                "paths": self.include_paths,
            },
            "settings": {
                "require_intent": self.require_intent,
                "require_tags": self.require_tags,
                "warn_on_unknown_tags": self.warn_on_unknown_tags,
                "max_intent_length": self.max_intent_length,
                "stale_threshold_days": self.stale_threshold_days,
                "auto_flag_modified": self.auto_flag_modified,
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MeaningConfig:
        exclude = data.get("exclude", {})
        include = data.get("include", {})
        settings = data.get("settings", {})

        return cls(
            version=data.get("version", VERSION),
            exclude_patterns=exclude.get("patterns", []),
            exclude_paths=exclude.get("paths", []),
            include_paths=include.get("paths", []),
            require_intent=settings.get("require_intent", True),
            require_tags=settings.get("require_tags", False),
            warn_on_unknown_tags=settings.get("warn_on_unknown_tags", True),
            max_intent_length=settings.get("max_intent_length", DEFAULT_MAX_INTENT_LENGTH),
            stale_threshold_days=settings.get("stale_threshold_days", DEFAULT_STALE_THRESHOLD_DAYS),
            auto_flag_modified=settings.get("auto_flag_modified", True),
        )

    def is_excluded(self, path: str) -> bool:
        """Check if path should be excluded from indexing."""
        # Check explicit includes first (override excludes)
        for include_path in self.include_paths:
            if path.startswith(include_path) or path == include_path:
                return False

        # Check explicit path excludes
        for exclude_path in self.exclude_paths:
            if path.startswith(exclude_path) or path == exclude_path:
                return True

        # Check pattern excludes
        for pattern in self.exclude_patterns:
            if fnmatch.fnmatch(path, pattern):
                return True
            # Also check if any path component matches
            if "**" in pattern:
                # Handle ** glob patterns
                regex_pattern = pattern.replace("**", ".*").replace("*", "[^/]*")
                if re.match(regex_pattern, path):
                    return True

        return False


# =============================================================================
# File I/O
# =============================================================================


def load_yaml(filepath: Path) -> dict[str, Any]:
    """Load and parse a YAML file."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data or {}


def save_yaml(filepath: Path, data: dict[str, Any]) -> None:
    """Save data to a YAML file."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


def load_index(project_root: Path) -> MeaningIndex:
    """Load the meaning index from a project."""
    index_path = project_root / MEANING_DIR / INDEX_FILENAME
    if not index_path.exists():
        raise FileNotFoundError(f"Index not found: {index_path}")
    data = load_yaml(index_path)
    return MeaningIndex.from_dict(data)


def save_index(project_root: Path, index: MeaningIndex) -> None:
    """Save the meaning index to a project."""
    index_path = project_root / MEANING_DIR / INDEX_FILENAME
    index.last_updated = datetime.now(timezone.utc)
    save_yaml(index_path, index.to_dict())


def load_schema(project_root: Path) -> MeaningSchema:
    """Load the meaning schema from a project."""
    schema_path = project_root / MEANING_DIR / SCHEMA_FILENAME
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema not found: {schema_path}")
    data = load_yaml(schema_path)
    return MeaningSchema.from_dict(data)


def save_schema(project_root: Path, schema: MeaningSchema) -> None:
    """Save the meaning schema to a project."""
    schema_path = project_root / MEANING_DIR / SCHEMA_FILENAME
    save_yaml(schema_path, schema.to_dict())


def load_config(project_root: Path) -> MeaningConfig:
    """Load the meaning config from a project."""
    config_path = project_root / MEANING_DIR / CONFIG_FILENAME
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")
    data = load_yaml(config_path)
    return MeaningConfig.from_dict(data)


def save_config(project_root: Path, config: MeaningConfig) -> None:
    """Save the meaning config to a project."""
    config_path = project_root / MEANING_DIR / CONFIG_FILENAME
    save_yaml(config_path, config.to_dict())


# =============================================================================
# Validation
# =============================================================================


@dataclass
class ValidationResult:
    """Result of validating a meaning index."""

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add_error(self, message: str) -> None:
        self.errors.append(message)
        self.is_valid = False

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)


def validate_index(
    index: MeaningIndex,
    schema: MeaningSchema,
    config: MeaningConfig,
    project_root: Path,
) -> ValidationResult:
    """Validate a meaning index against schema and filesystem."""
    result = ValidationResult(is_valid=True)

    # Track all indexed paths for relationship validation
    indexed_paths = {f.path for f in index.files}

    for entry in index.files:
        # Check file exists
        file_path = project_root / entry.path
        if not file_path.exists():
            result.add_error(f"Indexed file does not exist: {entry.path}")

        # Check intent length
        if len(entry.intent) > config.max_intent_length:
            result.add_warning(
                f"Intent exceeds max length ({len(entry.intent)} > {config.max_intent_length}): {entry.path}"
            )

        # Check intent required
        if config.require_intent and (
            not entry.intent or entry.intent.startswith("[NEEDS REVIEW]")
        ):
            result.add_warning(f"File missing proper intent: {entry.path}")

        # Check tags required
        if config.require_tags and not entry.tags:
            result.add_warning(f"File missing tags: {entry.path}")

        # Check tags valid
        if config.warn_on_unknown_tags:
            for tag in entry.tags:
                if not schema.is_valid_tag(tag):
                    result.add_warning(f"Unknown tag '{tag}' on file: {entry.path}")

        # Check relationship types valid
        for rel in entry.relationships:
            if not schema.is_valid_relationship_type(rel.type):
                result.add_warning(f"Unknown relationship type '{rel.type}' on file: {entry.path}")

            # Check relationship targets exist
            target = rel.target or rel.source
            if target and target not in indexed_paths:
                result.add_error(f"Dangling relationship to '{target}' from: {entry.path}")

        # Check staleness
        if entry.is_stale(config.stale_threshold_days):
            result.add_warning(f"Stale entry (>{config.stale_threshold_days} days): {entry.path}")

    # Check for unindexed files
    for root, dirs, files in os.walk(project_root):
        # Skip hidden directories and meaning directory
        dirs[:] = [d for d in dirs if not d.startswith(".")]

        for filename in files:
            filepath = Path(root) / filename
            rel_path = str(filepath.relative_to(project_root))

            if config.is_excluded(rel_path):
                continue

            if rel_path not in indexed_paths:
                result.add_warning(f"File not indexed: {rel_path}")

    # Validate concepts
    for concept in index.concepts:
        for file_path in concept.files:
            if file_path not in indexed_paths:
                result.add_warning(
                    f"Concept '{concept.name}' references non-indexed file: {file_path}"
                )
        if concept.entry_point and concept.entry_point not in concept.files:
            result.add_warning(
                f"Concept '{concept.name}' entry_point not in file list: {concept.entry_point}"
            )

    return result


# =============================================================================
# Project Detection
# =============================================================================

PROJECT_MARKERS = {
    "python": ["pyproject.toml", "setup.py", "requirements.txt", "Pipfile"],
    "node": ["package.json", "yarn.lock", "pnpm-lock.yaml"],
    "rust": ["Cargo.toml"],
    "go": ["go.mod"],
    "docs": ["mkdocs.yml", "docusaurus.config.js", "_config.yml"],
}


def detect_project_type(project_root: Path) -> str:
    """Detect the project type based on marker files."""
    for project_type, markers in PROJECT_MARKERS.items():
        for marker in markers:
            if (project_root / marker).exists():
                return project_type
    return "mixed"


def is_git_repo(project_root: Path) -> bool:
    """Check if directory is a git repository."""
    return (project_root / ".git").is_dir()


# =============================================================================
# Skeleton Creation
# =============================================================================


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


def meaning_dir_exists(project_root: Path) -> bool:
    """Check if .meaning directory exists."""
    return (project_root / MEANING_DIR).is_dir()


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


def scan_project_files(project_root: Path, config: MeaningConfig) -> list[str]:
    """
    Scan project directory for all non-excluded files.

    Args:
        project_root: Project root directory
        config: Configuration with exclusion patterns

    Returns:
        List of relative file paths
    """
    files = []
    for path in project_root.rglob("*"):
        if path.is_file():
            rel_path = str(path.relative_to(project_root))
            if not config.is_excluded(rel_path):
                files.append(rel_path)
    return sorted(files)


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
    return [f for f in all_files if f not in indexed_paths]


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


# =============================================================================
# Query Engine
# =============================================================================


@dataclass
class QueryResult:
    """Result from a semantic query."""

    files: list[FileEntry]
    explanation: str
    query_type: str


def query_index(index: MeaningIndex, schema: MeaningSchema, query: str) -> QueryResult:
    """
    Natural language query against the semantic index.

    Supports:
    - Tag searches: "test files", "config files", "API files"
    - Relationship queries: "what tests X", "what documents Y", "what imports Z"
    - Status queries: "what needs review", "what is stale"
    - Temporal queries: "what changed recently", "latest files"
    - Concept queries: "show me the core library"
    - Intent searches: "files that do parsing", "files about authentication"
    """
    q = query.lower().strip()
    results: list[FileEntry] = []
    explanation = ""
    query_type = "unknown"

    # Status queries
    if "need" in q and "review" in q:
        results = index.files_needing_review()
        explanation = "Files flagged for review"
        query_type = "status"

    elif "stale" in q:
        results = [f for f in index.files if f.is_stale()]
        explanation = "Files not verified in the last 7 days"
        query_type = "status"

    # Relationship queries - "what tests X", "what documents Y", "what imports Z"
    elif any(word in q for word in ["what", "which", "show"]) and any(
        rel in q for rel in ["test", "document", "import", "implement", "configure", "call"]
    ):
        # Extract relationship type
        rel_type = None
        for rel in ["tests", "documents", "imports", "implements", "configures", "calls"]:
            if rel.rstrip("s") in q:  # Handle singular forms
                rel_type = rel
                break

        if rel_type:
            # Try to extract target file from query
            target = None
            for file in index.files:
                # Check if any part of the file path is mentioned
                path_parts = file.path.replace("/", " ").replace("_", " ").replace(".", " ").split()
                if any(part.lower() in q for part in path_parts if len(part) > 3):
                    target = file.path
                    break

            if target:
                # Find files with this relationship to the target
                results = [
                    f
                    for f in index.files
                    if any(r.type == rel_type and r.target == target for r in f.relationships)
                ]
                explanation = f"Files that {rel_type} {target}"
                query_type = "relationship"
            else:
                # Show all files with this relationship type
                results = [
                    f for f in index.files if any(r.type == rel_type for r in f.relationships)
                ]
                explanation = f"Files with '{rel_type}' relationships"
                query_type = "relationship"

    # Concept queries
    elif "concept" in q or any(c.name.replace("-", " ") in q for c in index.concepts):
        # Find matching concept
        for concept in index.concepts:
            if concept.name.replace("-", " ") in q:
                results = [f for f in index.files if f.path in concept.files]
                explanation = f"Files in concept '{concept.name}': {concept.description}"
                query_type = "concept"
                break

    # Tag queries - look for common tag patterns
    elif any(word in q for word in ["file", "show", "find", "list"]):
        # Extract potential tag keywords
        tag_keywords = []

        # Check against schema vocabulary
        for category, tags in schema.tag_vocabulary.items():
            for tag in tags:
                if tag in q or tag.replace("-", " ") in q:
                    tag_keywords.append(tag)

        if tag_keywords:
            results = index.find_by_tags(tag_keywords, match_all=False)
            explanation = f"Files tagged with: {', '.join(tag_keywords)}"
            query_type = "tag"

    # Temporal queries
    elif "recent" in q or "latest" in q or "changed" in q:
        # Sort by last_verified, most recent first
        results = sorted(index.files, key=lambda f: f.last_verified, reverse=True)[:10]
        explanation = "10 most recently updated files"
        query_type = "temporal"

    # Intent search (fallback) - keyword matching in intent strings
    if not results:
        # Extract meaningful keywords from query (skip common words)
        stop_words = {
            "what",
            "where",
            "who",
            "when",
            "why",
            "how",
            "is",
            "are",
            "the",
            "a",
            "an",
            "do",
            "does",
            "did",
            "file",
            "files",
            "show",
            "find",
            "list",
            "me",
            "all",
        }
        keywords = [word for word in q.split() if word not in stop_words and len(word) > 3]

        if keywords:
            for file in index.files:
                intent_lower = file.intent.lower()
                # Match if any keyword is in the intent
                if any(kw in intent_lower for kw in keywords):
                    results.append(file)

            if results:
                explanation = f"Files with intents matching: {', '.join(keywords)}"
                query_type = "intent"

    # No results found
    if not results:
        explanation = f"No files found matching query: '{query}'"
        query_type = "no_match"

    return QueryResult(files=results, explanation=explanation, query_type=query_type)


def display_query_results(result: QueryResult, max_results: int = 20) -> None:
    """Display query results in a formatted way."""
    print(f"🔍 Query Results: {result.explanation}")
    print(f"   Type: {result.query_type}")
    print()

    if not result.files:
        print("  No files found.")
        return

    total = len(result.files)
    showing = min(total, max_results)

    print(f"  Found {total} file{'s' if total != 1 else ''} (showing {showing}):")
    print()

    for i, file in enumerate(result.files[:max_results], 1):
        # File path with status indicator
        status_icon = "⚠️ " if file.needs_review else "  "
        print(f"  {i}. {status_icon}{file.path}")

        # Intent (truncated)
        intent = file.intent[:80] + "..." if len(file.intent) > 80 else file.intent
        print(f'      "{intent}"')

        # Tags
        if file.tags:
            tags_str = ", ".join(file.tags[:5])
            if len(file.tags) > 5:
                tags_str += f" +{len(file.tags) - 5} more"
            print(f"      Tags: {tags_str}")

        # Key relationships
        if file.relationships:
            rel_summary = {}
            for rel in file.relationships:
                if rel.type not in rel_summary:
                    rel_summary[rel.type] = []
                if rel.target:
                    rel_summary[rel.type].append(rel.target)

            rel_strs = [f"{k}({len(v)})" for k, v in rel_summary.items()]
            print(f"      Relationships: {', '.join(rel_strs)}")

        print()

    if total > max_results:
        print(f"  ... and {total - max_results} more")
        print()


# =============================================================================
# CLI Entry Point (for testing)
# =============================================================================


def display_status(project_root: Path) -> None:
    """Display a comprehensive status overview of the meaning index."""
    try:
        index = load_index(project_root)
        schema = load_schema(project_root)
        config = load_config(project_root)
    except FileNotFoundError as e:
        print(f"❌ No .meaning/ directory found in {project_root}")
        print(f"\n💡 Initialize with: python -m meaning init")
        return

    # Validate to get health metrics
    result = validate_index(index, schema, config, project_root)

    # Detect project info
    project_type = detect_project_type(project_root)
    project_name = project_root.name

    # Calculate metrics
    total_files = len(index.files)
    needs_review = len(index.files_needing_review())
    stale = sum(1 for f in index.files if f.is_stale())

    # Find unindexed files
    all_files = scan_project_files(project_root, config)
    indexed_paths = {f.path for f in index.files}
    unindexed = [f for f in all_files if f not in indexed_paths]

    # Find latest session note
    agent_sessions = project_root / ".agent-sessions"
    latest_session = None
    if agent_sessions.exists():
        session_files = sorted(
            agent_sessions.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True
        )
        if session_files:
            latest_session = session_files[0].name

    # Print status
    print("📊 Meaning Index Status")
    print()
    print(f"Project: {project_name} ({project_type})")
    print(f"Version: {index.version}")
    print(f"Last Updated: {index.last_updated.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Concepts section
    if index.concepts:
        print("━" * 60)
        print(f"CONCEPTS ({len(index.concepts)})")
        print("━" * 60)
        print()
        for concept in index.concepts:
            file_count = len(concept.files)
            print(f"  {concept.name} ({file_count} files)")
            print(f"    └─ {concept.entry_point}")

            # Show intent from entry point file
            entry = index.get_file(concept.entry_point)
            if entry and entry.intent:
                intent = entry.intent[:70] + "..." if len(entry.intent) > 70 else entry.intent
                print(f'       "{intent}"')
            print()
    else:
        print("⚠️  No concepts defined")
        print()

    # Health section
    print("━" * 60)
    print("HEALTH")
    print("━" * 60)
    print()

    # Files
    status_icon = "✅" if total_files > 0 else "⚠️ "
    print(f"  {status_icon} {total_files} files indexed")

    # Needs review
    if needs_review > 0:
        print(f"  ⚠️  {needs_review} need review")
    else:
        print(f"  ✅ 0 need review")

    # Stale
    if stale > 0:
        print(f"  ⚠️  {stale} stale entries")
    else:
        print(f"  ✅ 0 stale entries")

    # Unindexed
    if unindexed:
        print(f"  ⚠️  {len(unindexed)} unindexed files")
    else:
        print(f"  ✅ 0 unindexed files")

    # Validation errors
    if result.errors:
        print(f"  ❌ {len(result.errors)} validation errors")
    else:
        print(f"  ✅ 0 validation errors")

    print()

    # Recent activity
    if latest_session:
        print("━" * 60)
        print("RECENT ACTIVITY")
        print("━" * 60)
        print()
        print(f"  Latest session: {latest_session}")
        print()

    # Quick actions
    print("━" * 60)
    print("QUICK ACTIONS")
    print("━" * 60)
    print()

    if needs_review > 0:
        print("  python -m meaning review    # Review flagged files")
    if unindexed:
        print("  python -m meaning update    # Sync with filesystem")
    if result.errors:
        print("  python -m meaning validate  # See detailed errors")

    print('  python -m meaning query "<question>"  # Semantic search')
    print()


def main() -> None:
    """Command-line interface for Meaning."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Meaning: Semantic File Index for AI Agents")
    subparsers = parser.add_subparsers(dest="command", required=True)

    status_parser = subparsers.add_parser("status", help="Show project status overview")
    status_parser.add_argument("project_root", nargs="?", default=".")

    query_parser = subparsers.add_parser("query", help="Run a semantic query")
    query_parser.add_argument("query", nargs="+")
    query_parser.add_argument("--project-root", default=".")

    validate_parser = subparsers.add_parser("validate", help="Validate the meaning index")
    validate_parser.add_argument("project_root", nargs="?", default=".")

    detect_parser = subparsers.add_parser("detect", help="Detect project type and git status")
    detect_parser.add_argument("project_root", nargs="?", default=".")

    init_parser = subparsers.add_parser("init", help="Initialize .meaning/ in a project")
    init_parser.add_argument("project_root", nargs="?", default=".")
    init_parser.add_argument("--type", dest="project_type", default=None)
    init_parser.add_argument("--limit", type=int, default=50)
    init_parser.add_argument("--install-hooks", action="store_true")
    init_parser.add_argument("--force-hooks", action="store_true")
    init_parser.add_argument(
        "--with-skills", action="store_true", help="Install Claude Code skills"
    )
    init_parser.add_argument(
        "--skip-crawl", action="store_true", help="Skip file scanning/inference"
    )

    update_parser = subparsers.add_parser("update", help="Sync index with filesystem changes")
    update_parser.add_argument("project_root", nargs="?", default=".")
    update_mode = update_parser.add_mutually_exclusive_group()
    update_mode.add_argument("--new", action="store_true")
    update_mode.add_argument("--modified", action="store_true")
    update_mode.add_argument("--deleted", action="store_true")
    update_mode.add_argument("--all", action="store_true")
    update_parser.add_argument("--re-infer", action="store_true")
    update_parser.add_argument("--dry-run", action="store_true")
    update_parser.add_argument("--threshold", type=float, default=DEFAULT_REVIEW_THRESHOLD)

    review_parser = subparsers.add_parser("review", help="Review and accept inferred metadata")
    review_parser.add_argument("project_root", nargs="?", default=".")
    review_parser.add_argument("--interactive", action="store_true")
    review_parser.add_argument("--file", dest="file_path", default=None)
    review_parser.add_argument("--dry-run", action="store_true")
    review_parser.add_argument("--threshold", type=float, default=DEFAULT_REVIEW_THRESHOLD)

    args = parser.parse_args()

    if args.command == "status":
        display_status(Path(args.project_root).resolve())
        return

    if args.command == "query":
        project_root = Path(args.project_root).resolve()
        query_str = " ".join(args.query)
        try:
            index = load_index(project_root)
            schema = load_schema(project_root)
            result = query_index(index, schema, query_str)
            display_query_results(result)
        except FileNotFoundError:
            print(f"❌ No .meaning/ directory found in {project_root}")
            print("\n💡 Initialize with: python -m meaning init")
            sys.exit(1)
        return

    if args.command == "validate":
        project_root = Path(args.project_root).resolve()
        try:
            index = load_index(project_root)
            schema = load_schema(project_root)
            config = load_config(project_root)
            result = validate_index(index, schema, config, project_root)

            print(f"Valid: {result.is_valid}")
            if result.errors:
                print(f"\nErrors ({len(result.errors)}):")
                for err in result.errors:
                    print(f"  ✗ {err}")
            if result.warnings:
                print(f"\nWarnings ({len(result.warnings)}):")
                for warn in result.warnings:
                    print(f"  ⚠ {warn}")
        except FileNotFoundError as e:
            print(f"Error: {e}")
            sys.exit(1)
        return

    if args.command == "detect":
        project_root = Path(args.project_root).resolve()
        project_type = detect_project_type(project_root)
        is_git = is_git_repo(project_root)
        print(f"Project type: {project_type}")
        print(f"Git repo: {is_git}")
        return

    if args.command == "init":
        from meaning.installer import (
            InstallOptions,
            get_package_template_dir,
            install_meaning,
            install_skills,
        )
        from meaning.meaning_inference import infer_file_metadata, infer_timestamps

        project_root = Path(args.project_root).resolve()

        # Use installer for setup
        options = InstallOptions(
            project_type=args.project_type,
            install_hooks=args.install_hooks,
            install_skills=args.with_skills,
            force_hooks=args.force_hooks,
        )

        result = install_meaning(project_root, options)

        if not result.success:
            for err in result.errors:
                print(f"❌ {err}")
            sys.exit(1)

        # Report installation results
        if result.meaning_dir_created:
            print(f"✓ Created .meaning/ with {len(result.files_copied)} files")

        if result.hooks_installed:
            print("✓ Installed Claude Code hooks")

        if result.skills_installed:
            print(f"✓ Installed {len(result.skills_installed)} skills")

        for warning in result.warnings:
            print(f"⚠️  {warning}")

        # Load the created config/schema
        index = load_index(project_root)
        schema = load_schema(project_root)
        config = load_config(project_root)

        # Skip crawl if requested
        if args.skip_crawl:
            print("✓ Skipped file scanning (use 'meaning update' to index files)")
            return

        # Scan and infer files
        all_files = scan_project_files(project_root, config)
        limit = args.limit
        if limit is not None and limit > 0:
            files_to_process = all_files[:limit]
        else:
            files_to_process = all_files

        now = infer_timestamps()
        for file_path in files_to_process:
            result_infer = infer_file_metadata(file_path, project_root, index, schema)
            entry = entry_from_inference(file_path, result_infer, DEFAULT_REVIEW_THRESHOLD, now)
            index.add_file(entry)

        save_index(project_root, index)

        validation = validate_index(index, schema, config, project_root)
        print(f"✓ Indexed {len(index.files)} files")
        if limit is not None and limit > 0 and len(all_files) > limit:
            print(
                f"⚠️  Limited to first {limit} files. Run 'meaning update' to index remaining {len(all_files) - limit} files."
            )
        print(f"⚠️  Files needing review: {len(index.files_needing_review())}")
        print(f"✓ Validation: {validation.is_valid}")
        return

    if args.command == "update":
        from meaning.meaning_inference import infer_file_metadata, infer_timestamps

        project_root = Path(args.project_root).resolve()
        if not meaning_dir_exists(project_root):
            print(f"❌ No .meaning/ directory found in {project_root}")
            print("Run 'meaning init' to create semantic index first")
            sys.exit(1)

        index = load_index(project_root)
        schema = load_schema(project_root)
        config = load_config(project_root)

        new_files = find_unindexed_files(project_root, index, config)
        modified_files = find_modified_files(project_root, index)
        deleted_files = find_deleted_files(project_root, index)

        if args.new:
            modified_files = []
            deleted_files = []
        elif args.modified:
            new_files = []
            deleted_files = []
        elif args.deleted:
            new_files = []
            modified_files = []

        if not new_files and not modified_files and not deleted_files:
            print("✓ Index is up to date")
            return

        print("📊 Changes detected:")
        print(f"   • New files: {len(new_files)}")
        print(f"   • Modified files: {len(modified_files)}")
        print(f"   • Deleted files: {len(deleted_files)}")

        if deleted_files:
            print(f"\n🗑️  Removing {len(deleted_files)} deleted files:")
            for path in deleted_files:
                print(f"   • {path}")
                if not args.dry_run:
                    index.remove_file(path)

        if new_files:
            print(f"\n✨ Adding {len(new_files)} new files:")
            now = infer_timestamps()
            for file_path in new_files:
                print(f"   • {file_path}")
                result = infer_file_metadata(file_path, project_root, index, schema)
                entry = entry_from_inference(file_path, result, args.threshold, now)
                if not args.dry_run:
                    index.add_file(entry)

        if modified_files:
            print(f"\n🔄 Processing {len(modified_files)} modified files:")
            now = infer_timestamps()
            for file_path in modified_files:
                print(f"   • {file_path}")
                entry = index.get_file(file_path)
                if entry is None:
                    continue
                if args.re_infer:
                    result = infer_file_metadata(file_path, project_root, index, schema)
                    if not args.dry_run:
                        apply_inference_to_entry(entry, result, args.threshold, config, now)
                else:
                    if not args.dry_run:
                        entry.needs_review = True
                        entry.last_verified = now

        if args.dry_run:
            print("\n⚠️  Dry run: no changes written")
            return

        save_index(project_root, index)
        validation = validate_index(index, schema, config, project_root)

        print("\n📋 Update complete")
        print(f"✓ Files in index: {len(index.files)}")
        print(f"⚠️  Files needing review: {len(index.files_needing_review())}")
        print(f"✓ Validation: {validation.is_valid}")
        return

    if args.command == "review":
        from meaning.meaning_inference import infer_file_metadata, infer_timestamps

        project_root = Path(args.project_root).resolve()
        if not meaning_dir_exists(project_root):
            print(f"❌ No .meaning/ directory found in {project_root}")
            print("Run 'meaning init' to create semantic index first")
            sys.exit(1)

        index = load_index(project_root)
        schema = load_schema(project_root)
        config = load_config(project_root)

        if args.file_path:
            entries = [index.get_file(args.file_path)]
            entries = [e for e in entries if e is not None]
        else:
            entries = index.files_needing_review()

        if not entries:
            print("✓ No files need review")
            return

        now = infer_timestamps()
        updated = 0
        skipped = 0

        for entry in entries:
            result = infer_file_metadata(entry.path, project_root, index, schema)
            if args.interactive:
                diff = preview_inference_diff(entry, result, args.threshold, config, now)
                print(f"\nFile: {entry.path}")
                if diff["intent"]:
                    print("  Intent:")
                    print(f"    - {diff['intent'][0]}")
                    print(f"    + {diff['intent'][1]}")
                if diff["tags_added"] or diff["tags_removed"]:
                    print("  Tags:")
                    for tag in diff["tags_added"]:
                        print(f"    + {tag}")
                    for tag in diff["tags_removed"]:
                        print(f"    - {tag}")
                if diff["rels_added"] or diff["rels_removed"]:
                    print("  Relationships:")
                    for rel in diff["rels_added"]:
                        print(f"    + {rel.type}:{rel.target or rel.source}")
                    for rel in diff["rels_removed"]:
                        print(f"    - {rel.type}:{rel.target or rel.source}")
                if diff["needs_review"]:
                    print("  Needs review:")
                    print(f"    - {diff['needs_review'][0]}")
                    print(f"    + {diff['needs_review'][1]}")
                if not any(
                    [
                        diff["intent"],
                        diff["tags_added"],
                        diff["tags_removed"],
                        diff["rels_added"],
                        diff["rels_removed"],
                        diff["needs_review"],
                    ]
                ):
                    print("  (no high-confidence changes)")

                choice = input("Apply changes? [y/N]: ").strip().lower()
                if choice != "y":
                    skipped += 1
                    continue

            if args.dry_run:
                changed = preview_inference_changes(entry, result, args.threshold, config, now)
            else:
                changed = apply_inference_to_entry(entry, result, args.threshold, config, now)

            if changed:
                updated += 1
            else:
                skipped += 1

        if args.dry_run:
            print("\n⚠️  Dry run: no changes written")
            print(f"✓ Would update {updated} file(s)")
            if skipped:
                print(f"⚠️  {skipped} file(s) have no high-confidence changes")
            return

        save_index(project_root, index)
        print(f"✓ Reviewed {updated} file(s)")
        if skipped:
            print(f"⚠️  {skipped} file(s) still need review")
            print("   Add docstrings/markdown summaries or use --interactive")
        remaining = len(index.files_needing_review())
        if remaining:
            print(f"⚠️  Files still needing review: {remaining}")
        return


if __name__ == "__main__":
    main()
