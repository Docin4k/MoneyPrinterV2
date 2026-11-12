"""8-bit style animated scenes for YouTube Shorts.

Scenes are laid out on a 180x320 design grid but drawn at DETAIL x that
resolution (360x640 by default) with a limited palette and ordered (Bayer)
dithering, then scaled up with hard pixel edges to 1080x1920. Animation is
stepped at 12 frames per second for a retro feel.

A scene is described by a dict, for example {"scene": "planet", "preset": "venus"}.
Available scenes: planet, sun, black_hole, pulsar, galaxy, surface, orbit,
diamond_rain, starfield and more; underwater scenes live in pixel_ocean.py.
See SCENES and PLANET_PRESETS below.

Text uses a built-in 5x7 bitmap font, so no font files are needed.
"""
import math
import re
import random

import numpy as np
from moviepy.editor import ImageClip, VideoClip

LW, LH = 180, 320          # design grid: all scene coordinates use these units
DETAIL = 2                 # pixels per design unit: 2 -> drawn at 360x640
PW, PH = LW * DETAIL, LH * DETAIL
SCALE = 1080 // PW         # 360x640 -> 1080x1920
ANIM_FPS = 12              # animation steps per second

BAYER = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) + 0.5) / 16.0
BAYER_FULL = np.tile(BAYER, (PH // 4 + 1, PW // 4 + 1))[:PH, :PW]

# Pixel indices, and the same positions in design units (for scene geometry)
PY, PX = np.mgrid[0:PH, 0:PW]
YY, XX = (PY + 0.5) / DETAIL, (PX + 0.5) / DETAIL


def px(v) -> int:
    """Design-unit coordinate -> pixel index."""
    return int(v * DETAIL)


def put(frame, x, y, color, size=1):
    """Set a size x size block of pixels at a design-unit position."""
    x0, y0 = px(x), px(y)
    if 0 <= y0 < PH and 0 <= x0 < PW:
        frame[y0:y0 + size, x0:x0 + size] = color

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
    ";": "00000 01100 01100 00000 01100 00100 01000",
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


def _outline(region: np.ndarray, width: int) -> np.ndarray:
    grown = region.copy()
    for dy in range(-width, width + 1):
        for dx in range(-width, width + 1):
            if dy or dx:
                grown |= np.roll(np.roll(region, dy, 0), dx, 1)
    return grown


def stamp_text(frame, text, y, scale, color, outline=(0, 0, 0), max_width=LW - 12):
    """Draw outlined pixel text centred horizontally at design row y (sizes in
    design units); returns the bottom row in design units."""
    mask = text_mask(text, scale * DETAIL, max_width * DETAIL)
    h, w = mask.shape
    x0, y0 = (PW - w) // 2, px(y)
    region = np.zeros((PH, PW), dtype=bool)
    y1, y2 = max(0, y0), min(PH, y0 + h)
    region[y1:y2, x0:x0 + w] = mask[y1 - y0:y2 - y0]
    if outline is not None:
        frame[_outline(region, DETAIL) & ~region] = outline
    frame[region] = color
    return y + h / DETAIL


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
        count = int(count * 1.6)  # finer grid: more, smaller stars
        rng = np.random.default_rng(seed)
        self.x = rng.uniform(0, LW, count)
        self.y = rng.uniform(0, LH, count)
        self.layer = rng.choice([1, 2, 3], count, p=[0.6, 0.3, 0.1])
        self.phase = rng.uniform(0, 2 * np.pi, count)
        self.speed = rng.uniform(0.6, 1.6, count)

    def draw(self, frame, t, drift=2.0, mask=None):
        x = (((self.x + t * drift * self.layer) % LW) * DETAIL).astype(int)
        y = (self.y * DETAIL).astype(int)
        tw = np.sin(self.phase + t * 3 * self.speed) > -0.6
        bright = np.where(self.layer == 3, 255, np.where(self.layer == 2, 200, 140))
        for xi, yi, b, on, layer in zip(x, y, bright, tw, self.layer):
            if not on or (mask is not None and mask[yi, xi]):
                continue
            size = 2 if layer == 3 else 1
            frame[yi:yi + size, xi:xi + size] = (b, b, min(255, b + 20))
            if layer == 3 and math.sin(t * 4 + xi) > 0.3:  # sparkle cross on big stars
                for dy, dx in ((-2, 0), (2, 0), (0, -2), (0, 2), (-3, 0), (3, 0), (0, -3), (0, 3)):
                    yy, xx = yi + dy, (xi + dx) % PW
                    if 0 <= yy < PH and (mask is None or not mask[yy, xx]):
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
    "rocket": ["...#...", "..###..", "..###..", ".#####.", ".##.##.", ".#####.", ".#####.", ".#####.",
               ".#####.", ".#####.", ".#####.", ".#####.", "##.#.##", "#.....#"],
}


def draw_sprite(frame, name, x, y, color, scale=1):
    """Draw a sprite at a design-unit position; `scale` is in design units."""
    rows = SPRITES[name]
    block = scale * DETAIL
    x0, y0 = px(x), px(y)
    for r, row in enumerate(rows):
        for c, ch in enumerate(row):
            if ch == "#":
                yy, xx = y0 + r * block, x0 + c * block
                if 0 <= yy < PH and 0 <= xx < PW:
                    frame[yy:yy + block, xx:xx + block] = color


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
    "pluto": {"ramp": [(60, 40, 30), (140, 100, 75), (200, 170, 140), (245, 235, 220)], "bands": 0.0,
              "noise": 0.8, "spin": 0.12, "atmo": None, "heart": True},
    "io": {"ramp": [(90, 50, 10), (200, 150, 40), (235, 210, 90), (250, 240, 170)], "bands": 0.0,
           "noise": 0.9, "spin": 0.3, "atmo": None, "volcanic": True},
    "europa": {"ramp": [(120, 90, 70), (190, 175, 160), (230, 225, 215), (250, 250, 245)], "bands": 0.0,
               "noise": 0.5, "spin": 0.2, "atmo": None, "cracks": 0.0},
    "titan": {"ramp": [(110, 60, 15), (180, 110, 40), (220, 160, 70), (240, 200, 120)], "bands": 0.25,
              "noise": 0.25, "spin": 0.15, "atmo": (240, 170, 80)},
    "ganymede": {"ramp": [(60, 50, 45), (110, 100, 90), (170, 160, 150), (215, 210, 200)], "bands": 0.0,
                 "noise": 1.0, "spin": 0.2, "atmo": None, "craters": True},
    "triton": {"ramp": [(90, 70, 75), (170, 140, 140), (220, 195, 190), (245, 235, 230)], "bands": 0.1,
               "noise": 0.7, "spin": -0.2, "atmo": None},
    "ceres": {"ramp": [(45, 45, 45), (95, 95, 95), (145, 145, 145), (190, 190, 190)], "bands": 0.0,
              "noise": 0.7, "spin": 0.3, "atmo": None, "craters": True, "bright_spots": True},
    "lava": {"ramp": [(20, 10, 10), (60, 20, 15), (200, 60, 20), (255, 200, 60)], "bands": 0.0,
             "noise": 0.6, "spin": 0.25, "atmo": (255, 120, 40), "cracks": 1.0},
    "ice": {"ramp": [(40, 70, 110), (110, 160, 200), (180, 220, 240), (240, 250, 255)], "bands": 0.4,
            "noise": 0.5, "spin": 0.3, "atmo": (180, 230, 255)},
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
    if p.get("heart"):
        # Pluto's bright heart-shaped plain (two overlapping lobes)
        hl = np.angle(np.exp(1j * lon))
        lobe1 = ((hl + 0.25) / 0.45) ** 2 + ((lat + 0.05) / 0.42) ** 2 < 1
        lobe2 = ((hl - 0.3) / 0.38) ** 2 + ((lat - 0.08) / 0.36) ** 2 < 1
        val = np.where(lobe1 | lobe2, 1.0, val)
    if p.get("cracks") is not None:
        # Long crossing lines (Europa's ice cracks, a lava world's glowing seams)
        crng = random.Random(seed + 5)
        lines = np.zeros_like(val, dtype=bool)
        for _ in range(8):
            k, m, ph = crng.randint(1, 4), crng.uniform(-3, 3), crng.uniform(0, 6.28)
            lines |= np.abs(np.sin(k * lon + m * lat + ph)) < 0.035
        val = np.where(lines, p["cracks"], val)
    if p.get("craters"):
        rng = random.Random(seed)
        for _ in range(14):
            clon, clat, cr = rng.uniform(-3.14, 3.14), rng.uniform(-1.2, 1.2), rng.uniform(0.08, 0.25)
            dl = np.angle(np.exp(1j * (lon - clon)))
            dd = np.sqrt((dl * np.cos(lat)) ** 2 + (lat - clat) ** 2)
            val = np.where(dd < cr, val - 0.25, np.where(dd < cr * 1.25, val + 0.15, val))
    if p.get("bright_spots"):
        brng = random.Random(seed + 9)
        for _ in range(3):
            clon, clat = brng.uniform(-3.14, 3.14), brng.uniform(-0.6, 0.6)
            dl = np.angle(np.exp(1j * (lon - clon)))
            val = np.where(np.sqrt((dl * np.cos(lat)) ** 2 + (lat - clat) ** 2) < 0.06, 1.0, val)

    lx, ly = light
    lz = math.sqrt(max(0.0, 1 - lx ** 2 - ly ** 2))
    shade = np.clip(nx * lx + ny * ly + nz * lz, 0, 1)
    v = np.clip(val, 0, 1) * (0.25 + 0.75 * shade)
    colors = dither_ramp(v, p["ramp"], PY[inside], PX[inside])
    if p.get("spot"):
        spot_col = dither_ramp(0.4 + 0.6 * shade[spot], [(90, 20, 10), (180, 60, 30), (230, 110, 70)],
                               PY[inside][spot], PX[inside][spot])
        colors[spot] = spot_col
    if p.get("volcanic"):
        vrng = random.Random(seed + 3)
        for _ in range(9):
            clon, clat = vrng.uniform(-3.14, 3.14), vrng.uniform(-1.1, 1.1)
            dl = np.angle(np.exp(1j * (lon - clon)))
            spot_v = np.sqrt((dl * np.cos(lat)) ** 2 + (lat - clat) ** 2) < vrng.uniform(0.05, 0.12)
            colors[spot_v & (shade > 0.05)] = (120, 25, 10)
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
    cols = dither_ramp(shimmer[sel], [(120, 100, 70), (190, 170, 130), (235, 220, 180)], PY[sel], PX[sel])
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
        field = np.zeros(XX.shape)
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
    for i in range(28):
        f = phase - i * 0.006
        if f < 0:
            break
        b = 255 - i * 8
        put(frame, x0 + dx * f, y0 + dy * f, (b, b, min(255, b + 30)))


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
    sel = ring.copy()
    sel[ring] = BAYER_FULL[ring] < strength * 0.5
    frame[sel] = (frame[sel] * 0.5 + np.array(color) * 0.5).astype(np.uint8)


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
    frame[corona] = dither_ramp(cv, [(60, 10, 10), (180, 50, 10), (250, 140, 30)], PY[corona], PX[corona])
    disc = d <= r
    nx, ny = (XX[disc] - cx) / r, (YY[disc] - cy) / r
    gran = periodic_noise(np.arctan2(nx, 0.3) * 3 + t * 0.4, ny * 3 + 0.2 * math.sin(t), seed, 3)
    limb = 1 - (nx ** 2 + ny ** 2) * 0.6
    frame[disc] = dither_ramp(gran * 0.35 + limb * 0.65,
                              [(200, 60, 10), (245, 130, 20), (255, 200, 60), (255, 245, 180)],
                              PY[disc], PX[disc])
    # Prominence loop
    a0 = (t * 0.3) % (2 * math.pi)
    for k in range(90):
        a = a0 + k * 0.0054
        h = 14 * math.sin(k / 89 * math.pi)
        put(frame, cx + (r + h) * math.cos(a), cy + (r + h) * math.sin(a), (255, 120, 40), size=2)


def scene_black_hole(frame, t, spec, seed):
    Stars(seed).draw(frame, t, drift=0.5)
    cx, cy, rh = LW // 2, 200, 20
    rng = np.random.default_rng(seed)
    n = 900 * DETAIL * DETAIL
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
        xi, yi = (x[sel] * DETAIL).astype(int), (y[sel] * DETAIL).astype(int)
        ok = (xi >= 0) & (xi < PW) & (yi >= 0) & (yi < PH)
        cols = dither_ramp(heat[sel][ok], ramp, yi[ok], xi[ok])
        frame[yi[ok], xi[ok]] = cols

    plot(back)
    # Lensed image of the far side of the disk, arching over the hole
    lens_r = rad[back] * 0.62 + rh * 0.5
    lx = ((cx + lens_r * np.cos(ang[back])) * DETAIL).astype(int)
    ly = ((cy - np.abs(lens_r * np.sin(ang[back])) * 0.9 - rh * 0.2) * DETAIL).astype(int)
    ok = (lx >= 0) & (lx < PW) & (ly >= 0) & (ly < PH)
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
                                  PY[beam], PX[beam])
    # Magnetic field loops
    for side in (-1, 1):
        for k in range(3):
            loop_r = 14 + k * 9
            for s in range(120):
                a = s / 119 * math.pi
                if (s // 2 + int(t * 12)) % 4:
                    put(frame, cx + side * loop_r * math.sin(a), cy - loop_r * 1.4 * math.cos(a), (70, 90, 170))
    glow = d <= 9
    frame[glow] = dither_ramp(1 - d[glow] / 9, [(80, 120, 255), (200, 230, 255), (255, 255, 255)],
                              PY[glow], PX[glow])


def scene_galaxy(frame, t, spec, seed):
    Stars(seed).draw(frame, t, drift=0.5)
    cx, cy = LW // 2, 205
    rng = np.random.default_rng(seed)
    n = 2600 * DETAIL * DETAIL
    arm = rng.integers(0, 2, n)
    rad = rng.exponential(22, n).clip(2, 85)
    ang = arm * math.pi + np.log(rad) * 2.2 + rng.normal(0, 0.35, n) - t * 0.25 * (30 / (rad + 10))
    x = ((cx + rad * np.cos(ang)) * DETAIL).astype(int)
    y = ((cy + rad * np.sin(ang) * 0.55) * DETAIL).astype(int)
    ok = (x >= 0) & (x < PW) & (y >= 0) & (y < PH)
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
                                  PY[glow], PX[glow])
    sun = (XX - sun_x) ** 2 + (YY - sun_y) ** 2 <= 16
    frame[sun] = (255, 250, 230) if p.get("sun_glow") else (255, 240, 200)

    rng = np.random.default_rng(seed)
    horizon = 210
    for layer, col in enumerate(p["ground"]):
        h = horizon + layer * 22
        xs = (np.arange(PW) + 0.5) / DETAIL
        prof = h + 8 * np.sin(xs / (25 + layer * 7) + rng.uniform(0, 6)) + 4 * np.sin(xs / 9 + rng.uniform(0, 6))
        if spec.get("volcano") and layer == 0:
            # Broad shield volcano with gentle slopes and a flat caldera on top
            u = np.clip(np.abs(xs - LW / 2) / 85, 0, 1)
            shield = horizon - 75 * (1 - u ** 1.6) + np.where(np.abs(xs - LW / 2) < 10, 3, 0)
            prof = np.minimum(prof, shield)
        frame[YY >= prof[None, :]] = col
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
            put(frame, min(LW - 1, x + 4), float(np.clip(y + 2, 0, LH - 1)), (255, 255, 255), size=DETAIL)


