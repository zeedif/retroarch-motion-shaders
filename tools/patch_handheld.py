#!/usr/bin/env python3
"""Make motion-aware copies of three libretro handheld shaders (the Game Boy dot-matrix pass 4, Pixel Transparency and Sunlight Shimmer).

Why: they turn the accelerometer into a shadow offset or a light position with the gravity direction normalised and taken as it is. Held
upright in landscape that vector is almost constant (pitching the console only changes it as cos of the angle), and the whole shadow travel
is 2.5 units, about 3.5 px on a 1080p screen, so nothing visibly follows the console. Here the shadow and the light follow the change of tilt
since the rest pose RetroArch captured (AccelerometerRest), with a full-scale angle you can set, and a test input for checking it. The
shadow's look and travel are the library's own.

The library's shaders keep their own license (GPL-3); nothing of them is stored in this repository: this script rewrites copies on your machine.

usage: patch_handheld.py <local clone of libretro/slang-shaders> <out dir>
  writes <out>/gameboy/*   (copy of handheld/shaders/gameboy/shader-files, gb-pass4 patched)
         <out>/pixel_transparency/*   (copy of handheld/shaders/pixel_transparency, pixel_transparency.slang and sunlight_shimmer.slang patched)

Parameters added: ZGM_TILT_FULL (degrees of tilt for the full travel of the shadow or light, 30), ZGM_TEST_X / ZGM_TEST_Y (pretend the console is
tilted, -1..1, 0 = off), ZGM_SHOW_TILT (shadow passes only: draws the tilt vector in a corner box, a red dot, x right, y down). A parameter that
two passes of one chain declare must read the same in both, or RetroArch refuses the whole preset: keep the texts identical.
"""
import os, shutil, sys

REST_FN = '''
// Tilt since the rest pose, as shadow-offset units (-1..1, texture axes: x right, y down). A shadow falls on the side the glass normal turns to.
vec2 restRelativeTilt(vec3 a, vec3 r, float fullDegrees) {
    if (length(a) < 0.3) return vec2(0.0);
    vec3 au = normalize(a);
    vec3 ru = (length(r) > 0.3) ? normalize(r) : au;
    vec3 d = cross(au, ru);
    return clamp(vec2(d.y, d.x) / sin(radians(fullDegrees)), vec2(-1.0), vec2(1.0));
}
'''


def load(path):
    return open(path, encoding='utf-8', newline='').read().replace('\r\n', '\n')


def sub(text, old, new, label):
    assert text.count(old) == 1, '%s: expected exactly one match, found %d' % (label, text.count(old))
    return text.replace(old, new)


def patch_gb_pass4(t):
    t = sub(t, '#include "gb-params.inc"',
            '#include "gb-params.inc"\n'
            '#pragma parameter ZGM_TILT_FULL "Motion: tilt that gives the full travel (degrees)" 30.0 5.0 90.0 1.0\n'
            '#pragma parameter ZGM_TEST_X "Motion test: pretend the console is tilted right (-1..1)" 0.0 -1.0 1.0 0.05\n'
            '#pragma parameter ZGM_TEST_Y "Motion test: pretend the console is tilted down (-1..1)" 0.0 -1.0 1.0 0.05\n'
            '#pragma parameter ZGM_SHOW_TILT "Motion test: draw the tilt vector in the corner" 0.0 0.0 1.0 1.0', 'gb include')
    t = sub(t, 'float shadow_max_offset;\n} registers;',
            'float shadow_max_offset;\n\tfloat ZGM_TILT_FULL;\n\tfloat ZGM_TEST_X;\n\tfloat ZGM_TEST_Y;\n\tfloat ZGM_SHOW_TILT;\n} registers;', 'gb push')
    t = sub(t, 'layout(location = 2) out vec2 shadow_offset;', 'layout(location = 2) out vec2 shadow_offset;\nlayout(location = 3) out vec2 zgm_tilt;', 'gb vs out')
    t = sub(t, '    return vec2(-dir.x, dir.y);\n}\n', '    return vec2(-dir.x, dir.y);\n}\n' + REST_FN.replace('fullDegrees', 'fullDegrees'), 'gb fn')
    t = sub(t, 'gravity = getOrientedTilt(accel);', 'gravity = restRelativeTilt(accel, global.AccelerometerRest, registers.ZGM_TILT_FULL);', 'gb call')
    t = sub(t, '    vec2 shadow_offset_px = vec2(registers.shadow_offset_x, registers.shadow_offset_y);',
            '    gravity = clamp(gravity + vec2(registers.ZGM_TEST_X, registers.ZGM_TEST_Y), vec2(-1.0), vec2(1.0));\n'
            '    zgm_tilt = gravity;\n'
            '    vec2 shadow_offset_px = vec2(registers.shadow_offset_x, registers.shadow_offset_y);', 'gb test')
    t = sub(t, 'layout(location = 2) in vec2 shadow_offset;', 'layout(location = 2) in vec2 shadow_offset;\nlayout(location = 3) in vec2 zgm_tilt;', 'gb fs in')
    t = sub(t, '    FragColor = out_color;\n}',
            '    if (registers.ZGM_SHOW_TILT > 0.5) {\n'
            '        vec2 q = vTexCoord * registers.OutputSize.xy - (registers.OutputSize.xy - vec2(80.0));\n'
            '        if (abs(q.x) < 62.0 && abs(q.y) < 62.0) {\n'
            '            out_color = vec4(0.0, 0.0, 0.0, 1.0);\n'
            '            if (abs(q.x) < 1.0 || abs(q.y) < 1.0) out_color.rgb = vec3(0.35);\n'
            '            vec2 dp = q - zgm_tilt * 55.0;\n'
            '            if (dot(dp, dp) < 25.0) out_color = vec4(1.0, 0.2, 0.2, 1.0);\n'
            '        }\n'
            '    }\n'
            '    FragColor = out_color;\n}', 'gb hud')
    return t


