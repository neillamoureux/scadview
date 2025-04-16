#version 330

in vec2 v_texcoord;

uniform sampler2D atlas;     // Texture atlas containing glyphs
uniform vec4 textColor;      // The desired text color (including alpha)

void main() {
    // Sample the atlas texture. Assuming a grayscale image, using the red channel.
    float sampled = texture(atlas, v_texcoord).r;
    
    // For a simple bitmap texture, you might use a threshold:
    // float alpha = sampled > 0.5 ? 1.0 : 0.0;
    
    // Or for smoother edges (helpful with SDFs), use a smoothstep:
    float alpha = smoothstep(0.45, 0.55, sampled);
    
    // Output the text color with computed alpha.
    gl_FragColor = vec4(textColor.rgb, textColor.a * alpha);
}
