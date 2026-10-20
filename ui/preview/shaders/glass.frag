#version 440
layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    vec2 surfaceSize;
    vec2 sceneSize;
    vec2 scenePosition;
    vec2 lightPosition;
    float cornerRadius;
    float frost;
    float thickness;
    float whiteMix;
};
layout(binding = 1) uniform sampler2D backdrop;

float roundedDistance(vec2 p, vec2 halfSize, float radius) {
    vec2 q = abs(p) - halfSize + radius;
    return min(max(q.x, q.y), 0.0) + length(max(q, 0.0)) - radius;
}

void main() {
    vec2 point = qt_TexCoord0 * surfaceSize;
    vec2 centered = point - surfaceSize * 0.5;
    float radius = min(cornerRadius, min(surfaceSize.x, surfaceSize.y) * 0.5);
    float distance = roundedDistance(centered, surfaceSize * 0.5 - 0.8, radius);
    float mask = 1.0 - smoothstep(-0.6, 0.6, distance);
    vec2 normal = normalize(vec2(
        roundedDistance(centered + vec2(0.5, 0.0), surfaceSize * 0.5, radius) - roundedDistance(centered - vec2(0.5, 0.0), surfaceSize * 0.5, radius),
        roundedDistance(centered + vec2(0.0, 0.5), surfaceSize * 0.5, radius) - roundedDistance(centered - vec2(0.0, 0.5), surfaceSize * 0.5, radius)
    ) + vec2(0.0001));
    float edge = exp(-abs(distance) / 10.0);
    vec2 uv = (scenePosition + point - normal * edge * thickness) / max(sceneSize, vec2(1.0));
    vec2 stepSize = vec2(frost) / max(sceneSize, vec2(1.0));
    vec3 sampled = texture(backdrop, uv).rgb * 0.28;
    sampled += texture(backdrop, uv + vec2(stepSize.x, 0.0)).rgb * 0.12;
    sampled += texture(backdrop, uv - vec2(stepSize.x, 0.0)).rgb * 0.12;
    sampled += texture(backdrop, uv + vec2(0.0, stepSize.y)).rgb * 0.12;
    sampled += texture(backdrop, uv - vec2(0.0, stepSize.y)).rgb * 0.12;
    sampled += texture(backdrop, uv + stepSize * 0.7).rgb * 0.06;
    sampled += texture(backdrop, uv - stepSize * 0.7).rgb * 0.06;
    sampled += texture(backdrop, uv + stepSize * vec2(0.7, -0.7)).rgb * 0.06;
    sampled += texture(backdrop, uv + stepSize * vec2(-0.7, 0.7)).rgb * 0.06;
    float luminance = dot(sampled, vec3(0.2126, 0.7152, 0.0722));
    sampled = mix(vec3(luminance), sampled, 0.78);
    vec3 material = mix(sampled, vec3(0.98, 0.995, 0.985), whiteMix);
    vec2 light = normalize(lightPosition * surfaceSize - point + vec2(0.001));
    float specular = pow(max(0.0, dot(normal, light)), 3.0);
    float rim = exp(-abs(distance + 1.0) / 0.65);
    material += rim * (0.25 + 0.55 * specular);
    material += edge * specular * 0.055;
    fragColor = vec4(clamp(material, 0.0, 1.0) * mask, mask) * qt_Opacity;
}
