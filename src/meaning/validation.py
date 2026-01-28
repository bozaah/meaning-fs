"""
Meaning: Index validation.

This module handles validation of meaning indexes against schemas and filesystem.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from meaning.models import (
    MeaningConfig,
    MeaningIndex,
    MeaningSchema,
)


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
    collection_patterns = [c.pattern for c in index.collections if c.pattern]

    collection_match_paths: set[str] = set()
    collection_hits = {c.name: 0 for c in index.collections}

    def is_collection_path(path: str) -> bool:
        return path in collection_match_paths

    # Pre-scan filesystem to identify collection members
    for root, dirs, files in os.walk(project_root):
        # Skip hidden directories and meaning directory
        dirs[:] = [d for d in dirs if not d.startswith(".")]

        for filename in files:
            filepath = Path(root) / filename
            rel_path = str(filepath.relative_to(project_root))

            if config.is_excluded(rel_path):
                continue

            matched_collections = [
                c for c in index.collections if c.pattern and Path(rel_path).match(c.pattern)
            ]
            if matched_collections:
                collection_match_paths.add(rel_path)
                for collection in matched_collections:
                    collection_hits[collection.name] = collection_hits.get(collection.name, 0) + 1
                continue

            if rel_path not in indexed_paths:
                result.add_warning(f"File not indexed: {rel_path}")

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
            if target and target not in indexed_paths and not is_collection_path(target):
                result.add_error(f"Dangling relationship to '{target}' from: {entry.path}")

        # Check staleness
        if entry.is_stale(config.stale_threshold_days):
            result.add_warning(f"Stale entry (>{config.stale_threshold_days} days): {entry.path}")

    # Validate concepts
    for concept in index.concepts:
        for concept_file in concept.files:
            if concept_file not in indexed_paths:
                result.add_warning(
                    f"Concept '{concept.name}' references non-indexed file: {concept_file}"
                )
        if concept.entry_point and concept.entry_point not in concept.files:
            result.add_warning(
                f"Concept '{concept.name}' entry_point not in file list: {concept.entry_point}"
            )

    # Validate collections
    for collection in index.collections:
        if not collection.pattern:
            result.add_warning(f"Collection '{collection.name}' is missing a pattern")

        if config.require_intent and (
            not collection.intent or collection.intent.startswith("[NEEDS REVIEW]")
        ):
            result.add_warning(f"Collection missing proper intent: {collection.name}")

        if len(collection.intent) > config.max_intent_length:
            result.add_warning(
                f"Collection intent exceeds max length ({len(collection.intent)} > {config.max_intent_length}): {collection.name}"
            )

        if config.require_tags and not collection.tags:
            result.add_warning(f"Collection missing tags: {collection.name}")

        if config.warn_on_unknown_tags:
            for tag in collection.tags:
                if not schema.is_valid_tag(tag):
                    result.add_warning(f"Unknown tag '{tag}' on collection: {collection.name}")

        for rel in collection.relationships:
            if not schema.is_valid_relationship_type(rel.type):
                result.add_warning(
                    f"Unknown relationship type '{rel.type}' on collection: {collection.name}"
                )
            target = rel.target or rel.source
            if target and target not in indexed_paths and not is_collection_path(target):
                result.add_error(
                    f"Dangling relationship to '{target}' from collection: {collection.name}"
                )

        if collection_hits.get(collection.name, 0) == 0:
            result.add_warning(
                f"Collection '{collection.name}' pattern matched no files: {collection.pattern}"
            )

    return result
