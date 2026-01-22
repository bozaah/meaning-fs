"""
Meaning: Semantic File Index for AI Agents

Core library for parsing, validating, and manipulating .meaning/ indexes.
"""

from __future__ import annotations

import fnmatch
import os
import re
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

    # Default to package templates
    if template_dir is None:
        template_dir = Path(__file__).parent.parent / "templates"

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


# =============================================================================
# Query Engine
# =============================================================================


@dataclass
class QueryResult:
    """Result from a semantic query."""

    files: list[FileEntry]
    explanation: str
    query_type: str


def query_index(
    index: MeaningIndex, schema: MeaningSchema, query: str
) -> QueryResult:
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
                    f
                    for f in index.files
                    if any(r.type == rel_type for r in f.relationships)
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
            "what", "where", "who", "when", "why", "how", "is", "are", "the", "a", "an",
            "do", "does", "did", "file", "files", "show", "find", "list", "me", "all",
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
        print(f"      \"{intent}\"")

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
        session_files = sorted(agent_sessions.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
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
                print(f"       \"{intent}\"")
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

    print("  python -m meaning query \"<question>\"  # Semantic search")
    print()


def main() -> None:
    """Simple CLI for testing."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m meaning_core <command> [args]")
        print("Commands: status, query, validate, detect")
        sys.exit(1)

    command = sys.argv[1]

    if command == "status":
        project_root = Path(sys.argv[2]) if len(sys.argv) > 2 else Path.cwd()
        display_status(project_root)

    elif command == "query":
        if len(sys.argv) < 3:
            print("Usage: python -m meaning_core query \"<question>\"")
            print("\nExample queries:")
            print("  \"what tests the core?\"")
            print("  \"show me all test files\"")
            print("  \"what needs review?\"")
            print("  \"files that do parsing\"")
            print("  \"what changed recently?\"")
            sys.exit(1)

        project_root = Path.cwd()
        query_str = sys.argv[2]

        try:
            index = load_index(project_root)
            schema = load_schema(project_root)
            result = query_index(index, schema, query_str)
            display_query_results(result)
        except FileNotFoundError:
            print(f"❌ No .meaning/ directory found in {project_root}")
            print(f"\n💡 Initialize with: python -m meaning init")
            sys.exit(1)

    elif command == "validate":
        project_root = Path(sys.argv[2]) if len(sys.argv) > 2 else Path.cwd()
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

    elif command == "detect":
        project_root = Path(sys.argv[2]) if len(sys.argv) > 2 else Path.cwd()
        project_type = detect_project_type(project_root)
        is_git = is_git_repo(project_root)
        print(f"Project type: {project_type}")
        print(f"Git repo: {is_git}")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
