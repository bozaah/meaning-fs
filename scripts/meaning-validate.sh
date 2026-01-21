#!/bin/bash
# meaning-validate.sh
# Called at end of Claude session (Stop hook)
# Validates index consistency and reports files needing review

set -euo pipefail

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
SCHEMA_FILE="$PROJECT_ROOT/.meaning/schema.yaml"

# Check if index exists
if [ ! -f "$INDEX_FILE" ]; then
    echo '{"status": "error", "message": "Index file not found"}'
    exit 0
fi

# Run validation using Python
python3 << 'PYTHON_SCRIPT'
import sys
import os
import yaml
import fnmatch
from datetime import datetime, timezone
from pathlib import Path

project_root = os.environ.get('PROJECT_ROOT', os.getcwd())
index_file = os.path.join(project_root, '.meaning', 'index.yaml')
config_file = os.path.join(project_root, '.meaning', 'config.yaml')
schema_file = os.path.join(project_root, '.meaning', 'schema.yaml')

def load_yaml_file(filepath):
    if not os.path.exists(filepath):
        return {}
    with open(filepath, 'r') as f:
        return yaml.safe_load(f) or {}

def is_excluded(path, config):
    exclude = config.get('exclude', {})
    include = config.get('include', {})
    
    for inc_path in include.get('paths', []):
        if path.startswith(inc_path) or path == inc_path:
            return False
    
    for exc_path in exclude.get('paths', []):
        if path.startswith(exc_path) or path == exc_path:
            return True
    
    for pattern in exclude.get('patterns', []):
        if fnmatch.fnmatch(path, pattern):
            return True
        if '**' in pattern:
            import re
            regex = pattern.replace('**', '.*').replace('*', '[^/]*')
            if re.match(regex, path):
                return True
    
    return False

try:
    index = load_yaml_file(index_file)
    config = load_yaml_file(config_file)
    schema = load_yaml_file(schema_file)
    
    files = index.get('files', [])
    indexed_paths = {f.get('path') for f in files}
    
    # Settings
    settings = config.get('settings', {})
    stale_days = settings.get('stale_threshold_days', 7)
    warn_unknown_tags = settings.get('warn_on_unknown_tags', True)
    
    # Collect valid tags from schema
    valid_tags = set()
    custom_prefix = schema.get('custom_prefix', 'x-')
    for category_tags in schema.get('tag_vocabulary', {}).values():
        valid_tags.update(category_tags)
    
    # Collect valid relationship types
    valid_rel_types = {r.get('name') for r in schema.get('relationship_types', [])}
    
    errors = []
    warnings = []
    needs_review = []
    stale = []
    
    now = datetime.now(timezone.utc)
    
    for entry in files:
        path = entry.get('path', '')
        
        # Check file exists
        full_path = os.path.join(project_root, path)
        if not os.path.exists(full_path):
            errors.append(f"Indexed file does not exist: {path}")
        
        # Check needs_review
        if entry.get('needs_review', False):
            needs_review.append(path)
        
        # Check staleness
        last_verified = entry.get('last_verified')
        if last_verified:
            if isinstance(last_verified, str):
                try:
                    last_dt = datetime.fromisoformat(last_verified.replace('Z', '+00:00'))
                except:
                    last_dt = now
            else:
                last_dt = now
            
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=timezone.utc)
            
            delta = now - last_dt
            if delta.days > stale_days:
                stale.append(path)
        
        # Check tags
        if warn_unknown_tags:
            for tag in entry.get('tags', []):
                if tag not in valid_tags and not tag.startswith(custom_prefix):
                    warnings.append(f"Unknown tag '{tag}' on: {path}")
        
        # Check relationships
        for rel in entry.get('relationships', []):
            rel_type = rel.get('type', '')
            if valid_rel_types and rel_type not in valid_rel_types:
                warnings.append(f"Unknown relationship type '{rel_type}' on: {path}")
            
            target = rel.get('target') or rel.get('source')
            if target and target not in indexed_paths:
                errors.append(f"Dangling relationship to '{target}' from: {path}")
    
    # Check for unindexed files (walk filesystem)
    unindexed = []
    for root, dirs, filenames in os.walk(project_root):
        # Skip hidden dirs
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        
        for filename in filenames:
            if filename.startswith('.'):
                continue
            
            full = os.path.join(root, filename)
            rel = os.path.relpath(full, project_root)
            
            if is_excluded(rel, config):
                continue
            
            if rel not in indexed_paths:
                unindexed.append(rel)
    
    if unindexed and len(unindexed) <= 10:
        for path in unindexed:
            warnings.append(f"File not indexed: {path}")
    elif unindexed:
        warnings.append(f"{len(unindexed)} files not indexed")
    
    # Build summary
    summary = {
        "total_files": len(files),
        "needs_review": len(needs_review),
        "stale": len(stale),
        "unindexed": len(unindexed),
        "errors": len(errors),
        "warnings": len(warnings)
    }
    
    import json
    result = {
        "status": "ok" if not errors else "error",
        "summary": summary,
        "errors": errors[:10],  # Limit output
        "warnings": warnings[:10],
        "files_needing_review": needs_review[:20],
        "stale_files": stale[:10]
    }
    
    print(json.dumps(result, indent=2))

except Exception as e:
    import json
    print(json.dumps({"status": "error", "message": str(e)}))

PYTHON_SCRIPT
