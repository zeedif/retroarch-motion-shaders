#version 450

/*
   CRT glass, moving with the device
   Last pass for CRT presets. Adds a soft hotspot of room light on the curved glass, the way a real tube had on top
   of the phosphors. The light follows the same law as the glare of libretro's handheld/glare.slang (a gaussian that
   pulls the picture toward white, spread 0.25 screen heights, strength 0.08: the library's 0.15 looks like a lamp) and adds the tube's own parts: it stays
   inside the curved outline, and it slides when the handheld is tilted (accelerometer) or turned (gyroscope,
   through motion-state.slang). The picture itself is never shifted or filtered, so pixels stay exactly where the
   integer scaling and the CRT passes put them; only light is added on top. Everything here can be switched off
   with "CRT glass" (ZGM_ENABLE), or just set Glow strength to 0.

   Geometry: on a convex screen the reflection sits where the glass normal bisects the light and the eye, and the
   normal turns with the device, so the reflection slides the opposite way to the turn. Tilt comes from the change
   of the gravity vector since the rest pose RetroArch captured when the sensors came on (AccelerometerRest);
   yaw, which gravity cannot show, comes from the gyroscope state kept in the alpha channel by motion-state.slang.

   Axes: the sensor values must already be in screen axes (x right, y up). RetroArch does that with
   Settings > Input > Sensor Orientation; on a landscape handheld whose sensors are mounted in portrait (AYN Thor)
   set it to 90 degrees instead of Auto, which only decides once and only after the device has been tilted.

   Needs RetroArch with the Gyroscope/Accelerometer/AccelerometerRest uniforms (nightly after 2026-03) and
   Settings > Input > "Auxiliary Sensor Input" on. Without them the glow simply stays put.
   License: CC0 / public domain.
*/

layout(push_constant) uniform Push
{
   vec4 SourceSize;
   vec4 OutputSize;
} param;

layout(std140, set = 0, binding = 0) uniform UBO
{
   mat4 MVP;
#ifdef _HAS_SENSOR_UNIFORMS
   vec3 Gyroscope;
   vec3 Accelerometer;
   vec3 AccelerometerRest;
#endif
   float ZGM_ENABLE;
   float ZGM_INTENSITY;
   float ZGM_SIZE;
   float ZGM_LIGHT_X;
   float ZGM_LIGHT_Y;
   float ZGM_WINDOW;
   float ZGM_WARM;
   float ZGM_RIM;
   float ZGM_LIFT;
   float ZGM_DITHER;
   float ZGM_TILT_GAIN;
   float ZGM_YAW_GAIN;
   float ZGM_RANGE;
   float ZGM_LIMIT;
   float ZGM_FLIP_X;
   float ZGM_FLIP_Y;
   float ZGM_DEBUG_X;
   float ZGM_DEBUG_Y;
   float ZGM_SHOW_STATE;
   // Screen shape. Same parameters, same text as crt-guest-advanced, so RetroArch shares their values with its passes.
   float warpX;
   float warpY;
   float c_shape;
   float csize;
   float bsize1;
   float sborder;
} global;

