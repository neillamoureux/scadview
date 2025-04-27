#version 330

// layout(location = 0) in vec3 in_position;   // Vertex position
// layout(location = 1) in vec2 in_uv;     // Texture coordinates
in vec3 in_position;   // Vertex position
in vec2 in_uv;     // Texture coordinates

uniform mat4 m_model;
uniform mat4 m_camera;
uniform mat4 m_proj;
uniform mat4 m_scale;

out vec2 v_uv;                          // Pass texture coordinate to fragment shader

void main() {
    mat4 m_view = m_camera * m_scale * m_model;
    vec4 p = m_view * vec4(in_position, 1.0);
    gl_Position =  m_proj * p;
    v_uv = in_uv;
}
