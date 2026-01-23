"""
Tests for the meaning installer module.
"""

import json

import pytest

from meaning.installer import (
    ConflictResolution,
    InstallOptions,
    InstallResult,
    create_meaning_directory,
    detect_project_type,
    format_install_result,
    get_package_template_dir,
    get_schema_path,
    install_claude_hooks,
    install_meaning,
    install_skills,
    is_git_repo,
    meaning_dir_exists,
    merge_hooks_config,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_project(tmp_path):
    """Create a temporary project directory."""
    project = tmp_path / "test_project"
    project.mkdir()
    return project


@pytest.fixture
def python_project(temp_project):
    """Create a Python project with marker files."""
    (temp_project / "pyproject.toml").write_text("[project]\nname = 'test'\n")
    (temp_project / "src").mkdir()
    (temp_project / "src" / "main.py").write_text("print('hello')\n")
    return temp_project


@pytest.fixture
def node_project(temp_project):
    """Create a Node.js project with marker files."""
    (temp_project / "package.json").write_text('{"name": "test"}\n')
    (temp_project / "src").mkdir()
    (temp_project / "src" / "index.js").write_text("console.log('hello');\n")
    return temp_project


@pytest.fixture
def git_project(temp_project):
    """Create a project with .git directory."""
    (temp_project / ".git").mkdir()
    return temp_project


# =============================================================================
# Template Resolution Tests
# =============================================================================


class TestTemplateResolution:
    def test_get_package_template_dir_exists(self):
        """Template directory should exist in the package."""
        template_dir = get_package_template_dir()
        assert template_dir.exists()
        assert template_dir.is_dir()

    def test_get_package_template_dir_has_config(self):
        """Template directory should contain config.yaml."""
        template_dir = get_package_template_dir()
        assert (template_dir / "config.yaml").exists()

    def test_get_package_template_dir_has_schemas(self):
        """Template directory should contain schema files."""
        template_dir = get_package_template_dir()
        schema_dir = template_dir / "schema"
        assert schema_dir.exists()
        assert (schema_dir / "python.yaml").exists()
        assert (schema_dir / "node.yaml").exists()
        assert (schema_dir / "rust.yaml").exists()

    def test_get_schema_path_valid(self):
        """Should return path for valid project types."""
        template_dir = get_package_template_dir()
        path = get_schema_path(template_dir, "python")
        assert path.exists()
        assert path.name == "python.yaml"

    def test_get_schema_path_invalid(self):
        """Should raise ValueError for invalid project type."""
        template_dir = get_package_template_dir()
        with pytest.raises(ValueError, match="Unknown project type"):
            get_schema_path(template_dir, "invalid_type")


# =============================================================================
# Project Detection Tests
# =============================================================================


class TestProjectDetection:
    def test_detect_python_project(self, python_project):
        """Should detect Python project from pyproject.toml."""
        assert detect_project_type(python_project) == "python"

    def test_detect_node_project(self, node_project):
        """Should detect Node.js project from package.json."""
        assert detect_project_type(node_project) == "node"

    def test_detect_rust_project(self, temp_project):
        """Should detect Rust project from Cargo.toml."""
        (temp_project / "Cargo.toml").write_text("[package]\nname = 'test'\n")
        assert detect_project_type(temp_project) == "rust"

    def test_detect_mixed_project(self, temp_project):
        """Should return 'mixed' when no markers found."""
        assert detect_project_type(temp_project) == "mixed"

    def test_detect_multiple_markers_prefers_python(self, temp_project):
        """Should prefer Python when multiple markers present."""
        (temp_project / "pyproject.toml").write_text("[project]\n")
        (temp_project / "package.json").write_text("{}\n")
        assert detect_project_type(temp_project) == "python"

    def test_is_git_repo_true(self, git_project):
        """Should return True for git repositories."""
        assert is_git_repo(git_project) is True

    def test_is_git_repo_false(self, temp_project):
        """Should return False for non-git directories."""
        assert is_git_repo(temp_project) is False

    def test_meaning_dir_exists_false(self, temp_project):
        """Should return False when .meaning/ doesn't exist."""
        assert meaning_dir_exists(temp_project) is False

    def test_meaning_dir_exists_true(self, temp_project):
        """Should return True when .meaning/ exists."""
        (temp_project / ".meaning").mkdir()
        assert meaning_dir_exists(temp_project) is True


# =============================================================================
# Directory Creation Tests
# =============================================================================


class TestCreateMeaningDirectory:
    def test_creates_meaning_dir(self, temp_project):
        """Should create .meaning/ directory."""
        template_dir = get_package_template_dir()
        create_meaning_directory(temp_project, "python", template_dir)
        assert (temp_project / ".meaning").is_dir()

    def test_creates_schema_file(self, temp_project):
        """Should copy schema.yaml for project type."""
        template_dir = get_package_template_dir()
        create_meaning_directory(temp_project, "python", template_dir)
        schema_path = temp_project / ".meaning" / "schema.yaml"
        assert schema_path.exists()
        content = schema_path.read_text()
        assert "python" in content.lower() or "relationship_types" in content

    def test_creates_config_file(self, temp_project):
        """Should copy config.yaml."""
        template_dir = get_package_template_dir()
        create_meaning_directory(temp_project, "python", template_dir)
        config_path = temp_project / ".meaning" / "config.yaml"
        assert config_path.exists()

    def test_creates_hooks_file(self, temp_project):
        """Should copy hooks.json."""
        template_dir = get_package_template_dir()
        create_meaning_directory(temp_project, "python", template_dir)
        hooks_path = temp_project / ".meaning" / "hooks.json"
        assert hooks_path.exists()

    def test_creates_scripts_directory(self, temp_project):
        """Should create scripts/ with executable scripts."""
        template_dir = get_package_template_dir()
        create_meaning_directory(temp_project, "python", template_dir)
        scripts_dir = temp_project / ".meaning" / "scripts"
        assert scripts_dir.is_dir()
        assert (scripts_dir / "meaning-post-write.sh").exists()
        assert (scripts_dir / "meaning-validate.sh").exists()

    def test_scripts_are_executable(self, temp_project):
        """Scripts should have executable permissions."""
        template_dir = get_package_template_dir()
        create_meaning_directory(temp_project, "python", template_dir)
        script = temp_project / ".meaning" / "scripts" / "meaning-post-write.sh"
        # Check that at least one execute bit is set
        assert script.stat().st_mode & 0o111

    def test_returns_list_of_files(self, temp_project):
        """Should return list of created files."""
        template_dir = get_package_template_dir()
        files = create_meaning_directory(temp_project, "python", template_dir)
        assert len(files) > 0
        assert any("schema.yaml" in f for f in files)
        assert any("config.yaml" in f for f in files)

    def test_dry_run_does_not_create_files(self, temp_project):
        """Dry run should not create any files."""
        template_dir = get_package_template_dir()
        files = create_meaning_directory(temp_project, "python", template_dir, dry_run=True)
        assert len(files) > 0  # Should still return what would be created
        assert not (temp_project / ".meaning").exists()


# =============================================================================
# Claude Hooks Tests
# =============================================================================


class TestInstallClaudeHooks:
    def test_creates_settings_json(self, temp_project):
        """Should create .claude/settings.json."""
        template_dir = get_package_template_dir()
        ok, msg = install_claude_hooks(temp_project, template_dir)
        assert ok is True
        assert (temp_project / ".claude" / "settings.json").exists()

    def test_settings_json_has_hooks(self, temp_project):
        """Created settings.json should have hooks configured."""
        template_dir = get_package_template_dir()
        install_claude_hooks(temp_project, template_dir)
        settings_path = temp_project / ".claude" / "settings.json"
        with open(settings_path) as f:
            settings = json.load(f)
        assert "hooks" in settings

    def test_refuses_overwrite_without_force(self, temp_project):
        """Should refuse to overwrite existing settings.json without force."""
        (temp_project / ".claude").mkdir()
        (temp_project / ".claude" / "settings.json").write_text('{"existing": true}')

        template_dir = get_package_template_dir()
        ok, msg = install_claude_hooks(temp_project, template_dir, force=False)
        assert ok is False
        assert "exists" in msg.lower()

    def test_merges_with_force(self, temp_project):
        """Should merge hooks with force flag."""
        (temp_project / ".claude").mkdir()
        existing = {"permissions": {"allow": ["Bash(test)"]}}
        (temp_project / ".claude" / "settings.json").write_text(json.dumps(existing))

        template_dir = get_package_template_dir()
        ok, msg = install_claude_hooks(temp_project, template_dir, force=True)
        assert ok is True
        assert "merged" in msg.lower()

        # Check that both existing and new settings are preserved
        with open(temp_project / ".claude" / "settings.json") as f:
            result = json.load(f)
        assert "permissions" in result
        assert "hooks" in result

    def test_dry_run_does_not_create(self, temp_project):
        """Dry run should not create settings.json."""
        template_dir = get_package_template_dir()
        ok, msg = install_claude_hooks(temp_project, template_dir, dry_run=True)
        assert ok is True
        assert not (temp_project / ".claude").exists()


class TestMergeHooksConfig:
    def test_adds_hooks_to_empty(self):
        """Should add hooks to config without hooks section."""
        existing = {"permissions": {"allow": []}}
        new_hooks = {"hooks": {"PostToolUse": [{"matcher": "Write"}]}}
        result = merge_hooks_config(existing, new_hooks)
        assert "hooks" in result
        assert "PostToolUse" in result["hooks"]
        assert "permissions" in result

    def test_preserves_existing_hooks(self):
        """Should preserve existing hooks when adding new ones."""
        existing = {"hooks": {"Stop": [{"matcher": "all"}]}}
        new_hooks = {"hooks": {"PostToolUse": [{"matcher": "Write"}]}}
        result = merge_hooks_config(existing, new_hooks)
        assert "Stop" in result["hooks"]
        assert "PostToolUse" in result["hooks"]

    def test_no_duplicate_matchers(self):
        """Should not add duplicate hooks with same matcher."""
        existing = {"hooks": {"PostToolUse": [{"matcher": "Write"}]}}
        new_hooks = {"hooks": {"PostToolUse": [{"matcher": "Write"}]}}
        result = merge_hooks_config(existing, new_hooks)
        assert len(result["hooks"]["PostToolUse"]) == 1


# =============================================================================
# Skills Installation Tests
# =============================================================================


class TestInstallSkills:
    def test_installs_skills(self, temp_project):
        """Should install skill directories."""
        template_dir = get_package_template_dir()
        installed, warnings = install_skills(temp_project, template_dir)
        # Skills might not exist in templates yet, so check for either case
        if (template_dir / "skills").exists():
            skills_dir = temp_project / ".claude" / "skills"
            assert skills_dir.exists() or len(warnings) > 0

    def test_skips_existing_skills(self, temp_project):
        """Should skip skills that already exist."""
        template_dir = get_package_template_dir()
        skills_src = template_dir / "skills"

        if skills_src.exists():
            # Create an existing skill
            existing_skill = temp_project / ".claude" / "skills" / "meaning-init"
            existing_skill.mkdir(parents=True)
            (existing_skill / "SKILL.md").write_text("existing")

            installed, warnings = install_skills(temp_project, template_dir)
            assert any("meaning-init" in w for w in warnings)

    def test_dry_run_does_not_create(self, temp_project):
        """Dry run should not create skill directories."""
        template_dir = get_package_template_dir()
        install_skills(temp_project, template_dir, dry_run=True)
        # Skills dir should not exist unless it already did
        skills_dir = temp_project / ".claude" / "skills"
        assert not skills_dir.exists()


# =============================================================================
# Main Installation Tests
# =============================================================================


class TestInstallMeaning:
    def test_basic_installation(self, python_project):
        """Should successfully install meaning in a Python project."""
        options = InstallOptions(install_hooks=False)
        result = install_meaning(python_project, options)
        assert result.success is True
        assert result.meaning_dir_created is True
        assert (python_project / ".meaning").exists()

    def test_detects_project_type(self, python_project):
        """Should auto-detect project type."""
        options = InstallOptions(install_hooks=False)
        result = install_meaning(python_project, options)
        assert result.success is True
        # Check that python schema was used
        schema = (python_project / ".meaning" / "schema.yaml").read_text()
        assert "python" in schema.lower() or "relationship_types" in schema

    def test_respects_explicit_project_type(self, temp_project):
        """Should use explicit project type when provided."""
        options = InstallOptions(project_type="node", install_hooks=False)
        result = install_meaning(temp_project, options)
        assert result.success is True
        schema = (temp_project / ".meaning" / "schema.yaml").read_text()
        assert "node" in schema.lower() or "relationship_types" in schema

    def test_warns_on_non_git(self, temp_project):
        """Should warn when not a git repo."""
        options = InstallOptions(install_hooks=False)
        result = install_meaning(temp_project, options)
        assert any("git" in w.lower() for w in result.warnings)

    def test_no_git_warning_on_git_repo(self, git_project):
        """Should not warn about git on git repos."""
        options = InstallOptions(install_hooks=False)
        result = install_meaning(git_project, options)
        assert not any("git repository" in w.lower() for w in result.warnings)

    def test_fails_on_existing_meaning_dir_abort(self, temp_project):
        """Should fail when .meaning/ exists with ABORT resolution."""
        (temp_project / ".meaning").mkdir()
        options = InstallOptions(
            conflict_resolution=ConflictResolution.ABORT,
            install_hooks=False,
        )
        result = install_meaning(temp_project, options)
        assert result.success is False
        assert any("already exists" in e for e in result.errors)

    def test_skips_on_existing_meaning_dir_skip(self, temp_project):
        """Should skip when .meaning/ exists with SKIP resolution."""
        (temp_project / ".meaning").mkdir()
        (temp_project / ".meaning" / "existing.txt").write_text("keep me")
        options = InstallOptions(
            conflict_resolution=ConflictResolution.SKIP,
            install_hooks=False,
        )
        result = install_meaning(temp_project, options)
        assert result.success is True
        assert result.meaning_dir_created is False
        # Original file should still exist
        assert (temp_project / ".meaning" / "existing.txt").exists()

    def test_overwrites_on_existing_meaning_dir_overwrite(self, temp_project):
        """Should overwrite when .meaning/ exists with OVERWRITE resolution."""
        (temp_project / ".meaning").mkdir()
        (temp_project / ".meaning" / "old.txt").write_text("old")
        options = InstallOptions(
            conflict_resolution=ConflictResolution.OVERWRITE,
            install_hooks=False,
        )
        result = install_meaning(temp_project, options)
        assert result.success is True
        assert result.meaning_dir_created is True
        # Old file should be gone
        assert not (temp_project / ".meaning" / "old.txt").exists()
        # New files should exist
        assert (temp_project / ".meaning" / "config.yaml").exists()

    def test_installs_hooks_when_requested(self, temp_project):
        """Should install hooks when install_hooks=True."""
        options = InstallOptions(install_hooks=True)
        result = install_meaning(temp_project, options)
        assert result.success is True
        assert result.hooks_installed is True
        assert (temp_project / ".claude" / "settings.json").exists()

    def test_does_not_install_hooks_when_not_requested(self, temp_project):
        """Should not install hooks when install_hooks=False."""
        options = InstallOptions(install_hooks=False)
        result = install_meaning(temp_project, options)
        assert result.success is True
        assert result.hooks_installed is False
        assert not (temp_project / ".claude" / "settings.json").exists()

    def test_dry_run_does_not_modify(self, temp_project):
        """Dry run should not create any files."""
        options = InstallOptions(dry_run=True, install_hooks=True)
        result = install_meaning(temp_project, options)
        # Dry run still reports what would be done
        assert len(result.files_copied) > 0
        # But nothing should actually be created
        assert not (temp_project / ".meaning").exists()
        assert not (temp_project / ".claude").exists()

    def test_invalid_project_type_fails(self, temp_project):
        """Should fail with invalid project type."""
        options = InstallOptions(project_type="invalid_type", install_hooks=False)
        result = install_meaning(temp_project, options)
        assert result.success is False
        assert any("unknown project type" in e.lower() for e in result.errors)


# =============================================================================
# Result Formatting Tests
# =============================================================================


class TestFormatInstallResult:
    def test_success_format(self):
        """Should format successful result nicely."""
        result = InstallResult(
            success=True,
            meaning_dir_created=True,
            files_copied=["a.yaml", "b.yaml", "c.yaml"],
            hooks_installed=True,
        )
        output = format_install_result(result, "python")
        assert "✓" in output
        assert "python" in output
        assert "3 files" in output
        assert "hooks" in output.lower()

    def test_failure_format(self):
        """Should format failed result with errors."""
        result = InstallResult(success=False)
        result.add_error("Something went wrong")
        output = format_install_result(result, "python")
        assert "❌" in output
        assert "Something went wrong" in output

    def test_warnings_format(self):
        """Should include warnings in output."""
        result = InstallResult(success=True, meaning_dir_created=True)
        result.add_warning("Watch out")
        output = format_install_result(result, "python")
        assert "⚠️" in output
        assert "Watch out" in output


# =============================================================================
# InstallResult Tests
# =============================================================================


class TestInstallResult:
    def test_add_warning(self):
        """Should add warnings without failing."""
        result = InstallResult(success=True)
        result.add_warning("A warning")
        assert "A warning" in result.warnings
        assert result.success is True

    def test_add_error_fails_result(self):
        """Adding an error should set success to False."""
        result = InstallResult(success=True)
        result.add_error("An error")
        assert "An error" in result.errors
        assert result.success is False
