from __future__ import annotations

import logging

import wx
from trimesh import Trimesh
from wx.glcanvas import (
    WX_GL_CORE_PROFILE,
    WX_GL_DEPTH_SIZE,
    WX_GL_DOUBLEBUFFER,
    WX_GL_MAJOR_VERSION,
    WX_GL_MINOR_VERSION,
    WX_GL_RGBA,
    WX_GL_STENCIL_SIZE,
    GLCanvas,
    GLContext,
)

from meshsee.load_status import LoadStatus
from meshsee.render.gl_widget_adapter import GlWidgetAdapter

logger = logging.getLogger(__name__)


def create_graphics_widget(
    parent: wx.Window, gl_widget_adapter: GlWidgetAdapter
) -> GlWidget:
    gl_widget = GlWidget(parent, gl_widget_adapter)
    return gl_widget


class GlWidget(GLCanvas):
    def __init__(self, parent: wx.Window, gl_widget_adapter: GlWidgetAdapter):
        attribs = [
            WX_GL_CORE_PROFILE,
            1,
            WX_GL_MAJOR_VERSION,
            3,
            WX_GL_MINOR_VERSION,
            3,
            WX_GL_DOUBLEBUFFER,
            1,
            WX_GL_RGBA,
            1,
            WX_GL_DEPTH_SIZE,
            24,
            WX_GL_STENCIL_SIZE,
            8,
            0,
        ]
        super().__init__(parent, attribList=attribs)
        self._gl_widget_adapter = gl_widget_adapter

        self.ctx_wx = GLContext(self)  # native GL context

        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_LEFT_DOWN, self.on_mouse_press_left)
        self.Bind(wx.EVT_LEFT_UP, self.on_mouse_release_left)
        self.Bind(wx.EVT_MOTION, self.on_mouse_move)
        self.Bind(wx.EVT_MOUSEWHEEL, self.on_mouse_wheel)

        self.Bind(wx.EVT_KEY_DOWN, self.on_key_down)

        self.on_camera_change = self._gl_widget_adapter.on_camera_change
        self.on_grid_change = self._gl_widget_adapter.on_grid_change
        self.on_axes_change = self._gl_widget_adapter.on_axes_change
        self.on_edges_change = self._gl_widget_adapter.on_edges_change
        self.on_gnomon_change = self._gl_widget_adapter.on_gnomon_change

        self._mouse_captured = False

    @property
    def show_grid(self):
        return self._gl_widget_adapter.show_grid

    @show_grid.setter
    def show_grid(self, value: bool):
        self._gl_widget_adapter.show_grid = value
        self.Refresh()

    def toggle_grid(self):
        self._gl_widget_adapter.toggle_grid()
        self.Refresh()

    def on_size(self, _evt: wx.SizeEvent):
        # Just schedule a repaint; set viewport during paint when context is current.
        size: wx.Size = (  # pyright: ignore[reportUnknownVariableType]
            self.GetClientSize()
        )
        self._gl_widget_adapter.resize(
            size.width,  # pyright: ignore[reportUnknownArgumentType]
            size.height,  # pyright: ignore[reportUnknownArgumentType]
        )
        self.Refresh(False)

    def on_paint(self, _evt: wx.PaintEvent):
        logger.debug("on_paint start")
        # Required so wx knows we handled the paint.
        try:
            self.SetSwapInterval(1)  # 0 = disable vsync, 1 = enable
        except Exception:
            pass
        dc = wx.PaintDC(self)
        del dc
        self.SetCurrent(self.ctx_wx)
        size = self.GetClientSize()  # pyright: ignore[reportUnknownVariableType]
        scale = (  # pyright: ignore[reportUnknownVariableType]
            self.GetContentScaleFactor()
        )
        self._gl_widget_adapter.render(
            scale * size.width,  # pyright: ignore[reportUnknownArgumentType]
            scale * size.height,  # pyright: ignore[reportUnknownArgumentType]
        )
        self.SwapBuffers()
        logger.debug("on_paint end")

    def on_mouse_press_left(self, event: wx.MouseEvent):
        pos = event.GetPosition()
        if not self._mouse_captured:
            self.CaptureMouse()
            self._mouse_captured = True
        self._gl_widget_adapter.start_orbit(int(pos.x), int(pos.y))

    def on_mouse_release_left(self, event: wx.MouseEvent):
        if self._mouse_captured:
            self.ReleaseMouse()
            self._mouse_captured = False
        self._gl_widget_adapter.end_orbit()

    def on_mouse_wheel(self, event: wx.MouseEvent):
        if event.GetWheelAxis() == wx.MOUSE_WHEEL_VERTICAL:
            distance = event.GetWheelRotation()
            position = self._get_scaled_position(event)
            self._gl_widget_adapter.move_to_screen(
                int(position.x),
                int(position.y),
                distance,
            )
        self.Refresh(False)

    def _get_scaled_position(self, event: wx.MouseEvent) -> wx.Point:
        pos = event.GetPosition()
        device_scale = (  # pyright: ignore[reportUnknownVariableType]
            self.GetContentScaleFactor()
        )
        return wx.Point(
            int(pos.x * device_scale),  # pyright: ignore[reportUnknownArgumentType]
            int(pos.y * device_scale),  # pyright: ignore[reportUnknownArgumentType]
        )

    def on_mouse_move(self, event: wx.MouseEvent):
        """
        Rotate the camera based on mouse movement.
        """
        pos = event.GetPosition()
        self._gl_widget_adapter.do_orbit(int(pos.x), int(pos.y))
        self.Refresh(False)

    def on_key_down(self, event: wx.KeyEvent):
        code = event.GetKeyCode()
        if code in (wx.WXK_UP, ord("W"), ord("w")):
            self._gl_widget_adapter.move(1.0)
        elif code in (wx.WXK_DOWN, ord("S"), ord("s")):
            self._gl_widget_adapter.move(-1.0)
        elif code in (wx.WXK_LEFT, ord("A"), ord("a")):
            self._gl_widget_adapter.move_right(-1.0)
        elif code in (wx.WXK_RIGHT, ord("D"), ord("d")):
            self._gl_widget_adapter.move_right(1.0)
        elif code in (wx.WXK_PAGEUP, ord("Q"), ord("q")):
            self._gl_widget_adapter.move_up(1.0)
        elif code in (wx.WXK_PAGEDOWN, ord("E"), ord("e")):
            self._gl_widget_adapter.move_up(-1.0)
        else:
            event.Skip()  # let other handlers process unhandled keys
            return
        self.Refresh(False)

    def load_mesh(self, mesh: Trimesh | list[Trimesh], name: str):
        self._gl_widget_adapter.load_mesh(mesh, name)
        self.Refresh(False)

    def frame(self):
        self._gl_widget_adapter.frame()
        self.Refresh(False)

    def view_from_xyz(self):
        self._gl_widget_adapter.view_from_xyz()
        self.Refresh(False)

    def view_from_x(self):
        self._gl_widget_adapter.view_from_x()
        self.Refresh(False)

    def view_from_y(self):
        self._gl_widget_adapter.view_from_y()
        self.Refresh(False)

    def view_from_z(self):
        self._gl_widget_adapter.view_from_z()
        self.Refresh(False)

    @property
    def camera_type(self) -> str:
        return self._gl_widget_adapter.camera_type

    @camera_type.setter
    def camera_type(self, value: str):
        self._gl_widget_adapter.camera_type = value
        self.Refresh()

    def toggle_camera(self):
        self._gl_widget_adapter.toggle_camera()
        self.Refresh(False)

    @property
    def show_axes(self) -> bool:
        return self._gl_widget_adapter.show_axes

    def toggle_axes(self):
        self._gl_widget_adapter.toggle_axes()
        self.Refresh(False)

    @property
    def show_edges(self) -> bool:
        return self._gl_widget_adapter.show_edges

    def toggle_edges(self):
        self._gl_widget_adapter.toggle_edges()
        self.Refresh(False)

    @property
    def show_gnomon(self) -> bool:
        return self._gl_widget_adapter.show_gnomon

    def toggle_gnomon(self):
        self._gl_widget_adapter.toggle_gnomon()
        self.Refresh(False)

    def indicate_load_status(self, status: LoadStatus):
        self._gl_widget_adapter.indicate_load_status(status)
        self.Refresh(False)
