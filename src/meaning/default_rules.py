"""
Meaning: Default Inference Rules

This module contains the built-in rules for the inference engine.
Separated from meaning_inference.py to improve maintainability.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FilenameRule:
    """Rule for exact filename matching."""

    filename: str  # exact filename to match (case-sensitive)
    intent: str
    tags: list[str]
    confidence: float = 0.95


@dataclass
class PathPatternRule:
    """Rule for glob pattern matching on full path."""

    pattern: str  # glob pattern, e.g., "**/upload_*.sh"
    intent: str
    tags: list[str]
    confidence: float = 0.85
    fallback_to_content: bool = False


@dataclass
class ExtensionRule:
    """Rule for file extension matching."""

    extension: str  # including dot, e.g., ".slurm"
    intent: str
    tags: list[str]
    confidence: float = 0.70
    fallback_to_content: bool = True


@dataclass
class InferenceRules:
    """Collection of all inference rules."""

    exact_filenames: list[FilenameRule] = field(default_factory=list)
    path_patterns: list[PathPatternRule] = field(default_factory=list)
    extension_rules: list[ExtensionRule] = field(default_factory=list)


# =============================================================================
# Default Rules
# =============================================================================

DEFAULT_FILENAME_RULES: list[FilenameRule] = [
    # === Git/VCS Files ===
    FilenameRule(
        ".gitignore", "Git version control ignore patterns", ["config", "vcs", "ignore"], 1.0
    ),
    FilenameRule(".gitattributes", "Git file attributes configuration", ["config", "vcs"], 1.0),
    FilenameRule(".gitmodules", "Git submodule configuration", ["config", "vcs"], 1.0),
    # === Python Project Files ===
    FilenameRule(
        "requirements.txt", "Python package dependencies (pip)", ["config", "dependencies"], 1.0
    ),
    FilenameRule(
        "requirements-dev.txt",
        "Python development dependencies",
        ["config", "dependencies", "dev"],
        1.0,
    ),
    FilenameRule("setup.py", "Python package setup script", ["config", "packaging"], 1.0),
    FilenameRule("setup.cfg", "Python package configuration", ["config", "packaging"], 1.0),
    FilenameRule(
        "pyproject.toml", "Python project configuration (PEP 518)", ["config", "packaging"], 1.0
    ),
    FilenameRule("MANIFEST.in", "Python package manifest", ["config", "packaging"], 0.95),
    FilenameRule("pytest.ini", "Pytest configuration", ["config", "test"], 1.0),
    FilenameRule("conftest.py", "Pytest fixtures and configuration", ["test", "fixture"], 0.95),
    FilenameRule(".python-version", "Python version specification", ["config"], 1.0),
    FilenameRule("tox.ini", "Tox testing configuration", ["config", "test"], 1.0),
    FilenameRule(".coveragerc", "Coverage.py configuration", ["config", "test"], 1.0),
    FilenameRule("mkdocs.yml", "MkDocs documentation configuration", ["config", "doc"], 0.95),
    FilenameRule("mkdocs.yaml", "MkDocs documentation configuration", ["config", "doc"], 0.95),
    # === Node/JavaScript Files ===
    FilenameRule(
        "package.json", "Node.js package manifest", ["config", "dependencies", "packaging"], 1.0
    ),
    FilenameRule(
        "package-lock.json",
        "Node.js dependency lock file",
        ["config", "dependencies", "generated"],
        1.0,
    ),
    FilenameRule(
        "yarn.lock", "Yarn dependency lock file", ["config", "dependencies", "generated"], 1.0
    ),
    FilenameRule(
        "pnpm-lock.yaml", "pnpm dependency lock file", ["config", "dependencies", "generated"], 1.0
    ),
    FilenameRule("tsconfig.json", "TypeScript configuration", ["config"], 1.0),
    FilenameRule(".nvmrc", "Node version specification", ["config"], 1.0),
    FilenameRule(".npmrc", "npm configuration", ["config"], 1.0),
    # === Rust Files ===
    FilenameRule(
        "Cargo.toml", "Rust package manifest", ["config", "dependencies", "packaging"], 1.0
    ),
    FilenameRule(
        "Cargo.lock", "Rust dependency lock file", ["config", "dependencies", "generated"], 1.0
    ),
    # === Documentation Files ===
    FilenameRule("README.md", "Project overview and documentation", ["doc", "overview"], 1.0),
    FilenameRule("README", "Project overview and documentation", ["doc", "overview"], 1.0),
    FilenameRule("README.txt", "Project overview and documentation", ["doc", "overview"], 1.0),
    FilenameRule("README.rst", "Project overview and documentation", ["doc", "overview"], 1.0),
    FilenameRule(
        "CHANGELOG.md", "Project change history and release notes", ["doc", "history"], 1.0
    ),
    FilenameRule("CHANGELOG", "Project change history and release notes", ["doc", "history"], 1.0),
    FilenameRule("HISTORY.md", "Project history", ["doc", "history"], 1.0),
    FilenameRule("CONTRIBUTING.md", "Contribution guidelines", ["doc", "dev-guide"], 1.0),
    FilenameRule("CODE_OF_CONDUCT.md", "Community code of conduct", ["doc"], 1.0),
    FilenameRule("LICENSE", "Project license", ["doc", "legal"], 1.0),
    FilenameRule("LICENSE.md", "Project license", ["doc", "legal"], 1.0),
    FilenameRule("LICENSE.txt", "Project license", ["doc", "legal"], 1.0),
    FilenameRule("AUTHORS", "Project authors list", ["doc"], 0.95),
    FilenameRule("AUTHORS.md", "Project authors list", ["doc"], 0.95),
    FilenameRule("SECURITY.md", "Security policy and reporting", ["doc", "security"], 1.0),
    # === AI Agent Context Files ===
    FilenameRule(
        "CLAUDE.md",
        "Claude AI agent project context and directives",
        ["doc", "ai", "agent-context"],
        1.0,
    ),
    FilenameRule(
        "GEMINI.md", "Google Gemini agent project context", ["doc", "ai", "agent-context"], 1.0
    ),
    FilenameRule("AGENTS.md", "AI agent project context", ["doc", "ai", "agent-context"], 1.0),
    FilenameRule("WARP.md", "AI/Warp agent project context", ["doc", "ai", "agent-context"], 1.0),
    FilenameRule("COPILOT.md", "GitHub Copilot context", ["doc", "ai", "agent-context"], 1.0),
    FilenameRule(".cursorrules", "Cursor AI editor rules", ["config", "ai", "agent-context"], 1.0),
    FilenameRule(".cursorignore", "Cursor AI ignore patterns", ["config", "ai", "ignore"], 1.0),
    FilenameRule(".aider.conf.yml", "Aider AI assistant configuration", ["config", "ai"], 1.0),
    # === System/Generated Files ===
    FilenameRule(
        ".DS_Store", "macOS Finder metadata (should be git-ignored)", ["system", "generated"], 1.0
    ),
    FilenameRule(
        "Thumbs.db", "Windows thumbnail cache (should be git-ignored)", ["system", "generated"], 1.0
    ),
    FilenameRule(".editorconfig", "Editor configuration", ["config"], 1.0),
    # === CI/CD Files ===
    FilenameRule("Makefile", "Build automation rules", ["config", "build"], 0.95),
    FilenameRule("Dockerfile", "Docker container definition", ["config", "container"], 1.0),
    FilenameRule(
        "docker-compose.yml",
        "Docker Compose service definitions",
        ["config", "container", "orchestration"],
        1.0,
    ),
    FilenameRule(
        "docker-compose.yaml",
        "Docker Compose service definitions",
        ["config", "container", "orchestration"],
        1.0,
    ),
    FilenameRule(
        ".dockerignore", "Docker build ignore patterns", ["config", "container", "ignore"], 1.0
    ),
    FilenameRule("Jenkinsfile", "Jenkins pipeline definition", ["config", "ci-cd"], 1.0),
    FilenameRule(".travis.yml", "Travis CI configuration", ["config", "ci-cd"], 1.0),
    FilenameRule(".gitlab-ci.yml", "GitLab CI configuration", ["config", "ci-cd"], 1.0),
]

DEFAULT_PATH_PATTERN_RULES: list[PathPatternRule] = [
    # === CI/CD Patterns ===
    PathPatternRule(
        ".github/workflows/*.yml", "GitHub Actions workflow", ["config", "ci-cd"], 0.95
    ),
    PathPatternRule(
        ".github/workflows/*.yaml", "GitHub Actions workflow", ["config", "ci-cd"], 0.95
    ),
    PathPatternRule(".circleci/config.yml", "CircleCI configuration", ["config", "ci-cd"], 1.0),
    # === Scientific Computing Patterns ===
    PathPatternRule(
        "**/compute_*.py",
        "Computational data processing module",
        ["module", "data-processing"],
        0.80,
        True,
    ),
    PathPatternRule(
        "**/process_*.py", "Data processing module", ["module", "data-processing"], 0.80, True
    ),
    PathPatternRule(
        "**/analyze_*.py",
        "Data analysis module",
        ["module", "data-processing", "statistics"],
        0.80,
        True,
    ),
    # === Data Operations Patterns ===
    PathPatternRule(
        "**/upload_*.sh", "Data upload script", ["script", "upload", "deployment"], 0.85
    ),
    PathPatternRule("**/download_*.sh", "Data download script", ["script", "download"], 0.85),
    PathPatternRule("**/sync_*.sh", "Data synchronization script", ["script", "sync"], 0.85),
    # === Test Patterns ===
    PathPatternRule("**/test_*.py", "Python test module", ["test"], 0.90),
    PathPatternRule("**/*_test.py", "Python test module", ["test"], 0.90),
    PathPatternRule("**/tests/**/*.py", "Python test module", ["test"], 0.85, True),
    # === Prompt/AI Patterns ===
    # Match prompts/ at any level, with files directly in prompts/ or in subdirs
    PathPatternRule("prompts/**/*.md", "LLM prompt template", ["doc", "ai", "llm-prompt"], 0.85),
    PathPatternRule("prompts/**/*.txt", "LLM prompt template", ["doc", "ai", "llm-prompt"], 0.85),
    PathPatternRule("prompts/*.md", "LLM prompt template", ["doc", "ai", "llm-prompt"], 0.85),
    PathPatternRule("prompts/*.txt", "LLM prompt template", ["doc", "ai", "llm-prompt"], 0.85),
]

DEFAULT_EXTENSION_RULES: list[ExtensionRule] = [
    # === Scientific/HPC Extensions ===
    ExtensionRule(
        ".slurm", "SLURM batch job submission script", ["script", "hpc", "slurm", "batch"], 0.95
    ),
    ExtensionRule(".sbatch", "SLURM batch script", ["script", "hpc", "slurm", "batch"], 0.95),
    ExtensionRule(".pbs", "PBS/Torque batch script", ["script", "hpc", "pbs", "batch"], 0.95),
    ExtensionRule(".sge", "Sun Grid Engine batch script", ["script", "hpc", "batch"], 0.95),
    # === Scientific Data Extensions ===
    ExtensionRule(".parquet", "Parquet columnar data", ["data", "binary"], 0.80, False),
    ExtensionRule(".h5", "HDF5 hierarchical data", ["data", "binary", "scientific"], 0.80, False),
    ExtensionRule(".hdf5", "HDF5 hierarchical data", ["data", "binary", "scientific"], 0.80, False),
    ExtensionRule(
        ".nc", "NetCDF climate/scientific data", ["data", "binary", "scientific"], 0.80, False
    ),
    ExtensionRule(".zarr", "Zarr array data", ["data", "binary", "scientific"], 0.80, False),
    # === Source Code Extensions ===
    ExtensionRule(".py", "Python source module", ["module"], 0.85, True),
    # === Data/Config Extensions (low confidence, fallback to content) ===
    ExtensionRule(".yaml", "YAML configuration or data", ["config"], 0.50, True),
    ExtensionRule(".yml", "YAML configuration or data", ["config"], 0.50, True),
    ExtensionRule(".toml", "TOML configuration", ["config"], 0.60, True),
    ExtensionRule(".json", "JSON data or configuration", ["config"], 0.50, True),
    ExtensionRule(".ini", "INI configuration file", ["config"], 0.60, True),
    ExtensionRule(".env", "Environment variables file", ["config", "security"], 0.80),
    # === Script Extensions ===
    ExtensionRule(".sh", "Shell script", ["script"], 0.80, True),
    ExtensionRule(".bash", "Bash script", ["script"], 0.80, True),
    ExtensionRule(".zsh", "Zsh script", ["script"], 0.80, True),
    # === Documentation Extensions ===
    ExtensionRule(".md", "Markdown documentation", ["doc"], 0.60, True),
    ExtensionRule(".rst", "reStructuredText documentation", ["doc"], 0.65, True),
    ExtensionRule(".txt", "Plain text file", [], 0.30, True),
]


def get_default_rules() -> InferenceRules:
    """Get the default built-in inference rules."""
    return InferenceRules(
        exact_filenames=DEFAULT_FILENAME_RULES.copy(),
        path_patterns=DEFAULT_PATH_PATTERN_RULES.copy(),
        extension_rules=DEFAULT_EXTENSION_RULES.copy(),
    )
