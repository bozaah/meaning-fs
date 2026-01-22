"""
Meaning: Semantic File Index for AI Agents

A lean, text-based semantic layer for codebases.
"""

from meaning.meaning_core import (
    # Data classes
    Relationship,
    FileEntry,
    Concept,
    MeaningIndex,
    MeaningSchema,
    MeaningConfig,
    RelationshipType,
    ValidationResult,
    QueryResult,
    # Functions
    validate_index,
    detect_project_type,
    is_git_repo,
    create_skeleton_entry,
    load_yaml,
    save_yaml,
    load_index,
    load_schema,
    load_config,
    save_index,
    query_index,
    display_query_results,
    display_status,
    # Constants
    VERSION,
    VALID_STATUSES,
)

__version__ = VERSION
__all__ = [
    "Relationship",
    "FileEntry",
    "Concept",
    "MeaningIndex",
    "MeaningSchema",
    "MeaningConfig",
    "RelationshipType",
    "ValidationResult",
    "QueryResult",
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
    "VERSION",
    "VALID_STATUSES",
]
