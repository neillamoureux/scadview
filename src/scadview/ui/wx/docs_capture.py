from __future__ import annotations

import time
from contextlib import suppress
from pathlib import Path

import wx

from scadview.controller import Controller
from scadview.docs_screenshots import (
    ScreenshotCaptureBackend,
    ScreenshotCaptureRequest,
)
from scadview.load_status import LoadStatus
from scadview.render.camera import CameraPerspective
from scadview.render.gl_widget_adapter import GlWidgetAdapter
from scadview.render.renderer import RendererFactory
from scadview.ui.wx.main_frame import LOAD_CHECK_INTERVAL_MS, MainFrame

LOAD_TIMEOUT_SECONDS = 30.0
SETTLE_EVENT_CYCLES = 3


class WxScreenshotCaptureBackend(ScreenshotCaptureBackend):
    def capture(self, request: ScreenshotCaptureRequest) -> None:
        app = _wx_app()
        controller = Controller()
        frame = _create_frame(controller)
        try:
            _capture_request(app, frame, request)
        finally:
            _close_frame(frame)
            controller.close()


def _wx_app() -> wx.App:
    app = wx.App.Get()
    if app is None:
        return wx.App(False)
    return app


def _create_frame(controller: Controller) -> MainFrame:
    renderer_factory = RendererFactory(CameraPerspective())
    gl_widget_adapter = GlWidgetAdapter(renderer_factory)
    return MainFrame(controller, gl_widget_adapter)


def _capture_request(
    app: wx.App,
    frame: MainFrame,
    request: ScreenshotCaptureRequest,
) -> None:
    frame.SetClientSize(wx.Size(*request.entry.window_size))
    frame.Show()
    _flush_events(app)
    frame.load_docs_screenshot_module(request.module_path)
    _wait_for_load(app, frame)
    frame.apply_docs_screenshot_state(request.entry)
    _settle_frame(app, frame)
    _save_bitmap(frame.capture_client_bitmap(), request.output_path)


def _flush_events(app: wx.App) -> None:
    app.Yield()


def _wait_for_load(app: wx.App, frame: MainFrame) -> None:
    deadline = time.monotonic() + LOAD_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        status = frame.poll_docs_screenshot_load()
        _flush_events(app)
        if status == LoadStatus.COMPLETE:
            return
        if status == LoadStatus.ERROR:
            raise RuntimeError("Docs screenshot module failed to load")
        time.sleep(LOAD_CHECK_INTERVAL_MS / 1000.0)
    raise TimeoutError("Timed out waiting for docs screenshot module to load")


def _settle_frame(app: wx.App, frame: MainFrame) -> None:
    frame.Layout()
    frame.Refresh(False)
    for _ in range(SETTLE_EVENT_CYCLES):
        frame.Update()
        _flush_events(app)


def _save_bitmap(bitmap: wx.Bitmap, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not bitmap.SaveFile(str(output_path), wx.BITMAP_TYPE_PNG):
        raise OSError(f"Failed to save screenshot: {output_path}")


def _close_frame(frame: MainFrame) -> None:
    with suppress(RuntimeError):
        frame.Destroy()
