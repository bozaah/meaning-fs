"""
Meaning: Constants and default values.

This module contains all constants used across the meaning package.
"""

VERSION = "0.1"
INDEX_FILENAME = "index.yaml"
SCHEMA_FILENAME = "schema.yaml"
CONFIG_FILENAME = "config.yaml"
MEANING_DIR = ".meaning"

DEFAULT_STALE_THRESHOLD_DAYS = 7
DEFAULT_MAX_INTENT_LENGTH = 280
DEFAULT_REVIEW_THRESHOLD = 0.8

VALID_STATUSES = {"active", "draft", "deprecated", "generated"}
