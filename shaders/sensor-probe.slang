#version 450

/*
   Sensor probe
   Diagnostic last pass: draws RetroArch's motion uniforms as bars on top of the picture.
   Rows, top to bottom: Gyroscope (rad/s), Accelerometer (g), AccelerometerRest (g).
   Columns: X, Y, Z. Green = positive, red = negative. A white tick marks zero.
   Needs a RetroArch build with the Gyroscope/Accelerometer/AccelerometerRest uniforms (nightly after 2026-03) and
   Settings > Input > "Auxiliary Sensor Input" on.
   License: CC0 / public domain.
*/

layout(push_constant) uniform Push
{
   vec4 SourceSize;
   vec4 OutputSize;
   float PROBE_ENABLE;
   float GYRO_RANGE;
   float ACCEL_RANGE;
   float PROBE_SIZE;
} param;

#pragma parameter PROBE_ENABLE "Sensor probe (OFF/ON)" 1.0 0.0 1.0 1.0
#pragma parameter GYRO_RANGE   "Gyroscope full scale (rad/s)" 6.0 0.5 20.0 0.5
#pragma parameter ACCEL_RANGE  "Accelerometer full scale (g)" 1.5 0.5 8.0 0.25
#pragma parameter PROBE_SIZE   "Probe size" 1.0 0.5 3.0 0.25

layout(std140, set = 0, binding = 0) uniform UBO
{
   mat4 MVP;
#ifdef _HAS_SENSOR_UNIFORMS
   vec3 Gyroscope;
   vec3 Accelerometer;
   vec3 AccelerometerRest;
#endif
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

// One bar cell: returns the colour to draw (alpha in .a) for pixel p (in px) inside a cell of size cs, for value v in [-1, 1].
vec4 bar(vec2 p, vec2 cs, float v)
{
   if (p.x < 0.0 || p.y < 0.0 || p.x >= cs.x || p.y >= cs.y)
      return vec4(0.0);
   float mid = cs.x * 0.5;
   vec4 c = vec4(0.0, 0.0, 0.0, 0.6);                 // dark backing
   float len = clamp(abs(v), 0.0, 1.0) * mid;
   if (p.y > cs.y * 0.2 && p.y < cs.y * 0.8)
   {
      if (v >= 0.0 && p.x >= mid && p.x <= mid + len) c = vec4(0.1, 0.9, 0.2, 1.0);
      if (v <  0.0 && p.x <= mid && p.x >= mid - len) c = vec4(0.95, 0.2, 0.2, 1.0);
   }
   if (abs(p.x - mid) < 1.0) c = vec4(1.0, 1.0, 1.0, 1.0);
   return c;
}

void main()
{
   vec4 base = texture(Source, vTexCoord);
   vec3 col = base.rgb;

   if (param.PROBE_ENABLE > 0.5)
   {
      vec2 px = vTexCoord * param.OutputSize.xy;
      vec2 cs = vec2(120.0, 26.0) * param.PROBE_SIZE;
      vec2 origin = vec2(16.0, 16.0);

      vec3 g = vec3(0.0), a = vec3(0.0), r = vec3(0.0);
#ifdef _HAS_SENSOR_UNIFORMS
      g = global.Gyroscope / param.GYRO_RANGE;
      a = global.Accelerometer / param.ACCEL_RANGE;
      r = global.AccelerometerRest / param.ACCEL_RANGE;
#endif
      for (int row = 0; row < 3; row++)
      {
         for (int c = 0; c < 3; c++)
         {
            vec3 src = (row == 0) ? g : ((row == 1) ? a : r);
            float v = (c == 0) ? src.x : ((c == 1) ? src.y : src.z);
            vec2 p = px - (origin + vec2(float(c) * (cs.x + 6.0), float(row) * (cs.y + 6.0)));
            vec4 b = bar(p, cs, v);
            col = mix(col, b.rgb, b.a);
         }
      }
   }

   FragColor = vec4(col, base.a);
}
