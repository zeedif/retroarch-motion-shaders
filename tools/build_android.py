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
import os, re, sys
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


# --- Game Boy family ---
# The shadow passes come from tools/patch_handheld.py (rest-relative tilt, more travel); their output dir is MOT/handheld-motion.
HM = MOT + '/handheld-motion'


def patched(text):
    text = text.replace(DEV + '/handheld/shaders/gameboy/shader-files/', HM + '/gameboy/')
    return text.replace(DEV + '/handheld/shaders/pixel_transparency/', HM + '/pixel_transparency/')


# --- sunlight shimmer (libretro's handheld/pixel_transparency): glare + rainbow shimmer that move with the console's tilt ---
# Its first input is a texture named Pixel_Transparency, which only the real pixel_transparency pass makes; everywhere else shaders/pt-passthrough.slang
# stands in for it. CRT presets do not carry it: their own glass pass is the light, and the shimmer's rainbow is a Game Boy Color thing.
LIGHT_REST = 0.35   # where every light rests (x and y, from the top left): between the middle and the top-left corner
# Light strength 0.08 (the library's 0.15 looks like a lamp in front of the screen). Light travel: PT_LIGHT_RANGE 0.20 gives 0.2 of the screen for 20 degrees
# of tilt (ZGM_TILT_FULL), the same as the CRT glass (ZGM_RANGE 0.6 per radian) and the GBA glare (LIGHT_RANGE 0.6 of sin(tilt)).
SHIMMER_LIGHT = ['PT_LIGHT_X=%.2f' % LIGHT_REST, 'PT_LIGHT_Y=%.2f' % LIGHT_REST, 'ZGM_TILT_FULL=20.0',
                 'PT_GLARE_INTENSITY=0.08', 'PT_LIGHT_RANGE=0.20']


def shimmer(text, on, rainbow, glare):
    n = int(re.search(r'^shaders = "(\d+)"', text, re.M).group(1))
    text = re.sub(r'^shaders = "\d+"', 'shaders = "%d"' % (n + 3), text, count=1, flags=re.M)
    pt = HM + '/pixel_transparency/'
    lines = ['shader%d = "%s/shaders/pt-passthrough.slang"' % (n, MOT), 'filter_linear%d = "false"' % n, 'scale_type%d = "viewport"' % n,
             'float_framebuffer%d = "true"' % n,
             'shader%d = "%sfilm_noise_cache.slang"' % (n + 1, pt), 'filter_linear%d = "false"' % (n + 1), 'scale_type%d = "absolute"' % (n + 1),
             'scale_x%d = "128"' % (n + 1), 'scale_y%d = "128"' % (n + 1),
             'shader%d = "%ssunlight_shimmer.slang"' % (n + 2, pt), 'filter_linear%d = "false"' % (n + 2), 'scale_type%d = "viewport"' % (n + 2),
             'PT_SUNLIGHT_ENABLE = "%d"' % on, 'PT_RAINBOW_ENABLE = "%d"' % rainbow, 'PT_GLARE_ENABLE = "%d"' % glare]
    lines += ['%s = "%s"' % tuple(kv.split('=', 1)) for kv in SHIMMER_LIGHT]
    return text + '\n'.join(lines) + '\n'


# --- CRT consoles: composite for NES/SNES, a sharper non-NTSC chain for N64/PS1 ---
write('Nestopia/Nestopia.slangp', crt('crt/crt-guest-advanced-ntsc.slangp', CRT_COMMON + ['quality=1.000000', 'ntsc_phase=3.000000']))
write('Snes9x/Snes9x.slangp', crt('crt/crt-guest-advanced-ntsc.slangp', CRT_COMMON + ['quality=1.000000', 'ntsc_phase=1.000000']))
write('Mupen64Plus-Next/Mupen64Plus-Next.slangp', crt('crt/crt-guest-advanced.slangp', CRT_COMMON))
write('SwanStation/SwanStation.slangp', crt('crt/crt-guest-advanced.slangp', CRT_COMMON))

# Shadow look and reach are the library's (its largest offset was 2.0 + 2.5 = 4.5 units); how the offset follows the console is the physical lamp model of
# tools/patch_handheld.py: the resting offset comes from the lamp and the orientation of gravity (so no fixed X/Y offset), and it can swing both ways
# (4.6 units at most either way). ZGM_TILT_FULL: a tilt of that many degrees counts as a quarter turn of the light.
# The sunlight shimmer is in the chain but off until it is switched on in the shader menu.
SHADOW = 'shadow_offset_x=0.0', 'shadow_offset_y=0.0', 'shadow_max_offset=4.6'
SHADOW_PT = 'PT_SHADOW_MOTION_X=0.0', 'PT_SHADOW_MOTION_Y=0.0', 'PT_SHADOW_MAX_OFFSET=4.6'
GB = shimmer(patched(build('handheld/gameboy.slangp', SLANG, DEV, None,
                           sets=['color_toggle=1.000000', 'palette=2.000000', 'response_time=0.333000', 'integer_mode=1.000000',
                                 'ZGM_TILT_FULL=20.0', *SHADOW])), 0, 0, 1)
write('Gambatte/gb.slangp', GB)

# GBC: reflective LCD, so no white backlight look: subpixel LCD, then "transparent" light pixels with their drop shadow (it shifts with the
# tilt). The library's sunlight_shimmer-authentic_gbc_fast chain; the shimmer itself starts off, with only its glare once switched on.
GBC = patched(build('presets/pixel_transparency/sunlight_shimmer-authentic_gbc_fast.slangp', SLANG, DEV, None,
                    sets=['PT_SHADOW_ENABLE=1.000000', 'PT_SHADOW_MOTION=1.000000',
                          'PT_PALETTE=1.000000', 'PT_POLARIZER=0.000000', 'PT_HIGHLIGHTS=0.000000',   # warm backing, as in the author's frontlit preset
                          'PT_SUNLIGHT_ENABLE=0', 'PT_RAINBOW_ENABLE=0', 'PT_GLARE_ENABLE=1', *SHADOW_PT] + SHIMMER_LIGHT))
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
        'GLARE_INTENSITY = "0.05"', 'REFLECT_INTENSITY = "0.035"', 'REFLECT_BIAS = "0.0"', 'ACCEL_RELATIVE = "1"',
        'LIGHT_X = "%.2f"' % LIGHT_REST, 'LIGHT_Y = "%.2f"' % LIGHT_REST, ''])


write('mGBA/gba.slangp', shimmer(gba('0.5', '2.6'), 0, 0, 1))   # the unlit AGB-001 look, for every game: the sources found no systematic palette change in later games
