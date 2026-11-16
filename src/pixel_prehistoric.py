"""Prehistoric 8-bit scenes (DinoBytes).

Same conventions as pixel_art.py / pixel_ocean.py: shapes on the 180x320
design grid (XX/YY are design-unit coordinates of every pixel), dithered
colour ramps, and each scene paints its own background. In the HUD layout
the text boxes cover the top of the frame, so subjects live roughly between
y = 120 and the ground at y = 256.

Scenes: trex, sauropod, triceratops, stegosaurus, raptor, pterosaur,
mosasaur, plesiosaur, mammoth, impact, fossil, eggs, amber, volcano, cambrian
"""
import math
import random

import numpy as np

import pixel_art as pa
from pixel_art import LW, LH, PW, PH, XX, YY, PX, PY, dither_ramp, periodic_noise
from pixel_ocean import _win, disc, tri, poly, water, light_rays, marine_snow, swimmer, small_fish, seafloor

GROUND = 256

GREEN = [(30, 50, 25), (60, 95, 40), (100, 140, 60), (150, 180, 90)]
BROWN = [(50, 32, 20), (95, 62, 38), (145, 100, 60), (195, 150, 100)]
OLIVE = [(45, 50, 25), (85, 95, 45), (130, 140, 70), (180, 185, 110)]
GREY = [(45, 48, 55), (85, 90, 100), (130, 135, 145), (185, 188, 195)]
RUST = [(70, 30, 20), (130, 60, 35), (185, 100, 55), (230, 160, 100)]


# ------------------------------------------------------------ helpers ----
def ellipse(frame, cx, cy, rx, ry, ramp, ang=0.0, light=0.0):
    """Shaded, optionally rotated ellipse, lit from the upper left."""
    r = max(rx, ry) + 1
    s = _win(cx, cy, r, r)
    if s is None:
        return None
    dx, dy = XX[s] - cx, YY[s] - cy
    c, si = math.cos(ang), math.sin(ang)
    u, v = (dx * c + dy * si) / rx, (-dx * si + dy * c) / ry
    m = u * u + v * v <= 1
    shade = np.clip(0.62 - 0.32 * (u * 0.5 + v * 0.9) + light, 0, 1)
    frame[s][m] = dither_ramp(shade[m], ramp, PY[s][m], PX[s][m])
    return s, m


def limb(frame, x1, y1, x2, y2, w1, w2, color):
    """A tapered segment (leg, neck, horn) as a quad."""
    a = math.atan2(y2 - y1, x2 - x1) + math.pi / 2
    c, s = math.cos(a), math.sin(a)
    poly(frame, [(x1 + c * w1, y1 + s * w1), (x2 + c * w2, y2 + s * w2),
                 (x2 - c * w2, y2 - s * w2), (x1 - c * w1, y1 - s * w1)], color)
    disc(frame, x2, y2, max(0.8, w2), color)


def chain(frame, pts, w0, w1, ramp):
    """Tapered curve (tail, neck) drawn as overlapping shaded discs."""
    n = len(pts)
    for i, (x, y) in enumerate(pts):
        r = w0 + (w1 - w0) * i / max(1, n - 1)
        ellipse(frame, x, y, r, r, ramp)


def curve(x0, y0, x1, y1, bend, n=24, wave=0.0, phase=0.0):
    """Points along a quadratic curve with an optional sideways wave."""
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    nx, ny = -(y1 - y0), (x1 - x0)
    ln = math.hypot(nx, ny) or 1
    cx, cy = mx + nx / ln * bend, my + ny / ln * bend
    out = []
    for i in range(n):
        f = i / (n - 1)
        x = (1 - f) ** 2 * x0 + 2 * (1 - f) * f * cx + f ** 2 * x1
        y = (1 - f) ** 2 * y0 + 2 * (1 - f) * f * cy + f ** 2 * y1
        out.append((x + nx / ln * wave * math.sin(f * 3 + phase) * f, y + ny / ln * wave * math.sin(f * 3 + phase) * f))
    return out


def sky(frame, top, mid, bottom, horizon=GROUND):
    v = np.clip(YY / horizon, 0, 1)
    frame[:] = dither_ramp(v, [top, mid, bottom])


def mountains(frame, seed, base, height, color, rough=1.0):
    rng = random.Random(seed)
    xs = XX[0]
    prof = base - height * (0.5 + 0.5 * np.sin(xs / (28 + rng.uniform(0, 10)) + rng.uniform(0, 6))) \
        - rough * 6 * np.sin(xs / 9 + rng.uniform(0, 6))
    frame[YY >= prof[None, :]] = color


def volcano_cone(frame, t, x, base, h, w, smoke=True, lava=True):
    pts = [(x - w, base), (x - 6, base - h), (x + 6, base - h), (x + w, base)]
    poly(frame, pts, (60, 45, 45))
    poly(frame, [(x - w * 0.5, base), (x - 4, base - h), (x + 1, base - h), (x - w * 0.15, base)], (80, 60, 55))
    if lava:
        for i in range(int(h * 0.7)):
            f = i / h
            pa.put(frame, x + 2 * math.sin(i * 0.4) + f * 6, base - h + i, (255, int(120 + 80 * f), 30), 2)
    if smoke:
        for k in range(14):
            life = (t * 0.25 + k / 14) % 1
            disc(frame, x + 10 * life + 4 * math.sin(k), base - h - 4 - life * 70, 4 + life * 9,
                 tuple(int(c * (1 - life * 0.4)) for c in (90, 85, 85)))


def ground(frame, seed, ramp=OLIVE, y0=GROUND):
    g = YY >= y0
    tex = periodic_noise(XX[g] / LW * 6.28, YY[g] / 12, seed, 3)
    frame[g] = dither_ramp(np.clip(0.75 - (YY[g] - y0) / 90 + (tex - 0.5) * 0.4, 0, 1), ramp, PY[g], PX[g])


def fern(frame, x, base, h, t, phase, color):
    for side in (-1, 1):
        for i in range(6):
            a = -math.pi / 2 + side * (0.35 + i * 0.16) + 0.06 * math.sin(t * 1.3 + phase)
            ln = h * (1 - i * 0.1)
            for j in range(int(ln)):
                f = j / ln
                px_ = x + math.cos(a) * j + side * f * f * 4
                py_ = base + math.sin(a) * j + f * f * h * 0.35
                pa.put(frame, px_, py_, color, 2 if f < 0.6 else 1)


def cycad(frame, x, base, h, t, phase):
    for i in range(int(h)):
        pa.put(frame, x + math.sin(i * 0.15) * 0.8, base - i, (90, 65, 40) if i % 3 else (70, 50, 30), 3)
    for k in range(9):
        a = math.pi + k * math.pi / 8 + 0.08 * math.sin(t + phase + k)
        for j in range(22):
            f = j / 22
            pa.put(frame, x + math.cos(a) * j * 1.1, base - h + math.sin(a) * j * 0.8 + f * f * 10,
                   (60, 120, 50) if j % 4 else (90, 150, 60), 2)


def landscape(frame, t, seed, mood="day"):
    """Prehistoric backdrop: sky, distant volcano, hills, ground and plants."""
    if mood == "dusk":
        sky(frame, (40, 30, 70), (190, 90, 70), (250, 170, 90))
        disc(frame, 130, GROUND - 40, 14, (255, 210, 120))
    elif mood == "ice":
        sky(frame, (110, 150, 190), (170, 200, 220), (220, 232, 240))
    else:
        sky(frame, (70, 140, 190), (140, 190, 200), (220, 215, 170))
        disc(frame, 140, 150, 9, (255, 245, 200))
    if mood == "ice":
        mountains(frame, seed, GROUND - 10, 40, (200, 215, 230))
        mountains(frame, seed + 1, GROUND, 18, (230, 238, 245), 0.5)
        g = YY >= GROUND
        frame[g] = dither_ramp(np.clip((YY[g] - GROUND) / 70, 0, 1),
                               [(245, 248, 252), (215, 225, 238), (180, 195, 215)], PY[g], PX[g])
        return
    volcano_cone(frame, t, 40, GROUND - 20, 70, 40)
    mountains(frame, seed, GROUND - 6, 26, (90, 110, 90) if mood == "day" else (90, 60, 70))
    mountains(frame, seed + 1, GROUND, 12, (70, 95, 60) if mood == "day" else (70, 50, 55), 0.6)
    ground(frame, seed)
    rng = random.Random(seed)
    for k in range(3):
        cycad(frame, rng.choice([8, 172, 160, 20]), GROUND + 2, rng.uniform(26, 40), t, k)


