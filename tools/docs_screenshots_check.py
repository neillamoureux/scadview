from __future__ import annotations

import tomllib
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

from pydantic import StringConstraints, TypeAdapter, ValidationError, field_validator
from pydantic.dataclasses import dataclass as validated_dataclass
from scadview.ui.view_state import CameraName, ViewName


class ScreenshotManifestError(ValueError):
    """Raised when the docs screenshot manifest is invalid."""


NonEmptyString = Annotated[str, StringConstraints(min_length=1, strict=True)]


@validated_dataclass(frozen=True)
class ScreenshotEntry:
    name: NonEmptyString
    output: Path
    module: Path
    window_size: tuple[int, int]
    view: ViewName
    camera: CameraName
    grid: bool
    axes: bool
    edges: bool
    gnomon: bool

    @field_validator("window_size", mode="before")
    @classmethod
    def _validate_window_size(cls, value: object) -> tuple[int, int]:
        if not isinstance(value, (list, tuple)) or len(value) != 2:
            raise ValueError(
                "window_size must contain two positive integer values"
            )
        width = value[0]
        height = value[1]
        if (
            not isinstance(width, int)
            or not isinstance(height, int)
            or isinstance(width, bool)
            or isinstance(height, bool)
            or width <= 0
            or height <= 0
        ):
            raise ValueError(
                "window_size must contain two positive integer values"
            )
        return (width, height)

    @field_validator("view", mode="before")
    @classmethod
    def _validate_view(cls, value: object) -> ViewName:
        if value == "frame":
            return "frame"
        if value == "xyz":
            return "xyz"
        if value == "x":
            return "x"
        if value == "y":
            return "y"
        if value == "z":
            return "z"
        raise ValueError(f"view value is not supported: {value}")

    @field_validator("camera", mode="before")
    @classmethod
    def _validate_camera(cls, value: object) -> CameraName:
        if value == "perspective":
            return "perspective"
        if value == "orthogonal":
            return "orthogonal"
        raise ValueError(f"camera value is not supported: {value}")

    @field_validator("grid", "axes", "edges", "gnomon", mode="before")
    @classmethod
    def _validate_toggle(cls, value: object, info: object) -> bool:
        field_name = getattr(info, "field_name", "value")
        if not isinstance(value, bool):
            raise ValueError(f"{field_name} must be true or false")
        return value


@dataclass(frozen=True)
class ScreenshotManifest:
    path: Path
    entries: tuple[ScreenshotEntry, ...]


def validate_manifest(
    manifest_path: Path,
    *,
    repo_root: Path,
    selected_names: Iterable[str] | None = None,
) -> ScreenshotManifest:
    manifest = load_manifest(manifest_path)
    _validate_unique_names(manifest.entries)
    requested_names = set(selected_names or ())
    selected_entries = _select_entries(manifest.entries, requested_names)
    docs_root = manifest.path.parent
    for entry in selected_entries:
        _validate_output(entry, docs_root)
        _validate_module(entry, repo_root)
    return ScreenshotManifest(path=manifest.path, entries=tuple(selected_entries))


def load_manifest(manifest_path: Path) -> ScreenshotManifest:
    raw_entries = _read_manifest_entries(manifest_path)
    entries = tuple(_parse_entry(raw_entry) for raw_entry in raw_entries)
    return ScreenshotManifest(path=manifest_path, entries=entries)


def _read_manifest_entries(manifest_path: Path) -> list[object]:
    try:
        payload = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        raise ScreenshotManifestError(f"invalid TOML: {error}") from error
    screenshots = payload.get("screenshots")
    if not isinstance(screenshots, list):
        raise ScreenshotManifestError("manifest must define a screenshots list")
    return screenshots


def _parse_entry(raw_entry: object) -> ScreenshotEntry:
    entry = _entry_table(raw_entry)
    try:
        return _screenshot_entry_adapter().validate_python(entry)
    except ValidationError as error:
        raise ScreenshotManifestError(_validation_error_message(error)) from error


def _entry_table(raw_entry: object) -> dict[str, object]:
    if not isinstance(raw_entry, dict):
        raise ScreenshotManifestError("screenshot entry must be a table")
    entry: dict[str, object] = {}
    for key, value in raw_entry.items():
        if not isinstance(key, str):
            raise ScreenshotManifestError("screenshot entry keys must be strings")
        entry[key] = value
    return entry


def _screenshot_entry_adapter() -> TypeAdapter[ScreenshotEntry]:
    return TypeAdapter(ScreenshotEntry)


def _validation_error_message(error: ValidationError) -> str:
    first_error = error.errors(include_url=False)[0]
    message = first_error["msg"]
    if isinstance(message, str) and message.startswith("Value error, "):
        return message.removeprefix("Value error, ")
    return str(message)


def _validate_unique_names(entries: Sequence[ScreenshotEntry]) -> None:
    seen: set[str] = set()
    for entry in entries:
        if entry.name in seen:
            raise ScreenshotManifestError(f"duplicate screenshot name: {entry.name}")
        seen.add(entry.name)


def _select_entries(
    entries: Sequence[ScreenshotEntry],
    selected_names: set[str],
) -> list[ScreenshotEntry]:
    if not selected_names:
        return list(entries)
    names = {entry.name for entry in entries}
    unknown_names = selected_names - names
    if unknown_names:
        names_text = ", ".join(sorted(unknown_names))
        raise ScreenshotManifestError(f"unknown screenshot name: {names_text}")
    return [entry for entry in entries if entry.name in selected_names]


def _validate_output(
    entry: ScreenshotEntry,
    docs_root: Path,
) -> None:
    output_path = resolve_relative_path(docs_root, entry.output)
    if not _is_relative_to(output_path, docs_root.resolve()):
        raise ScreenshotManifestError(
            f"output path may not escape docs: {entry.output}"
        )
    if output_path.suffix != ".png":
        raise ScreenshotManifestError(f"PNG output is required: {entry.output}")


def _validate_module(entry: ScreenshotEntry, repo_root: Path) -> None:
    module_path = resolve_relative_path(repo_root, entry.module)
    if not _is_relative_to(module_path, repo_root.resolve()):
        raise ScreenshotManifestError(
            f"module path may not escape repo: {entry.module}"
        )
    if not module_path.is_file():
        raise ScreenshotManifestError(f"module is missing: {entry.module}")


def resolve_relative_path(root: Path, relative_path: Path) -> Path:
    if relative_path.is_absolute():
        raise ScreenshotManifestError(f"path must be relative: {relative_path}")
    return (root / relative_path).resolve()


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True
