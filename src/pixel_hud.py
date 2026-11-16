"""Heads-up-display layout for pixel-art Shorts.

Instead of a plain header and footer, every frame gets bordered pixel-font
boxes: a small tag ("FACT 2 OF 5"), the video's title as a big question box,
an optional stat bar with the key number, the channel handle, and an optional
animated gauge. Captions sit in a fixed box under the stat bar, so the scene
below stays clear.

Turned on per channel with "video_layout": "hud" in content/channel.json.

The HUD is drawn on its own 360x640 RGBA layer (HW x HH, shown at 3x on the
1080x1920 video), so text and boxes keep the same size and crispness however
finely the scene behind them is drawn (pixel_art.DETAIL).
"""
import math

import numpy as np

import pixel_art as pa

WHITE, YELLOW, ORANGE, BLACK = (245, 245, 240), (255, 214, 64), (255, 150, 40), (6, 8, 14)
RED, CYAN = (235, 70, 60), (120, 230, 240)
MARGIN = 14
HW, HH = 360, 640                 # HUD layer size
HUD_SCALE = 1080 // HW            # 3x on the final video
HPY, HPX = np.mgrid[0:HH, 0:HW]


def new_layer():
    """Empty RGBA HUD layer."""
    return np.zeros((HH, HW, 4), dtype=np.uint8)


def upscale_layer(layer):
    return layer.repeat(HUD_SCALE, axis=0).repeat(HUD_SCALE, axis=1)


