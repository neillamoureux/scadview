from meshsee.render.gl_widget_adapter import GlWidgetAdapter

from PySide6.QtCore import Qt
from PySide6.QtOpenGLWidgets import QOpenGLWidget

from trimesh import Trimesh


class ModernglWidget(QOpenGLWidget):
    CAMERA_MOVE_FACTOR = 0.1
    MOVE_STEP = 10.0

    def __init__(self, gl_widget_adapter: GlWidgetAdapter, parent=None):
        super().__init__(parent)
        self._gl_widget_adapter = gl_widget_adapter
        self._render_twice = False
        self._last_error_indicator = False

    def paintGL(self):  # override
        self._gl_widget_adapter.render(self.width(), self.height())

    def _double_render_if_needed(self):
        if self._render_twice:
            self._render_twice = False
            self.update()

    def resizeGL(self, width, height):  # override
        self._gl_widget_adapter.resize(width, height)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._gl_widget_adapter.start_orbit(
                event.position().x(), event.position().y()
            )

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._gl_widget_adapter.end_orbit()

    def mouseMoveEvent(self, event):
        """
        Rotate the camera based on mouse movement.
        """
        self._gl_widget_adapter.do_orbit(event.position().x(), event.position().y())
        self.update()

    def wheelEvent(self, event):
        distance = event.angleDelta().y() * self.CAMERA_MOVE_FACTOR
        self._gl_widget_adapter.move_to_screen(
            event.position().x(), event.position().y(), distance
        )
        self.update()

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key.Key_W or key == Qt.Key.Key_Up:
            self._gl_widget_adapter.move(self.MOVE_STEP)
        elif key == Qt.Key.Key_S or key == Qt.Key.Key_Down:
            self._gl_widget_adapter.move(-self.MOVE_STEP)
        elif key == Qt.Key.Key_A or key == Qt.Key.Key_Left:
            self._gl_widget_adapter.move_right(-self.MOVE_STEP)
        elif key == Qt.Key.Key_D or key == Qt.Key.Key_Right:
            self._gl_widget_adapter.move_right(self.MOVE_STEP)
        elif key == Qt.Key.Key_Q or key == Qt.Key.Key_PageUp:
            self._gl_widget_adapter.move_up(self.MOVE_STEP)
        elif key == Qt.Key.Key_E or key == Qt.Key.Key_PageDown:
            self._gl_widget_adapter.move_up(-self.MOVE_STEP)
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

    def load_mesh(self, mesh: Trimesh, name: str):
        self._gl_widget_adapter.load_mesh(mesh, name)
        self.update()

    @property
    def show_grid(self):
        return self._gl_widget_adapter.show_grid

    def toggle_grid(self):
        self._gl_widget_adapter.toggle_grid()
        self.update()

    @property
    def show_gnomon(self):
        return self._gl_widget_adapter.show_gnomon

    def toggle_gnomon(self):
        self._gl_widget_adapter.toggle_gnomon()
        self.update()

    def use_perspective_camera(self):
        self._gl_widget_adapter.use_perspective_camera()
        self.update()

    def use_orthogonal_camera(self):
        self._gl_widget_adapter.use_orthogonal_camera()
        self.update()
