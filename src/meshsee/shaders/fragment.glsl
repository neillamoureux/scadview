#version 330
out vec4 fragColor;
uniform vec4 color;

in vec3 pos;
in vec3 w_pos;
//in vec3 color;
in vec3 normal;
//in bool show_grid;

vec4 gridColor;

float on_grid(float pos, float spacing, float frac_width) {
    // return 1.0 if pos is between spacing * n - spacing * frac_width and spacing * n + spacing * frac_width
    return step(pos / spacing - floor(pos/spacing), frac_width)
    + step(1.0 - frac_width, pos / spacing - floor(pos/spacing));
}

vec4 grid_color(vec3 pos, float spacing, float frac_width) {
    return vec4(
        on_grid(pos.x, spacing, frac_width),
        on_grid(pos.y, spacing, frac_width),
        on_grid(pos.z, spacing, frac_width),
        1.0
    );
}

vec4 combined_grid_color(vec3 pos, int levels, float[5] spacings, float frac_width) {
    vec4 combined_color = vec4(0.0, 0.0, 0.0, 0.0);
    for (int i = 0; i < levels; i++) {
        combined_color += grid_color(pos, spacings[i], frac_width);
    }
    return combined_color / levels;
}

void main() {
    float l = dot(normalize(-pos), normalize(normal)) 
    + 0.4;
    vec4 grid = combined_grid_color(w_pos, 3, float[5](0.1, 1.0, 10.0, 0.0, 0.0), 0.05);
    if (grid == vec4(0.0, 0.0, 0.0, 1.0)) {
        fragColor = color;
    } else {
        fragColor = grid;
    }

    fragColor = fragColor * (0.25 + abs(l) * 0.75);
}