def composite(big, layer):
    """Lay an RGBA HUD layer over a full-size (1080x1920) RGB frame. Only rows
    the HUD touches are blended, in integer maths, which keeps this fast."""
    rows = np.flatnonzero(layer[..., 3].any(axis=1))
    if rows.size == 0:
        return big
    out = big.copy()
    # Contiguous runs of HUD rows (top boxes, bottom boxes)
    breaks = np.flatnonzero(np.diff(rows) > 1)
    for seg in np.split(rows, breaks + 1):
        y0, y1 = seg[0], seg[-1] + 1
        part = layer[y0:y1].repeat(HUD_SCALE, axis=0).repeat(HUD_SCALE, axis=1)
        a = part[..., 3:4].astype(np.uint16)
        Y0, Y1 = y0 * HUD_SCALE, y1 * HUD_SCALE
        region = out[Y0:Y1].astype(np.uint16)
        out[Y0:Y1] = ((region * (255 - a) + part[..., :3].astype(np.uint16) * a) // 255).astype(np.uint8)
    return out


def _lines(text, scale, max_w):
    return pa._wrap(text.upper(), max(1, max_w // (6 * scale)))


def _line_mask(line, scale):
    char_w = 6 * scale
    w = max(1, len(line) * char_w - scale)
    m = np.zeros((7 * scale, w), dtype=bool)
    for ci, ch in enumerate(line):
        g = np.kron(pa.GLYPHS.get(ch, pa.GLYPHS[" "]), np.ones((scale, scale), dtype=bool))
        m[:, ci * char_w:ci * char_w + g.shape[1]] |= g
    return m


def text(layer, line, x, y, scale, color, center=False, shadow=True):
    """Draw one line of pixel text with its top-left (or top-centre) at x, y; returns its width."""
    m = _line_mask(line, scale)
    h, w = m.shape
    if center:
        x = int(x - w / 2)
    for dx, dy, col in (((scale // 2 or 1), (scale // 2 or 1), BLACK),) if shadow else ():
        _blit(layer, m, x + dx, y + dy, col)
    _blit(layer, m, x, y, color)
    return w


def _blit(layer, m, x, y, color):
    h, w = m.shape
    y0, x0 = max(0, y), max(0, x)
    y1, x1 = min(HH, y + h), min(HW, x + w)
    if y0 < y1 and x0 < x1:
        sub = m[y0 - y:y1 - y, x0 - x:x1 - x]
        layer[y0:y1, x0:x1][sub] = (*color, 255)


def box(layer, x0, y0, x1, y1, border, fill_alpha=0.82, width=2):
    """Dark see-through box with a solid pixel border."""
    x0, y0, x1, y1 = max(0, int(x0)), max(0, int(y0)), min(HW, int(x1)), min(HH, int(y1))
    if x0 >= x1 or y0 >= y1:
        return
    layer[y0:y1, x0:x1] = (*BLACK, int(fill_alpha * 255))
    edge = (*border, 255)
    layer[y0:y0 + width, x0:x1] = edge
    layer[y1 - width:y1, x0:x1] = edge
    layer[y0:y1, x0:x0 + width] = edge
    layer[y0:y1, x1 - width:x1] = edge


def title_layout(title):
    """Pick the biggest title size that fits in three lines."""
    inner = HW - 2 * MARGIN - 20
    for scale, most in ((4, 3), (3, 4), (2, 5)):
        lines = _lines(title, scale, inner)
        if len(lines) <= most:
            return scale, lines
    return 2, _lines(title, 2, inner)[:4]


def gauge(layer, t, spec, cx, cy, r=34):
    """Round dial whose needle sweeps up to the value, with a readout below."""
    value, top = float(spec.get("value", 0)), float(spec.get("max") or spec.get("value", 1) or 1)
    sweep = min(1.0, t / 1.2) ** 0.5
    wobble = 0.012 * math.sin(t * 9) if sweep >= 1 else 0
    frac = max(0.0, min(1.0, value / top * sweep + wobble))
    d = np.sqrt((HPX - cx) ** 2 + (HPY - cy) ** 2)
    layer[d <= r] = (14, 18, 30, 217)
    layer[(d <= r) & (d > r - 2)] = (*WHITE, 255)
    a0, a1 = math.radians(135), math.radians(405)          # dial runs clockwise from lower left
    for i in range(11):
        a = a0 + (a1 - a0) * i / 10
        for k in range(5 if i % 5 == 0 else 3):
            x, y = cx + math.cos(a) * (r - 4 - k), cy + math.sin(a) * (r - 4 - k)
            layer[int(y):int(y) + 1, int(x):int(x) + 1] = (*(RED if i >= 8 else WHITE), 255)
    a = a0 + (a1 - a0) * frac
    for k in range(int(r - 7)):
        x, y = cx + math.cos(a) * k, cy + math.sin(a) * k
        layer[int(y):int(y) + 2, int(x):int(x) + 2] = (*RED, 255)
    layer[cy - 2:cy + 3, cx - 2:cx + 3] = (*WHITE, 255)
    shown = value * sweep
    number = f"{shown:,.0f}" if value == int(value) else f"{shown:,.1f}"
    unit = str(spec.get("unit", ""))
    readout = f"{number} {unit}".strip()
    w = len(readout) * 12 + 12
    bx = int(min(cx - w // 2, HW - MARGIN - w))
    box(layer, bx, cy + r + 4, bx + w + 1, cy + r + 26, ORANGE, 0.85)
    text(layer, readout, bx + w // 2, cy + r + 9, 2, ORANGE, center=True, shadow=False)
    label = str(spec.get("label", "")).strip().upper()
    if label:
        w = len(label) * 12
        x = int(min(cx - w / 2, HW - MARGIN - w))
        text(layer, label, x, cy - r - 20, 2, CYAN)


# ------------------------------------------------- camera and lighting ----
def _blur(img, k):
    """Cheap box blur (float image), k pixels each way."""
    out = img.copy()
    for axis in (0, 1):
        c = np.cumsum(np.pad(out, [(k + 1, k) if a == axis else (0, 0) for a in range(3)], mode="edge"), axis=axis)
        hi = np.take(c, np.arange(2 * k + 1, c.shape[axis]), axis=axis)
        lo = np.take(c, np.arange(0, c.shape[axis] - 2 * k - 1), axis=axis)
        out = (hi - lo) / (2 * k + 1)
    return out


_VIGNETTE = None


# Words in a caption that point the camera at a body part, in priority order
PART_WORDS = [
    ("teeth", ("teeth", "tooth", "bite", "bites", "bit", "jaw", "jaws", "fang", "fangs", "chew", "crush", "crushed")),
    ("claw", ("claw", "claws", "sickle", "talon")),
    ("horns", ("horn", "horns")),
    ("frill", ("frill",)),
    ("plates", ("plate", "plates")),
    ("spikes", ("spike", "spikes", "thagomizer")),
    ("tusks", ("tusk", "tusks", "ivory")),
    ("trunk", ("trunk",)),
    ("eye", ("eye", "eyes", "see", "saw", "vision", "sight")),
    ("beak", ("beak",)),
    ("skull", ("skull",)),
    ("ribs", ("rib", "ribs")),
    ("head", ("head", "skull", "brain", "face", "mouth", "snout", "crest")),
    ("neck", ("neck", "necks")),
    ("arm", ("arm", "arms", "hand", "hands", "finger", "fingers")),
    ("arms", ("arm", "arms", "grasping")),
    ("wings", ("wing", "wings", "wingspan", "fly", "flew", "flight", "soar", "glide", "glided")),
    ("feathers", ("feather", "feathers", "feathered", "quill")),
    ("legs", ("leg", "legs", "run", "ran", "running", "walk", "walked", "stride", "speed", "fast")),
    ("feet", ("foot", "feet", "toe", "toes", "footprint", "footprints")),
    ("tail", ("tail", "tails")),
    ("fur", ("fur", "hair", "wool", "shaggy")),
    ("flippers", ("flipper", "flippers", "swim", "swam", "paddle")),
    ("insect", ("insect", "insects", "mosquito", "fly")),
    ("egg", ("egg", "eggs", "hatch", "hatched", "embryo", "embryos")),
    ("baby", ("baby", "babies", "young", "hatchling")),
    ("nest", ("nest", "nests")),
    ("crater", ("crater", "impact", "hit", "struck")),
    ("lava", ("lava", "eruption", "eruptions", "volcanic")),
    ("trilobite", ("trilobite", "trilobites")),
    ("wide", ("weigh", "weighed", "weight", "tonnes", "tons", "size", "big", "giant", "largest", "biggest", "long",
              "length", "tall", "height", "huge", "whole", "entire")),
]


def focus_parts(spec, t=0.0):
    """The named points available for a scene at time t."""
    parts = pa.FOCUS.get(spec.get("scene"))
    return parts(t) if callable(parts) else (parts or {})


def plan_shots(scenes, sentences):
    """Give every scene a camera shot. A sentence that mentions a body part
    the scene knows ("its teeth...") zooms in on that part; others cycle
    through push-in, wide and pan shots so consecutive clips look different.
    Explicit "focus" or "shot" keys in a script's scene are kept."""
    import re
    planned, cycle = [], ["push", "wide", "pan", "push"]
    for i, scene in enumerate(scenes):
        scene = dict(scene)
        words = set(re.findall(r"[a-z]+", (sentences[i] if i < len(sentences) else "").lower()))
        if "focus" not in scene and "shot" not in scene:
            parts = focus_parts(scene)
            recent = [p.get("focus") for p in planned[-2:]]
            for part, keys in PART_WORDS:
                if not words & set(keys):
                    continue
                if part == "wide" and parts:
                    scene["shot"] = "wide"          # size facts: show the whole animal
                    break
                if part in parts and recent != [part, part]:   # at most two close-ups of one part in a row
                    scene["focus"] = part
                    # The same part again: alternate close and closer so it isn't a repeat
                    if planned and planned[-1].get("focus") == part:
                        scene["zoom"] = 1.8 if planned[-1].get("zoom", 2.4) >= 2.4 else 2.9
                    break
            else:
                scene["shot"] = "wide" if i == len(scenes) - 1 else cycle[i % len(cycle)]
            if "focus" not in scene and "shot" not in scene:
                scene["shot"] = cycle[(i + 1) % len(cycle)]
            # Never the same kind of wide/pan/push shot twice in a row
            if "shot" in scene and planned and planned[-1].get("shot") == scene["shot"]:
                options = [c for c in ("pan", "push", "wide") if c != scene["shot"]]
                scene["shot"] = options[i % len(options)]
        planned.append(scene)
    return planned


def _ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def camera(frame, t, seed, spec=None, focus=0.578, target=0.703):
    """Frame the scene like a camera, below the text boxes (subject around
    `target` of the height). Shots: "focus" zooms in on a named body part,
    "wide" shows the whole scene, "pan" glides sideways, "push" (default)
    slowly pushes in with a gentle drift."""
    spec = spec or {}
    rng = np.random.default_rng(seed)
    k = pa.PH / 640
    tx, ty = 0.5 * pa.PW, target * pa.PH
    point = focus_parts(spec, t).get(spec.get("focus")) if spec.get("focus") else None
    shot = "focus" if point else spec.get("shot", "push")
    if shot == "focus":
        zoom_to = float(spec.get("zoom", 2.4))
        zoom = 1.3 + (zoom_to - 1.3) * _ease(t / 1.6)
        fx, fy = point[0] * pa.DETAIL, point[1] * pa.DETAIL
        fx += 3 * k * math.sin(t * 0.5 + seed)
    elif shot == "wide":
        zoom = 1.0 + 0.012 * t
        fx, fy = pa.PW / 2, focus * pa.PH
    elif shot == "pan":
        zoom = 1.55
        side = 1 if seed % 2 else -1
        fx = pa.PW * (0.5 - side * 0.18 + side * 0.36 * _ease(t / 6.0))
        fy = focus * pa.PH + 6 * k
    else:
        zoom = 1.12 + 0.05 * rng.random() + 0.01 * t
        fx = pa.PW / 2 + 5 * k * math.sin(t * 0.35 + seed)
        fy = focus * pa.PH + 3 * k * math.sin(t * 0.27 + seed * 2)
    h, w = pa.PH / zoom, pa.PW / zoom
    y0 = min(max(0.0, fy - ty / zoom), pa.PH - h)
    x0 = min(max(0.0, fx - tx / zoom), pa.PW - w)
    ys = np.clip((np.arange(pa.PH) / zoom + y0).astype(int), 0, pa.PH - 1)
    xs = np.clip((np.arange(pa.PW) / zoom + x0).astype(int), 0, pa.PW - 1)
    return frame[ys][:, xs]


def lighting(frame):
    """Bloom on bright parts, a vignette and a fine screen-dot texture."""
    global _VIGNETTE, _SCREEN
    if _VIGNETTE is None or _VIGNETTE.shape[:2] != frame.shape[:2]:
        yy, xx = (pa.PY / pa.PH - 0.55) * 1.1, (pa.PX / pa.PW - 0.5) * 1.3
        vignette = 1 - 0.45 * np.clip(xx ** 2 + yy ** 2, 0, 1)
        screen = np.where((pa.PY % 2 == 1) & (pa.PX % 2 == 1), 0.86, 1.0)
        _VIGNETTE = (vignette * screen).astype(np.float32)[..., None]   # one combined multiplier
    # Glow: find bright pixels on a quarter-size copy, blur, and add back
    small = frame[::4, ::4].astype(np.float32)
    bright = np.clip((small.max(axis=2) - 205) / 50, 0, 1)[..., None] * small
    k = max(1, round(3 * pa.PH / 640 / 1.5))
    glow = _blur(_blur(bright, k), k) * 1.1
    glow = np.repeat(np.repeat(glow, 4, 0), 4, 1)[:pa.PH, :pa.PW]
    f = (frame.astype(np.float32) + glow) * _VIGNETTE
    return np.clip(f, 0, 255).astype(np.uint8)


def draw_overlay(layer, t, info, tag=""):
    """All HUD boxes for one layer. `info` keys: title, stat, handle, gauge."""
    y = 10
    # Tag box with a play-arrow, e.g. "FACT 2 OF 5"
    if tag:
        w = len(tag) * 12 + 26
        box(layer, MARGIN, y, MARGIN + w, y + 22, ORANGE, 0.75)
        for i in range(8):   # little triangle
            layer[y + 7 + i // 2: y + 15 - i // 2, MARGIN + 6 + i:MARGIN + 7 + i] = (*ORANGE, 255)
        text(layer, tag, MARGIN + 18, y + 4, 2, ORANGE, shadow=False)
        y += 28
    # Title box: lines alternate white / yellow
    title = info.get("title", "")
    if title:
        scale, lines = title_layout(title)
        line_h = 9 * scale
        h = len(lines) * line_h + 14
        box(layer, MARGIN, y, HW - MARGIN, y + h, WHITE, 0.85, 3)
        for i, line in enumerate(lines):
            text(layer, line, HW // 2, y + 9 + i * line_h, scale, YELLOW if i % 2 else WHITE, center=True)
        y += h + 6
    # Stat bar
    stat = info.get("stat", "")
    if stat:
        lines = _lines(stat, 2, HW - 2 * MARGIN - 16)[:2]
        h = len(lines) * 18 + 8
        box(layer, MARGIN + 8, y, HW - MARGIN - 8, y + h, YELLOW, 0.85)
        for i, line in enumerate(lines):
            text(layer, line, HW // 2, y + 6 + i * 18, 2, YELLOW, center=True)
        y += h + 6
    # Handle box (bottom left) and gauge (bottom right)
    handle = info.get("handle", "")
    if handle:
        w = len(handle) * 12 + 16
        box(layer, MARGIN, HH - 46, MARGIN + w, HH - 22, WHITE, 0.7)
        text(layer, handle, MARGIN + 8, HH - 40, 2, WHITE, shadow=False)
    if info.get("gauge"):
        gauge(layer, t, info["gauge"], HW - MARGIN - 44, HH - 92)


def caption_top(info, tag=True):
    """Where the caption box starts: just under the tag, title and stat boxes."""
    y = 10 + (28 if tag else 0)
    if info.get("title"):
        scale, lines = title_layout(info["title"])
        y += len(lines) * 9 * scale + 14 + 6
    if info.get("stat"):
        y += len(_lines(info["stat"], 2, HW - 2 * MARGIN - 16)[:2]) * 18 + 8 + 6
    return y


def caption_frame(txt, top):
    """RGBA caption: white text in a fixed-size bordered box starting at `top`."""
    frame = np.zeros((HH, HW, 3), dtype=np.uint8)
    alpha = np.zeros((HH, HW), dtype=np.uint8)
    # Size 3 text, or size 2 if a long caption piece wouldn't fit in 3 lines
    scale = 3 if len(_lines(txt, 3, HW - 2 * MARGIN - 24)) <= 3 else 2
    step = 9 * scale
    lines = _lines(txt, scale, HW - 2 * MARGIN - 24)[:4]
    h = 3 * 27 + 14
    x0, x1 = MARGIN + 4, HW - MARGIN - 4
    frame[top:top + h, x0:x1] = BLACK
    alpha[top:top + h, x0:x1] = 210
    for edge in (frame[top:top + 2, x0:x1], frame[top + h - 2:top + h, x0:x1],
                 frame[top:top + h, x0:x0 + 2], frame[top:top + h, x1 - 2:x1]):
        edge[:] = CYAN
    alpha[top:top + 2, x0:x1] = alpha[top + h - 2:top + h, x0:x1] = 255
    alpha[top:top + h, x0:x0 + 2] = alpha[top:top + h, x1 - 2:x1] = 255
    y = top + 7 + (3 * 27 - len(lines) * step) // 2   # centred in the box
    for i, line in enumerate(lines):
        m = _line_mask(line, scale)
        x = HW // 2 - m.shape[1] // 2
        ly = y + i * step
        sh = np.zeros_like(alpha, dtype=bool)
        sh[ly + 2:ly + 2 + m.shape[0], x + 2:x + 2 + m.shape[1]] = m
        frame[sh] = (0, 0, 0)
        reg = np.zeros_like(sh)
        reg[ly:ly + m.shape[0], x:x + m.shape[1]] = m
        frame[reg] = WHITE
        alpha[reg | sh] = 255
    return np.concatenate([frame, alpha[..., None]], axis=2)