def scene_starfield(frame, t, spec, seed):
    nebula(frame, seed)
    shooting_star(frame, t, seed)
    Stars(seed, 220).draw(frame, t, drift=4)


def _plot(frame, xs, ys, values, ramp):
    """Plot design-unit points with a dithered colour ramp."""
    xi, yi = (np.asarray(xs) * DETAIL).astype(int), (np.asarray(ys) * DETAIL).astype(int)
    ok = (xi >= 0) & (xi < PW) & (yi >= 0) & (yi < PH)
    frame[yi[ok], xi[ok]] = dither_ramp(np.asarray(values)[ok], ramp, yi[ok], xi[ok])


def scene_comet(frame, t, spec, seed):
    Stars(seed).draw(frame, t, drift=0.6)
    hx, hy = 62 + t * 1.6, 120 + t * 0.9
    # Tails point away from the Sun, which is off-screen at (-60, -80)
    ux, uy = (hx + 60) / math.hypot(hx + 60, hy + 80), (hy + 80) / math.hypot(hx + 60, hy + 80)
    px_, py_ = -uy, ux                                # perpendicular
    rng = np.random.default_rng(seed)
    n = 2600
    s_ = rng.random(n) ** 1.7 * 170                  # distance along the tail
    spread = rng.normal(0, 1, n) * (1.5 + s_ * 0.13)
    bend = (s_ ** 2) * 0.0022
    _plot(frame, hx + ux * s_ + px_ * (spread + bend), hy + uy * s_ + py_ * (spread + bend),
          1 - s_ / 175 + rng.uniform(-0.1, 0.1, n),
          [(60, 50, 40), (170, 150, 110), (240, 225, 180), (255, 250, 230)])
    m = 1200
    s2 = rng.random(m) * 190
    flick = 0.6 + 0.4 * np.sin(s2 * 0.3 - t * 6)
    _plot(frame, hx + ux * s2 + px_ * rng.normal(0, 1, m) * (0.8 + s2 * 0.02),
          hy + uy * s2 + py_ * rng.normal(0, 1, m) * (0.8 + s2 * 0.02),
          (1 - s2 / 200) * flick, [(20, 40, 90), (60, 120, 220), (160, 210, 255)])
    d = np.sqrt((XX - hx) ** 2 + (YY - hy) ** 2)
    coma = d < 9
    frame[coma] = dither_ramp(1 - d[coma] / 9, [(120, 140, 160), (210, 230, 240), (255, 255, 255)], PY[coma], PX[coma])


