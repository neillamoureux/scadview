import logging

import wx
from trimesh import Trimesh

from meshsee.controller import Controller, export_formats
from meshsee.mesh_loader_process import LoadResult
from meshsee.render.gl_widget_adapter import GlWidgetAdapter
from meshsee.ui.wx.action import Action, CheckableAction, ChoiceAction
from meshsee.ui.wx.gl_widget import create_graphics_widget

logger = logging.getLogger(__name__)

LOAD_CHECK_INTERVAL_MS = 10
INITIAL_FRAME_SIZE = (900, 600)


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
        self._reload_action = Action("Reload", self.on_reload, "R")
        self._export_action = Action("Export...", self.export, "E")

    def _create_view_actions(self):
        self._frame_action = Action("Frame", lambda _: self._gl_widget.frame(), "F")
        self._view_from_xyz_action = Action(
            "XYZ", lambda _: self._gl_widget.view_from_xyz()
        )
        self._view_from_x_action = Action("X", lambda _: self._gl_widget.view_from_x())
        self._view_from_y_action = Action("Y", lambda _: self._gl_widget.view_from_y())
        self._view_from_z_action = Action("Z", lambda _: self._gl_widget.view_from_z())
        self._select_camera_action = ChoiceAction(
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
        self._toggle_axes_action = CheckableAction(
            "Axes",
            self.on_toggle_axes,
            self._gl_widget.show_axes,
            self._gl_widget.on_axes_change,
            "A",
        )
        self._toggle_edges_action = CheckableAction(
            "Edges",
            self.on_toggle_edges,
            self._gl_widget.show_edges,
            self._gl_widget.on_edges_change,
            "A",
        )
        self._toggle_gnonom_action = CheckableAction(
            "Gnomon",
            self.on_toggle_gnomon,
            self._gl_widget.show_gnomon,
            self._gl_widget.on_gnomon_change,
            "A",
        )

    def _set_camera_type(self, cam_type: str):
        self._gl_widget.camera_type = cam_type

    def _add_file_buttons(self):
        load_btn = self._load_action.button(self._button_panel)
        self._panel_sizer.Add(load_btn, 0, wx.ALL | wx.EXPAND, 6)
        self._reload_btn = self._reload_action.button(self._button_panel)
        self._reload_btn.Disable()
        self._controller.on_module_path_set.subscribe(self._on_module_path_set)
        self._panel_sizer.Add(self._reload_btn, 0, wx.ALL | wx.EXPAND, 6)
        self._export_btn = self._export_action.button(self._button_panel)
        self._export_btn.Disable()
        self._controller.on_current_mesh_set.subscribe(self._on_current_mesh_set)
        self._panel_sizer.Add(self._export_btn, 0, wx.ALL | wx.EXPAND, 6)

    def _on_module_path_set(self, path: str):
        if path == "":
            self._reload_btn.Disable()
            self._reload_menu_item.Enable(False)
        else:
            self._reload_btn.Enable()
            self._reload_menu_item.Enable(True)

    def _on_current_mesh_set(self, mesh: list[Trimesh] | Trimesh | None):
        enable = False
        if mesh is not None:
            if isinstance(mesh, list) and len(mesh) > 0:
                enable = True
            elif isinstance(mesh, Trimesh):
                enable = True
        self._export_btn.Enable() if enable else self._export_btn.Disable()
        self._export_menu_item.Enable(enable)

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

        for rb in self._select_camera_action.radio_buttons(self._button_panel):
            self._panel_sizer.Add(rb, 0, wx.ALL | wx.EXPAND, 6)

        for action in [
            self._toggle_axes_action,
            self._toggle_edges_action,
            self._toggle_gnonom_action,
        ]:
            chk = action.checkbox(self._button_panel)
            self._panel_sizer.Add(chk, 0, wx.ALL | wx.EXPAND, 6)

    def _create_file_menu(self) -> wx.Menu:
        file_menu = wx.Menu()
        self._load_action.menu_item(file_menu)
        self._reload_menu_item = self._reload_action.menu_item(file_menu)
        self._reload_menu_item.Enable(False)
        self._export_menu_item = self._export_action.menu_item(file_menu)
        self._export_menu_item.Enable(False)

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

        self._select_camera_action.menu_items(view_menu)

        for action in [
            self._toggle_axes_action,
            self._toggle_edges_action,
            self._toggle_gnonom_action,
        ]:
            action.menu_item(view_menu)

        return view_menu

    def on_load(self, _: wx.Event):
        with wx.FileDialog(
            self,
            "Load a python file",
            wildcard="Python files (*.py)|*.py",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dlg:  # pyright: ignore[reportUnknownVariableType]
            if dlg.ShowModal() == wx.ID_OK:
                self._controller.load_mesh(
                    dlg.GetPath()  # pyright: ignore[reportUnknownArgumentType]
                )
                self._loader_timer.Start(LOAD_CHECK_INTERVAL_MS)

    def on_reload(self, _: wx.Event):
        self._controller.reload_mesh()
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

    def export(self, _: wx.Event):
        default_export_path = self._controller.default_export_path()
        fmts = export_formats()
        wildcard = "|".join([f"{fmt.upper()} (*.{fmt})|*.{fmt}" for fmt in fmts])
        with wx.FileDialog(
            self,
            "Export",
            defaultFile=default_export_path,
            wildcard=wildcard,
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dlg:  # pyright: ignore[reportUnknownVariableType]
            if dlg.ShowModal() == wx.ID_OK:
                try:
                    self._controller.export(
                        dlg.GetPath()  # pyright: ignore[reportUnknownArgumentType]
                    )
                except Exception as e:
                    logger.error(f"Failure on export: {e}")

    def on_toggle_grid(self, _: wx.Event):
        self._gl_widget.toggle_grid()

    def on_toggle_axes(self, _: wx.Event):
        self._gl_widget.toggle_axes()

    def on_toggle_edges(self, _: wx.Event):
        self._gl_widget.toggle_edges()

    def on_toggle_gnomon(self, _: wx.Event):
        self._gl_widget.toggle_gnomon()

    def on_close(self, _: wx.Event):
        self._loader_timer.Stop()
        del self._controller
        self.Destroy()
