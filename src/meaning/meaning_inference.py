"""
Meaning: Inference Engine

Automatically infer semantic metadata for files to reduce manual work.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from meaning.meaning_core import (
    FileEntry,
    MeaningIndex,
    MeaningSchema,
    Relationship,
)

# =============================================================================
# Constants
# =============================================================================

# Confidence thresholds
CONFIDENCE_HIGH = 0.8
CONFIDENCE_MEDIUM = 0.5
CONFIDENCE_LOW = 0.3


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class InferredRelationship:
    """A suggested relationship with confidence score."""

    relationship: Relationship
    confidence: float
    reason: str  # Why we inferred this


@dataclass
class InferredTag:
    """A suggested tag with confidence score."""

    tag: str
    confidence: float
    reason: str


@dataclass
class InferredIntent:
    """A suggested intent description with confidence score."""

    intent: str
    confidence: float
    reason: str  # How we generated it


@dataclass
class FileInferenceResult:
    """Result of running inference on a single file."""

    path: str
    relationships: list[InferredRelationship] = field(default_factory=list)
    tags: list[InferredTag] = field(default_factory=list)
    intent: InferredIntent | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add_relationship(self, rel_type: str, target: str, confidence: float, reason: str) -> None:
        """Add an inferred relationship."""
        rel = Relationship(type=rel_type, target=target)
        inferred = InferredRelationship(relationship=rel, confidence=confidence, reason=reason)
        self.relationships.append(inferred)

    def add_tag(self, tag: str, confidence: float, reason: str) -> None:
        """Add an inferred tag."""
        self.tags.append(InferredTag(tag=tag, confidence=confidence, reason=reason))

    def set_intent(self, intent: str, confidence: float, reason: str) -> None:
        """Set the inferred intent."""
        self.intent = InferredIntent(intent=intent, confidence=confidence, reason=reason)

    def add_error(self, message: str) -> None:
        """Add an error message."""
        self.errors.append(message)

    def add_warning(self, message: str) -> None:
        """Add a warning message."""
        self.warnings.append(message)


@dataclass
class ConceptSuggestion:
    """A suggested concept grouping."""

    name: str
    description: str
    files: list[str]
    entry_point: str
    confidence: float
    reason: str


# =============================================================================
# Timestamp Inference (Trivial)
# =============================================================================


def infer_timestamps() -> datetime:
    """
    Generate current timestamp.

    Returns:
        Current UTC timestamp.
    """
    return datetime.now(timezone.utc)


# =============================================================================
# Tag Inference from File Paths
# =============================================================================


def infer_tags_from_path(file_path: str, schema: MeaningSchema) -> list[InferredTag]:
    """
    Infer tags based on file path patterns and naming conventions.

    Args:
        file_path: Relative path to the file
        schema: Schema with tag vocabulary

    Returns:
        List of inferred tags with confidence scores
    """
    tags: list[InferredTag] = []
    path = Path(file_path)
    name = path.name.lower()
    parts = path.parts

    # File extension patterns
    if path.suffix == ".py":
        tags.append(InferredTag(tag="module", confidence=0.9, reason="Python file"))
    elif path.suffix == ".md":
        tags.append(InferredTag(tag="doc", confidence=0.95, reason="Markdown file"))
    elif path.suffix in {".yaml", ".yml", ".toml", ".json", ".ini", ".conf"}:
        tags.append(InferredTag(tag="config", confidence=0.9, reason="Config file"))

    # Test files
    if name.startswith("test_") or "test" in parts:
        tags.append(InferredTag(tag="test", confidence=0.95, reason="Test file naming pattern"))

    # Fixture files
    if "fixture" in name.lower() or "fixtures" in parts:
        tags.append(InferredTag(tag="fixture", confidence=0.9, reason="Fixture directory/name"))

    # Documentation patterns
    if name in {"readme.md", "changelog.md", "contributing.md", "license.md"}:
        tags.append(InferredTag(tag="doc", confidence=0.95, reason="Standard doc file"))
    if name in {"readme.md"}:
        tags.append(InferredTag(tag="overview", confidence=0.9, reason="README file"))

    # Core/main files
    if name in {"main.py", "__main__.py", "core.py", "index.py"}:
        tags.append(InferredTag(tag="core", confidence=0.8, reason="Main/core file name"))

    # API patterns
    if "api" in parts or "api" in name:
        tags.append(InferredTag(tag="api", confidence=0.85, reason="'api' in path or filename"))

    # CLI patterns
    if "cli" in parts or "cli" in name or name in {"cli.py"}:
        tags.append(InferredTag(tag="cli", confidence=0.85, reason="'cli' in path or filename"))

    # Utils
    if "util" in name or "utils" in parts or "helper" in name:
        tags.append(InferredTag(tag="util", confidence=0.8, reason="Utility/helper file pattern"))

    # Models
    if "model" in name.lower() or "models" in parts:
        tags.append(InferredTag(tag="model", confidence=0.85, reason="Model file/directory"))

    # Schema
    if "schema" in name.lower() or "schemas" in parts:
        tags.append(InferredTag(tag="schema", confidence=0.85, reason="Schema file/directory"))

    # Controller/service/repository patterns
    if "controller" in name:
        tags.append(InferredTag(tag="controller", confidence=0.9, reason="Controller in name"))
    if "service" in name:
        tags.append(InferredTag(tag="service", confidence=0.9, reason="Service in name"))
    if "repository" in name or "repo" in name:
        tags.append(InferredTag(tag="repository", confidence=0.85, reason="Repository in name"))

    # Validation
    if "validat" in name:
        tags.append(InferredTag(tag="validation", confidence=0.85, reason="Validation in name"))

    # Parsing
    if "pars" in name:
        tags.append(InferredTag(tag="parsing", confidence=0.85, reason="Parser/parsing in name"))

    return tags


# =============================================================================
# Test Relationship Inference
# =============================================================================


def infer_test_relationships(
    file_path: str, project_dir: Path, index: MeaningIndex
) -> list[InferredRelationship]:
    """
    Infer 'tests' relationships based on file naming conventions.

    Matches test_foo.py to foo.py, tests/test_bar.py to src/bar.py, etc.

    Args:
        file_path: Path to the test file
        project_dir: Project root directory
        index: Current meaning index

    Returns:
        List of inferred test relationships
    """
    relationships: list[InferredRelationship] = []
    path = Path(file_path)

    # Only process test files
    if not path.name.startswith("test_"):
        return relationships

    # Extract the module name: test_foo.py -> foo.py
    module_name = path.name.replace("test_", "", 1)

    # Search for matching source files in common locations
    search_patterns = [
        f"src/{module_name}",
        f"lib/{module_name}",
        module_name,
        f"app/{module_name}",
        f"pkg/{module_name}",
    ]

    # Also try searching in subdirectories (e.g., test_client.py -> src/api/client.py)
    for entry in index.files:
        if entry.path.endswith(f"/{module_name}") or entry.path.endswith(f"\\{module_name}"):
            relationships.append(
                InferredRelationship(
                    relationship=Relationship(type="tests", target=entry.path),
                    confidence=0.85,
                    reason=f"Test file naming convention: {path.name} tests {entry.path}",
                )
            )
            return relationships

    for pattern in search_patterns:
        if index.get_file(pattern) is not None:
            relationships.append(
                InferredRelationship(
                    relationship=Relationship(type="tests", target=pattern),
                    confidence=0.9,
                    reason=f"Test file naming convention: {path.name} tests {pattern}",
                )
            )
            break  # Only add one relationship

    return relationships


# =============================================================================
# Markdown Document Relationship Inference
# =============================================================================


def infer_document_relationships(
    file_path: str, project_dir: Path, index: MeaningIndex
) -> list[InferredRelationship]:
    """
    Infer 'documents' relationships by parsing markdown file references.

    Looks for patterns like:
    - [link](path/to/file.py)
    - See `src/module.py`
    - Links to files in the project

    Args:
        file_path: Path to the markdown file
        project_dir: Project root directory
        index: Current meaning index

    Returns:
        List of inferred document relationships
    """
    relationships: list[InferredRelationship] = []
    path = Path(file_path)

    # Only process markdown files
    if path.suffix not in {".md", ".markdown"}:
        return relationships

    try:
        full_path = project_dir / file_path
        content = full_path.read_text(encoding="utf-8")
    except Exception:
        return relationships  # Skip files we can't read

    # Pattern 1: Markdown links [text](path)
    link_pattern = r"\[([^\]]+)\]\(([^\)]+)\)"
    for match in re.finditer(link_pattern, content):
        target = match.group(2)
        # Filter out external URLs and anchors
        if not target.startswith(("http://", "https://", "#", "mailto:")):
            # Normalize path
            clean_target = target.split("#")[0]  # Remove anchors
            if clean_target and index.get_file(clean_target) is not None:
                relationships.append(
                    InferredRelationship(
                        relationship=Relationship(type="documents", target=clean_target),
                        confidence=0.85,
                        reason=f"Markdown link to file: [{match.group(1)}]({clean_target})",
                    )
                )

    # Pattern 2: Inline code references `path/to/file.ext`
    code_pattern = r"`([a-zA-Z0-9_/.-]+\.(py|yaml|yml|json|js|ts|md))`"
    for match in re.finditer(code_pattern, content):
        target = match.group(1)
        if index.get_file(target) is not None:
            # Check if already added
            if not any(r.relationship.target == target for r in relationships):
                relationships.append(
                    InferredRelationship(
                        relationship=Relationship(type="documents", target=target),
                        confidence=0.75,
                        reason=f"Inline code reference: `{target}`",
                    )
                )

    return relationships


# =============================================================================
# Python Import Relationship Inference
# =============================================================================


def infer_import_relationships(
    file_path: str, project_dir: Path, index: MeaningIndex
) -> list[InferredRelationship]:
    """
    Infer 'imports' relationships by parsing Python import statements.

    Args:
        file_path: Path to the Python file
        project_dir: Project root directory
        index: Current meaning index

    Returns:
        List of inferred import relationships
    """
    relationships: list[InferredRelationship] = []
    path = Path(file_path)

    # Only process Python files
    if path.suffix != ".py":
        return relationships

    try:
        full_path = project_dir / file_path
        content = full_path.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(file_path))
    except Exception:
        return relationships  # Skip files we can't parse

    # Extract import statements
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_path = _module_to_path(alias.name, project_dir, index)
                if module_path:
                    relationships.append(
                        InferredRelationship(
                            relationship=Relationship(type="imports", target=module_path),
                            confidence=0.95,
                            reason=f"Direct import: import {alias.name}",
                        )
                    )
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                module_path = _module_to_path(node.module, project_dir, index)
                if module_path:
                    relationships.append(
                        InferredRelationship(
                            relationship=Relationship(type="imports", target=module_path),
                            confidence=0.95,
                            reason=f"From import: from {node.module} import ...",
                        )
                    )

    return relationships


def _module_to_path(module_name: str, project_dir: Path, index: MeaningIndex) -> str | None:
    """
    Convert a Python module name to a file path.

    Args:
        module_name: Python module name (e.g., 'meaning_core')
        project_dir: Project root directory
        index: Current meaning index

    Returns:
        File path if found in index, None otherwise
    """
    # Try common patterns
    patterns = [
        f"src/{module_name}.py",
        f"lib/{module_name}.py",
        f"{module_name}.py",
        f"src/{module_name}/__init__.py",
        f"lib/{module_name}/__init__.py",
        f"{module_name}/__init__.py",
    ]

    # Handle dotted imports (e.g., foo.bar.baz)
    if "." in module_name:
        parts = module_name.split(".")
        patterns.extend(
            [
                f"src/{'/'.join(parts)}.py",
                f"lib/{'/'.join(parts)}.py",
                f"{'/'.join(parts)}.py",
            ]
        )

    for pattern in patterns:
        if index.get_file(pattern) is not None:
            return pattern

    return None


# =============================================================================
# Intent Inference from Docstrings
# =============================================================================


def infer_intent_from_docstring(
    file_path: str, project_dir: Path, max_length: int = 280
) -> InferredIntent | None:
    """
    Infer intent description from file docstrings.

    Extracts the first sentence or summary line from module docstrings.

    Args:
        file_path: Path to the file
        project_dir: Project root directory
        max_length: Maximum intent length

    Returns:
        Inferred intent or None if can't extract
    """
    path = Path(file_path)

    # Python files
    if path.suffix == ".py":
        try:
            full_path = project_dir / file_path
            content = full_path.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(file_path))

            # Get module docstring
            docstring = ast.get_docstring(tree)
            if docstring:
                # Extract first meaningful line/sentence
                intent = _extract_summary(docstring, max_length)
                if intent:
                    return InferredIntent(
                        intent=intent,
                        confidence=0.8,
                        reason="Extracted from module docstring",
                    )
        except Exception:
            pass

    # Markdown files - use first paragraph after title
    elif path.suffix in {".md", ".markdown"}:
        try:
            full_path = project_dir / file_path
            content = full_path.read_text(encoding="utf-8")

            # Skip title (first # line)
            lines = content.split("\n")
            started = False
            summary_lines = []

            for line in lines:
                stripped = line.strip()
                if not started and stripped.startswith("#"):
                    started = True
                    continue
                if started and stripped and not stripped.startswith("#"):
                    summary_lines.append(stripped)
                    # Stop at first paragraph
                    if len(" ".join(summary_lines)) > max_length:
                        break
                elif started and summary_lines:
                    break  # End of first paragraph

            if summary_lines:
                intent = _extract_summary(" ".join(summary_lines), max_length)
                if intent:
                    return InferredIntent(
                        intent=intent,
                        confidence=0.8,
                        reason="Extracted from markdown first paragraph",
                    )
        except Exception:
            pass

    return None


def infer_intent_from_path(file_path: str) -> InferredIntent | None:
    """
    Infer intent from well-known filenames and project-specific paths.

    This is deterministic and intended for common documentation and template paths.
    """
    path = Path(file_path)
    name = path.name
    lower_name = name.lower()
    parts = path.parts

    known_files = {
        "readme.md": "Project overview and quick start guide.",
        "changelog.md": "Project change history and release notes.",
        "quickstart.md": "Quick start guide for getting started.",
        "license": "Project license text.",
    }

    if lower_name in known_files:
        return InferredIntent(
            intent=known_files[lower_name],
            confidence=0.85,
            reason="Known documentation filename",
        )

    if parts and parts[0] == ".agent-sessions":
        if lower_name == "readme.md":
            return InferredIntent(
                intent="Guide to agent session notes and continuity.",
                confidence=0.85,
                reason="Agent sessions documentation",
            )
        stem = path.stem
        match = re.match(r"\\d{4}-\\d{2}-\\d{2}-(.+)", stem)
        slug = match.group(1) if match else stem
        title = slug.replace("-", " ").strip()
        return InferredIntent(
            intent=f"Agent session note: {title}.",
            confidence=0.85,
            reason="Agent session note filename",
        )

    if parts and parts[0] == "audits":
        stem = path.stem
        match = re.match(r"audit-report-(\\d{4}-\\d{2}-\\d{2})", stem)
        if match:
            date = match.group(1)
            return InferredIntent(
                intent=f"Audit report for {date}.",
                confidence=0.85,
                reason="Audit report filename",
            )

    if parts[:3] == ("src", "meaning", "templates"):
        if len(parts) >= 4 and parts[3] == "schema" and path.suffix in {".yaml", ".yml"}:
            project_type = path.stem
            return InferredIntent(
                intent=f"Schema template for {project_type} projects.",
                confidence=0.85,
                reason="Template schema path",
            )
        if name == "config.yaml":
            return InferredIntent(
                intent="Default configuration template for Meaning projects.",
                confidence=0.85,
                reason="Template config path",
            )
        if name == "hooks.json":
            return InferredIntent(
                intent="Default Claude Code hooks template for Meaning projects.",
                confidence=0.85,
                reason="Template hooks path",
            )
        if len(parts) >= 4 and parts[3] == "scripts" and path.suffix == ".sh":
            return InferredIntent(
                intent=f"Hook script template for Meaning: {path.stem}.",
                confidence=0.85,
                reason="Template scripts path",
            )

    if parts and parts[0] == "scripts" and path.suffix == ".sh":
        return InferredIntent(
            intent=f"Meaning hook script: {path.stem}.",
            confidence=0.85,
            reason="Project scripts path",
        )

    return None


def _extract_summary(text: str, max_length: int) -> str | None:
    """
    Extract a summary sentence from text.

    Args:
        text: Source text
        max_length: Maximum length

    Returns:
        Summary string or None
    """
    # Clean up whitespace
    text = " ".join(text.split())

    # Truncate first if too long
    if len(text) > max_length:
        # Try to get first sentence within max_length
        truncated = text[:max_length]
        match = re.match(r"^([^.!?]+[.!?])", truncated)
        if match:
            summary = match.group(1).strip()
        else:
            # No sentence ending found, truncate at word boundary
            summary = text[: max_length - 3].rsplit(" ", 1)[0] + "..."
    else:
        # Try to get first sentence
        match = re.match(r"^([^.!?]+[.!?])", text)
        if match:
            summary = match.group(1).strip()
        else:
            # No sentence ending, take first line or use as-is
            summary = text.split("\n")[0].strip()

    return summary if summary else None


# =============================================================================
# Main Inference Function
# =============================================================================


def infer_file_metadata(
    file_path: str,
    project_dir: Path,
    index: MeaningIndex,
    schema: MeaningSchema,
) -> FileInferenceResult:
    """
    Run all inference on a single file.

    Args:
        file_path: Relative path to file
        project_dir: Project root directory
        index: Current meaning index
        schema: Schema with vocabulary

    Returns:
        FileInferenceResult with all inferences
    """
    result = FileInferenceResult(path=file_path)

    # Infer tags from path
    try:
        tags = infer_tags_from_path(file_path, schema)
        for tag in tags:
            result.add_tag(tag.tag, tag.confidence, tag.reason)
    except Exception as e:
        result.add_error(f"Failed to infer tags: {e}")

    # Infer test relationships
    try:
        test_rels = infer_test_relationships(file_path, project_dir, index)
        result.relationships.extend(test_rels)
    except Exception as e:
        result.add_error(f"Failed to infer test relationships: {e}")

    # Infer document relationships
    try:
        doc_rels = infer_document_relationships(file_path, project_dir, index)
        result.relationships.extend(doc_rels)
    except Exception as e:
        result.add_error(f"Failed to infer document relationships: {e}")

    # Infer import relationships
    try:
        import_rels = infer_import_relationships(file_path, project_dir, index)
        result.relationships.extend(import_rels)
    except Exception as e:
        result.add_error(f"Failed to infer import relationships: {e}")

    # Infer intent
    try:
        intent = infer_intent_from_docstring(file_path, project_dir)
        if not intent:
            intent = infer_intent_from_path(file_path)
        if intent:
            result.set_intent(intent.intent, intent.confidence, intent.reason)
    except Exception as e:
        result.add_error(f"Failed to infer intent: {e}")

    return result
