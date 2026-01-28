"""
Meaning: Project detection and scanning utilities.

This module handles project type detection and file scanning.
"""

from __future__ import annotations

from pathlib import Path

from meaning.constants import MEANING_DIR
from meaning.models import MeaningConfig

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


def meaning_dir_exists(project_root: Path) -> bool:
    """Check if .meaning directory exists."""
    return (project_root / MEANING_DIR).is_dir()


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