def foreground_ferns(frame, t, seed):
    rng = random.Random(seed + 5)
    for k in range(6):
        fern(frame, rng.uniform(0, LW), GROUND + 14 + rng.uniform(0, 8), rng.uniform(10, 16), t, k, (50, 100, 40))


def legs(frame, t, hips, top, length, width, colors, phase=0.0, speed=2.2, stride=8, toe=5):
    """Walking legs: each hip (x, y) gets a leg reaching the ground."""
    for i, (hx, hy) in enumerate(hips):
        p = math.sin(t * speed + phase + i * math.pi)
        fx = hx + p * stride
        lift = max(0.0, math.cos(t * speed + phase + i * math.pi)) * 3
        kx, ky = (hx + fx) / 2 + 3, hy + (GROUND - hy) * 0.5
        col = colors[i % len(colors)]
        limb(frame, hx, hy, kx, ky, width, width * 0.7, col)
        limb(frame, kx, ky, fx, GROUND - lift, width * 0.7, width * 0.5, col)
        if toe:
            limb(frame, fx - 1, GROUND - lift, fx + toe, GROUND - lift + 0.5, width * 0.45, 0.8, col)


def teeth(frame, x0, x1, y, down=True, size=2.5, color=(240, 235, 215)):
    n = max(2, int((x1 - x0) / 4))
    for i in range(n):
        x = x0 + (x1 - x0) * i / (n - 1)
        tri(frame, [(x - 1.2, y), (x + 1.2, y), (x, y + (size if down else -size))], color)


def eye(frame, x, y, r=1.6):
    disc(frame, x, y, r + 0.6, (20, 15, 10))
    pa.put(frame, x - 0.4, y - 0.6, (255, 240, 200))


# ------------------------------------------------ realistic anatomy ----
def skin_texture(x, y, seed, scale=1.0):
    """Small bumpy scales plus larger mottling, as a value around 0 (-1..1)."""
    bumps = np.sin(x * 2.2 / scale + np.sin(y * 1.7 / scale) * 1.3) * np.sin(y * 2.4 / scale + np.sin(x * 1.4 / scale))
    mottle = periodic_noise(x / 22, y / 14, seed, 3) - 0.5
    return bumps * 0.5 + mottle * 1.2


def ground_shadow(frame, cx, width, y=GROUND + 1, strength=0.45):
    """Soft dark ellipse on the ground under an animal."""
    s = _win(cx, y, width + 2, 6)
    if s is None:
        return
    d = ((XX[s] - cx) / width) ** 2 + ((YY[s] - y) / 4.5) ** 2
    m = d < 1
    k = (1 - d[m]) * strength
    frame[s][m] = (frame[s][m] * (1 - k)[:, None]).astype(np.uint8)


def body_profile(frame, hx, length, us, cys, tops, bots, back, belly, seed, stripes=0.0, facing=1):
    """Side-view body drawn from control points along its length.

    u = 0 at the snout (x = hx) to 1 at the tail tip (length units behind).
    At each control point `us`, the centre line is at `cys` and the outline
    is `tops` above and `bots` below it. Shading: lit from above, darker
    back pigment fading to a pale belly (countershading), scaly texture,
    optional dark stripes across the back. Returns (slices, mask, u, rel)."""
    us = np.asarray(us, float)
    h = max(max(tops), max(bots)) + 2
    ymin, ymax = min(cys) - h, max(cys) + h
    s = _win(hx - facing * length / 2, (ymin + ymax) / 2, length / 2 + 2, (ymax - ymin) / 2 + 2)
    if s is None:
        return None
    x, y = XX[s], YY[s]
    u = (hx - x) * facing / length
    uc = np.clip(u, 0, 1)
    cy = np.interp(uc, us, cys)
    tp, bt = np.interp(uc, us, tops), np.interp(uc, us, bots)
    m = (u >= 0) & (u <= 1) & (y > cy - tp) & (y < cy + bt)
    if not m.any():
        return s, m, u, None
    rel = (y - (cy - tp)) / np.maximum(tp + bt, 1e-6)          # 0 top edge .. 1 bottom edge
    light = 1.05 - 0.8 * rel ** 1.3                              # lit from above
    rim = np.clip(1 - rel / 0.08, 0, 1) * 0.25                   # bright rim along the top
    tex = skin_texture(x, y, seed)
    v = np.clip(light * 0.78 + rim + tex * 0.1, 0, 1)
    if stripes:
        band = (np.sin(x * 0.55 + seed) > 0.55) & (rel < 0.45)
        v = np.where(band, v * (1 - stripes), v)
    is_belly = rel > 0.62
    cols = np.where(is_belly[m][:, None],
                    dither_ramp(np.clip(v[m] + 0.15, 0, 1), belly, PY[s][m], PX[s][m]),
                    dither_ramp(v[m], back, PY[s][m], PX[s][m]))
    frame[s][m] = cols
    return s, m, u, rel


def limb_shaded(frame, x1, y1, x2, y2, w1, w2, ramp, seed=0, light=0.0):
    """A tapered limb segment shaded across its width (lit from the upper left)."""
    pad = max(w1, w2) + 2
    s = _win((x1 + x2) / 2, (y1 + y2) / 2, abs(x2 - x1) / 2 + pad, abs(y2 - y1) / 2 + pad)
    if s is None:
        return
    x, y = XX[s], YY[s]
    dx, dy = x2 - x1, y2 - y1
    ln2 = dx * dx + dy * dy or 1.0
    f = np.clip(((x - x1) * dx + (y - y1) * dy) / ln2, 0, 1)
    px_, py_ = x1 + f * dx, y1 + f * dy
    dist = np.sqrt((x - px_) ** 2 + (y - py_) ** 2)
    w = w1 + (w2 - w1) * f
    m = dist <= w
    side = ((x - px_) * -dy + (y - py_) * dx) / np.sqrt(ln2) / np.maximum(w, 0.5)   # -1..1 across
    v = np.clip(0.62 - side * 0.32 + light + skin_texture(x, y, seed) * 0.07, 0, 1)
    frame[s][m] = dither_ramp(v[m], ramp, PY[s][m], PX[s][m])


def muscle(frame, cx, cy, rx, ry, ramp, ang=0.0, seed=0):
    """Rounded muscle mass (thigh, shoulder) with soft shading and texture."""
    r = max(rx, ry) + 1
    s = _win(cx, cy, r, r)
    if s is None:
        return
    dx, dy = XX[s] - cx, YY[s] - cy
    c, si = math.cos(ang), math.sin(ang)
    uu, vv = (dx * c + dy * si) / rx, (-dx * si + dy * c) / ry
    d = uu * uu + vv * vv
    m = d <= 1
    v = np.clip(0.7 - 0.35 * (uu * 0.45 + vv * 0.85) - 0.2 * d + skin_texture(XX[s], YY[s], seed) * 0.08, 0, 1)
    frame[s][m] = dither_ramp(v[m], ramp, PY[s][m], PX[s][m])


def walking_leg(frame, t, hip_x, hip_y, ramp, phase, thigh=(10, 15), length=44, speed=2.2, stride=9, seed=0,
                toes=True, claw=None, thigh_ramp=None):
    """A muscular two-part leg (thigh, shin) with a foot, stepping in a loop."""
    p = math.sin(t * speed + phase)
    lift = max(0.0, math.cos(t * speed + phase)) * 3
    fx = hip_x + p * stride
    knee_x, knee_y = hip_x + 6 + p * 2, hip_y + length * 0.5
    ankle_x, ankle_y = fx - 3, GROUND - 7 - lift
    muscle(frame, hip_x + 2, hip_y + 4, thigh[0], thigh[1], thigh_ramp or ramp, ang=0.3, seed=seed)
    limb_shaded(frame, knee_x, knee_y, ankle_x, ankle_y, thigh[0] * 0.55, thigh[0] * 0.35, ramp, seed)
    limb_shaded(frame, ankle_x, ankle_y, fx + 2, GROUND - 1 - lift, thigh[0] * 0.35, thigh[0] * 0.3, ramp, seed)
    if toes:
        for k in range(3):
            limb_shaded(frame, fx + 1, GROUND - 1 - lift, fx + 7 + k * 1.5, GROUND - lift + k * 0.3 - 0.5,
                        thigh[0] * 0.22, 0.6, ramp, seed)
    if claw:
        limb_shaded(frame, fx + 3, GROUND - 3 - lift, fx + 6, GROUND - 8 - lift, 1.0, 0.3, claw, seed)


