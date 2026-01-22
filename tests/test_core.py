"""
Tests for meaning_core module.

Run with: python -m pytest tests/ -v
"""

import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path
import tempfile
import os

# Add src to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from meaning.meaning_core import (
    Relationship,
    FileEntry,
    Concept,
    MeaningIndex,
    RelationshipType,
    MeaningSchema,
    MeaningConfig,
    ValidationResult,
    QueryResult,
    validate_index,
    detect_project_type,
    is_git_repo,
    create_skeleton_entry,
    load_yaml,
    save_yaml,
    query_index,
    apply_inference_to_entry,
    preview_inference_changes,
    VERSION,
    VALID_STATUSES,
)
from meaning.meaning_inference import FileInferenceResult


# =============================================================================
# Relationship Tests
# =============================================================================

class TestRelationship:
    def test_create_with_target(self):
        rel = Relationship(type="imports", target="src/utils.py")
        assert rel.type == "imports"
        assert rel.target == "src/utils.py"
        assert rel.source is None

    def test_create_with_source(self):
        rel = Relationship(type="tests", source="tests/test_main.py")
        assert rel.type == "tests"
        assert rel.source == "tests/test_main.py"
        assert rel.target is None

    def test_create_with_both(self):
        rel = Relationship(type="transforms", source="src/input.py", target="src/output.py")
        assert rel.source == "src/input.py"
        assert rel.target == "src/output.py"

    def test_create_without_target_or_source_fails(self):
        with pytest.raises(ValueError, match="must have either target or source"):
            Relationship(type="imports")

    def test_to_dict(self):
        rel = Relationship(type="imports", target="src/utils.py")
        d = rel.to_dict()
        assert d == {"type": "imports", "target": "src/utils.py"}

    def test_to_dict_with_source(self):
        rel = Relationship(type="tests", source="tests/test_main.py")
        d = rel.to_dict()
        assert d == {"type": "tests", "source": "tests/test_main.py"}

    def test_from_dict(self):
        d = {"type": "imports", "target": "src/utils.py"}
        rel = Relationship.from_dict(d)
        assert rel.type == "imports"
        assert rel.target == "src/utils.py"


# =============================================================================
# FileEntry Tests
# =============================================================================

class TestFileEntry:
    def test_create_minimal(self):
        entry = FileEntry(path="src/main.py", intent="Main entry point")
        assert entry.path == "src/main.py"
        assert entry.intent == "Main entry point"
        assert entry.status == "active"
        assert entry.needs_review is False
        assert entry.tags == []
        assert entry.relationships == []

    def test_create_full(self):
        entry = FileEntry(
            path="src/api/client.py",
            intent="HTTP client for external APIs",
            status="active",
            needs_review=True,
            tags=["api", "http"],
            relationships=[Relationship(type="imports", target="src/config.py")],
        )
        assert entry.tags == ["api", "http"]
        assert len(entry.relationships) == 1

    def test_invalid_status_fails(self):
        with pytest.raises(ValueError, match="Invalid status"):
            FileEntry(path="test.py", intent="Test", status="invalid")

    def test_valid_statuses(self):
        for status in VALID_STATUSES:
            entry = FileEntry(path="test.py", intent="Test", status=status)
            assert entry.status == status

    def test_to_dict(self):
        entry = FileEntry(
            path="src/main.py",
            intent="Main entry point",
            tags=["core"],
        )
        d = entry.to_dict()
        assert d["path"] == "src/main.py"
        assert d["intent"] == "Main entry point"
        assert d["tags"] == ["core"]
        assert "last_verified" in d

    def test_from_dict(self):
        d = {
            "path": "src/main.py",
            "intent": "Main entry point",
            "status": "active",
            "needs_review": False,
            "last_verified": "2025-01-21T10:00:00+00:00",
            "tags": ["core"],
            "relationships": [{"type": "imports", "target": "src/utils.py"}],
        }
        entry = FileEntry.from_dict(d)
        assert entry.path == "src/main.py"
        assert entry.tags == ["core"]
        assert len(entry.relationships) == 1

    def test_from_dict_minimal(self):
        d = {"path": "test.py"}
        entry = FileEntry.from_dict(d)
        assert entry.path == "test.py"
        assert "[NEEDS REVIEW]" in entry.intent

    def test_is_stale_fresh(self):
        entry = FileEntry(path="test.py", intent="Test")
        assert entry.is_stale(threshold_days=7) is False

    def test_is_stale_old(self):
        old_date = datetime.now(timezone.utc) - timedelta(days=10)
        entry = FileEntry(path="test.py", intent="Test", last_verified=old_date)
        assert entry.is_stale(threshold_days=7) is True


