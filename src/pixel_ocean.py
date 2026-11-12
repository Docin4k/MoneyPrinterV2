"""Underwater 8-bit scenes for ocean channels (Pixel Abyss).

Same conventions as pixel_art.py: shapes are laid out on the 180x320 design
grid (XX/YY are design-unit coordinates of every pixel), drawn at DETAIL x that
resolution with dithered colour ramps. Every scene paints its own background.

Scenes register themselves in pixel_art.SCENES when this module is imported
(pixel_art imports it at the end, so importing either module is enough), so queue scripts can use them by name:

    deep_sea, anglerfish, jellyfish, whale, octopus, coral_reef, shark,
    shipwreck, vent, submarine, squid, ocean_surface, trench, fish_school,
    sea_turtle, kelp_forest
"""
import math
import random

import numpy as np

import pixel_art as pa
from pixel_art import LW, LH, PW, PH, DETAIL, XX, YY, PX, PY, dither_ramp, periodic_noise, px

# Water colour by depth, from sunlit to the abyss
SUNLIT = [(70, 170, 210), (30, 120, 180), (12, 70, 130), (6, 36, 80)]
TWILIGHT = [(14, 60, 110), (8, 34, 72), (4, 18, 44), (2, 8, 22)]
ABYSS = [(4, 10, 24), (2, 6, 16), (1, 3, 9), (0, 1, 4)]


# ------------------------------------------------------------ helpers ----
def _win(cx, cy, rx, ry):
    """Slices for the pixels within a design-unit box (clipped to the frame)."""
    x0, x1 = max(0, px(cx - rx)), min(PW, px(cx + rx) + 1)
    y0, y1 = max(0, px(cy - ry)), min(PH, px(cy + ry) + 1)
    if x0 >= x1 or y0 >= y1:
        return None
    return (slice(y0, y1), slice(x0, x1))


def water(frame, ramp, top=0.0, bottom=1.0):
    """Fill the frame with a dithered vertical water gradient."""
    v = top + (bottom - top) * YY / (LH - 1)
    frame[:] = dither_ramp(v, ramp)


def light_rays(frame, t, seed, strength=0.35, count=6, reach=260):
    """Slanted, slowly swaying shafts of sunlight from the surface."""
    rng = random.Random(seed)
    glow = np.zeros((PH, PW))
    for _ in range(count):
        x0 = rng.uniform(-30, LW + 10)
        w = rng.uniform(5, 14)
        ph = rng.uniform(0, 6.3)
        cx = x0 + YY * 0.32 + 4 * math.sin(t * 0.5 + ph)
        d = np.abs(XX - cx) / (w + YY * 0.04)
        glow += np.clip(1 - d, 0, 1) * (0.6 + 0.4 * math.sin(t * 0.8 + ph))
    glow *= np.clip(1 - YY / reach, 0, 1) * strength
    sel = glow > 0.02
    add = (np.clip(glow[sel], 0, 1)[:, None] * np.array([120, 200, 220]))
    frame[sel] = np.clip(frame[sel] + add * (pa.BAYER_FULL[sel][:, None] * 0.6 + 0.7), 0, 255).astype(np.uint8)


def caustics(frame, t, y0, y1, strength=40):
    """Rippling light pattern on the sea floor."""
    band = (YY >= y0) & (YY < y1)
    v = np.sin(XX[band] * 0.35 + t * 1.3 + np.sin(YY[band] * 0.4)) * np.sin(XX[band] * 0.2 - YY[band] * 0.5 - t)
    on = v > 0.55
    idx = np.flatnonzero(band.ravel())[on]
    flat = frame.reshape(-1, 3)
    flat[idx] = np.clip(flat[idx].astype(int) + strength, 0, 255).astype(np.uint8)


def marine_snow(frame, t, seed, count=160, color=(120, 140, 150), lit=None):
    """Slowly sinking specks of 'marine snow'. `lit` brightens specks in a mask."""
    rng = np.random.default_rng(seed + 7)
    x = (rng.uniform(0, LW, count) + np.sin(t * 0.7 + rng.uniform(0, 6, count)) * 2) % LW
    y = (rng.uniform(0, LH, count) + t * rng.uniform(1.5, 4, count)) % LH
    xi, yi = (x * DETAIL).astype(int), (y * DETAIL).astype(int)
    big = rng.random(count) < 0.2
    for a, b, g in zip(xi, yi, big):
        c = color
        if lit is not None and lit[min(b, PH - 1), min(a, PW - 1)]:
            c = (230, 240, 230)
        frame[b:b + 1 + g, a:a + 1 + g] = c


def glow_specks(frame, t, seed, count=40, color=(80, 220, 255)):
    """Blinking bioluminescent dots."""
    rng = np.random.default_rng(seed + 11)
    x = rng.uniform(0, LW, count)
    y = rng.uniform(40, LH, count)
    ph = rng.uniform(0, 6.3, count)
    for xi, yi, p in zip(x, y, ph):
        b = math.sin(t * 2.2 + p)
        if b > 0.2:
            c = tuple(int(ch * (0.5 + 0.5 * b)) for ch in color)
            pa.put(frame, xi, yi, c, 2 if b > 0.8 else 1)


def bubbles(frame, t, seed, x, y, count=10, spread=4, speed=14, color=(170, 220, 240)):
    """Bubbles rising from a point, wobbling as they go."""
    rng = random.Random(seed)
    for i in range(count):
        ph, r = rng.uniform(0, 1), rng.choice([1, 1, 1.5, 2])
        life = (t * speed / 100 + ph) % 1
        by = y - life * 160
        bx = x + rng.uniform(-spread, spread) + 2 * math.sin(life * 18 + i)
        if by < 0:
            continue
        s = _win(bx, by, r + 1, r + 1)
        if s is None:
            continue
        d = np.sqrt((XX[s] - bx) ** 2 + (YY[s] - by) ** 2)
        ring = (d <= r + 0.5) & (d >= r - 0.5)
        frame[s][ring] = color
        if r >= 1.5:
            pa.put(frame, bx - r * 0.4, by - r * 0.4, (240, 250, 255))


def disc(frame, x, y, r, color):
    s = _win(x, y, r + 1, r + 1)
    if s is None:
        return None
    m = (XX[s] - x) ** 2 + (YY[s] - y) ** 2 <= r * r
    frame[s][m] = color
    return s, m


def tri(frame, pts, color):
    """Filled triangle; `color` is an RGB tuple or a function (xx, yy) -> colours."""
    (ax, ay), (bx, by), (cx, cy) = pts
    s = _win((min(ax, bx, cx) + max(ax, bx, cx)) / 2, (min(ay, by, cy) + max(ay, by, cy)) / 2,
             (max(ax, bx, cx) - min(ax, bx, cx)) / 2 + 1, (max(ay, by, cy) - min(ay, by, cy)) / 2 + 1)
    if s is None:
        return
    x, y = XX[s], YY[s]

    def side(x1, y1, x2, y2):
        return (x2 - x1) * (y - y1) - (y2 - y1) * (x - x1)

    d1, d2, d3 = side(ax, ay, bx, by), side(bx, by, cx, cy), side(cx, cy, ax, ay)
    m = ~(((d1 < 0) | (d2 < 0) | (d3 < 0)) & ((d1 > 0) | (d2 > 0) | (d3 > 0)))
    frame[s][m] = color(x[m], y[m], PY[s][m], PX[s][m]) if callable(color) else color


def poly(frame, pts, color):
    """Filled convex polygon (fan of triangles)."""
    for i in range(1, len(pts) - 1):
        tri(frame, (pts[0], pts[i], pts[i + 1]), color)


