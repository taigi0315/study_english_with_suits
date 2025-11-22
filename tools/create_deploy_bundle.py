#!/usr/bin/env python3
"""
Create a minimal deployment bundle for LangFlix.

This script packages the repository into a ZIP archive while excluding
development-only artifacts (e.g., venv, docs, tests) so the resulting
bundle can be copied directly to a TrueNAS host.

Usage:
    python tools/create_deploy_bundle.py
    python tools/create_deploy_bundle.py --output dist/langflix.zip
    python tools/create_deploy_bundle.py --exclude "*.log" --exclude samples/
"""

from __future__ import annotations

import argparse
import fnmatch
import os
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Set
from zipfile import ZIP_DEFLATED, ZipFile


DEFAULT_EXCLUDE_DIRS: Set[str] = {
    ".git",
    ".github",
    ".idea",
    ".vscode",
    "__pycache__",
    "venv",
    ".venv",
    "docs",
    "tests",
    "test_output",
    "output",
    "cache",
    "dist",
    "htmlcov",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "Suits_Transcripts",
}

ASSETS_MEDIA_PATTERN = "assets/media*"


DEFAULT_EXCLUDE_GLOBS: Set[str] = {
    "*.pyc",
    "*.pyo",
    "*.pyd",
    "*.log",
    "*.tmp",
    "*.temp",
    "*.sqlite3",
    "*.db",
    "*.sqlite",
    "*.egg-info",
    "*.coverage",
    "*.cache",
    ".DS_Store",
    "Thumbs.db",
    ".env.local",
    "langflix.log",
    ASSETS_MEDIA_PATTERN,
    # Note: YouTube credentials (youtube_credentials.json, youtube_token.json) are INCLUDED
    # as they are required for YouTube functionality in deployment
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a minimal deployment ZIP bundle for LangFlix."
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Path to the output ZIP file (default: dist/langflix_deploy_<timestamp>.zip)",
    )
    parser.add_argument(
        "--exclude",
        "-x",
        action="append",
        default=[],
        help="Additional glob pattern or directory name to exclude (can be used multiple times).",
    )
    parser.add_argument(
        "--include-docs",
        action="store_true",
        help="Include documentation files (docs/) in the bundle.",
    )
    parser.add_argument(
        "--include-media",
        action="store_true",
        help="Include assets/media directory in the bundle.",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress non-error output.",
    )
    return parser.parse_args()


def build_exclude_sets(args: argparse.Namespace) -> tuple[Set[str], Set[str]]:
    exclude_dirs = set(DEFAULT_EXCLUDE_DIRS)
    exclude_globs = set(DEFAULT_EXCLUDE_GLOBS)

    if args.include_docs and "docs" in exclude_dirs:
        exclude_dirs.remove("docs")

    if args.include_media and ASSETS_MEDIA_PATTERN in exclude_globs:
        exclude_globs.remove(ASSETS_MEDIA_PATTERN)

    for pattern in args.exclude:
        # Treat bare names as directory exclusions, otherwise glob
        if pattern and "/" not in pattern and not any(ch in pattern for ch in "*?[]"):
            exclude_dirs.add(pattern)
        else:
            exclude_globs.add(pattern)

    return exclude_dirs, exclude_globs


def should_exclude(
    rel_path: Path, exclude_dirs: Set[str], exclude_globs: Set[str]
) -> bool:
    # Directory-based exclusion
    for part in rel_path.parts:
        if part in exclude_dirs:
            return True

    rel_str = rel_path.as_posix()
    name = rel_path.name

    for pattern in exclude_globs:
        if fnmatch.fnmatch(rel_str, pattern) or fnmatch.fnmatch(name, pattern):
            return True

    return False


def iter_project_files(
    root: Path, exclude_dirs: Set[str], exclude_globs: Set[str]
) -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        relative_dir = Path(dirpath).relative_to(root)

        # Mutate dirnames in-place to skip excluded directories early
        dirnames[:] = [
            d
            for d in dirnames
            if not should_exclude(relative_dir / d, exclude_dirs, exclude_globs)
        ]

        for filename in filenames:
            rel_file = relative_dir / filename
            if should_exclude(rel_file, exclude_dirs, exclude_globs):
                continue
            yield rel_file


def ensure_output_path(output: Path) -> Path:
    if output.suffix.lower() != ".zip":
        raise ValueError("Output path must have a .zip extension")
    output.parent.mkdir(parents=True, exist_ok=True)
    return output


def generate_default_output(root: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return root / "dist" / f"langflix_deploy_{timestamp}.zip"


def write_manifest(zip_file: ZipFile, entries: List[str]) -> None:
    content = "\n".join(entries)
    zip_file.writestr("MANIFEST_DEPLOY.txt", content)


def main() -> None:
    args = parse_args()
    project_root = Path(__file__).resolve().parents[1]

    # Resolve output path
    output_path = (
        ensure_output_path(args.output)
        if args.output
        else ensure_output_path(generate_default_output(project_root))
    )

    exclude_dirs, exclude_globs = build_exclude_sets(args)

    files = list(iter_project_files(project_root, exclude_dirs, exclude_globs))
    if not files:
        raise RuntimeError("No files matched for inclusion. Adjust exclude patterns.")

    entries_recorded: List[str] = []

    with ZipFile(output_path, "w", compression=ZIP_DEFLATED) as bundle:
        for rel_path in files:
            abs_path = project_root / rel_path
            # Skip if file doesn't exist (e.g., optional credentials files)
            if not abs_path.exists():
                if not args.quiet:
                    print(f"⚠️  Skipping non-existent file: {rel_path}")
                continue
            bundle.write(abs_path, rel_path.as_posix())
            entries_recorded.append(rel_path.as_posix())

        entries_recorded.sort()
        write_manifest(bundle, entries_recorded)

    if not args.quiet:
        print(f"✅ Deployment bundle created: {output_path}")
        print(f"   Included files: {len(entries_recorded)}")
        exclusion_notes: List[str] = []
        if not args.include_docs:
            exclusion_notes.append("docs/ (default)")
        if not args.include_media:
            exclusion_notes.append("assets/media (default)")
        if args.exclude:
            exclusion_notes.extend(f"custom: {pattern}" for pattern in args.exclude)
        if exclusion_notes:
            print("   Exclusions applied:")
            for note in exclusion_notes:
                print(f"     - {note}")


if __name__ == "__main__":
    main()

