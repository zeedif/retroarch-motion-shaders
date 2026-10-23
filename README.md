# retroarch-motion-shaders

Slang shaders and presets for RetroArch on Android handhelds that use the new **gyroscope / accelerometer shader uniforms**
(`Gyroscope`, `Accelerometer`, `AccelerometerRest`). Built and tested on an AYN Thor (Snapdragon 8 Gen 2), RetroArch 1.22.2 nightly of
2026-10-23, Vulkan video driver.

The shaders are CC0. The presets only *reference* shaders from [libretro/slang-shaders](https://github.com/libretro/slang-shaders)
(crt-guest-advanced by guest.r, the Game Boy dot-matrix shader and Pixel Transparency by Matt Akins, authentic_gbc by fishku, gba-color by
Pokefan531, lcd-grid-v2 by cgwg, response-time by hunterk and others); nothing from them is copied here.

## What is in it

| File | What it does |
|---|---|
| `shaders/crt-glass-motion.slang` | Last pass for CRT presets: a faint glow of room light on the glass that slides with tilt and turn. Never moves or filters the picture, so integer-scaled pixels stay where they are. Kept inside the curved screen outline, using the same `warpX/warpY/c_shape/csize/bsize1/sborder` parameters as crt-guest-advanced (RetroArch shares them between passes); that match holds while guest's own integer-scaling (`IOS`), overscan and raster-bloom options stay at 0. Off with `ZGM_ENABLE`, or strength 0. |
| `shaders/motion-state.slang` | Keeps the device's yaw (turn about the gravity axis), integrated from the gyroscope and leaking back to zero, in the alpha channel of a pass that otherwise passes the picture through. Gravity cannot show yaw, so this is the only way a shader can use the gyroscope for it. |
| `shaders/sensor-probe.slang` | Diagnostic: draws the three sensor vectors as bars. |
| `presets/sensor-probe.slangp` | Preset for the probe. |
| `tools/make_preset.py` | Takes any libretro preset, resolves its paths, applies parameter overrides and appends the two motion passes. RetroArch cannot append passes to a `#reference` preset, so the result lists every pass. |
| `tools/build_android.py` | Builds the presets I use on the Thor into `presets/android/` (one folder per core, named as RetroArch's `config/` expects). |

## Using it on Android

1. Copy `shaders/` to `/storage/emulated/0/RetroArch/shaders/zeedif/shaders/`.
2. In RetroArch: **Settings > Input > Auxiliary Sensor Input** on, and **Sensor Orientation** set to the screen's rotation, not Auto.
   On a landscape handheld whose sensors sit in portrait (Thor) that is **90°**. Auto decides once, only after the device has been tilted
   30° from flat, so a shader or core can see portrait axes: the glow then moves sideways when you pitch the device.
3. Build presets with `python tools/build_android.py <clone of libretro/slang-shaders>` and copy `presets/android/<Core>/` to
   `/storage/emulated/0/RetroArch/config/<Core>/`. `<Core>.slangp` applies to the whole core, `<folder>.slangp` to games in that content folder.

Sensor values RetroArch hands to shaders: accelerometer in **g** (face-up and still: `Z = 1`), gyroscope in rad/s, both after the Sensor
Orientation remap of X/Y. `AccelerometerRest` is the average over ~30 frames after the sensors come on, so launch the game while holding the
device the way you will play.

## How the glow moves

On a convex tube the reflection sits where the glass normal bisects the light and the eye. The normal turns with the device, so the reflection
slides **against** the turn: tilt the top edge away from you and it slides down the glass, tilt it toward you and it slides up; turn the
device to its right and it slides left. Tilt is `cross(a, rest)` of the unit gravity vectors (works from any holding pose); yaw is the gyroscope
rate about the gravity axis, leaky-integrated (`ZGM_YAW_RETURN` seconds to settle). `ZGM_FLIP_X/Y` invert an axis.
`ZGM_DEBUG_X/Y` force a turn without moving the device; `ZGM_SHOW_STATE` draws the yaw bar.

## Checked, and not

On the Thor, through RetroArch's normal per-core preset lookup: the sensors reach the shader (probe: Z = +1 g, gyro 0, rest = current at rest),
the glow slides in the expected direction for forced turns, the leaky integrator reaches `rate x return time` for a simulated constant turn
(0.3 rad/s x 1.2 s gives 0.35 rad), the full presets render at 59.6 fps on N64 (Angrylion RDP) and PS1, and with default settings the four viewport corners of a curved N64 picture stay at 0 (before the outline mask the glow and black lift drew a visible rectangle over the corners the curvature leaves black).
**Not checked by moving the device**: the direction convention above comes from the geometry, not from a physical test; use
`ZGM_FLIP_X/Y` if your device disagrees. Requires a RetroArch build that has the motion uniforms (merged 2026-03); older builds ignore them
and the glow stays put.

## Presets built for the Thor

- **NES/FDS, SNES**: crt-guest-advanced with its composite NTSC chain, CGWG mask (the Lottes triad mask drowns the scanlines at ~320 ppi),
  tube curvature `warpX/warpY` (0 = flat), plus the two motion passes.
- **N64, PS1**: crt-guest-advanced (non-NTSC) with the same look. N64 needs the Angrylion RDP in Mupen64Plus-Next: GLideN64 runs on GL, where
  slang shaders do not apply.
- **Game Boy**: `handheld/gameboy.slangp` with the Pocket palette; its drop shadow already follows the accelerometer.
- **Game Boy Color**: the library's `sunlight_shimmer-authentic_gbc_fast` chain (subpixel LCD, transparent light pixels, shadow that follows tilt).
  A chain that leaves out `film_noise_cache.slang` is silently dropped by RetroArch and the picture comes out unfiltered.
- **GBA**: response time, BGR subpixel LCD (gamma 2.6), Pokefan531's colour LUT with darkening for the unlit AGB-001, faint glare. A lighter
  variant without the darkening exists for games first released in 2005 or later (listed locally in `tools/late_gba_games.txt`).
