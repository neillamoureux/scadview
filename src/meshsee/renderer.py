from typing import Any
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


class Renderer:
    BACKGROUND_COLOR = (0.5, 0.3, 0.2)

    def __init__(self, context: moderngl.Context, camera: Camera, aspect_ratio: float):
        self._ctx = context
        self._program_updaters: list[ProgramUpdater] = []
        self._prog, prog_vars = self._create_shader_program()
        pu = ProgramUpdater(self._prog, prog_vars)
        self._program_updaters.append(pu)
        self._num_prog, num_prog_vars = self._create_num_shader_program()
        pu_num = ProgramUpdater(self._num_prog, num_prog_vars)
        self._program_updaters.append(pu_num)
        self._ctx.clear(*self.BACKGROUND_COLOR)
        self._default_mesh = _make_default_mesh()
        self._main_renderee = TrimeshRenderee(self._ctx, self._prog, self._default_mesh)
        self._axes = _make_axes()
        self._axes_renderee = TrimeshRenderee(self._ctx, self._prog, self._axes)
        self._label_atlas = LabelAtlas(self._ctx)
        self._label_renderees = {}
        self.on_program_value_change = Observable()
        pu.subscribe_to_updates(self.on_program_value_change)
        pu_num.subscribe_to_updates(self.on_program_value_change)
        self._camera = camera
        self._camera.on_program_value_change.subscribe(self._update_program_value)
        self.aspect_ratio = aspect_ratio
        self._m_model = Matrix44.identity(dtype="f4")
        self.show_grid = True
        self._m_scale = None
        self.frame()

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

    def _create_shader_program(self) -> moderngl.Program:
        program_vars = {
            ProgramValues.MODEL_MATRIX: "m_model",
            ProgramValues.CAMERA_MATRIX: "m_camera",
            ProgramValues.PROJECTION_MATRIX: "m_proj",
            ProgramValues.MESH_COLOR: "color",
            ProgramValues.SHOW_GRID: "show_grid",
        }
        vertex_shader_source = files(meshsee.shaders).joinpath("vertex.glsl")
        fragment_shader_source = files(meshsee.shaders).joinpath("fragment.glsl")
        with (
            as_file(vertex_shader_source) as vs_f,
            as_file(fragment_shader_source) as fs_f,
        ):
            try:
                prog = self._ctx.program(
                    vertex_shader=vs_f.read_text(),
                    fragment_shader=fs_f.read_text(),
                )
            except Exception as e:
                print(f"Error creating shader program: {e}")
        return prog, program_vars

    def _create_num_shader_program(self) -> moderngl.Program:
        program_vars = {
            ProgramValues.MODEL_MATRIX: "m_model",
            ProgramValues.CAMERA_MATRIX: "m_camera",
            ProgramValues.PROJECTION_MATRIX: "m_proj",
        }
        vertex_shader_source = files(meshsee.shaders).joinpath("label_vertex.glsl")
        fragment_shader_source = files(meshsee.shaders).joinpath("label_fragment.glsl")
        with (
            as_file(vertex_shader_source) as vs_f,
            as_file(fragment_shader_source) as fs_f,
        ):
            try:
                prog = self._ctx.program(
                    vertex_shader=vs_f.read_text(),
                    fragment_shader=fs_f.read_text(),
                )
            except Exception as e:
                print(f"Error creating num shader program: {e}")
            return prog, program_vars

    def load_mesh(
        self,
        mesh: Trimesh,
    ):
        self._main_renderee = TrimeshRenderee(self._ctx, self._prog, mesh)

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
                        self._num_prog,
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
