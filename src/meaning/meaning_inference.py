"""
Meaning: Inference Engine

Automatically infer semantic metadata for files to reduce manual work.
"""

from __future__ import annotations

import ast
import configparser
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

try:  # Python 3.11+
    import tomllib
except ImportError:  # pragma: no cover - fallback for older runtimes
    tomllib = None

from meaning.default_rules import (
    ExtensionRule,
    FilenameRule,
    InferenceRules,
    PathPatternRule,
    get_default_rules,
)
from meaning.meaning_core import (
    MeaningConfig,
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

# File type groupings
CONFIG_EXTENSIONS = {".yaml", ".yml", ".json", ".toml", ".ini"}
DATA_EXTENSIONS = {".csv", ".tsv", ".parquet", ".nc", ".hdf5", ".h5", ".zarr"}
BINARY_DATA_EXTENSIONS = {".parquet", ".nc", ".hdf5", ".h5", ".zarr"}
MAX_CONFIG_BYTES = 256_000


# =============================================================================
# Data Classes: Inference Results
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
# Rule-Based Inference
# =============================================================================


def infer_from_rules(
    file_path: str,
    rules: InferenceRules | None = None,
) -> tuple[InferredIntent | None, list[InferredTag], bool]:
    """
    Apply inference rules to a file path.

    Rules are evaluated in priority order:
    1. Exact filename match (highest confidence)
    2. Path pattern match (glob patterns)
    3. Extension match (lowest confidence, fallback)

    Args:
        file_path: Relative path to the file
        rules: Inference rules to apply (defaults to built-in rules)

    Returns:
        Tuple of (intent, tags, should_fallback_to_content)
        - intent: Inferred intent if a rule matched, None otherwise
        - tags: List of inferred tags from the matching rule
        - should_fallback_to_content: Whether to also run content-based inference
    """
    if rules is None:
        rules = get_default_rules()

    path = Path(file_path)
    filename = path.name

    # 1. Try exact filename match (highest priority)
    for fn_rule in rules.exact_filenames:
        if filename == fn_rule.filename:
            intent = InferredIntent(
                intent=fn_rule.intent,
                confidence=fn_rule.confidence,
                reason=f"Exact filename match: {fn_rule.filename}",
            )
            tags = [
                InferredTag(
                    tag=t,
                    confidence=fn_rule.confidence,
                    reason=f"From filename rule: {fn_rule.filename}",
                )
                for t in fn_rule.tags
            ]
            return intent, tags, False  # No fallback for exact matches

    # 2. Try path pattern match
    for pat_rule in rules.path_patterns:
        # Use PurePath.match for proper ** glob support
        if path.match(pat_rule.pattern):
            intent = InferredIntent(
                intent=pat_rule.intent,
                confidence=pat_rule.confidence,
                reason=f"Path pattern match: {pat_rule.pattern}",
            )
            tags = [
                InferredTag(
                    tag=t,
                    confidence=pat_rule.confidence,
                    reason=f"From path pattern: {pat_rule.pattern}",
                )
                for t in pat_rule.tags
            ]
            return intent, tags, pat_rule.fallback_to_content

    # 3. Try extension match (lowest priority)
    extension = path.suffix.lower()
    if extension:
        for ext_rule in rules.extension_rules:
            if extension == ext_rule.extension.lower():
                intent = InferredIntent(
                    intent=ext_rule.intent,
                    confidence=ext_rule.confidence,
                    reason=f"Extension match: {ext_rule.extension}",
                )
                tags = [
                    InferredTag(
                        tag=t,
                        confidence=ext_rule.confidence,
                        reason=f"From extension rule: {ext_rule.extension}",
                    )
                    for t in ext_rule.tags
                ]
                return intent, tags, ext_rule.fallback_to_content

    # No rule matched
    return None, [], True  # Fallback to content analysis


def _build_template_values(file_path: str, capture_regex: str | None) -> dict[str, str]:
    path = Path(file_path)
    values = {
        "path": file_path,
        "filename": path.name,
        "stem": path.stem,
        "suffix": path.suffix.lstrip("."),
        "parent": path.parent.name if path.parent else "",
    }
    if capture_regex:
        match = re.search(capture_regex, file_path)
        if match:
            values.update({k: v for k, v in match.groupdict().items() if v is not None})
    return values


def infer_from_file_patterns(
    file_path: str,
    config: MeaningConfig | None,
) -> tuple[bool, InferredIntent | None, list[InferredTag], bool]:
    """Apply user-configured file pattern templates."""
    if not config or not config.file_patterns:
        return False, None, [], True

    path = Path(file_path)
    for pattern in config.file_patterns:
        if not pattern.pattern:
            continue
        if path.match(pattern.pattern):
            intent: InferredIntent | None = None
            reason = f"Config file pattern: {pattern.pattern}"
            values = _build_template_values(file_path, pattern.capture_regex)

            if pattern.intent_template:
                try:
                    rendered = pattern.intent_template.format(**values).strip()
                    if rendered:
                        intent = InferredIntent(
                            intent=rendered,
                            confidence=pattern.confidence,
                            reason=reason,
                        )
                except (KeyError, ValueError):
                    intent = None

            if intent is None and pattern.intent:
                intent = InferredIntent(
                    intent=pattern.intent,
                    confidence=pattern.confidence,
                    reason=reason,
                )

            tags = [
                InferredTag(tag=tag, confidence=pattern.confidence, reason=reason)
                for tag in pattern.tags
            ]

            return True, intent, tags, pattern.fallback_to_content

    return False, None, [], True


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

    # Data/file collection patterns
    if path.suffix in DATA_EXTENSIONS or "data" in parts:
        tags.append(InferredTag(tag="data", confidence=0.8, reason="Data file pattern"))
    if "data" in parts and "src" in parts:
        tags.append(InferredTag(tag="config", confidence=0.75, reason="src/*/data context"))
    if "output" in parts or "outputs" in parts or "output" in name:
        tags.append(InferredTag(tag="output", confidence=0.8, reason="Output file pattern"))
    if "reference" in parts or "ref" in parts or "reference" in name:
        tags.append(InferredTag(tag="reference", confidence=0.75, reason="Reference data pattern"))
    if "metadata" in parts or "meta" in name:
        tags.append(InferredTag(tag="metadata", confidence=0.75, reason="Metadata file pattern"))
    if path.suffix in BINARY_DATA_EXTENSIONS:
        tags.append(InferredTag(tag="binary", confidence=0.7, reason="Binary data extension"))
    if "weather" in parts or "weather" in name:
        tags.append(InferredTag(tag="weather", confidence=0.8, reason="Weather keyword in path"))
    if "disease" in parts or "disease" in name:
        tags.append(InferredTag(tag="disease", confidence=0.8, reason="Disease keyword in path"))
    if "docs" in parts and "notes" in parts:
        tags.append(InferredTag(tag="doc", confidence=0.85, reason="docs/notes context"))
        tags.append(InferredTag(tag="notes", confidence=0.8, reason="docs/notes context"))

    return tags


# =============================================================================
# Directory Context Intent Inference
# =============================================================================


def _format_context_label(label: str) -> str:
    """Format a directory name into a readable label."""
    return label.replace("_", " ").replace("-", " ").strip()


def infer_intent_from_directory_context(file_path: str) -> InferredIntent | None:
    """
    Infer intent based on directory structure for data/config/test artifacts.
    Generalized to detect context markers like 'data', 'configs' recursively.
    """
    path = Path(file_path)
    parts = path.parts
    lower_parts = [p.lower() for p in parts]

    # Map directory markers to base intents
    markers = {
        "test_files": "Test output data",
        "fixtures": "Test fixture data",
        "fixture": "Test fixture data",
        "configs": "Configuration files",
        "config": "Configuration files",
        "data": "Data files",
        "models": "Model definitions",
        "schemas": "Schema definitions",
        "migrations": "Database migrations",
    }

    # Special combined case
    if "docs" in lower_parts and "notes" in lower_parts:
        return InferredIntent(
            intent="Documentation notes and data.",
            confidence=0.75,
            reason="Directory context: docs/notes",
        )

    # Iterate backwards (deepest first) to find markers
    # We skip the filename (last part)
    for i in range(len(parts) - 2, -1, -1):
        part = lower_parts[i]

        if part in markers:
            base_intent = markers[part]
            context = None

            # Special case: 'test_files' usually organizes by subject in subdirectories
            # e.g., tests/test_files/integration/data.json -> context "integration"
            if part == "test_files":
                if i + 1 < len(parts) - 1:
                    context = _format_context_label(parts[i + 1])

            # Default: Look for context in the parent directory
            elif i > 0:
                parent = parts[i - 1]
                # Skip generic source roots as context
                if parent.lower() not in {"src", "lib", "tests", "test", "bin", "pkg"}:
                    context = _format_context_label(parent)
                # If parent is generic (e.g. src/configs), check if we can use grandparent?
                # Usually no, src/configs means global configs.

            intent = f"{base_intent} for {context}." if context else f"{base_intent}."

            return InferredIntent(
                intent=intent,
                confidence=0.8,
                reason=f"Directory context: {part}",
            )

    return None


# =============================================================================
# Config Intent Inference
# =============================================================================


def _load_config_payload(file_path: str, project_dir: Path) -> Any | None:
    path = Path(file_path)
    full_path = project_dir / file_path
    try:
        if full_path.stat().st_size > MAX_CONFIG_BYTES:
            return None
        raw = full_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None

    try:
        if path.suffix in {".yaml", ".yml"}:
            return yaml.safe_load(raw)
        if path.suffix == ".json":
            return json.loads(raw)
        if path.suffix == ".toml" and tomllib is not None:
            return tomllib.loads(raw)
        if path.suffix == ".ini":
            parser = configparser.ConfigParser()
            parser.read_string(raw)
            return {section: dict(parser.items(section)) for section in parser.sections()}
    except Exception:
        return None

    return None


def _extract_config_keys(data: Any) -> set[str]:
    if isinstance(data, dict):
        dict_keys = set(data.keys())
        return {str(k).lower() for k in dict_keys}
    if isinstance(data, list):
        list_keys: set[str] = set()
        for item in data:
            if isinstance(item, dict):
                list_keys.update(str(k).lower() for k in item.keys())
        return list_keys
    return set()


def infer_intent_from_config(file_path: str, project_dir: Path) -> InferredIntent | None:
    """Infer intent for config files using path context and content keys."""
    path = Path(file_path)
    if path.suffix not in CONFIG_EXTENSIONS:
        return None

    name = path.name.lower()
    known_config_files = {
        "mkdocs.yml": "MkDocs documentation configuration.",
        "mkdocs.yaml": "MkDocs documentation configuration.",
        "config.json": "Project configuration file.",
        "config.yaml": "Project configuration file.",
        "config.yml": "Project configuration file.",
        "settings.json": "Project settings configuration.",
        "settings.yaml": "Project settings configuration.",
        "settings.yml": "Project settings configuration.",
    }
    if name in known_config_files:
        return InferredIntent(
            intent=known_config_files[name],
            confidence=0.85,
            reason="Known config filename",
        )

    payload = _load_config_payload(file_path, project_dir)
    if payload is not None:
        keys = _extract_config_keys(payload)
        if {"dependencies", "devdependencies", "peerdependencies"} & keys:
            return InferredIntent(
                intent="Dependency configuration.",
                confidence=0.85,
                reason="Config content keys",
            )
        if {"logging", "loggers", "handlers"} & keys:
            return InferredIntent(
                intent="Logging configuration.",
                confidence=0.85,
                reason="Config content keys",
            )
        if {"database", "databases", "db"} & keys:
            return InferredIntent(
                intent="Database configuration.",
                confidence=0.85,
                reason="Config content keys",
            )
        if {"input", "inputs", "output", "outputs"} & keys:
            return InferredIntent(
                intent="Input/output parameter configuration.",
                confidence=0.8,
                reason="Config content keys",
            )
        if {"parameters", "params", "model"} & keys:
            return InferredIntent(
                intent="Model parameter configuration.",
                confidence=0.8,
                reason="Config content keys",
            )

    # Directory context (configs/data)
    # Handled by infer_intent_from_directory_context now

    return None


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
                intent = _extract_summary(_sanitize_inline_markdown(docstring), max_length)
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
                    if stripped.startswith("```"):
                        continue
                    summary_lines.append(_strip_markdown_leading(stripped))
                    # Stop at first paragraph
                    if len(" ".join(summary_lines)) > max_length:
                        break
                elif started and summary_lines:
                    break  # End of first paragraph

            if summary_lines:
                intent = _extract_summary(
                    _sanitize_inline_markdown(" ".join(summary_lines)), max_length
                )
                if intent:
                    return InferredIntent(
                        intent=intent,
                        confidence=0.8,
                        reason="Extracted from markdown first paragraph",
                    )
        except Exception:
            pass

    return None


def infer_intent_from_comment_block(
    file_path: str, project_dir: Path, max_length: int = 280
) -> InferredIntent | None:
    """
    Infer intent from a leading comment block in script-like files.

    Skips shebang and common tooling directives.
    """
    path = Path(file_path)
    if path.suffix not in {".py", ".sh", ".bash", ".zsh", ".slurm", ".sbatch", ".pbs", ".sge"}:
        return None

    try:
        full_path = project_dir / file_path
        content = full_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None

    lines = content.splitlines()
    i = 0

    # Skip leading blank lines
    while i < len(lines) and not lines[i].strip():
        i += 1

    # Skip shebang
    if i < len(lines) and lines[i].startswith("#!"):
        i += 1

    comment_lines: list[str] = []
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            if comment_lines:
                break
            i += 1
            continue

        if stripped.startswith("#"):
            text = stripped[1:].strip()
            if not text:
                i += 1
                continue
            lower = text.lower()
            if "coding:" in lower or "coding=" in lower:
                i += 1
                continue
            if lower.startswith(("pylint:", "flake8:", "ruff:", "mypy:", "pyright:", "type:")):
                i += 1
                continue
            comment_lines.append(text)
            i += 1
            continue

        break

    if not comment_lines:
        return None

    intent = _extract_summary(_sanitize_inline_markdown(" ".join(comment_lines)), max_length)
    if not intent:
        return None

    return InferredIntent(
        intent=intent,
        confidence=0.8,
        reason="Extracted from leading comment block",
    )


def _strip_markdown_leading(text: str) -> str:
    text = re.sub(r"^>\s*", "", text)
    text = re.sub(r"^[-*+]\s+", "", text)
    text = re.sub(r"^\d+\.\s+", "", text)
    return text.strip()


def _sanitize_inline_markdown(text: str) -> str:
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"__(.*?)__", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = re.sub(r"_(.*?)_", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    return text


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
        match = re.match(r"^(.+?[.!?])(?:\s|$)", truncated)
        if match:
            summary = match.group(1).strip()
        else:
            # No sentence ending found, truncate at word boundary
            summary = text[: max_length - 3].rsplit(" ", 1)[0] + "..."
    else:
        # Try to get first sentence
        match = re.match(r"^(.+?[.!?])(?:\s|$)", text)
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
    config: MeaningConfig | None = None,
    rules: InferenceRules | None = None,
) -> FileInferenceResult:
    """
    Run all inference on a single file.

    Inference is applied in priority order:
    1. Rule-based inference (filename, path pattern, extension)
    2. Content-based inference (if rule allows fallback or no rule matched)
    3. Path-based tag inference (always runs, merged with rule tags)

    Args:
        file_path: Relative path to file
        project_dir: Project root directory
        index: Current meaning index
        schema: Schema with vocabulary
        config: Optional config for file pattern templates
        rules: Optional custom inference rules (defaults to built-in)

    Returns:
        FileInferenceResult with all inferences
    """
    result = FileInferenceResult(path=file_path)

    # Step 1: Apply rule-based inference first
    rule_intent: InferredIntent | None = None
    rule_tags: list[InferredTag] = []
    fallback_to_content = True

    try:
        matched_pattern = False
        if config and config.file_patterns:
            matched_pattern, rule_intent, rule_tags, fallback_to_content = infer_from_file_patterns(
                file_path, config
            )
        if not matched_pattern:
            rule_intent, rule_tags, fallback_to_content = infer_from_rules(file_path, rules)

        # Add rule-based tags
        for tag in rule_tags:
            result.add_tag(tag.tag, tag.confidence, tag.reason)

        # Set rule-based intent (may be overridden by content if fallback)
        if rule_intent:
            result.set_intent(rule_intent.intent, rule_intent.confidence, rule_intent.reason)
            if rule_intent.confidence >= 0.9:
                fallback_to_content = False

    except Exception as e:
        result.add_error(f"Failed to apply inference rules: {e}")
        fallback_to_content = True  # On error, try content analysis

    # Step 2: Infer additional tags from path patterns (always runs)
    try:
        path_tags = infer_tags_from_path(file_path, schema)
        # Only add tags not already present from rules
        existing_tags = {t.tag for t in result.tags}
        for tag in path_tags:
            if tag.tag not in existing_tags:
                result.add_tag(tag.tag, tag.confidence, tag.reason)
    except Exception as e:
        result.add_error(f"Failed to infer tags from path: {e}")

    # Step 3: Content-based inference (if allowed by rules)
    if fallback_to_content:
        # Infer intent from content (docstring/markdown) if no rule intent or fallback
        try:
            content_intent = None
            parts = Path(file_path).parts

            # Special handling for agent sessions and audits
            if parts and parts[0] in {".agent-sessions", "audits"}:
                content_intent = infer_intent_from_path(file_path)

            if not content_intent and Path(file_path).suffix in CONFIG_EXTENSIONS:
                content_intent = infer_intent_from_config(file_path, project_dir)

            if not content_intent:
                content_intent = infer_intent_from_docstring(file_path, project_dir)

            if not content_intent:
                content_intent = infer_intent_from_comment_block(file_path, project_dir)

            if not content_intent:
                content_intent = infer_intent_from_directory_context(file_path)

            if not content_intent:
                content_intent = infer_intent_from_path(file_path)

            # Only override rule intent if content has higher confidence
            if content_intent:
                if result.intent is None:
                    result.set_intent(
                        content_intent.intent, content_intent.confidence, content_intent.reason
                    )
                elif (
                    result.intent.reason.startswith("Extension match")
                    and content_intent.confidence >= 0.8
                ):
                    result.set_intent(
                        content_intent.intent, content_intent.confidence, content_intent.reason
                    )
                elif content_intent.confidence > result.intent.confidence:
                    result.set_intent(
                        content_intent.intent, content_intent.confidence, content_intent.reason
                    )

        except Exception as e:
            result.add_error(f"Failed to infer intent from content: {e}")

    # Step 4: Infer relationships (always runs)
    try:
        test_rels = infer_test_relationships(file_path, project_dir, index)
        result.relationships.extend(test_rels)
    except Exception as e:
        result.add_error(f"Failed to infer test relationships: {e}")

    try:
        doc_rels = infer_document_relationships(file_path, project_dir, index)
        result.relationships.extend(doc_rels)
    except Exception as e:
        result.add_error(f"Failed to infer document relationships: {e}")

    try:
        import_rels = infer_import_relationships(file_path, project_dir, index)
        result.relationships.extend(import_rels)
    except Exception as e:
        result.add_error(f"Failed to infer import relationships: {e}")

    return result
