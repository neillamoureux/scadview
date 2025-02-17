from meshsee.gl_widget_adapter import GlWidgetAdapter

from PySide6.QtCore import Qt
from PySide6.QtOpenGLWidgets import QOpenGLWidget

from trimesh import Trimesh


class ModernglWidget(QOpenGLWidget):

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
