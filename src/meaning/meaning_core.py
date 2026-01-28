"""
Meaning: Semantic File Index for AI Agents

Core library for parsing, validating, and manipulating .meaning/ indexes.

This module serves as the main facade, re-exporting from specialized modules
for backward compatibility:
- meaning.constants: Constants and default values
- meaning.models: Core dataclasses (FileEntry, Concept, MeaningIndex, etc.)
- meaning.index_io: YAML file I/O operations
- meaning.validation: Index validation
- meaning.project: Project detection and scanning
- meaning.index_ops: Index manipulation operations
- meaning.query: Query engine and display functions
- meaning.cli: Command-line interface
"""

from __future__ import annotations

# =============================================================================
# Re-exports from cli module
# =============================================================================
from meaning.cli import main

# =============================================================================
# Re-exports from constants module
# =============================================================================
from meaning.constants import (
    CONFIG_FILENAME,
    DEFAULT_MAX_INTENT_LENGTH,
    DEFAULT_REVIEW_THRESHOLD,
    DEFAULT_STALE_THRESHOLD_DAYS,
    INDEX_FILENAME,
    MEANING_DIR,
    SCHEMA_FILENAME,
    VALID_STATUSES,
    VERSION,
)

# =============================================================================
# Re-exports from index_io module
# =============================================================================
from meaning.index_io import (
    load_config,
    load_index,
    load_schema,
    load_yaml,
    save_config,
    save_index,
    save_schema,
    save_yaml,
)

# =============================================================================
# Re-exports from index_ops module
# =============================================================================
from meaning.index_ops import (
    apply_inference_to_entry,
    copy_template_file,
    create_meaning_dir,
    create_skeleton_entry,
    entry_from_inference,
    find_deleted_files,
    find_modified_files,
    find_unindexed_files,
    initialize_meaning,
    install_claude_hooks,
    preview_inference_changes,
    preview_inference_diff,
    prune_excluded_entries,
    resolve_template_dir,
)

# =============================================================================
# Re-exports from models module
# =============================================================================
from meaning.models import (
    Concept,
    FileEntry,
    MeaningConfig,
    MeaningIndex,
    MeaningSchema,
    Relationship,
    RelationshipType,
)

# =============================================================================
# Re-exports from project module
# =============================================================================
from meaning.project import (
    PROJECT_MARKERS,
    detect_project_type,
    is_git_repo,
    meaning_dir_exists,
    scan_project_files,
)

# =============================================================================
# Re-exports from query module
# =============================================================================
from meaning.query import (
    QueryResult,
    display_query_results,
    display_status,
    query_index,
)

# =============================================================================
# Re-exports from validation module
# =============================================================================
from meaning.validation import (
    ValidationResult,
    validate_index,
)

# =============================================================================
# Public API
# =============================================================================
__all__ = [
    # Constants
    "CONFIG_FILENAME",
    "DEFAULT_MAX_INTENT_LENGTH",
    "DEFAULT_REVIEW_THRESHOLD",
    "DEFAULT_STALE_THRESHOLD_DAYS",
    "INDEX_FILENAME",
    "MEANING_DIR",
    "PROJECT_MARKERS",
    "SCHEMA_FILENAME",
    "VALID_STATUSES",
    "VERSION",
    # Models
    "Concept",
    "FileEntry",
    "MeaningConfig",
    "MeaningIndex",
    "MeaningSchema",
    "QueryResult",
    "Relationship",
    "RelationshipType",
    "ValidationResult",
    # I/O
    "load_config",
    "load_index",
    "load_schema",
    "load_yaml",
    "save_config",
    "save_index",
    "save_schema",
    "save_yaml",
    # Validation
    "validate_index",
    # Project
    "detect_project_type",
    "is_git_repo",
    "meaning_dir_exists",
    "scan_project_files",
    # Index Operations
    "apply_inference_to_entry",
    "copy_template_file",
    "create_meaning_dir",
    "create_skeleton_entry",
    "entry_from_inference",
    "find_deleted_files",
    "find_modified_files",
    "find_unindexed_files",
    "initialize_meaning",
    "install_claude_hooks",
    "preview_inference_changes",
    "preview_inference_diff",
    "prune_excluded_entries",
    "resolve_template_dir",
    # Query
    "display_query_results",
    "display_status",
    "query_index",
    # CLI
    "main",
]
