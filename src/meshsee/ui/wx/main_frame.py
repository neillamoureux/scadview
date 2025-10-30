import logging

import wx
from typing import Any, Callable, TypeVar, Generic


from meshsee.controller import Controller
from meshsee.mesh_loader_process import LoadResult
from meshsee.render.gl_widget_adapter import GlWidgetAdapter
from meshsee.ui.wx.moderngl_widget import create_graphics_widget
from meshsee.observable import Observable

logger = logging.getLogger(__name__)

LOAD_CHECK_INTERVAL_MS = 10
INITIAL_FRAME_SIZE = (900, 600)


class Action:
    def __init__(
        self,
        label: str,
        callback: Callable[[wx.Event], None],
        accelerator: str | None = None,
    ):
        self._label = label
        self._callback = callback
        self._accelerator = accelerator
        self._id: int = wx.NewIdRef()

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
        callback: Callable[[wx.Event], None],
        initial_state: bool,
        on_state_change: Observable,
        accelerator: str | None = None,
    ):
        super().__init__(label, callback, accelerator)
        on_state_change.subscribe(self._on_state_change)
        self._initial_state = initial_state
        self._menu_items: list[wx.MenuItem] = []
        self._checkboxes: list[wx.CheckBox] = []

    def menu_item(self, menu: wx.Menu):
        label = self._menu_item_label()
        item = menu.AppendCheckItem(self._id, label)
        item.Check(self._initial_state)
        menu.Bind(wx.EVT_MENU, self._update_state, item)
        self._menu_items.append(item)
        return item

    def checkbox(self, parent: wx.Window) -> wx.CheckBox:
        chk = wx.CheckBox(parent, label=self._label, id=self._id)
        chk.Bind(wx.EVT_CHECKBOX, self._update_state)
        chk.SetValue(self._initial_state)
        self._checkboxes.append(chk)
        return chk

    def _update_state(self, event: wx.Event):
        self._callback(event)

    def _on_state_change(self, state: bool):
        for item in self._menu_items:
            item.Check(state)
        for chk in self._checkboxes:
            chk.SetValue(state)


class ChoiceAction:
    def __init__(
        self,
        labels: list[str],
        values: list[str],
        callback: Callable[[wx.CommandEvent, str], None],
        initial_value: str,
        on_value_change: Observable,
    ):
        on_value_change.subscribe(self._on_value_change)
        self._labels = labels
        self._values = values
        self._callback = callback
        self._initial_value = initial_value
        self._id: int = wx.NewIdRef()
        self._radio_buttons: list[wx.RadioButton] = []
        self._menu_items: list[wx.MenuItem] = []

    def _on_value_change(self, value: str):
        for rb, v in zip(self._radio_buttons, self._values):
            rb.SetValue(v == value)
        for item, v in zip(self._menu_items, self._values):
            item.Check(v == value)

    def menu_items(self, menu: wx.Menu) -> list[wx.MenuItem]:
        for label, value in zip(self._labels, self._values):
            item = menu.AppendRadioItem(id=wx.ID_ANY, item=label)
            item.Check(self._initial_value == value)
            menu.Bind(wx.EVT_MENU, self._update_value_from_menu, item)
            self._menu_items.append(item)
        return self._menu_items

    def radio_buttons(self, parent: wx.Window) -> list[wx.RadioButton]:
        self._radio_buttons: list[wx.RadioButton] = []
        first = True
        for label, value in zip(self._labels, self._values):
            if first:
                rb = wx.RadioButton(parent, label=label, style=wx.RB_GROUP)
            else:
                rb = wx.RadioButton(parent, label=label)
            rb.SetValue(value == self._initial_value)
            rb.Bind(
                wx.EVT_RADIOBUTTON,
                self._update_value_from_radio_button,
            )
            self._radio_buttons.append(rb)
        return self._radio_buttons

    def _update_value_from_radio_button(self, e: wx.CommandEvent):
        for label, value in zip(self._labels, self._values):
            if label == e.GetEventObject().GetLabel():
                self._callback(e, value)

    def _update_value_from_menu(self, e: wx.CommandEvent):
        event_item_id = e.GetId()
        for item, value in zip(self._menu_items, self._values):
            item_id = item.GetId()
            if e.IsChecked() and event_item_id == item_id:
                self._callback(e, value)