def rotate(pts, cx, cy, ang):
    c, s = math.cos(ang), math.sin(ang)
    return [(cx + (x - cx) * c - (y - cy) * s, cy + (x - cx) * s + (y - cy) * c) for x, y in pts]


def tentacle(frame, x0, y0, ang, length, width, t, phase, ramp, curl=1.0, suckers=None, steps=None):
    """A tapering, waving arm drawn as a chain of discs."""
    steps = steps or max(12, int(length * 1.2))
    x, y = x0, y0
    pts = []
    for i in range(steps):
        f = i / steps
        a = ang + curl * (0.9 * math.sin(t * 1.6 + phase + f * 4) * f + 1.4 * f ** 2 * math.sin(phase))
        x += math.cos(a) * length / steps
        y += math.sin(a) * length / steps
        pts.append((x, y, a, f))
    for x, y, a, f in pts:
        r = max(0.6, width * (1 - f * 0.9))
        hit = disc(frame, x, y, r, (0, 0, 0))
        if hit:
            s, m = hit
            shade = np.clip(0.75 - ((XX[s][m] - x) * 0.3 + (YY[s][m] - y) * 0.5) / (r + 0.5) * 0.35, 0, 1)
            frame[s][m] = dither_ramp(shade, ramp, PY[s][m], PX[s][m])
    if suckers:
        for x, y, a, f in pts[1::3]:
            r = width * (1 - f * 0.9)
            if r > 1.2:
                pa.put(frame, x + math.cos(a + 1.57) * r * 0.6, y + math.sin(a + 1.57) * r * 0.6, suckers)
    return pts


def swimmer(frame, hx, cy, length, top, bottom, ramp, facing=1, bend=0.0, belly_ramp=None):
    """Side-view body of a fish, shark or whale.

    The snout is at (hx, cy) and the body runs `length` units behind it
    (to the left when facing=1). `top(u)` and `bottom(u)` give the half-heights
    above and below the centre line at u = 0 (snout) .. 1 (tail end); the centre
    line bends by `bend * u^2` units. Returns (slices, mask, u, rel) so callers
    can add markings, or None when off-screen."""
    h = max(float(np.max(top(np.linspace(0, 1, 50)))), float(np.max(bottom(np.linspace(0, 1, 50))))) + abs(bend) + 2
    s = _win(hx - facing * length / 2, cy, length / 2 + 2, h)
    if s is None:
        return None
    x, y = XX[s], YY[s]
    u = (hx - x) * facing / length
    yc = cy + bend * np.clip(u, 0, 1) ** 2
    uu = np.clip(u, 0, 1)
    tp, bt = top(uu), bottom(uu)
    m = (u >= 0) & (u <= 1) & (y > yc - tp) & (y < yc + bt)
    rel = (y - (yc - tp)) / np.maximum(tp + bt, 1e-6)
    if m.any():
        if belly_ramp is not None:
            back = rel[m] < 0.62
            cols = np.where(back[:, None],
                            dither_ramp(rel[m] / 0.62, ramp, PY[s][m], PX[s][m]),
                            dither_ramp((rel[m] - 0.62) / 0.38, belly_ramp, PY[s][m], PX[s][m]))
            frame[s][m] = cols
        else:
            frame[s][m] = dither_ramp(rel[m], ramp, PY[s][m], PX[s][m])
    return s, m, u, rel


def small_fish(frame, x, y, size, facing, color, t, phase=0.0, stripe=None):
    """A little fish: oval body, wagging tail, eye."""
    wag = math.sin(t * 8 + phase) * size * 0.25
    tri(frame, [(x - facing * size * 0.8, y), (x - facing * size * 1.5, y - size * 0.55 + wag),
                (x - facing * size * 1.5, y + size * 0.55 + wag)], tuple(int(c * 0.8) for c in color))
    s = _win(x, y, size + 1, size * 0.6 + 1)
    if s is None:
        return
    m = ((XX[s] - x) / size) ** 2 + ((YY[s] - y) / (size * 0.5)) ** 2 <= 1
    shade = np.clip(0.5 + (YY[s][m] - y) / size * 0.6, 0, 1)
    dark = tuple(int(c * 0.55) for c in color)
    light = tuple(min(255, int(c * 1.25) + 30) for c in color)
    frame[s][m] = dither_ramp(shade, [dark, color, light], PY[s][m], PX[s][m])
    if stripe is not None:
        sm = m & (np.abs(XX[s] - (x - facing * size * 0.1)) < max(0.6, size * 0.14))
        frame[s][sm] = stripe
    if size >= 3:
        pa.put(frame, x + facing * size * 0.55, y - size * 0.12, (10, 10, 10))


def seafloor(frame, y0, seed, ramp, rough=4.0):
    xs = XX[0]
    rng = random.Random(seed)
    prof = y0 + rough * np.sin(xs / 23 + rng.uniform(0, 6)) + rough * 0.5 * np.sin(xs / 7 + rng.uniform(0, 6))
    ground = YY >= prof[None, :]
    tex = periodic_noise(XX[ground] / LW * 6.28, YY[ground] / 30, seed, 3)
    depth = np.clip((YY[ground] - prof[None, :].repeat(PH, 0)[ground]) / 40, 0, 1)
    frame[ground] = dither_ramp(np.clip(0.75 - depth * 0.55 + (tex - 0.5) * 0.5, 0, 1), ramp, PY[ground], PX[ground])
    return prof


def rock(frame, cx, cy, r, seed, ramp):
    inside, nx, ny, theta = pa._rock_mask(cx, cy, r, 0, seed)
    if inside.any():
        shade = np.clip(0.6 - 0.45 * (nx[inside] * 0.5 + ny[inside] * 0.8), 0, 1)
        frame[inside] = dither_ramp(shade, ramp, PY[inside], PX[inside])


def seaweed(frame, x, base, height, t, phase, color):
    for i in range(int(height)):
        f = i / height
        sx = x + math.sin(t * 1.2 + phase + f * 3) * 4 * f
        pa.put(frame, sx, base - i, color, 2)
        if i % 5 == 2:
            pa.put(frame, sx + (2 if i % 10 == 2 else -2) * (1 - f * 0.4), base - i, color, 2)


# ------------------------------------------------------------- scenes ----
def scene_deep_sea(frame, t, spec, seed):
    """The dark midwater: marine snow, blinking light, lanternfish and a glowing siphonophore."""
    water(frame, TWILIGHT, 0.35, 1.0)
    light_rays(frame, t, seed, strength=0.12, count=4, reach=150)
    glow_specks(frame, t, seed, 70)
    marine_snow(frame, t, seed, 220, (70, 95, 110))
    # A long glowing siphonophore chain drifting through
    for i in range(70):
        f = i / 69
        x = 40 + f * 110 + 6 * math.sin(f * 9 + t * 0.8)
        y = 90 + f * 150 + 10 * math.sin(f * 5 - t * 0.6)
        b = 0.5 + 0.5 * math.sin(t * 3 - f * 14)
        pa.put(frame, x, y, (int(60 + 140 * b), int(120 + 120 * b), 255), 2)
        if i % 5 == 0:
            for k in range(6):
                pa.put(frame, x - 2 + math.sin(t + k + i) * 2, y + 2 + k * 1.5, (60, 110, 200))
    # Lanternfish with glowing photophores
    for i, (y, sz, sp) in enumerate(((60, 6, 6), (175, 5, 7), (255, 4, 5), (120, 3, 4), (215, 3, 3.5))):
        facing = 1 if i % 2 == 0 else -1
        x = (facing * t * sp + i * 63 + seed % 50) % (LW + 40) - 20
        small_fish(frame, x, y, sz, facing, (50, 75, 100), t, i)
        for k in range(4):
            pa.put(frame, x - facing * sz * 0.7 + facing * k * sz * 0.45, y + sz * 0.3, (140, 240, 255))


