"""Make YouTube channel art in the same 8-bit style as the Shorts.

Run from the project folder:
    python scripts/make_channel_art.py [--name WonderBytes] [--tagline "..."] [--out channel-art]
    python scripts/make_channel_art.py --theme ocean --name "Pixel Abyss" --tagline "..."

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
import pixel_ocean as po  # noqa: E402


def set_canvas(design_w: int, design_h: int) -> None:
    """Point pixel_art's drawing grids at a canvas of a different size."""
    pa.LW, pa.LH = design_w, design_h
    pa.PW, pa.PH = design_w * pa.DETAIL, design_h * pa.DETAIL
    pa.BAYER_FULL = np.tile(pa.BAYER, (pa.PH // 4 + 1, pa.PW // 4 + 1))[:pa.PH, :pa.PW]
    pa.PY, pa.PX = np.mgrid[0:pa.PH, 0:pa.PW]
    pa.YY, pa.XX = (pa.PY + 0.5) / pa.DETAIL, (pa.PX + 0.5) / pa.DETAIL
    pa._NEBULA_CACHE.clear()
    for name in ("LW", "LH", "PW", "PH", "PY", "PX", "YY", "XX"):
        setattr(po, name, getattr(pa, name))


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


def ocean_profile(out, seed, initials=None):
    """The glowing anglerfish, cropped to a square around the fish and its lure."""
    set_canvas(180, 320)
    f = pa.render_frame({"scene": "anglerfish"}, 1.0, seed)
    x0, y0, size = 18, 108, 160
    crop = f[pa.px(y0):pa.px(y0 + size), pa.px(x0):pa.px(x0 + size)]
    if initials:
        crop = crop.copy()
        set_canvas(size, size)
        title(crop, initials, 12, 5, color=(120, 255, 240), shadow=(20, 90, 110))
    save(crop, out, (800, 800))


def ocean_banner(out, name, tagline, seed):
    set_canvas(640, 360)
    f = blank()
    po.water(f, po.SUNLIT, 0.0, 1.0)
    po.light_rays(f, 1.0, seed, strength=0.45, count=16)
    po.marine_snow(f, 1.0, seed, 300, (130, 180, 210))
    po.seafloor(f, 330, seed, [(120, 110, 80), (200, 185, 140), (240, 225, 180)], rough=3)
    import random
    rng = random.Random(seed)
    for bx, col in ((20, (240, 110, 120)), (70, (250, 170, 60)), (560, (150, 90, 210)), (610, (240, 120, 160)),
                    (110, (120, 230, 200)), (530, (250, 200, 80))):
        po._coral_branch(f, bx, 330, -1.57 + rng.uniform(-0.2, 0.2), 18, 3, col, rng)
    # A whale on the left, jellyfish on the right, outside the middle strip
    po.swimmer(f, 120, 120, 160, lambda u: po._whale_top(u) * 1.2, lambda u: po._whale_bottom(u) * 1.2,
               [(30, 50, 80), (55, 85, 120), (80, 115, 150)], 1, bend=4,
               belly_ramp=[(110, 140, 165), (150, 175, 190), (185, 205, 210)])
    pa.put(f, 120 - 0.17 * 160, 124, (10, 15, 25), 3)
    for jx, jy, r, ramp in ((560, 90, 18, [(70, 20, 80), (200, 80, 200), (255, 190, 250)]),
                            (605, 160, 12, [(20, 60, 90), (60, 190, 230), (200, 250, 255)]),
                            (530, 200, 9, [(90, 40, 20), (240, 140, 70), (255, 220, 170)])):
        for k in range(6):
            for i in range(int(r * 3)):
                if (i + k) % 2 == 0:
                    pa.put(f, jx - r * 0.8 + k * r * 0.32 + (i * 0.15 if k % 2 else -i * 0.1), jy + 1 + i, ramp[1])
        s = (pa.XX - jx) ** 2 / r ** 2 + (pa.YY - jy) ** 2 / (r * 0.8) ** 2
        bell = (s <= 1) & (pa.YY <= jy + 1)
        f[bell] = pa.dither_ramp(0.3 + 0.7 * s[bell], ramp, pa.PY[bell], pa.PX[bell])
    for i in range(18):
        po.small_fish(f, rng.uniform(130, 510), rng.choice([rng.uniform(40, 115), rng.uniform(245, 310)]),
                      rng.uniform(2.5, 5), rng.choice([-1, 1]), rng.choice([(250, 230, 60), (60, 160, 250),
                                                                              (250, 120, 160), (250, 140, 40)]), 0, i)
    # Darken the middle strip a touch so the name stands out
    band = (pa.YY > 132) & (pa.YY < 228) & (pa.XX > 120) & (pa.XX < 520)
    f[band] = (f[band] * 0.6).astype(np.uint8)
    title(f, name.upper(), 144, 5, color=(120, 255, 240), shadow=(20, 90, 110))
    pa.stamp_text(f, tagline.upper(), 192, 2, (232, 245, 255), outline=(0, 0, 0), max_width=360)
    save(f, out, (2560, 1440))


def main():
    ap = argparse.ArgumentParser(description="Make 8-bit YouTube channel art.")
    ap.add_argument("--name", default="WonderBytes")
    ap.add_argument("--tagline", default="Space facts that sound fake but are true")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--theme", choices=["space", "ocean"], default="space")
    ap.add_argument("--out", default=os.path.join(ROOT, "channel-art"))
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    initials = "".join(c for c in args.name if c.isupper())[:2] or args.name[:2].upper()
    make_profile, make_banner = (ocean_profile, ocean_banner) if args.theme == "ocean" else (profile, banner)
    make_profile(os.path.join(args.out, "profile.png"), args.seed)
    make_profile(os.path.join(args.out, "profile-letters.png"), args.seed, initials=initials)
    make_banner(os.path.join(args.out, "banner.png"), args.name, args.tagline, args.seed)


if __name__ == "__main__":
    main()
