from importlib.resources import as_file, files
from math import pi

import moderngl
import numpy as np
from pyrr import Matrix44
from trimesh import Trimesh
from trimesh.creation import box

from meshsee.camera import Camera
from meshsee.label_atlas import LabelAtlas
from meshsee.label_metrics import label_char_width, label_step, labels_to_show
from meshsee.render.renderee import LabelRenderee
import meshsee.shaders


AXIS_LENGTH = 1000.0
AXIS_WIDTH = 0.01
AXIS_DEPTH = 0.01
MESH_COLOR = (0.5, 0.5, 0.5, 1.0)
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


class RenderBuffers:
    def __init__(self, ctx: moderngl.Context, prog: moderngl.Program, mesh: Trimesh):
        self.mesh = mesh
        self.points = mesh.triangles.reshape(-1, 3)
        self.vertices = ctx.buffer(data=mesh.triangles.astype("f4"))
        self.normals = ctx.buffer(
            data=np.array([[v] * 3 for v in mesh.triangles_cross])
            .astype("f4")
            .tobytes()
        )
        try:
            self.vao = self._create_vao(ctx, prog)
        except Exception as e:
            print(f"Error creating vertex array: {e}")

    def _create_vao(self, ctx: moderngl.Context, prog: moderngl.Program):
        vao = ctx.vertex_array(
            prog,
            [
                (self.vertices, "3f4", "in_position"),
                (self.normals, "3f4", "in_normal"),
            ],
            mode=moderngl.TRIANGLES,
        )
        return vao

    def render(self):
        self.vao.render()


