from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from tools.docs_screenshots_check import (
    ScreenshotManifest,
    # ScreenshotManifestError,
    # load_manifest,
    validate_manifest,
)

if TYPE_CHECKING:
    from tools.docs_screenshots_generate import ScreenshotCaptureBackend
else:
    ScreenshotCaptureBackend = object


@dataclass(frozen=True)
class RunContext:
    generate: bool
    manifest_path: Path
    repo_root: Path
    selected_names: frozenset[str]


CaptureBackendFactory = Callable[[], ScreenshotCaptureBackend]


def main(
    argv: Sequence[str] | None = None,
    *,
    capture_backend_factory: CaptureBackendFactory | None = None,
) -> int:
    args = _parse_args(argv)
    context = _run_context(args)
    _run_command(context, capture_backend_factory=capture_backend_factory)
    return 0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate or validate docs screenshots"
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--generate", action="store_true")
    parser.add_argument("names", nargs="*")
    args = parser.parse_args(argv)
    if args.check and args.generate:
        parser.error("--check and --generate may not be used together")
    return args


def _run_context(args: argparse.Namespace) -> RunContext:
    return RunContext(
        generate=args.generate,
        manifest_path=args.manifest,
        repo_root=_repo_root(args.manifest),
        selected_names=frozenset(args.names),
    )


def _repo_root(manifest_path: Path) -> Path:
    return manifest_path.parent.parent


def _run_command(
    context: RunContext,
    *,
    capture_backend_factory: CaptureBackendFactory | None,
) -> None:
    if context.generate:
        _run_generate(
            context,
            capture_backend_factory=capture_backend_factory,
        )
        return
    _run_check(context)


def _run_generate(
    context: RunContext,
    *,
    capture_backend_factory: CaptureBackendFactory | None,
) -> None:
    from tools.docs_screenshots_generate import create_default_capture_backend

    manifest = validate_manifest(
        context.manifest_path,
        repo_root=context.repo_root,
        selected_names=context.selected_names,
    )
    backend_factory = capture_backend_factory or create_default_capture_backend
    generate_screenshots(
        manifest,
        repo_root=context.repo_root,
        capture_backend=backend_factory(),
    )


def generate_screenshots(
    manifest: ScreenshotManifest,
    *,
    repo_root: Path,
    capture_backend: ScreenshotCaptureBackend,
) -> None:
    from tools.docs_screenshots_generate import generate_screenshots as _generate

    _generate(
        manifest,
        repo_root=repo_root,
        capture_backend=capture_backend,
    )


def _run_check(context: RunContext) -> None:
    validate_manifest(
        context.manifest_path,
        repo_root=context.repo_root,
        selected_names=context.selected_names,
    )


if __name__ == "__main__":
    sys.exit(main())
