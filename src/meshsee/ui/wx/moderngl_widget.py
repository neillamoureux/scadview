from __future__ import annotations

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

from meshsee.render.gl_widget_adapter import GlWidgetAdapter


def create_graphics_widget(
    parent: wx.Window, gl_widget_adapter: GlWidgetAdapter
) -> ModernglWidget:
    gl_widget = ModernglWidget(parent, gl_widget_adapter)
    return gl_widget


class ModernglWidget(GLCanvas):
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

        # prevent background erase flicker on some platforms
        self.Bind(wx.EVT_ERASE_BACKGROUND, lambda e: None)

        self.ctx_wx = GLContext(self)  # native GL context
        self.ctx_mgl = None  # ModernGL context (lazy)
        self.prog = None
        self.vbo = None
        self.vao = None

        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_LEFT_DOWN, self.on_mouse_press_left)
        self.Bind(wx.EVT_LEFT_UP, self.on_mouse_release_left)
        self.Bind(wx.EVT_MOTION, self.on_mouse_move)

    def on_size(self, _evt: wx.SizeEvent):
        # Just schedule a repaint; set viewport during paint when context is current.
        size = self.GetClientSize()
        self._gl_widget_adapter.resize(size.width, size.height)
        self.Refresh(False)

    def on_paint(self, _evt: wx.PaintEvent):
        # Required so wx knows we handled the paint.
        dc = wx.PaintDC(self)
        del dc
        self.SetCurrent(self.ctx_wx)
        size = self.GetClientSize()
        self._gl_widget_adapter.render(size.width, size.height)
        self.SwapBuffers()

    def on_mouse_press_left(self, event: wx.MouseEvent):
        pos = event.GetPosition()
        self._gl_widget_adapter.start_orbit(int(pos.x), int(pos.y))

    def on_mouse_release_left(self, event: wx.MouseEvent):
        self._gl_widget_adapter.end_orbit()

    def on_mouse_move(self, event: wx.MouseEvent):
        """
        Rotate the camera based on mouse movement.
        """
        pos = event.GetPosition()
        self._gl_widget_adapter.do_orbit(int(pos.x), int(pos.y))
        self.Refresh(False)

    def load_mesh(self, mesh: Trimesh | list[Trimesh], name: str):
        self._gl_widget_adapter.load_mesh(mesh, name)
        self.Refresh(False)