def column_leg(frame, t, x, top_y, ramp, phase, width=8, speed=1.1, stride=4, seed=0, thigh_ramp=None):
    """A thick, tapering leg for four-legged dinosaurs and mammoths: a big
    upper muscle that blends into the body, a narrower lower leg and a foot."""
    p = math.sin(t * speed + phase)
    lift = max(0.0, math.cos(t * speed + phase)) * 2
    fx = x + p * stride
    kx, ky = x + p * stride * 0.45 + 1.5, top_y + (GROUND - top_y) * 0.55
    muscle(frame, x, top_y - 3, width * 1.35, width * 1.9, thigh_ramp or ramp, ang=0.12, seed=seed)
    limb_shaded(frame, x + 0.5, top_y + 4, kx, ky, width * 0.95, width * 0.7, ramp, seed)
    limb_shaded(frame, kx, ky, fx, GROUND - 3 - lift, width * 0.7, width * 0.6, ramp, seed)
    muscle(frame, fx + width * 0.2, GROUND - 1.5 - lift, width * 0.85, 2.4, ramp, seed=seed)
    for k in range(3):   # toenails
        pa.put(frame, fx + width * 0.5 + k * 1.6, GROUND - lift, (200, 190, 165), 2)


def neck_tube(frame, pts, widths, ramp, belly, seed):
    """A smooth tapering neck along a list of points, darker on top and pale underneath."""
    for (x1, y1), (x2, y2), w1, w2 in zip(pts, pts[1:], widths, widths[1:]):
        limb_shaded(frame, x1, y1, x2, y2, w1, w2, ramp, seed)
    for (x1, y1), (x2, y2), w1, w2 in zip(pts, pts[1:], widths, widths[1:]):
        limb_shaded(frame, x1 + w1 * 0.3, y1 + w1 * 0.45, x2 + w2 * 0.3, y2 + w2 * 0.45, w1 * 0.45, w2 * 0.45, belly, seed)


# ------------------------------------------------------------- scenes ----
TREX_BACK = [(28, 36, 22), (52, 64, 34), (84, 98, 52), (122, 134, 78), (160, 168, 110)]
TREX_BELLY = [(120, 112, 80), (165, 155, 115), (205, 195, 150), (230, 222, 185)]
TREX_LEG = [(30, 36, 24), (55, 64, 38), (88, 98, 60), (125, 133, 90)]
TREX_LEG_FAR = [(20, 24, 16), (38, 44, 28), (60, 68, 42), (85, 92, 62)]


def scene_trex(frame, t, spec, seed):
    """A Tyrannosaurus rex striding through a fern forest, jaws snapping:
    one smooth body outline (snout to tail), scaly countershaded skin,
    muscular legs and a ground shadow."""
    landscape(frame, t, seed, spec.get("mood", "day"))
    bob = 1.2 * math.sin(t * 4.4)
    sway = 5 * math.sin(t * 2.2)
    hx = 166
    ground_shadow(frame, 90, 62)
    # Far leg first (darker), then body, then near leg
    walking_leg(frame, t, 84, 190 + bob, TREX_LEG_FAR, math.pi, thigh=(13, 18), length=46, seed=seed + 1)
    us =   [0.0, 0.03, 0.10, 0.17, 0.22, 0.28, 0.37, 0.46, 0.56, 0.70, 0.85, 1.0]
    cys =  [158, 157, 156, 158, 165, 173, 181, 186, 188, 191, 194, 197]
    tops = [4.5, 9, 14, 15, 10, 13, 19, 22, 18, 10, 5, 1.2]
    bots = [4.5, 7, 10, 11, 10, 15, 21, 20, 13, 7, 3.5, 1.0]
    cys = [c + bob * (1 - u) + sway * u ** 2 for c, u in zip(cys, us)]
    res = body_profile(frame, hx, 172, us, cys, tops, bots, TREX_BACK, TREX_BELLY, seed, stripes=0.25)
    # Snapping jaws: open a wedge-shaped mouth and line it with teeth
    snap = max(0.0, math.sin(t * 1.8)) ** 3
    head_y = cys[2]
    if res is not None and snap > 0.05:
        s_, m, u, rel = res
        mouth_top = head_y + 1
        open_h = 7 * snap * np.clip((0.16 - u) / 0.16, 0, 1)
        gap = m & (u < 0.16) & (YY[s_] > mouth_top) & (YY[s_] < mouth_top + open_h)
        frame[s_][gap] = (70, 18, 22)
    jaw_x0, jaw_x1 = hx - 26, hx - 2
    teeth(frame, jaw_x0, jaw_x1, head_y + 1.2, True, 2.6 + 2 * snap)
    if snap > 0.05:
        teeth(frame, jaw_x0 + 2, jaw_x1 - 2, head_y + 1 + 7 * snap, False, 2.2)
    # Eye with a bony brow ridge, nostril, jaw line
    eye(frame, hx - 18, head_y - 6, 1.7)
    limb(frame, hx - 23, head_y - 9, hx - 13, head_y - 9.5, 1.2, 0.8, (60, 70, 40))
    pa.put(frame, hx - 3, head_y - 5, (25, 25, 18), 2)
    # Tiny two-fingered arm
    ax, ay = hx - 44, cys[5] + 9
    limb_shaded(frame, ax, ay, ax + 5, ay + 6, 2.4, 1.6, TREX_LEG, seed)
    limb_shaded(frame, ax + 5, ay + 6, ax + 9, ay + 4, 1.6, 0.7, TREX_LEG, seed)
    walking_leg(frame, t, 88, 190 + bob, TREX_LEG, 0.0, thigh=(15, 21), length=46, seed=seed,
                thigh_ramp=TREX_BACK[:4])
    foreground_ferns(frame, t, seed)


SAURO_BACK = [(48, 50, 46), (78, 80, 70), (112, 112, 96), (150, 146, 124), (190, 184, 160)]
SAURO_BELLY = [(140, 132, 110), (180, 172, 145), (215, 206, 180)]
SAURO_FAR = [(38, 40, 36), (60, 62, 54), (88, 88, 76), (115, 112, 96)]


def scene_sauropod(frame, t, spec, seed):
    """A long-necked sauropod browsing a tall tree, a herd member behind."""
    landscape(frame, t, seed, spec.get("mood", "day"))
    haze = [(80, 92, 98), (100, 112, 116), (122, 132, 134), (140, 150, 150)]
    body_profile(frame, 40, 46, [0, 0.3, 0.6, 1], [214, 212, 218, 228], [5, 9, 6, 1], [5, 7, 4, 1], haze, haze, seed)
    for x in (16, 30):
        limb_shaded(frame, x, 218, x, 236, 2.8, 2.4, haze, seed)
    pts = curve(36, 210, 50, 176, -5, 8)
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        limb_shaded(frame, x1, y1, x2, y2, 3, 2.4, haze, seed)
    sway = 3 * math.sin(t * 0.8)
    ground_shadow(frame, 82, 52)
    for i, x in enumerate((58, 100)):
        column_leg(frame, t, x, 222, SAURO_FAR, i * 1.7 + 0.8, width=7.5, seed=seed + 2)
    us =   [0.0, 0.05, 0.18, 0.30, 0.45, 0.62, 0.80, 1.0]
    cys =  [212, 210, 212, 214, 220, 228, 236, 244]
    tops = [11, 17, 22, 22, 15, 9, 5, 1.2]
    bots = [10, 15, 18, 16, 10, 6, 3, 1.0]
    body_profile(frame, 118, 120, us, cys, tops, bots, SAURO_BACK, SAURO_BELLY, seed)
    # Neck rising in a long curve to a small head in the treetop
    pts = curve(112, 204, 148 + sway, 134, -16, 12)
    widths = [9.5 - 5.5 * i / 11 for i in range(12)]
    neck_tube(frame, pts, widths, SAURO_BACK[:4], SAURO_BELLY, seed)
    hx, hy = pts[-1]
    body_profile(frame, hx + 14, 18, [0, 0.4, 1], [hy + 1, hy, hy + 1], [2.5, 5, 4.5], [2.5, 3.5, 4], SAURO_BACK,
                 SAURO_BELLY, seed)
    eye(frame, hx + 6, hy - 2, 1.2)
    for i, x in enumerate((64, 106)):
        column_leg(frame, t, x, 224, SAURO_BACK[:4], i * 1.7, width=8.5, seed=seed, thigh_ramp=SAURO_BACK[:4])
    cycad(frame, 166, GROUND + 4, 120, t, 2)
    foreground_ferns(frame, t, seed)