#pragma parameter ZGM_ENABLE    "=== CRT glass glow, moving with the device (OFF/ON) ===" 1.0 0.0 1.0 1.0
#pragma parameter ZGM_INTENSITY "      Glow strength (how far it pulls toward white)" 0.08 0.0 1.0 0.01
#pragma parameter ZGM_SIZE      "      Glow spread (screen heights)" 0.25 0.05 1.0 0.01
#pragma parameter ZGM_LIGHT_X   "      Resting position X (0 = left, 1 = right)" 0.35 -0.5 1.5 0.01
#pragma parameter ZGM_LIGHT_Y   "      Resting position Y (0 = top, 1 = bottom)" 0.35 -0.5 1.5 0.01
#pragma parameter ZGM_WINDOW    "      Window-shaped instead of a plain glow" 0.0 0.0 1.0 0.1
#pragma parameter ZGM_WARM      "      Warm tint" 0.25 0.0 1.0 0.05
#pragma parameter ZGM_RIM       "      Glass edge sheen" 0.20 0.0 2.0 0.05
#pragma parameter ZGM_LIFT      "      Black lift from room light" 0.004 0.0 0.05 0.001
#pragma parameter ZGM_DITHER    "      Dither (hides banding in the gradient)" 1.0 0.0 2.0 0.05
#pragma parameter ZGM_TILT_GAIN "== MOTION == Tilt (accelerometer) gain" 1.0 0.0 4.0 0.05
#pragma parameter ZGM_YAW_GAIN  "      Turn (gyroscope) gain" 1.0 0.0 4.0 0.05
#pragma parameter ZGM_RANGE     "      Slide per radian (screen widths)" 0.60 0.1 4.0 0.05
#pragma parameter ZGM_LIMIT     "      Furthest it may slide" 0.40 0.05 1.5 0.01
#pragma parameter ZGM_FLIP_X    "      Invert horizontal slide" 0.0 0.0 1.0 1.0
#pragma parameter ZGM_FLIP_Y    "      Invert vertical slide" 0.0 0.0 1.0 1.0
#pragma parameter ZGM_DEBUG_X   "      Test: turn the glass normal sideways (radians)" 0.0 -0.6 0.6 0.02
#pragma parameter ZGM_DEBUG_Y   "      Test: turn the glass normal up/down (radians)" 0.0 -0.6 0.6 0.02
#pragma parameter ZGM_SHOW_STATE "      Test: draw a bar for the gyro yaw state" 0.0 0.0 1.0 1.0

// Declared exactly as in crt-guest-advanced (crt-guest-advanced.slang / deconvergence.slang): the glow is kept inside the same curved
// screen outline, so nothing is drawn on the black corners the curvature leaves. With no curvature the outline is the whole viewport.
#pragma parameter warpX "          CurvatureX (default 0.03)" 0.0 0.0 0.25 0.01
#pragma parameter warpY "          CurvatureY (default 0.04)" 0.0 0.0 0.25 0.01
#pragma parameter c_shape "          Curvature Shape" 0.25 0.05 0.60 0.05
#pragma parameter csize "          Corner Size" 0.0 0.0 0.35 0.01
#pragma parameter bsize1 "          Border Size" 0.0 0.0 2.0 0.01
#pragma parameter sborder "          Border Intensity" 0.75 0.25 2.0 0.05

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

// Same warp and corner fade as crt-guest-advanced (deconvergence.slang): 1 inside the curved screen, 0 outside it.
vec2 warp(vec2 pos)
{
   pos = pos * 2.0 - 1.0;
   pos = mix(pos, vec2(pos.x * inversesqrt(1.0 - global.c_shape * pos.y * pos.y),
                       pos.y * inversesqrt(1.0 - global.c_shape * pos.x * pos.x)),
             vec2(global.warpX, global.warpY) / global.c_shape);
   return pos * 0.5 + 0.5;
}

float screenMask(vec2 uv)
{
   vec2 pos = abs(2.0 * (warp(uv) - 0.5));
   vec2 aspect = vec2(1.0, param.OutputSize.x / param.OutputSize.y);
   float b = global.bsize1 * 0.05 + 0.0005;
   pos.y = pos.y + b * (aspect.y - 1.0);
   vec2 crn = max(vec2(global.csize), 2.0 * b + 0.0015);
   vec2 cp = max(pos - (1.0 - crn * aspect), 0.0) / aspect;
   float cd = sqrt(dot(cp, cp));
   pos = max(pos, 1.0 - crn + cd);
   float res = mix(1.0, 0.0, smoothstep(1.0 - b, 1.0, sqrt(max(pos.x, pos.y))));
   return pow(res, global.sborder);
}

// Interleaved gradient noise (Jimenez), two samples apart: triangular-distributed, -1..1, one value per colour channel.
float ign(vec2 p)
{
   return fract(52.9829189 * fract(dot(p, vec2(0.06711056, 0.00583715))));
}

vec3 triangularDither(vec2 p)
{
   return vec3(ign(p) - ign(p + vec2(5.588238, 11.17)),
               ign(p + vec2(23.0, 7.0)) - ign(p + vec2(31.0, 19.0)),
               ign(p + vec2(47.0, 3.0)) - ign(p + vec2(61.0, 29.0)));
}

// Signed distance to a rounded box centred on the origin.
float roundBox(vec2 p, vec2 halfSize, float r)
{
   vec2 q = abs(p) - halfSize + r;
   return length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - r;
}

