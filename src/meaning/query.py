"""
Meaning: Query engine and display functions.

This module handles semantic queries against the index and result display.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from meaning.models import (
    FileEntry,
    MeaningIndex,
    MeaningSchema,
)


@dataclass
class QueryResult:
    """Result from a semantic query."""

    files: list[FileEntry]
    explanation: str
    query_type: str


def query_index(index: MeaningIndex, schema: MeaningSchema, query: str) -> QueryResult:
    """
    Natural language query against the semantic index.

    Supports:
    - Tag searches: "test files", "config files", "API files"
    - Relationship queries: "what tests X", "what documents Y", "what imports Z"
    - Status queries: "what needs review", "what is stale"
    - Temporal queries: "what changed recently", "latest files"
    - Concept queries: "show me the core library"
    - Intent searches: "files that do parsing", "files about authentication"
    """
    q = query.lower().strip()
    results: list[FileEntry] = []
    explanation = ""
    query_type = "unknown"

    # Status queries
    if "need" in q and "review" in q:
        results = index.files_needing_review()
        explanation = "Files flagged for review"
        query_type = "status"

    elif "stale" in q:
        results = [f for f in index.files if f.is_stale()]
        explanation = "Files not verified in the last 7 days"
        query_type = "status"

    # Relationship queries - "what tests X", "what documents Y", "what imports Z"
    elif any(word in q for word in ["what", "which", "show"]) and any(
        rel in q for rel in ["test", "document", "import", "implement", "configure", "call"]
    ):
        # Extract relationship type
        rel_type = None
        for rel in ["tests", "documents", "imports", "implements", "configures", "calls"]:
            if rel.rstrip("s") in q:  # Handle singular forms
                rel_type = rel
                break

        if rel_type:
            # Try to extract target file from query
            target = None
            for file in index.files:
                # Check if any part of the file path is mentioned
                path_parts = file.path.replace("/", " ").replace("_", " ").replace(".", " ").split()
                if any(part.lower() in q for part in path_parts if len(part) > 3):
                    target = file.path
                    break

            if target:
                # Find files with this relationship to the target
                results = [
                    f
                    for f in index.files
                    if any(r.type == rel_type and r.target == target for r in f.relationships)
                ]
                explanation = f"Files that {rel_type} {target}"
                query_type = "relationship"
            else:
                # Show all files with this relationship type
                results = [
                    f for f in index.files if any(r.type == rel_type for r in f.relationships)
                ]
                explanation = f"Files with '{rel_type}' relationships"
                query_type = "relationship"

    # Concept queries
    elif "concept" in q or any(c.name.replace("-", " ") in q for c in index.concepts):
        # Find matching concept
        for concept in index.concepts:
            if concept.name.replace("-", " ") in q:
                results = [f for f in index.files if f.path in concept.files]
                explanation = f"Files in concept '{concept.name}': {concept.description}"
                query_type = "concept"
                break

    # Tag queries - look for common tag patterns
    elif any(word in q for word in ["file", "show", "find", "list"]):
        # Extract potential tag keywords
        tag_keywords = []

        # Check against schema vocabulary
        for _category, tags in schema.tag_vocabulary.items():
            for tag in tags:
                if tag in q or tag.replace("-", " ") in q:
                    tag_keywords.append(tag)

        if tag_keywords:
            results = index.find_by_tags(tag_keywords, match_all=False)
            explanation = f"Files tagged with: {', '.join(tag_keywords)}"
            query_type = "tag"

    # Temporal queries
    elif "recent" in q or "latest" in q or "changed" in q:
        # Sort by last_verified, most recent first
        results = sorted(index.files, key=lambda f: f.last_verified, reverse=True)[:10]
        explanation = "10 most recently updated files"
        query_type = "temporal"

    # Intent search (fallback) - keyword matching in intent strings
    if not results:
        # Extract meaningful keywords from query (skip common words)
        stop_words = {
            "what",
            "where",
            "who",
            "when",
            "why",
            "how",
            "is",
            "are",
            "the",
            "a",
            "an",
            "do",
            "does",
            "did",
            "file",
            "files",
            "show",
            "find",
            "list",
            "me",
            "all",
        }
        keywords = [word for word in q.split() if word not in stop_words and len(word) > 3]

        if keywords:
            for file in index.files:
                intent_lower = file.intent.lower()
                # Match if any keyword is in the intent
                if any(kw in intent_lower for kw in keywords):
                    results.append(file)

            if results:
                explanation = f"Files with intents matching: {', '.join(keywords)}"
                query_type = "intent"

    # No results found
    if not results:
        explanation = f"No files found matching query: '{query}'"
        query_type = "no_match"

    return QueryResult(files=results, explanation=explanation, query_type=query_type)


def display_query_results(result: QueryResult, max_results: int = 20) -> None:
    """Display query results in a formatted way."""
    print(f"🔍 Query Results: {result.explanation}")
    print(f"   Type: {result.query_type}")
    print()

    if not result.files:
        print("  No files found.")
        return

    total = len(result.files)
    showing = min(total, max_results)

    print(f"  Found {total} file{'s' if total != 1 else ''} (showing {showing}):")
    print()

    for i, file in enumerate(result.files[:max_results], 1):
        # File path with status indicator
        status_icon = "⚠️ " if file.needs_review else "  "
        print(f"  {i}. {status_icon}{file.path}")

        # Intent (truncated)
        intent = file.intent[:80] + "..." if len(file.intent) > 80 else file.intent
        print(f'      "{intent}"')

        # Tags
        if file.tags:
            tags_str = ", ".join(file.tags[:5])
            if len(file.tags) > 5:
                tags_str += f" +{len(file.tags) - 5} more"
            print(f"      Tags: {tags_str}")

        # Key relationships
        if file.relationships:
            rel_summary = {}
            for rel in file.relationships:
                if rel.type not in rel_summary:
                    rel_summary[rel.type] = []
                if rel.target:
                    rel_summary[rel.type].append(rel.target)

            rel_strs = [f"{k}({len(v)})" for k, v in rel_summary.items()]
            print(f"      Relationships: {', '.join(rel_strs)}")

        print()

    if total > max_results:
        print(f"  ... and {total - max_results} more")
        print()


def display_status(project_root: Path) -> None:
    """Display a comprehensive status overview of the meaning index."""
    # Import here to avoid circular imports
    from meaning.index_io import load_config, load_index, load_schema
    from meaning.project import detect_project_type, scan_project_files
    from meaning.validation import validate_index

    try:
        index = load_index(project_root)
        schema = load_schema(project_root)
        config = load_config(project_root)
    except FileNotFoundError:
        print(f"❌ No .meaning/ directory found in {project_root}")
        print("\n💡 Initialize with: python -m meaning init")
        return

    # Validate to get health metrics
    result = validate_index(index, schema, config, project_root)

    # Detect project info
    project_type = detect_project_type(project_root)
    project_name = project_root.name

    # Calculate metrics
    total_files = len(index.files)
    needs_review = len(index.files_needing_review())
    stale = sum(1 for f in index.files if f.is_stale())

    # Find unindexed files
    all_files = scan_project_files(project_root, config)
    indexed_paths = {f.path for f in index.files}
    unindexed = [f for f in all_files if f not in indexed_paths]

    # Find latest session note
    agent_sessions = project_root / ".agent-sessions"
    latest_session = None
    if agent_sessions.exists():
        session_files = sorted(
            agent_sessions.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True
        )
        if session_files:
            latest_session = session_files[0].name

    # Print status
    print("📊 Meaning Index Status")
    print()
    print(f"Project: {project_name} ({project_type})")
    print(f"Version: {index.version}")
    print(f"Last Updated: {index.last_updated.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Concepts section
    if index.concepts:
        print("━" * 60)
        print(f"CONCEPTS ({len(index.concepts)})")
        print("━" * 60)
        print()
        for concept in index.concepts:
            file_count = len(concept.files)
            print(f"  {concept.name} ({file_count} files)")
            print(f"    └─ {concept.entry_point}")

            # Show intent from entry point file
            entry = index.get_file(concept.entry_point)
            if entry and entry.intent:
                intent = entry.intent[:70] + "..." if len(entry.intent) > 70 else entry.intent
                print(f'       "{intent}"')
            print()
    else:
        print("⚠️  No concepts defined")
        print()

    # Health section
    print("━" * 60)
    print("HEALTH")
    print("━" * 60)
    print()

    # Files
    status_icon = "✅" if total_files > 0 else "⚠️ "
    print(f"  {status_icon} {total_files} files indexed")

    # Needs review
    if needs_review > 0:
        print(f"  ⚠️  {needs_review} need review")
    else:
        print("  ✅ 0 need review")

    # Stale
    if stale > 0:
        print(f"  ⚠️  {stale} stale entries")
    else:
        print("  ✅ 0 stale entries")

    # Unindexed
    if unindexed:
        print(f"  ⚠️  {len(unindexed)} unindexed files")
    else:
        print("  ✅ 0 unindexed files")

    # Validation errors
    if result.errors:
        print(f"  ❌ {len(result.errors)} validation errors")
    else:
        print("  ✅ 0 validation errors")

    print()

    # Recent activity
    if latest_session:
        print("━" * 60)
        print("RECENT ACTIVITY")
        print("━" * 60)
        print()
        print(f"  Latest session: {latest_session}")
        print()

    # Quick actions
    print("━" * 60)
    print("QUICK ACTIONS")
    print("━" * 60)
    print()

    if needs_review > 0:
        print("  python -m meaning review    # Review flagged files")
    if unindexed:
        print("  python -m meaning update    # Sync with filesystem")
    if result.errors:
        print("  python -m meaning validate  # See detailed errors")

    print('  python -m meaning query "<question>"  # Semantic search')
    print()