TRIKE_BACK = [(60, 32, 22), (100, 56, 34), (145, 86, 52), (185, 120, 76), (215, 160, 110)]
TRIKE_BELLY = [(160, 130, 100), (200, 170, 135), (225, 205, 170)]
TRIKE_FAR = [(45, 25, 18), (75, 42, 28), (110, 66, 42), (140, 90, 60)]


def scene_triceratops(frame, t, spec, seed):
    """A Triceratops with a solid bony frill and three horns, grazing."""
    landscape(frame, t, seed, spec.get("mood", "day"))
    nod = 2 * math.sin(t * 1.1)
    ground_shadow(frame, 86, 58)
    for i, x in enumerate((62, 112)):
        column_leg(frame, t, x, 218, TRIKE_FAR, i * 1.7 + 0.8, width=7.5, speed=0.9, seed=seed + 2)
    us =   [0.0, 0.10, 0.25, 0.45, 0.65, 0.82, 1.0]
    cys =  [212, 210, 206, 205, 208, 214, 222]
    tops = [12, 18, 23, 24, 19, 10, 2]
    bots = [10, 15, 20, 20, 15, 8, 1.5]
    body_profile(frame, 132, 124, us, cys, tops, bots, TRIKE_BACK, TRIKE_BELLY, seed, stripes=0.15)
    # Frill: a fan of bone behind the head, with a pale knobbed rim
    fx, fy = 132, 192 + nod
    s_ = _win(fx, fy, 28, 28)
    d = np.sqrt((XX[s_] - fx) ** 2 + (YY[s_] - fy) ** 2)
    a = np.arctan2(YY[s_] - fy, XX[s_] - fx)
    fr = (d < 26) & (np.abs(a + 0.85) < 1.45)
    v = np.clip(0.45 + 0.4 * (1 - d / 26) + skin_texture(XX[s_], YY[s_], seed) * 0.08, 0, 1)
    frame[s_][fr] = dither_ramp(v[fr], [(110, 45, 35), (160, 75, 50), (205, 115, 75), (230, 160, 110)], PY[s_][fr], PX[s_][fr])
    rim = fr & (d > 23.5)
    frame[s_][rim] = (230, 205, 160)
    for k in range(7):
        aa = -0.85 - 1.35 + k * 0.45
        disc(frame, fx + math.cos(aa) * 26, fy + math.sin(aa) * 26, 1.7, (235, 212, 165))
    # Head with a hooked beak
    body_profile(frame, 168, 46, [0, 0.12, 0.4, 0.75, 1], [214 + nod, 210 + nod, 206 + nod, 205, 206],
                 [3, 7, 11, 13, 14], [3, 6, 9, 12, 13], TRIKE_BACK, TRIKE_BELLY, seed)
    tri(frame, [(162, 206 + nod), (170, 215 + nod), (161, 216 + nod)], (70, 55, 40))
    # Two long brow horns and a short nose horn, pale with darker tips
    for bx, by, tx, ty in ((146, 199, 172, 178), (151, 201, 175, 184)):
        limb_shaded(frame, bx, by + nod, tx, ty + nod, 2.8, 0.5, [(150, 140, 115), (210, 200, 170), (240, 232, 205)], seed)
    limb_shaded(frame, 163, 205 + nod, 168, 198 + nod, 2.0, 0.4, [(150, 140, 115), (215, 205, 175)], seed)
    eye(frame, 150, 203 + nod)
    for i, x in enumerate((68, 118)):
        column_leg(frame, t, x, 220, TRIKE_BACK[:4], i * 1.7, width=8.5, speed=0.9, seed=seed, thigh_ramp=TRIKE_BACK[:4])
    foreground_ferns(frame, t, seed)


STEGO_BACK = [(45, 52, 26), (78, 88, 42), (115, 125, 64), (155, 162, 96), (195, 198, 140)]
STEGO_BELLY = [(150, 145, 105), (190, 185, 140), (220, 215, 175)]
STEGO_FAR = [(35, 40, 20), (58, 66, 32), (85, 94, 48), (115, 122, 70)]


def scene_stegosaurus(frame, t, spec, seed):
    """A Stegosaurus with two rows of back plates and a swinging spiked tail."""
    landscape(frame, t, seed, spec.get("mood", "day"))
    swing = 6 * math.sin(t * 1.4)
    ground_shadow(frame, 84, 62)
    for i, x in enumerate((66, 112)):
        column_leg(frame, t, x, 222, STEGO_FAR, i * 1.7 + 0.8, width=7, speed=0.9, seed=seed + 2)
    us =   [0.0, 0.06, 0.15, 0.30, 0.45, 0.60, 0.75, 0.90, 1.0]
    cys =  [232, 230, 222, 212, 206, 208, 214, 220 + swing * 0.6, 222 + swing]
    tops = [4, 6, 12, 20, 25, 21, 12, 6, 3]
    bots = [3, 5, 12, 18, 20, 16, 9, 5, 2.5]
    # Plates first, so the body overlaps their bases
    for i in range(11):
        f = i / 10
        u = 0.18 + f * 0.62
        x = 136 - u * 140
        y = float(np.interp(u, us, cys)) - float(np.interp(u, us, tops)) + 3
        h = 8 + 16 * math.sin(f * math.pi)
        for off, col in ((-2.5, (150, 70, 45)), (2.0, (205, 110, 65))):
            tri(frame, [(x - 5 + off, y + 3), (x + 5 + off, y + 3), (x + 1 + off, y - h)], col)
            tri(frame, [(x - 2 + off, y + 1), (x + 2 + off, y + 1), (x + 1 + off, y - h * 0.7)],
                (225, 150, 95) if off > 0 else (175, 90, 55))
    body_profile(frame, 136, 140, us, cys, tops, bots, STEGO_BACK, STEGO_BELLY, seed, stripes=0.12)
    # Four tail spikes (the thagomizer)
    tx, ty = 136 - 0.93 * 140, 220 + swing * 0.8
    for dx, dy, ex, ey in ((0, -2, -7, -13), (3, -2, -3, -14), (0, 1, -11, -5), (3, 1, -7, -3)):
        limb_shaded(frame, tx + dx, ty + dy, tx + ex, ty + ey, 1.8, 0.4, [(160, 150, 120), (225, 215, 185), (245, 238, 215)], seed)
    eye(frame, 130, 229, 1.2)
    for i, x in enumerate((72, 118)):
        column_leg(frame, t, x, 224, STEGO_BACK[:4], i * 1.7, width=8, speed=0.9, seed=seed, thigh_ramp=STEGO_BACK[:4])
    foreground_ferns(frame, t, seed)


RAPTOR_BACK = [(55, 35, 22), (95, 62, 36), (140, 95, 55), (185, 135, 85), (220, 180, 125)]
RAPTOR_BELLY = [(170, 150, 120), (210, 192, 160), (235, 222, 195)]


def scene_raptor(frame, t, spec, seed):
    """A small feathered dromaeosaur (about turkey-sized) running past, sickle claws up."""
    landscape(frame, t, seed, spec.get("mood", "dusk"))
    fern(frame, 150, GROUND + 2, 30, t, 1, (55, 110, 45))
    x = raptor_x(t)
    run = 8.0
    ground_shadow(frame, x - 4, 20, strength=0.35)
    walking_leg(frame, t, x - 6, 218, [(45, 30, 20), (75, 50, 32), (110, 75, 48)], math.pi, thigh=(5, 7), length=26,
                speed=run, stride=8, seed=seed + 1, claw=[(200, 190, 170), (240, 235, 220)])
    us =   [0.0, 0.05, 0.12, 0.20, 0.30, 0.42, 0.55, 0.75, 1.0]
    cys =  [197, 196, 196, 200, 207, 212, 213, 211, 208]
    tops = [2, 4, 6, 5, 8, 11, 10, 6, 3]
    bots = [2, 3.5, 5, 5, 9, 11, 8, 4, 2.5]
    res = body_profile(frame, x + 30, 76, us, cys, tops, bots, RAPTOR_BACK, RAPTOR_BELLY, seed, stripes=0.2)
    if res is not None and res[3] is not None:   # feather texture: fine light streaks
        s_, m, u, rel = res
        streak = m & (np.sin(XX[s_] * 1.6 + YY[s_] * 3.1) > 0.85) & (rel < 0.6)
        frame[s_][streak] = (225, 185, 125)
    for k in range(7):   # tail-tip feather fan
        limb(frame, x + 30 - 76 + 2, 208, x + 30 - 76 - 6 - k * 0.8, 203 + k * 1.6, 0.8, 0.5, (205, 160, 100))
    teeth(frame, x + 22, x + 29, 197.5, True, 1.3)
    eye(frame, x + 23, 194, 1.1)
    # Feathered arm with long wing feathers
    ax, ay = x + 14, 207
    limb_shaded(frame, ax, ay, ax + 4, ay + 9, 2.0, 1.4, RAPTOR_BACK, seed)
    for k in range(6):
        limb(frame, ax + 1, ay + 3 + k * 1.2, ax - 4 + k, ay + 13 + k * 0.6, 0.9, 0.5, (150 + k * 12, 100 + k * 9, 60))
    walking_leg(frame, t, x - 2, 220, [(60, 40, 25), (100, 68, 42), (145, 100, 62)], 0.0, thigh=(6, 8), length=26,
                speed=run, stride=8, seed=seed, claw=[(210, 200, 180), (245, 240, 225)], thigh_ramp=RAPTOR_BACK[:4])
    foreground_ferns(frame, t, seed)


