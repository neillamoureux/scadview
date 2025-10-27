import wx

from meshsee.controller import Controller
from meshsee.render.gl_widget_adapter import GlWidgetAdapter
from meshsee.ui.wx.moderngl_widget import create_graphics_widget

LOAD_CHECK_INTERVAL_MS = 10
INITIAL_FRAME_SIZE = (900, 600)


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
        label = self._menu_item_label()
        item = menu.Append(self._id, label)
        menu.Bind(wx.EVT_MENU, self._callback, item)
        return item

    def _menu_item_label(self):
        return (
            f"{self._label}\tCtrl+{self._accelerator}"
            if self._accelerator
            else self._label
        )


class CheckableAction(Action):
    def __init__(
        self,
        label: str,
        callback,
        initial_state: bool = False,
        accelerator: str | None = None,
    ):
        super().__init__(label, callback, accelerator)
        self._state = initial_state
        self._menu_items: list[wx.MenuItem] = []
        self._checkboxes: list[wx.CheckBox] = []

    def menu_item(self, menu):
        label = self._menu_item_label()
        item = menu.AppendCheckItem(self._id, label)
        item.Check(self._state)
        menu.Bind(wx.EVT_MENU, self._update_state, item)
        self._menu_items.append(item)
        return item

    def checkbox(self, parent: wx.Window) -> wx.CheckBox:
        chk = wx.CheckBox(parent, label=self._label, id=self._id)
        chk.Bind(wx.EVT_CHECKBOX, self._update_state)
        chk.SetValue(self._state)
        self._checkboxes.append(chk)
        return chk

    def _update_state(self, event):
        self._callback(event)
        self._state = not self._state
        for item in self._menu_items:
            item.Check(self._state)
        for chk in self._checkboxes:
            chk.SetValue(self._state)


class MainFrame(wx.Frame):
    def __init__(
        self,
        controller: Controller,
        gl_widget_adapter: GlWidgetAdapter,
    ):
        super().__init__(None, title="Meshsee", size=wx.Size(*INITIAL_FRAME_SIZE))
        self._controller = controller
        panel = wx.Panel(self)
        self._gl_widget = create_graphics_widget(panel, gl_widget_adapter)

        self._frame_action = Action("Frame", lambda _: self._gl_widget.frame(), "F")
        frame_btn = self._frame_action.button(panel)

        self._load_action = Action("Load .py...", self.on_load, "L")
        load_btn = self._load_action.button(panel)
        load_btn.Bind(wx.EVT_BUTTON, self.on_load)

        self._toggle_grid_action = CheckableAction(
            "Grid", self.on_toggle_grid, self._gl_widget.show_grid, "G"
        )
        toggle_grid_chk = self._toggle_grid_action.checkbox(panel)

        side = wx.BoxSizer(wx.VERTICAL)
        side.Add(frame_btn, 0, wx.ALL | wx.EXPAND, 6)
        side.Add(load_btn, 0, wx.ALL | wx.EXPAND, 6)
        side.Add(toggle_grid_chk, 0, wx.ALL | wx.EXPAND, 6)
        side.AddStretchSpacer()

        root = wx.BoxSizer(wx.HORIZONTAL)
        root.Add(self._gl_widget, 1, wx.EXPAND | wx.ALL, 6)
        root.Add(side, 0, wx.EXPAND | wx.ALL, 6)
        panel.SetSizer(root)
        self.make_menu_bar()

        self._loader_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_load_timer, self._loader_timer)
        self._loader_first_mesh = True
        self._loader_load_completed = False

    def on_load(self, _):
        with wx.FileDialog(
            self,
            "Load a python file",
            wildcard="Python files (*.py)|*.py",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                self._controller.load_mesh(dlg.GetPath())
                self._load_completed = False
                self._loader_first_mesh = True
                self._loader_timer.Start(30)

    def on_load_timer(self, _):
        mesh, self._load_completed = self._controller.check_load_queue()
        if self._load_completed:
            self._loader_timer.Stop()
        if mesh is not None:
            self._gl_widget.load_mesh(mesh, "loaded mesh")
            if self._loader_first_mesh:
                self._loader_first_mesh = False
                self._gl_widget.frame()

    def make_menu_bar(self):
        file_menu = wx.Menu()
        self._load_action.menu_item(file_menu)
        view_menu = wx.Menu()
        self._frame_action.menu_item(view_menu)
        self._toggle_grid_action.menu_item(view_menu)

        menuBar = wx.MenuBar()
        menuBar.Append(file_menu, "&File")
        menuBar.Append(view_menu, "&View")
        self.SetMenuBar(menuBar)

    def on_toggle_grid(self, _):
        self._gl_widget.toggle_grid()
