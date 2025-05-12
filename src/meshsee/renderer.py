from importlib.resources import as_file, files
from math import pi

import moderngl
import numpy as np
from pyrr import Matrix44
from trimesh import Trimesh
from trimesh.creation import box

from meshsee.camera import Camera
from meshsee.label_atlas import LabelAtlas
import meshsee.shaders


AXIS_LENGTH = 1000.0
AXIS_WIDTH = 0.01
AXIS_DEPTH = 0.1
MESH_COLOR = (0.5, 0.5, 0.5, 1.0)
LABEL_WIDTH = 30.0
LABEL_HEIGHT = 10.0
NUMBER_HEIGHT = 1.0
NUMBER_WIDTH = 0.5
MAX_LABEL_FRAC_OF_AXIS = 0.2
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


def _make_axis_label() -> Trimesh:
    vertices = np.array(
        [
            [0, 0, 0],
            [LABEL_WIDTH, 0, 0],
            [0, LABEL_HEIGHT, 0],
            [LABEL_WIDTH, 0, 0],
            [LABEL_WIDTH, LABEL_HEIGHT, 0],
            [0, LABEL_HEIGHT, 0],
        ]
    )
    faces = [[0, 1, 2], [3, 4, 5]]
    return Trimesh(vertices=vertices, faces=faces)


def _make_number_2() -> np.ndarray:
    vertices = np.array(
        [
            [NUMBER_HEIGHT, 0, 0],
            [NUMBER_HEIGHT, NUMBER_WIDTH, 0],
            [NUMBER_HEIGHT / 2.0, NUMBER_WIDTH, 0],
            [NUMBER_HEIGHT / 2.0, 0, 0],
            [0, 0, 0],
            [0, NUMBER_WIDTH, 0],
        ]
    )
    return vertices


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


class RenderBuffersLabel(RenderBuffers):

    def __init__(
        self,
        ctx: moderngl.Context,
        prog: moderngl.Program,
        label_atlas: LabelAtlas,
        camera: Camera,
        number: int,
    ):
        self.ctx = ctx
        self.camera = camera
        self._number = number
        self.scale = 1.0
        text = str(self._number)
        base_vertices = np.array(
            [
                [NUMBER_WIDTH, NUMBER_HEIGHT, 0.0],  # top left
                [NUMBER_WIDTH, 0.0, 0.0],  # bottom left
                [0.0, NUMBER_HEIGHT, 0.0],  # top right
                [0.0, 0.0, 0.0],  # bottom right
            ],
            dtype="f4",
        )

        vertices = np.empty(base_vertices.shape, dtype="f4")
        uvs = np.empty((0, 2), dtype="f4")
        center = len(text) * NUMBER_WIDTH / -2.0 + self._number
        for i, c in enumerate(text):
            offset = NUMBER_WIDTH * i + center
            vertices = np.concatenate(
                [
                    (base_vertices + np.array([offset, 0.0, 0.0], dtype="f4")),
                    vertices,
                ],
                axis=0,
                dtype="f4",
            )
            c_uvs = label_atlas.uv(c).astype("f4")

            uvs = np.concatenate(
                [
                    np.array(
                        [
                            [c_uvs[2], c_uvs[1]],  # top right
                            [c_uvs[2], c_uvs[3]],  # bottom right
                            [c_uvs[0], c_uvs[1]],  # top left
                            [c_uvs[0], c_uvs[3]],  # bottom left
                        ],
                        dtype="f4",
                    ),
                    uvs,
                ],
                axis=0,
                dtype="f4",
            )

        self.vertices = ctx.buffer(data=vertices.tobytes())
        self.uv = ctx.buffer(data=uvs.tobytes())
        self.sampler = label_atlas.sampler
        try:
            self.vao = self._create_vao(ctx, prog)
        except Exception as e:
            print(f"Error creating vertex array: {e}")

        prog["atlas"].value = 0
        self.sampler.use(location=0)
        self._prog = prog
        self._translate_to_origin = Matrix44.from_translation(
            [-self._number, 0.0, 0.0], dtype="f4"
        )
        self._translate_from_origin = Matrix44.from_translation(
            [self._number, 0.0, 0.0], dtype="f4"
        )

    def _create_vao(self, ctx: moderngl.Context, prog: moderngl.Program):
        vao = ctx.vertex_array(
            prog,
            [
                (self.vertices, "3f4", "in_position"),
                (self.uv, "2f4", "in_uv"),
            ],
            mode=moderngl.TRIANGLES,
        )
        return vao

    def render(self):
        m_mag = np.identity(4, dtype="f4")
        m_mag[0, 0] = self.scale
        m_mag[1, 1] = self.scale
        m_scale = self._translate_from_origin * m_mag * self._translate_to_origin
        self._prog["m_scale"].write(m_scale)
        self.sampler.use(location=0)
        self.ctx.enable(moderngl.BLEND)
        # Use the standard alpha blend function
        self.ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)
        self.vao.render(moderngl.TRIANGLE_STRIP)

        # y axis
        rotation = Matrix44.from_z_rotation(-pi / 2.0, dtype="f4")
        m_scale = (
            rotation * self._translate_from_origin * m_mag * self._translate_to_origin
        )
        self._prog["m_scale"].write(m_scale)
        self.vao.render(moderngl.TRIANGLE_STRIP)

        # z axis
        rotation_z = Matrix44.from_z_rotation(
            pi, dtype="f4"
        ) * Matrix44.from_y_rotation(pi / 2.0, dtype="f4")
        m_scale = (
            rotation_z * self._translate_from_origin * m_mag * self._translate_to_origin
        )
        self._prog["m_scale"].write(m_scale)
        self.vao.render(moderngl.TRIANGLE_STRIP)

        self.ctx.disable(moderngl.BLEND)


class RenderBuffersLineStrip:
    def __init__(
        self, ctx: moderngl.Context, prog: moderngl.Program, points: np.ndarray
    ):
        self._ctx = ctx
        self.vertices = ctx.buffer(data=points.astype("f4").tobytes())
        try:
            self.vao = self._create_vao(ctx, prog)
        except Exception as e:
            print(f"Error creating vertex array: {e}")

    def _create_vao(self, ctx: moderngl.Context, prog: moderngl.Program):
        vao = ctx.vertex_array(
            prog,
            [
                (self.vertices, "3f4", "in_position"),
            ],
            mode=moderngl.LINE_STRIP,
        )
        return vao

    def render(self):
        self._ctx.line_width = 10.0
        self.vao.render()


class Renderer:
    # ORBIT_ROTATION_SPEED = 0.01
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
        ranges = [self._camera.axis_visible_range(i) for i in range(3)]
        ranges = list(filter(lambda x: x is not None, ranges))
        if len(ranges) == 0:
            return
        spans = [range[1] - range[0] for range in ranges]
        scale = max(spans) * PER_NUMBER_FRAC_OF_AXIS

        for i in range(-100, 101, 10):
            if i not in self._label_meshes.keys():
                self._label_meshes[i] = RenderBuffersLabel(
                    self._ctx, self._num_prog, self._label_atlas, self._camera, i
                )
        for l in self._label_meshes.values():
            l.scale = scale
            l.render()


class RendererFactory:
    def __init__(self, camera: Camera):
        self._camera = camera

    def make(self, aspect_ratio) -> Renderer:
        return Renderer(moderngl.create_context(), self._camera, aspect_ratio)