def raptor_x(t):
    return 60 + (t * 14) % 80


def scene_pterosaur(frame, t, spec, seed):
    """Pterosaurs soaring over a cliff and sea at dusk."""
    sky(frame, (50, 40, 90), (200, 110, 90), (250, 190, 120), horizon=230)
    disc(frame, 120, 210, 16, (255, 220, 140))
    sea = YY >= 226
    frame[sea] = dither_ramp(np.clip((YY[sea] - 226) / 40, 0, 1), [(200, 120, 90), (90, 70, 100), (40, 40, 70)], PY[sea], PX[sea])
    poly(frame, [(0, 170), (36, 176), (48, 230), (0, 260)], (60, 45, 50))
    poly(frame, [(0, 230), (60, 236), (80, 320), (0, 320)], (45, 35, 40))
    for k, (cx, cy, sc, ph) in enumerate(((100, 150, 1.0, 0.0), (40, 132, 0.5, 1.7), (150, 128, 0.4, 3.1))):
        flap = math.sin(t * 2.5 + ph)
        x = cx + 6 * math.sin(t * 0.5 + ph)
        y = cy + 3 * math.sin(t * 0.9 + ph)
        span = 46 * sc
        col = (70, 45, 45) if k else (110, 70, 55)
        tip_y = y - flap * 14 * sc
        tri(frame, [(x - 4 * sc, y), (x + 4 * sc, y + 2 * sc), (x - span, tip_y)], col)
        tri(frame, [(x - 4 * sc, y), (x + 4 * sc, y + 2 * sc), (x + span, tip_y)], col)
        ellipse(frame, x, y + 1, 7 * sc + 1, 3 * sc + 1, [(60, 40, 35), (130, 90, 70), (180, 130, 100)])
        # Long beak and back-swept crest
        limb(frame, x + 5 * sc, y - 1, x + 20 * sc, y + 1, 1.8 * sc + 0.5, 0.4, (200, 170, 120))
        limb(frame, x + 5 * sc, y - 2, x - 6 * sc, y - 9 * sc, 1.6 * sc + 0.4, 0.4, (210, 90, 60))


MOSA_BACK = [(18, 32, 42), (32, 54, 66), (52, 80, 92), (80, 112, 122), (120, 150, 156)]
MOSA_BELLY = [(140, 150, 140), (185, 192, 178), (215, 220, 205)]
MOSA_FIN = [(16, 28, 36), (30, 48, 58), (48, 72, 84), (72, 100, 110)]


def _sea_backdrop(frame, t, seed):
    water(frame, [(40, 130, 170), (20, 80, 130), (8, 40, 80), (3, 18, 40)], 0.1, 1.0)
    light_rays(frame, t, seed, strength=0.3)
    marine_snow(frame, t, seed, 80, (110, 160, 190))


def _ammonites(frame, t, seed, count=4, behind=True):
    for i in range(count):
        ax, ay = (i * 47 + t * 3 + (0 if behind else 20)) % (LW + 20) - 10, 140 + (i * 31) % 90
        s = _win(ax, ay, 7, 7)
        if s is None:
            continue
        d = np.sqrt((XX[s] - ax) ** 2 + (YY[s] - ay) ** 2)
        a = np.arctan2(YY[s] - ay, XX[s] - ax)
        shell = d < 5.5
        frame[s][shell] = dither_ramp(0.5 + 0.5 * np.sin(d[shell] * 2.2 + a[shell]),
                                      [(120, 80, 50), (200, 160, 110), (235, 210, 170)], PY[s][shell], PX[s][shell])
        for k in range(4):   # tentacles trailing from the shell opening
            limb(frame, ax - 4, ay + 1, ax - 8 - k * 0.6, ay + 3 + k * 1.5 + math.sin(t * 2 + k), 0.6, 0.4, (180, 140, 100))


def mosasaur_geometry(t):
    hx = 120 + t * 5
    cy = 196 + 4 * math.sin(t * 0.8)
    return hx, cy, 160


def scene_mosasaur(frame, t, spec, seed):
    """A mosasaur, a giant sea reptile related to lizards, gliding past ammonites:
    a long crocodile-like head, paddle flippers and a shark-like tail fin."""
    _sea_backdrop(frame, t, seed)
    _ammonites(frame, t, seed)
    hx, cy, L = mosasaur_geometry(t)
    wave = 5 * math.sin(t * 2.0)
    # Far flippers (darker), then body
    for u0, ph in ((0.27, 0.6), (0.55, 2.1)):
        bx = hx - u0 * L + 3
        a = 0.9 + 0.35 * math.sin(t * 2 + ph)
        limb_shaded(frame, bx, cy + 4, bx - 13 * math.cos(a) - 2, cy + 4 + 13 * math.sin(a), 3.6, 1.4, MOSA_FIN, seed + 3)
    us =   [0.0, 0.04, 0.10, 0.17, 0.23, 0.32, 0.45, 0.60, 0.75, 0.88, 1.0]
    cys =  [cy + 1, cy, cy - 1, cy - 1.5, cy, cy + 1, cy + 2, cy + 3, cy + 4, cy + 5, cy + 6]
    cys = [c + wave * u ** 2 for c, u in zip(cys, us)]
    tops = [2.2, 4.2, 6.2, 7.5, 7.5, 11, 12.5, 10.5, 6.5, 3.5, 2]
    bots = [2.2, 4, 5.5, 7, 8, 11, 12.5, 9.5, 5.5, 3, 2]
    res = body_profile(frame, hx, L, us, cys, tops, bots, MOSA_BACK, MOSA_BELLY, seed, stripes=0.12)
    # Jaws open now and then
    snap = max(0.0, math.sin(t * 1.3)) ** 4
    if res is not None and res[3] is not None and snap > 0.05:
        s_, m, u, rel = res
        gap = m & (u < 0.15) & (YY[s_] > cys[2] - 0.2) & (YY[s_] < cys[2] + 5.5 * snap * np.clip((0.15 - u) / 0.15, 0, 1))
        frame[s_][gap] = (70, 25, 30)
    teeth(frame, hx - 23, hx - 2, cys[2] + 0.2, True, 2.0 + 1.2 * snap)
    if snap > 0.05:
        teeth(frame, hx - 21, hx - 4, cys[2] + 5 * snap, False, 1.8)
    eye(frame, hx - 26, cys[3] - 3.5, 1.4)
    # Shark-like tail fin, bigger lobe pointing down (as fossils show)
    tx, ty = hx - L + 2, cys[-1]
    tri(frame, [(tx + 10, ty - 1), (tx - 12, ty + 18 + wave), (tx + 2, ty + 3)], MOSA_FIN[2])
    tri(frame, [(tx + 10, ty), (tx - 6, ty - 9 + wave * 0.5), (tx + 2, ty + 1)], MOSA_FIN[1])
    # Near flippers
    for u0, ph in ((0.25, 0.0), (0.53, 1.5)):
        bx = hx - u0 * L
        a = 0.9 + 0.35 * math.sin(t * 2 + ph)
        limb_shaded(frame, bx, cy + 6, bx - 15 * math.cos(a) - 2, cy + 6 + 15 * math.sin(a), 4.2, 1.6, MOSA_BACK[:4], seed)
    _ammonites(frame, t, seed + 9, 2, behind=False)


PLESIO_BACK = [(36, 42, 30), (62, 72, 50), (95, 106, 74), (135, 145, 108), (175, 182, 145)]
PLESIO_BELLY = [(150, 150, 120), (190, 190, 155), (220, 220, 190)]


def plesiosaur_geometry(t):
    cx, cy = 70 + t * 3, 212 + 3 * math.sin(t)
    return cx, cy


