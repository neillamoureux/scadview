#!/usr/bin/env python3
"""Cross-platform helpers for docs-related local tasks."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def run_command(command: list[str], env: dict[str, str] | None = None) -> None:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    subprocess.run(command, cwd=REPO_ROOT, env=merged_env, check=True)


def resolve_docs_version(override: str | None = None) -> str:
    if override:
        return override
    env_version = os.environ.get("DOCS_VERSION")
    if env_version:
        return env_version

    result = subprocess.run(
        ["git", "tag", "--points-at", "HEAD"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    for tag in result.stdout.splitlines():
        if re.match(r"^v[0-9]", tag):
            return tag[1:]
    return "dev"


def serve_docs() -> None:
    run_command([sys.executable, "-m", "mkdocs", "serve"])


def sync_docs(serve: bool, docs_version: str | None = None) -> None:
    version = resolve_docs_version(docs_version)
    print(f"Deploying docs version {version} with alias latest (local gh-pages)...")
    run_command(
        [
            sys.executable,
            "-m",
            "mike",
            "deploy",
            "--update-aliases",
            version,
            "latest",
        ]
    )
    run_command([sys.executable, "-m", "mike", "set-default", "latest"])
    if serve:
        print("Serving versioned docs from local gh-pages branch...")
        run_command([sys.executable, "-m", "mike", "serve"])


def preview_docs(docs_version: str | None = None) -> None:
    version = docs_version or os.environ.get("DOCS_VERSION")
    if not version:
        raise SystemExit(
            "DOCS_VERSION is required. Example: "
            "mise run docs-release-preview -- --docs-version 0.2.6"
        )
    sync_docs(serve=True, docs_version=version)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run docs maintenance tasks.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("serve", help="Run mkdocs live server.")

    sync_parser = subparsers.add_parser(
        "sync",
        help="Deploy docs version locally using mike and optionally serve.",
    )
    sync_parser.add_argument(
        "--serve",
        action="store_true",
        help="Serve versioned docs after syncing.",
    )
    sync_parser.add_argument(
        "--docs-version",
        default=None,
        help="Override docs version (otherwise uses DOCS_VERSION, tag, or dev).",
    )

    preview_parser = subparsers.add_parser(
        "preview",
        help="Sync and serve a release docs version.",
    )
    preview_parser.add_argument(
        "--docs-version",
        default=None,
        help="Release docs version to preview (e.g. 0.2.6).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "serve":
        serve_docs()
        return
    if args.command == "sync":
        sync_docs(serve=args.serve, docs_version=args.docs_version)
        return
    if args.command == "preview":
        preview_docs(docs_version=args.docs_version)
        return
    raise SystemExit(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()