class MainFrame(wx.Frame):
    def __init__(
        self,
        controller: Controller,
        gl_widget_adapter: GlWidgetAdapter,
    ):
        super().__init__(None, title="Meshsee", size=wx.Size(*INITIAL_FRAME_SIZE))
        self._controller = controller
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self._button_panel = wx.Panel(self)
        self._gl_widget = create_graphics_widget(self._button_panel, gl_widget_adapter)

        self._create_file_actions()
        self._create_view_actions()

        self._panel_sizer = wx.BoxSizer(wx.VERTICAL)

        self._add_file_buttons()
        self._add_view_buttons()

        self._panel_sizer.AddStretchSpacer()

        root = wx.BoxSizer(wx.HORIZONTAL)
        root.Add(self._gl_widget, 1, wx.EXPAND | wx.ALL, 6)
        root.Add(self._panel_sizer, 0, wx.EXPAND | wx.ALL, 6)
        self._button_panel.SetSizer(root)

        menu_bar = wx.MenuBar()
        menu_bar.Append(self._create_file_menu(), "File")
        menu_bar.Append(self._create_view_menu(), "View")
        self.SetMenuBar(menu_bar)

        self._loader_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_load_timer, self._loader_timer)
        self._loader_load_completed = False
        self._loader_last_load_number = 0
        self._loader_last_sequence_number = 0

    def _create_file_actions(self):
        self._load_action = Action("Load .py...", self.on_load, "L")

    def _create_view_actions(self):
        self._frame_action = Action("Frame", lambda _: self._gl_widget.frame(), "F")
        self._view_from_xyz_action = Action(
            "XYZ", lambda _: self._gl_widget.view_from_xyz()
        )
        self._view_from_x_action = Action("X", lambda _: self._gl_widget.view_from_x())
        self._view_from_y_action = Action("Y", lambda _: self._gl_widget.view_from_y())
        self._view_from_z_action = Action("Z", lambda _: self._gl_widget.view_from_z())
        self._toggle_camera_action = ChoiceAction(
            ["Perspective", "Orthogonal"],
            ["perspective", "orthogonal"],
            lambda _, value: self._set_camera_type(value),
            self._gl_widget.camera_type,
            self._gl_widget.on_camera_change,
        )
        self._toggle_grid_action = CheckableAction(
            "Grid",
            self.on_toggle_grid,
            self._gl_widget.show_grid,
            self._gl_widget.on_grid_change,
            "G",
        )

    def _set_camera_type(self, cam_type: str):
        self._gl_widget.camera_type = cam_type

    def _add_file_buttons(self):
        load_btn = self._load_action.button(self._button_panel)
        self._panel_sizer.Add(load_btn, 0, wx.ALL | wx.EXPAND, 6)

    def _add_view_buttons(self):
        for action in [
            self._frame_action,
            self._view_from_xyz_action,
            self._view_from_x_action,
            self._view_from_y_action,
            self._view_from_z_action,
        ]:
            btn = action.button(self._button_panel)
            self._panel_sizer.Add(btn, 0, wx.ALL | wx.EXPAND, 6)

        chk = self._toggle_grid_action.checkbox(self._button_panel)
        self._panel_sizer.Add(chk, 0, wx.ALL | wx.EXPAND, 6)

        for rb in self._toggle_camera_action.radio_buttons(self._button_panel):
            self._panel_sizer.Add(rb, 0, wx.ALL | wx.EXPAND, 6)

    def _create_file_menu(self) -> wx.Menu:
        file_menu = wx.Menu()
        self._load_action.menu_item(file_menu)
        return file_menu

    def _create_view_menu(self) -> wx.Menu:
        view_menu = wx.Menu()
        for action in [
            self._frame_action,
            self._view_from_xyz_action,
            self._view_from_x_action,
            self._view_from_y_action,
            self._view_from_z_action,
            self._toggle_grid_action,
        ]:
            action.menu_item(view_menu)

        self._toggle_camera_action.menu_items(view_menu)
        return view_menu

    def on_load(self, _: wx.Event):
        with wx.FileDialog(
            self,
            "Load a python file",
            wildcard="Python files (*.py)|*.py",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                self._controller.load_mesh(dlg.GetPath())
                self._loader_timer.Start(LOAD_CHECK_INTERVAL_MS)

    def on_load_timer(self, _: wx.Event):
        load_result = self._controller.check_load_queue()
        mesh = load_result.mesh
        if load_result.complete:
            self._loader_timer.Stop()
        if load_result.error:
            logger.error(load_result.error)
        if self._has_mesh_changed(load_result):
            if mesh is not None:  # Keep the type checker happy
                self._gl_widget.load_mesh(mesh, "loaded mesh")
            if self._is_first_in_load(load_result):
                self._gl_widget.frame()
            self._loader_last_load_number = load_result.load_number
            self._loader_last_sequence_number = load_result.sequence_number

    def _has_mesh_changed(self, load_result: LoadResult) -> bool:
        return load_result.mesh is not None and (
            self._loader_last_load_number != load_result.load_number
            or self._loader_last_sequence_number != load_result.sequence_number
        )

    def _is_first_in_load(self, load_result: LoadResult) -> bool:
        return self._loader_last_load_number != load_result.load_number

    def on_toggle_grid(self, _: wx.Event):
        self._gl_widget.toggle_grid()

    def on_close(self, _: wx.Event):
        self._loader_timer.Stop()
        del self._controller
        self.Destroy()