def scene_plesiosaur(frame, t, spec, seed):
    """A long-necked plesiosaur flying underwater on four long flippers
    through a school of fish."""
    _sea_backdrop(frame, t, seed)
    for i in range(16):
        small_fish(frame, (i * 23 + t * 9) % (LW + 20) - 10, 130 + (i * 37) % 60, 2.5, 1, (200, 210, 190), t, i)
    cx, cy = plesiosaur_geometry(t)
    row = math.sin(t * 2)

    def flipper(fx, fy, ph, ramp, scale):
        a = 0.55 + 0.55 * math.sin(t * 2 + ph)
        ex, ey = fx - 24 * scale * math.cos(a), fy + 20 * scale * math.sin(a)
        mx, my = (fx + ex) / 2 - 2, (fy + ey) / 2 + 1
        limb_shaded(frame, fx, fy, mx, my, 5 * scale, 3.5 * scale, ramp, seed)
        limb_shaded(frame, mx, my, ex, ey, 3.5 * scale, 0.8, ramp, seed)

    flipper(cx + 14, cy + 2, 0.4, PLESIO_BACK[:3], 0.9)       # far front
    flipper(cx - 16, cy + 2, 1.9, PLESIO_BACK[:3], 0.85)      # far back
    # Body (broad, short tail) and long neck
    body_profile(frame, cx + 28, 64, [0, 0.15, 0.4, 0.62, 0.8, 1.0], [cy - 2, cy - 1, cy, cy + 1, cy + 2, cy + 3],
                 [6, 11, 13, 10, 5, 1.5], [6, 11, 13, 10, 4, 1.2], PLESIO_BACK, PLESIO_BELLY, seed, stripes=0.1)
    pts = curve(cx + 22, cy - 3, cx + 74, cy - 40 + 3 * row, -10, 14)
    widths = [6.5 - 3.5 * i / 13 for i in range(14)]
    neck_tube(frame, pts, widths, PLESIO_BACK[:4], PLESIO_BELLY, seed)
    hx, hy = pts[-1]
    body_profile(frame, hx + 12, 15, [0, 0.4, 1], [hy + 0.5, hy, hy], [1.5, 3.5, 3.5], [1.5, 2.5, 3], PLESIO_BACK,
                 PLESIO_BELLY, seed)
    teeth(frame, hx + 3, hx + 11, hy + 0.8, True, 1.6)
    eye(frame, hx + 3, hy - 1.5, 1.0)
    flipper(cx + 12, cy + 5, 0.0, PLESIO_BACK[:4], 1.0)       # near front
    flipper(cx - 18, cy + 5, 1.5, PLESIO_BACK[:4], 0.95)      # near back


MAMMOTH_FUR = [(38, 22, 14), (66, 40, 24), (100, 64, 38), (140, 96, 58), (180, 135, 88)]
MAMMOTH_FUR_FAR = [(30, 18, 11), (50, 30, 18), (75, 48, 28), (105, 70, 42)]
IVORY = [(150, 130, 100), (205, 190, 160), (235, 225, 200), (250, 245, 230)]


def scene_mammoth(frame, t, spec, seed):
    """A woolly mammoth walking through falling snow: domed head, shoulder
    hump, shaggy fur hanging below the body, curving tusks and a swinging trunk."""
    landscape(frame, t, seed, "ice")
    sw = 3 * math.sin(t * 1.2)
    ground_shadow(frame, 88, 56, strength=0.25)
    for i, x in enumerate((64, 108)):
        column_leg(frame, t, x, 214, MAMMOTH_FUR_FAR, i * 1.7 + 0.8, width=7.5, speed=0.9, seed=seed + 2)
    hx, L = 138, 100
    us =   [0.0, 0.07, 0.16, 0.26, 0.36, 0.50, 0.66, 0.82, 0.94, 1.0]
    cys =  [194, 188, 184, 190, 193, 196, 198, 200, 202, 205]
    tops = [9, 16, 19, 14, 18, 16, 14, 11, 7, 3]
    bots = [13, 15, 14, 17, 21, 22, 20, 16, 9, 4]
    res = body_profile(frame, hx, L, us, cys, tops, bots, MAMMOTH_FUR, MAMMOTH_FUR[1:], seed)
    if res is not None and res[3] is not None:   # fur streaks running down the body
        s_, m, u, rel = res
        streak = m & (np.sin(XX[s_] * 2.3 + np.sin(YY[s_] * 0.6) * 2) > 0.7)
        frame[s_][streak] = (frame[s_][streak] * 0.72).astype(np.uint8)
    # Shaggy fringe of long hair hanging below the belly and chest
    rng = np.random.default_rng(seed)
    for k in range(70):
        u = rng.uniform(0.08, 0.9)
        x = hx - u * L
        y = float(np.interp(u, us, cys)) + float(np.interp(u, us, bots)) - 1
        ln = rng.uniform(4, 9)
        swing = math.sin(t * 1.5 + k) * 0.8
        limb(frame, x, y, x - 1 + swing, y + ln, 0.9, 0.4, MAMMOTH_FUR[rng.integers(0, 3)])
    # Small furry ear, eye
    muscle(frame, hx - 22, 188, 5, 7, MAMMOTH_FUR, ang=0.2, seed=seed)
    eye(frame, hx - 12, 186, 1.3)
    # Trunk: a tapering tube with wrinkle rings
    pts = curve(hx - 4, 196, hx - 2 + sw, 238, 8, 14)
    widths = [5.5 - 3 * i / 13 for i in range(14)]
    for (x1, y1), (x2, y2), w1, w2 in zip(pts, pts[1:], widths, widths[1:]):
        limb_shaded(frame, x1, y1, x2, y2, w1, w2, MAMMOTH_FUR[1:], seed)
    for i in range(1, 13, 2):
        x, y = pts[i]
        limb(frame, x - widths[i] * 0.8, y, x + widths[i] * 0.8, y + 0.4, 0.4, 0.4, MAMMOTH_FUR[0])
    # Long tusks curving out and up
    for k, off in enumerate((-3, 2)):
        tusk = curve(hx - 6 + off, 204, hx + 26 + off, 188 - k * 2, 16, 14)
        tw = [3.2 - 2.2 * i / 13 for i in range(14)]
        for (x1, y1), (x2, y2), w1, w2 in zip(tusk, tusk[1:], tw, tw[1:]):
            limb_shaded(frame, x1, y1, x2, y2, w1, w2, IVORY if k else IVORY[:3], seed)
    for i, x in enumerate((70, 114)):
        column_leg(frame, t, x, 216, MAMMOTH_FUR[:4], i * 1.7, width=8.5, speed=0.9, seed=seed, thigh_ramp=MAMMOTH_FUR[:4])
    # Snow
    srng = np.random.default_rng(seed + 3)
    for i in range(160):
        x = (srng.uniform(0, LW) + 6 * math.sin(t * 0.8 + i)) % LW
        y = (srng.uniform(0, LH) + t * srng.uniform(6, 14)) % LH
        pa.put(frame, x, y, (255, 255, 255), 3 if i % 4 == 0 else 2)


def scene_impact(frame, t, spec, seed):
    """The asteroid strike: a fireball streaks in, then a flash and blast wave."""
    phase = (t % 8) / 8
    sky(frame, (20, 20, 50), (120, 70, 80), (230, 150, 90), horizon=230)
    mountains(frame, seed, 236, 18, (50, 40, 45))
    ground(frame, seed, [(40, 30, 25), (80, 60, 40), (120, 95, 60)], 236)
    if phase < 0.55:
        f = phase / 0.55
        x, y = 170 - f * 100, 110 + f * 120
        for k in range(40):   # glowing trail
            g = k / 40
            disc(frame, x + g * 70, y - g * 84, 7 * (1 - g) + 1, (255, int(220 - 120 * g), int(150 - 140 * g)))
        disc(frame, x, y, 8, (255, 250, 230))
    else:
        f = (phase - 0.55) / 0.45
        cx, cy = 70, 232
        d = np.sqrt((XX - cx) ** 2 + ((YY - cy) * 1.6) ** 2)
        r = 20 + f * 220
        flash = np.clip(1 - d / r, 0, 1) * (1 - f * 0.6)
        sel = flash > 0.02
        frame[sel] = np.clip(frame[sel] + (flash[sel][:, None] * np.array([255, 200, 120])), 0, 255).astype(np.uint8)
        ring = (np.abs(d - r) < 4) & (YY < 240)
        frame[ring] = (255, 230, 170)
        for k in range(30):   # flying debris
            a = -math.pi * (0.1 + 0.8 * k / 29)
            dist = f * (60 + (k * 37) % 80)
            pa.put(frame, cx + math.cos(a) * dist, cy + math.sin(a) * dist * 0.8 + f * f * 40, (255, 150, 60), 2)


