from __future__ import annotations

import argparse
import re
import sys
import time
import tomllib
from collections.abc import Callable, Iterable, Sequence
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from scadview.load_status import LoadStatus
from scadview.ui.view_state import CameraName, ViewName, ViewState

MARKDOWN_IMAGE_PATTERN: re.Pattern[str] = re.compile(r"!\[[^\]]*\]\(([^)\s]+)")
LOAD_TIMEOUT_SECONDS = 120.0
SETTLE_EVENT_CYCLES = 3


class ScreenshotManifestError(ValueError):
    """Raised when the docs screenshot manifest is invalid."""


@dataclass(frozen=True)
class ScreenshotEntry:
    name: str
    output: Path
    module: Path
    window_size: tuple[int, int]
    view: ViewName
    camera: CameraName
    grid: bool
    axes: bool
    edges: bool
    gnomon: bool


@dataclass(frozen=True)
class ScreenshotManifest:
    path: Path
    entries: tuple[ScreenshotEntry, ...]


@dataclass(frozen=True)
class ScreenshotCaptureRequest:
    entry: ScreenshotEntry
    module_path: Path
    output_path: Path


class ScreenshotCaptureBackend(Protocol):
    def capture(self, request: ScreenshotCaptureRequest) -> None:
        pass


class WxAppProtocol(Protocol):
    def Yield(self) -> None:
        pass


class ControllerProtocol(Protocol):
    def close(self) -> None:
        pass


class BitmapProtocol(Protocol):
    def SaveFile(self, filename: str, file_type: int) -> bool:
        pass


class ScreenshotFrameProtocol(Protocol):
    def SetClientSize(self, size: object) -> None:
        pass

    def Show(self) -> None:
        pass

    def load_module(self, module_path: Path, *, start_timer: bool = True) -> None:
        pass

    def poll_load_status(self) -> LoadStatus:
        pass

    def apply_view_state(self, view_state: ViewState) -> None:
        pass

    def capture_client_bitmap(self) -> BitmapProtocol:
        pass

    def Layout(self) -> None:
        pass

    def Refresh(self, erase_background: bool = True) -> None:
        pass

    def Update(self) -> None:
        pass

    def Destroy(self) -> None:
        pass


CaptureBackendFactory = Callable[[], ScreenshotCaptureBackend]


def main(
    argv: Sequence[str] | None = None,
    *,
    capture_backend_factory: CaptureBackendFactory | None = None,
) -> int:
    args = _parse_args(argv)
    repo_root = args.manifest.parent.parent
    manifest = validate_manifest(
        args.manifest,
        repo_root=repo_root,
        selected_names=set(args.names),
    )
    if not args.generate:
        return 0
    backend_factory = capture_backend_factory or _create_default_capture_backend
    generate_screenshots(
        manifest,
        repo_root=repo_root,
        capture_backend=backend_factory(),
    )
    return 0


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
    referenced_paths = _collect_markdown_image_paths(repo_root)
    for entry in selected_entries:
        _validate_output(entry, docs_root, referenced_paths)
        _validate_module(entry, repo_root)
    return ScreenshotManifest(path=manifest.path, entries=tuple(selected_entries))


def load_manifest(manifest_path: Path) -> ScreenshotManifest:
    raw_entries = _read_manifest_entries(manifest_path)
    entries = tuple(_parse_entry(raw_entry) for raw_entry in raw_entries)
    return ScreenshotManifest(path=manifest_path, entries=entries)


def generate_screenshots(
    manifest: ScreenshotManifest,
    *,
    repo_root: Path,
    capture_backend: ScreenshotCaptureBackend,
) -> None:
    docs_root = manifest.path.parent
    for entry in manifest.entries:
        capture_backend.capture(_capture_request(entry, repo_root, docs_root))


