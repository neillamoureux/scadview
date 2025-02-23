from meshsee.gl_widget_adapter import GlWidgetAdapter

from PySide6.QtCore import Qt
from PySide6.QtOpenGLWidgets import QOpenGLWidget

from trimesh import Trimesh


class ModernglWidget(QOpenGLWidget):
    CAMERA_MOVE_FACTOR = 0.1
    MOVE_STEP = 10.0

    def __init__(self, gl_widget_adapter: GlWidgetAdapter, parent=None):
        super().__init__(parent)
        self._gl_widget_adapter = gl_widget_adapter
        self._gl_initialized = False

    def initializeGL(self):  # override
        self._gl_widget_adapter.init_gl(self.width(), self.height())
        self._gl_initialized = True

    def paintGL(self):  # override
        self._gl_widget_adapter.render()

    def resizeGL(self, width, height):  # override
        self._gl_widget_adapter.resize(width, height)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._gl_widget_adapter.start_orbit(
                event.position().x(), event.position().y()
            )

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._gl_widget_adapter.end_orbit()

    def mouseMoveEvent(self, event):
        """
        Rotate the camera based on mouse movement.
        """
        self._gl_widget_adapter.do_orbit(event.position().x(), event.position().y())
        self.update()
    
    def wheelEvent(self, event):
        self._gl_widget_adapter.move(event.angleDelta().y() * self.CAMERA_MOVE_FACTOR)
        self.update()

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_W:
            self._gl_widget_adapter.move(self.MOVE_STEP)
        elif key == Qt.Key_S:
            self._gl_widget_adapter.move(-self.MOVE_STEP)
        elif key == Qt.Key_A:
            self._gl_widget_adapter.move_right(-self.MOVE_STEP)
        elif key == Qt.Key_D:
            self._gl_widget_adapter.move_right(self.MOVE_STEP)
        elif key == Qt.Key_Q:
            self._gl_widget_adapter.move_up(self.MOVE_STEP)
        elif key == Qt.Key_E:
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

    def load_mesh(self, mesh: Trimesh):
        self._gl_widget_adapter.load_mesh(mesh)
        self.update()

    
