from __future__ import annotations

import time
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from scadview.load_status import LoadStatus
from scadview.ui.view_state import ViewState
from tools.docs_screenshots_check import (
    ScreenshotEntry,
    ScreenshotManifest,
    resolve_relative_path,
)

LOAD_TIMEOUT_SECONDS = 120.0
SETTLE_EVENT_CYCLES = 3


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


def generate_screenshots(
    manifest: ScreenshotManifest,
    *,
    repo_root: Path,
    capture_backend: ScreenshotCaptureBackend,
) -> None:
    docs_root = manifest.path.parent
    for entry in manifest.entries:
        capture_backend.capture(_capture_request(entry, repo_root, docs_root))


def _capture_request(
    entry: ScreenshotEntry,
    repo_root: Path,
    docs_root: Path,
) -> ScreenshotCaptureRequest:
    return ScreenshotCaptureRequest(
        entry=entry,
        module_path=resolve_relative_path(repo_root, entry.module),
        output_path=resolve_relative_path(docs_root, entry.output),
    )


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


def create_default_capture_backend() -> ScreenshotCaptureBackend:
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