# =============================================================================
# Concept Tests
# =============================================================================

class TestConcept:
    def test_create(self):
        concept = Concept(
            name="authentication",
            description="User auth and sessions",
            files=["src/auth/login.py", "src/auth/session.py"],
            entry_point="src/auth/login.py",
        )
        assert concept.name == "authentication"
        assert len(concept.files) == 2
        assert concept.entry_point == "src/auth/login.py"

    def test_to_dict(self):
        concept = Concept(name="auth", description="Auth", files=["a.py"])
        d = concept.to_dict()
        assert d["name"] == "auth"
        assert d["files"] == ["a.py"]

    def test_from_dict(self):
        d = {
            "name": "auth",
            "description": "Auth",
            "files": ["a.py", "b.py"],
            "entry_point": "a.py",
        }
        concept = Concept.from_dict(d)
        assert concept.name == "auth"
        assert concept.entry_point == "a.py"


# =============================================================================
# MeaningIndex Tests
# =============================================================================

class TestMeaningIndex:
    def test_create_empty(self):
        index = MeaningIndex()
        assert index.version == VERSION
        assert index.files == []
        assert index.concepts == []

    def test_get_file_found(self):
        index = MeaningIndex(files=[
            FileEntry(path="a.py", intent="A"),
            FileEntry(path="b.py", intent="B"),
        ])
        entry = index.get_file("b.py")
        assert entry is not None
        assert entry.intent == "B"

    def test_get_file_not_found(self):
        index = MeaningIndex()
        assert index.get_file("missing.py") is None

    def test_add_file_new(self):
        index = MeaningIndex()
        entry = FileEntry(path="new.py", intent="New file")
        index.add_file(entry)
        assert len(index.files) == 1
        assert index.get_file("new.py") is not None

    def test_add_file_update(self):
        index = MeaningIndex(files=[
            FileEntry(path="a.py", intent="Old intent")
        ])
        updated = FileEntry(path="a.py", intent="New intent")
        index.add_file(updated)
        assert len(index.files) == 1
        assert index.get_file("a.py").intent == "New intent"

    def test_remove_file(self):
        index = MeaningIndex(files=[
            FileEntry(path="a.py", intent="A"),
            FileEntry(path="b.py", intent="B"),
        ])
        result = index.remove_file("a.py")
        assert result is True
        assert len(index.files) == 1
        assert index.get_file("a.py") is None

    def test_remove_file_not_found(self):
        index = MeaningIndex()
        result = index.remove_file("missing.py")
        assert result is False

    def test_files_needing_review(self):
        index = MeaningIndex(files=[
            FileEntry(path="a.py", intent="A", needs_review=True),
            FileEntry(path="b.py", intent="B", needs_review=False),
            FileEntry(path="c.py", intent="C", needs_review=True),
        ])
        needing = index.files_needing_review()
        assert len(needing) == 2
        assert all(f.needs_review for f in needing)

    def test_find_by_tags_any(self):
        index = MeaningIndex(files=[
            FileEntry(path="a.py", intent="A", tags=["api", "http"]),
            FileEntry(path="b.py", intent="B", tags=["database"]),
            FileEntry(path="c.py", intent="C", tags=["api", "auth"]),
        ])
        results = index.find_by_tags(["api"])
        assert len(results) == 2

    def test_find_by_tags_all(self):
        index = MeaningIndex(files=[
            FileEntry(path="a.py", intent="A", tags=["api", "http"]),
            FileEntry(path="b.py", intent="B", tags=["api"]),
        ])
        results = index.find_by_tags(["api", "http"], match_all=True)
        assert len(results) == 1
        assert results[0].path == "a.py"

    def test_find_by_intent(self):
        index = MeaningIndex(files=[
            FileEntry(path="a.py", intent="HTTP client for API requests"),
            FileEntry(path="b.py", intent="Database connection handler"),
            FileEntry(path="c.py", intent="API response parser"),
        ])
        results = index.find_by_intent(["API"])
        assert len(results) == 2

    def test_to_dict_from_dict_roundtrip(self):
        index = MeaningIndex(
            concepts=[Concept(name="auth", description="Auth", files=["a.py"])],
            files=[FileEntry(path="a.py", intent="A", tags=["auth"])],
        )
        d = index.to_dict()
        restored = MeaningIndex.from_dict(d)
        assert len(restored.files) == 1
        assert len(restored.concepts) == 1
        assert restored.files[0].path == "a.py"


# =============================================================================
# MeaningSchema Tests
# =============================================================================

