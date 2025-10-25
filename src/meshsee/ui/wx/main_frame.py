import wx

# from meshsee.ui.wx.moderngl_widget import ModernglWidget
from meshsee.controller import Controller
from meshsee.render.gl_widget_adapter import GlWidgetAdapter
from meshsee.ui.wx.moderngl_widget import create_graphics_widget


class MainFrame(wx.Frame):
    def __init__(
        self,
        controller: Controller,
        gl_widget_adapter: GlWidgetAdapter,
    ):
        super().__init__(
            None, title="wx + ModernGL (fixed mac SwapBuffers)", size=(900, 600)
        )
        self._controller = controller
        panel = wx.Panel(self)
        self._gl_widget = create_graphics_widget(panel, gl_widget_adapter)
        # self.gl = ModernglWidget(panel)

        # Native controls
        chk = wx.CheckBox(panel, label="Enable option")
        frame_action_id = wx.NewIdRef()
        frame_action_label = "Frame Mesh\tCtrl-F"
        frame_btn = wx.Button(panel, label=frame_action_label, id=frame_action_id)
        load_btn = wx.Button(panel, label="Load .py...")

        frame_btn.Bind(
            wx.EVT_BUTTON,
            lambda _: self._gl_widget.frame(),
        )
        load_btn.Bind(wx.EVT_BUTTON, self.on_load)

        side = wx.BoxSizer(wx.VERTICAL)
        side.Add(chk, 0, wx.ALL | wx.EXPAND, 6)
        side.Add(frame_btn, 0, wx.ALL | wx.EXPAND, 6)
        side.Add(load_btn, 0, wx.ALL | wx.EXPAND, 6)
        side.AddStretchSpacer()

        root = wx.BoxSizer(wx.HORIZONTAL)
        root.Add(self._gl_widget, 1, wx.EXPAND | wx.ALL, 6)
        root.Add(side, 0, wx.EXPAND | wx.ALL, 6)
        panel.SetSizer(root)

    def on_load(self, _):
        with wx.FileDialog(
            self,
            "Choose a file",
            wildcard="Pythons files (*.py)|*.py",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                for mesh in self._controller.load_mesh(dlg.GetPath()):
                    self._gl_widget.load_mesh(mesh, "test")
                    self._gl_widget.frame()