def scene_anglerfish(frame, t, spec, seed):
    """An anglerfish in the pitch-black deep, lit only by its glowing lure."""
    water(frame, ABYSS, 0.2, 1.0)
    marine_snow(frame, t, seed, 120, (30, 40, 50))
    bob = 3 * math.sin(t * 0.9)
    cx, cy = 104, 196 + bob
    lx, ly = 52 + 4 * math.sin(t * 1.3), 140 + bob + 3 * math.sin(t * 1.9)
    flick = 0.85 + 0.15 * math.sin(t * 7) * math.sin(t * 3.1)
    # Glow around the lure
    d = np.sqrt((XX - lx) ** 2 + (YY - ly) ** 2)
    g = np.clip(1 - d / (55 * flick), 0, 1) ** 2
    sel = g > 0.03
    frame[sel] = np.maximum(frame[sel], dither_ramp(g[sel] * 0.55, [(0, 0, 0), (5, 30, 40), (20, 80, 90)], PY[sel], PX[sel]))
    # Body, lit from the lure side
    s = _win(cx, cy, 48, 40)
    x, y = XX[s], YY[s]
    edge = 38 + 3 * np.sin(np.arctan2(y - cy, x - cx) * 7)
    body = ((x - cx) / 1.12) ** 2 + (y - cy) ** 2 < edge ** 2
    light = np.clip(1 - np.sqrt((x - lx) ** 2 + (y - ly) ** 2) / 95, 0, 1)
    bump = periodic_noise(x / 20, y / 20, seed, 3)
    frame[s][body] = dither_ramp(np.clip(light[body] * 1.1 + (bump[body] - 0.5) * 0.25, 0, 1),
                                 [(6, 8, 12), (24, 26, 32), (60, 62, 66), (110, 110, 100)], PY[s][body], PX[s][body])
    # Dorsal spines and tail fin
    for k in range(4):
        bx = cx + 6 + k * 8
        tri(frame, [(bx - 3, cy - 34 + k * 2), (bx + 3, cy - 33 + k * 3), (bx + 2, cy - 44 + k * 3)], (30, 32, 38))
    wag = 3 * math.sin(t * 2.4)
    tri(frame, [(cx + 40, cy), (cx + 62, cy - 16 + wag), (cx + 62, cy + 16 + wag)], (28, 30, 36))
    # Gaping mouth with needle teeth
    mx, my = cx - 26, cy + 10
    ms = _win(mx, my, 22, 16)
    mouth = (((XX[ms] - mx) / 20) ** 2 + ((YY[ms] - my) / 13) ** 2 <= 1) & (XX[ms] < cx - 8 + (YY[ms] - my) * 0.2)
    frame[ms][mouth] = (2, 0, 4)
    rng = random.Random(seed)
    for k in range(9):
        a = math.pi + (k - 4) * 0.28
        tx, ty = mx + 19 * math.cos(a) * 0.9 + 3, my - 12 * abs(math.sin(a + 1.57)) + 1
        tri(frame, [(tx - 1.2, ty), (tx + 1.2, ty), (tx, ty + rng.uniform(5, 9))], (225, 225, 205))
        bx, by = tx + 1, my + 12 - abs(k - 4) * 1.2
        tri(frame, [(bx - 1.2, by), (bx + 1.2, by), (bx, by - rng.uniform(4, 7))], (210, 210, 190))
    # Small eye
    pa.put(frame, cx - 14, cy - 14, (170, 180, 170), 4)
    pa.put(frame, cx - 13.5, cy - 13.5, (0, 0, 0), 2)
    # The fishing rod (illicium) and the glowing bulb (esca)
    sx, sy = cx - 10, cy - 34
    for i in range(30):
        f = i / 29
        qx = (1 - f) ** 2 * sx + 2 * (1 - f) * f * (sx - 18) + f ** 2 * lx
        qy = (1 - f) ** 2 * sy + 2 * (1 - f) * f * (ly - 28) + f ** 2 * ly
        pa.put(frame, qx, qy, (60, 62, 60), 2)
    disc(frame, lx, ly, 4.5 * flick, (120, 255, 240))
    disc(frame, lx - 0.8, ly - 0.8, 2, (240, 255, 255))


def scene_jellyfish(frame, t, spec, seed):
    """Glowing jellyfish pulsing through dark water."""
    water(frame, TWILIGHT, 0.45, 1.0)
    marine_snow(frame, t, seed, 140, (50, 70, 90))
    rng = random.Random(seed)
    palettes = [[(70, 20, 80), (200, 80, 200), (255, 190, 250)], [(20, 60, 90), (60, 190, 230), (200, 250, 255)],
                [(90, 40, 20), (240, 140, 70), (255, 220, 170)]]
    jellies = sorted(({"x": rng.uniform(25, 155), "y": rng.uniform(90, 250), "r": rng.uniform(9, 24),
                       "p": rng.uniform(0, 6.3), "c": rng.randrange(3)} for _ in range(5)), key=lambda j: j["r"])
    for j in jellies:
        pulse = 0.5 + 0.5 * math.sin(t * 2.2 + j["p"])
        cx = j["x"] + 3 * math.sin(t * 0.4 + j["p"])
        cy = (j["y"] - t * j["r"] * 0.35 - pulse * 2 + 40) % 300 - 20
        rx, ry = j["r"] * (1 - 0.15 * pulse), j["r"] * (0.75 + 0.2 * pulse)
        ramp = palettes[j["c"]]
        # Trailing tentacles (thin, translucent lines)
        for k in range(7):
            tx0 = cx - rx * 0.8 + k * rx * 0.27
            for i in range(int(j["r"] * 3)):
                f = i / (j["r"] * 3)
                tx = tx0 + math.sin(t * 2 + k + f * 6) * 3 * f
                ty = cy + 1 + i
                if f < 0.9 and (i + k) % 2 == 0:
                    pa.put(frame, tx, ty, ramp[1] if f < 0.5 else ramp[0])
        # Frilly oral arms
        for k in range(3):
            for i in range(int(j["r"] * 1.4)):
                ox = cx - rx * 0.3 + k * rx * 0.3 + math.sin(t * 3 + i * 0.5 + k) * 1.5
                pa.put(frame, ox, cy + 1 + i, ramp[2] if i % 3 else ramp[1], 2 if j["r"] > 15 else 1)
        # Translucent bell
        s = _win(cx, cy - ry / 2, rx + 1, ry / 2 + 2)
        if s is None:
            continue
        x, y = XX[s], YY[s]
        e = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
        bell = (e <= 1) & (y <= cy + 1.5 + 1.5 * np.sin((x - cx) * 0.9))
        v = np.clip(0.25 + 0.75 * e + 0.3 * pulse, 0, 1)
        col = dither_ramp(v[bell], ramp, PY[s][bell], PX[s][bell]).astype(float)
        frame[s][bell] = (frame[s][bell] * 0.35 + col * 0.65).astype(np.uint8)
        rim = bell & (e > 0.82)
        frame[s][rim] = ramp[2]


def _whale_top(u):
    head = np.clip(u / 0.22, 0, 1) ** 0.45
    return 15 * head * (1 - np.clip((u - 0.3) / 0.62, 0, 1) ** 1.3 * 0.86)


def _whale_bottom(u):
    head = np.clip(u / 0.2, 0, 1) ** 0.6
    return 17 * head * (1 - np.clip((u - 0.25) / 0.65, 0, 1) ** 1.2 * 0.88)


