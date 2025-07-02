import logging

from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from meshsee.controller import Controller, export_formats
from meshsee.ui.mesh_handler import MeshHandler
from meshsee.ui.moderngl_widget import ModernglWidget

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    BUTTON_STRIP_HEIGHT = 50
    UPDATE_MESH_INTERVAL_MS = 100

    def __init__(
        self,
        title: str,
        size: tuple[int, int],
        controller: Controller,
        gl_widget: ModernglWidget,
    ):
        super().__init__()
        self._controller = controller
        self._gl_widget = gl_widget
        self.setWindowTitle(title)
        self.resize(*size)
        self._main_layout = self._create_main_layout()
        self._mesh_handler = MeshHandler(
            controller=controller,
            gl_widget=self._gl_widget,
            reload_file_btn=self._reload_file_btn,
            export_btn=self._export_btn,
        )

    def _create_main_layout(self) -> QVBoxLayout:
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.addWidget(self._gl_widget)
        file_buttons = self._create_file_buttons()
        main_layout.addWidget(file_buttons)
        camera_buttons = self._create_camera_buttons()
        main_layout.addWidget(camera_buttons)
        return main_layout

    def _create_file_buttons(self) -> QWidget:
        file_button_strip = QWidget()
        file_button_layout = QHBoxLayout()
        file_button_strip.setLayout(file_button_layout)
        file_button_strip.setFixedHeight(self.BUTTON_STRIP_HEIGHT)

        load_file_btn = QPushButton("Load .py")
        load_file_btn.clicked.connect(self.load_file)
        file_button_layout.addWidget(load_file_btn)

        self._reload_file_btn = QPushButton("Reload .py")
        self._reload_file_btn.setDisabled(True)
        self._reload_file_btn.clicked.connect(self.reload)
        file_button_layout.addWidget(self._reload_file_btn)

        self._export_btn = QPushButton("Export")
        self._export_btn.setDisabled(True)
        self._export_btn.clicked.connect(self.export)
        file_button_layout.addWidget(self._export_btn)

        return file_button_strip

    def _create_camera_buttons(self) -> QWidget:
        camera_button_strip = QWidget()
        camera_button_layout = QHBoxLayout()
        camera_button_strip.setLayout(camera_button_layout)
        camera_button_strip.setFixedHeight(
            self.BUTTON_STRIP_HEIGHT
        )  # Set fixed height for the button strip

        # Add buttons to the button layout
        frame_btn = QPushButton("Frame")
        frame_btn.clicked.connect(self._gl_widget.frame)
        camera_button_layout.addWidget(frame_btn)

        view_from_xyz_btn = QPushButton("View from XYZ")
        view_from_xyz_btn.clicked.connect(self._gl_widget.view_from_xyz)
        camera_button_layout.addWidget(view_from_xyz_btn)

        view_from_x_btn = QPushButton("View from X+")
        view_from_x_btn.clicked.connect(self._gl_widget.view_from_x)
        camera_button_layout.addWidget(view_from_x_btn)

        view_from_y_btn = QPushButton("View from Y+")
        view_from_y_btn.clicked.connect(self._gl_widget.view_from_y)
        camera_button_layout.addWidget(view_from_y_btn)

        view_from_z_btn = QPushButton("View from Z+")
        view_from_z_btn.clicked.connect(self._gl_widget.view_from_z)
        camera_button_layout.addWidget(view_from_z_btn)

        orthogonal_camera_btn = QPushButton("Ortho")
        orthogonal_camera_btn.clicked.connect(self._gl_widget.use_orthogonal_camera)
        camera_button_layout.addWidget(orthogonal_camera_btn)

        perspective_camera_btn = QPushButton("Persp")
        perspective_camera_btn.clicked.connect(self._gl_widget.use_perspective_camera)
        camera_button_layout.addWidget(perspective_camera_btn)

        grid_btn = QPushButton("Grid")
        grid_btn.setCheckable(True)
        grid_btn.setChecked(self._gl_widget.show_grid)
        grid_btn.clicked.connect(self._gl_widget.toggle_grid)
        camera_button_layout.addWidget(grid_btn)

        grid_btn = QPushButton("Gnomon")
        grid_btn.setCheckable(True)
        grid_btn.setChecked(self._gl_widget.show_gnomon)
        grid_btn.clicked.connect(self._gl_widget.toggle_gnomon)
        camera_button_layout.addWidget(grid_btn)

        return camera_button_strip

    def load_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open File", "", "Python Files (*.py)"
        )
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
