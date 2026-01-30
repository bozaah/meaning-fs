#!/usr/bin/env python3
"""
Run inference on files and display results.

Usage:
    python scripts/run-inference.py <file_path> [--project-dir .]
    python scripts/run-inference.py --all [--project-dir .]
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from meaning.meaning_core import load_config, load_index, load_schema
from meaning.meaning_inference import infer_file_metadata


def display_inference_result(result):
    """Display inference results in a nice format."""
    print(f"\n{'=' * 70}")
    print(f"File: {result.path}")
    print(f"{'=' * 70}")

    # Tags
    if result.tags:
        print(f"\nTags ({len(result.tags)}):")
        for tag in result.tags:
            confidence_bar = "█" * int(tag.confidence * 10)
            print(f"   • {tag.tag:20} [{confidence_bar:10}] {tag.confidence:.2f}")
            print(f"     Reason: {tag.reason}")

    # Intent
    if result.intent:
        print(f"\nIntent (confidence: {result.intent.confidence:.2f}):")
        print(f"   {result.intent.intent}")
        print(f"   Reason: {result.intent.reason}")

    # Relationships
    if result.relationships:
        print(f"\nRelationships ({len(result.relationships)}):")
        for rel in result.relationships:
            confidence_bar = "█" * int(rel.confidence * 10)
            print(f"   • {rel.relationship.type:15} → {rel.relationship.target}")
            print(f"     [{confidence_bar:10}] {rel.confidence:.2f}")
            print(f"     Reason: {rel.reason}")

    # Errors and warnings
    if result.errors:
        print(f"\nErrors ({len(result.errors)}):")
        for error in result.errors:
            print(f"   • {error}")

    if result.warnings:
        print(f"\nWarnings ({len(result.warnings)}):")
        for warning in result.warnings:
            print(f"   • {warning}")

    if not result.tags and not result.intent and not result.relationships:
        print("\n   (No inferences generated)")


def main():
    """Main CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Run inference on files")
    parser.add_argument("file_path", nargs="?", help="File to analyze (or --all)")
    parser.add_argument("--all", action="store_true", help="Run inference on all unindexed files")
    parser.add_argument("--project-dir", default=".", help="Project root directory (default: .)")
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.5,
        help="Minimum confidence to show (default: 0.5)",
    )

    args = parser.parse_args()

    project_dir = Path(args.project_dir)

    # Load index and schema
    try:
        index = load_index(project_dir)
        schema = load_schema(project_dir)
        config = load_config(project_dir)
    except Exception as e:
        print(f"Error loading meaning data: {e}")
        sys.exit(1)

    if args.all:
        # Find all unindexed files
        print("Finding unindexed files...")
        indexed_paths = {entry.path for entry in index.files}

        # Walk project directory
        unindexed = []
        for path in project_dir.rglob("*"):
            if path.is_file():
                rel_path = path.relative_to(project_dir)
                rel_path_str = str(rel_path)

                # Check if excluded
                if config.is_excluded(rel_path_str):
                    continue

                # Check if already indexed
                if rel_path_str not in indexed_paths:
                    unindexed.append(rel_path_str)

        print(f"Found {len(unindexed)} unindexed files\n")

        # Run inference on each
        for file_path in unindexed[:10]:  # Limit to first 10 for demo
            result = infer_file_metadata(file_path, project_dir, index, schema)
            display_inference_result(result)

        if len(unindexed) > 10:
            print(f"\n... and {len(unindexed) - 10} more files")

    else:
        if not args.file_path:
            parser.print_help()
            sys.exit(1)

        # Run inference on single file
        result = infer_file_metadata(args.file_path, project_dir, index, schema)
        display_inference_result(result)

    print(f"\n{'=' * 70}\n")


if __name__ == "__main__":
    main()
