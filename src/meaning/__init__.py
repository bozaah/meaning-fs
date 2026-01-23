"""
Meaning: Semantic File Index for AI Agents

A lean, text-based semantic layer for codebases.
"""

from meaning.installer import (
    ConflictResolution,
    # Data classes
    InstallOptions,
    InstallResult,
    format_install_result,
    get_package_template_dir,
    install_claude_hooks,
    # Functions
    install_meaning,
    install_skills,
)
from meaning.meaning_core import (
    VALID_STATUSES,
    # Constants
    VERSION,
    Concept,
    FileEntry,
    MeaningConfig,
    MeaningIndex,
    MeaningSchema,
    QueryResult,
    # Data classes
    Relationship,
    RelationshipType,
    ValidationResult,
    create_skeleton_entry,
    detect_project_type,
    display_query_results,
    display_status,
    is_git_repo,
    load_config,
    load_index,
    load_schema,
    load_yaml,
    query_index,
    save_index,
    save_yaml,
    # Functions
    validate_index,
)

__version__ = VERSION
__all__ = [
    # Core data classes
    "Relationship",
    "FileEntry",
    "Concept",
    "MeaningIndex",
    "MeaningSchema",
    "MeaningConfig",
    "RelationshipType",
    "ValidationResult",
    "QueryResult",
    # Core functions
    "validate_index",
    "detect_project_type",
    "is_git_repo",
    "create_skeleton_entry",
    "load_yaml",
    "save_yaml",
    "load_index",
    "load_schema",
    "load_config",
    "save_index",
    "query_index",
    "display_query_results",
    "display_status",
    # Core constants
    "VERSION",
    "VALID_STATUSES",
    # Installer data classes
    "InstallOptions",
    "InstallResult",
    "ConflictResolution",
    # Installer functions
    "install_meaning",
    "install_claude_hooks",
    "install_skills",
    "format_install_result",
    "get_package_template_dir",
]
