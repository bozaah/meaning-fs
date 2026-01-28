"""
Tests for meaning_inference.py

Tests all inference functions with realistic examples.
"""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from meaning.meaning_core import (
    FileEntry,
    MeaningIndex,
    MeaningSchema,
    RelationshipType,
)
from meaning.meaning_inference import (
    ExtensionRule,
    FileInferenceResult,
    FilenameRule,
    InferenceRules,
    PathPatternRule,
    get_default_rules,
    infer_document_relationships,
    infer_file_metadata,
    infer_from_rules,
    infer_import_relationships,
    infer_intent_from_comment_block,
    infer_intent_from_docstring,
    infer_intent_from_path,
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
# Rule-Based Inference Tests
# =============================================================================


class TestInferenceRuleDataStructures:
    """Test inference rule data structures."""

    def test_filename_rule_creation(self):
        """Test FilenameRule dataclass."""
        rule = FilenameRule(
            filename=".gitignore",
            intent="Git ignore patterns",
            tags=["config", "vcs"],
            confidence=1.0,
        )
        assert rule.filename == ".gitignore"
        assert rule.intent == "Git ignore patterns"
        assert rule.tags == ["config", "vcs"]
        assert rule.confidence == 1.0

    def test_path_pattern_rule_creation(self):
        """Test PathPatternRule dataclass."""
        rule = PathPatternRule(
            pattern="**/test_*.py",
            intent="Python test module",
            tags=["test"],
            confidence=0.90,
            fallback_to_content=True,
        )
        assert rule.pattern == "**/test_*.py"
        assert rule.fallback_to_content is True

    def test_extension_rule_creation(self):
        """Test ExtensionRule dataclass."""
        rule = ExtensionRule(
            extension=".slurm",
            intent="SLURM batch script",
            tags=["script", "hpc"],
            confidence=0.95,
            fallback_to_content=False,
        )
        assert rule.extension == ".slurm"
        assert rule.fallback_to_content is False

    def test_inference_rules_collection(self):
        """Test InferenceRules collection."""
        rules = InferenceRules(
            exact_filenames=[FilenameRule(".gitignore", "Git ignore", ["config"], 1.0)],
            path_patterns=[PathPatternRule("**/test_*.py", "Test", ["test"], 0.9)],
            extension_rules=[ExtensionRule(".md", "Markdown", ["doc"], 0.6, True)],
        )
        assert len(rules.exact_filenames) == 1
        assert len(rules.path_patterns) == 1
        assert len(rules.extension_rules) == 1


class TestGetDefaultRules:
    """Test get_default_rules function."""

    def test_returns_inference_rules(self):
        """Test that get_default_rules returns an InferenceRules instance."""
        rules = get_default_rules()
        assert isinstance(rules, InferenceRules)

    def test_has_filename_rules(self):
        """Test that default rules include common filenames."""
        rules = get_default_rules()
        filenames = {r.filename for r in rules.exact_filenames}
        assert ".gitignore" in filenames
        assert "requirements.txt" in filenames
        assert "CLAUDE.md" in filenames
        assert "README.md" in filenames
        assert "pyproject.toml" in filenames

    def test_has_path_patterns(self):
        """Test that default rules include path patterns."""
        rules = get_default_rules()
        patterns = {r.pattern for r in rules.path_patterns}
        assert ".github/workflows/*.yml" in patterns
        assert "**/test_*.py" in patterns

    def test_has_extension_rules(self):
        """Test that default rules include extension rules."""
        rules = get_default_rules()
        extensions = {r.extension for r in rules.extension_rules}
        assert ".slurm" in extensions
        assert ".md" in extensions
        assert ".sh" in extensions

    def test_returns_copies(self):
        """Test that get_default_rules returns copies, not originals."""
        rules1 = get_default_rules()
        rules2 = get_default_rules()
        # Modifying one shouldn't affect the other
        rules1.exact_filenames.append(FilenameRule("test.txt", "Test", ["test"], 1.0))
        assert len(rules1.exact_filenames) != len(rules2.exact_filenames)


class TestInferFromRulesFilename:
    """Test infer_from_rules with filename matching."""

    def test_gitignore_exact_match(self):
        """Test exact filename match for .gitignore."""
        intent, tags, fallback = infer_from_rules(".gitignore")
        assert intent is not None
        assert intent.intent == "Git version control ignore patterns"
        assert intent.confidence == 1.0
        assert "Exact filename match" in intent.reason
        tag_names = [t.tag for t in tags]
        assert "config" in tag_names
        assert "vcs" in tag_names
        assert "ignore" in tag_names
        assert fallback is False  # No fallback for exact matches

    def test_requirements_txt(self):
        """Test exact filename match for requirements.txt."""
        intent, tags, fallback = infer_from_rules("requirements.txt")
        assert intent is not None
        assert "Python package dependencies" in intent.intent
        tag_names = [t.tag for t in tags]
        assert "config" in tag_names
        assert "dependencies" in tag_names

    def test_claude_md(self):
        """Test AI agent context file detection."""
        intent, tags, fallback = infer_from_rules("CLAUDE.md")
        assert intent is not None
        assert "Claude AI agent" in intent.intent
        tag_names = [t.tag for t in tags]
        assert "doc" in tag_names
        assert "ai" in tag_names
        assert "agent-context" in tag_names

    def test_gemini_md(self):
        """Test Gemini agent context file detection."""
        intent, tags, fallback = infer_from_rules("GEMINI.md")
        assert intent is not None
        assert "Gemini" in intent.intent
        tag_names = [t.tag for t in tags]
        assert "agent-context" in tag_names

    def test_readme_md(self):
        """Test README.md detection."""
        intent, tags, fallback = infer_from_rules("README.md")
        assert intent is not None
        assert "overview" in intent.intent.lower() or "documentation" in intent.intent.lower()
        tag_names = [t.tag for t in tags]
        assert "doc" in tag_names
        assert "overview" in tag_names

    def test_pyproject_toml(self):
        """Test pyproject.toml detection."""
        intent, tags, fallback = infer_from_rules("pyproject.toml")
        assert intent is not None
        assert "Python project" in intent.intent
        tag_names = [t.tag for t in tags]
        assert "config" in tag_names
        assert "packaging" in tag_names

    def test_dockerfile(self):
        """Test Dockerfile detection."""
        intent, tags, fallback = infer_from_rules("Dockerfile")
        assert intent is not None
        assert "Docker" in intent.intent
        tag_names = [t.tag for t in tags]
        assert "container" in tag_names

    def test_nested_path_filename(self):
        """Test that filename rules match regardless of directory."""
        intent, tags, fallback = infer_from_rules("src/myproject/.gitignore")
        assert intent is not None
        assert "Git" in intent.intent

    def test_case_sensitive_filename(self):
        """Test that filename matching is case-sensitive."""
        # README.md should match
        intent, _, _ = infer_from_rules("README.md")
        assert intent is not None
        # readme.md should NOT match the exact rule
        intent2, _, fallback = infer_from_rules("readme.md")
        # Should fall through to extension rule
        assert fallback is True


class TestInferFromRulesPathPattern:
    """Test infer_from_rules with path pattern matching."""

    def test_github_workflow(self):
        """Test GitHub Actions workflow pattern."""
        intent, tags, fallback = infer_from_rules(".github/workflows/ci.yml")
        assert intent is not None
        assert "GitHub Actions" in intent.intent
        tag_names = [t.tag for t in tags]
        assert "ci-cd" in tag_names

    def test_test_file_pattern(self):
        """Test test file pattern matching."""
        intent, tags, fallback = infer_from_rules("tests/test_core.py")
        assert intent is not None
        assert "test" in intent.intent.lower()
        tag_names = [t.tag for t in tags]
        assert "test" in tag_names

    def test_upload_script_pattern(self):
        """Test upload script pattern."""
        intent, tags, fallback = infer_from_rules("scripts/upload_data.sh")
        assert intent is not None
        assert "upload" in intent.intent.lower()
        tag_names = [t.tag for t in tags]
        assert "upload" in tag_names

    def test_compute_module_pattern(self):
        """Test computational module pattern."""
        intent, tags, fallback = infer_from_rules("src/compute_metrics.py")
        assert intent is not None
        assert "Computational" in intent.intent or "processing" in intent.intent.lower()
        tag_names = [t.tag for t in tags]
        assert "data-processing" in tag_names
        assert fallback is True  # Should fallback for content

    def test_prompts_directory(self):
        """Test LLM prompts directory pattern."""
        intent, tags, fallback = infer_from_rules("prompts/system/assistant.md")
        assert intent is not None
        assert "prompt" in intent.intent.lower()
        tag_names = [t.tag for t in tags]
        assert "llm-prompt" in tag_names


class TestInferFromRulesExtension:
    """Test infer_from_rules with extension matching."""

    def test_slurm_extension(self):
        """Test SLURM batch script extension."""
        intent, tags, fallback = infer_from_rules("jobs/run_analysis.slurm")
        assert intent is not None
        assert "SLURM" in intent.intent
        tag_names = [t.tag for t in tags]
        assert "hpc" in tag_names
        assert "slurm" in tag_names
        assert "batch" in tag_names

    def test_pbs_extension(self):
        """Test PBS batch script extension."""
        intent, tags, fallback = infer_from_rules("jobs/process.pbs")
        assert intent is not None
        assert "PBS" in intent.intent
        tag_names = [t.tag for t in tags]
        assert "hpc" in tag_names
        assert "pbs" in tag_names

    def test_shell_script_extension(self):
        """Test shell script extension with fallback."""
        intent, tags, fallback = infer_from_rules("scripts/setup.sh")
        assert intent is not None
        assert "Shell script" in intent.intent
        tag_names = [t.tag for t in tags]
        assert "script" in tag_names
        assert fallback is True  # Shell scripts should fallback

    def test_markdown_extension(self):
        """Test markdown extension with fallback."""
        intent, tags, fallback = infer_from_rules("docs/guide.md")
        assert intent is not None
        tag_names = [t.tag for t in tags]
        assert "doc" in tag_names
        assert fallback is True  # Markdown should fallback

    def test_yaml_extension(self):
        """Test YAML extension with low confidence."""
        intent, tags, fallback = infer_from_rules("config/settings.yaml")
        assert intent is not None
        assert intent.confidence == 0.50  # Low confidence
        assert fallback is True


class TestInferFromRulesPriority:
    """Test that rule priority is respected (filename > pattern > extension)."""

    def test_filename_beats_extension(self):
        """Test that exact filename match beats extension rule."""
        # README.md matches both filename rule and .md extension
        intent, tags, _ = infer_from_rules("README.md")
        assert intent is not None
        # Should use filename rule (higher confidence, specific intent)
        assert intent.confidence == 1.0
        assert "overview" in intent.intent.lower() or "documentation" in intent.intent.lower()

    def test_pattern_beats_extension(self):
        """Test that path pattern beats extension rule."""
        # test_core.py matches both pattern and would match .py extension if we had one
        intent, tags, _ = infer_from_rules("tests/test_core.py")
        assert intent is not None
        # Should use pattern rule
        assert "Path pattern match" in intent.reason

    def test_no_match_returns_fallback(self):
        """Test that unmatched files return None with fallback=True."""
        intent, tags, fallback = infer_from_rules("random_file.xyz")
        assert intent is None
        assert tags == []
        assert fallback is True


class TestInferFromRulesCustomRules:
    """Test infer_from_rules with custom rules."""

    def test_custom_filename_rule(self):
        """Test custom filename rules override defaults."""
        custom_rules = InferenceRules(
            exact_filenames=[
                FilenameRule(
                    "CUSTOM.md",
                    "Custom project file",
                    ["custom", "important"],
                    0.99,
                )
            ],
            path_patterns=[],
            extension_rules=[],
        )
        intent, tags, fallback = infer_from_rules("CUSTOM.md", custom_rules)
        assert intent is not None
        assert intent.intent == "Custom project file"
        tag_names = [t.tag for t in tags]
        assert "custom" in tag_names

    def test_empty_rules_fallback(self):
        """Test that empty rules result in fallback."""
        empty_rules = InferenceRules(
            exact_filenames=[],
            path_patterns=[],
            extension_rules=[],
        )
        intent, tags, fallback = infer_from_rules(".gitignore", empty_rules)
        assert intent is None
        assert fallback is True


# =============================================================================
# Timestamp Inference
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
    md_file.write_text("""
# Guide

This guide explains [the API client](src/api/client.py) and [models](src/models/user.py).

See also: https://example.com (external link)
""")

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
    md_file.write_text("""
# Documentation

The main implementation is in `src/api/client.py`.
""")

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
    py_file.write_text("""
import meaning.meaning_core
from pathlib import Path

def main():
    pass
""")

    # Add meaning.meaning_core to index
    index.add_file(
        FileEntry(
            path="src/meaning/meaning_core.py",
            intent="Core module",
            tags=["module"],
            status="active",
        )
    )

    rels = infer_import_relationships("src/test.py", tmp_path, index)

    # Should find meaning.meaning_core (Path is stdlib, won't be in index)
    assert len(rels) >= 1
    assert any(r.relationship.target == "src/meaning/meaning_core.py" for r in rels)
    assert all(r.confidence >= 0.9 for r in rels)


def test_infer_import_relationships_from_import(index, tmp_path):
    """Test inferring import relationships from 'from' imports."""
    py_file = tmp_path / "src" / "main.py"
    py_file.parent.mkdir(parents=True, exist_ok=True)
    py_file.write_text("""
from api.client import APIClient
from models.user import User
""")

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
    py_file.write_text("""
def broken(
    # Missing closing parenthesis
""")

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
    py_file.write_text('''"""
This is a module for parsing API responses.

It handles JSON and XML formats.
"""

def parse():
    pass
''')

    intent = infer_intent_from_docstring("module.py", tmp_path)

    assert intent is not None
    assert "parsing API responses" in intent.intent
    assert intent.confidence >= 0.7
    assert "docstring" in intent.reason.lower()


def test_infer_intent_from_markdown(tmp_path):
    """Test inferring intent from markdown first paragraph."""
    md_file = tmp_path / "guide.md"
    md_file.write_text("""# API Guide

This guide explains how to use the API client. It covers authentication and requests.

## Getting Started

...
""")

    intent = infer_intent_from_docstring("guide.md", tmp_path)

    assert intent is not None
    assert "API client" in intent.intent or "API" in intent.intent
    assert intent.confidence >= 0.8


def test_infer_intent_from_comment_block_shell(tmp_path):
    sh_file = tmp_path / "run.sh"
    sh_file.write_text("""#!/usr/bin/env bash
# Upload derived artifacts to S3.
# Uses aws cli for sync.
echo \"ok\"
""")

    intent = infer_intent_from_comment_block("run.sh", tmp_path)

    assert intent is not None
    assert "Upload derived artifacts to S3" in intent.intent
    assert intent.confidence >= 0.8


def test_infer_intent_from_comment_block_python(tmp_path):
    py_file = tmp_path / "script.py"
    py_file.write_text("""# -*- coding: utf-8 -*-
# Compute zonal statistics for monthly datasets.

def main():
    pass
""")

    intent = infer_intent_from_comment_block("script.py", tmp_path)

    assert intent is not None
    assert "Compute zonal statistics" in intent.intent
    assert intent.confidence >= 0.8


def test_infer_intent_sanitizes_markdown(tmp_path):
    md_file = tmp_path / "notes.md"
    md_file.write_text("""# Notes

- **Purpose:** Learn the `.meaning/` index format.
""")

    intent = infer_intent_from_docstring("notes.md", tmp_path)

    assert intent is not None
    assert "Purpose:" in intent.intent
    assert "`" not in intent.intent
    assert "**" not in intent.intent
    assert "index format" in intent.intent


def test_infer_intent_from_path_known_docs():
    intent = infer_intent_from_path("README.md")

    assert intent is not None
    assert "overview" in intent.intent.lower()
    assert intent.confidence >= 0.8


def test_infer_intent_from_path_template_schema():
    intent = infer_intent_from_path("src/meaning/templates/schema/python.yaml")

    assert intent is not None
    assert "schema template" in intent.intent.lower()
    assert "python" in intent.intent.lower()
    assert intent.confidence >= 0.8


def test_infer_intent_no_docstring(tmp_path):
    """Test that files without docstrings return None."""
    py_file = tmp_path / "nodoc.py"
    py_file.write_text("""
def function():
    pass
""")

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
    py_file.write_text('''"""Parser module for API responses."""

import json
from meaning.meaning_core import FileEntry

def parse():
    pass
''')

    # Add meaning.meaning_core to index
    index.add_file(
        FileEntry(
            path="src/meaning/meaning_core.py",
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
    test_file.write_text('''"""Tests for API client."""

def test_client():
    pass
''')

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
    md_file.write_text("""# Project

This project implements an API client using `src/api/client.py`.
""")

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


def test_infer_file_metadata_slurm_rule_definitive(index, schema, tmp_path):
    slurm_file = tmp_path / "jobs" / "run_analysis.slurm"
    slurm_file.parent.mkdir(parents=True, exist_ok=True)
    slurm_file.write_text("""# Run monthly aggregates for 1990-2020
# Uses array jobs

srun python run.py
""")

    result = infer_file_metadata("jobs/run_analysis.slurm", tmp_path, index, schema)

    assert result.intent is not None
    assert result.intent.intent == "SLURM batch job submission script"
    assert result.intent.confidence >= 0.9


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
