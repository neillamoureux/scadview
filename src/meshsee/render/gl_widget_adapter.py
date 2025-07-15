import logging
import numpy as np


from meshsee.render.renderer import RendererFactory
from meshsee.render.camera import CameraPerspective, CameraOrthogonal

logger = logging.getLogger(__name__)

class GlWidgetAdapter:
    ORBIT_ROTATION_SPEED = 0.01

    def __init__(self, renderer_factory: RendererFactory):
        self._renderer_factory = renderer_factory
        self._gl_initialized = False
        self._orbiting = False
        self.show_grid = False
        self.show_gnomon = True
        self._current_fbo = -1

    @property
    def show_grid(self) -> bool:
        return self._show_grid

    @show_grid.setter
    def show_grid(self, show_grid: bool):
        self._show_grid = show_grid

    def toggle_grid(self):
        self.show_grid = not self.show_grid

    @property
    def show_gnomon(self) -> bool:
        return self._show_gnomon

    @show_gnomon.setter
    def show_gnomon(self, show_gnomon: bool):
        self._show_gnomon = show_gnomon

    def toggle_gnomon(self):
        self.show_gnomon = not self.show_gnomon

    def init_gl(self, width: int, height: int, current_fbo: int):
        self.resize(width, height)
        # You cannot create the context before initializeGL is called
        self._renderer = self._renderer_factory.make((width, height))
        self._gl_initialized = True
        self._current_fbo = current_fbo

    def _reinit_gl_if_needed(self, width: int, height: int, current_fbo: int):
        if current_fbo != self._renderer._ctx.fbo.glo:
            logger.debug(f"Framebuffer has changed from {self._renderer._ctx.fbo.glo} to {current_fbo}")
            self._gl_initialized = False
            self.init_gl(width, height, current_fbo)
            logger.debug(f"Framebuffer after init_gl: {self._renderer._ctx.fbo.glo}")

    def render(self, width: int, height: int, current_fbo: int):  # override
        self._reinit_gl_if_needed(width, height, current_fbo)
        self._renderer.render(self.show_grid, self.show_gnomon)

    def resize(self, width, height):  # override
        self._width = width
        self._height = height
        if self._gl_initialized:
            self._renderer.window_size = (width, height)

    def start_orbit(self, x: int, y: int):
        self._orbiting = True
        self._last_x = x
        self._last_y = y

    def do_orbit(self, x: int, y: int):
        if not self._orbiting:
            return
        dx = x - self._last_x
        dy = y - self._last_y
        self._last_x = x
        self._last_y = y
        angle_from_up = np.arctan2(dy, dx) + np.pi / 2.0
        rotation_angle = np.linalg.norm([dx, dy]) * self.ORBIT_ROTATION_SPEED
        self.orbit(angle_from_up, rotation_angle)

    def end_orbit(self):
        self._orbiting = False

    def orbit(self, angle_from_up, rotation_angle):
        self._renderer.orbit(angle_from_up, rotation_angle)

    def move(self, distance):
        self._renderer.move(distance)

    def move_up(self, distance):
        self._renderer.move_up(distance)

    def move_right(self, distance):
        self._renderer.move_right(distance)

    def move_along(self, vector):
        self._renderer.move_along(vector)

    def move_to_screen(self, x: int, y: int, distance: float):
        ndx = x / self._width * 2 - 1
        ndy = 1 - y / self._height * 2
        self._renderer.move_to_screen(ndx, ndy, distance)

    def view_from_xyz(self):
        direction = np.array([-1, 1, -1])
        up = np.array([0, 0, 1])
        self._renderer.frame(direction, up)

    def view_from_x(self):
        direction = np.array([-1, 0, 0])
        up = np.array([0, 0, 1])
        self._renderer.frame(direction, up)

    def view_from_y(self):
        direction = np.array([0, -1, 0])
        up = np.array([0, 0, 1])
        self._renderer.frame(direction, up)

    def view_from_z(self):
        direction = np.array([0, 0, -1])
        up = np.array([0, 1, 0])
        self._renderer.frame(direction, up)

    def indicate_load_state(self, state: str):
        self._renderer.indicate_load_state(state)

    def load_mesh(self, mesh, name: str):
        self._renderer.load_mesh(mesh, name)

    def frame(self, direction=None, up=None):
        self._renderer.frame(direction, up)

    def use_orthogonal_camera(self):
        self._renderer.camera = CameraOrthogonal()

    def use_perspective_camera(self):
        self._renderer.camera = CameraPerspective()
