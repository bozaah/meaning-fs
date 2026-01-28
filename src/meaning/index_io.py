"""
Meaning: File I/O operations for indexes, schemas, and configs.

This module handles all YAML file operations for the meaning package.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from meaning.constants import (
    CONFIG_FILENAME,
    INDEX_FILENAME,
    MEANING_DIR,
    SCHEMA_FILENAME,
)
from meaning.models import (
    MeaningConfig,
    MeaningIndex,
    MeaningSchema,
)


def load_yaml(filepath: Path) -> dict[str, Any]:
    """Load and parse a YAML file."""
    with open(filepath, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data or {}


def save_yaml(filepath: Path, data: dict[str, Any]) -> None:
    """Save data to a YAML file."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


def load_index(project_root: Path) -> MeaningIndex:
    """Load the meaning index from a project."""
    index_path = project_root / MEANING_DIR / INDEX_FILENAME
    if not index_path.exists():
        raise FileNotFoundError(f"Index not found: {index_path}")
    data = load_yaml(index_path)
    return MeaningIndex.from_dict(data)


def save_index(project_root: Path, index: MeaningIndex) -> None:
    """Save the meaning index to a project."""
    index_path = project_root / MEANING_DIR / INDEX_FILENAME
    index.last_updated = datetime.now(timezone.utc)
    save_yaml(index_path, index.to_dict())


def load_schema(project_root: Path) -> MeaningSchema:
    """Load the meaning schema from a project."""
    schema_path = project_root / MEANING_DIR / SCHEMA_FILENAME
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema not found: {schema_path}")
    data = load_yaml(schema_path)
    return MeaningSchema.from_dict(data)


def save_schema(project_root: Path, schema: MeaningSchema) -> None:
    """Save the meaning schema to a project."""
    schema_path = project_root / MEANING_DIR / SCHEMA_FILENAME
    save_yaml(schema_path, schema.to_dict())


def load_config(project_root: Path) -> MeaningConfig:
    """Load the meaning config from a project."""
    config_path = project_root / MEANING_DIR / CONFIG_FILENAME
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")
    data = load_yaml(config_path)
    return MeaningConfig.from_dict(data)


def save_config(project_root: Path, config: MeaningConfig) -> None:
    """Save the meaning config to a project."""
    config_path = project_root / MEANING_DIR / CONFIG_FILENAME
    save_yaml(config_path, config.to_dict())
