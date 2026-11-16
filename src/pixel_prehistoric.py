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


# ------------------------------------------------------------- scenes ----
def scene_trex(frame, t, spec, seed):
    """Tyrannosaurus rex striding through a fern forest, jaws snapping."""
    landscape(frame, t, seed, spec.get("mood", "day"))
    bob = 1.5 * math.sin(t * 4.4)
    dark, light = [c for c in GREEN], [(25, 40, 20), (50, 80, 35), (85, 120, 50), (130, 160, 80)]
    legs(frame, t, [(78, 212 + bob)], 0, 0, 7.5, [(45, 70, 32)], phase=math.pi)
    # Tail
    sway = 4 * math.sin(t * 2.2)
    chain(frame, curve(62, 196 + bob, 4, 204 + sway, -6, 26), 13, 2, light)
    # Body and neck
    ellipse(frame, 92, 194 + bob, 40, 22, dark, ang=-0.18)
    ellipse(frame, 90, 204 + bob, 30, 9, [(110, 140, 70), (150, 175, 100), (190, 200, 140)], ang=-0.15)
    chain(frame, curve(118, 186 + bob, 136, 168 + bob, 3, 8), 13, 10, dark)
    legs(frame, t, [(80, 212 + bob)], 0, 0, 8.5, [(70, 105, 45)])
    ellipse(frame, 84, 210 + bob, 15, 20, dark, ang=0.2)
    # Head: skull and snapping jaw
    snap = 0.32 * max(0.0, math.sin(t * 1.8)) ** 3
    hx, hy = 133, 158 + bob
    poly(frame, [(hx, hy - 9), (hx + 30, hy - 7), (hx + 40, hy + 1), (hx + 38, hy + 6), (hx, hy + 8)], (75, 110, 48))
    poly(frame, [(hx + 2, hy - 9), (hx + 30, hy - 7), (hx + 36, hy - 3), (hx + 2, hy - 3)], (105, 140, 65))
    jaw = [(hx + 2, hy + 6), (hx + 36, hy + 7), (hx + 34, hy + 12), (hx + 4, hy + 13)]
    c, s = math.cos(snap), math.sin(snap)
    jaw = [(hx + 2 + (x - hx - 2) * c - (y - hy - 6) * s, hy + 6 + (x - hx - 2) * s + (y - hy - 6) * c) for x, y in jaw]
    if snap > 0.05:
        poly(frame, [(hx + 4, hy + 6), (hx + 38, hy + 6), jaw[1], jaw[2]], (90, 20, 25))
    poly(frame, jaw, (65, 95, 42))
    teeth(frame, hx + 6, hx + 36, hy + 6, True, 3)
    eye(frame, hx + 14, hy - 3)
    pa.put(frame, hx + 36, hy - 3, (30, 40, 20), 2)
    # Tiny arm
    limb(frame, 120, 200 + bob, 127, 206 + bob, 2.2, 1.2, (60, 90, 40))
    limb(frame, 127, 206 + bob, 131, 203 + bob, 1.2, 0.6, (60, 90, 40))
    foreground_ferns(frame, t, seed)


def scene_sauropod(frame, t, spec, seed):
    """A long-necked sauropod browsing treetops, with a smaller one behind."""
    landscape(frame, t, seed, spec.get("mood", "day"))
    ramp = [(60, 60, 55), (100, 100, 85), (145, 140, 115), (190, 185, 155)]
    far = [(85, 95, 100), (110, 120, 120), (135, 145, 140)]
    # A distant herd member
    ellipse(frame, 30, 214, 16, 9, far)
    chain(frame, curve(40, 210, 58, 170, -4, 10), 3.5, 2, far)
    for x in (22, 36):
        limb(frame, x, 218, x, 236, 2.5, 2.2, far[0])
    # Main animal
    sway = 3 * math.sin(t * 0.8)
    for i, x in enumerate((62, 106)):
        legs(frame, t * 0.5, [(x - 4, 236)], 0, 0, 7, [(80, 80, 70)], phase=i, stride=4, toe=0)
    chain(frame, curve(52, 222, 2, 246, 5, 20, 2, t), 11, 2, ramp)
    ellipse(frame, 84, 222, 40, 22, ramp, ang=-0.08)
    neck = curve(110, 210, 146 + sway, 132, -14, 22)
    chain(frame, neck, 10, 5, ramp)
    hx, hy = neck[-1]
    ellipse(frame, hx + 6, hy - 1, 8, 5, ramp)
    eye(frame, hx + 6, hy - 3, 1.2)
    for i, x in enumerate((70, 112)):
        legs(frame, t * 0.5, [(x, 236)], 0, 0, 8, [(110, 108, 92)], phase=i + 0.5, stride=4, toe=0)
    # Tree being browsed
    cycad(frame, 166, GROUND + 4, 120, t, 2)
    foreground_ferns(frame, t, seed)


