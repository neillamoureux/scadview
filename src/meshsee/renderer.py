from typing import Any, Callable
from importlib.resources import as_file, files

import moderngl
import numpy as np
from pyrr import Matrix44
from trimesh import Trimesh
from trimesh.creation import box

from meshsee.camera import Camera
from meshsee.label_atlas import LabelAtlas
from meshsee.label_metrics import label_char_width, label_step, labels_to_show
from meshsee.observable import Observable
from meshsee.program_updater import ProgramUpdater, ProgramValues
from meshsee.render.renderee import LabelRenderee, TrimeshRenderee
import meshsee.shaders


AXIS_LENGTH = 1000.0
AXIS_WIDTH = 0.01
AXIS_DEPTH = 0.01
MESH_COLOR = np.array([0.5, 0.5, 0.5, 1.0], "f4")
MAX_LABEL_FRAC_OF_STEP = 0.5
MAX_LABELS_PER_AXIS = 20
PER_NUMBER_FRAC_OF_AXIS = 0.04


def _make_default_mesh() -> Trimesh:
    return box([50.0, 40.0, 30.0])


def _make_axes() -> Trimesh:
    return (
        box([AXIS_LENGTH, AXIS_DEPTH, AXIS_WIDTH])
        .union(box([AXIS_LENGTH, AXIS_WIDTH, AXIS_DEPTH]))
        .union(box([AXIS_WIDTH, AXIS_LENGTH, AXIS_DEPTH]))
        .union(box([AXIS_DEPTH, AXIS_LENGTH, AXIS_WIDTH]))
        .union(box([AXIS_DEPTH, AXIS_WIDTH, AXIS_LENGTH]))
        .union(box([AXIS_WIDTH, AXIS_DEPTH, AXIS_LENGTH]))
    )


class ShaderProgram:
    def __init__(
        self,
        ctx: moderngl.Context,
        vertex_shader_loc: str,
        fragment_shader_loc: str,
        register: dict[ProgramValues, str],
    ):
        self._ctx = ctx
        self.register = register
        vertex_shader_source = files(meshsee.shaders).joinpath(vertex_shader_loc)
        fragment_shader_source = files(meshsee.shaders).joinpath(fragment_shader_loc)
        with (
            as_file(vertex_shader_source) as vs_f,
            as_file(fragment_shader_source) as fs_f,
        ):
            try:
                self.program = self._ctx.program(
                    vertex_shader=vs_f.read_text(),
                    fragment_shader=fs_f.read_text(),
                )
            except Exception as e:
                print(f"Error creating shader program: {e}")

    def update_program_var(self, var: ProgramValues, value: Any):
        if var not in self.register:
            return
        var_name = self.register[var]
        uniform = self.program[var_name]
        if uniform.gl_type == 0x8B56:
            uniform.value = value
        else:
            uniform.write(value)

    def subscribe_to_updates(self, updates: Observable):
        updates.subscribe(self.update_program_var)


