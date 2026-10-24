#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Safely renumber VSE strip channels in a .blend.

Why this exists: assigning `strip.channel` while another strip already occupies
the target channel makes Blender silently PUSH the other strip to a different
frame range. No error, no warning -- the layer just disappears from the visible
range. Measured case: assigning channel 3 to a text strip moved the character
image sequence from frames 1..89 to 89..177.

Two-phase fix: park everything on high free channels, then land each strip on
its final channel.

Usage:
  blender --background --factory-startup --python relayout_channels.py -- \
      --blend D:/proj/file.blend --map "bg=1,elem=2,char=3,lyric_l=4,lyric_r=5,fg=6,sub=7"

Add --save to write the file, otherwise it only reports what would change.
"""
import argparse
import sys

import bpy


def parse():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--blend", required=True)
    ap.add_argument("--map", required=True, help='"name=ch,name=ch,..."')
    ap.add_argument("--park-base", type=int, default=20,
                    help="first free channel used for the parking pass")
    ap.add_argument("--save", action="store_true")
    return ap.parse_args(argv)


def main():
    a = parse()
    bpy.ops.wm.open_mainfile(filepath=a.blend)
    sc = bpy.context.scene
    strips = sc.sequence_editor.strips

    plan = {}
    for item in a.map.split(","):
        name, ch = item.split("=")
        plan[name.strip()] = int(ch)

    missing = [n for n in plan if n not in strips]
    if missing:
        sys.exit("unknown strip names: %s" % missing)

    before = {s.name: (s.channel, s.frame_start, s.frame_final_end) for s in strips}

    # phase 1: park
    for i, name in enumerate(plan):
        strips[name].channel = a.park_base + i
    # phase 2: land
    for name, ch in plan.items():
        strips[name].channel = ch

    moved = []
    for s in strips:
        if s.name in before:
            c0, f0, e0 = before[s.name]
            if (c0, f0, e0) != (s.channel, s.frame_start, s.frame_final_end):
                moved.append((s.name, c0, s.channel, f0, s.frame_start, e0, s.frame_final_end))

    print("\nresult:")
    for s in sorted(strips, key=lambda x: (x.channel, x.frame_start)):
        flag = ""
        if s.name in before:
            c0, f0, e0 = before[s.name]
            if f0 != s.frame_start or e0 != s.frame_final_end:
                flag = "   <-- FRAME RANGE CHANGED (was %d..%d)" % (f0, e0)
        print("  ch%-3d %-14s %-10s %d..%d%s" % (
            s.channel, s.name, s.type, s.frame_start, s.frame_final_end, flag))

    bad = [m for m in moved if m[3] != m[4] or m[5] != m[6]]
    if bad:
        print("\n!! %d strip(s) changed frame range -- the parking pass failed" % len(bad))
        return 1

    if a.save:
        for w in bpy.data.workspaces:
            if w.sequencer_scene is None:
                w.sequencer_scene = sc
                print("  fixed workspace.sequencer_scene on", w.name)
        bpy.ops.wm.save_mainfile(filepath=a.blend)
        print("\nsaved", a.blend)
    else:
        print("\n(dry run -- pass --save to write)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
