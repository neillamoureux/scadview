from importlib.resources import as_file, files

import moderngl
import numpy as np
from pyrr import Matrix44
from trimesh import Trimesh
from trimesh.creation import box

from meshsee.camera import Camera
from meshsee.label_atlas import LabelAtlas
import meshsee.shaders


AXIS_LENGTH = 200.0
AXIS_WIDTH = 0.1
MESH_COLOR = (0.5, 0.5, 0.5, 1.0)
LABEL_WIDTH = 30.0
LABEL_HEIGHT = 10.0
NUMBER_HEIGHT = 10.0
NUMBER_WIDTH = 5.0


def _make_default_mesh() -> Trimesh:
    return box([50.0, 40.0, 30.0])


def _make_axes() -> Trimesh:
    return (
        box([AXIS_LENGTH, AXIS_WIDTH, AXIS_WIDTH])
        .union(box([AXIS_WIDTH, AXIS_LENGTH, AXIS_WIDTH]))
        .union(box([AXIS_WIDTH, AXIS_WIDTH, AXIS_LENGTH]))
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
    def __init__(self, ctx: moderngl.Context, prog: moderngl.Program, mesh: Trimesh):
        self.mesh = mesh
        self.points = mesh.triangles.reshape(-1, 3)
        self.vertices = ctx.buffer(data=mesh.triangles.astype("f4"))
        label_atlas = LabelAtlas(ctx)
        uvs = label_atlas.uv("3").astype("f4")
        uvarr = np.array(
            [
                uvs[0],
                uvs[1],
                uvs[2],
                uvs[1],
                uvs[0],
                uvs[3],
                uvs[2],
                uvs[1],
                uvs[2],
                uvs[3],
                uvs[0],
                uvs[3],
            ],
            dtype="f4",
        )
        self.uv = ctx.buffer(data=uvarr.tobytes())
        # self.texture = label_atlas.texture
        self.sampler = label_atlas.sampler
        try:
            self.vao = self._create_vao(ctx, prog)
        except Exception as e:
            print(f"Error creating vertex array: {e}")

        prog["atlas"].value = 0
        # self.texture.use(location=0)
        self.sampler.use(location=0)
        self._prog = prog

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
        self.sampler.use(location=0)
        self.vao.render()


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
        # self.load_mesh(self._default_mesh)
        self.frame()
        self._axes = _make_axes()
        self._axes_render_mesh = RenderBuffers(self._ctx, self._prog, self._axes)
        self._label_mesh = RenderBuffersLabel(
            self._ctx, self._num_prog, _make_axis_label()
        )
        # self._label_atlas = LabelAtlas(self._ctx)
        # self._number_2 = RendererBuffersLineStrip(
        #     self._ctx, self._num_prog, _make_number_2()
        # )
        # self._load_axes(self._axes)

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
        # vertex_shader_source = files(meshsee.shaders).joinpath("vertex_num.glsl")
        # fragment_shader_source = files(meshsee.shaders).joinpath("fragment_num.glsl")
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
        # self._prog["show_grid"] = show_grid
        # self._render_mesh.render()

        self._prog["show_grid"] = False
        self._label_mesh.render()

        # self._number_2.render()
        # I don't know why calling clear after the render works
        # Calling before obliterates the rendering
        # Possibly because the render method swaps the frame buffer?
        # It still produces GL_INVALID_FRAMEBUFFER_OPERATION
        # self._ctx.clear(*self.BACKGROUND_COLOR)


class RendererFactory:
    def __init__(self, camera: Camera):
        self._camera = camera

    def make(self, aspect_ratio) -> Renderer:
        return Renderer(moderngl.create_context(), self._camera, aspect_ratio)
