import wx
from wx.glcanvas import GLCanvas, GLContext
import moderngl
import numpy as np


VERT_SRC = """
#version 330
in vec2 in_pos;
void main() { gl_Position = vec4(in_pos, 0.0, 1.0); }
"""

FRAG_SRC = """
#version 330
out vec4 f_color;
void main() { f_color = vec4(0.2, 0.8, 0.4, 1.0); }
"""


class GlUi:
    def __init__(self, controller, gl_widget_adapter):
        self.app = wx.App(False)
        self.frame = MainFrame()

    def run(self):
        self.frame.Show()
        self.app.MainLoop()


class GLPanel(GLCanvas):
    def __init__(self, parent):
        attribs = [
            wx.glcanvas.WX_GL_CORE_PROFILE,
            1,
            wx.glcanvas.WX_GL_MAJOR_VERSION,
            3,
            wx.glcanvas.WX_GL_MINOR_VERSION,
            3,
            wx.glcanvas.WX_GL_DOUBLEBUFFER,
            1,
            wx.glcanvas.WX_GL_RGBA,
            1,
            wx.glcanvas.WX_GL_DEPTH_SIZE,
            24,
            wx.glcanvas.WX_GL_STENCIL_SIZE,
            8,
            0,
        ]
        super().__init__(parent, attribList=attribs)

        # prevent background erase flicker on some platforms
        self.Bind(wx.EVT_ERASE_BACKGROUND, lambda e: None)

        self.ctx_wx = GLContext(self)  # native GL context
        self.ctx_mgl = None  # ModernGL context (lazy)
        self.prog = None
        self.vbo = None
        self.vao = None

        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_SIZE, self.on_size)

    def init_mgl(self):
        """Create ModernGL resources; assumes wx context is current."""
        if self.ctx_mgl:
            return
        self.ctx_mgl = moderngl.create_context()  # binds to current OS context
        self.prog = self.ctx_mgl.program(
            vertex_shader=VERT_SRC, fragment_shader=FRAG_SRC
        )
        tri = np.array(
            [
                -0.6,
                -0.5,
                0.6,
                -0.5,
                0.0,
                0.6,
            ],
            dtype="f4",
        )
        self.vbo = self.ctx_mgl.buffer(tri.tobytes())
        self.vao = self.ctx_mgl.simple_vertex_array(self.prog, self.vbo, "in_pos")

    def on_size(self, _evt):
        # Just schedule a repaint; set viewport during paint when context is current.
        self.Refresh(False)

    def on_paint(self, _evt):
        # Required so wx knows we handled the paint.
        dc = wx.PaintDC(self)
        del dc

        # Make the native GL context current **every paint** (important on macOS).
        self.SetCurrent(self.ctx_wx)

        # Lazy-create ModernGL linked to the current native context.
        if not self.ctx_mgl:
            self.init_mgl()

        # Resize viewport to current drawable size.
        w, h = self.GetSize()
        self.ctx_mgl.viewport = (0, 0, max(1, w), max(1, h))

        # Draw
        self.ctx_mgl.clear(0.08, 0.08, 0.1, 1.0)
        self.vao.render()

        # Swap requires a current context on macOS.
        self.SwapBuffers()


class MainFrame(wx.Frame):
    def __init__(self):
        super().__init__(
            None, title="wx + ModernGL (fixed mac SwapBuffers)", size=(900, 600)
        )
        panel = wx.Panel(self)
        self.gl = GLPanel(panel)

        # Native controls
        chk = wx.CheckBox(panel, label="Enable option")
        btn = wx.Button(panel, label="Do thing")
        file_btn = wx.Button(panel, label="Open file…")

        btn.Bind(
            wx.EVT_BUTTON,
            lambda _: wx.MessageBox(
                f"Checkbox is {'checked' if chk.IsChecked() else 'unchecked'}", "Info"
            ),
        )
        file_btn.Bind(wx.EVT_BUTTON, self.on_open)

        side = wx.BoxSizer(wx.VERTICAL)
        side.Add(chk, 0, wx.ALL | wx.EXPAND, 6)
        side.Add(btn, 0, wx.ALL | wx.EXPAND, 6)
        side.Add(file_btn, 0, wx.ALL | wx.EXPAND, 6)
        side.AddStretchSpacer()

        root = wx.BoxSizer(wx.HORIZONTAL)
        root.Add(self.gl, 1, wx.EXPAND | wx.ALL, 6)
        root.Add(side, 0, wx.EXPAND | wx.ALL, 6)
        panel.SetSizer(root)

    def on_open(self, _):
        with wx.FileDialog(
            self,
            "Choose a file",
            wildcard="All files (*.*)|*.*",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                wx.MessageBox(f"Selected: {dlg.GetPath()}", "File chosen")


if __name__ == "__main__":
    app = wx.App(False)
    MainFrame().Show()
    app.MainLoop()
