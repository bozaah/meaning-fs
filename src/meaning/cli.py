"""
Meaning: Command-line interface.

This module contains the CLI entry point and command routing.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from meaning.constants import DEFAULT_REVIEW_THRESHOLD
from meaning.index_io import load_config, load_index, load_schema, save_index
from meaning.index_ops import (
    apply_inference_to_entry,
    entry_from_inference,
    find_deleted_files,
    find_modified_files,
    find_unindexed_files,
    preview_inference_changes,
    preview_inference_diff,
    prune_excluded_entries,
)
from meaning.project import (
    detect_project_type,
    is_git_repo,
    meaning_dir_exists,
    scan_project_files,
)
from meaning.query import display_query_results, display_status, query_index
from meaning.validation import validate_index


def main() -> None:
    """Command-line interface for Meaning."""
    parser = argparse.ArgumentParser(description="Meaning: Semantic File Index for AI Agents")
    subparsers = parser.add_subparsers(dest="command", required=True)

    status_parser = subparsers.add_parser("status", help="Show project status overview")
    status_parser.add_argument("project_root", nargs="?", default=".")

    query_parser = subparsers.add_parser("query", help="Run a semantic query")
    query_parser.add_argument("query", nargs="+")
    query_parser.add_argument("--project-root", default=".")

    validate_parser = subparsers.add_parser("validate", help="Validate the meaning index")
    validate_parser.add_argument("project_root", nargs="?", default=".")

    detect_parser = subparsers.add_parser("detect", help="Detect project type and git status")
    detect_parser.add_argument("project_root", nargs="?", default=".")

    init_parser = subparsers.add_parser("init", help="Initialize .meaning/ in a project")
    init_parser.add_argument("project_root", nargs="?", default=".")
    init_parser.add_argument("--type", dest="project_type", default=None)
    init_parser.add_argument("--limit", type=int, default=50)
    init_parser.add_argument("--install-hooks", action="store_true")
    init_parser.add_argument("--force-hooks", action="store_true")
    init_parser.add_argument(
        "--with-skills", action="store_true", help="Install Claude Code skills"
    )
    init_parser.add_argument(
        "--skip-crawl", action="store_true", help="Skip file scanning/inference"
    )

    update_parser = subparsers.add_parser("update", help="Sync index with filesystem changes")
    update_parser.add_argument("project_root", nargs="?", default=".")
    update_mode = update_parser.add_mutually_exclusive_group()
    update_mode.add_argument("--new", action="store_true")
    update_mode.add_argument("--modified", action="store_true")
    update_mode.add_argument("--deleted", action="store_true")
    update_mode.add_argument("--all", action="store_true")
    update_parser.add_argument("--re-infer", action="store_true")
    update_parser.add_argument("--dry-run", action="store_true")
    update_parser.add_argument("--threshold", type=float, default=DEFAULT_REVIEW_THRESHOLD)

    review_parser = subparsers.add_parser("review", help="Review and accept inferred metadata")
    review_parser.add_argument("project_root", nargs="?", default=".")
    review_parser.add_argument("--interactive", action="store_true")
    review_parser.add_argument("--file", dest="file_path", default=None)
    review_parser.add_argument("--dry-run", action="store_true")
    review_parser.add_argument("--threshold", type=float, default=DEFAULT_REVIEW_THRESHOLD)

    args = parser.parse_args()

    if args.command == "status":
        display_status(Path(args.project_root).resolve())
        return

    if args.command == "query":
        project_root = Path(args.project_root).resolve()
        query_str = " ".join(args.query)
        try:
            index = load_index(project_root)
            schema = load_schema(project_root)
            result = query_index(index, schema, query_str)
            display_query_results(result)
        except FileNotFoundError:
            print(f"❌ No .meaning/ directory found in {project_root}")
            print("\n💡 Initialize with: python -m meaning init")
            sys.exit(1)
        return

    if args.command == "validate":
        project_root = Path(args.project_root).resolve()
        try:
            index = load_index(project_root)
            schema = load_schema(project_root)
            config = load_config(project_root)
            result = validate_index(index, schema, config, project_root)

            print(f"Valid: {result.is_valid}")
            if result.errors:
                print(f"\nErrors ({len(result.errors)}):")
                for err in result.errors:
                    print(f"  ✗ {err}")
            if result.warnings:
                print(f"\nWarnings ({len(result.warnings)}):")
                for warn in result.warnings:
                    print(f"  ⚠ {warn}")
        except FileNotFoundError as e:
            print(f"Error: {e}")
            sys.exit(1)
        return

    if args.command == "detect":
        project_root = Path(args.project_root).resolve()
        project_type = detect_project_type(project_root)
        is_git = is_git_repo(project_root)
        print(f"Project type: {project_type}")
        print(f"Git repo: {is_git}")
        return

    if args.command == "init":
        from meaning.installer import (
            InstallOptions,
            install_meaning,
        )
        from meaning.meaning_inference import infer_file_metadata, infer_timestamps

        project_root = Path(args.project_root).resolve()

        # Use installer for setup
        options = InstallOptions(
            project_type=args.project_type,
            install_hooks=args.install_hooks,
            install_skills=args.with_skills,
            force_hooks=args.force_hooks,
        )

        result = install_meaning(project_root, options)

        if not result.success:
            for err in result.errors:
                print(f"❌ {err}")
            sys.exit(1)

        # Report installation results
        if result.meaning_dir_created:
            print(f"✓ Created .meaning/ with {len(result.files_copied)} files")

        if result.hooks_installed:
            print("✓ Installed Claude Code hooks")

        if result.skills_installed:
            print(f"✓ Installed {len(result.skills_installed)} skills")

        for warning in result.warnings:
            print(f"⚠️  {warning}")

        # Load the created config/schema
        index = load_index(project_root)
        schema = load_schema(project_root)
        config = load_config(project_root)

        # Skip crawl if requested
        if args.skip_crawl:
            print("✓ Skipped file scanning (use 'meaning update' to index files)")
            return

        # Scan and infer files
        all_files = scan_project_files(project_root, config)
        limit = args.limit
        if limit is not None and limit > 0:
            files_to_process = all_files[:limit]
        else:
            files_to_process = all_files

        now = infer_timestamps()
        for file_path in files_to_process:
            result_infer = infer_file_metadata(file_path, project_root, index, schema)
            entry = entry_from_inference(file_path, result_infer, DEFAULT_REVIEW_THRESHOLD, now)
            index.add_file(entry)

        save_index(project_root, index)

        validation = validate_index(index, schema, config, project_root)
        print(f"✓ Indexed {len(index.files)} files")
        if limit is not None and limit > 0 and len(all_files) > limit:
            print(
                f"⚠️  Limited to first {limit} files. Run 'meaning update' to index remaining {len(all_files) - limit} files."
            )
        print(f"⚠️  Files needing review: {len(index.files_needing_review())}")
        print(f"✓ Validation: {validation.is_valid}")
        return

    if args.command == "update":
        from meaning.meaning_inference import infer_file_metadata, infer_timestamps

        project_root = Path(args.project_root).resolve()
        if not meaning_dir_exists(project_root):
            print(f"❌ No .meaning/ directory found in {project_root}")
            print("Run 'meaning init' to create semantic index first")
            sys.exit(1)

        index = load_index(project_root)
        schema = load_schema(project_root)
        config = load_config(project_root)

        excluded = [entry.path for entry in index.files if config.is_excluded(entry.path)]
        if excluded:
            print(f"\n🧹 Removing {len(excluded)} excluded files from index:")
            for path in excluded[:10]:
                print(f"   • {path}")
            if len(excluded) > 10:
                print(f"   ... and {len(excluded) - 10} more")
            if not args.dry_run:
                prune_excluded_entries(index, config)

        new_files = find_unindexed_files(project_root, index, config)
        modified_files = find_modified_files(project_root, index)
        deleted_files = find_deleted_files(project_root, index)

        if args.new:
            modified_files = []
            deleted_files = []
        elif args.modified:
            new_files = []
            deleted_files = []
        elif args.deleted:
            new_files = []
            modified_files = []

        if not new_files and not modified_files and not deleted_files and not excluded:
            print("✓ Index is up to date")
            return

        print("📊 Changes detected:")
        print(f"   • New files: {len(new_files)}")
        print(f"   • Modified files: {len(modified_files)}")
        print(f"   • Deleted files: {len(deleted_files)}")

        if deleted_files:
            print(f"\n🗑️  Removing {len(deleted_files)} deleted files:")
            for path in deleted_files:
                print(f"   • {path}")
                if not args.dry_run:
                    index.remove_file(path)

        if new_files:
            print(f"\n✨ Adding {len(new_files)} new files:")
            now = infer_timestamps()
            for file_path in new_files:
                print(f"   • {file_path}")
                result = infer_file_metadata(file_path, project_root, index, schema)
                entry = entry_from_inference(file_path, result, args.threshold, now)
                if not args.dry_run:
                    index.add_file(entry)

        if modified_files:
            print(f"\n🔄 Processing {len(modified_files)} modified files:")
            now = infer_timestamps()
            for file_path in modified_files:
                print(f"   • {file_path}")
                entry = index.get_file(file_path)
                if entry is None:
                    continue
                if args.re_infer:
                    result = infer_file_metadata(file_path, project_root, index, schema)
                    if not args.dry_run:
                        apply_inference_to_entry(entry, result, args.threshold, config, now)
                else:
                    if not args.dry_run:
                        entry.needs_review = True
                        entry.last_verified = now

        if args.dry_run:
            print("\n⚠️  Dry run: no changes written")
            return

        save_index(project_root, index)
        validation = validate_index(index, schema, config, project_root)

        print("\n📋 Update complete")
        print(f"✓ Files in index: {len(index.files)}")
        print(f"⚠️  Files needing review: {len(index.files_needing_review())}")
        print(f"✓ Validation: {validation.is_valid}")
        if modified_files and not args.re_infer:
            print("💡 Tip: run 'meaning update --re-infer' to refresh intents and tags")
        return

    if args.command == "review":
        from meaning.meaning_inference import infer_file_metadata, infer_timestamps

        project_root = Path(args.project_root).resolve()
        if not meaning_dir_exists(project_root):
            print(f"❌ No .meaning/ directory found in {project_root}")
            print("Run 'meaning init' to create semantic index first")
            sys.exit(1)

        index = load_index(project_root)
        schema = load_schema(project_root)
        config = load_config(project_root)

        if args.file_path:
            entries = [index.get_file(args.file_path)]
            entries = [e for e in entries if e is not None]
        else:
            entries = index.files_needing_review()

        if not entries:
            print("✓ No files need review")
            return

        now = infer_timestamps()
        updated = 0
        skipped = 0

        for entry in entries:
            result = infer_file_metadata(entry.path, project_root, index, schema)
            if args.interactive:
                diff = preview_inference_diff(entry, result, args.threshold, config, now)
                print(f"\nFile: {entry.path}")
                if diff["intent"]:
                    print("  Intent:")
                    print(f"    - {diff['intent'][0]}")
                    print(f"    + {diff['intent'][1]}")
                if diff["tags_added"] or diff["tags_removed"]:
                    print("  Tags:")
                    for tag in diff["tags_added"]:
                        print(f"    + {tag}")
                    for tag in diff["tags_removed"]:
                        print(f"    - {tag}")
                if diff["rels_added"] or diff["rels_removed"]:
                    print("  Relationships:")
                    for rel in diff["rels_added"]:
                        print(f"    + {rel.type}:{rel.target or rel.source}")
                    for rel in diff["rels_removed"]:
                        print(f"    - {rel.type}:{rel.target or rel.source}")
                if diff["needs_review"]:
                    print("  Needs review:")
                    print(f"    - {diff['needs_review'][0]}")
                    print(f"    + {diff['needs_review'][1]}")
                if not any(
                    [
                        diff["intent"],
                        diff["tags_added"],
                        diff["tags_removed"],
                        diff["rels_added"],
                        diff["rels_removed"],
                        diff["needs_review"],
                    ]
                ):
                    print("  (no high-confidence changes)")

                choice = input("Apply changes? [y/N]: ").strip().lower()
                if choice != "y":
                    skipped += 1
                    continue

            if args.dry_run:
                changed = preview_inference_changes(entry, result, args.threshold, config, now)
            else:
                changed = apply_inference_to_entry(entry, result, args.threshold, config, now)

            if changed:
                updated += 1
            else:
                skipped += 1

        if args.dry_run:
            print("\n⚠️  Dry run: no changes written")
            print(f"✓ Would update {updated} file(s)")
            if skipped:
                print(f"⚠️  {skipped} file(s) have no high-confidence changes")
            return

        save_index(project_root, index)
        print(f"✓ Reviewed {updated} file(s)")
        if skipped:
            print(f"⚠️  {skipped} file(s) still need review")
            print("   Add docstrings/markdown summaries or use --interactive")
        remaining = len(index.files_needing_review())
        if remaining:
            print(f"⚠️  Files still needing review: {remaining}")
        return


if __name__ == "__main__":
    main()