def scene_whale(frame, t, spec, seed):
    """A blue whale gliding through sunlit water, too big to fit on screen."""
    water(frame, SUNLIT, 0.2, 1.0)
    light_rays(frame, t, seed, strength=0.4)
    marine_snow(frame, t, seed, 90, (120, 170, 200))
    hx, cy, L = 112 + t * 7, 196, 230
    beat = math.sin(t * 1.4)
    res = swimmer(frame, hx, cy, L, _whale_top, _whale_bottom,
                  [(30, 50, 80), (55, 85, 120), (80, 115, 150)], 1, bend=6 * beat,
                  belly_ramp=[(110, 140, 165), (150, 175, 190), (185, 205, 210)])
    if res:
        s, m, u, rel = res
        grooves = m & (rel > 0.66) & (u < 0.45) & (np.sin((YY[s]) * 2.6) > 0.55)
        frame[s][grooves] = (90, 115, 140)
        mottled = m & (rel < 0.55) & (periodic_noise(XX[s] / 14, YY[s] / 9, seed, 3) > 0.68)
        frame[s][mottled] = (95, 125, 160)
    # Flipper
    fx, fy = hx - 0.3 * L, cy + 12
    tri(frame, [(fx + 8, fy - 2), (fx - 4, fy), (fx - 26, fy + 18 + 3 * beat)], (40, 62, 95))
    # Eye and mouth line
    pa.put(frame, hx - 0.17 * L, cy + 4, (10, 15, 25), 3)
    for i in range(int(0.16 * L)):
        pa.put(frame, hx - 4 - i, cy + 3 + i * 0.05, (25, 40, 65))
    # Little fish for scale
    for i in range(6):
        small_fish(frame, (40 + i * 23 - t * 10) % (LW + 20) - 10, 90 + (i * 37) % 60, 2.5, -1, (200, 210, 150), t, i)


def scene_octopus(frame, t, spec, seed):
    """An octopus on the sea floor, changing colour as it moves its arms."""
    water(frame, SUNLIT, 0.45, 1.0)
    light_rays(frame, t, seed, strength=0.25)
    prof = seafloor(frame, 262, seed, [(40, 50, 60), (110, 105, 85), (180, 165, 120)])
    caustics(frame, t, 255, LH, 30)
    rock(frame, 150, 262, 22, seed, [(30, 35, 40), (70, 75, 80), (120, 120, 115)])
    rock(frame, 25, 270, 15, seed + 3, [(30, 35, 40), (70, 75, 80), (120, 120, 115)])
    seaweed(frame, 160, 250, 46, t, 1, (40, 120, 70))
    seaweed(frame, 12, 262, 34, t, 2, (60, 140, 60))
    # Colour shift: red -> mottled sand -> red
    shift = 0.5 + 0.5 * math.sin(t * 0.8)
    red = np.array([[90, 20, 20], [190, 60, 40], [240, 130, 90]])
    sand = np.array([[80, 70, 50], [150, 130, 90], [210, 190, 140]])
    ramp = [tuple(int(v) for v in row) for row in (red * (1 - shift) + sand * shift)]
    cx, cy = 90, 200 + 2 * math.sin(t * 1.1)
    for k in range(8):
        a = math.pi * (0.1 + 0.8 * k / 7)
        tentacle(frame, cx + math.cos(a) * 12, cy + 16, a, 52, 5.5, t, k * 0.9, ramp, curl=1.1,
                 suckers=(250, 210, 190))
    s = _win(cx, cy, 26, 28)
    x, y = XX[s], YY[s]
    mantle = (((x - cx) / 22) ** 2 + ((y - cy + 4) / 26) ** 2 <= 1) & (y < cy + 20)
    shade = np.clip(0.85 - ((x - cx) * 0.4 + (y - cy) * 0.8) / 40, 0, 1)
    spots = periodic_noise(x / 9, y / 9, seed, 2) > 0.62
    frame[s][mantle] = dither_ramp(np.clip(shade[mantle] - spots[mantle] * 0.3 * shift, 0, 1), ramp, PY[s][mantle], PX[s][mantle])
    for ex in (cx - 9, cx + 9):
        disc(frame, ex, cy + 8, 4, (240, 220, 160))
        pa.put(frame, ex - 2, cy + 7.5, (10, 10, 10), 8)


def _coral_branch(frame, x, y, ang, length, depth, color, rng):
    for i in range(int(length)):
        x += math.cos(ang)
        y += math.sin(ang)
        pa.put(frame, x, y, color, 2 + (depth > 1) * 1)
    if depth > 0:
        for d in (-0.5, 0.45):
            _coral_branch(frame, x, y, ang + d + rng.uniform(-0.2, 0.2), length * 0.72, depth - 1, color, rng)
    else:
        pa.put(frame, x, y, tuple(min(255, c + 60) for c in color), 3)


