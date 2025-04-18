#version 330

in vec2 v_uv;
out vec4 fragColor;


uniform sampler2D atlas;     // Texture atlas containing glyphs
// uniform vec4 textColor;      // The desired text color (including alpha)

void main() {
    // Sample the atlas texture. Assuming a grayscale image, using the red channel.
    float sampled = 1.0 - texture(atlas, v_uv).r;
    // float sampled2 = texture(atlas, v_uv).g;
    
    // For a simple bitmap texture, you might use a threshold:
    // float alpha = sampled > 0.5 ? 1.0 : 0.0;
    
    // Or for smoother edges (helpful with SDFs), use a smoothstep:
    // float alpha = smoothstep(0.45, 0.55, sampled);
    
    // Output the text color with computed alpha.
    // gl_FragColor = vec4(textColor.rgb, textColor.a * alpha);
    fragColor = vec4(sampled, sampled, sampled, step(sampled, 0.5));
    // fragColor = vec4(sampled,  v_uv.x * 11.0 - 3.0, v_uv.y, 0.5);
}
