from __future__ import annotations

import os
import re
import shlex
from pathlib import Path

from invoke.context import Context
from invoke.exceptions import Exit
from invoke.tasks import task  # type: ignore[reportUnknownVariableType]

REPO_ROOT: Path = Path(__file__).resolve().parent
DEFAULT_TARGETS: tuple[str, ...] = ("src", "tests", "examples")
TASKRUNNER_GROUP: str = "taskrunner"
MISE_STAMP_DIR: Path = REPO_ROOT / ".cache" / "mise_stamps"
DOCS_VERSION_TAG_PATTERN: str = r"^v[0-9]"


def _existing_targets() -> list[str]:
    return [path for path in DEFAULT_TARGETS if (REPO_ROOT / path).exists()]


def _run_checked(
    context: Context,
    command: str,
    *,
    pty: bool = False,
    env: dict[str, str] | None = None,
) -> None:
    result = context.run(command, warn=True, pty=pty, env=env)
    if result and result.failed:
        raise Exit(code=result.exited)


def _join_args(raw: str) -> str:
    return f" {raw.strip()}" if raw.strip() else ""


def _run_capture(context: Context, command: str) -> str:
    result = context.run(command, warn=True, hide=True, pty=False)
    if result:
        if result.failed:
            raise Exit(code=result.exited)
        return result.stdout
    return ""


def _resolve_docs_version(context: Context, override: str = "") -> str:
    if override.strip():
        return override.strip()
    env_version = os.environ.get("DOCS_VERSION", "").strip()
    if env_version:
        return env_version

    tag_output = _run_capture(context, "git tag --points-at HEAD")
    for tag in tag_output.splitlines():
        if re.match(DOCS_VERSION_TAG_PATTERN, tag):
            return tag[1:]
    return "dev"


@task(name="write_stamp")  # type: ignore[reportUntypedFunctionDecorator]
def write_stamp(_context: Context, task_name: str) -> None:
    """Write a mise freshness stamp file for a task name."""
    MISE_STAMP_DIR.mkdir(parents=True, exist_ok=True)
    stamp_path: Path = MISE_STAMP_DIR / f"{task_name}.stamp"
    stamp_path.touch()
    print(stamp_path)


@task
def bootstrap(context: Context, ci: bool = False, frozen: bool = True) -> None:
    """Install Python dependencies using uv sync."""
    is_ci: bool = ci or bool(os.environ.get("CI"))
    cmd_parts: list[str] = ["uv", "sync"]
    if frozen:
        cmd_parts.append("--frozen")
    cmd_parts.extend(["--group", TASKRUNNER_GROUP])
    if is_ci:
        cmd_parts.extend(["--no-install-package", "wxpython"])
    else:
        cmd_parts.append("--dev")
    _run_checked(context, " ".join(cmd_parts))


@task(name="format")  # type: ignore[reportUntypedFunctionDecorator]
def format_(context: Context, args: str = "") -> None:
    """Format source, tests, and examples."""
    targets: list[str] = _existing_targets()
    if not targets:
        raise Exit(
            "No format targets found (expected one of src/tests/examples).", code=2
        )
    target_str: str = " ".join(shlex.quote(target) for target in targets)
    extra: str = _join_args(args)

    if not os.environ.get("CI"):
        _run_checked(context, f"ruff check --select I --fix{extra} {target_str}")
    _run_checked(context, f"ruff format{extra} {target_str}")


@task
def lint(context: Context, args: str = "") -> None:
    """Run lint checks."""
    targets: list[str] = _existing_targets()
    if not targets:
        raise Exit(
            "No lint targets found (expected one of src/tests/examples).", code=2
        )
    target_str: str = " ".join(shlex.quote(target) for target in targets)
    extra: str = _join_args(args)

    _run_checked(context, f"ruff check{extra} {target_str}")
    _run_checked(context, f"ruff check --select I{extra} {target_str}")


@task(name="type")  # type: ignore[reportUntypedFunctionDecorator]
def type_(context: Context, args: str = "", ci: bool = False) -> None:
    """Run pyright type checks."""
    extra: str = _join_args(args)
    project_flag: str = " --project pyright.ci.json" if ci else ""
    _run_checked(context, f"pyright{project_flag}{extra}")


@task
def test(context: Context, args: str = "", ci: bool = False) -> None:
    """Run tests."""
    extra: str = _join_args(args)
    env: dict[str, str] | None = None
    plugin_flags: str = ""
    pty: bool = True

    if ci or os.environ.get("CI"):
        env = {"PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"}
        plugin_flags = " -p pytest_cov"
        pty = False

    _run_checked(
        context,
        f"pytest{plugin_flags}{extra}",
        env=env,
        pty=pty,
    )


@task
def run(context: Context, args: str = "") -> None:
    """Run the application."""
    extra: str = _join_args(args)
    _run_checked(context, f"python -m scadview{extra}")


@task(name="docs_live_serve")  # type: ignore[reportUntypedFunctionDecorator]
def docs_live_serve(context: Context) -> None:
    """Serve docs with live reload (mkdocs)."""
    _run_checked(context, "python -m mkdocs serve")


@task(name="docs_sync")  # type: ignore[reportUntypedFunctionDecorator]
def docs_sync(
    context: Context,
    serve: bool = False,
    docs_version: str = "",
) -> None:
    """Sync local versioned docs state."""
    version = _resolve_docs_version(context, docs_version)
    print(f"Deploying docs version {version} with alias latest (local gh-pages)...")
    _run_checked(
        context,
        f"mike deploy --update-aliases {shlex.quote(version)} latest",
    )
    _run_checked(context, "mike set-default latest")
    if serve:
        print(
            "Serving versioned docs on http://localhost:8000 from local gh-pages branch..."
        )
        _run_checked(context, "mike serve")


@task(name="docs_preview_serve")  # type: ignore[reportUntypedFunctionDecorator]
def docs_preview_serve(context: Context, docs_version: str = "") -> None:
    """Preview release docs locally."""
    version = docs_version.strip() or os.environ.get("DOCS_VERSION", "").strip()
    if not version:
        raise Exit(
            "DOCS_VERSION is required. Example: "
            + "mise run docs-release-preview -- --docs-version 0.2.6",
            code=2,
        )
    docs_sync(context, serve=True, docs_version=version)


@task
def preflight(context: Context) -> None:
    """Run lint, types, and tests."""
    lint(context)
    type_(context)
    test(context)