def patch_pt(t):
    t = sub(t, '#pragma name Pixel_Transparency',
            '#pragma name Pixel_Transparency\n'
            '#pragma parameter ZGM_TILT_FULL "Motion: tilt that gives the full travel (degrees)" 30.0 5.0 90.0 1.0\n'
            '#pragma parameter ZGM_TEST_X "Motion test: pretend the console is tilted right (-1..1)" 0.0 -1.0 1.0 0.05\n'
            '#pragma parameter ZGM_TEST_Y "Motion test: pretend the console is tilted down (-1..1)" 0.0 -1.0 1.0 0.05\n'
            '#pragma parameter ZGM_SHOW_TILT "Motion test: draw the tilt vector in the corner" 0.0 0.0 1.0 1.0', 'pt pragma')
    t = sub(t, 'float PT_SHADOW_EDGE_ENABLE;\n} global;',
            'float PT_SHADOW_EDGE_ENABLE;\n    float ZGM_TILT_FULL;\n    float ZGM_TEST_X;\n    float ZGM_TEST_Y;\n    float ZGM_SHOW_TILT;\n} global;', 'pt ubo')
    t = sub(t, 'layout(location = 3) out vec2 shadow_offset_raw;', 'layout(location = 3) out vec2 shadow_offset_raw;\nlayout(location = 4) out vec2 zgm_tilt;', 'pt vs out')
    t = sub(t, '    return vec2(-dir.x, dir.y);\n}\n', '    return vec2(-dir.x, dir.y);\n}\n' + REST_FN, 'pt fn')
    t = sub(t, 'gravity = getOrientedTilt(accel);', 'gravity = restRelativeTilt(accel, global.AccelerometerRest, global.ZGM_TILT_FULL);', 'pt call')
    t = sub(t, '\n\n    // Shadow offset: motion or static.',
            '\n    gravity = clamp(gravity + vec2(global.ZGM_TEST_X, global.ZGM_TEST_Y), vec2(-1.0), vec2(1.0));\n'
            '    zgm_tilt = gravity;\n\n    // Shadow offset: motion or static.', 'pt test')
    t = sub(t, 'layout(location = 3) in vec2 shadow_offset_raw;', 'layout(location = 3) in vec2 shadow_offset_raw;\nlayout(location = 4) in vec2 zgm_tilt;', 'pt fs in')
    t = sub(t, 'layout(set = 0, binding = 3) uniform sampler2D Original;\n',
            'layout(set = 0, binding = 3) uniform sampler2D Original;\n\n'
            'vec4 zgm_hud(vec4 c) {\n'
            '    if (global.ZGM_SHOW_TILT > 0.5) {\n'
            '        vec2 q = vTexCoord * param.OutputSize.xy - (param.OutputSize.xy - vec2(80.0));\n'
            '        if (abs(q.x) < 62.0 && abs(q.y) < 62.0) {\n'
            '            c = vec4(0.0, 0.0, 0.0, 1.0);\n'
            '            if (abs(q.x) < 1.0 || abs(q.y) < 1.0) c.rgb = vec3(0.35);\n'
            '            vec2 dp = q - zgm_tilt * 55.0;\n'
            '            if (dot(dp, dp) < 25.0) c = vec4(1.0, 0.2, 0.2, 1.0);\n'
            '        }\n'
            '    }\n'
            '    return c;\n'
            '}\n', 'pt hud fn')
    assert t.count('FragColor = output_color;') == 2, 'pt FragColor count %d' % t.count('FragColor = output_color;')
    t = t.replace('FragColor = output_color;', 'FragColor = zgm_hud(output_color);')
    return t