class Renderer:
    BACKGROUND_COLOR = (0.5, 0.3, 0.2)

    def __init__(self, context: moderngl.Context, camera: Camera, aspect_ratio: float):
        self._ctx = context
        self._camera = camera
        self._prog = self._create_shader_program()
        self._num_prog = self._create_num_shader_program()
        self.aspect_ratio = aspect_ratio
        self._ctx.clear(*self.BACKGROUND_COLOR)
        self._default_mesh = _make_default_mesh()
        self._render_mesh = RenderBuffers(self._ctx, self._prog, self._default_mesh)
        self.frame()
        self._axes = _make_axes()
        self._axes_render_mesh = RenderBuffers(self._ctx, self._prog, self._axes)
        self._label_atlas = LabelAtlas(self._ctx)
        self._label_meshes = {}

    @property
    def aspect_ratio(self):
        return self._camera.aspect_ratio

    @aspect_ratio.setter
    def aspect_ratio(self, aspect_ratio):
        self._camera.aspect_ratio = aspect_ratio
        self._prog["m_proj"].write(self._camera.projection_matrix)
        self._num_prog["m_proj"].write(self._camera.projection_matrix)

    def _create_shader_program(self) -> moderngl.Program:
        vertex_shader_source = files(meshsee.shaders).joinpath("vertex.glsl")
        fragment_shader_source = files(meshsee.shaders).joinpath("fragment.glsl")
        with (
            as_file(vertex_shader_source) as vs_f,
            as_file(fragment_shader_source) as fs_f,
        ):
            try:
                return self._ctx.program(
                    vertex_shader=vs_f.read_text(),
                    fragment_shader=fs_f.read_text(),
                )
            except Exception as e:
                print(f"Error creating shader program: {e}")

    def _create_num_shader_program(self) -> moderngl.Program:
        vertex_shader_source = files(meshsee.shaders).joinpath("label_vertex.glsl")
        fragment_shader_source = files(meshsee.shaders).joinpath("label_fragment.glsl")
        with (
            as_file(vertex_shader_source) as vs_f,
            as_file(fragment_shader_source) as fs_f,
        ):
            try:
                return self._ctx.program(
                    vertex_shader=vs_f.read_text(),
                    fragment_shader=fs_f.read_text(),
                )
            except Exception as e:
                print(f"Error creating num shader program: {e}")

    def load_mesh(
        self,
        mesh: Trimesh,
    ):
        self._render_mesh = RenderBuffers(self._ctx, self._prog, mesh)

    def frame(self, direction=None, up=None):
        self._camera.frame(self._render_mesh.points, direction, up)
        self._set_program_data()

    def _set_program_data(self):
        m_model = Matrix44.identity(dtype="f4")

        self._prog["m_model"].write(m_model)
        self._prog["m_camera"].write(self._camera.view_matrix)
        self._prog["m_proj"].write(self._camera.projection_matrix)
        self._prog["color"].value = MESH_COLOR
        self._num_prog["m_model"].write(m_model)
        self._num_prog["m_camera"].write(self._camera.view_matrix)
        self._num_prog["m_proj"].write(self._camera.projection_matrix)

    def orbit(self, angle_from_up, rotation_angle):
        self._camera.orbit(angle_from_up, rotation_angle)
        self._prog["m_camera"].write(self._camera.view_matrix)
        self._prog["m_proj"].write(self._camera.projection_matrix)
        self._num_prog["m_camera"].write(self._camera.view_matrix)
        self._num_prog["m_proj"].write(self._camera.projection_matrix)

    def move(self, distance):
        self._camera.move(distance)
        self._prog["m_camera"].write(self._camera.view_matrix)
        self._prog["m_proj"].write(self._camera.projection_matrix)
        self._num_prog["m_camera"].write(self._camera.view_matrix)
        self._num_prog["m_proj"].write(self._camera.projection_matrix)

    def move_up(self, distance):
        self._camera.move_up(distance)
        self._prog["m_camera"].write(self._camera.view_matrix)
        self._prog["m_proj"].write(self._camera.projection_matrix)
        self._num_prog["m_camera"].write(self._camera.view_matrix)
        self._num_prog["m_proj"].write(self._camera.projection_matrix)

    def move_right(self, distance):
        self._camera.move_right(distance)
        self._prog["m_camera"].write(self._camera.view_matrix)
        self._prog["m_proj"].write(self._camera.projection_matrix)
        self._num_prog["m_camera"].write(self._camera.view_matrix)
        self._num_prog["m_proj"].write(self._camera.projection_matrix)

    def move_along(self, vector):
        self._camera.move_along(vector)
        self._prog["m_camera"].write(self._camera.view_matrix)
        self._prog["m_proj"].write(self._camera.projection_matrix)
        self._num_prog["m_camera"].write(self._camera.view_matrix)
        self._num_prog["m_proj"].write(self._camera.projection_matrix)

    def move_to_screen(self, ndx: float, ndy: float, distance: float):
        """
        Move the camera to the normalized screen position (ndx, ndy) and move it by distance.
        """
        self._camera.move_to_screen(ndx, ndy, distance)
        self._prog["m_camera"].write(self._camera.view_matrix)
        self._prog["m_proj"].write(self._camera.projection_matrix)
        self._num_prog["m_camera"].write(self._camera.view_matrix)
        self._num_prog["m_proj"].write(self._camera.projection_matrix)

    def render(self, show_grid: bool):  # override
        self._ctx.enable_only(moderngl.DEPTH_TEST)
        # self.ctx.enable_only(moderngl.BLEND)
        # self._ctx.clear(0.5, 0.3, 0.2, 1.0)
        self._prog["show_grid"] = True
        self._axes_render_mesh.render()
        self._prog["show_grid"] = show_grid
        self._render_mesh.render()
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
                if label not in self._label_meshes.keys():
                    self._label_meshes[label] = LabelRenderee(
                        self._ctx,
                        self._num_prog,
                        self._label_atlas,
                        self._camera,
                        label,
                    )
                l = self._label_meshes[label]
                l.char_width = char_width
                l.axis = axis
                l.render()


class RendererFactory:
    def __init__(self, camera: Camera):
        self._camera = camera

    def make(self, aspect_ratio) -> Renderer:
        return Renderer(moderngl.create_context(), self._camera, aspect_ratio)
