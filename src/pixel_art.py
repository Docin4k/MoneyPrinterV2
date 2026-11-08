"""8-bit style animated scenes for YouTube Shorts.

Every frame is drawn on a small 180x320 canvas with a limited palette and
ordered (Bayer) dithering, then scaled up 6x with hard pixel edges to
1080x1920. Animation is stepped at 12 frames per second for a retro feel.

A scene is described by a dict, for example {"scene": "planet", "preset": "venus"}.
Available scenes: planet, sun, black_hole, pulsar, galaxy, surface, orbit,
diamond_rain, starfield. See SCENES and PLANET_PRESETS below.

Text uses a built-in 5x7 bitmap font, so no font files are needed.
"""
import math
import re
import random

import numpy as np
from moviepy.editor import ImageClip, VideoClip

LW, LH = 180, 320          # low-resolution canvas
SCALE = 6                  # 180x320 -> 1080x1920
ANIM_FPS = 12              # animation steps per second

BAYER = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) + 0.5) / 16.0
BAYER_FULL = np.tile(BAYER, (LH // 4 + 1, LW // 4 + 1))[:LH, :LW]

YY, XX = np.mgrid[0:LH, 0:LW]

# ---------------------------------------------------------------- font ----
_GLYPHS = {
    "A": "01110 10001 10001 11111 10001 10001 10001", "B": "11110 10001 10001 11110 10001 10001 11110",
    "C": "01110 10001 10000 10000 10000 10001 01110", "D": "11100 10010 10001 10001 10001 10010 11100",
    "E": "11111 10000 10000 11110 10000 10000 11111", "F": "11111 10000 10000 11110 10000 10000 10000",
    "G": "01110 10001 10000 10111 10001 10001 01111", "H": "10001 10001 10001 11111 10001 10001 10001",
    "I": "01110 00100 00100 00100 00100 00100 01110", "J": "00111 00010 00010 00010 00010 10010 01100",
    "K": "10001 10010 10100 11000 10100 10010 10001", "L": "10000 10000 10000 10000 10000 10000 11111",
    "M": "10001 11011 10101 10101 10001 10001 10001", "N": "10001 10001 11001 10101 10011 10001 10001",
    "O": "01110 10001 10001 10001 10001 10001 01110", "P": "11110 10001 10001 11110 10000 10000 10000",
    "Q": "01110 10001 10001 10001 10101 10010 01101", "R": "11110 10001 10001 11110 10100 10010 10001",
    "S": "01111 10000 10000 01110 00001 00001 11110", "T": "11111 00100 00100 00100 00100 00100 00100",
    "U": "10001 10001 10001 10001 10001 10001 01110", "V": "10001 10001 10001 10001 10001 01010 00100",
    "W": "10001 10001 10001 10101 10101 10101 01010", "X": "10001 10001 01010 00100 01010 10001 10001",
    "Y": "10001 10001 01010 00100 00100 00100 00100", "Z": "11111 00001 00010 00100 01000 10000 11111",
    "0": "01110 10001 10011 10101 11001 10001 01110", "1": "00100 01100 00100 00100 00100 00100 01110",
    "2": "01110 10001 00001 00010 00100 01000 11111", "3": "11111 00010 00100 00010 00001 10001 01110",
    "4": "00010 00110 01010 10010 11111 00010 00010", "5": "11111 10000 11110 00001 00001 10001 01110",
    "6": "00110 01000 10000 11110 10001 10001 01110", "7": "11111 00001 00010 00100 01000 01000 01000",
    "8": "01110 10001 10001 01110 10001 10001 01110", "9": "01110 10001 10001 01111 00001 00010 01100",
    ".": "00000 00000 00000 00000 00000 01100 01100", ",": "00000 00000 00000 00000 01100 00100 01000",
    "'": "01100 00100 01000 00000 00000 00000 00000", "!": "00100 00100 00100 00100 00100 00000 00100",
    "?": "01110 10001 00001 00010 00100 00000 00100", "-": "00000 00000 00000 11111 00000 00000 00000",
    ":": "00000 01100 01100 00000 01100 01100 00000", "/": "00001 00010 00010 00100 01000 01000 10000",
    "%": "11000 11001 00010 00100 01000 10011 00011", "&": "01100 10010 10100 01000 10101 10010 01101",
    "(": "00010 00100 01000 01000 01000 00100 00010", ")": "01000 00100 00010 00010 00010 00100 01000",
    "#": "01010 01010 11111 01010 11111 01010 01010", " ": "00000 00000 00000 00000 00000 00000 00000",
}
GLYPHS = {k: np.array([[c == "1" for c in row] for row in v.split()], dtype=bool) for k, v in _GLYPHS.items()}


def _wrap(text: str, max_chars: int) -> list[str]:
    lines, line = [], ""
    for word in text.split():
        if line and len(line) + 1 + len(word) > max_chars:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    if line:
        lines.append(line)
    return lines


def text_mask(text: str, scale: int, max_width: int, align_center: bool = True) -> np.ndarray:
    """Boolean mask of text in the pixel font, wrapped to max_width pixels."""
    char_w = 6 * scale
    lines = _wrap(text.upper(), max(1, max_width // char_w))
    h = len(lines) * 9 * scale
    w = max_width
    mask = np.zeros((max(h, 1), w), dtype=bool)
    for li, line in enumerate(lines):
        line_w = len(line) * char_w - scale
        x0 = (w - line_w) // 2 if align_center else 0
        for ci, ch in enumerate(line):
            g = GLYPHS.get(ch, GLYPHS[" "])
            g = np.kron(g, np.ones((scale, scale), dtype=bool))
            y, x = li * 9 * scale, x0 + ci * char_w
            if x + g.shape[1] <= w:
                mask[y:y + g.shape[0], x:x + g.shape[1]] |= g
    return mask


def stamp_text(frame, text, y, scale, color, outline=(0, 0, 0), max_width=LW - 12):
    """Draw outlined pixel text centred horizontally at row y; returns the bottom row."""
    mask = text_mask(text, scale, max_width)
    h, w = mask.shape
    x0 = (LW - w) // 2
    region = np.zeros((LH, LW), dtype=bool)
    y1, y2 = max(0, y), min(LH, y + h)
    region[y1:y2, x0:x0 + w] = mask[y1 - y:y2 - y]
    if outline is not None:
        grown = region.copy()
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (-1, 1), (1, -1)):
            grown |= np.roll(np.roll(region, dy, 0), dx, 1)
        frame[grown & ~region] = outline
    frame[region] = color
    return y + h


# ----------------------------------------------------------- helpers ----
def dither_ramp(value: np.ndarray, ramp: list, ys=None, xs=None) -> np.ndarray:
    """Map values in [0, 1] onto a colour ramp with ordered dithering."""
    ramp = np.array(ramp, dtype=np.uint8)
    n = len(ramp)
    b = BAYER_FULL if ys is None else BAYER[ys % 4, xs % 4]
    idx = np.clip(np.floor(np.clip(value, 0, 1) * (n - 1) + b), 0, n - 1).astype(int)
    return ramp[idx]


def tq(t: float) -> float:
    """Quantise time to the animation step."""
    return math.floor(t * ANIM_FPS) / ANIM_FPS


def sky(top, bottom, frame=None):
    """Vertical dithered gradient between two colours (plus a midpoint)."""
    mid = tuple((a + b) // 2 for a, b in zip(top, bottom))
    v = YY / (LH - 1)
    out = dither_ramp(v, [top, mid, bottom])
    if frame is not None:
        frame[:] = out
    return out


class Stars:
    """Parallax starfield with twinkling."""

    def __init__(self, seed: int, count: int = 140):
        rng = np.random.default_rng(seed)
        self.x = rng.uniform(0, LW, count)
        self.y = rng.integers(0, LH, count)
        self.layer = rng.choice([1, 2, 3], count, p=[0.6, 0.3, 0.1])
        self.phase = rng.uniform(0, 2 * np.pi, count)
        self.speed = rng.uniform(0.6, 1.6, count)

    def draw(self, frame, t, drift=2.0, mask=None):
        x = ((self.x + t * drift * self.layer) % LW).astype(int)
        y = self.y
        tw = np.sin(self.phase + t * 3 * self.speed) > -0.6
        bright = np.where(self.layer == 3, 255, np.where(self.layer == 2, 200, 140))
        for xi, yi, b, on, layer in zip(x, y, bright, tw, self.layer):
            if not on or (mask is not None and mask[yi, xi]):
                continue
            frame[yi, xi] = (b, b, min(255, b + 20))
            if layer == 3 and math.sin(t * 4 + xi) > 0.3:  # sparkle cross on big stars
                for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    yy, xx = yi + dy, (xi + dx) % LW
                    if 0 <= yy < LH and (mask is None or not mask[yy, xx]):
                        frame[yy, xx] = (b // 2, b // 2, b // 2 + 30)


def periodic_noise(lon, lat, seed, octaves=4):
    """Smooth noise that wraps around in longitude (sum of sines)."""
    rng = random.Random(seed)
    total = np.zeros_like(lon)
    amp, norm = 1.0, 0.0
    for o in range(octaves):
        for _ in range(3):
            k = rng.randint(1 + o * 2, 3 + o * 3)
            m = rng.uniform(1.5, 4.0) * (o + 1)
            ph1, ph2 = rng.uniform(0, 6.28), rng.uniform(0, 6.28)
            total += amp * np.sin(k * lon + ph1) * np.cos(m * lat + ph2)
            norm += amp
        amp *= 0.5
    return total / norm * 0.5 + 0.5


SPRITES = {
    "iss": ["....#...#....", "##########...", "####.#.####..", ".....###.....", "####.#.####..",
            "##########...", "....#...#...."],
    "diamond": [".###.", "#####", ".###.", "..#.."],
    "flag": ["#####", "####.", "#####", "#....", "#....", "#....", "#...."],
    "rover": ["...##....", "..####...", "#######..", "#.#.#.#..", ".#.#.#..."],
    "footprint": [".##.", "####", "####", ".##.", "....", ".##.", ".##."],
}


def draw_sprite(frame, name, x, y, color, scale=1):
    rows = SPRITES[name]
    for r, row in enumerate(rows):
        for c, ch in enumerate(row):
            if ch == "#":
                for sy in range(scale):
                    for sx in range(scale):
                        yy, xx = int(y) + r * scale + sy, int(x) + c * scale + sx
                        if 0 <= yy < LH and 0 <= xx < LW:
                            frame[yy, xx] = color


# ------------------------------------------------------------ planets ----
PLANET_PRESETS = {
    "venus": {"ramp": [(60, 30, 10), (150, 90, 30), (220, 170, 80), (250, 225, 150)], "bands": 0.6,
              "noise": 0.7, "spin": -0.25, "atmo": (255, 220, 140)},
    "earth": {"ramp": [(10, 30, 90), (20, 70, 160), (40, 140, 70), (230, 240, 250)], "bands": 0.0,
              "noise": 1.0, "spin": 0.35, "atmo": (120, 180, 255), "earthlike": True},
    "mars": {"ramp": [(60, 20, 10), (130, 50, 25), (190, 90, 50), (230, 150, 100)], "bands": 0.1,
             "noise": 0.9, "spin": 0.3, "atmo": (230, 140, 100), "caps": True},
    "jupiter": {"ramp": [(90, 50, 30), (170, 120, 80), (220, 190, 150), (245, 235, 215)], "bands": 1.0,
                "noise": 0.35, "spin": 0.6, "atmo": (240, 210, 170), "spot": True},
    "saturn": {"ramp": [(110, 80, 40), (190, 150, 90), (230, 200, 140), (250, 235, 190)], "bands": 0.8,
               "noise": 0.25, "spin": 0.55, "atmo": (250, 230, 170), "rings": True},
    "neptune": {"ramp": [(10, 20, 80), (30, 60, 170), (70, 120, 230), (170, 210, 255)], "bands": 0.5,
                "noise": 0.5, "spin": 0.5, "atmo": (120, 170, 255)},
    "uranus": {"ramp": [(30, 90, 110), (80, 170, 190), (140, 215, 225), (210, 245, 250)], "bands": 0.3,
               "noise": 0.3, "spin": 0.4, "atmo": (170, 240, 250)},
    "moon": {"ramp": [(40, 40, 45), (100, 100, 105), (160, 160, 165), (215, 215, 220)], "bands": 0.0,
             "noise": 0.8, "spin": 0.15, "atmo": None, "craters": True},
    "mercury": {"ramp": [(50, 40, 35), (110, 95, 85), (170, 155, 140), (220, 210, 195)], "bands": 0.0,
                "noise": 0.8, "spin": 0.1, "atmo": None, "craters": True},
}


def draw_planet(frame, t, preset, cx, cy, r, seed=1, light=(-0.6, -0.4)):
    p = PLANET_PRESETS[preset]
    dx, dy = (XX - cx) / r, (YY - cy) / r
    d2 = dx ** 2 + dy ** 2
    inside = d2 <= 1.0

    # Saturn's rings: back half first
    if p.get("rings"):
        _draw_rings(frame, cx, cy, r, front=False, t=t)

    nx, ny = dx[inside], dy[inside]
    nz = np.sqrt(np.clip(1 - nx ** 2 - ny ** 2, 0, 1))
    lat = np.arcsin(np.clip(ny, -1, 1))
    lon = np.arctan2(nx, nz) + t * p["spin"]
    val = 0.5 + p["bands"] * 0.35 * np.sin(lat * 9 + 0.6 * np.sin(lon * 2 + lat * 4))
    val = val * (1 - p["noise"] * 0.5) + periodic_noise(lon, lat, seed) * p["noise"] * 0.5

    if p.get("earthlike"):
        land = periodic_noise(lon, lat, seed + 7) > 0.56
        cloud = periodic_noise(lon * 1.0 + t * 0.15, lat, seed + 13, 3) > 0.62
        val = np.where(land, 0.62, 0.3 + 0.1 * val)
        val = np.where(cloud, 1.0, val)
    if p.get("spot"):
        slon = (lon % (2 * np.pi)) - np.pi
        spot = ((slon / 0.45) ** 2 + ((lat + 0.35) / 0.18) ** 2) < 1
    if p.get("caps"):
        val = np.where(np.abs(lat) > 1.25, 1.0, val)
    if p.get("craters"):
        rng = random.Random(seed)
        for _ in range(14):
            clon, clat, cr = rng.uniform(-3.14, 3.14), rng.uniform(-1.2, 1.2), rng.uniform(0.08, 0.25)
            dl = np.angle(np.exp(1j * (lon - clon)))
            dd = np.sqrt((dl * np.cos(lat)) ** 2 + (lat - clat) ** 2)
            val = np.where(dd < cr, val - 0.25, np.where(dd < cr * 1.25, val + 0.15, val))

    lx, ly = light
    lz = math.sqrt(max(0.0, 1 - lx ** 2 - ly ** 2))
    shade = np.clip(nx * lx + ny * ly + nz * lz, 0, 1)
    v = np.clip(val, 0, 1) * (0.25 + 0.75 * shade)
    colors = dither_ramp(v, p["ramp"], YY[inside], XX[inside])
    if p.get("spot"):
        spot_col = dither_ramp(0.4 + 0.6 * shade[spot], [(90, 20, 10), (180, 60, 30), (230, 110, 70)],
                               YY[inside][spot], XX[inside][spot])
        colors[spot] = spot_col
    frame[inside] = colors

    if p.get("atmo"):
        rim = (d2 > 1.0) & (d2 <= (1 + 2.0 / r) ** 2)
        lit = ((XX - cx) * lx + (YY - cy) * ly) > -r * 0.3
        frame[rim & lit] = p["atmo"]
    if p.get("rings"):
        _draw_rings(frame, cx, cy, r, front=True, t=t)
    return inside


def _draw_rings(frame, cx, cy, r, front, t):
    tilt = 0.28
    ex, ey = (XX - cx), (YY - cy) / tilt
    rr = np.sqrt(ex ** 2 + ey ** 2) / r
    band = (rr > 1.35) & (rr < 2.25) & ~((rr > 1.85) & (rr < 1.92))  # with a gap
    half = (YY >= cy) if front else (YY < cy)
    planet = ((XX - cx) ** 2 + (YY - cy) ** 2) <= r * r
    sel = band & half & (~planet if not front else np.ones_like(planet))
    shimmer = 0.5 + 0.35 * np.sin(rr * 30 + t * 0.5) + 0.15 * np.sin(rr * 90)
    cols = dither_ramp(shimmer[sel], [(120, 100, 70), (190, 170, 130), (235, 220, 180)], YY[sel], XX[sel])
    frame[sel] = cols


# ------------------------------------------------------------ details ----
_NEBULA_CACHE = {}
NEBULA_HUES = [((60, 20, 90), (20, 40, 110)), ((90, 20, 50), (40, 20, 90)), ((20, 60, 90), (10, 30, 70)),
               ((80, 40, 20), (50, 20, 60)), ((20, 70, 60), (20, 30, 80))]


def nebula(frame, seed):
    """Soft, dithered nebula clouds behind a space scene (colours vary by seed)."""
    if seed not in _NEBULA_CACHE:
        rng = random.Random(seed * 7 + 3)
        u, v = XX / LW * 2 * np.pi, YY / LH * 2 * np.pi
        field = np.zeros((LH, LW))
        for k in range(6):
            a, b = rng.uniform(0.5, 2.5), rng.uniform(0.5, 3.0)
            field += np.sin(u * a + rng.uniform(0, 6.3) + np.sin(v * b + rng.uniform(0, 6.3)) * 1.5) / (k + 1)
        field = (field - field.min()) / (np.ptp(field) + 1e-9)
        density = np.clip((field - 0.55) / 0.45, 0, 1) ** 1.3
        c1, c2 = NEBULA_HUES[seed % len(NEBULA_HUES)]
        colors = dither_ramp(density, [(4, 4, 16), c2, c1])
        _NEBULA_CACHE[seed] = (density > 0.02, colors)
    mask, colors = _NEBULA_CACHE[seed]
    frame[mask] = colors[mask]


def shooting_star(frame, t, seed):
    """A short streak every few seconds, at a different place each time."""
    period = 4.5
    n = int(t // period)
    phase = (t % period) / 0.6
    if phase > 1:
        return
    rng = random.Random(seed * 131 + n)
    x0, y0 = rng.uniform(20, LW), rng.uniform(40, LH * 0.55)
    dx, dy = -rng.uniform(60, 110), rng.uniform(20, 50)
    for i in range(14):
        f = phase - i * 0.012
        if f < 0:
            break
        x, y = int(x0 + dx * f), int(y0 + dy * f)
        if 0 <= x < LW and 0 <= y < LH:
            b = 255 - i * 16
            frame[y, x] = (b, b, min(255, b + 30))


# Moons: (orbit radius in planet radii, size in pixels, speed, colour, phase)
PLANET_MOONS = {
    "jupiter": [(1.35, 2, 1.6, (220, 210, 170), 0.0), (1.6, 2, 1.1, (200, 180, 150), 2.0),
                (1.95, 3, 0.75, (180, 170, 160), 4.0), (2.3, 3, 0.5, (140, 130, 120), 1.0)],
    "saturn": [(2.6, 3, 0.45, (220, 180, 110), 1.0)],
    "mars": [(1.4, 1, 2.0, (150, 130, 120), 0.0), (1.9, 1, 1.0, (170, 150, 140), 3.0)],
    "earth": [(2.1, 4, 0.4, (200, 200, 205), 2.5)],
    "neptune": [(1.8, 2, -0.7, (210, 200, 200), 1.5)],
}


def draw_moons(frame, t, preset, cx, cy, r, front):
    for orbit, size, speed, color, phase in PLANET_MOONS.get(preset, []):
        a = phase + t * speed
        is_front = math.sin(a) > 0
        if is_front != front:
            continue
        x = cx + orbit * r * math.cos(a)
        y = cy + orbit * r * 0.22 * math.sin(a)
        d = (XX - x) ** 2 + (YY - y) ** 2 <= size * size
        if not front:
            d &= (XX - cx) ** 2 + (YY - cy) ** 2 > r * r
        lit = d & ((XX - x) < size * 0.3)
        frame[d] = tuple(c // 2 for c in color)
        frame[lit] = color


def halo(frame, cx, cy, r, color, width=6):
    """Faint dithered glow just outside a planet's edge."""
    d = np.sqrt((XX - cx) ** 2 + (YY - cy) ** 2)
    ring = (d > r + 1) & (d < r + width)
    strength = 1 - (d[ring] - r - 1) / (width - 1)
    keep = BAYER_FULL[ring] < strength * 0.5
    ys, xs = YY[ring][keep], XX[ring][keep]
    frame[ys, xs] = (frame[ys, xs] * 0.5 + np.array(color) * 0.5).astype(np.uint8)


# ------------------------------------------------------------- scenes ----
def scene_planet(frame, t, spec, seed):
    Stars(seed).draw(frame, t)
    preset = spec.get("preset", "venus")
    r = spec.get("radius", 58 if preset != "saturn" else 42)
    cx, cy = LW // 2, spec.get("y", 205)
    atmo = PLANET_PRESETS[preset].get("atmo")
    if atmo:
        halo(frame, cx, cy, r, atmo)
    draw_moons(frame, t, preset, cx, cy, r, front=False)
    draw_planet(frame, t, preset, cx, cy, r, seed=seed)
    draw_moons(frame, t, preset, cx, cy, r, front=True)


def scene_sun(frame, t, spec, seed):
    Stars(seed).draw(frame, t, drift=1)
    cx, cy, r = LW // 2, 210, 62
    d = np.sqrt((XX - cx) ** 2 + (YY - cy) ** 2)
    ang = np.arctan2(YY - cy, XX - cx)
    corona_len = 10 + 6 * np.sin(ang * 7 + t * 2) + 4 * np.sin(ang * 13 - t * 3)
    corona = (d > r) & (d < r + corona_len)
    cv = 1 - (d[corona] - r) / corona_len[corona]
    frame[corona] = dither_ramp(cv, [(60, 10, 10), (180, 50, 10), (250, 140, 30)], YY[corona], XX[corona])
    disc = d <= r
    nx, ny = (XX[disc] - cx) / r, (YY[disc] - cy) / r
    gran = periodic_noise(np.arctan2(nx, 0.3) * 3 + t * 0.4, ny * 3 + 0.2 * math.sin(t), seed, 3)
    limb = 1 - (nx ** 2 + ny ** 2) * 0.6
    frame[disc] = dither_ramp(gran * 0.35 + limb * 0.65,
                              [(200, 60, 10), (245, 130, 20), (255, 200, 60), (255, 245, 180)],
                              YY[disc], XX[disc])
    # Prominence loop
    a0 = (t * 0.3) % (2 * math.pi)
    for k in range(40):
        a = a0 + k * 0.012
        h = 14 * math.sin(k / 39 * math.pi)
        x, y = cx + (r + h) * math.cos(a), cy + (r + h) * math.sin(a)
        if 0 <= int(y) < LH and 0 <= int(x) < LW:
            frame[int(y), int(x)] = (255, 120, 40)


def scene_black_hole(frame, t, spec, seed):
    Stars(seed).draw(frame, t, drift=0.5)
    cx, cy, rh = LW // 2, 200, 20
    rng = np.random.default_rng(seed)
    n = 900
    rad = rng.uniform(rh * 1.6, rh * 4.2, n)
    a0 = rng.uniform(0, 2 * np.pi, n)
    ang = a0 + t * 3.0 * (rh * 1.6 / rad) ** 1.5
    x = cx + rad * np.cos(ang)
    y = cy + rad * np.sin(ang) * 0.28
    heat = 1 - (rad - rh * 1.6) / (rh * 2.6)
    ramp = [(120, 30, 10), (220, 90, 20), (255, 180, 60), (255, 245, 210)]
    back = np.sin(ang) < 0
    hole = (XX - cx) ** 2 + (YY - cy) ** 2 <= rh ** 2

    def plot(sel):
        xi, yi = x[sel].astype(int), y[sel].astype(int)
        ok = (xi >= 0) & (xi < LW) & (yi >= 0) & (yi < LH)
        cols = dither_ramp(heat[sel][ok], ramp, yi[ok], xi[ok])
        frame[yi[ok], xi[ok]] = cols

    plot(back)
    # Lensed image of the far side of the disk, arching over the hole
    lens_r = rad[back] * 0.62 + rh * 0.5
    lx = (cx + lens_r * np.cos(ang[back])).astype(int)
    ly = (cy - np.abs(lens_r * np.sin(ang[back])) * 0.9 - rh * 0.2).astype(int)
    ok = (lx >= 0) & (lx < LW) & (ly >= 0) & (ly < LH)
    frame[ly[ok], lx[ok]] = dither_ramp(heat[back][ok] * 0.8, ramp, ly[ok], lx[ok])
    ring = ((XX - cx) ** 2 + (YY - cy) ** 2 <= (rh + 1.5) ** 2) & ~hole
    frame[ring] = (255, 230, 170)
    frame[hole] = (0, 0, 0)
    plot(~back)


def scene_pulsar(frame, t, spec, seed):
    Stars(seed).draw(frame, t, drift=1)
    cx, cy = LW // 2, 200
    spin = t * 2.2
    ang = np.arctan2(YY - cy, XX - cx)
    d = np.sqrt((XX - cx) ** 2 + (YY - cy) ** 2)
    for offset in (0, math.pi):
        diff = np.angle(np.exp(1j * (ang - spin - offset)))
        width = 0.10 + 6 / np.maximum(d, 1)
        beam = (np.abs(diff) < width) & (d > 6) & (d < 150)
        bv = (1 - np.abs(diff[beam]) / width[beam]) * (1 - d[beam] / 160)
        frame[beam] = dither_ramp(bv, [(20, 30, 80), (60, 120, 220), (170, 220, 255), (255, 255, 255)],
                                  YY[beam], XX[beam])
    # Magnetic field loops
    for side in (-1, 1):
        for k in range(3):
            loop_r = 14 + k * 9
            for s in range(60):
                a = s / 59 * math.pi
                x = cx + side * loop_r * math.sin(a)
                y = cy - loop_r * 1.4 * math.cos(a)
                if (s + int(t * 12)) % 4 and 0 <= int(y) < LH:
                    frame[int(y), int(x)] = (70, 90, 170)
    glow = d <= 9
    frame[glow] = dither_ramp(1 - d[glow] / 9, [(80, 120, 255), (200, 230, 255), (255, 255, 255)],
                              YY[glow], XX[glow])


def scene_galaxy(frame, t, spec, seed):
    Stars(seed).draw(frame, t, drift=0.5)
    cx, cy = LW // 2, 205
    rng = np.random.default_rng(seed)
    n = 2600
    arm = rng.integers(0, 2, n)
    rad = rng.exponential(22, n).clip(2, 85)
    ang = arm * math.pi + np.log(rad) * 2.2 + rng.normal(0, 0.35, n) - t * 0.25 * (30 / (rad + 10))
    x = (cx + rad * np.cos(ang)).astype(int)
    y = (cy + rad * np.sin(ang) * 0.55).astype(int)
    ok = (x >= 0) & (x < LW) & (y >= 0) & (y < LH)
    v = 1 - rad / 85
    frame[y[ok], x[ok]] = dither_ramp(v[ok], [(60, 70, 160), (130, 150, 230), (240, 220, 200), (255, 250, 230)],
                                      y[ok], x[ok])
    core = ((XX - cx) / 9) ** 2 + ((YY - cy) / 5) ** 2 <= 1
    frame[core] = (255, 245, 220)


SURFACE_PRESETS = {
    "mars_day": {"sky": ((200, 150, 100), (235, 190, 140)), "ground": [(90, 35, 20), (150, 70, 35), (190, 110, 60)]},
    "mars_sunset": {"sky": ((20, 20, 50), (120, 90, 80)), "ground": [(40, 20, 15), (80, 40, 25), (120, 65, 40)],
                    "sun_glow": (110, 170, 230)},
    "venus": {"sky": ((130, 70, 20), (230, 160, 70)), "ground": [(60, 35, 20), (95, 55, 30), (130, 80, 40)],
              "sun_glow": (255, 235, 180), "glow_mid": (240, 185, 100), "sun_rising": True},
    "moon": {"sky": ((0, 0, 5), (5, 5, 15)), "ground": [(60, 60, 65), (120, 120, 125), (180, 180, 185)],
             "earth": True, "stars": True},
}


def scene_surface(frame, t, spec, seed):
    p = SURFACE_PRESETS[spec.get("preset", "mars_day")]
    sky(*p["sky"], frame)
    if p.get("stars"):
        Stars(seed).draw(frame, t, drift=0.3)
    if p.get("earth"):
        draw_planet(frame, t, "earth", 120, 90, 22, seed=seed + 3)
    if p.get("sun_rising"):
        sun_y = 200 - t * 2.0
    elif p.get("sun_glow"):
        sun_y = 150 + t * 1.5
    else:
        sun_y = 70
    sun_x = 60
    if p.get("sun_glow"):
        d = np.sqrt((XX - sun_x) ** 2 + ((YY - sun_y) * 1.3) ** 2)
        glow = d < 60
        frame[glow] = dither_ramp(1 - d[glow] / 60, [p["sky"][1], p.get("glow_mid", (60, 110, 170)), p["sun_glow"]],
                                  YY[glow], XX[glow])
    sun = (XX - sun_x) ** 2 + (YY - sun_y) ** 2 <= 16
    frame[sun] = (255, 250, 230) if p.get("sun_glow") else (255, 240, 200)

    rng = np.random.default_rng(seed)
    horizon = 210
    for layer, col in enumerate(p["ground"]):
        h = horizon + layer * 22
        xs = np.arange(LW)
        prof = h + 8 * np.sin(xs / (25 + layer * 7) + rng.uniform(0, 6)) + 4 * np.sin(xs / 9 + rng.uniform(0, 6))
        if spec.get("volcano") and layer == 0:
            # Broad shield volcano with gentle slopes and a flat caldera on top
            u = np.clip(np.abs(xs - LW / 2) / 85, 0, 1)
            shield = horizon - 75 * (1 - u ** 1.6) + np.where(np.abs(xs - LW / 2) < 10, 3, 0)
            prof = np.minimum(prof, shield)
        frame[YY >= prof[None, :].repeat(LH, 0)] = col
    if spec.get("rover"):
        draw_sprite(frame, "rover", (t * 6) % (LW + 20) - 10, 252, (220, 220, 230))
    if spec.get("footprints"):
        for k in range(6):
            draw_sprite(frame, "footprint", 40 + k * 18, 290 - (k % 2) * 6, (90, 90, 95))
        draw_sprite(frame, "flag", 130, 238, (230, 230, 240), scale=2)


def scene_orbit(frame, t, spec, seed):
    Stars(seed).draw(frame, t, drift=1.5)
    draw_planet(frame, t * 2, "earth", LW // 2, 380, 170, seed=seed, light=(0.3, -0.9))
    a = (t * 0.6) % (2 * math.pi)
    x = LW / 2 + 70 * math.cos(a) - 6
    y = 150 + 24 * math.sin(a)
    draw_sprite(frame, "iss", x, y, (230, 230, 240), scale=2)


def scene_diamond_rain(frame, t, spec, seed):
    sky((5, 10, 40), (20, 50, 120), frame)
    Stars(seed).draw(frame, t * 0.2, drift=0)
    rng = np.random.default_rng(seed)
    n = 26
    xs = rng.uniform(5, LW - 10, n)
    speed = rng.uniform(25, 55, n)
    offs = rng.uniform(0, LH, n)
    for x, s, o in zip(xs, speed, offs):
        y = (o + t * s) % (LH + 10) - 10
        draw_sprite(frame, "diamond", x, y, (200, 240, 255), scale=2)
        if math.sin(t * 9 + x) > 0.7:
            frame[int(np.clip(y + 2, 0, LH - 1)), min(LW - 1, int(x) + 4)] = (255, 255, 255)


def scene_starfield(frame, t, spec, seed):
    nebula(frame, seed)
    shooting_star(frame, t, seed)
    Stars(seed, 220).draw(frame, t, drift=4)


SCENES = {
    "planet": scene_planet, "sun": scene_sun, "black_hole": scene_black_hole, "pulsar": scene_pulsar,
    "galaxy": scene_galaxy, "surface": scene_surface, "orbit": scene_orbit,
    "diamond_rain": scene_diamond_rain, "starfield": scene_starfield,
}
# Scenes set in space (dark background) that get a nebula and shooting stars
SPACE_SCENES = {"planet", "sun", "black_hole", "pulsar", "galaxy", "orbit"}


def render_frame(spec: dict, t: float, seed: int, headline: str = "", channel: str = "",
                 footer: str = "") -> np.ndarray:
    """Draw one low-resolution frame of a scene with its text overlay."""
    frame = np.zeros((LH, LW, 3), dtype=np.uint8)
    frame[:] = (4, 4, 16)
    scene = spec.get("scene", "starfield")
    if scene in SPACE_SCENES:
        nebula(frame, seed)
        shooting_star(frame, tq(t), seed)
    SCENES.get(scene, scene_starfield)(frame, tq(t), spec, seed)

    # Darkened band behind the top text and footer for readability
    if channel or headline:
        bottom = 26 + text_mask(headline, 1, LW - 16).shape[0] + 4 if headline else 22
        frame[:bottom] = (frame[:bottom] * 0.35).astype(np.uint8)
    if footer:
        frame[LH - 20:] = (frame[LH - 20:] * 0.35).astype(np.uint8)
    if channel:
        stamp_text(frame, channel, 8, 1, (255, 255, 255))
        frame[18, LW // 2 - 22:LW // 2 + 22] = (255, 210, 60)
    if headline:
        stamp_text(frame, headline, 26, 1, (255, 255, 255), max_width=LW - 16)
    if footer:
        stamp_text(frame, footer, LH - 16, 1, (255, 210, 60))
    return frame


def upscale(frame: np.ndarray) -> np.ndarray:
    return frame.repeat(SCALE, axis=0).repeat(SCALE, axis=1)


def scene_clip(spec: dict, duration: float, seed: int, headline: str = "", channel: str = "",
               footer: str = "") -> VideoClip:
    """A 1080x1920 MoviePy clip animating one scene."""
    cache = {}

    def make_frame(t):
        key = tq(t)
        if key not in cache:
            cache.clear()
            cache[key] = upscale(render_frame(spec, key, seed, headline, channel, footer))
        return cache[key]

    return VideoClip(make_frame, duration=duration)


def render_caption(txt: str, **_) -> ImageClip:
    """Pixel-font caption for SubtitlesClip: yellow with a black outline, centred."""
    frame = np.zeros((LH, LW, 3), dtype=np.uint8)
    mask = text_mask(txt, 2, LW - 12)
    h, w = mask.shape
    y0, x0 = (LH - h) // 2 + 20, (LW - w) // 2
    region = np.zeros((LH, LW), dtype=bool)
    region[y0:y0 + h, x0:x0 + w] = mask
    outline = region.copy()
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            outline |= np.roll(np.roll(region, dy, 0), dx, 1)
    frame[outline] = (0, 0, 0)
    frame[region] = (255, 230, 40)
    alpha = (outline.astype(np.uint8) * 255)[..., None]
    rgba = np.concatenate([frame, alpha], axis=2)
    return ImageClip(upscale(rgba), transparent=True)


# Keyword -> scene, checked in order; the first match wins
_KEYWORD_SCENES = [
    (("black hole", "spaghetti", "event horizon"), {"scene": "black_hole"}),
    (("neutron", "pulsar", "magnetar"), {"scene": "pulsar"}),
    (("diamond",), {"scene": "diamond_rain"}),
    (("galaxy", "galaxies", "andromeda", "milky way"), {"scene": "galaxy"}),
    (("space station", "iss", "astronaut", "orbit earth", "orbits earth"), {"scene": "orbit"}),
    (("footprint", "walked on the moon", "moon landing", "apollo"),
     {"scene": "surface", "preset": "moon", "footprints": True}),
    (("olympus", "volcano"), {"scene": "surface", "preset": "mars_day", "volcano": True}),
    (("sunset", "sunrise on mars"), {"scene": "surface", "preset": "mars_sunset", "rover": True}),
    (("rover",), {"scene": "surface", "preset": "mars_day", "rover": True}),
    (("saturn", "rings"), {"scene": "planet", "preset": "saturn"}),
    (("jupiter", "great red spot"), {"scene": "planet", "preset": "jupiter"}),
    (("venus",), {"scene": "planet", "preset": "venus"}),
    (("mars", "martian"), {"scene": "planet", "preset": "mars"}),
    (("neptune",), {"scene": "planet", "preset": "neptune"}),
    (("uranus",), {"scene": "planet", "preset": "uranus"}),
    (("mercury",), {"scene": "planet", "preset": "mercury"}),
    (("moon", "lunar"), {"scene": "planet", "preset": "moon"}),
    (("earth",), {"scene": "planet", "preset": "earth"}),
    (("sun", "solar", "sunlight"), {"scene": "sun"}),
]


# Phrases where a body is only a unit of comparison ("243 Earth days")
_UNIT_PHRASES = re.compile(r"\b(earth|earth's)\s+(days?|years?|hours?|masses|mass|sizes?)\b|\bearths\b|\bsuns\b")
# Scenes that sentences mention in passing ("orbits the Sun"); they only win
# when the video's topic doesn't already have a scene
_WEAK = ({"scene": "sun"}, {"scene": "planet", "preset": "earth"})


def scene_for_text(text: str, fallback: dict | None = None) -> dict:
    """Pick a scene for a sentence by keywords, else return the fallback."""
    lowered = " " + re.sub(r"[^a-z' ]", " ", _UNIT_PHRASES.sub(" ", text.lower())) + " "
    for keywords, scene in _KEYWORD_SCENES:
        if any(f" {k} " in lowered or f" {k}s " in lowered for k in keywords):
            return dict(scene)
    return dict(fallback) if fallback else {"scene": "starfield"}


def scenes_for_script(sentences: list[str], topic: str = "") -> list[dict]:
    """One scene per sentence. Sentences without a strong match keep the
    previous scene, or the topic's scene."""
    topic_scene = scene_for_text(topic) if topic else None
    if topic_scene == {"scene": "starfield"}:
        topic_scene = None
    scenes, previous = [], topic_scene
    for sentence in sentences:
        fallback = previous or topic_scene
        scene = scene_for_text(sentence, fallback)
        if scene in _WEAK and fallback and fallback not in _WEAK:
            scene = dict(fallback)
        scenes.append(scene)
        previous = scene
    return scenes