def scene_coral_reef(frame, t, spec, seed):
    """A bright, busy coral reef in shallow water."""
    water(frame, SUNLIT, 0.0, 0.7)
    light_rays(frame, t, seed, strength=0.45)
    seafloor(frame, 268, seed, [(120, 110, 80), (200, 185, 140), (240, 225, 180)], rough=3)
    caustics(frame, t, 262, LH, 35)
    rng = random.Random(seed)
    # Brain coral domes
    for bx, br, col in ((30, 20, (200, 160, 90)), (140, 26, (170, 120, 160)), (95, 14, (210, 120, 80))):
        s = _win(bx, 268, br + 1, br + 1)
        m = ((XX[s] - bx) ** 2 + (YY[s] - 268) ** 2 <= br * br) & (YY[s] < 270)
        ridges = np.sin(XX[s] * 0.9 + np.sin(YY[s] * 0.5) * 3) > 0.3
        shade = np.clip(0.8 - (YY[s] - 268 + br) / (br * 3) - ridges * 0.25, 0, 1)
        dark = tuple(c // 3 for c in col)
        frame[s][m] = dither_ramp(1 - shade[m], [tuple(min(255, c + 40) for c in col), col, dark], PY[s][m], PX[s][m])
    # Branching coral
    for bx, col in ((60, (240, 110, 120)), (118, (250, 170, 60)), (170, (150, 90, 210)), (8, (240, 120, 160))):
        _coral_branch(frame, bx, 266, -math.pi / 2 + rng.uniform(-0.2, 0.2), 16, 3, col, rng)
    # Sea fan
    for i in range(40):
        a = -math.pi / 2 + (i / 39 - 0.5) * 1.6
        for r in range(0, 44, 2):
            pa.put(frame, 82 + math.cos(a) * r + math.sin(t + r * 0.1), 262 + math.sin(a) * r * 0.9, (200, 70, 150))
    # Anemone with a clownfish
    for k in range(14):
        a = -math.pi / 2 + (k - 6.5) * 0.18
        for i in range(14):
            pa.put(frame, 108 + math.cos(a) * i + math.sin(t * 2 + i * 0.4 + k) * i * 0.15,
                   258 + math.sin(a) * i, (230, 200, 220) if i > 10 else (190, 120, 190), 2)
    cfx = 108 + 10 * math.sin(t * 0.9)
    small_fish(frame, cfx, 236 + 3 * math.sin(t * 1.7), 5, 1 if math.cos(t * 0.9) > 0 else -1, (250, 120, 30), t,
               stripe=(255, 255, 255))
    # Schools of reef fish
    for i in range(14):
        sp = 8 + (i % 4) * 3
        facing = 1 if i % 3 else -1
        x = (i * 41 + facing * t * sp) % (LW + 30) - 15
        col = [(250, 230, 60), (60, 160, 250), (250, 120, 160), (120, 230, 200)][i % 4]
        small_fish(frame, x, 80 + (i * 53) % 140, 3 + (i % 3), facing, col, t, i)


def _shark_top(u):
    return 12 * np.clip(u / 0.3, 0, 1) ** 0.7 * (1 - np.clip((u - 0.35) / 0.55, 0, 1) ** 1.1 * 0.85)


def _shark_bottom(u):
    return 11 * np.clip(u / 0.25, 0, 1) ** 0.8 * (1 - np.clip((u - 0.3) / 0.6, 0, 1) ** 1.1 * 0.85)


def scene_shark(frame, t, spec, seed):
    """A great white shark cruising past through open blue water."""
    water(frame, SUNLIT, 0.25, 1.0)
    light_rays(frame, t, seed, strength=0.35)
    marine_snow(frame, t, seed, 80, (110, 160, 190))
    L = 135
    hx = 95 + t * 7      # cruises slowly to the right, always on screen
    cy = 190 + 6 * math.sin(t * 0.7)
    beat = math.sin(t * 3)
    grey, belly = [(45, 55, 70), (85, 95, 110), (120, 130, 140)], [(190, 195, 200), (220, 225, 230), (245, 245, 245)]
    res = swimmer(frame, hx, cy, L, _shark_top, _shark_bottom, grey, 1, bend=4 * beat, belly_ramp=belly)
    tail_y = cy + 4 * beat
    tri(frame, [(hx - L + 4, tail_y - 1), (hx - L - 16, tail_y - 26), (hx - L - 4, tail_y)], (70, 80, 95))
    tri(frame, [(hx - L + 4, tail_y), (hx - L - 12, tail_y + 16), (hx - L - 2, tail_y + 1)], (70, 80, 95))
    tri(frame, [(hx - 0.36 * L, cy - 10), (hx - 0.55 * L, cy - 30), (hx - 0.6 * L, cy - 6)], (60, 70, 85))
    tri(frame, [(hx - 0.3 * L, cy + 6), (hx - 0.42 * L, cy + 26), (hx - 0.5 * L, cy + 6)], (75, 85, 100))
    if res:
        s, m, u, rel = res
        for g in range(5):
            gill = m & (np.abs(u - (0.22 + g * 0.025)) < 0.005) & (rel > 0.3) & (rel < 0.65)
            frame[s][gill] = (40, 45, 55)
        mouth = m & (rel > 0.66) & (rel < 0.72) & (u > 0.03) & (u < 0.13)
        frame[s][mouth] = (40, 30, 35)
    pa.put(frame, hx - 0.11 * L, cy - 3, (5, 5, 10), 3)
    # A pilot fish or two
    for i in range(3):
        small_fish(frame, hx - 0.4 * L + i * 9, cy + 22 + i * 3, 2.5, 1, (180, 190, 120), t, i, stripe=(40, 40, 50))


def scene_shipwreck(frame, t, spec, seed):
    """A wooden shipwreck resting on the sea floor."""
    water(frame, [(20, 90, 110), (10, 55, 75), (5, 30, 45), (2, 14, 22)], 0.1, 1.0)
    light_rays(frame, t, seed, strength=0.25, reach=220)
    marine_snow(frame, t, seed, 120, (90, 120, 120))
    seafloor(frame, 266, seed, [(35, 40, 35), (80, 80, 60), (130, 120, 90)])
    cx, cy, tilt = 92, 240, -0.18
    wood = lambda x, y, py_, px_: dither_ramp(
        np.clip(0.3 + ((y - 215) / 60) * -0.2 + (np.sin(y * 3.1 + x * 0.2 * tilt) > 0.7) * -0.25 +
                periodic_noise(x / 12, y / 6, seed, 2) * 0.4, 0, 1),
        [(30, 22, 18), (65, 45, 30), (100, 72, 45), (140, 105, 70)], py_, px_)
    hull = rotate([(cx - 70, cy - 22), (cx + 55, cy - 22), (cx + 72, cy - 36), (cx + 48, cy + 16), (cx - 52, cy + 16),
                   (cx - 75, cy - 30)], cx, cy, tilt)
    poly(frame, hull, wood)
    deck = rotate([(cx - 70, cy - 22), (cx + 55, cy - 22), (cx + 55, cy - 19), (cx - 70, cy - 19)], cx, cy, tilt)
    poly(frame, deck, (45, 32, 24))
    # Broken masts
    for mx, h, a in ((cx - 25, 70, tilt - 0.1), (cx + 22, 40, tilt + 0.25)):
        base = rotate([(mx, cy - 22)], cx, cy, tilt)[0]
        top = (base[0] + math.sin(a) * h, base[1] - math.cos(a) * h)
        poly(frame, [(base[0] - 2.5, base[1]), (base[0] + 2.5, base[1]), (top[0] + 1.8, top[1]), (top[0] - 1.8, top[1])],
             (70, 50, 34))
        if h > 50:
            yard = (base[0] + math.sin(a) * h * 0.7, base[1] - math.cos(a) * h * 0.7)
            poly(frame, [(yard[0] - 22, yard[1] - 1), (yard[0] + 20, yard[1] + 3), (yard[0] + 20, yard[1] + 5),
                         (yard[0] - 22, yard[1] + 1)], (60, 44, 30))
            for i in range(30):   # torn sail drifting
                sx = yard[0] - 16 + i * 1.2
                for j in range(int(10 + 6 * math.sin(i * 0.7))):
                    if (i + j) % 3:
                        pa.put(frame, sx + math.sin(t + j * 0.3) * 1.5, yard[1] + 3 + j, (150, 150, 120))
    # Portholes and a hole in the hull
    for i in range(5):
        p = rotate([(cx - 45 + i * 22, cy - 6)], cx, cy, tilt)[0]
        disc(frame, p[0], p[1], 3, (150, 120, 60))
        disc(frame, p[0], p[1], 2, (5, 10, 15))
    hole = rotate([(cx + 20, cy + 4)], cx, cy, tilt)[0]
    s = _win(hole[0], hole[1], 14, 10)
    h = ((XX[s] - hole[0]) / 12) ** 2 + ((YY[s] - hole[1]) / 7) ** 2 + 0.25 * np.sin(XX[s] * 1.7) < 1
    frame[s][h] = (4, 8, 10)
    seaweed(frame, cx - 55, 252, 30, t, 0.5, (50, 110, 60))
    seaweed(frame, cx + 60, 254, 24, t, 2, (60, 120, 50))
    bubbles(frame, t, seed, hole[0], hole[1] - 4, 8, 3, 10)
    for i in range(5):
        small_fish(frame, (i * 37 + t * 9) % (LW + 20) - 10, 150 + i * 9, 3, 1, (150, 170, 150), t, i)


def scene_vent(frame, t, spec, seed):
    """A hydrothermal vent: a 'black smoker' chimney with tube worms."""
    water(frame, ABYSS, 0.0, 1.0)
    # A submersible's light from the right
    d = np.sqrt((XX - 210) ** 2 + (YY - 150) ** 2)
    beam = np.clip(1 - d / 220, 0, 1) * 0.55
    sel = beam > 0.05
    frame[sel] = np.maximum(frame[sel], dither_ramp(beam[sel], [(0, 0, 0), (10, 30, 40), (30, 70, 80)], PY[sel], PX[sel]))
    marine_snow(frame, t, seed, 110, (60, 80, 90), lit=beam > 0.3)
    seafloor(frame, 272, seed, [(10, 10, 12), (35, 30, 30), (70, 60, 55)], rough=5)
    # Chimney
    cx, top = 86, 150
    s = _win(cx, 210, 26, 64)
    x, y = XX[s], YY[s]
    halfw = 6 + (y - top) * 0.17 + 3 * np.sin(y * 0.4 + seed)
    chim = (y >= top) & (np.abs(x - cx) < halfw)
    tex = periodic_noise(x / 8, y / 10, seed, 3)
    shade = np.clip(0.5 + (x - cx) / halfw * 0.35 + (tex - 0.5) * 0.6, 0, 1)
    frame[s][chim] = dither_ramp(shade[chim], [(15, 12, 12), (45, 35, 30), (95, 75, 55), (150, 110, 70)], PY[s][chim], PX[s][chim])
    hot = chim & (np.abs(x - cx) < 3) & (y < top + 6)
    frame[s][hot] = (255, 120, 30)
    # Billowing black smoke
    s = _win(cx, top / 2, 70, top / 2 + 4)
    x, y = XX[s], YY[s]
    rise = top - y
    width = 5 + rise * 0.35
    n = periodic_noise(x / 18, (y + t * 25) / 14, seed + 1, 3)
    smoke = (y < top + 1) & (np.abs(x - cx - np.sin(rise * 0.03 + t * 0.5) * rise * 0.12) < width * (0.6 + n * 0.8))
    v = np.clip(n * (1 - rise / 170), 0, 1)
    cols = dither_ramp(v[smoke], [(4, 4, 6), (20, 20, 22), (45, 42, 40), (70, 60, 50)], PY[s][smoke], PX[s][smoke])
    near = rise[smoke] < 10
    cols[near] = dither_ramp(1 - rise[smoke][near] / 10, [(60, 40, 30), (180, 80, 30), (255, 160, 60)],
                             PY[s][smoke][near], PX[s][smoke][near])
    frame[s][smoke] = cols
    # Tube worms with red plumes
    rng = random.Random(seed)
    for k in range(16):
        wx = cx + rng.choice([-1, 1]) * rng.uniform(16, 46)
        base = 272 + rng.uniform(-2, 2)
        h = rng.uniform(14, 34)
        lean = rng.uniform(-0.3, 0.3)
        for i in range(int(h)):
            pa.put(frame, wx + lean * i, base - i, (225, 220, 205) if i % 4 else (180, 175, 160), 2)
        tip = (wx + lean * h, base - h)
        sway = 1.5 * math.sin(t * 1.5 + k)
        for j in range(6):
            pa.put(frame, tip[0] - 2 + j * 0.8 + sway, tip[1] - 2 - abs(j - 2.5) * 0.6, (220, 30, 40), 2)
    # A pale crab
    cbx = 140 + 6 * math.sin(t * 0.6)
    disc(frame, cbx, 266, 5, (210, 200, 190))
    for k in (-1, 1):
        for i in range(3):
            pa.put(frame, cbx + k * (5 + i * 2), 266 + i, (190, 180, 170))


def scene_submarine(frame, t, spec, seed):
    """A small research submersible descending with its lights on."""
    water(frame, TWILIGHT, 0.5, 1.0)
    sx, sy = 60, 140 + t * 3
    # Headlight beam toward the lower right
    ang = 0.5
    dx, dy = XX - (sx + 30), YY - (sy + 8)
    along = dx * math.cos(ang) + dy * math.sin(ang)
    across = -dx * math.sin(ang) + dy * math.cos(ang)
    cone = (along > 0) & (np.abs(across) < along * 0.38)
    v = np.clip(1 - along / 190, 0, 1) * np.clip(1 - np.abs(across) / (along * 0.38 + 1e-6), 0, 1) ** 0.5
    sel = cone & (v > 0.04)
    frame[sel] = np.maximum(frame[sel], dither_ramp(v[sel], [(5, 20, 35), (30, 70, 90), (90, 150, 160), (180, 220, 210)],
                                                    PY[sel], PX[sel]))
    marine_snow(frame, t, seed, 240, (40, 60, 80), lit=sel)
    # Hull
    s = _win(sx, sy, 32, 20)
    x, y = XX[s], YY[s]
    hull = ((x - sx) / 30) ** 2 + ((y - sy) / 16) ** 2 <= 1
    shade = np.clip(0.8 - ((x - sx) * 0.3 + (y - sy) * 0.9) / 30, 0, 1)
    frame[s][hull] = dither_ramp(shade[hull], [(110, 70, 10), (210, 150, 20), (250, 210, 60), (255, 245, 170)],
                                 PY[s][hull], PX[s][hull])
    stripe = hull & (np.abs(y - sy - 4) < 1.2)
    frame[s][stripe] = (60, 60, 70)
    # Conning tower, viewport, propeller, arm and lights
    poly(frame, [(sx - 8, sy - 14), (sx + 6, sy - 14), (sx + 4, sy - 22), (sx - 6, sy - 22)], (220, 160, 30))
    disc(frame, sx + 20, sy - 2, 7, (40, 70, 90))
    disc(frame, sx + 20, sy - 2, 5, (90, 160, 190))
    pa.put(frame, sx + 18, sy - 5, (220, 250, 255), 3)
    blade = math.sin(t * 20) * 6
    poly(frame, [(sx - 32, sy - 1), (sx - 36, sy - 1 - blade), (sx - 38, sy - 1 - blade), (sx - 34, sy - 1)], (90, 90, 100))
    poly(frame, [(sx - 32, sy + 1), (sx - 36, sy + 1 + blade), (sx - 38, sy + 1 + blade), (sx - 34, sy + 1)], (90, 90, 100))
    for i in range(14):
        pa.put(frame, sx + 18 + i * 0.9, sy + 12 + i * 0.6 + math.sin(t + i * 0.3), (120, 120, 130), 2)
    disc(frame, sx + 28, sy + 7, 2.5, (255, 255, 220))
    if math.sin(t * 5) > 0:
        pa.put(frame, sx - 2, sy - 23, (255, 60, 60), 2)
    bubbles(frame, t, seed, sx - 30, sy - 4, 6, 2, 9)


def scene_squid(frame, t, spec, seed):
    """A giant squid drifting in the deep, its huge eye catching the light."""
    water(frame, ABYSS, 0.0, 0.9)
    d = np.sqrt((XX - 100) ** 2 + (YY - 170) ** 2)
    g = np.clip(1 - d / 150, 0, 1) * 0.4
    frame[:] = np.maximum(frame, dither_ramp(g, [(0, 0, 0), (8, 18, 35), (20, 40, 70)]))
    marine_snow(frame, t, seed, 140, (40, 50, 70))
    cx, cy = 98 + 4 * math.sin(t * 0.5), 110 + 3 * math.sin(t * 0.8)
    ramp = [(60, 10, 15), (140, 30, 35), (200, 70, 60), (240, 140, 120)]
    # Arms and the two long feeding tentacles
    for k in range(8):
        a = math.pi / 2 + (k - 3.5) * 0.14
        tentacle(frame, cx + (k - 3.5) * 2.4, cy + 46, a, 60, 3.6, t, k * 0.7, ramp, curl=0.6, suckers=(250, 200, 190))
    for k, sgn in enumerate((-1, 1)):
        pts = tentacle(frame, cx + sgn * 4, cy + 46, math.pi / 2 + sgn * 0.2, 150, 1.6, t * 0.7, 2 + k, ramp, curl=0.35)
        ex, ey = pts[-1][:2]
        disc(frame, ex, ey, 3.5, ramp[2])
    # Mantle with two side fins near its tip
    flap = 2 * math.sin(t * 1.5)
    tri(frame, [(cx - 3, cy - 52), (cx - 3, cy - 24), (cx - 22, cy - 36 + flap)], ramp[1])
    tri(frame, [(cx + 3, cy - 52), (cx + 3, cy - 24), (cx + 22, cy - 36 + flap)], ramp[1])
    s = _win(cx, cy, 18, 50)
    x, y = XX[s], YY[s]
    halfw = 12 * np.clip((y - (cy - 50)) / 30, 0, 1) ** 0.6
    mantle = (y > cy - 50) & (y < cy + 46) & (np.abs(x - cx) < halfw)
    shade = np.clip(0.75 - (x - cx) / 30 + periodic_noise(x / 6, y / 8, seed, 2) * 0.3 - 0.15, 0, 1)
    frame[s][mantle] = dither_ramp(shade[mantle], ramp, PY[s][mantle], PX[s][mantle])
    # The eye (the largest in the animal kingdom)
    disc(frame, cx - 2, cy + 36, 7, (220, 200, 160))
    disc(frame, cx - 2, cy + 36, 5, (20, 20, 30))
    pa.put(frame, cx - 4, cy + 33, (255, 255, 255), 3)


def scene_ocean_surface(frame, t, spec, seed):
    """Split view: sky and waves above, sunlit water below."""
    horizon = 132
    frame[:] = dither_ramp(np.clip(YY / horizon, 0, 1), [(60, 120, 210), (110, 170, 230), (200, 225, 245)])
    sun = (XX - 135) ** 2 + (YY - 70) ** 2 <= 14 ** 2
    frame[sun] = (255, 240, 170)
    rng = random.Random(seed)
    for _ in range(3):   # puffy clouds
        cxl, cyl = rng.uniform(0, LW), rng.uniform(40, 100)
        for k in range(5):
            disc(frame, (cxl + k * 6 + t * 2) % (LW + 30) - 15, cyl - 3 * math.sin(k * 1.3), 5 + k % 3, (245, 248, 255))
    under = YY > horizon
    frame[under] = dither_ramp(np.clip((YY[under] - horizon) / (LH - horizon), 0, 1), SUNLIT, PY[under], PX[under])
    light_rays(frame, t, seed, strength=0.25)
    # Waves on the waterline
    xs = XX[0]
    for layer in range(3):
        wave = horizon - 3 + layer * 2 + 2.5 * np.sin(xs / (8 + layer * 3) + t * (2 - layer * 0.4) + layer)
        band = (YY > wave[None, :] - 1.5) & (YY < wave[None, :] + 1.5) & (YY < horizon + 10)
        frame[band] = [(255, 255, 255), (170, 210, 240), (90, 160, 210)][layer]
    for i in range(30):   # sparkles on the water
        x = rng.uniform(0, LW)
        if math.sin(t * 5 + i) > 0.6:
            pa.put(frame, x, horizon - 4 + rng.uniform(0, 4), (255, 255, 230), 2)
    # A distant ship and a breaching whale's tail
    poly(frame, [(20, horizon - 6), (50, horizon - 6), (46, horizon - 1), (24, horizon - 1)], (50, 50, 60))
    poly(frame, [(30, horizon - 12), (40, horizon - 12), (40, horizon - 6), (30, horizon - 6)], (200, 60, 50))
    rise = max(0.0, math.sin(t * 0.7)) * 16
    tx = 100
    tri(frame, [(tx - 2, horizon + 2), (tx + 2, horizon + 2), (tx, horizon - rise * 0.6)], (40, 55, 75))
    tri(frame, [(tx, horizon - rise * 0.6), (tx - 14, horizon - rise - 2), (tx - 2, horizon - rise * 0.5)], (40, 55, 75))
    tri(frame, [(tx, horizon - rise * 0.6), (tx + 14, horizon - rise - 2), (tx + 2, horizon - rise * 0.5)], (40, 55, 75))
    for i in range(10):
        small_fish(frame, (i * 30 + t * 6) % (LW + 20) - 10, 200 + (i * 17) % 80, 2.5, 1, (200, 210, 220), t, i)


def scene_trench(frame, t, spec, seed):
    """A cross-section of the ocean down into a deep trench."""
    v = np.clip(YY / LH, 0, 1)
    frame[:] = dither_ramp(v, [(60, 160, 210), (20, 90, 160), (6, 36, 80), (2, 10, 28), (0, 2, 8)])
    xs = XX[0]
    # Trench walls closing in with depth
    wall_l = 10 + (YY / LH) ** 1.6 * 62 + 4 * np.sin(YY / 9 + seed)
    wall_r = LW - 10 - (YY / LH) ** 1.6 * 62 + 4 * np.sin(YY / 11 + seed * 2)
    rockm = ((XX < wall_l) | (XX > wall_r)) & (YY > 70)
    tex = periodic_noise(XX[rockm] / 20, YY[rockm] / 20, seed, 3)
    frame[rockm] = dither_ramp(np.clip(0.7 - YY[rockm] / LH * 0.6 + (tex - 0.5) * 0.4, 0, 1),
                               [(5, 5, 8), (25, 25, 30), (60, 55, 50), (100, 90, 75)], PY[rockm], PX[rockm])
    # Depth ticks on the left
    for i in range(1, 9):
        y = 30 + i * 32
        for k in range(6):
            pa.put(frame, 2 + k, y, (200, 210, 220) if i % 2 else (120, 130, 140))
    # Surface waves
    wave = 6 + 1.5 * np.sin(xs / 6 + t * 2)
    frame[(YY < wave[None, :])] = (150, 200, 240)
    # A tiny sub dropping toward the bottom with its light on
    sy = 60 + (t * 22) % 240
    disc(frame, 90, sy, 4, (250, 200, 40))
    d = np.sqrt((XX - 90) ** 2 + (YY - sy - 10) ** 2)
    lit = (d < 14) & (YY > sy)
    frame[lit] = np.maximum(frame[lit], dither_ramp(1 - d[lit] / 14, [(0, 0, 0), (40, 70, 80), (120, 160, 160)],
                                                    PY[lit], PX[lit]))
    marine_snow(frame, t, seed, 100, (60, 90, 110))
    glow_specks(frame, t, seed, 18)


def scene_fish_school(frame, t, spec, seed):
    """A swirling 'bait ball' of silver fish."""
    water(frame, SUNLIT, 0.25, 0.95)
    light_rays(frame, t, seed, strength=0.35)
    rng = np.random.default_rng(seed)
    n = 380
    rad = np.sqrt(rng.random(n)) * 52 + 4
    ang0 = rng.uniform(0, 6.3, n)
    z = rng.uniform(-1, 1, n)
    speed = 0.9 + 0.3 * rng.random(n)
    ang = ang0 + t * speed * (60 / (rad + 20))
    cx, cy = LW / 2 + 8 * math.sin(t * 0.4), 190 + 6 * math.sin(t * 0.6)
    x = cx + np.cos(ang) * rad
    y = cy + np.sin(ang) * rad * 0.62 + z * 10
    vx, vy = -np.sin(ang), np.cos(ang) * 0.62
    flash = np.clip(0.5 + 0.5 * np.sin(ang * 2 + z * 3), 0, 1)   # sides catching the light
    order = np.argsort(z)
    ramp = [(40, 70, 100), (110, 140, 160), (190, 210, 220), (255, 255, 255)]
    for i in order:
        L = 2.6 + z[i] * 0.6
        for k in range(4):
            pa.put(frame, x[i] - vx[i] * k * L / 3, y[i] - vy[i] * k * L / 3,
                   ramp[min(3, int(flash[i] * 3.99))] if k < 3 else ramp[1])
    # A dolphin cutting through
    dx = (t * 30) % (LW + 120) - 60
    res = swimmer(frame, dx, 120, 46, lambda u: 6 * np.clip(u / 0.3, 0, 1) ** 0.6 * (1 - np.clip((u - 0.4) / 0.6, 0, 1) * 0.8),
                  lambda u: 5 * np.clip(u / 0.25, 0, 1) ** 0.7 * (1 - np.clip((u - 0.35) / 0.65, 0, 1) * 0.8),
                  [(50, 70, 90), (90, 110, 130)], 1, bend=3 * math.sin(t * 4),
                  belly_ramp=[(160, 175, 185), (210, 215, 220)])
    tri(frame, [(dx - 20, 115), (dx - 28, 105), (dx - 28, 115)], (60, 80, 100))
    tri(frame, [(dx - 46, 120), (dx - 54, 112), (dx - 54, 128)], (60, 80, 100))
    pa.put(frame, dx - 7, 118, (10, 10, 15), 2)


def scene_sea_turtle(frame, t, spec, seed):
    """A sea turtle gliding with slow strokes of its flippers."""
    water(frame, SUNLIT, 0.1, 0.85)
    light_rays(frame, t, seed, strength=0.4)
    marine_snow(frame, t, seed, 70, (130, 180, 210))
    cx, cy = 90 + 6 * math.sin(t * 0.4), 190 + 4 * math.sin(t * 0.9)
    stroke = math.sin(t * 1.6)
    flip = [(70, 120, 80), (110, 160, 110)]
    for side, (bx, by, length) in enumerate(((cx + 10, cy - 12, 38), (cx + 10, cy + 12, 38))):
        sgn = -1 if side == 0 else 1
        a = sgn * (0.9 + 0.6 * stroke)
        tip = (bx - 10 + math.cos(a) * length * 0.3, by + math.sin(a) * length)
        tri(frame, [(bx - 4, by), (bx + 8, by), tip], flip[1])
        tri(frame, [(bx - 4, by), (bx - 8, by + sgn * 4), tip], flip[0])
    for sgn in (-1, 1):
        tri(frame, [(cx - 22, cy + sgn * 6), (cx - 16, cy + sgn * 10), (cx - 34, cy + sgn * 16 + 2 * stroke)], flip[0])
    # Head
    disc(frame, cx + 34, cy, 8, (110, 160, 110))
    pa.put(frame, cx + 37, cy - 3, (10, 10, 10), 3)
    s = _win(cx + 34, cy, 8, 8)
    scales = ((XX[s] - cx - 34) ** 2 + (YY[s] - cy) ** 2 < 64) & (np.sin(XX[s] * 1.4) * np.sin(YY[s] * 1.4) > 0.6)
    frame[s][scales] = (70, 115, 75)
    # Shell with a pattern of plates
    s = _win(cx, cy, 30, 24)
    x, y = XX[s], YY[s]
    shell = ((x - cx) / 28) ** 2 + ((y - cy) / 22) ** 2 <= 1
    cells = np.sin((x - cx) * 0.42) + np.sin((y - cy) * 0.42 + (x - cx) * 0.2)
    shade = np.clip(0.85 - ((x - cx) * 0.2 + (y - cy) * 0.9) / 34, 0, 1)
    edge = np.abs(cells) < 0.25
    frame[s][shell] = dither_ramp(np.clip(shade[shell] - edge[shell] * 0.35, 0, 1),
                                  [(50, 35, 20), (110, 75, 40), (170, 120, 60), (210, 170, 100)], PY[s][shell], PX[s][shell])
    rim = shell & (((x - cx) / 28) ** 2 + ((y - cy) / 22) ** 2 > 0.85)
    frame[s][rim] = (200, 170, 110)


def scene_kelp_forest(frame, t, spec, seed):
    """Towering kelp swaying in a sunlit forest under the sea."""
    water(frame, SUNLIT, 0.05, 0.9)
    light_rays(frame, t, seed, strength=0.5, count=8)
    seafloor(frame, 282, seed, [(60, 55, 45), (110, 100, 75), (160, 145, 105)], rough=3)
    rng = random.Random(seed)
    stalks = sorted(((rng.uniform(-5, LW + 5), rng.uniform(0.5, 1.0), rng.uniform(0, 6.3)) for _ in range(11)),
                    key=lambda k: k[1])
    for x0, near, ph in stalks:
        col = tuple(int(c * (0.5 + 0.5 * near)) for c in (150, 120, 30))
        leaf = tuple(int(c * (0.5 + 0.5 * near)) for c in (120, 150, 40))
        for i in range(0, 250, 2):
            f = i / 250
            x = x0 + math.sin(t * 0.8 + ph + f * 2.5) * 10 * f
            y = 282 - i
            pa.put(frame, x, y, col, 2 if near > 0.75 else 1)
            if i % 14 == 0 and i > 10:   # blades with gas floats
                sgn = 1 if (i // 14) % 2 else -1
                for j in range(int(10 * near) + 4):
                    pa.put(frame, x + sgn * j, y - j * 0.5 + math.sin(t + j * 0.4) * 0.8, leaf, 2 if near > 0.75 else 1)
                pa.put(frame, x + sgn, y, (190, 170, 60), 2)
    # A sea otter at the surface and some fish
    xs = XX[0]
    surf = 32 + 1.5 * np.sin(xs / 7 + t * 2)
    above = YY < surf[None, :]
    frame[above] = dither_ramp(YY[above] / 34, [(150, 200, 235), (110, 180, 225)], PY[above], PX[above])
    line = (YY >= surf[None, :]) & (YY < surf[None, :] + 1.2)
    frame[line] = (225, 245, 255)
    ox = 120 + 10 * math.sin(t * 0.3)
    disc(frame, ox, 33, 7, (90, 60, 40))
    disc(frame, ox + 8, 29, 4, (140, 110, 80))
    pa.put(frame, ox + 9, 28, (10, 10, 10), 2)
    for i in range(8):
        small_fish(frame, (i * 29 + t * (6 + i % 3)) % (LW + 20) - 10, 120 + (i * 31) % 130, 3, 1,
                   [(250, 140, 40), (200, 210, 220)][i % 2], t, i)


OCEAN_SCENES = {
    "deep_sea": scene_deep_sea, "anglerfish": scene_anglerfish, "jellyfish": scene_jellyfish,
    "whale": scene_whale, "octopus": scene_octopus, "coral_reef": scene_coral_reef, "shark": scene_shark,
    "shipwreck": scene_shipwreck, "vent": scene_vent, "submarine": scene_submarine, "squid": scene_squid,
    "ocean_surface": scene_ocean_surface, "trench": scene_trench, "fish_school": scene_fish_school,
    "sea_turtle": scene_sea_turtle, "kelp_forest": scene_kelp_forest,
}

# Keyword -> scene for sentences without explicit scenes (checked before the space keywords)
OCEAN_KEYWORDS = [
    (("anglerfish", "angler fish", "lure"), {"scene": "anglerfish"}),
    (("jellyfish", "jelly", "jellies", "man o' war"), {"scene": "jellyfish"}),
    (("whale", "whales", "orca"), {"scene": "whale"}),
    (("octopus", "octopuses", "cuttlefish"), {"scene": "octopus"}),
    (("coral", "reef", "clownfish"), {"scene": "coral_reef"}),
    (("shark", "sharks"), {"scene": "shark"}),
    (("shipwreck", "titanic", "wreck"), {"scene": "shipwreck"}),
    (("vent", "vents", "black smoker", "tube worm"), {"scene": "vent"}),
    (("submarine", "submersible", "trieste", "dive"), {"scene": "submarine"}),
    (("squid",), {"scene": "squid"}),
    (("trench", "mariana", "challenger deep"), {"scene": "trench"}),
    (("sardine", "school of fish", "dolphin"), {"scene": "fish_school"}),
    (("turtle",), {"scene": "sea_turtle"}),
    (("kelp", "otter"), {"scene": "kelp_forest"}),
    (("wave", "waves", "tide", "tides", "surface"), {"scene": "ocean_surface"}),
    (("deep sea", "abyss", "midnight zone", "twilight zone", "bioluminescen"), {"scene": "deep_sea"}),
]


def register():
    pa.SCENES.update(OCEAN_SCENES)
    pa._KEYWORD_SCENES[:0] = OCEAN_KEYWORDS


register()