def patch_shimmer(t):
    """sunlight_shimmer: the light (glare, rainbow, reflection) sits at PT_LIGHT_X/Y when the console is held at its rest pose and moves with the
    change of tilt; the library moves it by the absolute gravity direction instead, which hardly changes when the console is held upright."""
    t = sub(t, '#pragma parameter PT_LIGHT_Y',
            '#pragma parameter ZGM_TILT_FULL "Motion: tilt that gives the full travel (degrees)" 30.0 5.0 90.0 1.0\n'
            '#pragma parameter ZGM_TEST_X "Motion test: pretend the console is tilted right (-1..1)" 0.0 -1.0 1.0 0.05\n'
            '#pragma parameter ZGM_TEST_Y "Motion test: pretend the console is tilted down (-1..1)" 0.0 -1.0 1.0 0.05\n'
            '#pragma parameter PT_LIGHT_Y', 'sh pragma')
    t = sub(t, 'float PT_LIGHT_HEIGHT;\n} global;',
            'float PT_LIGHT_HEIGHT;\n    float ZGM_TILT_FULL;\n    float ZGM_TEST_X;\n    float ZGM_TEST_Y;\n} global;', 'sh ubo')
    old = ('            vec2 gravity = clamp(vec2(-accel.x, accel.y) / magnitude * param.PT_ACCEL_SENSITIVITY,\n'
           '                                 vec2(-1.0), vec2(1.0));')
    new = ('            vec3 au = accel / magnitude;\n'
           '            vec3 r = global.AccelerometerRest;\n'
           '            vec3 ru = (length(r) > 0.3) ? normalize(r) : au;\n'
           '            vec3 d = cross(au, ru);\n'
           '            vec2 gravity = clamp(vec2(d.y, d.x) / sin(radians(global.ZGM_TILT_FULL)) * param.PT_ACCEL_SENSITIVITY, vec2(-1.0), vec2(1.0));')
    t = sub(t, old, new, 'sh gravity')
    t = sub(t, '    #endif\n}\n\n#pragma stage fragment',
            '    #endif\n    light_pos += vec2(global.ZGM_TEST_X, -global.ZGM_TEST_Y) * param.PT_LIGHT_RANGE;\n}\n\n#pragma stage fragment', 'sh test')
    return t


def main():
    root, out = sys.argv[1], sys.argv[2]
    gb_src = os.path.join(root, 'handheld', 'shaders', 'gameboy', 'shader-files')
    pt_src = os.path.join(root, 'handheld', 'shaders', 'pixel_transparency')
    for src, name, target, fn in ((gb_src, 'gameboy', 'gb-pass4.slang', patch_gb_pass4), (pt_src, 'pixel_transparency', 'pixel_transparency.slang', patch_pt)):
        dst = os.path.join(out, name)
        if os.path.exists(dst):
            shutil.rmtree(dst)
        os.makedirs(dst)
        for f in os.listdir(src):
            p = os.path.join(src, f)
            if os.path.isfile(p):
                with open(os.path.join(dst, f), 'w', encoding='utf-8', newline='\n') as h:
                    h.write(load(p))
        todo = [(target, fn)] + ([('sunlight_shimmer.slang', patch_shimmer)] if name == 'pixel_transparency' else [])
        for tgt, f in todo:
            pth = os.path.join(dst, tgt)
            patched = f(load(pth))   # read before the file is reopened for writing
            with open(pth, 'w', encoding='utf-8', newline='\n') as h:
                h.write(patched)
            print('patched', os.path.join(name, tgt))


if __name__ == '__main__':
    main()
