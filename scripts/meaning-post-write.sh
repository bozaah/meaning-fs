#!/bin/bash
# meaning-post-write.sh
# Called after file write/create/edit operations
# Updates .meaning/index.yaml to track modified files

set -euo pipefail

# Read JSON input from stdin
INPUT=$(cat)

# Extract the file path from tool_input
# Handles different tool input formats
FILE_PATH=$(echo "$INPUT" | python3 -c "
import sys
import json

data = json.load(sys.stdin)
tool_input = data.get('tool_input', {})

# Try different field names for the path
path = tool_input.get('path') or tool_input.get('file_path') or tool_input.get('filename', '')
print(path)
" 2>/dev/null || echo "")

# If we couldn't extract a path, exit silently
if [ -z "$FILE_PATH" ]; then
    echo '{"status": "skip", "message": "Could not extract file path from tool input"}'
    exit 0
fi

# Find project root (directory containing .meaning/)
find_project_root() {
    local dir="$PWD"
    while [ "$dir" != "/" ]; do
        if [ -d "$dir/.meaning" ]; then
            echo "$dir"
            return 0
        fi
        dir=$(dirname "$dir")
    done
    return 1
}

PROJECT_ROOT=$(find_project_root) || {
    echo '{"status": "skip", "message": "No .meaning directory found"}'
    exit 0
}

INDEX_FILE="$PROJECT_ROOT/.meaning/index.yaml"
CONFIG_FILE="$PROJECT_ROOT/.meaning/config.yaml"

# Check if index exists
if [ ! -f "$INDEX_FILE" ]; then
    echo '{"status": "error", "message": "Index file not found"}'
    exit 0
fi

# Make path relative to project root
REL_PATH=$(python3 -c "
import os
import sys

file_path = sys.argv[1]
project_root = sys.argv[2]

# Handle absolute vs relative paths
if os.path.isabs(file_path):
    try:
        rel = os.path.relpath(file_path, project_root)
    except ValueError:
        rel = file_path
else:
    rel = file_path

# Normalize
rel = rel.lstrip('./')
print(rel)
" "$FILE_PATH" "$PROJECT_ROOT")

# Update the index using Python
python3 << PYTHON_SCRIPT
import sys
import os
import yaml
import fnmatch
from datetime import datetime, timezone

project_root = "$PROJECT_ROOT"
index_file = "$INDEX_FILE"
config_file = "$CONFIG_FILE"
rel_path = "$REL_PATH"

# Load config to check exclusions
def is_excluded(path, config):
    exclude = config.get('exclude', {})
    include = config.get('include', {})
    
    # Check explicit includes first
    for inc_path in include.get('paths', []):
        if path.startswith(inc_path) or path == inc_path:
            return False
    
    # Check explicit path excludes
    for exc_path in exclude.get('paths', []):
        if path.startswith(exc_path) or path == exc_path:
            return True
    
    # Check pattern excludes
    for pattern in exclude.get('patterns', []):
        if fnmatch.fnmatch(path, pattern):
            return True
        # Handle ** patterns
        if '**' in pattern:
            import re
            regex = pattern.replace('**', '.*').replace('*', '[^/]*')
            if re.match(regex, path):
                return True
    
    return False

try:
    # Load config
    config = {}
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f) or {}
    
    # Check if file is excluded
    if is_excluded(rel_path, config):
        print('{"status": "skip", "message": "File is excluded by config"}')
        sys.exit(0)
    
    # Load index
    with open(index_file, 'r') as f:
        index = yaml.safe_load(f) or {}
    
    if 'files' not in index:
        index['files'] = []
    
    # Find existing entry
    existing_idx = None
    for i, entry in enumerate(index['files']):
        if entry.get('path') == rel_path:
            existing_idx = i
            break
    
    now = datetime.now(timezone.utc).isoformat()
    
    if existing_idx is not None:
        # Update existing entry
        index['files'][existing_idx]['needs_review'] = True
        index['files'][existing_idx]['last_verified'] = now
        action = "updated"
    else:
        # Add new skeleton entry
        new_entry = {
            'path': rel_path,
            'intent': '[NEEDS REVIEW] Created/modified by agent',
            'status': 'active',
            'needs_review': True,
            'last_verified': now,
            'tags': [],
            'relationships': []
        }
        index['files'].append(new_entry)
        action = "added"
    
    # Update last_updated timestamp
    index['last_updated'] = now
    
    # Write back
    with open(index_file, 'w') as f:
        yaml.dump(index, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
    
    print(f'{{"status": "ok", "action": "{action}", "path": "{rel_path}"}}')

except Exception as e:
    print(f'{{"status": "error", "message": "{str(e)}"}}')
    sys.exit(0)

PYTHON_SCRIPT