class Renderer:
    BACKGROUND_COLOR = (0.5, 0.3, 0.2)

    def __init__(self, context: moderngl.Context, camera: Camera, aspect_ratio: float):
        self._ctx = context
        self._create_shaders()
        self._create_renderees()
        self._set_up_camera(camera, aspect_ratio)
        self._init_shaders()
        self._ctx.clear(*self.BACKGROUND_COLOR)
        self.frame()

    def _create_shaders(self):
        self.on_program_value_change = Observable()
        self._prog = self._create_main_shader_program(self.on_program_value_change)
        self._num_prog = self._create_num_shader_program(self.on_program_value_change)

    def _create_renderees(self):
        self._default_mesh = _make_default_mesh()
        self._main_renderee = TrimeshRenderee(
            self._ctx, self._prog.program, self._default_mesh
        )
        self._axes = _make_axes()
        self._axes_renderee = TrimeshRenderee(self._ctx, self._prog.program, self._axes)
        self._label_atlas = LabelAtlas(self._ctx)
        self._label_renderees = {}

    def _set_up_camera(self, camera: Camera, aspect_ratio: float):
        self._camera = camera
        self._camera.on_program_value_change.subscribe(self._update_program_value)
        self.aspect_ratio = aspect_ratio

    def _init_shaders(self):
        self._m_model = Matrix44.identity(dtype="f4")
        self.show_grid = True
        self._update_program_value(ProgramValues.MODEL_MATRIX, self._m_model)
        self._update_program_value(ProgramValues.MESH_COLOR, MESH_COLOR)

    @property
    def aspect_ratio(self):
        return self._camera.aspect_ratio

    @aspect_ratio.setter
    def aspect_ratio(self, aspect_ratio):
        self._camera.aspect_ratio = aspect_ratio

    @property
    def show_grid(self):
        return self._show_grid

    @show_grid.setter
    def show_grid(self, value: bool):
        self._show_grid = value
        self._update_program_value(ProgramValues.SHOW_GRID, value)

    def _update_program_value(self, t: ProgramValues, value: Any):
        self.on_program_value_change.notify(t, value)

    def _create_main_shader_program(self, observable: Observable) -> ShaderProgram:
        program_vars = {
            ProgramValues.MODEL_MATRIX: "m_model",
            ProgramValues.CAMERA_MATRIX: "m_camera",
            ProgramValues.PROJECTION_MATRIX: "m_proj",
            ProgramValues.MESH_COLOR: "color",
            ProgramValues.SHOW_GRID: "show_grid",
        }
        return self._create_shader_program(
            "vertex.glsl", "fragment.glsl", program_vars, observable
        )

    def _create_shader_program(
        self,
        vertex_shader_loc: str,
        fragment_shader_loc: str,
        register: dict[ProgramValues, str],
        observable: Observable,
    ) -> ShaderProgram:
        prog = ShaderProgram(
            self._ctx, vertex_shader_loc, fragment_shader_loc, register
        )
        prog.subscribe_to_updates(observable)
        return prog

    def _create_num_shader_program(self, observable: Observable) -> ShaderProgram:
        program_vars = {
            ProgramValues.MODEL_MATRIX: "m_model",
            ProgramValues.CAMERA_MATRIX: "m_camera",
            ProgramValues.PROJECTION_MATRIX: "m_proj",
        }
        return self._create_shader_program(
            "label_vertex.glsl", "label_fragment.glsl", program_vars, observable
        )

    def load_mesh(
        self,
        mesh: Trimesh,
    ):
        self._main_renderee = TrimeshRenderee(self._ctx, self._prog.program, mesh)

    def frame(self, direction=None, up=None):
        self._camera.frame(self._main_renderee.points, direction, up)

    def orbit(self, angle_from_up, rotation_angle):
        self._camera.orbit(angle_from_up, rotation_angle)

    def move(self, distance):
        self._camera.move(distance)

    def move_up(self, distance):
        self._camera.move_up(distance)

    def move_right(self, distance):
        self._camera.move_right(distance)

    def move_along(self, vector):
        self._camera.move_along(vector)

    def move_to_screen(self, ndx: float, ndy: float, distance: float):
        """
        Move the camera to the normalized screen position (ndx, ndy) and move it by distance.
        """
        self._camera.move_to_screen(ndx, ndy, distance)

    def render(self, show_grid: bool):  # override
        self._ctx.enable_only(moderngl.DEPTH_TEST)
        # self.ctx.enable_only(moderngl.BLEND)
        # self._ctx.clear(0.5, 0.3, 0.2, 1.0)
        self.show_grid = True
        self._axes_renderee.render()
        self.show_grid = show_grid
        self._main_renderee.render()
        self._render_labels()

    def _render_labels(self):
        axis_ranges = [(i, self._camera.axis_visible_range(i)) for i in range(3)]
        visible_ranges = list(filter(lambda x: x[1] is not None, axis_ranges))
        if len(visible_ranges) == 0:
            return
        spans = [range[1][1] - range[1][0] for range in visible_ranges]
        max_span = max(spans)
        step = label_step(max_span, MAX_LABELS_PER_AXIS)
        min_value = min([visible_range[1][0] for visible_range in visible_ranges])
        max_value = max([visible_range[1][1] for visible_range in visible_ranges])
        char_width = label_char_width(
            min_value, max_value, step, MAX_LABEL_FRAC_OF_STEP
        )
        for visible in visible_ranges:
            axis = visible[0]
            min_value = visible[1][0]
            max_value = visible[1][1]
            show = labels_to_show(min_value, max_value, step)
            for label in show:
                if label not in self._label_renderees.keys():
                    self._label_renderees[label] = LabelRenderee(
                        self._ctx,
                        self._num_prog.program,
                        self._label_atlas,
                        self._camera,
                        label,
                    )
                l = self._label_renderees[label]
                l.char_width = char_width
                l.axis = axis
                l.render()


class RendererFactory:
    def __init__(self, camera: Camera):
        self._camera = camera

    def make(self, aspect_ratio) -> Renderer:
        return Renderer(moderngl.create_context(), self._camera, aspect_ratio)
