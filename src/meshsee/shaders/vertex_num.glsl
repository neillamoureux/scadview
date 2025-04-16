#version 330

in vec3 in_position;

uniform mat4 m_model;
uniform mat4 m_camera;
uniform mat4 m_proj;

// out vec3 pos;
// out vec3 w_pos;

void main() {
    mat4 m_view = m_camera * m_model;
    // vec4 world_pos = m_model * vec4(in_position, 1.0);
    // w_pos = world_pos.xyz / world_pos.w;
    vec4 p = m_view * vec4(in_position, 1.0);
    gl_Position =  m_proj * p;
    // mat3 m_normal = inverse(transpose(mat3(m_view)));
    // normal = m_normal * normalize(in_normal);
    // pos = p.xyz/ p.w;
    //color = in_color;
}