def _rock_mask(cx, cy, r, ang, seed):
    rng = random.Random(seed)
    a1, a2, p1, p2 = rng.uniform(0.12, 0.22), rng.uniform(0.05, 0.12), rng.uniform(0, 6.3), rng.uniform(0, 6.3)
    dx, dy = XX - cx, YY - cy
    theta = np.arctan2(dy, dx) - ang
    edge = r * (1 + a1 * np.sin(3 * theta + p1) + a2 * np.sin(5 * theta + p2))
    d = np.sqrt(dx ** 2 + dy ** 2)
    return d < edge, dx / np.maximum(edge, 1e-6), dy / np.maximum(edge, 1e-6), theta


def scene_asteroids(frame, t, spec, seed):
    Stars(seed).draw(frame, t, drift=1)
    rng = random.Random(seed)
    rocks = sorted(({"r": rng.uniform(4, 26), "x": rng.uniform(0, LW), "y": rng.uniform(40, 300),
                     "w": rng.uniform(-0.6, 0.6), "s": rng.randint(0, 9999)} for _ in range(16)), key=lambda k: k["r"])
    ramp = [(30, 25, 22), (80, 70, 60), (140, 125, 110), (200, 185, 165)]
    for k in rocks:
        x = (k["x"] - t * k["r"] * 0.35) % (LW + 60) - 30
        inside, nx, ny, theta = _rock_mask(x, k["y"], k["r"], t * k["w"], k["s"])
        if not inside.any():
            continue
        shade = np.clip(0.55 - 0.45 * (nx[inside] * 0.7 + ny[inside] * 0.5), 0, 1)
        tex = periodic_noise(theta[inside] * 2, np.sqrt(nx[inside] ** 2 + ny[inside] ** 2) * 3, k["s"], 3)
        frame[inside] = dither_ramp(shade * (0.7 + 0.3 * tex), ramp, PY[inside], PX[inside])


