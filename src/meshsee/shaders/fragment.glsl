#version 330
out vec4 fragColor;
uniform vec4 color;

in vec3 pos;
in vec3 w_pos;
//in vec3 color;
in vec3 normal;

vec4 gridColor;

float on_grid(float pos, float spacing, float frac_width) {
    // return 1.0 if pos is between spacing * n - spacing * frac_width and spacing * n + spacing * frac_width
    return step(pos / spacing - floor(pos/spacing), frac_width)
    + step(1.0 - frac_width, pos / spacing - floor(pos/spacing));
}

void main() {

    float l = dot(normalize(-pos), normalize(normal)) + 0.4;
    vec4 gridColor1 = vec4(
        on_grid(w_pos.x, 0.1, 0.05),
        on_grid(w_pos.y, 0.1, 0.05),
        on_grid(w_pos.z, 0.1, 0.05),
        1.0
    );
    vec4 gridColor2 = vec4(
        on_grid(w_pos.x, 1.0, 0.05),
        on_grid(w_pos.y, 1.0, 0.05),
        on_grid(w_pos.z, 1.0, 0.05),
        1.0
    );
    vec4 gridColor3 = vec4(
        on_grid(w_pos.x, 10.0, 0.05),
        on_grid(w_pos.y, 10.0, 0.05),
        on_grid(w_pos.z, 10.0, 0.05),
        1.0
    );
    if (gridColor1 == vec4(0.0, 0.0, 0.0, 1.0) 
    && gridColor2 == vec4(0.0, 0.0, 0.0, 1.0) 
    && gridColor3 == vec4(0.0, 0.0, 0.0, 1.0)) {
        fragColor = color;
    } else {
        fragColor = (gridColor1 + gridColor2 + gridColor3) / 3.0;
    }

    fragColor = fragColor * (0.25 + abs(l) * 0.75);
}
