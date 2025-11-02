import logging

import numpy as np
from numpy.typing import NDArray
from trimesh import Trimesh

from meshsee.load_status import LoadStatus
from meshsee.observable import Observable
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
        self.on_axes_change = Observable()
        self.show_axes = True
        self.on_grid_change = Observable()
        self.show_grid = False
        self.on_edges_change = Observable()
        self.show_edges = False
        self.on_gnomon_change = Observable()
        self.show_gnomon = True
        self.on_camera_change = Observable()
        self._camera_type = "perspective"

    @property
    def show_axes(self) -> bool:
        return self._show_axes

    @show_axes.setter
    def show_axes(self, show_axes: bool):
        self._show_axes = show_axes
        self.on_axes_change.notify(show_axes)

    def toggle_axes(self):
        self.show_axes = not self.show_axes

    @property
    def show_grid(self) -> bool:
        return self._show_grid

    @show_grid.setter
    def show_grid(self, show_grid: bool):
        self._show_grid = show_grid
        self.on_grid_change.notify(show_grid)

    def toggle_grid(self):
        self.show_grid = not self.show_grid

    @property
    def show_edges(self) -> bool:
        return self._show_edges

    @show_edges.setter
    def show_edges(self, show_edges: bool):
        self._show_edges = show_edges
        self.on_edges_change.notify(show_edges)

    def toggle_edges(self):
        self.show_edges = not self.show_edges

    @property
    def show_gnomon(self) -> bool:
        return self._show_gnomon

    @show_gnomon.setter
    def show_gnomon(self, show_gnomon: bool):
        self._show_gnomon = show_gnomon
        self.on_gnomon_change.notify(show_gnomon)

    def toggle_gnomon(self):
        self.show_gnomon = not self.show_gnomon

    @property
    def camera_type(self) -> str:
        return self._camera_type

    @camera_type.setter
    def camera_type(self, value: str):
        if self.camera_type != value:
            if value == "perspective":
                self.use_perspective_camera()
            elif value == "orthogonal":
                self.use_orthogonal_camera()

    def toggle_camera(self):
        if self._camera_type == "orthogonal":
            self.use_perspective_camera()
        else:
            self.use_orthogonal_camera()

    def render(self, width: int, height: int):  # override
        if not self._gl_initialized:
            self._init_gl(width, height)
        self._renderer.render(
            self.show_grid, self.show_edges, self.show_gnomon, self.show_axes
        )

    def _init_gl(self, width: int, height: int):
        # You cannot create the context before initializeGL is called
        self._renderer = self._renderer_factory.make((width, height))
        self._gl_initialized = True
        if self._camera_type == "orthogonal":
            self.use_orthogonal_camera()
        else:
            self.use_perspective_camera()
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

    def indicate_load_status(self, status: LoadStatus):
        self._renderer.indicate_load_status(status)

    def load_mesh(self, mesh: Trimesh | list[Trimesh], name: str):
        self._renderer.load_mesh(mesh, name)

    def frame(
        self,
        direction: NDArray[np.float32] | None = None,
        up: NDArray[np.float32] | None = None,
    ):
        self._renderer.frame(direction, up)

    def use_orthogonal_camera(self):
        if self._gl_initialized:
            self._renderer.camera = CameraOrthogonal()
        self._camera_type = "orthogonal"
        self.on_camera_change.notify(self._camera_type)

    def use_perspective_camera(self):
        if self._gl_initialized:
            self._renderer.camera = CameraPerspective()
        self._camera_type = "perspective"
        self.on_camera_change.notify(self._camera_type)
