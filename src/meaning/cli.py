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
    update_parser.add_argument(
        "--check-stale", action="store_true", help="Flag stale files for review"
    )
    update_parser.add_argument("--dry-run", action="store_true")
    update_parser.add_argument("--verbose", action="store_true")
    update_parser.add_argument("--threshold", type=float, default=DEFAULT_REVIEW_THRESHOLD)

    review_parser = subparsers.add_parser("review", help="Review and accept inferred metadata")
    review_parser.add_argument("project_root", nargs="?", default=".")
    review_parser.add_argument("--interactive", action="store_true")
    review_parser.add_argument("--file", dest="file_path", default=None)
    review_parser.add_argument("--stale", action="store_true", help="Include stale files in review")
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
            query_result = query_index(index, schema, query_str)
            display_query_results(query_result)
        except FileNotFoundError:
            print(f"ERROR: No .meaning/ directory found in {project_root}")
            print("\nTIP: Initialize with: python -m meaning init")
            sys.exit(1)
        return

    if args.command == "validate":
        project_root = Path(args.project_root).resolve()
        try:
            index = load_index(project_root)
            schema = load_schema(project_root)
            config = load_config(project_root)
            validation_result = validate_index(index, schema, config, project_root)

            print(f"Valid: {validation_result.is_valid}")
            if validation_result.errors:
                print(f"\nErrors ({len(validation_result.errors)}):")
                for err in validation_result.errors:
                    print(f"  - {err}")
            if validation_result.warnings:
                print(f"\nWarnings ({len(validation_result.warnings)}):")
                for warn in validation_result.warnings:
                    print(f"  WARN: {warn}")
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

        install_result = install_meaning(project_root, options)

        if not install_result.success:
            for err in install_result.errors:
                print(f"ERROR: {err}")
            sys.exit(1)

        # Report installation results
        if install_result.meaning_dir_created:
            print(f"OK: Created .meaning/ with {len(install_result.files_copied)} files")

        if install_result.hooks_installed:
            print("OK: Installed Claude Code hooks")

        if install_result.skills_installed:
            print(f"OK: Installed {len(install_result.skills_installed)} skills")

        for warning in install_result.warnings:
            print(f"WARN: {warning}")

        # Load the created config/schema
        index = load_index(project_root)
        schema = load_schema(project_root)
        config = load_config(project_root)

        # Skip crawl if requested
        if args.skip_crawl:
            print("OK: Skipped file scanning (use 'meaning update' to index files)")
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
            result_infer = infer_file_metadata(file_path, project_root, index, schema, config)
            entry = entry_from_inference(file_path, result_infer, DEFAULT_REVIEW_THRESHOLD, now)
            index.add_file(entry)

        save_index(project_root, index)

        validation = validate_index(index, schema, config, project_root)
        print(f"OK: Indexed {len(index.files)} files")
        if limit is not None and limit > 0 and len(all_files) > limit:
            print(
                f"WARN: Limited to first {limit} files. Run 'meaning update' to index remaining {len(all_files) - limit} files."
            )
        print(f"WARN: Files needing review: {len(index.files_needing_review())}")
        print(f"OK: Validation: {validation.is_valid}")
        return

    if args.command == "update":
        from meaning.meaning_inference import infer_file_metadata, infer_timestamps

        project_root = Path(args.project_root).resolve()
        if not meaning_dir_exists(project_root):
            print(f"ERROR: No .meaning/ directory found in {project_root}")
            print("Run 'meaning init' to create semantic index first")
            sys.exit(1)

        index = load_index(project_root)
        schema = load_schema(project_root)
        config = load_config(project_root)

        excluded = [entry.path for entry in index.files if config.is_excluded(entry.path)]

        def print_file_list(label: str, files: list[str]) -> None:
            if not files:
                return
            print(f"{label}: {len(files)}")
            shown = files if args.verbose else files[:10]
            for path in shown:
                print(f"  - {path}")
            if len(files) > len(shown):
                print(f"  ... and {len(files) - len(shown)} more")

        all_files = scan_project_files(project_root, config)
        indexed_paths = {entry.path for entry in index.files}
        collection_skipped = [
            f for f in all_files if f not in indexed_paths and index.is_collected(f)
        ]
        new_files = [f for f in all_files if f not in indexed_paths and not index.is_collected(f)]
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
            print("OK: Index is up to date")
            if collection_skipped:
                print(f"INFO: Collection-covered files (not indexed): {len(collection_skipped)}")
            return

        print("UPDATE SUMMARY")
        print(f"  Project files: {len(all_files)}")
        print(f"  Indexed files: {len(index.files)}")
        print(f"  Collections: {len(index.collections)}")
        print(f"  Collection-covered (not indexed): {len(collection_skipped)}")
        print(
            "  Pending changes: "
            f"new {len(new_files)}, modified {len(modified_files)}, "
            f"deleted {len(deleted_files)}, excluded {len(excluded)}"
        )
        if args.dry_run:
            print("  Mode: dry-run")
        print()

        if excluded:
            print_file_list("CLEAN excluded entries", excluded)
            if not args.dry_run:
                prune_excluded_entries(index, config)

        if deleted_files:
            print_file_list("REMOVE deleted files", deleted_files)
            if not args.dry_run:
                for path in deleted_files:
                    index.remove_file(path)

        if new_files:
            print_file_list("ADD new files", new_files)
            if not args.dry_run:
                now = infer_timestamps()
                for file_path in new_files:
                    inference_result = infer_file_metadata(
                        file_path, project_root, index, schema, config
                    )
                    entry = entry_from_inference(file_path, inference_result, args.threshold, now)
                    index.add_file(entry)

        if modified_files:
            mode_label = "re-infer" if args.re_infer else "flag review"
            print_file_list(f"UPDATE modified files ({mode_label})", modified_files)
            if not args.dry_run:
                now = infer_timestamps()
                for file_path in modified_files:
                    modified_entry = index.get_file(file_path)
                    if modified_entry is None:
                        continue
                    if args.re_infer:
                        inference_result = infer_file_metadata(
                            file_path, project_root, index, schema, config
                        )
                        apply_inference_to_entry(
                            modified_entry, inference_result, args.threshold, config, now
                        )
                    else:
                        modified_entry.needs_review = True
                        modified_entry.last_verified = now

        if args.check_stale:
            stale_entries = index.stale_files(config.stale_threshold_days)
            if stale_entries:
                print_file_list("FLAG stale files for review", [f.path for f in stale_entries])
                if not args.dry_run:
                    for f in stale_entries:
                        f.needs_review = True

        if collection_skipped and args.verbose:
            print_file_list("INFO collection-covered files (not indexed)", collection_skipped)

        if args.dry_run:
            print("\nWARN: Dry run: no changes written")
            return

        save_index(project_root, index)
        validation = validate_index(index, schema, config, project_root)

        print("\nUPDATE RESULTS")
        print(f"  Files in index: {len(index.files)}")
        print(f"  Files needing review: {len(index.files_needing_review())}")
        print(f"  Validation: {validation.is_valid}")
        if modified_files and not args.re_infer:
            print("TIP: run 'meaning update --re-infer' to refresh intents and tags")
        return

    if args.command == "review":
        from meaning.meaning_inference import infer_file_metadata, infer_timestamps

        project_root = Path(args.project_root).resolve()
        if not meaning_dir_exists(project_root):
            print(f"ERROR: No .meaning/ directory found in {project_root}")
            print("Run 'meaning init' to create semantic index first")
            sys.exit(1)

        index = load_index(project_root)
        schema = load_schema(project_root)
        config = load_config(project_root)

        if args.file_path:
            selected_entry = index.get_file(args.file_path)
            entries = [selected_entry] if selected_entry is not None else []
        else:
            entries = index.files_needing_review()
            if args.stale:
                stale = index.stale_files(config.stale_threshold_days)
                existing_paths = {e.path for e in entries}
                for s in stale:
                    if s.path not in existing_paths:
                        entries.append(s)

        if not entries:
            print("OK: No files need review")
            return

        now = infer_timestamps()
        updated_count = 0
        verified_count = 0
        skipped_count = 0
        changes_log = []

        for entry in entries:
            inference_result = infer_file_metadata(entry.path, project_root, index, schema, config)

            # Calculate diff before applying
            diff = preview_inference_diff(entry, inference_result, args.threshold, config, now)

            if args.interactive:
                print(f"\nFile: {entry.path}")
                has_changes = False
                if diff["intent"]:
                    print("  Intent:")
                    print(f"    - {diff['intent'][0]}")
                    print(f"    + {diff['intent'][1]}")
                    has_changes = True
                if diff["tags_added"] or diff["tags_removed"]:
                    print("  Tags:")
                    for tag in diff["tags_added"]:
                        print(f"    + {tag}")
                    for tag in diff["tags_removed"]:
                        print(f"    - {tag}")
                    has_changes = True
                if diff["rels_added"] or diff["rels_removed"]:
                    print("  Relationships:")
                    for rel in diff["rels_added"]:
                        print(f"    + {rel.type}:{rel.target or rel.source}")
                    for rel in diff["rels_removed"]:
                        print(f"    - {rel.type}:{rel.target or rel.source}")
                    has_changes = True
                if diff["needs_review"]:
                    print("  Needs review:")
                    print(f"    - {diff['needs_review'][0]}")
                    print(f"    + {diff['needs_review'][1]}")
                    has_changes = True

                if not has_changes:
                    print("  (no high-confidence changes)")

                choice = input("Apply changes? [y/N]: ").strip().lower()
                if choice != "y":
                    skipped_count += 1
                    continue

            if args.dry_run:
                # In dry run, we just simulate
                has_semantic_changes = any(
                    [
                        diff["intent"],
                        diff["tags_added"],
                        diff["tags_removed"],
                        diff["rels_added"],
                        diff["rels_removed"],
                    ]
                )
                if has_semantic_changes:
                    updated_count += 1
                    changes_log.append((entry.path, diff))
                else:
                    verified_count += 1
            else:
                changed = apply_inference_to_entry(
                    entry, inference_result, args.threshold, config, now
                )

                if changed:
                    updated_count += 1
                    changes_log.append((entry.path, diff))
                else:
                    verified_count += 1

        if args.dry_run:
            print("\nWARN: Dry run: no changes written")

        if not args.dry_run:
            save_index(project_root, index)

        # Summary Report
        print("\nREVIEW SUMMARY")
        print(f"  Processed: {len(entries)}")
        print(f"  Updated:   {updated_count}")
        print(f"  Verified:  {verified_count} (timestamp updated, no semantic changes)")
        if skipped_count:
            print(f"  Skipped:   {skipped_count}")

        if changes_log:
            print("\nDETAILS")
            for path, diff in changes_log:
                print(f"  {path}")
                if diff["intent"]:
                    print(f'    + Intent: "{diff["intent"][1]}"')
                if diff["tags_added"]:
                    print(f"    + Tags: {', '.join(diff['tags_added'])}")
                if diff["rels_added"]:
                    rels = [f"{r.type}:{r.target or r.source}" for r in diff["rels_added"]]
                    print(f"    + Rels: {', '.join(rels)}")
                if diff["needs_review"] and not diff["needs_review"][1]:
                    print("    + Status: Review cleared")

        remaining = len(index.files_needing_review())
        if remaining:
            print(f"\nNOTE: {remaining} files still need review")
        return


if __name__ == "__main__":
    main()