def scene_aurora(frame, t, spec, seed):
    sky((2, 6, 20), (8, 30, 45), frame)
    Stars(seed).draw(frame, t, drift=0.2)
    xs = XX[0]
    for i, (hue, base) in enumerate(((0, 120), (1, 95), (0, 150))):
        ph = i * 2.1
        yb = base + 18 * np.sin(xs / 30 + t * 0.6 + ph) + 8 * np.sin(xs / 13 - t * 0.9 + ph)
        h = 55 + 22 * np.sin(xs / 22 + t * 0.4 + ph)
        rel = (yb[None, :] - YY) / h[None, :]
        band = (rel > 0) & (rel < 1)
        rays = 0.55 + 0.45 * np.sin(XX * 0.9 + t * 3 + ph) ** 2
        v = (1 - rel) * rays * (0.85 if i else 1.0)
        ramp = [(10, 40, 40), (30, 160, 90), (120, 255, 170)] if hue == 0 else [(30, 15, 50), (120, 60, 170), (220, 150, 255)]
        sel = band & (v > 0.12)
        frame[sel] = np.maximum(frame[sel], dither_ramp(v[sel], ramp, PY[sel], PX[sel]))
    hills = 250 + 10 * np.sin(xs / 40 + seed) + 5 * np.sin(xs / 11)
    ground = YY >= hills[None, :]
    frame[ground] = dither_ramp(((YY[ground] - 240) / 80), [(150, 170, 200), (60, 80, 110), (20, 30, 50)], PY[ground], PX[ground])
    rng = random.Random(seed)
    for _ in range(9):
        tx, th = rng.uniform(0, LW), rng.uniform(14, 30)
        base = 250 + 10 * math.sin(tx / 40 + seed) + 5 * math.sin(tx / 11)
        tree = (YY < base + 2) & (YY > base - th) & (np.abs(XX - tx) < (YY - (base - th)) * 0.32)
        frame[tree] = (6, 12, 20)


