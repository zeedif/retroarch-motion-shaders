#!/usr/bin/env python3
"""Build a RetroArch .slangp from a libretro preset, with parameter overrides and, optionally, the two motion passes
(motion-state + crt-glass-motion) appended.

The output lists every pass itself (RetroArch cannot append passes to a #reference'd preset) and uses absolute paths, so
it works wherever the files sit on the device.

  make_preset.py --base crt/crt-guest-advanced-ntsc.slangp --slang-root <local clone of libretro/slang-shaders> \
      --device-slang-root /data/user/0/com.retroarch.aarch64/shaders/shaders_slang \
      --device-motion-root /storage/emulated/0/RetroArch/shaders/zeedif \
      --set shadowMask=1 --set ntsc_phase=3 --motion --out nes.slangp

--set KEY=VALUE      parameter override (written as KEY = "VALUE"); repeat as needed
--set-from FILE      read KEY = "VALUE" lines (a user's saved parameter overrides) and apply them
--motion             append motion-state.slang + crt-glass-motion.slang
--motion-set K=V     same as --set, kept apart for readability

From Python: build(base, slang_root, device_slang_root, device_motion_root, sets, set_from, motion, motion_set) -> text
"""
import argparse, os, posixpath, re, sys


def parse(path):
    """Ordered (key, value) pairs of a preset, plus the target of one #reference if there is one."""
    items, ref = [], None
    for raw in open(path, encoding='utf-8', errors='replace').read().splitlines():
        line = raw.strip()
        if line.startswith('#reference'):
            ref = line.split(None, 1)[1].strip().strip('"')
            continue
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        items.append((k.strip(), v.split(' //')[0].strip().strip('"')))
    return items, ref


def build(base, slang_root, device_slang_root, device_motion_root=None, sets=(), set_from=(), motion=False, motion_set=()):
    base_rel = base.replace('\\', '/')
    items, ref = parse(os.path.join(slang_root, base_rel))
    if ref:  # a preset that only references another one: take the referenced passes, then our overrides on top
        ref_rel = posixpath.normpath(posixpath.join(posixpath.dirname(base_rel), ref))
        ref_items, _ = parse(os.path.join(slang_root, ref_rel))
        items = ref_items + items
        base_rel = ref_rel
    base_dir = posixpath.dirname(base_rel)

    d = dict(items)
    seen = set()
    order = [k for k, _ in items if not (k in seen or seen.add(k))]

    n = int(d['shaders'])
    path_keys = {k for k in d if re.fullmatch(r'shader\d+', k)}
    tex_names = [t for t in d.get('textures', '').split(';') if t]
    path_keys |= {t for t in tex_names if t in d}
    for k in path_keys:
        d[k] = posixpath.join(device_slang_root, posixpath.normpath(posixpath.join(base_dir, d[k])))

    overrides = {}
    for f in set_from:
        for raw in open(f, encoding='utf-8').read().splitlines():
            raw = raw.strip()
            if raw and not raw.startswith('#') and '=' in raw:
                k, v = raw.split('=', 1)
                overrides[k.strip()] = v.strip().strip('"')
    for kv in list(sets) + list(motion_set):
        k, v = kv.split('=', 1)
        overrides[k] = v
    for k, v in overrides.items():
        if k not in d:
            order.append(k)
        d[k] = v

    if motion:
        if not device_motion_root:
            raise SystemExit('motion needs device_motion_root')
        m0, m1 = n, n + 1
        d['shaders'] = str(n + 2)
        spec = [
            ('shader%d' % m0, posixpath.join(device_motion_root, 'shaders/motion-state.slang')),
            ('alias%d' % m0, 'MOTION'),
            ('filter_linear%d' % m0, 'false'),
            ('float_framebuffer%d' % m0, 'true'),
            ('scale_type%d' % m0, 'viewport'),
            ('scale%d' % m0, '1.0'),
            ('shader%d' % m1, posixpath.join(device_motion_root, 'shaders/crt-glass-motion.slang')),
            ('filter_linear%d' % m1, 'false'),
            ('scale_type%d' % m1, 'viewport'),
            ('scale%d' % m1, '1.0'),
        ]
        for k, v in spec:
            if k not in d:
                order.append(k)
            d[k] = v

    keys = ['shaders'] + [k for k in order if k != 'shaders']
    return ''.join('%s = "%s"\n' % (k, d[k]) for k in keys)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', required=True, help='preset path relative to --slang-root')
    ap.add_argument('--slang-root', required=True)
    ap.add_argument('--device-slang-root', required=True)
    ap.add_argument('--device-motion-root')
    ap.add_argument('--set', action='append', default=[])
    ap.add_argument('--set-from', action='append', default=[])
    ap.add_argument('--motion', action='store_true')
    ap.add_argument('--motion-set', action='append', default=[])
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    text = build(a.base, a.slang_root, a.device_slang_root, a.device_motion_root, a.set, a.set_from, a.motion, a.motion_set)
    with open(a.out, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)
    print('wrote %s' % a.out)


if __name__ == '__main__':
    main()
