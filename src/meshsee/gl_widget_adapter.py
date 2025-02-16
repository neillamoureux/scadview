import numpy as np

from meshsee.renderer import RendererFactory


class GlWidgetAdapter:
    ORBIT_ROTATION_SPEED = 0.01

    def __init__(self, renderer_factory: RendererFactory):
        self._renderer_factory = renderer_factory
        self._gl_initialized = False
        self._orbiting = False

    def init_gl(self, width: int, height: int):
        aspect_ratio = width / height
        # You cannot create the context before initializeGL is called
        self._renderer = self._renderer_factory.make(aspect_ratio)
        self._gl_initialized = True

    def render(self):  # override
        self._renderer.render()

    def resize(self, width, height):  # override
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

    def view_from_xyz(self):
        direction = np.array([-1, -1, -1])
        up = np.array([0, 0, 1])
        self._renderer.frame(direction, up)
