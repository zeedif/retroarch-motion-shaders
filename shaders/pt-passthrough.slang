#version 450

/*
   Pixel Transparency stand-in
   Passes the picture through untouched and is named "Pixel_Transparency", the texture sunlight_shimmer.slang (libretro handheld/ shaders) composes
   its light effects over. Put it, then film_noise_cache.slang, then sunlight_shimmer.slang at the end of any preset that has no real
   pixel_transparency pass (CRT, Game Boy, GBA) to get the shimmer without the GBC "transparent pixel" look.
   License: CC0 / public domain.
*/

#pragma name Pixel_Transparency

layout(push_constant) uniform Push
{
   vec4 SourceSize;
   vec4 OutputSize;
} param;

layout(std140, set = 0, binding = 0) uniform UBO
{
   mat4 MVP;
} global;

#pragma stage vertex
layout(location = 0) in vec4 Position;
layout(location = 1) in vec2 TexCoord;
layout(location = 0) out vec2 vTexCoord;

void main()
{
   gl_Position = global.MVP * Position;
   vTexCoord = TexCoord;
}

#pragma stage fragment
layout(location = 0) in vec2 vTexCoord;
layout(location = 0) out vec4 FragColor;
layout(set = 0, binding = 2) uniform sampler2D Source;

void main()
{
   FragColor = texture(Source, vTexCoord);
}