def scene_triceratops(frame, t, spec, seed):
    """A Triceratops with its frill and three horns, grazing."""
    landscape(frame, t, seed, spec.get("mood", "day"))
    nod = 2 * math.sin(t * 1.1)
    legs(frame, t * 0.6, [(60, 226), (110, 226)], 0, 0, 7, [(110, 70, 40)], stride=4, toe=0)
    chain(frame, curve(48, 214, 12, 232, 3, 12), 9, 2, RUST)
    ellipse(frame, 82, 214, 38, 22, RUST, ang=-0.05)
    legs(frame, t * 0.6, [(66, 226), (116, 226)], 0, 0, 8, [(150, 90, 50)], phase=0.7, stride=4, toe=0)
    # Frill (fan behind the head) with a pale rim
    fx, fy = 122, 192 + nod
    s = _win(fx, fy, 26, 26)
    d = np.sqrt((XX[s] - fx) ** 2 + (YY[s] - fy) ** 2)
    a = np.arctan2(YY[s] - fy, XX[s] - fx)
    fr = (d < 25) & (np.abs(a + 0.9) < 1.5)
    frame[s][fr] = dither_ramp(np.clip(1 - d[fr] / 25, 0, 1), [(120, 50, 40), (175, 85, 55), (210, 130, 80)], PY[s][fr], PX[s][fr])
    rim = fr & (d > 22.5)
    frame[s][rim] = (235, 205, 150)
    for k in range(6):   # bony knobs on the rim
        aa = -0.9 - 1.4 + k * 0.56
        disc(frame, fx + math.cos(aa) * 25, fy + math.sin(aa) * 25, 1.6, (235, 210, 160))
    # Head and beak
    ellipse(frame, 140, 206 + nod, 16, 11, RUST, ang=0.25)
    tri(frame, [(150, 202 + nod), (162, 214 + nod), (150, 214 + nod)], (90, 70, 50))
    # Horns: two long brow horns, one short nose horn
    for bx, by, tx, ty in ((136, 198, 162, 178), (142, 200, 166, 184)):
        limb(frame, bx, by + nod, tx, ty + nod, 2.6, 0.5, (235, 225, 195))
    limb(frame, 155, 204 + nod, 160, 197 + nod, 1.8, 0.4, (225, 215, 185))
    eye(frame, 140, 202 + nod)
    foreground_ferns(frame, t, seed)


def scene_stegosaurus(frame, t, spec, seed):
    """A Stegosaurus with back plates and a spiked tail swinging."""
    landscape(frame, t, seed, spec.get("mood", "day"))
    ramp = OLIVE
    legs(frame, t * 0.6, [(64, 226), (108, 228)], 0, 0, 7, [(80, 85, 40)], stride=4, toe=0)
    swing = 6 * math.sin(t * 1.4)
    tail = curve(52, 214, 6, 222 + swing, -8, 18)
    chain(frame, tail, 9, 2.5, ramp)
    for k in (0.75, 0.9):   # tail spikes
        x, y = tail[int(k * 17)]
        limb(frame, x, y - 2, x - 6, y - 12, 1.8, 0.4, (230, 220, 190))
        limb(frame, x, y - 1, x - 9, y - 6, 1.6, 0.4, (230, 220, 190))
    # Plates along the back, tallest over the hips
    for i in range(9):
        f = i / 8
        x = 50 + f * 70
        y = 200 - 18 * math.sin(f * math.pi) + 2
        h = 8 + 14 * math.sin(f * math.pi)
        tri(frame, [(x - 5, y + 4), (x + 5, y + 4), (x + 1, y - h)], (185, 90, 60) if i % 2 else (210, 120, 70))
    ellipse(frame, 84, 214, 40, 20, ramp, ang=0.05)
    legs(frame, t * 0.6, [(70, 228), (114, 230)], 0, 0, 8, [(110, 115, 55)], phase=0.7, stride=4, toe=0)
    ellipse(frame, 132, 226, 11, 6, ramp, ang=0.4)
    eye(frame, 136, 224, 1.2)
    foreground_ferns(frame, t, seed)