def scene_fossil(frame, t, spec, seed):
    """A dinosaur skeleton revealed in layers of rock, with a brush sweeping dust."""
    bands = [(150, 110, 75), (175, 135, 90), (130, 95, 70), (190, 155, 110), (120, 90, 65), (165, 125, 85)]
    wav = 4 * np.sin(XX / 25 + seed)
    idx = np.clip(((YY + wav - 100) / 34).astype(int), 0, len(bands) - 1)
    base = np.array(bands)[idx]
    tex = periodic_noise(XX / LW * 6.28, YY / 20, seed, 3)
    frame[:] = np.clip(base * (0.8 + 0.35 * tex[..., None]), 0, 255).astype(np.uint8)
    bone = (238, 228, 205)
    shade = (190, 175, 150)
    # Spine and tail
    spine = curve(24, 196, 132, 178, -12, 30)
    for i, (x, y) in enumerate(spine):
        disc(frame, x, y, 2.4 - i * 0.03, bone if i % 2 else shade)
    tail = curve(24, 196, 2, 220, 4, 10)
    for x, y in tail:
        disc(frame, x, y, 1.4, bone)
    # Ribs
    for i in range(10):
        x, y = spine[6 + i]
        pts = curve(x, y, x - 4, y + 26 - abs(i - 4.5) * 2, 3, 10)
        for px_, py_ in pts:
            pa.put(frame, px_, py_, bone, 2)
    # Skull with jaw and teeth
    sx, sy = 132, 168
    poly(frame, [(sx, sy - 6), (sx + 24, sy - 4), (sx + 28, sy + 2), (sx + 2, sy + 6)], bone)
    disc(frame, sx + 8, sy - 1, 3, (90, 70, 55))
    poly(frame, [(sx + 2, sy + 7), (sx + 26, sy + 6), (sx + 24, sy + 10), (sx + 4, sy + 11)], shade)
    teeth(frame, sx + 6, sx + 24, sy + 6, False, 2.2, (250, 245, 230))
    # Legs
    for hx in (40, 60):
        limb(frame, hx, 196, hx + 6, 222, 3, 2, bone)
        limb(frame, hx + 6, 222, hx - 2, 246, 2, 1.5, bone)
        limb(frame, hx - 2, 246, hx + 8, 248, 1.5, 0.8, bone)
    # Brush sweeping
    bx = 100 + 22 * math.sin(t * 2)
    limb(frame, bx, 238, bx + 16, 222, 1.6, 1.6, (150, 90, 40))
    poly(frame, [(bx - 6, 236), (bx + 2, 236), (bx + 3, 246), (bx - 7, 246)], (60, 50, 40))
    rng = np.random.default_rng(int(t * 12))
    for _ in range(25):
        pa.put(frame, bx + rng.normal(0, 6), 246 + rng.uniform(-6, 2), (220, 190, 140))


def scene_eggs(frame, t, spec, seed):
    """A nest of dinosaur eggs, one cracking open."""
    landscape(frame, t, seed, "day")
    nx, ny = 92, 244
    ellipse(frame, nx, ny + 2, 46, 13, [(80, 60, 35), (130, 100, 60), (170, 140, 90)])
    rng = random.Random(seed)
    for i in range(70):   # twigs
        a = rng.uniform(0, math.pi * 2)
        x, y = nx + math.cos(a) * rng.uniform(30, 46), ny + math.sin(a) * rng.uniform(6, 12)
        limb(frame, x, y, x + rng.uniform(-6, 6), y + rng.uniform(-2, 2), 0.8, 0.6, (110, 80, 45))
    crack = min(1.0, max(0.0, (t % 7) / 5))
    for k, ex in enumerate((62, 80, 100, 118)):
        ey = ny - 8 - (k % 2) * 3
        if k == 2 and crack > 0.6:
            continue
        ellipse(frame, ex, ey, 8, 11, [(170, 160, 140), (215, 205, 185), (245, 240, 225)])
        for j in range(5):   # speckles
            pa.put(frame, ex - 4 + (j * 13) % 8, ey - 6 + (j * 7) % 12, (150, 120, 90))
    ex, ey = 100, ny - 8
    if crack <= 0.6:
        for j in range(int(crack * 14)):
            pa.put(frame, ex - 5 + j * 0.8, ey - 2 + (2 if j % 2 else -1), (60, 50, 40))
    else:
        poly(frame, [(ex - 8, ey + 2), (ex + 8, ey + 2), (ex + 7, ey + 10), (ex - 7, ey + 10)], (230, 222, 205))
        peek = min(1, (crack - 0.6) * 4)
        ellipse(frame, ex + 2, ey - 2 * peek, 7, 6, [(100, 130, 70), (140, 170, 90), (180, 200, 120)])
        eye(frame, ex + 4, ey - 4 * peek, 1.4)
        for k in range(5):
            tri(frame, [(ex - 9 + k * 4, ey + 2), (ex - 6 + k * 4, ey + 2), (ex - 7.5 + k * 4, ey - 2)], (240, 235, 220))
    foreground_ferns(frame, t, seed)


def scene_amber(frame, t, spec, seed):
    """A glowing drop of amber with an ancient insect trapped inside."""
    frame[:] = dither_ramp(np.clip(YY / LH, 0, 1), [(30, 20, 10), (55, 35, 18), (25, 15, 8)])
    cx, cy = 90, 196
    s = _win(cx, cy, 52, 46)
    x, y = XX[s], YY[s]
    edge = 44 + 4 * np.sin(np.arctan2(y - cy, x - cx) * 3 + seed)
    d = np.sqrt(((x - cx) * 0.95) ** 2 + ((y - cy) * 1.15) ** 2)
    m = d < edge
    glow = np.clip(1 - d / edge, 0, 1)
    tex = periodic_noise(x / 18, y / 18, seed, 3)
    v = np.clip(0.35 + glow * 0.6 + (tex - 0.5) * 0.25 + 0.08 * math.sin(t * 1.5), 0, 1)
    frame[s][m] = dither_ramp(v[m], [(120, 50, 10), (190, 100, 20), (240, 160, 40), (255, 220, 120)], PY[s][m], PX[s][m])
    # The trapped insect: a mosquito-like fly
    ix, iy = cx - 2, cy + 2
    ellipse(frame, ix, iy, 9, 3.5, [(40, 25, 10), (70, 45, 20), (100, 70, 35)], ang=0.2)
    ellipse(frame, ix + 10, iy - 2, 3.5, 3, [(40, 25, 10), (80, 50, 25)])
    limb(frame, ix + 12, iy - 2, ix + 20, iy + 2, 0.6, 0.4, (60, 35, 15))
    for k, (dx, dy) in enumerate(((-4, 10), (0, 12), (4, 11), (-6, 9), (2, 13), (6, 10))):
        limb(frame, ix - 2 + k * 2, iy + 2, ix - 2 + k * 2 + dx * 0.6, iy + dy, 0.5, 0.4, (60, 35, 15))
    for side in (-1, 1):
        tri(frame, [(ix + 2, iy - 2), (ix - 14, iy - 9 * side - 2), (ix - 6, iy - 1)], (200, 150, 70))
    # Bubbles and a sparkle
    for k in range(6):
        disc(frame, cx - 25 + k * 9, cy - 22 + (k * 13) % 30, 1.4, (255, 230, 160))
    if math.sin(t * 2) > 0.3:
        for dx, dy in ((0, 0), (-3, 0), (3, 0), (0, -3), (0, 3)):
            pa.put(frame, cx + 20 + dx, cy - 26 + dy, (255, 255, 230))


def scene_volcano(frame, t, spec, seed):
    """An erupting volcano over a prehistoric forest, pterosaurs in the distance."""
    sky(frame, (40, 25, 40), (150, 70, 50), (230, 140, 70))
    volcano_cone(frame, t, 92, GROUND - 4, 100, 70)
    glow = np.clip(1 - np.sqrt((XX - 92) ** 2 + (YY - (GROUND - 104)) ** 2) / 50, 0, 1)
    sel = glow > 0.05
    frame[sel] = np.clip(frame[sel] + glow[sel][:, None] * np.array([200, 90, 20]), 0, 255).astype(np.uint8)
    rng = np.random.default_rng(seed)
    for k in range(24):   # lava bombs
        life = (t * 0.6 + k / 24) % 1
        vx, vy = rng.uniform(-30, 30), rng.uniform(40, 70)
        x = 92 + vx * life
        y = GROUND - 104 - vy * life + 70 * life * life
        disc(frame, x, y, 1.6, (255, int(200 - 120 * life), 40))
    mountains(frame, seed, GROUND, 14, (40, 30, 30), 0.7)
    ground(frame, seed, [(30, 25, 20), (60, 45, 30), (90, 70, 45)])
    for k in range(3):
        x = (k * 61 + t * 8) % (LW + 20) - 10
        y = 135 + k * 9
        f = math.sin(t * 3 + k)
        tri(frame, [(x, y), (x - 6, y - f * 3), (x - 2, y + 1)], (30, 20, 25))
        tri(frame, [(x, y), (x + 6, y - f * 3), (x + 2, y + 1)], (30, 20, 25))
    for k in range(4):
        cycad(frame, (8, 30, 150, 172)[k], GROUND + 4, 24 + k * 3, t, k)


