#!/usr/bin/env bash
# Validate the .meaning/ index for this project
# Usage: ./scripts/validate-meaning.sh

set -euo pipefail

# Change to project root (parent of scripts/)
cd "$(dirname "$0")/.."

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Run validation
python -c "
from meaning_core import load_index, load_schema, load_config, validate_index
from pathlib import Path

project_dir = Path('.')
index = load_index(project_dir)
schema = load_schema(project_dir)
config = load_config(project_dir)

result = validate_index(index, schema, config, project_dir)

print('📋 Meaning Index Validation')
print('=' * 60)
print(f'✓ Valid: {result.is_valid}')
print(f'  Errors: {len(result.errors)}')
print(f'  Warnings: {len(result.warnings)}')
print()

if result.errors:
    print('❌ ERRORS:')
    for error in result.errors:
        print(f'  • {error}')
    print()
    exit(1)

if result.warnings:
    print('⚠️  WARNINGS:')
    shown = 0
    for warning in result.warnings:
        if 'not indexed' not in warning:  # Skip unindexed file warnings for now
            print(f'  • {warning}')
            shown += 1
    unindexed = len([w for w in result.warnings if 'not indexed' in w])
    if unindexed:
        print(f'  • {unindexed} files not yet indexed (expected)')
    print()

if not result.errors:
    print('✅ Index is valid!')
print('=' * 60)
"
