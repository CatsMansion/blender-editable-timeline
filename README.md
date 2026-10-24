# blender-editable-timeline

An agent skill for the deliverable that is **not a video**: a Blender timeline the client opens, drags, retypes and saves themselves.

If the ask is "I want to adjust the captions / positions / sizes myself", rendering them an MP4 answers the wrong question. Every tweak becomes another round trip through you. Hand them a project with native TEXT strips instead.

## What is hard about this

Blender 5.x's VSE has six traps that all fail silently — no exception, no warning, just a wrong result you notice three renders later:

| Trap | Symptom | In SKILL.md |
|---|---|---|
| channel reassignment | a layer vanishes; its frame range was silently shifted | §2.1 + `scripts/relayout_channels.py` |
| `color` dimensionality | `TextStrip.color` takes 4 floats, `ColorStrip.color` takes 3 — and the traceback points at the other assignment | §2.2 |
| `transform.offset_*` | units are pixels with `ky = −1`; hand-written deltas fling layers off-canvas | §2.3 (two-point calibration) |
| `workspace.sequencer_scene` | timeline is full but the editor renders **blank** — while headless renders work fine | §2.4 |
| view transform | default AgX double-grades already-graded footage | §2.5 |
| text editing | native text strips cannot be typed into in the viewport | §2.6 |

Plus the two delivery-side facts that decide whether the client can actually use it: `save_version` maxes out at **32** (not 64), and a launch shortcut must be a CRLF `.cmd` written as bytes — `printf` eats `\U` in `C:\Users`.

## The seam-free composite trick

A 1080×1920 character plate can be dropped into a 1920×1080 canvas **without matting**, when both share one exact background colour and every gradient/vignette is applied *after* the paste. SKILL.md §5 documents the two conditions and the BGR/RGB mistake that breaks it (canvas turns deep blue-purple, a visible rectangle appears around the character).

It also documents the *wrong* fix people reach for — recolouring background-coloured pixels — which leaves a hard rim (measured: 75.9 % of pixels touched, visible edge step). The right fix is a uniform per-channel offset of 1–2 units.

## Install

Copy the folder into your agent's skills directory. The script runs inside Blender:

```bash
blender --background --factory-startup --python scripts/relayout_channels.py -- \
  --blend D:/proj/file.blend --map "bg=1,elem=2,char=3,lyric_l=4,lyric_r=5,fg=6" --save
```

It does the two-phase renumber, then **verifies no strip changed its frame range** and reports the full channel table. Dry-run by default.

## What you still have to write by hand

The skill gives structure, not copy. You still owe the client:

- a 操控卡 that lists **five keys only** (`space`, arrow, click, `G`, `S`) — a full hotkey list is the same as no hotkey list
- a backup card with three recovery paths, from `.blend1` up to a full copy
- a written warning that the `bg/ char/ elem/` folders must not be renamed — strips reference them by absolute path

## Licence

MIT. See `LICENSE`.
