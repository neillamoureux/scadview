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
        panel = wx.Panel(self)
        self._gl_widget = create_graphics_widget(panel, gl_widget_adapter)
        # self.gl = ModernglWidget(panel)

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
        root.Add(self._gl_widget, 1, wx.EXPAND | wx.ALL, 6)
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