def scene_raptor(frame, t, spec, seed):
    """A feathered Velociraptor-sized dromaeosaur running past, sickle claw up."""
    landscape(frame, t, seed, spec.get("mood", "dusk"))
    x = 50 + (t * 14) % 90
    run = t * 8
    feathers = [(70, 45, 30), (120, 80, 45), (170, 120, 70), (210, 170, 110)]
    # A small raptor is about turkey-sized, so it gets a big fern for scale
    fern(frame, 150, GROUND + 2, 30, t, 1, (55, 110, 45))
    for i in range(2):
        p = math.sin(run + i * math.pi)
        hx, hy = x, 222
        kx, ky = x + 4 + p * 4, 234
        fx = x + p * 9
        col = (90, 60, 35) if i == 0 else (130, 90, 55)
        limb(frame, hx, hy, kx, ky, 3, 2, col)
        limb(frame, kx, ky, fx, GROUND - max(0, math.cos(run + i * math.pi)) * 4, 2, 1.2, col)
        disc(frame, fx + 2, GROUND - 3, 1.2, (230, 220, 200))   # raised sickle claw
    chain(frame, curve(x - 6, 216, x - 40, 210 + 2 * math.sin(run / 2), -3, 14), 5, 1.5, feathers)
    for k in range(6):   # tail feather fan
        pa.put(frame, x - 40 - k, 208 + k * 0.8, (200, 150, 90), 2)
    ellipse(frame, x + 4, 214, 13, 8, feathers, ang=-0.2)
    chain(frame, curve(x + 14, 210, x + 22, 198, -2, 6), 4.5, 3.5, feathers)
    ellipse(frame, x + 27, 196, 7, 4, feathers, ang=0.15)
    teeth(frame, x + 24, x + 33, 198, True, 1.5)
    eye(frame, x + 26, 194, 1.2)
    # Feathered arm
    for k in range(5):
        limb(frame, x + 8, 212, x + 14 - k, 222 + k, 1.4, 0.6, (150 + k * 10, 100 + k * 8, 60))
    foreground_ferns(frame, t, seed)


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


def _water_reptile(frame, t, seed, top, bottom, length, cx, cy, ramp, belly):
    water(frame, [(40, 130, 170), (20, 80, 130), (8, 40, 80), (3, 18, 40)], 0.1, 1.0)
    light_rays(frame, t, seed, strength=0.3)
    marine_snow(frame, t, seed, 80, (110, 160, 190))
    return swimmer(frame, cx, cy, length, top, bottom, ramp, 1, bend=6 * math.sin(t * 2), belly_ramp=belly)


def scene_mosasaur(frame, t, spec, seed):
    """A mosasaur, a giant sea reptile, gliding past ammonites."""
    hx = 120 + t * 5
    cy = 196 + 4 * math.sin(t * 0.8)
    L = 160
    top = lambda u: 11 * np.clip(u / 0.15, 0, 1) ** 0.6 * (1 - np.clip((u - 0.3) / 0.7, 0, 1) * 0.85)
    bot = lambda u: 10 * np.clip(u / 0.12, 0, 1) ** 0.6 * (1 - np.clip((u - 0.3) / 0.7, 0, 1) * 0.85)
    ramp = [(30, 50, 60), (55, 85, 95), (85, 120, 125)]
    belly = [(150, 160, 150), (190, 195, 180)]
    # Ammonites (coiled shells) drift in front of the water
    _water_reptile(frame, t, seed, top, bot, L, hx, cy, ramp, belly)
    for i in range(4):
        ax, ay = (i * 47 + t * 3) % (LW + 20) - 10, 140 + (i * 31) % 90
        s = _win(ax, ay, 7, 7)
        if s is None:
            continue
        d = np.sqrt((XX[s] - ax) ** 2 + (YY[s] - ay) ** 2)
        a = np.arctan2(YY[s] - ay, XX[s] - ax)
        shell = d < 5.5
        frame[s][shell] = dither_ramp(0.5 + 0.5 * np.sin(d[shell] * 2.2 + a[shell]), [(120, 80, 50), (200, 160, 110), (235, 210, 170)],
                                      PY[s][shell], PX[s][shell])
    # Flippers and tail fin
    for fx, fy, dx in ((hx - 0.3 * L, cy + 8, 14), (hx - 0.6 * L, cy + 6, 10)):
        tri(frame, [(fx, fy), (fx + 6, fy), (fx - dx, fy + 12 + 3 * math.sin(t * 2))], (40, 65, 75))
    tri(frame, [(hx - L + 4, cy + 2), (hx - L - 12, cy - 12), (hx - L - 6, cy + 14)], (40, 65, 75))
    # Long jaw with teeth
    teeth(frame, hx - 26, hx - 3, cy + 1, True, 2.2)
    eye(frame, hx - 22, cy - 4, 1.3)