class WxScreenshotCaptureBackend(ScreenshotCaptureBackend):
    def capture(self, request: ScreenshotCaptureRequest) -> None:
        app = _wx_app()
        controller = _create_controller()
        frame = _create_frame(controller)
        try:
            _capture_with_frame(app, frame, request)
        finally:
            _close_frame(frame)
            controller.close()


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
    return ScreenshotEntry(
        name=_required_str(entry, "name"),
        output=Path(_required_str(entry, "output")),
        module=Path(_required_str(entry, "module")),
        window_size=_parse_window_size(entry.get("window_size")),
        view=_parse_view(_required_str(entry, "view")),
        camera=_parse_camera(_required_str(entry, "camera")),
        grid=_required_bool(entry, "grid"),
        axes=_required_bool(entry, "axes"),
        edges=_required_bool(entry, "edges"),
        gnomon=_required_bool(entry, "gnomon"),
    )


def _entry_table(raw_entry: object) -> dict[str, object]:
    if not isinstance(raw_entry, dict):
        raise ScreenshotManifestError("screenshot entry must be a table")
    entry: dict[str, object] = {}
    for key, value in raw_entry.items():
        if not isinstance(key, str):
            raise ScreenshotManifestError("screenshot entry keys must be strings")
        entry[key] = value
    return entry


def _required_str(raw_entry: dict[str, object], field: str) -> str:
    value = raw_entry.get(field)
    if not isinstance(value, str) or not value:
        raise ScreenshotManifestError(f"{field} must be a non-empty string")
    return value


def _required_bool(raw_entry: dict[str, object], field: str) -> bool:
    value = raw_entry.get(field)
    if not isinstance(value, bool):
        raise ScreenshotManifestError(f"{field} must be true or false")
    return value


def _parse_window_size(value: object) -> tuple[int, int]:
    if not isinstance(value, list) or len(value) != 2:
        raise ScreenshotManifestError(
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
        raise ScreenshotManifestError(
            "window_size must contain two positive integer values"
        )
    return (width, height)


def _parse_view(value: str) -> ViewName:
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
    raise ScreenshotManifestError(f"view value is not supported: {value}")


def _parse_camera(value: str) -> CameraName:
    if value == "perspective":
        return "perspective"
    if value == "orthogonal":
        return "orthogonal"
    raise ScreenshotManifestError(f"camera value is not supported: {value}")


def _capture_request(
    entry: ScreenshotEntry,
    repo_root: Path,
    docs_root: Path,
) -> ScreenshotCaptureRequest:
    return ScreenshotCaptureRequest(
        entry=entry,
        module_path=_resolve_relative_path(repo_root, entry.module),
        output_path=_resolve_relative_path(docs_root, entry.output),
    )


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
    referenced_paths: set[Path],
) -> None:
    output_path = _resolve_relative_path(docs_root, entry.output)
    if not _is_relative_to(output_path, docs_root.resolve()):
        raise ScreenshotManifestError(
            f"output path may not escape docs: {entry.output}"
        )
    if output_path.suffix != ".png":
        raise ScreenshotManifestError(f"PNG output is required: {entry.output}")
    if output_path not in referenced_paths:
        raise ScreenshotManifestError(
            f"output is not referenced by markdown: {entry.output}"
        )


def _validate_module(entry: ScreenshotEntry, repo_root: Path) -> None:
    module_path = _resolve_relative_path(repo_root, entry.module)
    if not _is_relative_to(module_path, repo_root.resolve()):
        raise ScreenshotManifestError(
            f"module path may not escape repo: {entry.module}"
        )
    if not module_path.is_file():
        raise ScreenshotManifestError(f"module is missing: {entry.module}")


def _resolve_relative_path(root: Path, relative_path: Path) -> Path:
    if relative_path.is_absolute():
        raise ScreenshotManifestError(f"path must be relative: {relative_path}")
    return (root / relative_path).resolve()


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _collect_markdown_image_paths(repo_root: Path) -> set[Path]:
    references: set[Path] = set()
    for markdown_path in _docs_markdown_paths(repo_root):
        references.update(_markdown_image_paths(markdown_path))
    return references


