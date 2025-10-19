import logging

from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLayout,
    QMainWindow,
    QRadioButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from meshsee.controller import Controller, export_formats
from meshsee.ui.font_dialog import FontDialog
from meshsee.ui.mesh_handler import MeshHandler
from meshsee.ui.moderngl_widget import ModernglWidget

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    BUTTON_STRIP_HEIGHT = 40
    UPDATE_MESH_INTERVAL_MS = 100
    FONT_DIALOG_OFFSET = (50, 50)

    def __init__(
        self,
        title: str,
        size: tuple[int, int],
        controller: Controller,
        gl_widget: ModernglWidget,
        add_gl_widget: bool = True,  # Set to False for testing
    ):
        super().__init__()
        self._controller = controller
        self._gl_widget = gl_widget
        self._add_gl_widget = add_gl_widget
        self.setWindowTitle(title)
        self.resize(*size)
        self._create_file_actions()
        self._create_view_actions()
        self._create_help_actions()
        self._create_menu_bar()
        self.font_dialog: FontDialog | None = None
        self._main_layout = self._create_main_layout()
        self._mesh_handler = MeshHandler(
            controller=controller,
            gl_widget=self._gl_widget,
            reload_enable_callback=self._reload_action.setEnabled,
            export_enable_callback=self._export_action.setEnabled,
        )

    def _create_file_actions(self) -> None:
        self._load_action = QAction("&Load .py...", self)
        self._load_action.setToolTip(
            "Load a Python file containing a def create_mesh()..."
        )
        self._load_action.triggered.connect(self.load_file)

        self._reload_action = QAction("&Reload .py", self)
        self._reload_action.setToolTip("Reload the current mesh from the file")
        self._reload_action.triggered.connect(self.reload)
        self._reload_action.setDisabled(True)

        self._export_action = QAction("&Export...", self)
        self._export_action.setToolTip("Export the current mesh to a file")
        self._export_action.triggered.connect(self.export)
        self._export_action.setDisabled(True)

    def _create_view_actions(self) -> None:
        self._frame_action = QAction("Frame", self)
        self._frame_action.triggered.connect(self._gl_widget.frame)
        self._view_from_xyz_action = QAction("View from XYZ", self)
        self._view_from_xyz_action.triggered.connect(self._gl_widget.view_from_xyz)
        self._view_from_x_action = QAction("View from X+", self)
        self._view_from_x_action.triggered.connect(self._gl_widget.view_from_x)
        self._view_from_y_action = QAction("View from Y+", self)
        self._view_from_y_action.triggered.connect(self._gl_widget.view_from_y)
        self._view_from_z_action = QAction("View from Z+", self)
        self._view_from_z_action.triggered.connect(self._gl_widget.view_from_z)

        def update_camera_action(checked: bool):
            if checked:
                logging.debug("Switching to perspective camera")
                self._gl_widget.use_perspective_camera()
            else:
                logging.debug("Switching to orthogonal camera")
                self._gl_widget.use_orthogonal_camera()

        self._toggle_camera_action = QAction("Perspective Camera", self)
        self._toggle_camera_action.setCheckable(True)
        self._toggle_camera_action.toggled.connect(update_camera_action)
        self._toggle_camera_action.setChecked(
            self._gl_widget.camera_type == "perspective"
        )

        self._toggle_grid_action = QAction("Grid", self)
        self._toggle_grid_action.setCheckable(True)
        self._toggle_grid_action.setChecked(self._gl_widget.show_grid)
        self._toggle_grid_action.toggled.connect(self._gl_widget.toggle_grid)

        self._toggle_edges_action = QAction("Edges", self)
        self._toggle_edges_action.setCheckable(True)
        self._toggle_edges_action.setChecked(self._gl_widget.show_edges)
        self._toggle_edges_action.toggled.connect(self._gl_widget.toggle_edges)

        self._toggle_gnomon_action = QAction("Gnomon", self)
        self._toggle_gnomon_action.triggered.connect(self._gl_widget.toggle_gnomon)
        self._toggle_gnomon_action.setCheckable(True)
        self._toggle_gnomon_action.setChecked(self._gl_widget.show_gnomon)

    def _create_help_actions(self) -> None:
        self._show_font_action = QAction("Fonts", self)
        self._show_font_action.triggered.connect(self._open_font_dialog)

    def _open_font_dialog(self):
        if self.font_dialog is None:
            self.font_dialog = FontDialog()
        # Offset dialog from main window
        main_geom = self.geometry()
        offset_x = main_geom.x() + self.FONT_DIALOG_OFFSET[0]
        offset_y = main_geom.y() + self.FONT_DIALOG_OFFSET[1]
        self.font_dialog.move(offset_x, offset_y)
        self.font_dialog.show()
        self.font_dialog.raise_()  # bring it to front
        self.font_dialog.activateWindow()

    def _create_menu_bar(self) -> None:
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")
        file_menu.addAction(self._load_action)
        file_menu.addAction(self._reload_action)
        file_menu.addAction(self._export_action)

        view_menu = menu_bar.addMenu("&View")
        view_menu.addAction(self._frame_action)
        view_menu.addAction(self._view_from_xyz_action)
        view_menu.addAction(self._view_from_x_action)
        view_menu.addAction(self._view_from_y_action)
        view_menu.addAction(self._view_from_z_action)
        view_menu.addAction(self._toggle_camera_action)
        view_menu.addAction(self._toggle_grid_action)
        view_menu.addAction(self._toggle_edges_action)

        help_menu = menu_bar.addMenu("Help")
        help_menu.addAction(self._show_font_action)
        self._help_menu = help_menu
        # help_menu.addAction("About", self._controller.show_about_dialog)
        # help_menu.addAction("Documentation", self._controller.open_documentation)

    def _create_main_layout(self) -> QVBoxLayout:
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        if self._add_gl_widget:
            main_layout.addWidget(self._gl_widget)
        file_buttons = self._create_file_buttons()
        main_layout.addWidget(file_buttons)
        camera_buttons = self._create_view_buttons()
        main_layout.addWidget(camera_buttons)
        # self._init_buttons_state()
        return main_layout

    def _create_file_buttons(self) -> QWidget:
        file_button_strip = QWidget()
        file_button_layout = QHBoxLayout()
        file_button_strip.setLayout(file_button_layout)
        file_button_strip.setFixedHeight(self.BUTTON_STRIP_HEIGHT)

        self._load_file_btn = self._add_button(file_button_layout, self._load_action)
        self._reload_file_btn = self._add_button(
            file_button_layout, self._reload_action
        )
        self._export_btn = self._add_button(file_button_layout, self._export_action)
        return file_button_strip

    def _create_view_buttons(self) -> QWidget:
        view_button_strip = QWidget()
        view_button_layout = QHBoxLayout()
        view_button_strip.setLayout(view_button_layout)
        view_button_strip.setFixedHeight(
            self.BUTTON_STRIP_HEIGHT
        )  # Set fixed height for the button strip

        self._frame_btn = self._add_button(view_button_layout, self._frame_action)
        self._view_from_xyz_btn = self._add_button(
            view_button_layout, self._view_from_xyz_action
        )
        self._view_from_x_btn = self._add_button(
            view_button_layout, self._view_from_x_action
        )
        self._view_from_y_btn = self._add_button(
            view_button_layout, self._view_from_y_action
        )
        self._view_from_z_btn = self._add_button(
            view_button_layout, self._view_from_z_action
        )
        self._perspective_camera_radio, self._orthogonal_camera_radio = (
            self._add_radio_buttons(
                view_button_layout,
                self._toggle_camera_action,
                ["Perspective", "Orthogonal"],
            )
        )
        self._toggle_grid_btn = self._add_checkbox(
            view_button_layout, self._toggle_grid_action
        )
        self._toggle_edges_btn = self._add_checkbox(
            view_button_layout, self._toggle_edges_action
        )
        self._toggle_gnomon_btn = self._add_checkbox(
            view_button_layout, self._toggle_gnomon_action
        )

        return view_button_strip

    def _add_button(self, layout: QLayout, action: QAction) -> QToolButton:
        """
        Helper method to add a button with an action to a layout.
        """
        button = QToolButton()
        button.setDefaultAction(action)
        layout.addWidget(button)
        return button

    def _add_checkbox(self, layout: QLayout, action: QAction) -> QCheckBox:
        """
        Helper method to add a button with an action to a layout.
        """
        cb = QCheckBox(action.text())
        cb.setChecked(action.isChecked())
        action.toggled.connect(cb.setChecked)
        cb.toggled.connect(action.setChecked)
        layout.addWidget(cb)
        return cb

    def _add_radio_buttons(
        self, layout: QLayout, action: QAction, texts: list[str]
    ) -> tuple[QRadioButton, QRadioButton]:
        """
        Helper method to add a button with an action to a layout.
        """
        rb_0 = QRadioButton(texts[0])
        rb_1 = QRadioButton(texts[1])

        rb_0.setChecked(action.isChecked())

        def update_radio(checked: bool):
            logging.debug(f"Radio button updated: {checked}")
            if checked:
                rb_0.setChecked(checked)
            else:
                rb_1.setChecked(not checked)

        action.toggled.connect(update_radio)
        rb_0.toggled.connect(action.setChecked)

        layout.addWidget(rb_0)
        layout.addWidget(rb_1)
        return rb_0, rb_1

    def load_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open File", "", "Python Files (*.py)"
        )
        if file_path == "":
            return
        self._load_mesh(file_path)

    def reload(self):
        self._load_mesh(None)

    def _load_mesh(self, file_path: str | None):
        self._mesh_handler.load_mesh(file_path)

    def export(self):
        default_export_path = self._controller.default_export_path()
        filt = ";;".join([f"{fmt.upper()} (*.{fmt})" for fmt in export_formats()])
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export File", dir=default_export_path, filter=filt
        )
        if file_path:
            self._controller.export(file_path)
