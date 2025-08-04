from typing import Any

import moderngl
import numpy as np
from pyrr import Matrix44
from trimesh import Trimesh
from trimesh.creation import box

from meshsee.render.camera import Camera, copy_camera_state
from meshsee.render.label_atlas import LabelAtlas

from meshsee.observable import Observable
from meshsee.render.shader_program import ShaderProgram, ShaderVar
from meshsee.render.label_renderee import (
    LabelSetRenderee,
)
from meshsee.render.renderee import GnomonRenderee
from meshsee.render.trimesh_renderee import (
    create_trimesh_renderee,
    TrimeshListRenderee,
    TrimeshOpaqueRenderee,
)
import logging

logger = logging.getLogger(__name__)

AXIS_LENGTH = 10000.0
AXIS_WIDTH = 1.0
AXIS_DEPTH = 1.0
AXIS_SCALE_FACTOR = 0.005
MESH_COLOR = np.array([0.5, 0.5, 0.5, 1.0], "f4")
MAX_LABEL_FRAC_OF_STEP = 0.5
MAX_LABELS_PER_AXIS = 20
PER_NUMBER_FRAC_OF_AXIS = 0.04


def _make_default_mesh() -> Trimesh:
    return box([1.0, 1.0, 1.0])


def _make_base_axes() -> Trimesh:
    return (
        box([AXIS_LENGTH, AXIS_DEPTH, AXIS_WIDTH])
        .union(box([AXIS_LENGTH, AXIS_WIDTH, AXIS_DEPTH]))
        .union(box([AXIS_WIDTH, AXIS_LENGTH, AXIS_DEPTH]))
        .union(box([AXIS_DEPTH, AXIS_LENGTH, AXIS_WIDTH]))
        .union(box([AXIS_DEPTH, AXIS_WIDTH, AXIS_LENGTH]))
        .union(box([AXIS_WIDTH, AXIS_DEPTH, AXIS_LENGTH]))
    )


def _scale_axes(base_axes: Trimesh, scale: float) -> Trimesh:
    """
    Scale the axes by the given scale factor.
    """
    axes = base_axes.copy()
    axes.apply_scale(scale)
    return axes


