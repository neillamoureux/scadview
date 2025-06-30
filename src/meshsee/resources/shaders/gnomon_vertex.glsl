#version 330

in vec3 in_position;
in vec3 in_color;

uniform mat4 m_model;
uniform mat4 m_camera;
uniform mat4 m_proj;

// out vec3 pos;
out vec3 color;

void main() {
    // vec4 world_pos = m_model * vec4(in_position, 1.0);
    // w_pos = world_pos.xyz / world_pos.w;
    // w_normal = normalize(inverse(transpose(mat3(m_model))) * in_normal);
    // mat4 m_view = m_camera * m_model;
    // vec4 p = m_view * vec4(in_position, 1.0);
    gl_Position =  m_proj * m_camera * m_model * vec4(in_position, 1.0);
    // mat3 m_normal = inverse(transpose(mat3(m_view)));
    // normal = normalize(m_normal * in_normal);
    // pos = p.xyz/ p.w;
    color = in_color;
}