def _docs_markdown_paths(repo_root: Path) -> list[Path]:
    markdown_paths: list[Path] = []
    readme_path = repo_root / "README.md"
    if readme_path.is_file():
        markdown_paths.append(readme_path)

    docs_root = repo_root / "docs"
    if docs_root.is_dir():
        markdown_paths.extend(sorted(docs_root.rglob("*.md")))
    return markdown_paths


def _markdown_image_paths(markdown_path: Path) -> set[Path]:
    text = markdown_path.read_text(encoding="utf-8")
    return {
        (markdown_path.parent / reference).resolve()
        for reference in MARKDOWN_IMAGE_PATTERN.findall(text)
        if _is_local_reference(reference)
    }


def _is_local_reference(reference: str) -> bool:
    return not re.match(r"^[a-z][a-z0-9+.-]*:", reference)


def _create_default_capture_backend() -> ScreenshotCaptureBackend:
    return WxScreenshotCaptureBackend()


def _wx_app() -> WxAppProtocol:
    import wx

    app = wx.App.Get()
    if app is None:
        return wx.App(False)
    return app


def _create_controller() -> ControllerProtocol:
    from scadview.controller import Controller

    return Controller()


def _create_frame(controller: object) -> ScreenshotFrameProtocol:
    from scadview.render.camera import CameraPerspective
    from scadview.render.gl_widget_adapter import GlWidgetAdapter
    from scadview.render.renderer import RendererFactory
    from scadview.ui.wx.main_frame import MainFrame

    renderer_factory = RendererFactory(CameraPerspective())
    gl_widget_adapter = GlWidgetAdapter(renderer_factory)
    return MainFrame(controller, gl_widget_adapter)


def _capture_with_frame(
    app: WxAppProtocol,
    frame: ScreenshotFrameProtocol,
    request: ScreenshotCaptureRequest,
) -> None:
    import wx

    frame.SetClientSize(wx.Size(*request.entry.window_size))
    frame.Show()
    _flush_events(app)
    frame.load_module(request.module_path, start_timer=False)
    _wait_for_load(app, frame, request.entry.name)
    frame.apply_view_state(_view_state(request.entry))
    _settle_frame(app, frame)
    _save_bitmap(frame.capture_client_bitmap(), request.output_path)


def _flush_events(app: WxAppProtocol) -> None:
    app.Yield()


def _wait_for_load(
    app: WxAppProtocol,
    frame: ScreenshotFrameProtocol,
    screenshot_name: str,
) -> None:
    from scadview.ui.wx.main_frame import LOAD_CHECK_INTERVAL_MS

    deadline = time.monotonic() + LOAD_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        status = frame.poll_load_status()
        _flush_events(app)
        if status == LoadStatus.COMPLETE:
            return
        if status == LoadStatus.ERROR:
            raise RuntimeError("Docs screenshot module failed to load")
        time.sleep(LOAD_CHECK_INTERVAL_MS / 1000.0)
    raise TimeoutError(
        f"Timed out waiting for docs screenshot module to load: {screenshot_name}"
    )


def _view_state(entry: ScreenshotEntry) -> ViewState:
    return ViewState(
        view=entry.view,
        camera=entry.camera,
        grid=entry.grid,
        axes=entry.axes,
        edges=entry.edges,
        gnomon=entry.gnomon,
    )


def _settle_frame(app: WxAppProtocol, frame: ScreenshotFrameProtocol) -> None:
    frame.Layout()
    frame.Refresh(False)
    for _ in range(SETTLE_EVENT_CYCLES):
        frame.Update()
        _flush_events(app)


def _save_bitmap(bitmap: BitmapProtocol, output_path: Path) -> None:
    import wx

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not bitmap.SaveFile(str(output_path), wx.BITMAP_TYPE_PNG):
        raise OSError(f"Failed to save screenshot: {output_path}")


def _close_frame(frame: ScreenshotFrameProtocol) -> None:
    with suppress(RuntimeError):
        frame.Destroy()


if __name__ == "__main__":
    sys.exit(main())