class Renderer:
    DEFAULT_BACKGROUND_COLOR = (0.552, 0.770, 0.770, 1.0)  # cyan
    LOADING_BACKGROUND_COLOR = (0.741, 0.781, 0.996, 1.0)  # blue
    SUCCESS_BACKGROUND_COLOR = (0.720, 0.964, 0.720, 1.0)  # green
    DEBUG_BACKGROUND_COLOR = (0.980, 0.980, 0.690, 1.0)  # yellow
    ERROR_BACKGROUND_COLOR = (0.976, 0.765, 0.765, 1.0)  #  red

    def __init__(
        self,
        context: moderngl.Context,
        camera: Camera,
        window_size: tuple[int, int],
    ):
        self._window_size = window_size
        # self._aspect_ratio = aspect_rati
        self._ctx = context
        self._create_shaders()
        self.camera = camera
        self._init_shaders()
        self._scale = 1.0
        self._create_renderees()
        self._clear_background = True
        self._last_background_color = self.ERROR_BACKGROUND_COLOR
        self.background_color = self.DEFAULT_BACKGROUND_COLOR
        self.load_mesh(_make_default_mesh(), "default_mesh")
        self.frame()

    def _create_shaders(self):
        self.on_program_value_change = Observable()
        self._main_prog = self._create_main_shader_program(self.on_program_value_change)
        self._num_prog = self._create_num_shader_program(self.on_program_value_change)
        self._axis_prog = self._create_axis_shader_program(self.on_program_value_change)
        self._gnomon_prog = self._create_gnomon_shader_program(
            self.on_program_value_change
        )

    def _create_renderees(self):
        self._base_axes = _make_base_axes()
        self._axes_renderee = self._create_axes_renderee()
        self._label_atlas = LabelAtlas(self._ctx)
        self._label_set_renderee = LabelSetRenderee(
            self._ctx,
            self._num_prog.program,
            self._label_atlas,
            MAX_LABELS_PER_AXIS,
            MAX_LABEL_FRAC_OF_STEP,
            self._camera,
            name="label_set",
        )
        self._gnomon_renderee = GnomonRenderee(
            self._ctx, self._gnomon_prog.program, self.window_size, name="gnomon"
        )

    def _create_axes_renderee(self) -> TrimeshOpaqueRenderee:
        axes = _scale_axes(self._base_axes, self._scale * AXIS_SCALE_FACTOR)
        axes_renderee = TrimeshOpaqueRenderee(
            self._ctx, self._axis_prog.program, axes, cull_back_face=True, name="axes"
        )
        axes_renderee.subscribe_to_updates(self.on_program_value_change)
        return axes_renderee

    @property
    def scale(self):
        return self._scale

    @scale.setter
    def scale(self, value):
        if self.scale != value:
            self._scale = value
            self._axes_renderee = self._create_axes_renderee()
            self._label_set_renderee.shift_up = value * AXIS_SCALE_FACTOR / 2.0

    @property
    def camera(self):
        return self._camera

    @camera.setter
    def camera(self, camera: Camera):
        old_camera = None
        if hasattr(self, "_camera"):
            if self._camera == camera:
                return
            old_camera = self._camera
        camera.on_program_value_change.subscribe(self._update_program_value)
        if old_camera is not None:
            old_camera.on_program_value_change.unsubscribe(self._update_program_value)
            copy_camera_state(old_camera, camera)
            self._label_set_renderee.camera = camera
        self._camera = camera

    def _init_shaders(self):
        self._m_model = np.array(Matrix44.identity(), dtype="f4")
        self.show_grid = True
        self._update_program_value(ShaderVar.MODEL_MATRIX, self._m_model)
        self._update_program_value(ShaderVar.MESH_COLOR, MESH_COLOR)

    @property
    def background_color(self):
        return self._background_color

    @background_color.setter
    def background_color(self, color: tuple[float, float, float, float]):
        self._background_color = color
        if self._last_background_color != self._background_color:
            logger.debug("Background color changed)")
            self._clear_background = True
        self._last_background_color = self._background_color

    @property
    def aspect_ratio(self) -> float:
        return float(self._window_size[0]) / self._window_size[1]

    @property
    def window_size(self) -> tuple[int, int]:
        return self._window_size

    @window_size.setter
    def window_size(self, value: tuple[int, int]):
        self._window_size = value
        self._ctx.viewport = (0, 0, value[0], value[1])
        if self._camera is not None:
            self._camera.aspect_ratio = self.aspect_ratio
        self._gnomon_renderee.window_size = value

    @property
    def show_grid(self):
        return self._show_grid

    @show_grid.setter
    def show_grid(self, value: bool):
        self._show_grid = value
        self._update_program_value(ShaderVar.SHOW_GRID, value)

    def _update_program_value(self, t: ShaderVar, value: Any):
        self.on_program_value_change.notify(t, value)

    def _create_main_shader_program(self, observable: Observable) -> ShaderProgram:
        program_vars = {
            ShaderVar.MODEL_MATRIX: "m_model",
            ShaderVar.VIEW_MATRIX: "m_camera",
            ShaderVar.PROJECTION_MATRIX: "m_proj",
            ShaderVar.SHOW_GRID: "show_grid",
        }
        return self._create_shader_program(
            "main_vertex.glsl", "main_fragment.glsl", program_vars, observable
        )

    def _create_axis_shader_program(self, observable: Observable) -> ShaderProgram:
        program_vars = {
            ShaderVar.MODEL_MATRIX: "m_model",
            ShaderVar.VIEW_MATRIX: "m_camera",
            ShaderVar.PROJECTION_MATRIX: "m_proj",
            ShaderVar.SHOW_GRID: "show_grid",
        }
        return self._create_shader_program(
            "main_vertex.glsl", "main_fragment.glsl", program_vars, observable
        )

    def _create_gnomon_shader_program(self, observable: Observable) -> ShaderProgram:
        program_vars = {
            ShaderVar.MODEL_MATRIX: "m_model",
            ShaderVar.GNOMON_VIEW_MATRIX: "m_camera",
            ShaderVar.GNOMON_PROJECTION_MATRIX: "m_proj",
        }
        return self._create_shader_program(
            "gnomon_vertex.glsl", "gnomon_fragment.glsl", program_vars, observable
        )

    def _create_shader_program(
        self,
        vertex_shader_loc: str,
        fragment_shader_loc: str,
        register: dict[ShaderVar, str],
        observable: Observable,
    ) -> ShaderProgram:
        prog = ShaderProgram(
            self._ctx, vertex_shader_loc, fragment_shader_loc, register
        )
        prog.subscribe_to_updates(observable)
        return prog

    def _create_num_shader_program(self, observable: Observable) -> ShaderProgram:
        program_vars = {
            ShaderVar.MODEL_MATRIX: "m_model",
            ShaderVar.VIEW_MATRIX: "m_camera",
            ShaderVar.PROJECTION_MATRIX: "m_proj",
        }
        return self._create_shader_program(
            "label_vertex.glsl", "label_fragment.glsl", program_vars, observable
        )

    def indicate_load_state(self, state: str):
        if state == "loading":
            self.background_color = self.LOADING_BACKGROUND_COLOR
            self._main_renderee = create_trimesh_renderee(
                self._ctx,
                self._main_prog.program,
                _make_default_mesh(),
                self._m_model,
                self._camera.view_matrix,
                name="loading",
            )
        elif state == "success":
            if isinstance(self._main_renderee, TrimeshListRenderee):
                self.background_color = self.DEBUG_BACKGROUND_COLOR
            else:
                self.background_color = self.SUCCESS_BACKGROUND_COLOR
        elif state == "error":
            self.background_color = self.ERROR_BACKGROUND_COLOR
        else:
            self.background_color = self.DEFAULT_BACKGROUND_COLOR

    def load_mesh(self, mesh: Trimesh | list[Trimesh], name: str = "Unknown load_mesh"):
        logger.debug("load_mesh started")
        self._main_renderee = create_trimesh_renderee(
            self._ctx,
            self._main_prog.program,
            mesh,
            self._m_model,
            self._camera.view_matrix,
            name=name,
        )
        if isinstance(mesh, list):
            self.scale = max([m.scale for m in mesh])
        else:
            self.scale = mesh.scale
        self._main_renderee.subscribe_to_updates(self.on_program_value_change)
        self._framing_points = self._main_renderee.points
        logger.debug("load_mesh_finished")

    def frame(self, direction=None, up=None):
        self._camera.frame(self._framing_points, direction, up)

    def orbit(self, angle_from_up, rotation_angle):
        self._camera.orbit(angle_from_up, rotation_angle)

    def move(self, distance):
        self._camera.move(distance)

    def move_up(self, distance):
        self._camera.move_up(distance)

    def move_right(self, distance):
        self._camera.move_right(distance)

    def move_to_screen(self, ndx: float, ndy: float, distance: float):
        """
        Move the camera to the normalized screen position (ndx, ndy) and move it by distance.
        """
        self._camera.move_to_screen(ndx, ndy, distance)

    def render(self, show_grid: bool, show_gnomon: bool):  # override
        self._ctx.clear(*self._background_color, depth=1.0)
        self._ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)
        self.show_grid = True
        self._ctx.enable(moderngl.DEPTH_TEST)
        self._axes_renderee.render()
        self.show_grid = show_grid
        self._main_renderee.render()
        self._label_set_renderee.render()
        if show_gnomon:
            self._gnomon_renderee.render()


class RendererFactory:
    def __init__(self, camera: Camera):
        self._camera = camera

    def make(self, window_size: tuple[int, int]) -> Renderer:
        ctx = moderngl.create_context()
        return Renderer(ctx, self._camera, window_size)