void main()
{
   vec4 s = texture(Source, vTexCoord);
   vec3 col = s.rgb;

   if (global.ZGM_ENABLE > 0.5)
   {
      // How far the glass normal has turned, in screen axes (x right, y up), radians.
      vec2 turn = vec2(global.ZGM_DEBUG_X, global.ZGM_DEBUG_Y);

#ifdef _HAS_SENSOR_UNIFORMS
      vec3 a = global.Accelerometer;
      vec3 r = global.AccelerometerRest;
      if (length(a) > 0.3)
      {
         vec3 au = normalize(a);
         vec3 ru = (length(r) > 0.3) ? normalize(r) : au;
         // Rotation of the device since the rest pose, as far as gravity can tell: a' x r.
         vec3 d = cross(au, ru);
         turn += global.ZGM_TILT_GAIN * vec2(d.y, -d.x);
         // Yaw about the gravity axis, from the gyroscope state carried in alpha.
         vec3 down = -au;
         turn += global.ZGM_YAW_GAIN * s.a * vec2(down.y, -down.x);
      }
#endif

      // The glow slides against the turn. Convert to texture space (y down).
      vec2 shift = -turn * global.ZGM_RANGE;
      shift = clamp(shift, vec2(-global.ZGM_LIMIT), vec2(global.ZGM_LIMIT));
      shift.y = -shift.y;
      if (global.ZGM_FLIP_X > 0.5) shift.x = -shift.x;
      if (global.ZGM_FLIP_Y > 0.5) shift.y = -shift.y;

      float aspect = param.OutputSize.x / param.OutputSize.y;
      vec2 p = (vTexCoord - (vec2(global.ZGM_LIGHT_X, global.ZGM_LIGHT_Y) + shift)) * vec2(aspect, 1.0);

      // Plain glow: a wide gaussian. Optional window: rounded box with two frame bars, blended in with ZGM_WINDOW.
      float sigma = global.ZGM_SIZE;
      float glow = exp(-dot(p, p) / (2.0 * sigma * sigma));

      vec2 halfSize = vec2(global.ZGM_SIZE * 0.85, global.ZGM_SIZE * 0.6) * 0.8;
      float sdf = roundBox(p, halfSize, min(halfSize.x, halfSize.y) * 0.25);
      float win = 1.0 - smoothstep(-0.035, 0.035, sdf);
      float bars = max(1.0 - smoothstep(0.004, 0.016, abs(p.x)), 1.0 - smoothstep(0.004, 0.016, abs(p.y)));
      win *= 1.0 - 0.6 * bars;
      float refl = mix(glow, win + 0.35 * glow, global.ZGM_WINDOW);

      // Glass reflects more toward the rim, where it curves away from the eye.
      vec2 c = (vTexCoord - 0.5) * 2.0;
      float rim = pow(clamp(dot(c, c) * 0.5, 0.0, 1.0), 2.0) * global.ZGM_RIM;

      vec3 tint = mix(vec3(1.0), vec3(1.0, 0.90, 0.74), global.ZGM_WARM);
      float inside = screenMask(vTexCoord);
      // Like glare.slang: the picture is pulled toward the light's colour by the glow, so bright pixels stay bright and black rises.
      float k = inside * global.ZGM_INTENSITY * (refl * (1.0 + rim) + rim * 0.5);
      col = mix(col, tint, clamp(k, 0.0, 0.85)) + inside * tint * global.ZGM_LIFT;
      col += inside * triangularDither(gl_FragCoord.xy) * (global.ZGM_DITHER / 255.0);
   }

   if (global.ZGM_SHOW_STATE > 0.5)
   {
      // yaw state carried in alpha, +-1 rad; green = positive, red = negative
      vec2 px = vTexCoord * param.OutputSize.xy;
      if (px.y > 20.0 && px.y < 44.0 && px.x > 20.0 && px.x < 420.0)
      {
         float mid = 220.0, v = clamp(s.a, -1.0, 1.0) * 200.0, x = px.x - mid;
         col = vec3(0.1);
         if ((v >= 0.0 && x >= 0.0 && x <= v) || (v < 0.0 && x <= 0.0 && x >= v)) col = (v >= 0.0) ? vec3(0.1, 0.9, 0.2) : vec3(0.95, 0.2, 0.2);
         if (abs(x) < 1.0) col = vec3(1.0);
      }
   }

   FragColor = vec4(min(col, vec3(1.0)), 1.0);
}
