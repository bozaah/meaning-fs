"""
Meaning: Core data models.

This module contains all dataclasses for the meaning package:
- Relationship
- FileEntry
- Concept
- MeaningIndex
- RelationshipType
- MeaningSchema
- MeaningConfig
"""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from meaning.constants import (
    DEFAULT_MAX_INTENT_LENGTH,
    DEFAULT_STALE_THRESHOLD_DAYS,
    VALID_STATUSES,
    VERSION,
)


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
class Collection:
    """A grouped collection of files described by a glob pattern."""

    name: str
    pattern: str
    intent: str
    tags: list[str] = field(default_factory=list)
    member_intent_template: str | None = None
    relationships: list[Relationship] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "name": self.name,
            "pattern": self.pattern,
            "intent": self.intent,
            "tags": self.tags,
        }
        if self.member_intent_template:
            d["member_intent_template"] = self.member_intent_template
        if self.relationships:
            d["relationships"] = [r.to_dict() for r in self.relationships]
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Collection:
        relationships = [Relationship.from_dict(r) for r in data.get("relationships", [])]
        return cls(
            name=data["name"],
            pattern=data.get("pattern", ""),
            intent=data.get("intent", ""),
            tags=data.get("tags", []),
            member_intent_template=data.get("member_intent_template"),
            relationships=relationships,
        )


@dataclass
class MeaningIndex:
    """The complete semantic index for a project."""

    version: str = VERSION
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    concepts: list[Concept] = field(default_factory=list)
    collections: list[Collection] = field(default_factory=list)
    files: list[FileEntry] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "generated_at": self.generated_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "concepts": [c.to_dict() for c in self.concepts],
            "collections": [c.to_dict() for c in self.collections],
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
        collections = [Collection.from_dict(c) for c in data.get("collections", [])]
        files = [FileEntry.from_dict(f) for f in data.get("files", [])]

        return cls(
            version=data.get("version", VERSION),
            generated_at=generated_at,
            last_updated=last_updated,
            concepts=concepts,
            collections=collections,
            files=files,
        )

    def get_file(self, path: str) -> FileEntry | None:
        """Find a file entry by path."""
        for f in self.files:
            if f.path == path:
                return f
        return None

    def is_collected(self, path: str) -> bool:
        """Check if a path is covered by any collection pattern."""
        candidate = Path(path)
        for collection in self.collections:
            if collection.pattern and candidate.match(collection.pattern):
                return True
        return False

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
class FilePattern:
    """Configurable file pattern inference rule."""

    pattern: str
    intent: str | None = None
    intent_template: str | None = None
    tags: list[str] = field(default_factory=list)
    confidence: float = 0.85
    fallback_to_content: bool = False
    capture_regex: str | None = None
    auto_accept: bool = False

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "pattern": self.pattern,
            "tags": self.tags,
            "confidence": self.confidence,
            "fallback_to_content": self.fallback_to_content,
            "auto_accept": self.auto_accept,
        }
        if self.intent:
            data["intent"] = self.intent
        if self.intent_template:
            data["intent_template"] = self.intent_template
        if self.capture_regex:
            data["capture_regex"] = self.capture_regex
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FilePattern:
        confidence = float(data.get("confidence", 0.85))
        auto_accept = bool(data.get("auto_accept", False))
        if auto_accept and "confidence" not in data:
            confidence = 0.95
        return cls(
            pattern=str(data.get("pattern", "")),
            intent=data.get("intent"),
            intent_template=data.get("intent_template"),
            tags=list(data.get("tags", [])),
            confidence=confidence,
            fallback_to_content=bool(data.get("fallback_to_content", False)),
            capture_regex=data.get("capture_regex"),
            auto_accept=auto_accept,
        )


@dataclass
class MeaningConfig:
    """Project settings and exclusion patterns."""

    version: str = VERSION
    exclude_patterns: list[str] = field(default_factory=list)
    exclude_paths: list[str] = field(default_factory=list)
    include_paths: list[str] = field(default_factory=list)
    file_patterns: list[FilePattern] = field(default_factory=list)
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
            "inference": {
                "file_patterns": [pattern.to_dict() for pattern in self.file_patterns],
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
        inference = data.get("inference", {})
        settings = data.get("settings", {})

        return cls(
            version=data.get("version", VERSION),
            exclude_patterns=exclude.get("patterns", []),
            exclude_paths=exclude.get("paths", []),
            include_paths=include.get("paths", []),
            file_patterns=[
                FilePattern.from_dict(item) for item in inference.get("file_patterns", [])
            ],
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