def scene_plesiosaur(frame, t, spec, seed):
    """A long-necked plesiosaur rowing with four flippers through a school of fish."""
    water(frame, [(40, 130, 170), (20, 80, 130), (8, 40, 80), (3, 18, 40)], 0.1, 1.0)
    light_rays(frame, t, seed, strength=0.3)
    for i in range(16):
        small_fish(frame, (i * 23 + t * 9) % (LW + 20) - 10, 130 + (i * 37) % 60, 2.5, 1, (200, 210, 190), t, i)
    cx, cy = 70 + t * 3, 212 + 3 * math.sin(t)
    ramp = [(50, 60, 45), (90, 100, 70), (130, 140, 100), (175, 180, 140)]
    row = math.sin(t * 2)
    for fx, ph in ((cx + 14, 0), (cx - 18, 1.5)):
        a = 0.6 + 0.5 * math.sin(t * 2 + ph)
        limb(frame, fx, cy + 4, fx - 18 * math.cos(a), cy + 4 + 16 * math.sin(a), 4, 1, (60, 70, 50))
    chain(frame, curve(cx - 22, cy, cx - 48, cy + 4, 2, 10), 7, 1.5, ramp)
    ellipse(frame, cx, cy, 26, 12, ramp)
    neck = curve(cx + 22, cy - 4, cx + 74, cy - 40 + 3 * row, -10, 26)
    chain(frame, neck, 5.5, 3, ramp)
    hx, hy = neck[-1]
    ellipse(frame, hx + 3, hy, 6, 3.5, ramp)
    teeth(frame, hx + 2, hx + 8, hy + 1.5, True, 1.4)
    eye(frame, hx + 3, hy - 1.5, 1.0)
    for fx, ph in ((cx + 10, 0.4), (cx - 14, 1.9)):
        a = 0.6 + 0.5 * math.sin(t * 2 + ph)
        limb(frame, fx, cy + 6, fx - 18 * math.cos(a), cy + 6 + 16 * math.sin(a), 4.5, 1.2, (85, 95, 65))


def scene_mammoth(frame, t, spec, seed):
    """A woolly mammoth walking through falling snow."""
    landscape(frame, t, seed, "ice")
    wool = [(50, 30, 20), (90, 55, 30), (135, 90, 50), (175, 130, 80)]
    leg_dark, leg_light = (70, 45, 28), (110, 72, 42)
    for i, x in enumerate((60, 100)):
        legs(frame, t * 0.5, [(x, 210)], 0, 0, 9, [leg_dark], phase=i, stride=5, toe=0)
    ellipse(frame, 80, 194, 38, 24, wool)
    ellipse(frame, 112, 176, 15, 17, wool)   # domed head
    ellipse(frame, 104, 168, 7, 6, wool)     # shoulder hump
    rng = np.random.default_rng(seed)
    for _ in range(300):   # shaggy hair strands hanging down
        x, y = rng.uniform(42, 126), rng.uniform(168, 218)
        if ((x - 80) / 39) ** 2 + ((y - 194) / 25) ** 2 < 1 or ((x - 112) / 16) ** 2 + ((y - 176) / 18) ** 2 < 1:
            for k in range(5):
                pa.put(frame, x + 0.2 * k, y + k, (55, 35, 20) if rng.random() < 0.5 else (160, 112, 65))
    for i, x in enumerate((68, 108)):
        legs(frame, t * 0.5, [(x, 212)], 0, 0, 10, [leg_light], phase=i + 0.5, stride=5, toe=0)
    # Trunk, then long curving tusks in front of it
    sw = 3 * math.sin(t * 1.2)
    chain(frame, curve(122, 186, 128 + sw, 236, 7, 18), 5, 2.4, wool)
    for k, off in enumerate((0, 4)):
        for x, y in curve(118 + off, 196, 154 + off, 182, 16, 26):
            disc(frame, x, y, 2.6, (245, 238, 220) if k else (215, 205, 180))
    eye(frame, 117, 172, 1.4)
    # Snow
    srng = np.random.default_rng(seed + 3)
    for i in range(160):
        x = (srng.uniform(0, LW) + 6 * math.sin(t * 0.8 + i)) % LW
        y = (srng.uniform(0, LH) + t * srng.uniform(6, 14)) % LH
        pa.put(frame, x, y, (255, 255, 255), 2 if i % 4 == 0 else 1)


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


def register():
    pa.SCENES.update(PREHISTORIC_SCENES)
    pa._KEYWORD_SCENES[:0] = PREHISTORIC_KEYWORDS


register()
