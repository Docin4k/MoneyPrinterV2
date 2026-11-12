"""Make YouTube channel art in the same 8-bit style as the Shorts.

Run from the project folder:
    python scripts/make_channel_art.py [--name WonderBytes] [--tagline "..."] [--out channel-art]

Writes:
  profile.png         800x800 profile picture (YouTube shows it as a circle)
  profile-letters.png 800x800 alternative with the channel's initials
  banner.png          2560x1440 banner; the name and tagline stay inside the
                      1546x423 area that YouTube shows on every device
"""
import argparse
import os
import sys

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
import pixel_art as pa  # noqa: E402


def set_canvas(design_w: int, design_h: int) -> None:
    """Point pixel_art's drawing grids at a canvas of a different size."""
    pa.LW, pa.LH = design_w, design_h
    pa.PW, pa.PH = design_w * pa.DETAIL, design_h * pa.DETAIL
    pa.BAYER_FULL = np.tile(pa.BAYER, (pa.PH // 4 + 1, pa.PW // 4 + 1))[:pa.PH, :pa.PW]
    pa.PY, pa.PX = np.mgrid[0:pa.PH, 0:pa.PW]
    pa.YY, pa.XX = (pa.PY + 0.5) / pa.DETAIL, (pa.PX + 0.5) / pa.DETAIL
    pa._NEBULA_CACHE.clear()


def blank():
    frame = np.zeros((pa.PH, pa.PW, 3), dtype=np.uint8)
    frame[:] = (4, 4, 16)
    return frame


def title(frame, text, y, scale, color=(255, 210, 60), shadow=(184, 64, 28)):
    """Pixel-font text with a chunky drop shadow, like the page header."""
    pa.stamp_text(frame, text, y + scale * 0.6, scale, shadow, outline=None, max_width=pa.LW)
    pa.stamp_text(frame, text, y, scale, color, outline=(0, 0, 0), max_width=pa.LW)


def save(frame, path, size):
    Image.fromarray(frame).resize(size, Image.NEAREST).save(path)
    print("wrote", path, f"{size[0]}x{size[1]}")


def profile(out, seed, initials=None):
    set_canvas(200, 200)
    f = blank()
    pa.nebula(f, seed)
    pa.Stars(seed, 120).draw(f, 0.0)
    # Rings reach 2.25 radii, so r=38 keeps them inside YouTube's circle crop
    cx, cy, r = (100, 102, 38) if initials is None else (100, 122, 32)
    pa.halo(f, cx, cy, r, (250, 230, 170))
    pa.draw_moons(f, 1.2, "saturn", cx, cy, r, front=False)
    pa.draw_planet(f, 1.2, "saturn", cx, cy, r, seed=seed, light=(-0.55, -0.45))
    pa.draw_moons(f, 1.2, "saturn", cx, cy, r, front=True)
    if initials:
        title(f, initials, 30, 5)
    save(f, out, (800, 800))


def banner(out, name, tagline, seed):
    set_canvas(640, 360)
    f = blank()
    pa.nebula(f, seed)
    pa.Stars(seed, 600).draw(f, 0.0)
    # Planets outside the always-visible middle strip (x 127-513, y 127-233)
    pa.halo(f, 50, 185, 50, (250, 230, 170))
    pa.draw_planet(f, 0.8, "saturn", 50, 185, 38, seed=seed)
    pa.halo(f, 598, 175, 50, (240, 210, 170))
    pa.draw_moons(f, 0.6, "jupiter", 598, 175, 50, front=False)
    pa.draw_planet(f, 0.6, "jupiter", 598, 175, 50, seed=seed + 1)
    pa.draw_moons(f, 0.6, "jupiter", 598, 175, 50, front=True)
    pa.draw_planet(f, 0.3, "mars", 150, 300, 14, seed=seed + 2)
    pa.draw_planet(f, 0.3, "neptune", 505, 60, 12, seed=seed + 3)
    pa.draw_planet(f, 0.3, "earth", 470, 320, 10, seed=seed + 4)
    pa.shooting_star(f, 0.2, seed)
    # Name and tagline inside the safe area
    title(f, name.upper(), 144, 5)
    pa.stamp_text(f, tagline.upper(), 192, 2, (232, 230, 255), outline=(0, 0, 0), max_width=360)
    save(f, out, (2560, 1440))


def main():
    ap = argparse.ArgumentParser(description="Make 8-bit YouTube channel art.")
    ap.add_argument("--name", default="WonderBytes")
    ap.add_argument("--tagline", default="Space facts that sound fake but are true")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", default=os.path.join(ROOT, "channel-art"))
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    initials = "".join(c for c in args.name if c.isupper())[:2] or args.name[:2].upper()
    profile(os.path.join(args.out, "profile.png"), args.seed)
    profile(os.path.join(args.out, "profile-letters.png"), args.seed, initials=initials)
    banner(os.path.join(args.out, "banner.png"), args.name, args.tagline, args.seed)


if __name__ == "__main__":
    main()