class TestMeaningSchema:
    def test_create_default(self):
        schema = MeaningSchema()
        assert schema.project_type == "mixed"
        assert schema.custom_prefix == "x-"

    def test_is_valid_relationship_type(self):
        schema = MeaningSchema(relationship_types=[
            RelationshipType(name="imports", description="Import dep"),
            RelationshipType(name="tests", description="Test"),
        ])
        assert schema.is_valid_relationship_type("imports") is True
        assert schema.is_valid_relationship_type("unknown") is False

    def test_is_valid_tag_in_vocabulary(self):
        schema = MeaningSchema(tag_vocabulary={
            "domain": ["api", "auth"],
            "layer": ["service", "model"],
        })
        assert schema.is_valid_tag("api") is True
        assert schema.is_valid_tag("service") is True
        assert schema.is_valid_tag("unknown") is False

    def test_is_valid_tag_custom(self):
        schema = MeaningSchema(custom_prefix="x-")
        assert schema.is_valid_tag("x-custom") is True
        assert schema.is_valid_tag("custom") is False

    def test_all_tags(self):
        schema = MeaningSchema(tag_vocabulary={
            "a": ["one", "two"],
            "b": ["three"],
        })
        tags = schema.all_tags()
        assert set(tags) == {"one", "two", "three"}


# =============================================================================
# MeaningConfig Tests
# =============================================================================

class TestMeaningConfig:
    def test_create_default(self):
        config = MeaningConfig()
        assert config.require_intent is True
        assert config.stale_threshold_days == 7

    def test_is_excluded_pattern(self):
        config = MeaningConfig(exclude_patterns=["*.pyc", "__pycache__/**"])
        assert config.is_excluded("test.pyc") is True
        assert config.is_excluded("test.py") is False

    def test_is_excluded_path(self):
        config = MeaningConfig(exclude_paths=["vendor/", "dist/"])
        assert config.is_excluded("vendor/lib.py") is True
        assert config.is_excluded("src/main.py") is False

    def test_is_excluded_include_override(self):
        config = MeaningConfig(
            exclude_paths=["vendor/"],
            include_paths=["vendor/important/"],
        )
        assert config.is_excluded("vendor/lib.py") is True
        assert config.is_excluded("vendor/important/keep.py") is False

    def test_to_dict_from_dict_roundtrip(self):
        config = MeaningConfig(
            exclude_patterns=["*.pyc"],
            stale_threshold_days=14,
        )
        d = config.to_dict()
        restored = MeaningConfig.from_dict(d)
        assert restored.stale_threshold_days == 14
        assert "*.pyc" in restored.exclude_patterns


# =============================================================================
# Validation Tests
# =============================================================================

class TestValidation:
    def test_validate_empty_index(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            index = MeaningIndex()
            schema = MeaningSchema()
            config = MeaningConfig()
            
            result = validate_index(index, schema, config, project_root)
            assert result.is_valid is True

    def test_validate_missing_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            index = MeaningIndex(files=[
                FileEntry(path="missing.py", intent="Does not exist")
            ])
            schema = MeaningSchema()
            config = MeaningConfig()
            
            result = validate_index(index, schema, config, project_root)
            assert result.is_valid is False
            assert any("does not exist" in e for e in result.errors)

    def test_validate_dangling_relationship(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / "a.py").touch()
            
            index = MeaningIndex(files=[
                FileEntry(
                    path="a.py", 
                    intent="A",
                    relationships=[Relationship(type="imports", target="missing.py")]
                )
            ])
            schema = MeaningSchema(relationship_types=[
                RelationshipType(name="imports", description="Import")
            ])
            config = MeaningConfig()
            
            result = validate_index(index, schema, config, project_root)
            assert any("Dangling relationship" in e for e in result.errors)

    def test_validate_unknown_tag_warning(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / "a.py").touch()
            
            index = MeaningIndex(files=[
                FileEntry(path="a.py", intent="A", tags=["unknown-tag"])
            ])
            schema = MeaningSchema(tag_vocabulary={"domain": ["api"]})
            config = MeaningConfig(warn_on_unknown_tags=True)
            
            result = validate_index(index, schema, config, project_root)
            assert any("Unknown tag" in w for w in result.warnings)

    def test_validate_stale_entry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / "a.py").touch()
            
            old_date = datetime.now(timezone.utc) - timedelta(days=10)
            index = MeaningIndex(files=[
                FileEntry(path="a.py", intent="A", last_verified=old_date)
            ])
            schema = MeaningSchema()
            config = MeaningConfig(stale_threshold_days=7)
            
            result = validate_index(index, schema, config, project_root)
            assert any("Stale entry" in w for w in result.warnings)