def scene_eclipse(frame, t, spec, seed):
    Stars(seed).draw(frame, t, drift=0.3)
    cx, cy, r = LW / 2, 190, 34
    d = np.sqrt((XX - cx) ** 2 + (YY - cy) ** 2)
    ang = np.arctan2(YY - cy, XX - cx)
    rng = random.Random(seed)
    streak = sum(rng.uniform(0.3, 1) * np.abs(np.sin(ang * k + rng.uniform(0, 6.3) + t * 0.05)) ** 6
                 for k in (2, 3, 5, 7))
    v = np.exp(-(d - r) / (10 + 22 * streak)) * (d > r)
    sel = v > 0.06
    frame[sel] = dither_ramp(v[sel], [(10, 20, 40), (90, 110, 160), (200, 215, 240), (255, 255, 255)], PY[sel], PX[sel])
    mx = cx + 2.5 * math.sin(t * 0.25)
    moon = (XX - mx) ** 2 + (YY - cy) ** 2 <= (r + 0.6) ** 2
    frame[moon] = (0, 0, 0)
    if abs(mx - cx) > 1.6:   # a sliver of sunlight: the "diamond ring"
        bx = cx - r * math.copysign(1, mx - cx)
        bead = (XX - bx) ** 2 + (YY - cy) ** 2 <= 9
        frame[bead] = (255, 255, 255)


