#!/usr/bin/env python3
"""Generate the presets used on the AYN Thor (RetroArch aarch64, Vulkan driver) into presets/android/.

usage: build_android.py <local clone of libretro/slang-shaders> [out dir]

Layout it writes mirrors RetroArch's config dir, so the files can be pushed as they are:
  <out>/Nestopia/Nestopia.slangp           core level (NES + FDS look the same)
  <out>/Snes9x/Snes9x.slangp               core level (every SNES-family folder)
  <out>/Mupen64Plus-Next/Mupen64Plus-Next.slangp   needs the Angrylion RDP: GLideN64 runs on GL, which cannot take slang
  <out>/SwanStation/SwanStation.slangp
  <out>/Gambatte/gb.slangp, gbc.slangp     content-directory level (one core, two folders)
  <out>/mGBA/gba.slangp, gbc.slangp        gbc is only for Kirby Tilt 'n' Tumble (MBC7), which Gambatte cannot load
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_preset import build

SLANG = sys.argv[1]
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'presets', 'android')
DEV = '/data/user/0/com.retroarch.aarch64/shaders/shaders_slang'
MOT = '/storage/emulated/0/RetroArch/shaders/zeedif'

# The user's own NES preset (crt-guest-advanced, composite) is the starting point for every CRT console. Only the mask changed:
# on a ~320 ppi screen the Lottes triad mask (shadowMask 1) drowns the scanlines in a dot pattern, the CGWG mask (0) keeps the beam structure.
CRT_COMMON = ['CP=2.000000', 'BP=-18.000000', 'GAMMA_INPUT=2.450000', 'gamma_out=2.400000', 'scangamma=2.400000',
              'shadowMask=0.000000', 'maskstr=0.400000',
              # tube curvature, the numbers crt-lottes uses; set warpX/warpY to 0 for a flat screen, up to 0.25 for a rounder one
              'warpX=0.031000', 'warpY=0.041000', 'csize=0.020000']


def write(rel, text):
    path = os.path.normpath(os.path.join(OUT, rel))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)
    print('wrote', rel)


def crt(base, sets):
    return build(base, SLANG, DEV, MOT, sets=sets, motion=True)


# --- CRT consoles: composite for NES/SNES, a sharper non-NTSC chain for N64/PS1 ---
write('Nestopia/Nestopia.slangp', crt('crt/crt-guest-advanced-ntsc.slangp', CRT_COMMON + ['quality=1.000000', 'ntsc_phase=3.000000']))
write('Snes9x/Snes9x.slangp', crt('crt/crt-guest-advanced-ntsc.slangp', CRT_COMMON + ['quality=1.000000', 'ntsc_phase=1.000000']))
write('Mupen64Plus-Next/Mupen64Plus-Next.slangp', crt('crt/crt-guest-advanced.slangp', CRT_COMMON))
write('SwanStation/SwanStation.slangp', crt('crt/crt-guest-advanced.slangp', CRT_COMMON))

# --- Game Boy family ---
GB = build('handheld/gameboy.slangp', SLANG, DEV, None,
           sets=['color_toggle=1.000000', 'palette=2.000000', 'response_time=0.333000', 'integer_mode=1.000000'])
write('Gambatte/gb.slangp', GB)

# GBC: reflective LCD, so no white backlight look: subpixel LCD, "transparent" light pixels with their drop shadow (it shifts with
# the tilt), then sunlight shimmer. That is the library's own sunlight_shimmer-authentic_gbc_fast preset, rainbow band off.
GBC = build('presets/pixel_transparency/sunlight_shimmer-authentic_gbc_fast.slangp', SLANG, DEV, None,
            sets=['PT_RAINBOW_ENABLE=0.000000', 'PT_SHADOW_ENABLE=1.000000', 'PT_SHADOW_MOTION=1.000000',
                 'PT_PALETTE=1.000000', 'PT_POLARIZER=0.000000', 'PT_HIGHLIGHTS=0.000000'])   # warm backing, as in the author's frontlit preset
write('Gambatte/gbc.slangp', GBC)
write('mGBA/gbc.slangp', GBC)


# --- GBA: response time, BGR subpixel LCD (gamma 2.6 as nfp0 suggests for the AGB-001), Pokefan531's colour LUT after it, glare ---
def gba(darken, gamma):
    return '\n'.join([
        'shaders = "4"',
        'shader0 = "%s/motionblur/shaders/response-time.slang"' % DEV, 'filter_linear0 = "false"',
        'shader1 = "%s/handheld/shaders/lcd-cgwg/lcd-grid-v2.slang"' % DEV, 'filter_linear1 = "false"', 'scale_type1 = "viewport"',
        'shader2 = "%s/handheld/shaders/color/gba-color.slang"' % DEV, 'filter_linear2 = "false"',
        'shader3 = "%s/handheld/shaders/glare.slang"' % DEV, 'filter_linear3 = "false"', 'scale_type3 = "viewport"',
        'response_time = "0.333"',
        'RSUBPIX_R = "1"', 'RSUBPIX_G = "0"', 'RSUBPIX_B = "0"', 'GSUBPIX_R = "0"', 'GSUBPIX_G = "1"', 'GSUBPIX_B = "0"',
        'BSUBPIX_R = "0"', 'BSUBPIX_G = "0"', 'BSUBPIX_B = "1"',
        'gain = "1.0"', 'gamma = "%s"' % gamma, 'blacklevel = "0"', 'ambient = "0"', 'BGR = "1"',
        'profile = "1"', 'darken_screen = "%s"' % darken,
        # glare at its default strength washed out light-grey text on bright screens; keep it faint, neutral = how the console is held
        'GLARE_INTENSITY = "0.05"', 'REFLECT_INTENSITY = "0.035"', 'REFLECT_BIAS = "0.0"', 'ACCEL_RELATIVE = "1"', ''])


write('mGBA/gba.slangp', gba('0.5', '2.6'))   # the unlit AGB-001 look, for every game: the sources found no systematic palette change in later games
