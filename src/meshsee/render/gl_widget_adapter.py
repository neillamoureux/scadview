import logging

import numpy as np
from numpy.typing import NDArray
from trimesh import Trimesh

from meshsee.render.camera import CameraOrthogonal, CameraPerspective
from meshsee.render.renderer import RendererFactory

logger = logging.getLogger(__name__)


class GlWidgetAdapter:
    ORBIT_ROTATION_SPEED = 0.01
    CAMERA_WHEEL_MOVE_FACTOR = 0.0003
    MOVE_STEP = 0.1

    def __init__(self, renderer_factory: RendererFactory):
        self._renderer_factory = renderer_factory
        self._gl_initialized = False
        self._orbiting = False
        self.show_grid = False
        self.show_gnomon = True
        self._camera_type = "perspective"

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

    @property
    def camera_type(self) -> str:
        return self._camera_type

    def toggle_camera(self):
        if self._camera_type == "orthogonal":
            self.use_perspective_camera()
        else:
            self.use_orthogonal_camera()

    def render(self, width: int, height: int):  # override
        if not self._gl_initialized:
            self._init_gl(width, height)
        self._renderer.render(self.show_grid, self.show_gnomon)

    def _init_gl(self, width: int, height: int):
        # You cannot create the context before initializeGL is called
        self._renderer = self._renderer_factory.make((width, height))
        self._gl_initialized = True
        self.resize(width, height)

    def resize(self, width: int, height: int):  # override
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
        self.orbit(angle_from_up, float(rotation_angle))

    def end_orbit(self):
        self._orbiting = False

    def orbit(self, angle_from_up: float, rotation_angle: float):
        self._renderer.orbit(angle_from_up, rotation_angle)

    def move(self, distance: float):
        self._renderer.move(distance * self.MOVE_STEP)

    def move_up(self, distance: float):
        self._renderer.move_up(distance * self.MOVE_STEP)

    def move_right(self, distance: float):
        self._renderer.move_right(distance * self.MOVE_STEP)

    def move_to_screen(self, x: int, y: int, distance: float):
        ndx = x / self._width * 2 - 1
        ndy = 1 - y / self._height * 2
        self._renderer.move_to_screen(
            ndx, ndy, distance * self.CAMERA_WHEEL_MOVE_FACTOR
        )

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

    def load_mesh(self, mesh: Trimesh | list[Trimesh], name: str):
        self._renderer.load_mesh(mesh, name)

    def frame(
        self,
        direction: NDArray[np.float32] | None = None,
        up: NDArray[np.float32] | None = None,
    ):
        self._renderer.frame(direction, up)

    def use_orthogonal_camera(self):
        self._renderer.camera = CameraOrthogonal()
        self._camera_type = "orthogonal"

    def use_perspective_camera(self):
        self._renderer.camera = CameraPerspective()
        self._camera_type = "perspective"
