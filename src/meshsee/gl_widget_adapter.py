import numpy as np

from meshsee.renderer import RendererFactory


class GlWidgetAdapter:
    ORBIT_ROTATION_SPEED = 0.01

    def __init__(self, renderer_factory: RendererFactory):
        self._renderer_factory = renderer_factory
        self._gl_initialized = False
        self._orbiting = False
        self.show_grid = True

    @property
    def show_grid(self):
        return self._show_grid

    @show_grid.setter
    def show_grid(self, show_grid: bool):
        self._show_grid = show_grid

    def toggle_grid(self):
        self.show_grid = not self.show_grid

    def init_gl(self, width: int, height: int):
        self.resize(width, height)
        # You cannot create the context before initializeGL is called
        self._renderer = self._renderer_factory.make(width / height)
        self._gl_initialized = True

    def render(self):  # override
        self._renderer.render(self.show_grid)

    def resize(self, width, height):  # override
        self._width = width
        self._height = height
        if self._gl_initialized:
            self._renderer.aspect_ratio = width / height

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
        direction = np.array([-1, -1, -1])
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

    def load_mesh(self, mesh):
        self._renderer.load_mesh(mesh)

    def frame(self, direction=None, up=None):
        self._renderer.frame(direction, up)