def scene_rocket(frame, t, spec, seed):
    # Dawn: navy -> purple -> orange near the horizon
    frame[:] = dither_ramp(np.clip((YY - 20) / 270, 0, 1), [(8, 14, 50), (40, 30, 90), (120, 60, 120), (240, 140, 80)])
    Stars(seed).draw(frame, t, drift=0.2, mask=YY > 130)
    lift = max(0.0, t - 0.6) ** 1.7 * 5
    rx, ry = LW / 2 - 10.5, 180 - lift
    rng = np.random.default_rng(seed + int(t * 12))
    n = 420
    fx = rx + 10.5 + rng.normal(0, 3.2, n)
    fy = ry + 42 + rng.random(n) ** 1.5 * 46
    _plot(frame, fx, fy, 1 - (fy - ry - 42) / 48, [(200, 60, 20), (250, 160, 40), (255, 240, 180)])
    smoke = np.random.default_rng(seed)
    for _ in range(14):
        sx, sr = LW / 2 + smoke.normal(0, 30), smoke.uniform(8, 22) * (1 + min(t, 6) * 0.15)
        puff = (XX - sx) ** 2 + ((YY - 268) * 1.4) ** 2 <= sr ** 2
        frame[puff] = dither_ramp(np.full(puff.sum(), 0.6), [(90, 90, 100), (170, 170, 180), (230, 230, 235)], PY[puff], PX[puff])
    frame[YY > 280] = (40, 35, 40)
    tower = (XX > LW / 2 + 16) & (XX < LW / 2 + 20) & (YY > 170) & (YY < 280)
    frame[tower & ((PY // 6 + PX // 6) % 2 == 0)] = (180, 60, 40)
    body = (220, 225, 235)
    draw_sprite(frame, "rocket", rx, ry, body, scale=3)
    for fx_, fy_ in ((rx, ry + 36), (rx + 18, ry + 36), (rx + 9, ry + 3)):
        put(frame, fx_, fy_, (200, 40, 40), size=3 * DETAIL)


def scene_supernova(frame, t, spec, seed):
    Stars(seed).draw(frame, t, drift=0.3)
    cx, cy = LW / 2, 190
    phase = t % 7
    R = 12 + phase * 20
    d = np.sqrt((XX - cx) ** 2 + (YY - cy) ** 2)
    ang = np.arctan2(YY - cy, XX - cx)
    wob = 1 + 0.08 * np.sin(ang * 7 + seed) + 0.05 * np.sin(ang * 13)
    ring = np.abs(d - R * wob) < (2 + R * 0.05)
    frame[ring] = dither_ramp(0.6 + 0.4 * np.sin(ang[ring] * 9 + t), [(120, 40, 120), (240, 110, 150), (255, 220, 200)], PY[ring], PX[ring])
    rng = np.random.default_rng(seed)
    n = 1800
    a = rng.uniform(0, 2 * np.pi, n)
    dist = R * (0.35 + 0.6 * rng.random(n)) * (1 + 0.08 * np.sin(a * 7 + seed))
    hue = rng.random(n)
    _plot(frame, cx + np.cos(a) * dist, cy + np.sin(a) * dist, hue, [(30, 120, 140), (90, 200, 200), (250, 160, 80), (255, 230, 150)])
    glow = np.exp(-d / (10 + 6 * math.sin(t * 3))) * (1.2 - phase / 7)
    sel = glow > 0.08
    frame[sel] = np.maximum(frame[sel], dither_ramp(glow[sel], [(80, 90, 160), (200, 210, 255), (255, 255, 255)], PY[sel], PX[sel]))


def scene_nebula(frame, t, spec, seed):
    rng = random.Random(seed * 3 + 1)
    u, v = XX / LW * 2 * np.pi + t * 0.02, YY / LH * 2 * np.pi
    layers = [((220, 100, 150), (60, 15, 50)), ((70, 180, 180), (8, 40, 55)), ((210, 160, 90), (60, 35, 15))]
    for hi, lo in layers:
        field = np.zeros(XX.shape)
        for k in range(5):
            a, b = rng.uniform(0.6, 2.4), rng.uniform(0.6, 3.0)
            field += np.sin(u * a + rng.uniform(0, 6.3) + np.sin(v * b + rng.uniform(0, 6.3)) * 1.6) / (k + 1)
        field = (field - field.min()) / (np.ptp(field) + 1e-9)
        dens = np.clip((field - 0.62) / 0.38, 0, 1) ** 1.2   # separate clouds with dark space between
        sel = dens > 0.04
        frame[sel] = np.maximum(frame[sel], dither_ramp(dens[sel], [(4, 4, 16), lo, hi], PY[sel], PX[sel]))
    Stars(seed, 260).draw(frame, t, drift=0.3)
    srng = random.Random(seed)
    for _ in range(7):
        x, y = srng.uniform(20, LW - 20), srng.uniform(60, 290)
        b = 0.6 + 0.4 * math.sin(t * 2 + x)
        for dx in range(-6, 7):
            put(frame, x + dx * 0.5, y, (int(255 * b), int(255 * b), 255))
        for dy in range(-6, 7):
            put(frame, x, y + dy * 0.5, (int(255 * b), int(255 * b), 255))


def _hex(cx, cy, s):
    dx, dy = np.abs(XX - cx), np.abs(YY - cy)
    h = s * math.sqrt(3) / 2
    return (dy <= h) & (dx * math.sqrt(3) / 2 + dy / 2 <= h)


def scene_telescope(frame, t, spec, seed):
    Stars(seed).draw(frame, t, drift=0.4)
    cx, cy = LW / 2 + 3 * math.sin(t * 0.3), 175
    for k in range(5):     # sunshield layers
        y0 = cy + 52 + k * 3
        layer = (np.abs(XX - cx) / 82 + np.abs(YY - y0) / 26) <= 1
        frame[layer] = (120 + k * 20, 90 + k * 22, 170 + k * 16)
    s = 9.0
    cells = [(q, r) for q in range(-2, 3) for r in range(-2, 3) if 0 < max(abs(q), abs(r), abs(q + r)) <= 2]
    for q, r in cells:
        hx, hy = cx + s * 1.5 * q, cy + s * math.sqrt(3) * (r + q / 2)
        cell = _hex(hx, hy, s - 0.8)
        shine = 0.55 + 0.45 * np.sin((XX[cell] + YY[cell]) * 0.08 - t * 1.5)
        frame[cell] = dither_ramp(shine, [(120, 80, 20), (210, 160, 40), (255, 220, 110), (255, 250, 210)], PY[cell], PX[cell])
    tip = (cx, cy - 46)
    for ex, ey in ((cx - 24, cy + 20), (cx + 24, cy + 20), (cx, cy + 34)):
        for i in range(60):
            f = i / 59
            put(frame, tip[0] + (ex - tip[0]) * f, tip[1] + (ey - tip[1]) * f, (190, 190, 200))
    frame[_hex(*tip, 3.5)] = (230, 200, 120)


def scene_binary_suns(frame, t, spec, seed):
    sky((60, 30, 70), (250, 170, 90), frame)
    a = t * 0.5
    for (ox, r, core, glow) in ((1, 14, (255, 200, 120), (255, 140, 60)), (-1, 9, (255, 250, 220), (255, 220, 150))):
        sx, sy = LW / 2 + ox * 34 * math.cos(a), 110 + ox * 10 * math.sin(a)
        d = np.sqrt((XX - sx) ** 2 + (YY - sy) ** 2)
        halo_ = (d > r) & (d < r * 2.6)
        frame[halo_] = np.maximum(frame[halo_], dither_ramp(1 - (d[halo_] - r) / (r * 1.6), [(200, 110, 80), glow], PY[halo_], PX[halo_]))
        frame[d <= r] = core
    rng = np.random.default_rng(seed)
    xs = XX[0]
    for layer, col in enumerate([(160, 90, 50), (200, 120, 60), (230, 160, 90)]):
        prof = 215 + layer * 24 + 9 * np.sin(xs / (30 + layer * 9) + rng.uniform(0, 6)) + 3 * np.sin(xs / 7 + rng.uniform(0, 6))
        frame[YY >= prof[None, :]] = col


SCENES = {
    "planet": scene_planet, "sun": scene_sun, "black_hole": scene_black_hole, "pulsar": scene_pulsar,
    "galaxy": scene_galaxy, "surface": scene_surface, "orbit": scene_orbit,
    "diamond_rain": scene_diamond_rain, "starfield": scene_starfield,
    "comet": scene_comet, "asteroids": scene_asteroids, "aurora": scene_aurora, "eclipse": scene_eclipse,
    "rocket": scene_rocket, "supernova": scene_supernova, "nebula": scene_nebula,
    "telescope": scene_telescope, "binary_suns": scene_binary_suns,
}
# Scenes set in space (dark background) that get a nebula and shooting stars
SPACE_SCENES = {"planet", "sun", "black_hole", "pulsar", "galaxy", "orbit", "comet", "asteroids",
                "eclipse", "supernova", "telescope"}


def render_frame(spec: dict, t: float, seed: int, headline: str = "", channel: str = "",
                 footer: str = "") -> np.ndarray:
    """Draw one low-resolution frame of a scene with its text overlay."""
    frame = np.zeros((PH, PW, 3), dtype=np.uint8)
    frame[:] = (4, 4, 16)
    scene = spec.get("scene", "starfield")
    if scene in SPACE_SCENES:
        nebula(frame, seed)
        shooting_star(frame, tq(t), seed)
    SCENES.get(scene, scene_starfield)(frame, tq(t), spec, seed)

    # Darkened band behind the top text and footer for readability
    if channel or headline:
        bottom = 26 + text_mask(headline, 1, LW - 16).shape[0] + 4 if headline else 22
        frame[:px(bottom)] = (frame[:px(bottom)] * 0.35).astype(np.uint8)
    if footer:
        frame[px(LH - 20):] = (frame[px(LH - 20):] * 0.35).astype(np.uint8)
    if channel:
        stamp_text(frame, channel, 8, 1, (255, 255, 255))
        frame[px(18):px(19), px(LW / 2 - 22):px(LW / 2 + 22)] = (255, 210, 60)
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


# Where captions sit: "center" (over the scene) or "top" (in the band under the
# channel name, used when there is no voice-over and no headline)
CAPTION_POSITION = "center"


def render_caption(txt: str, **_) -> ImageClip:
    """Pixel-font caption for SubtitlesClip: yellow with a black outline."""
    frame = np.zeros((PH, PW, 3), dtype=np.uint8)
    mask = text_mask(txt, 2 * DETAIL, (LW - 12) * DETAIL)
    h, w = mask.shape
    x0 = (PW - w) // 2
    y0 = px(34) if CAPTION_POSITION == "top" else (PH - h) // 2 + px(20)
    region = np.zeros((PH, PW), dtype=bool)
    region[y0:y0 + h, x0:x0 + w] = mask
    outline = _outline(region, DETAIL)
    frame[outline] = (0, 0, 0)
    frame[region] = (255, 230, 40)
    alpha = (outline.astype(np.uint8) * 255)[..., None]
    rgba = np.concatenate([frame, alpha], axis=2)
    return ImageClip(upscale(rgba), transparent=True)


# Keyword -> scene, checked in order; the first match wins
_KEYWORD_SCENES = [
    (("supernova", "exploding star", "kilonova"), {"scene": "supernova"}),
    (("nebula", "stellar nursery", "pillars of creation"), {"scene": "nebula"}),
    (("telescope", "webb", "hubble"), {"scene": "telescope"}),
    (("two suns", "binary star", "tatooine"), {"scene": "binary_suns"}),
    (("comet", "halley", "meteor shower"), {"scene": "comet"}),
    (("asteroid", "meteorite", "dinosaur", "tunguska", "apophis"), {"scene": "asteroids"}),
    (("aurora", "northern lights", "solar storm", "solar wind"), {"scene": "aurora"}),
    (("eclipse",), {"scene": "eclipse"}),
    (("rocket", "launch", "gagarin", "laika", "spacewalk"), {"scene": "rocket"}),
    (("pluto",), {"scene": "planet", "preset": "pluto"}),
    (("europa",), {"scene": "planet", "preset": "europa"}),
    (("titan",), {"scene": "planet", "preset": "titan"}),
    (("ganymede",), {"scene": "planet", "preset": "ganymede"}),
    (("triton",), {"scene": "planet", "preset": "triton"}),
    (("ceres",), {"scene": "planet", "preset": "ceres"}),
    (("io",), {"scene": "planet", "preset": "io"}),
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


# Underwater scenes (deep_sea, whale, anglerfish, ...) register themselves here
import pixel_ocean  # noqa: E402,F401
