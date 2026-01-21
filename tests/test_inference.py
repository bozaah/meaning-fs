"""
Tests for meaning_inference.py

Tests all inference functions with realistic examples.
"""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from meaning_core import (
    Concept,
    FileEntry,
    MeaningIndex,
    MeaningSchema,
    Relationship,
    RelationshipType,
)
from meaning_inference import (
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    CONFIDENCE_MEDIUM,
    ConceptSuggestion,
    FileInferenceResult,
    InferredIntent,
    InferredRelationship,
    InferredTag,
    infer_document_relationships,
    infer_file_metadata,
    infer_import_relationships,
    infer_intent_from_docstring,
    infer_tags_from_path,
    infer_test_relationships,
    infer_timestamps,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def schema():
    """Create a basic schema for testing."""
    return MeaningSchema(
        version="0.1",
        project_type="python",
        relationship_types=[
            RelationshipType(name="imports", description="Imports", direction="source_to_target"),
            RelationshipType(name="tests", description="Tests", direction="source_to_target"),
            RelationshipType(
                name="documents", description="Documents", direction="source_to_target"
            ),
        ],
        tag_vocabulary={
            "domain": ["api", "core", "database"],
            "concern": ["parsing", "validation"],
            "layer": ["module", "test", "doc", "util", "controller", "service", "model"],
            "doc_type": ["overview", "spec"],
        },
        custom_prefix="x-",
        statuses=["active", "draft", "deprecated"],
    )


@pytest.fixture
def index():
    """Create a basic index for testing."""
    return MeaningIndex(
        version="0.1",
        generated_at=datetime.now(timezone.utc),
        last_updated=datetime.now(timezone.utc),
        concepts=[],
        files=[
            FileEntry(
                path="src/api/client.py",
                intent="API client implementation",
                tags=["api", "core"],
                status="active",
            ),
            FileEntry(
                path="src/models/user.py",
                intent="User model",
                tags=["model"],
                status="active",
            ),
            FileEntry(
                path="tests/test_client.py",
                intent="Tests for API client",
                tags=["test"],
                status="active",
            ),
            FileEntry(
                path="README.md",
                intent="Project overview",
                tags=["doc", "overview"],
                status="active",
            ),
        ],
    )


# =============================================================================
# Test Timestamp Inference
# =============================================================================


def test_infer_timestamps():
    """Test timestamp generation returns current time."""
    before = datetime.now(timezone.utc)
    result = infer_timestamps()
    after = datetime.now(timezone.utc)

    assert isinstance(result, datetime)
    assert before <= result <= after
    assert result.tzinfo == timezone.utc


# =============================================================================
# Test Tag Inference from Paths
# =============================================================================


def test_infer_tags_python_file(schema):
    """Test tag inference for Python files."""
    tags = infer_tags_from_path("src/parser.py", schema)
    tag_names = [t.tag for t in tags]

    assert "module" in tag_names
    tag = next(t for t in tags if t.tag == "module")
    assert tag.confidence >= 0.8
    assert "Python file" in tag.reason


def test_infer_tags_test_file(schema):
    """Test tag inference for test files."""
    tags = infer_tags_from_path("tests/test_parser.py", schema)
    tag_names = [t.tag for t in tags]

    assert "test" in tag_names
    assert "module" in tag_names


def test_infer_tags_markdown_file(schema):
    """Test tag inference for markdown files."""
    tags = infer_tags_from_path("docs/api.md", schema)
    tag_names = [t.tag for t in tags]

    assert "doc" in tag_names
    tag = next(t for t in tags if t.tag == "doc")
    assert tag.confidence >= 0.9


def test_infer_tags_readme(schema):
    """Test tag inference for README."""
    tags = infer_tags_from_path("README.md", schema)
    tag_names = [t.tag for t in tags]

    assert "doc" in tag_names
    assert "overview" in tag_names


def test_infer_tags_config_file(schema):
    """Test tag inference for config files."""
    for ext in [".yaml", ".yml", ".json", ".toml"]:
        tags = infer_tags_from_path(f"config/settings{ext}", schema)
        tag_names = [t.tag for t in tags]
        assert "config" in tag_names


def test_infer_tags_fixture_file(schema):
    """Test tag inference for fixture files."""
    tags = infer_tags_from_path("tests/fixtures/sample_data.json", schema)
    tag_names = [t.tag for t in tags]

    assert "fixture" in tag_names


def test_infer_tags_api_file(schema):
    """Test tag inference for API files."""
    tags = infer_tags_from_path("src/api/endpoints.py", schema)
    tag_names = [t.tag for t in tags]

    assert "api" in tag_names
    assert "module" in tag_names


def test_infer_tags_model_file(schema):
    """Test tag inference for model files."""
    tags = infer_tags_from_path("src/models/user.py", schema)
    tag_names = [t.tag for t in tags]

    assert "model" in tag_names


def test_infer_tags_util_file(schema):
    """Test tag inference for utility files."""
    tags = infer_tags_from_path("src/utils/helpers.py", schema)
    tag_names = [t.tag for t in tags]

    assert "util" in tag_names


def test_infer_tags_validation_file(schema):
    """Test tag inference for validation files."""
    tags = infer_tags_from_path("src/validators.py", schema)
    tag_names = [t.tag for t in tags]

    assert "validation" in tag_names


def test_infer_tags_parser_file(schema):
    """Test tag inference for parser files."""
    tags = infer_tags_from_path("src/parsers.py", schema)
    tag_names = [t.tag for t in tags]

    assert "parsing" in tag_names


# =============================================================================
# Test Test Relationship Inference
# =============================================================================


def test_infer_test_relationships_matching_file(index):
    """Test inferring test relationship when source file exists."""
    rels = infer_test_relationships("tests/test_client.py", Path("."), index)

    assert len(rels) == 1
    assert rels[0].relationship.type == "tests"
    assert rels[0].relationship.target == "src/api/client.py"
    assert rels[0].confidence >= 0.8
    assert "naming convention" in rels[0].reason.lower()


def test_infer_test_relationships_no_match(index):
    """Test inferring test relationship when source doesn't exist."""
    rels = infer_test_relationships("tests/test_nonexistent.py", Path("."), index)

    assert len(rels) == 0


def test_infer_test_relationships_non_test_file(index):
    """Test that non-test files don't infer test relationships."""
    rels = infer_test_relationships("src/api/client.py", Path("."), index)

    assert len(rels) == 0


# =============================================================================
# Test Document Relationship Inference
# =============================================================================


def test_infer_document_relationships_markdown_links(index, tmp_path):
    """Test inferring document relationships from markdown links."""
    # Create a markdown file with links
    md_file = tmp_path / "guide.md"
    md_file.write_text(
        """
# Guide

This guide explains [the API client](src/api/client.py) and [models](src/models/user.py).

See also: https://example.com (external link)
"""
    )

    # Add the markdown file to index
    index.add_file(FileEntry(path="guide.md", intent="Guide", tags=["doc"], status="active"))

    rels = infer_document_relationships("guide.md", tmp_path, index)

    assert len(rels) == 2
    targets = [r.relationship.target for r in rels]
    assert "src/api/client.py" in targets
    assert "src/models/user.py" in targets


def test_infer_document_relationships_inline_code(index, tmp_path):
    """Test inferring document relationships from inline code references."""
    md_file = tmp_path / "docs.md"
    md_file.write_text(
        """
# Documentation

The main implementation is in `src/api/client.py`.
"""
    )

    index.add_file(FileEntry(path="docs.md", intent="Docs", tags=["doc"], status="active"))

    rels = infer_document_relationships("docs.md", tmp_path, index)

    assert len(rels) >= 1
    assert any(r.relationship.target == "src/api/client.py" for r in rels)


def test_infer_document_relationships_non_markdown(index, tmp_path):
    """Test that non-markdown files don't infer document relationships."""
    rels = infer_document_relationships("src/api/client.py", tmp_path, index)

    assert len(rels) == 0


def test_infer_document_relationships_missing_file(index, tmp_path):
    """Test graceful handling of missing files."""
    rels = infer_document_relationships("nonexistent.md", tmp_path, index)

    assert len(rels) == 0


# =============================================================================
# Test Import Relationship Inference
# =============================================================================


def test_infer_import_relationships_direct_import(index, tmp_path):
    """Test inferring import relationships from direct imports."""
    py_file = tmp_path / "src" / "test.py"
    py_file.parent.mkdir(parents=True, exist_ok=True)
    py_file.write_text(
        """
import meaning_core
from pathlib import Path

def main():
    pass
"""
    )

    # Add meaning_core to index
    index.add_file(
        FileEntry(
            path="src/meaning_core.py",
            intent="Core module",
            tags=["module"],
            status="active",
        )
    )

    rels = infer_import_relationships("src/test.py", tmp_path, index)

    # Should find meaning_core (Path is stdlib, won't be in index)
    assert len(rels) >= 1
    assert any(r.relationship.target == "src/meaning_core.py" for r in rels)
    assert all(r.confidence >= 0.9 for r in rels)


def test_infer_import_relationships_from_import(index, tmp_path):
    """Test inferring import relationships from 'from' imports."""
    py_file = tmp_path / "src" / "main.py"
    py_file.parent.mkdir(parents=True, exist_ok=True)
    py_file.write_text(
        """
from api.client import APIClient
from models.user import User
"""
    )

    # Add modules to index
    index.add_file(
        FileEntry(path="src/api/client.py", intent="API client", tags=["api"], status="active")
    )

    rels = infer_import_relationships("src/main.py", tmp_path, index)

    # Should find api.client
    assert len(rels) >= 1


def test_infer_import_relationships_syntax_error(index, tmp_path):
    """Test graceful handling of syntax errors."""
    py_file = tmp_path / "src" / "broken.py"
    py_file.parent.mkdir(parents=True, exist_ok=True)
    py_file.write_text(
        """
def broken(
    # Missing closing parenthesis
"""
    )

    rels = infer_import_relationships("src/broken.py", tmp_path, index)

    # Should return empty list, not crash
    assert len(rels) == 0


def test_infer_import_relationships_non_python(index, tmp_path):
    """Test that non-Python files don't infer import relationships."""
    rels = infer_import_relationships("README.md", tmp_path, index)

    assert len(rels) == 0


# =============================================================================
# Test Intent Inference
# =============================================================================


def test_infer_intent_from_python_docstring(tmp_path):
    """Test inferring intent from Python module docstring."""
    py_file = tmp_path / "module.py"
    py_file.write_text(
        '''"""
This is a module for parsing API responses.

It handles JSON and XML formats.
"""

def parse():
    pass
'''
    )

    intent = infer_intent_from_docstring("module.py", tmp_path)

    assert intent is not None
    assert "parsing API responses" in intent.intent
    assert intent.confidence >= 0.7
    assert "docstring" in intent.reason.lower()


def test_infer_intent_from_markdown(tmp_path):
    """Test inferring intent from markdown first paragraph."""
    md_file = tmp_path / "guide.md"
    md_file.write_text(
        """# API Guide

This guide explains how to use the API client. It covers authentication and requests.

## Getting Started

...
"""
    )

    intent = infer_intent_from_docstring("guide.md", tmp_path)

    assert intent is not None
    assert "API client" in intent.intent or "API" in intent.intent
    assert intent.confidence >= 0.6


def test_infer_intent_no_docstring(tmp_path):
    """Test that files without docstrings return None."""
    py_file = tmp_path / "nodoc.py"
    py_file.write_text(
        """
def function():
    pass
"""
    )

    intent = infer_intent_from_docstring("nodoc.py", tmp_path)

    assert intent is None


def test_infer_intent_truncates_long_text(tmp_path):
    """Test that long intents are truncated."""
    py_file = tmp_path / "long.py"
    # Long text without sentence endings to force truncation
    long_text = "This is a very long description that goes on and on without any punctuation to end the sentence so it will definitely exceed the maximum length limit and need to be truncated at a word boundary with ellipsis"
    py_file.write_text(f'"""{long_text}"""\n')

    intent = infer_intent_from_docstring("long.py", tmp_path, max_length=100)

    assert intent is not None
    assert len(intent.intent) <= 100
    assert intent.intent.endswith("...")


# =============================================================================
# Test Main Inference Function
# =============================================================================


def test_infer_file_metadata_python_file(index, schema, tmp_path):
    """Test complete inference on a Python file."""
    py_file = tmp_path / "src" / "parser.py"
    py_file.parent.mkdir(parents=True, exist_ok=True)
    py_file.write_text(
        '''"""Parser module for API responses."""

import json
from meaning_core import FileEntry

def parse():
    pass
'''
    )

    # Add meaning_core to index
    index.add_file(
        FileEntry(
            path="src/meaning_core.py",
            intent="Core",
            tags=["module"],
            status="active",
        )
    )

    result = infer_file_metadata("src/parser.py", tmp_path, index, schema)

    assert result.path == "src/parser.py"

    # Should have inferred tags
    assert len(result.tags) > 0
    tag_names = [t.tag for t in result.tags]
    assert "module" in tag_names
    assert "parsing" in tag_names

    # Should have inferred intent
    assert result.intent is not None
    assert "Parser" in result.intent.intent or "API" in result.intent.intent

    # Should have inferred imports
    assert len(result.relationships) > 0
    assert any(r.relationship.type == "imports" for r in result.relationships)

    # Should have no errors
    assert len(result.errors) == 0


def test_infer_file_metadata_test_file(index, schema, tmp_path):
    """Test complete inference on a test file."""
    # First create the source file
    src_file = tmp_path / "src" / "api" / "client.py"
    src_file.parent.mkdir(parents=True, exist_ok=True)
    src_file.write_text("# API client")

    # Create test file
    test_file = tmp_path / "tests" / "test_client.py"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text(
        '''"""Tests for API client."""

def test_client():
    pass
'''
    )

    result = infer_file_metadata("tests/test_client.py", tmp_path, index, schema)

    # Should identify as test
    tag_names = [t.tag for t in result.tags]
    assert "test" in tag_names

    # Should infer test relationship
    test_rels = [r for r in result.relationships if r.relationship.type == "tests"]
    assert len(test_rels) == 1
    assert test_rels[0].relationship.target == "src/api/client.py"


def test_infer_file_metadata_markdown_file(index, schema, tmp_path):
    """Test complete inference on a markdown file."""
    md_file = tmp_path / "README.md"
    md_file.write_text(
        """# Project

This project implements an API client using `src/api/client.py`.
"""
    )

    result = infer_file_metadata("README.md", tmp_path, index, schema)

    # Should identify as doc
    tag_names = [t.tag for t in result.tags]
    assert "doc" in tag_names
    assert "overview" in tag_names

    # Should have inferred intent
    assert result.intent is not None

    # Should have document relationships
    doc_rels = [r for r in result.relationships if r.relationship.type == "documents"]
    assert len(doc_rels) >= 1


# =============================================================================
# Test Error Handling
# =============================================================================


def test_infer_file_metadata_graceful_errors(index, schema, tmp_path):
    """Test that inference handles errors gracefully."""
    # Non-existent file should not crash
    result = infer_file_metadata("nonexistent.py", tmp_path, index, schema)

    assert result.path == "nonexistent.py"
    # May have some inferred tags from path, but shouldn't crash
    assert isinstance(result.tags, list)
    assert isinstance(result.relationships, list)


def test_file_inference_result_add_methods():
    """Test FileInferenceResult helper methods."""
    result = FileInferenceResult(path="test.py")

    result.add_tag("test", 0.9, "Test file")
    result.add_relationship("tests", "src/main.py", 0.85, "Naming convention")
    result.set_intent("Test suite for main", 0.8, "Docstring")
    result.add_error("Something went wrong")
    result.add_warning("Missing docstring")

    assert len(result.tags) == 1
    assert result.tags[0].tag == "test"
    assert len(result.relationships) == 1
    assert result.relationships[0].relationship.type == "tests"
    assert result.intent is not None
    assert result.intent.intent == "Test suite for main"
    assert len(result.errors) == 1
    assert len(result.warnings) == 1