def scene_cambrian(frame, t, spec, seed):
    """The Cambrian sea floor: trilobites crawling and a predator swimming over."""
    water(frame, [(30, 110, 130), (15, 70, 100), (8, 40, 70), (3, 20, 40)], 0.1, 1.0)
    light_rays(frame, t, seed, strength=0.25)
    seafloor(frame, 238, seed, [(60, 60, 50), (110, 105, 80), (160, 150, 110)])
    # Sponges and simple stalks
    rng = random.Random(seed)
    for k in range(6):
        x = rng.uniform(5, 175)
        for i in range(int(rng.uniform(10, 24))):
            pa.put(frame, x + math.sin(t + i * 0.3 + k) * i * 0.08, 240 - i, (200, 140, 90) if k % 2 else (150, 170, 110), 3)
    # Trilobites
    for k in range(5):
        x = (rng.uniform(0, LW) + t * (3 + k)) % (LW + 20) - 10
        y = 244 + (k * 7) % 12
        ellipse(frame, x, y, 8, 4.5, [(60, 45, 35), (110, 85, 60), (160, 130, 95)])
        for j in range(5):
            frame_x = x - 6 + j * 3
            pa.put(frame, frame_x, y - 2, (60, 45, 35))
        disc(frame, x + 7, y, 2.5, (130, 100, 70))
        for side in (-1, 1):
            for j in range(3):
                pa.put(frame, x - 3 + j * 3, y + side * 5 + math.sin(t * 6 + j) * 0.6, (90, 70, 50))
    # Anomalocaris-like predator: segmented body with side flaps and grasping arms
    ax, ay = 40 + (t * 10) % 120, 170 + 4 * math.sin(t)
    for i in range(10):
        f = i / 9
        x = ax - i * 5
        flap = math.sin(t * 5 - i * 0.7) * 3
        tri(frame, [(x, ay - 3), (x - 4, ay - 3), (x - 2, ay - 9 - flap)], (170, 90, 80))
        tri(frame, [(x, ay + 3), (x - 4, ay + 3), (x - 2, ay + 9 + flap)], (170, 90, 80))
        ellipse(frame, x, ay, 4 - f * 1.5, 4 - f * 1.5, [(110, 50, 45), (170, 90, 75), (210, 140, 110)])
    for side in (-1, 1):
        pts = curve(ax + 3, ay + side * 2, ax + 12, ay + side * 2 + 10, -side * 5, 8)
        for x, y in pts:
            disc(frame, x, y, 1.1, (200, 120, 100))
    eye(frame, ax + 2, ay - 4, 1.4)


PREHISTORIC_SCENES = {
    "trex": scene_trex, "sauropod": scene_sauropod, "triceratops": scene_triceratops,
    "stegosaurus": scene_stegosaurus, "raptor": scene_raptor, "pterosaur": scene_pterosaur,
    "mosasaur": scene_mosasaur, "plesiosaur": scene_plesiosaur, "mammoth": scene_mammoth,
    "impact": scene_impact, "fossil": scene_fossil, "eggs": scene_eggs, "amber": scene_amber,
    "volcano": scene_volcano, "cambrian": scene_cambrian,
}

PREHISTORIC_KEYWORDS = [
    (("t. rex", "t rex", "tyrannosaurus"), {"scene": "trex"}),
    (("sauropod", "brachiosaurus", "diplodocus", "argentinosaurus", "long neck"), {"scene": "sauropod"}),
    (("triceratops", "frill"), {"scene": "triceratops"}),
    (("stegosaurus",), {"scene": "stegosaurus"}),
    (("velociraptor", "raptor", "feather"), {"scene": "raptor"}),
    (("pterosaur", "pteranodon", "quetzalcoatlus"), {"scene": "pterosaur"}),
    (("mosasaur",), {"scene": "mosasaur"}),
    (("plesiosaur",), {"scene": "plesiosaur"}),
    (("mammoth", "ice age"), {"scene": "mammoth"}),
    (("chicxulub", "extinction", "impact"), {"scene": "impact"}),
    (("fossil", "skeleton", "bones", "paleontologist"), {"scene": "fossil"}),
    (("egg", "eggs", "nest", "hatch"), {"scene": "eggs"}),
    (("amber",), {"scene": "amber"}),
    (("volcano", "eruption", "lava"), {"scene": "volcano"}),
    (("cambrian", "trilobite"), {"scene": "cambrian"}),
]


# Named body parts the camera can zoom in on (design units; a function of t
# for animals that move across the frame). Used by pixel_hud.plan_shots.
def _raptor_parts(t):
    x = raptor_x(t)
    return {"claw": (x + 2, 250), "legs": (x - 2, 234), "head": (x + 24, 197), "teeth": (x + 25, 199),
            "eye": (x + 23, 195), "feathers": (x + 12, 214), "arm": (x + 14, 214), "tail": (x - 30, 208),
            "body": (x + 2, 210)}


def _mosasaur_parts(t):
    hx, cy, L = mosasaur_geometry(t)
    return {"teeth": (hx - 12, cy + 1), "head": (hx - 18, cy - 1), "eye": (hx - 26, cy - 4), "body": (hx - 70, cy + 2),
            "flippers": (hx - 45, cy + 14), "tail": (hx - L + 4, cy + 10)}


def _plesiosaur_parts(t):
    cx, cy = plesiosaur_geometry(t)
    return {"neck": (cx + 46, cy - 22), "head": (cx + 80, cy - 40), "teeth": (cx + 82, cy - 39),
            "eye": (cx + 77, cy - 42), "flippers": (cx - 2, cy + 16), "body": (cx, cy)}


def _cambrian_parts(t):
    ax, ay = 40 + (t * 10) % 120, 170 + 4 * math.sin(t)
    return {"arms": (ax + 8, ay + 4), "predator": (ax - 15, ay), "eye": (ax + 2, ay - 4), "trilobite": (90, 246)}


FOCUS_POINTS = {
    "trex": {"teeth": (152, 160), "head": (150, 157), "eye": (148, 151), "arm": (124, 190), "legs": (90, 228),
             "feet": (96, 250), "tail": (40, 195), "neck": (135, 172), "body": (96, 186)},
    "sauropod": {"head": (150, 134), "neck": (128, 168), "body": (82, 214), "legs": (86, 240), "tail": (22, 238)},
    "triceratops": {"horns": (160, 190), "frill": (130, 188), "head": (150, 206), "beak": (166, 212),
                    "eye": (150, 203), "body": (86, 206), "legs": (90, 240)},
    "stegosaurus": {"plates": (76, 188), "spikes": (14, 212), "tail": (26, 220), "head": (130, 228),
                    "body": (80, 212), "legs": (95, 240)},
    "raptor": _raptor_parts,
    "pterosaur": {"wings": (100, 150), "head": (115, 148), "beak": (118, 149)},
    "mosasaur": _mosasaur_parts,
    "plesiosaur": _plesiosaur_parts,
    "mammoth": {"tusks": (150, 196), "trunk": (137, 220), "head": (124, 186), "eye": (126, 186),
                "fur": (88, 214), "legs": (90, 238)},
    "fossil": {"skull": (142, 168), "teeth": (142, 176), "ribs": (75, 205), "spine": (75, 185), "legs": (52, 232),
               "brush": (100, 240)},
    "eggs": {"egg": (100, 236), "nest": (92, 244), "baby": (101, 234)},
    "amber": {"insect": (90, 198), "amber": (90, 196)},
    "volcano": {"crater": (92, 150), "lava": (92, 176)},
    "cambrian": _cambrian_parts,
    "impact": {"crater": (70, 230)},
}


def register():
    pa.SCENES.update(PREHISTORIC_SCENES)
    pa.FOCUS.update(FOCUS_POINTS)
    pa._KEYWORD_SCENES[:0] = PREHISTORIC_KEYWORDS


register()
