import moderngl
import numpy as np
from pyrr import matrix44, Matrix44
from PySide6 import QtGui
from PySide6.QtOpenGLWidgets import QOpenGLWidget
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


def prepare_surface_format(gl_version: tuple[int, int]):
    # In macos, the surface format must be set before creating the application
    fmt = QtGui.QSurfaceFormat()
    fmt.setVersion(*gl_version)
    fmt.setProfile(QtGui.QSurfaceFormat.CoreProfile)
    QtGui.QSurfaceFormat.setDefaultFormat(fmt)


def _make_default_mesh() -> Trimesh:
    return box([1.0, 1.0, 1.0])


class ModernglWidget(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._default_mesh = _make_default_mesh()
        self._gl_initialized = False

    def initializeGL(self):  # override
        self._camera = Camera()
        # self.camera.position = np.array([0.0, 2.0, 2.0])
        # self.camera.look_at = np.array([0.0, 0.0, 0.0])
        # self.camera.up = np.array([0.0, 1.0, 0.0])
        # self.camera.fovy = 22.5
        self._camera.aspect_ratio = self.width() / self.height()
        # self.camera.near = 0.1
        # self.camera.far = 1000.0
        # self.camera.frame_points(VERTICES)
        # logging.info(f"Camera position: {self.camera.position}")

        # You cannot create the context before initializeGL is called
        self._ctx = moderngl.create_context()
        self._update_framebuffer_size(
            self.width(), self.height(), self.devicePixelRatio()
        )

        self._prog = self._create_shader_program()
        self.load_mesh(self._default_mesh)
        self._gl_initialized = True

    def _update_framebuffer_size(self, width, height, device_pixel_ratio):
        framebuffer_width = int(width * device_pixel_ratio)
        framebuffer_height = int(height * device_pixel_ratio)
        self._aspect_ratio = framebuffer_width / framebuffer_height
        if self._gl_initialized:
            # m_proj = matrix44.create_perspective_projection(
            #     22.5, self._aspect_ratio, 0.1, 1000.0, dtype="f4"
            # )
            # self._prog["m_proj"].write(m_proj)
            self._camera.aspect_ratio = self._aspect_ratio
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
        self._mesh, self._vertices, self._normals = self._setup_mesh(mesh)
        try:
            self._vao = self._create_vao()
        except Exception as e:
            print(f"Error creating vertex array: {e}")

        self._set_program_data()

        self.update()

    def _setup_mesh(self, mesh: Trimesh):
        mesh = mesh
        vertices = self._ctx.buffer(data=mesh.triangles.astype("f4"))
        normals = self._ctx.buffer(
            data=np.array([[v] * 3 for v in mesh.triangles_cross])
            .astype("f4")
            .tobytes()
        )
        return mesh, vertices, normals

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

    def _set_program_data(self):
        # self.camera.position = np.array([0.0, 2.0, 2.0])
        # self.camera.look_at = np.array([0.0, 0.0, 0.0])
        # self.camera.up = np.array([0.0, 1.0, 0.0])
        # self.camera.fovy = 22.5
        # self.camera.aspect_ratio = self.width() / self.height()
        # self.camera.near = 0.1
        # self.camera.far = 1000.0

        m_model = Matrix44.identity(dtype="f4")
        # m_camera = matrix44.create_look_at(
        #     np.array([0.0, 2.0, 2.0]),
        #     np.array([0.0, 0.0, 0.0]),
        #     np.array([0.0, 1.0, 0.0]),
        #     dtype="f4",
        # )

        # m_proj = matrix44.create_perspective_projection(
        #     22.5, self.width() / self.height(), 0.1, 1000.0, dtype="f4"
        # )

        self._prog["m_model"].write(m_model)
        self._prog["m_camera"].write(self._camera.view_matrix)
        # self._prog["m_camera"].write(m_camera)
        self._prog["m_proj"].write(self._camera.projection_matrix)
        # self._prog["m_proj"].write(m_proj)
        self._prog["color"].value = 1.0, 0.0, 1.0, 1.0
        # self.camera.frame_points(mesh.vertices.astype("f4"))

    def paintGL(self):  # override
        # self._ctx.clear(0.5, 0.3, 0.2, 1.0)
        self._ctx.enable_only(moderngl.DEPTH_TEST)
        # self.ctx.enable_only(moderngl.BLEND)
        self._vao.render()
        # I don't know why calling clear after the render works
        # Calling before obliterates the rendering
        # It still produces GL_INVALID_FRAMEBUFFER_OPERATION
        self._ctx.clear(0.5, 0.3, 0.2, 1.0)

    def resizeGL(self, width, height):  # override
        self._update_framebuffer_size(width, height, self.devicePixelRatio())