# =============================================================================
# Utility Function Tests
# =============================================================================

class TestUtilities:
    def test_detect_project_type_python(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / "pyproject.toml").touch()
            assert detect_project_type(project_root) == "python"

    def test_detect_project_type_node(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / "package.json").touch()
            assert detect_project_type(project_root) == "node"

    def test_detect_project_type_mixed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            assert detect_project_type(project_root) == "mixed"

    def test_is_git_repo_true(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / ".git").mkdir()
            assert is_git_repo(project_root) is True

    def test_is_git_repo_false(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            assert is_git_repo(project_root) is False

    def test_create_skeleton_entry(self):
        entry = create_skeleton_entry("new_file.py")
        assert entry.path == "new_file.py"
        assert entry.needs_review is True
        assert "[NEEDS REVIEW]" in entry.intent


# =============================================================================
# YAML I/O Tests
# =============================================================================

class TestYamlIO:
    def test_save_and_load_yaml(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.yaml"
            data = {"key": "value", "list": [1, 2, 3]}
            
            save_yaml(filepath, data)
            loaded = load_yaml(filepath)
            
            assert loaded == data

    def test_load_yaml_creates_parent_dirs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "nested" / "deep" / "test.yaml"
            data = {"test": True}
            
            save_yaml(filepath, data)
            assert filepath.exists()


# =============================================================================
# Query Engine Tests
# =============================================================================

class TestQueryEngine:
    @pytest.fixture
    def sample_index(self):
        """Create a sample index with various file types for testing queries."""
        now = datetime.now(timezone.utc)

        files = [
            FileEntry(
                path="src/api.py",
                intent="API client for external services",
                tags=["api", "core"],
                status="active",
                needs_review=False,
                last_verified=now,
                relationships=[
                    Relationship(type="imports", target="src/utils.py")
                ]
            ),
            FileEntry(
                path="tests/test_api.py",
                intent="Test suite for API client",
                tags=["test"],
                status="active",
                needs_review=False,
                last_verified=now,
                relationships=[
                    Relationship(type="tests", target="src/api.py"),
                    Relationship(type="imports", target="src/api.py")
                ]
            ),
            FileEntry(
                path="config.yaml",
                intent="Configuration file with settings",
                tags=["config"],
                status="active",
                needs_review=True,
                last_verified=now - timedelta(days=1),
                relationships=[]
            ),
            FileEntry(
                path="src/parser.py",
                intent="Parses JSON responses from API",
                tags=["parsing", "core"],
                status="active",
                needs_review=False,
                last_verified=now - timedelta(days=10),
                relationships=[]
            ),
            FileEntry(
                path="README.md",
                intent="Project documentation",
                tags=["doc"],
                status="active",
                needs_review=False,
                last_verified=now,
                relationships=[
                    Relationship(type="documents", target="src/api.py")
                ]
            ),
        ]

        concepts = [
            Concept(
                name="api-client",
                description="External API integration",
                files=["src/api.py", "tests/test_api.py"],
                entry_point="src/api.py"
            )
        ]

        return MeaningIndex(
            version="0.1",
            generated_at=now,
            last_updated=now,
            concepts=concepts,
            files=files
        )

    @pytest.fixture
    def sample_schema(self):
        """Create a sample schema for testing tag-based queries."""
        return MeaningSchema(
            relationship_types=["tests", "documents", "imports"],
            tag_vocabulary={
                "file_type": ["api", "test", "doc", "config"],
                "feature": ["core", "parsing"]
            }
        )

    def test_status_query_needs_review(self, sample_index, sample_schema):
        result = query_index(sample_index, sample_schema, "what needs review?")
        assert result.query_type == "status"
        assert len(result.files) == 1
        assert result.files[0].path == "config.yaml"

    def test_status_query_stale(self, sample_index, sample_schema):
        result = query_index(sample_index, sample_schema, "what is stale?")
        assert result.query_type == "status"
        assert len(result.files) == 1
        assert result.files[0].path == "src/parser.py"

    def test_tag_query(self, sample_index, sample_schema):
        result = query_index(sample_index, sample_schema, "find config files")
        # Should match tag query for 'config'
        assert result.query_type == "tag"
        assert len(result.files) == 1
        assert result.files[0].path == "config.yaml"

    def test_relationship_query_tests(self, sample_index, sample_schema):
        # Query for files with 'tests' relationship type
        result = query_index(sample_index, sample_schema, "what imports utils?")
        assert result.query_type == "relationship"
        assert len(result.files) >= 1
        # Should find src/api.py which imports src/utils.py
        assert any(f.path == "src/api.py" for f in result.files)

    def test_relationship_query_all(self, sample_index, sample_schema):
        result = query_index(sample_index, sample_schema, "what documents files?")
        assert result.query_type == "relationship"
        assert len(result.files) >= 1
        assert any(f.path == "README.md" for f in result.files)

    def test_concept_query(self, sample_index, sample_schema):
        result = query_index(sample_index, sample_schema, "show me the api client")
        assert result.query_type == "concept"
        assert len(result.files) == 2
        paths = {f.path for f in result.files}
        assert "src/api.py" in paths
        assert "tests/test_api.py" in paths

    def test_temporal_query(self, sample_index, sample_schema):
        result = query_index(sample_index, sample_schema, "what changed recently?")
        assert result.query_type == "temporal"
        assert len(result.files) <= 10
        # Most recent should be first
        assert result.files[0].path != "src/parser.py"  # This is the oldest

    def test_intent_query(self, sample_index, sample_schema):
        result = query_index(sample_index, sample_schema, "files about client services")
        # Should match intent keyword 'client' or 'services'
        assert result.query_type in ["intent", "tag"]  # Could match either way
        assert len(result.files) >= 1
        # Should find src/api.py with "API client for external services"
        paths = [f.path for f in result.files]
        assert "src/api.py" in paths

    def test_no_match_query(self, sample_index, sample_schema):
        result = query_index(sample_index, sample_schema, "nonexistent thing")
        assert result.query_type == "no_match"
        assert len(result.files) == 0


# =============================================================================
# Review Inference Application Tests
# =============================================================================

class TestInferenceApplication:
    def test_apply_inference_updates_intent_and_tags(self):
        entry = FileEntry(
            path="src/app.py",
            intent="[NEEDS REVIEW] src/app.py",
            needs_review=True,
        )
        result = FileInferenceResult(path="src/app.py")
        result.set_intent("App module for CLI smoke tests.", 0.9, "docstring")
        result.add_tag("module", 0.9, "path")

        config = MeaningConfig(require_intent=True, require_tags=False)
        now = datetime.now(timezone.utc)
        changed = apply_inference_to_entry(entry, result, 0.8, config, now)

        assert changed is True
        assert entry.intent == "App module for CLI smoke tests."
        assert "module" in entry.tags
        assert entry.needs_review is False

    def test_apply_inference_no_high_confidence_returns_false(self):
        entry = FileEntry(
            path="README.md",
            intent="[NEEDS REVIEW] README.md",
            needs_review=True,
        )
        result = FileInferenceResult(path="README.md")
        result.set_intent("Sample", 0.3, "title")

        config = MeaningConfig(require_intent=True, require_tags=False)
        now = datetime.now(timezone.utc)
        changed = apply_inference_to_entry(entry, result, 0.8, config, now)

        assert changed is False
        assert entry.intent.startswith("[NEEDS REVIEW]")
        assert entry.needs_review is True

    def test_apply_inference_marks_review_on_error(self):
        entry = FileEntry(
            path="src/app.py",
            intent="Existing intent",
            needs_review=False,
        )
        result = FileInferenceResult(path="src/app.py")
        result.add_error("Failed to infer intent")

        config = MeaningConfig(require_intent=True, require_tags=False)
        now = datetime.now(timezone.utc)
        changed = apply_inference_to_entry(entry, result, 0.8, config, now)

        assert changed is True
        assert entry.needs_review is True

    def test_preview_inference_changes_does_not_mutate(self):
        entry = FileEntry(
            path="src/app.py",
            intent="[NEEDS REVIEW] src/app.py",
            needs_review=True,
        )
        result = FileInferenceResult(path="src/app.py")
        result.set_intent("App module", 0.9, "docstring")

        config = MeaningConfig(require_intent=True, require_tags=False)
        now = datetime.now(timezone.utc)
        changed = preview_inference_changes(entry, result, 0.8, config, now)

        assert changed is True
        assert entry.intent.startswith("[NEEDS REVIEW]")

    def test_apply_inference_replaces_markdown_intent(self):
        entry = FileEntry(
            path="README.md",
            intent="- **Purpose:** Learn the `.meaning/` index.",
            needs_review=True,
        )
        result = FileInferenceResult(path="README.md")
        result.set_intent("Project overview and quick start guide.", 0.9, "path")

        config = MeaningConfig(require_intent=True, require_tags=False)
        now = datetime.now(timezone.utc)
        changed = apply_inference_to_entry(entry, result, 0.8, config, now)

        assert changed is True
        assert entry.intent == "Project overview and quick start guide."


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
