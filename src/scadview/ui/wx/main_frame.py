from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import cast

import wx
from trimesh import Trimesh

from scadview.controller import Controller, export_formats
from scadview.features import FeatureState
from scadview.load_status import LoadStatus
from scadview.mesh_loader_process import LoadResult
from scadview.render.gl_widget_adapter import GlWidgetAdapter
from scadview.ui.view_state import ViewState
from scadview.ui.wx.action import (
    Action,
    CheckableAction,
    ChoiceAction,
    EnableableAction,
)
from scadview.ui.wx.font_dialog import FontDialog
from scadview.ui.wx.gl_widget import create_graphics_widget

logger = logging.getLogger(__name__)

LOAD_CHECK_INTERVAL_MS = 10
INITIAL_FRAME_SIZE = (900, 600)
BORDER_SIZE = 6


class MainFrame(wx.Frame):
    def __init__(
        self,
        controller: Controller,
        gl_widget_adapter: GlWidgetAdapter,
    ):
        super().__init__(None, title="SCADview", size=wx.Size(*INITIAL_FRAME_SIZE))
        self._controller = controller

        self.Bind(wx.EVT_CLOSE, self.on_close)
        self._button_panel = wx.Panel(self)
        self._gl_widget = create_graphics_widget(self._button_panel, gl_widget_adapter)

        self._create_file_actions()
        self._create_view_actions()
        self._create_help_actions()

        self._panel_sizer = wx.BoxSizer(wx.VERTICAL)
        self._load_progress_gauge = wx.Gauge(
            self._button_panel, style=wx.GA_HORIZONTAL | wx.GA_SMOOTH | wx.GA_PROGRESS
        )
        self._panel_sizer.Add(
            self._load_progress_gauge, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, BORDER_SIZE
        )

        self._add_file_buttons()
        self._add_feature_controls()
        self._add_view_buttons()

        root = wx.BoxSizer(wx.HORIZONTAL)
        root.Add(
            self._gl_widget,
            1,
            wx.EXPAND | wx.ALL,
        )
        root.Add(self._panel_sizer, 0, wx.EXPAND | wx.ALL, BORDER_SIZE)
        self._button_panel.SetSizer(root)

        menu_bar = wx.MenuBar()
        menu_bar.Append(self._create_file_menu(), "File")
        menu_bar.Append(self._create_view_menu(), "View")
        menu_bar.Append(self._create_help_menu(), "Help")
        self.SetMenuBar(menu_bar)

        self._loader_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_load_timer, self._loader_timer)
        self._loader_load_completed = False
        self._loader_last_load_number = 0
        self._loader_last_sequence_number = 0
        self._controller.on_load_status_change.subscribe(self._indicate_load_status)
        self._controller.on_features_change.subscribe(self._update_feature_controls)

    def _create_file_actions(self):
        self._load_action = Action("Load .py...", self.on_load, "L")
        self._reload_action = EnableableAction[str](
            Action("Reload", self.on_reload, accelerator="R"),
            initial_value="",
            on_value_change=self._controller.on_module_path_set,
            enable_func=self._on_module_path_set,
        )
        self._export_action = EnableableAction[LoadStatus](
            Action("Export...", self.export, accelerator="E"),
            initial_value=LoadStatus.NONE,
            on_value_change=self._controller.on_load_status_change,
            enable_func=self._can_be_exported,
        )
        self._debug_features_action = CheckableAction[bool](
            Action("Debug features", self._on_debug_features_toggle, checkable=True),
            self._controller.debug_features,
            lambda value: value,
            self._controller.on_debug_features_change,
        )

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
        self._toggle_grid_action = CheckableAction[bool](
            Action("Grid", self.on_toggle_grid, "G", checkable=True),
            self._gl_widget.show_grid,
            lambda x: x,
            self._gl_widget.on_grid_change,
        )
        self._toggle_axes_action = CheckableAction(
            Action("Axes", self.on_toggle_axes, "A", checkable=True),
            self._gl_widget.show_axes,
            lambda x: x,
            self._gl_widget.on_axes_change,
        )
        self._toggle_edges_action = CheckableAction(
            Action("Edges", self.on_toggle_edges, "A", checkable=True),
            self._gl_widget.show_edges,
            lambda x: x,
            self._gl_widget.on_edges_change,
        )
        self._toggle_gnonom_action = CheckableAction(
            Action("Gnomon", self.on_toggle_gnomon, "A", checkable=True),
            self._gl_widget.show_gnomon,
            lambda x: x,
            self._gl_widget.on_gnomon_change,
        )

    def _set_camera_type(self, cam_type: str):
        self._gl_widget.camera_type = cam_type

    def _create_help_actions(self) -> None:
        self._show_fonts_action = Action("Fonts", self._open_font_dialog)

    def _open_font_dialog(self, _evt: wx.Event):
        dlg = FontDialog(None)
        dlg.ShowModal()
        dlg.Destroy()

    def _add_file_buttons(self):
        load_btn = self._load_action.button(self._button_panel)
        self._panel_sizer.Add(load_btn, 0, wx.ALL | wx.EXPAND, BORDER_SIZE)
        self._reload_btn = self._reload_action.button(self._button_panel)
        self._panel_sizer.Add(self._reload_btn, 0, wx.ALL | wx.EXPAND, BORDER_SIZE)
        self._export_btn = self._export_action.button(self._button_panel)
        self._panel_sizer.Add(self._export_btn, 0, wx.ALL | wx.EXPAND, BORDER_SIZE)

    def _add_feature_controls(self):
        self._feature_box = wx.StaticBoxSizer(
            wx.VERTICAL,
            self._button_panel,
            "Features",
        )
        self._feature_scroll = wx.ScrolledWindow(
            self._feature_box.GetStaticBox(),
            style=wx.VSCROLL,
        )
        self._feature_scroll.SetScrollRate(0, 10)
        self._feature_sizer = wx.BoxSizer(wx.VERTICAL)
        self._feature_scroll.SetSizer(self._feature_sizer)
        self._feature_checkboxes: list[wx.CheckBox] = []
        self._debug_features_checkbox = self._debug_features_action.checkbox(
            self._feature_box.GetStaticBox()
        )
        self._feature_box.Add(
            self._debug_features_checkbox,
            0,
            wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND,
            BORDER_SIZE,
        )
        self._feature_box.Add(
            self._feature_scroll,
            1,
            wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND,
            BORDER_SIZE,
        )
        self._feature_box.ShowItems(False)
        self._panel_sizer.Add(
            self._feature_box,
            1,
            wx.ALL | wx.EXPAND,
            BORDER_SIZE,
        )

    def _on_module_path_set(self, path: str) -> bool:
        return path != ""

    def _can_be_exported(self, status: LoadStatus) -> bool:
        return (
            status == LoadStatus.COMPLETE and self._controller.current_mesh is not None
        )

    def _add_view_buttons(self):
        for action in [
            self._frame_action,
            self._view_from_xyz_action,
            self._view_from_x_action,
            self._view_from_y_action,
            self._view_from_z_action,
        ]:
            btn = action.button(self._button_panel)
            self._panel_sizer.Add(btn, 0, wx.ALL | wx.EXPAND, BORDER_SIZE)

        chk = self._toggle_grid_action.checkbox(self._button_panel)
        self._panel_sizer.Add(chk, 0, wx.ALL | wx.EXPAND, BORDER_SIZE)

        for rb in self._select_camera_action.radio_buttons(self._button_panel):
            self._panel_sizer.Add(rb, 0, wx.ALL | wx.EXPAND, BORDER_SIZE)

        for action in [
            self._toggle_axes_action,
            self._toggle_edges_action,
            self._toggle_gnonom_action,
        ]:
            chk = action.checkbox(self._button_panel)
            self._panel_sizer.Add(chk, 0, wx.ALL | wx.EXPAND, BORDER_SIZE)

    def _update_feature_controls(self, features: list[FeatureState]):
        self._clear_feature_controls()
        if not features:
            self._feature_box.ShowItems(False)
            self._button_panel.Layout()
            return
        self._feature_box.ShowItems(True)
        for feature in features:
            checkbox = self._create_feature_checkbox(feature)
            self._feature_sizer.Add(
                checkbox,
                0,
                wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND,
                BORDER_SIZE,
            )
            self._feature_checkboxes.append(checkbox)
        self._feature_scroll.Layout()
        self._feature_scroll.FitInside()
        self._button_panel.Layout()

    def _clear_feature_controls(self):
        self._feature_sizer.Clear(delete_windows=True)
        self._feature_checkboxes = []

    def _create_feature_checkbox(self, feature: FeatureState) -> wx.CheckBox:
        checkbox = wx.CheckBox(
            self._feature_scroll,
            label=feature.name,
        )
        checkbox.SetValue(feature.enabled)
        checkbox.Bind(
            wx.EVT_CHECKBOX,
            lambda evt, name=feature.name: self._on_feature_toggle(evt, name),
        )
        return checkbox

    def _on_feature_toggle(self, event: wx.CommandEvent, name: str):
        self._controller.set_feature_enabled(name, event.IsChecked())
        self._loader_timer.Start(LOAD_CHECK_INTERVAL_MS)
        self._load_progress_gauge.Pulse()

    def _on_debug_features_toggle(self, event: wx.Event):
        command_event = cast(wx.CommandEvent, event)
        self._controller.set_debug_features(command_event.IsChecked())
        self._loader_timer.Start(LOAD_CHECK_INTERVAL_MS)
        self._load_progress_gauge.Pulse()

    def _create_file_menu(self) -> wx.Menu:
        file_menu = wx.Menu()
        self._load_action.menu_item(file_menu)
        self._reload_menu_item = self._reload_action.menu_item(file_menu)
        self._export_menu_item = self._export_action.menu_item(file_menu)

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

    def _create_help_menu(self) -> wx.Menu:
        help_menu = wx.Menu()
        self._show_fonts_action.menu_item(help_menu)
        return help_menu

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
                self._load_progress_gauge.Pulse()

    def on_reload(self, _: wx.Event):
        self._controller.reload_mesh()
        self._loader_timer.Start(LOAD_CHECK_INTERVAL_MS)
        self._load_progress_gauge.Pulse()

    def on_load_timer(self, _: wx.Event):
        load_result = self._controller.check_load_queue()
        self._handle_load_result(load_result)

    def _handle_load_result(self, load_result: LoadResult) -> None:
        mesh = load_result.mesh
        if load_result.complete:
            self._loader_timer.Stop()
            self._load_progress_gauge.SetValue(self._load_progress_gauge.GetRange())
        if load_result.error:
            logger.error(load_result.error)
        if self._has_mesh_changed(load_result):
            logger.debug("on_load_time: mesh has changed")
            self._load_mesh_in_view(mesh)
            if self._is_first_in_load(load_result):
                self._gl_widget.frame()
            self._loader_last_load_number = load_result.load_number
            self._loader_last_sequence_number = load_result.sequence_number

    def load_module(self, module_path: Path, *, start_timer: bool = True) -> None:
        self._controller.load_mesh(str(module_path))
        if start_timer:
            self._loader_timer.Start(LOAD_CHECK_INTERVAL_MS)
            self._load_progress_gauge.Pulse()

    def poll_load_status(self) -> LoadStatus:
        load_result = self._controller.check_load_queue()
        self._handle_load_result(load_result)
        if load_result.complete:
            return LoadStatus.COMPLETE
        if load_result.error:
            return LoadStatus.ERROR
        return self._controller.load_status

    def _indicate_load_status(self, status: LoadStatus):
        self._gl_widget.indicate_load_status(status)

    def _has_mesh_changed(self, load_result: LoadResult) -> bool:
        new_load = self._loader_last_load_number != load_result.load_number
        new_sequence = self._loader_last_sequence_number != load_result.sequence_number
        if load_result.mesh is not None:
            return new_load or new_sequence
        return load_result.complete and new_load

    def _load_mesh_in_view(self, mesh: Trimesh | list[Trimesh] | None):
        if mesh is None:
            self._gl_widget.load_mesh([], "loaded mesh")
            return
        self._gl_widget.load_mesh(mesh, "loaded mesh")

    def _is_first_in_load(self, load_result: LoadResult) -> bool:
        return self._loader_last_load_number != load_result.load_number

    def export(self, _: wx.Event):
        default_export_path = self._controller.default_export_path()
        default_export_dir, default_export_file = os.path.split(default_export_path)
        fmts = export_formats()
        wildcard = "|".join([f"{fmt.upper()} (*.{fmt})|*.{fmt}" for fmt in fmts])
        with wx.FileDialog(
            self,
            "Export",
            defaultDir=default_export_dir,
            defaultFile=default_export_file,
            wildcard=wildcard,
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                try:
                    self._controller.export(dlg.GetPath())
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

    def apply_view_state(self, view_state: ViewState) -> None:
        self._gl_widget.show_grid = view_state.grid
        self._gl_widget.show_axes = view_state.axes
        self._gl_widget.show_edges = view_state.edges
        self._gl_widget.show_gnomon = view_state.gnomon
        self._gl_widget.camera_type = view_state.camera
        self._apply_view(view_state.view)

    def capture_client_bitmap(self) -> wx.Bitmap:
        bitmap = self._capture_client_bitmap()
        self._draw_gl_bitmap(bitmap)
        return bitmap

    def _capture_client_bitmap(self) -> wx.Bitmap:
        size = self.GetClientSize()
        bitmap = wx.Bitmap(size.width, size.height)
        dc = wx.MemoryDC(bitmap)
        source_dc = wx.ClientDC(self)
        try:
            dc.Blit(
                0,
                0,
                size.width,
                size.height,
                source_dc,
                0,
                0,
            )
        finally:
            dc.SelectObject(wx.NullBitmap)
        return bitmap

    def _draw_gl_bitmap(self, bitmap: wx.Bitmap) -> None:
        gl_bitmap = self._gl_widget.capture_bitmap()
        gl_position = self._gl_widget.ClientToScreen(wx.Point(0, 0))
        frame_position = self.ClientToScreen(wx.Point(0, 0))
        target_position = gl_position - frame_position
        dc = wx.MemoryDC(bitmap)
        try:
            dc.DrawBitmap(gl_bitmap, target_position.x, target_position.y)
        finally:
            dc.SelectObject(wx.NullBitmap)

    def _apply_view(self, view: str) -> None:
        if view == "frame":
            self._gl_widget.frame()
        elif view == "xyz":
            self._gl_widget.view_from_xyz()
        elif view == "x":
            self._gl_widget.view_from_x()
        elif view == "y":
            self._gl_widget.view_from_y()
        elif view == "z":
            self._gl_widget.view_from_z()

    def on_close(self, _: wx.Event):
        self._loader_timer.Stop()
        del self._controller
        self.Destroy()
