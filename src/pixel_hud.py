"""Heads-up-display layout for pixel-art Shorts.

Instead of a plain header and footer, every frame gets bordered pixel-font
boxes: a small tag ("FACT 2 OF 5"), the video's title as a big question box,
an optional stat bar with the key number, the channel handle, and an optional
animated gauge. Captions sit in a fixed box under the stat bar, so the scene
below stays clear.

Turned on per channel with "video_layout": "hud" in content/channel.json.
Sizes here are in pixels on the 360x640 drawing (pixel_art.PW x PH).
"""
import math

import numpy as np

import pixel_art as pa

WHITE, YELLOW, ORANGE, BLACK = (245, 245, 240), (255, 214, 64), (255, 150, 40), (6, 8, 14)
RED, CYAN = (235, 70, 60), (120, 230, 240)
MARGIN = 14


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


def text(frame, line, x, y, scale, color, center=False, shadow=True):
    """Draw one line of pixel text with its top-left (or top-centre) at x, y; returns its width."""
    m = _line_mask(line, scale)
    h, w = m.shape
    if center:
        x = int(x - w / 2)
    for dx, dy, col in (((scale // 2 or 1), (scale // 2 or 1), BLACK),) if shadow else ():
        _blit(frame, m, x + dx, y + dy, col)
    _blit(frame, m, x, y, color)
    return w


def _blit(frame, m, x, y, color):
    h, w = m.shape
    y0, x0 = max(0, y), max(0, x)
    y1, x1 = min(pa.PH, y + h), min(pa.PW, x + w)
    if y0 < y1 and x0 < x1:
        sub = m[y0 - y:y1 - y, x0 - x:x1 - x]
        frame[y0:y1, x0:x1][sub] = color


def box(frame, x0, y0, x1, y1, border, fill_alpha=0.82, width=2):
    """Dark see-through box with a solid pixel border."""
    x0, y0, x1, y1 = max(0, int(x0)), max(0, int(y0)), min(pa.PW, int(x1)), min(pa.PH, int(y1))
    if x0 >= x1 or y0 >= y1:
        return
    region = frame[y0:y1, x0:x1]
    region[:] = (region * (1 - fill_alpha) + np.array(BLACK) * fill_alpha).astype(np.uint8)
    frame[y0:y0 + width, x0:x1] = border
    frame[y1 - width:y1, x0:x1] = border
    frame[y0:y1, x0:x0 + width] = border
    frame[y0:y1, x1 - width:x1] = border


def title_layout(title):
    """Pick the biggest title size that fits in three lines."""
    inner = pa.PW - 2 * MARGIN - 20
    for scale, most in ((4, 3), (3, 4), (2, 5)):
        lines = _lines(title, scale, inner)
        if len(lines) <= most:
            return scale, lines
    return 2, _lines(title, 2, inner)[:4]


def gauge(frame, t, spec, cx, cy, r=34):
    """Round dial whose needle sweeps up to the value, with a readout below."""
    value, top = float(spec.get("value", 0)), float(spec.get("max") or spec.get("value", 1) or 1)
    sweep = min(1.0, t / 1.2) ** 0.5
    wobble = 0.012 * math.sin(t * 9) if sweep >= 1 else 0
    frac = max(0.0, min(1.0, value / top * sweep + wobble))
    yy, xx = pa.PY - cy, pa.PX - cx
    d = np.sqrt(xx ** 2 + yy ** 2)
    disc = d <= r
    frame[disc] = (frame[disc] * 0.15 + np.array((14, 18, 30)) * 0.85).astype(np.uint8)
    frame[(d <= r) & (d > r - 2)] = WHITE
    a0, a1 = math.radians(135), math.radians(405)          # dial runs clockwise from lower left
    for i in range(11):
        a = a0 + (a1 - a0) * i / 10
        for k in range(5 if i % 5 == 0 else 3):
            x, y = cx + math.cos(a) * (r - 4 - k), cy + math.sin(a) * (r - 4 - k)
            frame[int(y):int(y) + 1, int(x):int(x) + 1] = RED if i >= 8 else WHITE
    a = a0 + (a1 - a0) * frac
    for k in range(int(r - 7)):
        x, y = cx + math.cos(a) * k, cy + math.sin(a) * k
        frame[int(y):int(y) + 2, int(x):int(x) + 2] = RED
    frame[cy - 2:cy + 3, cx - 2:cx + 3] = WHITE
    shown = value * sweep
    number = f"{shown:,.0f}" if value >= 10 or value == int(value) else f"{shown:.1f}"
    unit = str(spec.get("unit", ""))
    readout = f"{number} {unit}".strip()
    w = len(readout) * 12 + 12
    box(frame, cx - w // 2, cy + r + 4, cx + w // 2 + 1, cy + r + 26, ORANGE, 0.85)
    text(frame, readout, cx, cy + r + 9, 2, ORANGE, center=True, shadow=False)
    label = str(spec.get("label", "")).strip()
    if label:
        text(frame, label, cx, cy - r - 12, 1, CYAN, center=True)


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
_SCREEN = None


def camera(frame, t, seed, focus_y=370, target_y=450):
    """Zoom in a little and frame the scene so its subject (around focus_y in
    the drawing) lands in the clear area under the text boxes (target_y),
    with a slow push-in and gentle drift, so shots feel filmed."""
    rng = np.random.default_rng(seed)
    zoom = 1.12 + 0.05 * rng.random() + 0.01 * t
    dx = 5 * math.sin(t * 0.35 + seed)
    dy = 3 * math.sin(t * 0.27 + seed * 2)
    h, w = pa.PH / zoom, pa.PW / zoom
    y0 = min(max(0.0, focus_y + dy - target_y / zoom), pa.PH - h)
    x0 = min(max(0.0, pa.PW / 2 + dx - w / 2), pa.PW - w)
    ys = np.clip((np.arange(pa.PH) / zoom + y0).astype(int), 0, pa.PH - 1)
    xs = np.clip((np.arange(pa.PW) / zoom + x0).astype(int), 0, pa.PW - 1)
    return frame[ys][:, xs]


def lighting(frame):
    """Bloom on bright parts, a vignette and a fine screen-dot texture."""
    global _VIGNETTE, _SCREEN
    f = frame.astype(np.float32)
    lum = f.max(axis=2)
    bright = np.clip((lum - 150) / 105, 0, 1)[..., None] * f
    small = bright[::4, ::4]
    glow = _blur(_blur(small, 3), 3)
    glow = np.repeat(np.repeat(glow, 4, 0), 4, 1)[:pa.PH, :pa.PW]
    f = f + glow * 0.9
    if _VIGNETTE is None:
        yy, xx = (pa.PY / pa.PH - 0.55) * 1.1, (pa.PX / pa.PW - 0.5) * 1.3
        _VIGNETTE = (1 - 0.45 * np.clip(xx ** 2 + yy ** 2, 0, 1))[..., None]
        _SCREEN = np.where((pa.PY % 2 == 1) & (pa.PX % 2 == 1), 0.86, 1.0)[..., None]
    f = f * _VIGNETTE * _SCREEN
    return np.clip(f, 0, 255).astype(np.uint8)


def draw_overlay(frame, t, info, tag=""):
    """All HUD boxes for one frame. `info` keys: title, stat, handle, gauge."""
    y = 10
    # Tag box with a play-arrow, e.g. "FACT 2 OF 5"
    if tag:
        w = len(tag) * 12 + 26
        box(frame, MARGIN, y, MARGIN + w, y + 22, ORANGE, 0.75)
        for i in range(8):   # little triangle
            frame[y + 7 + i // 2: y + 15 - i // 2, MARGIN + 6 + i:MARGIN + 7 + i] = ORANGE
        text(frame, tag, MARGIN + 18, y + 4, 2, ORANGE, shadow=False)
        y += 28
    # Title box: lines alternate white / yellow
    title = info.get("title", "")
    if title:
        scale, lines = title_layout(title)
        line_h = 9 * scale
        h = len(lines) * line_h + 14
        box(frame, MARGIN, y, pa.PW - MARGIN, y + h, WHITE, 0.85, 3)
        for i, line in enumerate(lines):
            text(frame, line, pa.PW // 2, y + 9 + i * line_h, scale, YELLOW if i % 2 else WHITE, center=True)
        y += h + 6
    # Stat bar
    stat = info.get("stat", "")
    if stat:
        lines = _lines(stat, 2, pa.PW - 2 * MARGIN - 16)[:2]
        h = len(lines) * 18 + 8
        box(frame, MARGIN + 8, y, pa.PW - MARGIN - 8, y + h, YELLOW, 0.85)
        for i, line in enumerate(lines):
            text(frame, line, pa.PW // 2, y + 6 + i * 18, 2, YELLOW, center=True)
        y += h + 6
    # Handle box (bottom left) and gauge (bottom right)
    handle = info.get("handle", "")
    if handle:
        w = len(handle) * 12 + 16
        box(frame, MARGIN, pa.PH - 46, MARGIN + w, pa.PH - 22, WHITE, 0.7)
        text(frame, handle, MARGIN + 8, pa.PH - 40, 2, WHITE, shadow=False)
    if info.get("gauge"):
        gauge(frame, t, info["gauge"], pa.PW - MARGIN - 44, pa.PH - 92)


def caption_top(info, tag=True):
    """Where the caption box starts: just under the tag, title and stat boxes."""
    y = 10 + (28 if tag else 0)
    if info.get("title"):
        scale, lines = title_layout(info["title"])
        y += len(lines) * 9 * scale + 14 + 6
    if info.get("stat"):
        y += len(_lines(info["stat"], 2, pa.PW - 2 * MARGIN - 16)[:2]) * 18 + 8 + 6
    return y


def caption_frame(txt, top):
    """RGBA caption: white text in a fixed-size bordered box starting at `top`."""
    frame = np.zeros((pa.PH, pa.PW, 3), dtype=np.uint8)
    alpha = np.zeros((pa.PH, pa.PW), dtype=np.uint8)
    lines = _lines(txt, 3, pa.PW - 2 * MARGIN - 24)[:3]
    h = 2 * 27 + 14
    x0, x1 = MARGIN + 4, pa.PW - MARGIN - 4
    frame[top:top + h, x0:x1] = BLACK
    alpha[top:top + h, x0:x1] = 210
    for edge in (frame[top:top + 2, x0:x1], frame[top + h - 2:top + h, x0:x1],
                 frame[top:top + h, x0:x0 + 2], frame[top:top + h, x1 - 2:x1]):
        edge[:] = CYAN
    alpha[top:top + 2, x0:x1] = alpha[top + h - 2:top + h, x0:x1] = 255
    alpha[top:top + h, x0:x0 + 2] = alpha[top:top + h, x1 - 2:x1] = 255
    y = top + 8 + (2 - len(lines)) * 27 // 2 if len(lines) < 2 else top + 8
    for i, line in enumerate(lines):
        m = _line_mask(line, 3)
        x = pa.PW // 2 - m.shape[1] // 2
        sh = np.zeros_like(alpha, dtype=bool)
        sh[y + i * 27 + 2:y + i * 27 + 2 + m.shape[0], x + 2:x + 2 + m.shape[1]] = m
        frame[sh] = (0, 0, 0)
        reg = np.zeros_like(sh)
        reg[y + i * 27:y + i * 27 + m.shape[0], x:x + m.shape[1]] = m
        frame[reg] = WHITE
        alpha[reg | sh] = 255
    return np.concatenate([frame, alpha[..., None]], axis=2)
