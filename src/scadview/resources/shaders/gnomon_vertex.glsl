#version 330

in vec3 in_position;
in vec3 in_color;

uniform mat4 m_model;
uniform mat4 m_camera;
uniform mat4 m_proj;

out vec3 color;

void main() {
    gl_Position =  m_proj * m_camera * m_model * vec4(in_position, 1.0);
    color = in_color;
}
