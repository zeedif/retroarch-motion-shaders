#version 450

/*
   Motion state
   Passes the picture through untouched and keeps one number in the ALPHA channel: the device's yaw,
   the angle it has turned about the gravity axis, integrated from the gyroscope and leaking back to zero.
   The accelerometer cannot see yaw (it only feels gravity), so this is the only way to know about it.
   Put it right before a pass that reads the state (crt-glass-motion.slang) and give it:
      alias = "MOTION"          (this pass reads its own previous frame through "MOTIONFeedback")
      float_framebuffer = true  (alpha must hold a signed float; the picture keeps full precision)
      filter_linear = false, scale_type = viewport
   Needs RetroArch with the Gyroscope/Accelerometer uniforms (nightly after 2026-03) and
   Settings > Input > "Auxiliary Sensor Input" on. Without them it holds 0 and everything stays still.
   License: CC0 / public domain.
*/

layout(push_constant) uniform Push
{
   vec4 SourceSize;
   vec4 OutputSize;
   uint FrameTimeDelta;     // microseconds since the previous frame
} param;

layout(std140, set = 0, binding = 0) uniform UBO
{
   mat4 MVP;
#ifdef _HAS_SENSOR_UNIFORMS
   vec3 Gyroscope;          // rad/s about the device's own X, Y, Z
   vec3 Accelerometer;      // g, reaction to gravity (face-up and still: +Z = 1)
   vec3 AccelerometerRest;
#endif
   float ZGM_YAW_ENABLE;
   float ZGM_YAW_RETURN;
   float ZGM_TEST_YAW;
} global;

#pragma parameter ZGM_YAW_ENABLE "Gyro yaw tracking (OFF/ON)" 1.0 0.0 1.0 1.0
#pragma parameter ZGM_YAW_RETURN "      Seconds to settle back after a turn" 1.2 0.2 8.0 0.1
#pragma parameter ZGM_TEST_YAW   "      Test: pretend the device turns at this rate (rad/s)" 0.0 -3.0 3.0 0.1

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
layout(set = 0, binding = 3) uniform sampler2D MOTIONFeedback;

void main()
{
   vec3 src = texture(Source, vTexCoord).rgb;

   // Every pixel carries the same copy of the state, so any texel of last frame's output has it.
   float prev = texture(MOTIONFeedback, vec2(0.5)).a;
   float state = 0.0;

#ifdef _HAS_SENSOR_UNIFORMS
   if (global.ZGM_YAW_ENABLE > 0.5)
   {
      float dt = clamp(float(param.FrameTimeDelta) * 1e-6, 0.0, 0.1);
      vec3 a = global.Accelerometer;
      // "down" in the device's frame; before the accelerometer has reported, assume an upright device.
      vec3 down = (length(a) > 0.3) ? -normalize(a) : vec3(0.0, -1.0, 0.0);
      float yawRate = dot(global.Gyroscope, down) + global.ZGM_TEST_YAW;          // rad/s, positive = turning to the device's right
      float keep = exp(-dt / max(global.ZGM_YAW_RETURN, 0.05));
      state = clamp(prev * keep + yawRate * dt, -1.5, 1.5);
   }
#endif

   FragColor = vec4(src, state);
}
