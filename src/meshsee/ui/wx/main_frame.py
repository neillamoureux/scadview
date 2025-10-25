import wx

# from meshsee.ui.wx.moderngl_widget import ModernglWidget
from meshsee.controller import Controller
from meshsee.render.gl_widget_adapter import GlWidgetAdapter
from meshsee.ui.wx.moderngl_widget import create_graphics_widget


class Action:
    def __init__(self, label: str, callback, accelerator: str | None = None):
        self._label = label
        self._callback = callback
        self._accelerator = accelerator
        self._id = wx.NewIdRef()

    def button(self, parent: wx.Window) -> wx.Button:
        btn = wx.Button(parent, label=self._label, id=self._id)
        btn.Bind(wx.EVT_BUTTON, self._callback)
        return btn

    def menu_item(self, menu: wx.Menu) -> wx.MenuItem:
        label = (
            f"{self._label}\tCtrl+{self._accelerator}"
            if self._accelerator
            else self._label
        )
        item = menu.Append(self._id, label)
        menu.Bind(wx.EVT_MENU, self._callback, item)
        return item


class MainFrame(wx.Frame):
    def __init__(
        self,
        controller: Controller,
        gl_widget_adapter: GlWidgetAdapter,
    ):
        super().__init__(None, title="Meshsee", size=(900, 600))
        self._controller = controller
        panel = wx.Panel(self)
        self._gl_widget = create_graphics_widget(panel, gl_widget_adapter)

        chk = wx.CheckBox(panel, label="Enable option")
        self._frame_action = Action("Frame", lambda _: self._gl_widget.frame(), "F")
        frame_btn = self._frame_action.button(panel)

        self._load_action = Action("Load .py...", self.on_load, "L")
        load_btn = self._load_action.button(panel)
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
        self.make_menu_bar()

    def on_load(self, _):
        with wx.FileDialog(
            self,
            "Load a python file",
            wildcard="Python files (*.py)|*.py",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                for mesh in self._controller.load_mesh(dlg.GetPath()):
                    self._gl_widget.load_mesh(mesh, "test")
                    self._gl_widget.frame()

    def make_menu_bar(self):
        file_menu = wx.Menu()
        self._load_action.menu_item(file_menu)
        view_menu = wx.Menu()
        self._frame_action.menu_item(view_menu)

        menuBar = wx.MenuBar()
        menuBar.Append(file_menu, "&File")
        menuBar.Append(view_menu, "&View")
        self.SetMenuBar(menuBar)
