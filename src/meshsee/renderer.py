import moderngl
import numpy as np
from pyrr import Matrix44
from trimesh import Trimesh
from trimesh.creation import box

from meshsee.camera import Camera


# Place vertex straight in the window, no transformation
_VERTEX_SHADER = """
#version 330

in vec3 in_position;
//in vec3 in_color;
in vec3 in_normal;

uniform mat4 m_model;
uniform mat4 m_camera;
uniform mat4 m_proj;

out vec3 pos;
out vec3 normal;
out vec3 w_pos;
//out vec3 color;

void main() {
    mat4 m_view = m_camera * m_model;
    vec4 world_pos = m_model * vec4(in_position, 1.0);
    w_pos = world_pos.xyz / world_pos.w;
    vec4 p = m_view * vec4(in_position, 1.0);
    gl_Position =  m_proj * p;
    mat3 m_normal = inverse(transpose(mat3(m_view)));
    normal = m_normal * normalize(in_normal);
    pos = p.xyz/ p.w;
    //color = in_color;
}

"""

# Paint the triangle in magenta
_FRAGMENT_SHADER = """
#version 330
out vec4 fragColor;
uniform vec4 color;

in vec3 pos;
in vec3 w_pos;
//in vec3 color;
in vec3 normal;

vec4 gridColor;

void main() {
    float l = dot(normalize(-pos), normalize(normal)) + 0.4;
    fragColor = color * (0.25 + abs(l) * 0.75);
    vec4 gridColor = vec4(
        1.0 - step(0.1, fract(1.0 * w_pos.x + 0.05)),
        1.0 - step(0.1, fract(1.0 * w_pos.y + 0.05)),
        1.0 - step(0.1, fract(1.0 * w_pos.z + 0.05)),
        1.0
    );
    fragColor = mix(fragColor, gridColor, 0.3);
}
"""

AXIS_LENGTH = 200.0
AXIS_WIDTH = 0.1

def _make_default_mesh() -> Trimesh:
    return box([50.0, 40.0, 30.0])

def _make_axes() -> Trimesh:
    return (box([AXIS_LENGTH, AXIS_WIDTH, AXIS_WIDTH])
        .union(box([AXIS_WIDTH, AXIS_LENGTH, AXIS_WIDTH]))
        .union(box([AXIS_WIDTH, AXIS_WIDTH, AXIS_LENGTH])))

class Renderer:
    # ORBIT_ROTATION_SPEED = 0.01
    BACKGROUND_COLOR = (0.5, 0.3, 0.2)

    def __init__(self, context: moderngl.Context, camera: Camera, aspect_ratio: float):
        self._ctx = context
        self._camera = camera
        self._prog = self._create_shader_program()
        self.aspect_ratio = aspect_ratio
        self._ctx.clear(*self.BACKGROUND_COLOR)
        self._default_mesh = _make_default_mesh()
        self.load_mesh(self._default_mesh)
        self.frame()
        self._axes = _make_axes()
        self._load_axes(self._axes)

    @property
    def aspect_ratio(self):
        return self._camera.aspect_ratio

    @aspect_ratio.setter
    def aspect_ratio(self, aspect_ratio):
        self._camera.aspect_ratio = aspect_ratio
        self._prog["m_proj"].write(self._camera.projection_matrix)

    def _create_shader_program(self) -> moderngl.Program:
        try:
            return self._ctx.program(
                vertex_shader=_VERTEX_SHADER,
                fragment_shader=_FRAGMENT_SHADER,
            )
        except Exception as e:
            print(f"Error creating shader program: {e}")

    def load_mesh(
        self,
        mesh: Trimesh,
    ):
        self._mesh, self._points, self._vertices, self._normals = self._setup_mesh(mesh)
        try:
            self._vao = self._create_vao()
        except Exception as e:
            print(f"Error creating vertex array: {e}")

        # self.frame()

    def _load_axes(
        self,
        axes: Trimesh,
    ):
        self._axes_mesh, self._axes_points, self._axes_vertices, self._axes_normals = self._setup_mesh(axes)
        try:
            self._axes_vao = self._create_axes_vao()
        except Exception as e:
            print(f"Error creating vertex array: {e}")

    def _setup_mesh(self, mesh: Trimesh):
        mesh = mesh
        points = mesh.triangles.reshape(-1, 3)
        vertices = self._ctx.buffer(data=mesh.triangles.astype("f4"))
        normals = self._ctx.buffer(
            data=np.array([[v] * 3 for v in mesh.triangles_cross])
            .astype("f4")
            .tobytes()
        )
        return mesh, points, vertices, normals

    def _create_vao(self):
        vao = self._ctx.vertex_array(
            self._prog,
            [
                (self._vertices, "3f4", "in_position"),
                (self._normals, "3f4", "in_normal"),
            ],
            mode=moderngl.TRIANGLES,
        )
        return vao

    def _create_axes_vao(self):
        vao = self._ctx.vertex_array(
            self._prog,
            [
                (self._axes_vertices, "3f4", "in_position"),
                (self._axes_normals, "3f4", "in_normal"),
            ],
            mode=moderngl.TRIANGLES,
        )
        return vao

    def frame(self, direction=None, up=None):
        self._camera.frame(self._points, direction, up)
        self._set_program_data()

    def _set_program_data(self):
        m_model = Matrix44.identity(dtype="f4")

        self._prog["m_model"].write(m_model)
        self._prog["m_camera"].write(self._camera.view_matrix)
        self._prog["m_proj"].write(self._camera.projection_matrix)
        self._prog["color"].value = 1.0, 0.0, 1.0, 1.0

    def orbit(self, angle_from_up, rotation_angle):
        self._camera.orbit(angle_from_up, rotation_angle)
        self._prog["m_camera"].write(self._camera.view_matrix)
        self._prog["m_proj"].write(self._camera.projection_matrix)

    def move(self, distance):
        self._camera.move(distance)
        self._prog["m_camera"].write(self._camera.view_matrix)
        self._prog["m_proj"].write(self._camera.projection_matrix)

    def move_up(self, distance):
        self._camera.move_up(distance)
        self._prog["m_camera"].write(self._camera.view_matrix)
        self._prog["m_proj"].write(self._camera.projection_matrix)

    def move_right(self, distance):
        self._camera.move_right(distance)
        self._prog["m_camera"].write(self._camera.view_matrix)
        self._prog["m_proj"].write(self._camera.projection_matrix)

    def move_along(self, vector):
        self._camera.move_along(vector)
        self._prog["m_camera"].write(self._camera.view_matrix)
        self._prog["m_proj"].write(self._camera.projection_matrix)

    def move_to_screen(self, ndx:float, ndy:float, distance: float):
        """
        Move the camera to the normalized screen position (ndx, ndy) and move it by distance.
        """
        self._camera.move_to_screen(ndx, ndy, distance)
        self._prog["m_camera"].write(self._camera.view_matrix)
        self._prog["m_proj"].write(self._camera.projection_matrix)

    def render(self):  # override
        self._ctx.enable_only(moderngl.DEPTH_TEST)
        # self.ctx.enable_only(moderngl.BLEND)
        # self._ctx.clear(0.5, 0.3, 0.2, 1.0)
        self._axes_vao.render()
        self._vao.render()
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
