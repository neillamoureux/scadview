import logging

from PySide6 import QtGui
from PySide6.QtCore import Qt
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtWidgets import QWidget
from trimesh import Trimesh

from meshsee.render.gl_widget_adapter import GlWidgetAdapter

logger = logging.getLogger(__name__)


class ModernglWidget(QOpenGLWidget):
    def __init__(
        self, gl_widget_adapter: GlWidgetAdapter, parent: QWidget | None = None
    ):
        super().__init__(parent)
        self._gl_widget_adapter = gl_widget_adapter
        self._render_twice = False
        self._last_error_indicator = False

    @property
    def camera_type(self):
        return self._gl_widget_adapter.camera_type

    def toggle_camera(self):
        self._gl_widget_adapter.toggle_camera()
        self.update()

    def paintGL(self):  # override
        self._gl_widget_adapter.render(self.width(), self.height())

    def _double_render_if_needed(self):
        if self._render_twice:
            self._render_twice = False
            self.update()

    def resizeGL(self, width: int, height: int):  # override
        self._gl_widget_adapter.resize(width, height)

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._gl_widget_adapter.start_orbit(
                int(event.position().x()), int(event.position().y())
            )

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._gl_widget_adapter.end_orbit()

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        """
        Rotate the camera based on mouse movement.
        """
        self._gl_widget_adapter.do_orbit(
            int(event.position().x()), int(event.position().y())
        )
        self.update()

    def wheelEvent(self, event: QtGui.QWheelEvent):
        distance = event.angleDelta().y()
        self._gl_widget_adapter.move_to_screen(
            int(event.position().x()), int(event.position().y()), distance
        )
        self.update()

    def keyPressEvent(self, event: QtGui.QKeyEvent):
        key = event.key()
        if key == Qt.Key.Key_W or key == Qt.Key.Key_Up:
            self._gl_widget_adapter.move(1.0)
        elif key == Qt.Key.Key_S or key == Qt.Key.Key_Down:
            self._gl_widget_adapter.move(-1.0)
        elif key == Qt.Key.Key_A or key == Qt.Key.Key_Left:
            self._gl_widget_adapter.move_right(-1.0)
        elif key == Qt.Key.Key_D or key == Qt.Key.Key_Right:
            self._gl_widget_adapter.move_right(1.0)
        elif key == Qt.Key.Key_Q or key == Qt.Key.Key_PageUp:
            self._gl_widget_adapter.move_up(1.0)
        elif key == Qt.Key.Key_E or key == Qt.Key.Key_PageDown:
            self._gl_widget_adapter.move_up(-1.0)
        self.update()

    def view_from_xyz(self):
        self._gl_widget_adapter.view_from_xyz()
        self.update()

    def view_from_x(self):
        self._gl_widget_adapter.view_from_x()
        self.update()

    def view_from_y(self):
        self._gl_widget_adapter.view_from_y()
        self.update()

    def view_from_z(self):
        self._gl_widget_adapter.view_from_z()
        self.update()

    def indicate_load_state(self, state: str):
        # Changing the background color seems to require two renders
        self._gl_widget_adapter.indicate_load_state(state)
        self._render_twice = True
        self.update()

    def frame(self):
        self._gl_widget_adapter.frame()
        self.update()

    def load_mesh(self, mesh: Trimesh | list[Trimesh], name: str):
        self._gl_widget_adapter.load_mesh(mesh, name)
        self.update()

    @property
    def show_grid(self):
        return self._gl_widget_adapter.show_grid

    def toggle_grid(self):
        self._gl_widget_adapter.toggle_grid()
        self.update()

    @property
    def show_edges(self):
        return self._gl_widget_adapter.show_edges

    def toggle_edges(self):
        self._gl_widget_adapter.toggle_edges()
        self.update()

    @property
    def show_gnomon(self):
        return self._gl_widget_adapter.show_gnomon

    def toggle_gnomon(self):
        self._gl_widget_adapter.toggle_gnomon()
        self.update()
