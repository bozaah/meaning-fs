"""
Meaning: Query engine and display functions.

This module handles semantic queries against the index and result display.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from meaning.models import (
    Collection,
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
    collections: list[Collection] = field(default_factory=list)


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
    collections: list[Collection] = []
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

    # Collection queries
    elif "collection" in q or any(c.name.replace("-", " ") in q for c in index.collections):
        if any(word in q for word in ["list", "show", "all"]):
            collections = list(index.collections)
            explanation = "All collections"
            query_type = "collection"
        else:
            matches = [c for c in index.collections if c.name.replace("-", " ") in q or c.name in q]
            if matches:
                collections = matches
                explanation = "Matching collections"
                query_type = "collection"

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
    if not results and not collections:
        explanation = f"No files found matching query: '{query}'"
        query_type = "no_match"

    return QueryResult(
        files=results,
        collections=collections,
        explanation=explanation,
        query_type=query_type,
    )


def display_query_results(result: QueryResult, max_results: int = 20) -> None:
    """Display query results in a formatted way."""
    print(f"Query Results: {result.explanation}")
    print(f"   Type: {result.query_type}")
    print()

    if not result.files and not result.collections:
        print("  No files found.")
        return

    if result.collections:
        total_collections = len(result.collections)
        showing_collections = min(total_collections, max_results)
        print(
            f"  Found {total_collections} collection{'s' if total_collections != 1 else ''} (showing {showing_collections}):"
        )
        print()
        for i, collection in enumerate(result.collections[:max_results], 1):
            print(f"  {i}. {collection.name}")
            print(f"      Pattern: {collection.pattern}")
            print(f'      "{collection.intent}"')
            if collection.tags:
                tags_str = ", ".join(collection.tags[:5])
                if len(collection.tags) > 5:
                    tags_str += f" +{len(collection.tags) - 5} more"
                print(f"      Tags: {tags_str}")
            if collection.relationships:
                rel_summary: dict[str, list[str]] = {}
                for rel in collection.relationships:
                    if rel.type not in rel_summary:
                        rel_summary[rel.type] = []
                    if rel.target:
                        rel_summary[rel.type].append(rel.target)
                rel_strs = [f"{k}({len(v)})" for k, v in rel_summary.items()]
                print(f"      Relationships: {', '.join(rel_strs)}")
            print()

        if total_collections > showing_collections:
            print(f"  ... and {total_collections - showing_collections} more")
            print()

    if not result.files:
        return

    total = len(result.files)
    showing = min(total, max_results)

    print(f"  Found {total} file{'s' if total != 1 else ''} (showing {showing}):")
    print()

    for i, file in enumerate(result.files[:max_results], 1):
        # File path with status indicator
        status_icon = "[WARN] " if file.needs_review else ""
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
            rel_summary: dict[str, list[str]] = {}
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
    from datetime import datetime, timezone

    from meaning.index_io import load_config, load_index, load_schema
    from meaning.project import detect_project_type, scan_project_files
    from meaning.validation import validate_index

    try:
        index = load_index(project_root)
        schema = load_schema(project_root)
        config = load_config(project_root)
    except FileNotFoundError:
        print(f"[!] No .meaning/ directory found in {project_root}")
        print("\nInitialize with: python -m meaning init")
        return

    # Validate to get health metrics
    result = validate_index(index, schema, config, project_root)

    # Detect project info
    project_type = detect_project_type(project_root)
    project_name = project_root.name

    # Calculate metrics
    total_files = len(index.files)
    needs_review_list = index.files_needing_review()
    needs_review = len(needs_review_list)
    stale = sum(1 for f in index.files if f.is_stale())

    # Find unindexed files
    all_files = scan_project_files(project_root, config)
    indexed_paths = {f.path for f in index.files}
    unindexed = [f for f in all_files if f not in indexed_paths and not index.is_collected(f)]

    # Calculate coverage (indexed + collection coverage only)
    total_project_files = len(all_files)
    covered_files = {f for f in indexed_paths if f in all_files}
    covered_files.update(f for f in all_files if index.is_collected(f))
    covered_count = len(covered_files)
    coverage_pct = (covered_count / total_project_files * 100) if total_project_files > 0 else 0

    # Count relationships and unique tags
    total_relationships = sum(len(f.relationships) for f in index.files)
    all_tags = set()
    for f in index.files:
        all_tags.update(f.tags)
    unique_tags = len(all_tags)

    # Time since last update
    now = datetime.now(timezone.utc)
    time_since_update = now - index.last_updated
    if time_since_update.days > 0:
        last_update_str = f"{time_since_update.days}d ago"
    elif time_since_update.seconds > 3600:
        last_update_str = f"{time_since_update.seconds // 3600}h ago"
    elif time_since_update.seconds > 60:
        last_update_str = f"{time_since_update.seconds // 60}m ago"
    else:
        last_update_str = "just now"

    # Find latest session note
    agent_sessions = project_root / ".agent-sessions"
    latest_session = None
    session_time = None
    if agent_sessions.exists():
        session_files = sorted(
            agent_sessions.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True
        )
        if session_files:
            latest_session = session_files[0].name
            session_mtime = datetime.fromtimestamp(
                session_files[0].stat().st_mtime, tz=timezone.utc
            )
            session_delta = now - session_mtime
            if session_delta.days > 0:
                session_time = f"{session_delta.days}d ago"
            elif session_delta.seconds > 3600:
                session_time = f"{session_delta.seconds // 3600}h ago"
            elif session_delta.seconds > 60:
                session_time = f"{session_delta.seconds // 60}m ago"
            else:
                session_time = "just now"

    # Header
    print("=" * 70)
    print("MEANING INDEX STATUS")
    print("=" * 70)
    print()
    print(f"Project: {project_name} ({project_type})")
    print(f"Coverage: {covered_count}/{total_project_files} files ({coverage_pct:.0f}%)")
    print(f"Last Updated: {last_update_str}")
    print()

    # Project Overview - entry points and high-level stats
    if index.concepts:
        print("━" * 70)
        print("PROJECT OVERVIEW")
        print("━" * 70)
        print()
        print("  Entry Points:")
        for concept in index.concepts:
            file_count = len(concept.files)
            print(
                f"    • {concept.name.replace('-', ' ').title()} ({file_count} files) → {concept.entry_point}"
            )
        print()
        print(
            f"  Coverage: {covered_count}/{total_project_files} files indexed ({coverage_pct:.0f}%)"
        )

        # Count relationship types
        rel_types: dict[str, int] = {}
        for f in index.files:
            for rel in f.relationships:
                rel_types[rel.type] = rel_types.get(rel.type, 0) + 1
        rel_summary = ", ".join(sorted(rel_types.keys())[:3])
        if len(rel_types) > 3:
            rel_summary += f", +{len(rel_types) - 3} more"

        print(f"  Relationships: {total_relationships} tracked ({rel_summary})")

        if latest_session and session_time:
            print(f"  Last session: {latest_session} ({session_time})")
        print()

    # Attention section - show problems first
    has_issues = needs_review > 0 or len(unindexed) > 0 or stale > 0 or len(result.errors) > 0

    if has_issues:
        print("-" * 70)
        print("ATTENTION NEEDED")
        print("-" * 70)
        print()

        if needs_review > 0:
            print(f"  [{needs_review}] Files need review")
            for i, entry in enumerate(needs_review_list[:3], 1):
                reason = (
                    "auto-inferred" if entry.intent.startswith("[NEEDS REVIEW]") else "modified"
                )
                print(f"      {i}. {entry.path} ({reason})")
            if needs_review > 3:
                print(f"      ... and {needs_review - 3} more")
            print()

        if len(unindexed) > 0:
            print(f"  [{len(unindexed)}] Files unindexed")
            # Show first 3 unindexed files
            for i, path in enumerate(unindexed[:3], 1):
                print(f"      {i}. {path}")
            if len(unindexed) > 3:
                print(f"      ... and {len(unindexed) - 3} more")
            print()

        if stale > 0:
            print(f"  [{stale}] Files stale (not verified in >{config.stale_threshold_days} days)")
            print()

        if result.errors:
            print(f"  [{len(result.errors)}] Validation errors")
            for i, err in enumerate(result.errors[:3], 1):
                print(f"      {i}. {err}")
            if len(result.errors) > 3:
                print(f"      ... and {len(result.errors) - 3} more")
            print()

    # Semantic map - concepts as entry points
    if index.concepts:
        print("-" * 70)
        print("SEMANTIC MAP")
        print("-" * 70)
        print()
        for concept in index.concepts:
            file_count = len(concept.files)
            print(f"  [{concept.name}] {file_count} files -> {concept.entry_point}")
            # Show description instead of entry point intent
            if concept.description:
                desc = (
                    concept.description[:65] + "..."
                    if len(concept.description) > 65
                    else concept.description
                )
                print(f"      {desc}")
        print()

    # Index health summary
    print("-" * 70)
    print("INDEX HEALTH")
    print("-" * 70)
    print()

    health_items = [
        ("Indexed", total_files, total_files > 0),
        ("Need Review", needs_review, needs_review == 0),
        ("Stale", stale, stale == 0),
        ("Unindexed", len(unindexed), len(unindexed) == 0),
        ("Errors", len(result.errors), len(result.errors) == 0),
    ]

    for label, count, is_good in health_items:
        status = "[OK]" if is_good else "[!]"
        print(f"  {status} {label}: {count}")
    print()

    # Metadata stats
    print("-" * 70)
    print("METADATA")
    print("-" * 70)
    print()
    print(f"  Relationships: {total_relationships} tracked")
    print(f"  Tags: {unique_tags} unique types")
    print(f"  Concepts: {len(index.concepts)} defined")
    print()

    # Recent context
    if latest_session:
        print("-" * 70)
        print("RECENT CONTEXT")
        print("-" * 70)
        print()
        print(f"  Last session: {latest_session}")
        if session_time:
            print(f"  Time: {session_time}")
        print()

    # Next steps - actionable commands
    print("-" * 70)
    print("NEXT STEPS")
    print("-" * 70)
    print()

    if needs_review > 0:
        print("  meaning review              # Review and approve inferred metadata")
    if len(unindexed) > 0:
        print("  meaning update              # Sync with filesystem changes")
    if result.errors:
        print("  meaning validate            # See detailed validation errors")

    print('  meaning query "<question>"  # Semantic search for files/concepts')

    # Show example query based on concepts
    if index.concepts:
        first_concept = index.concepts[0].name
        print(f'  meaning query "{first_concept}"  # Explore {first_concept} files')

    print()
    print("=" * 70)
    print()
