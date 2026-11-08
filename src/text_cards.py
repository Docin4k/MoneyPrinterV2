"""Locally rendered visuals for YouTube Shorts.

- Text cards: 1080x1920 images with a space-style gradient, a starfield, the
  channel name, a headline and a footer label. Used instead of AI images when
  `image_provider` is "text_cards" (no API key needed).
- Captions: subtitle text drawn with Pillow, matching the look of the original
  MoviePy TextClip captions (yellow, black outline). Used when
  `caption_renderer` is "pillow", so ImageMagick is not required.
"""
import os
import random
import textwrap

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from moviepy.editor import ImageClip

from config import get_font, get_fonts_dir

WIDTH, HEIGHT = 1080, 1920

# (top, bottom) gradient colours; consecutive cards use different pairs
PALETTES = [
    ((10, 12, 48), (88, 24, 120)),
    ((4, 30, 60), (12, 110, 140)),
    ((30, 8, 40), (160, 40, 90)),
    ((6, 20, 30), (30, 90, 70)),
    ((20, 10, 60), (40, 70, 170)),
    ((40, 16, 8), (150, 70, 20)),
]


def _font_path() -> str:
    return os.path.join(get_fonts_dir(), get_font())


def _fit_lines(draw, text: str, size: int, max_width: int, max_lines: int):
    """Shrink the font until the wrapped text fits max_width and max_lines."""
    path = _font_path()
    while size > 30:
        font = ImageFont.truetype(path, size)
        avg = draw.textlength("abcdefghijklmnopqrstuvwxyz", font=font) / 26
        lines = textwrap.wrap(text, width=max(8, int(max_width / avg)))
        if len(lines) <= max_lines and all(
            draw.textlength(line, font=font) <= max_width for line in lines
        ):
            return font, lines
        size -= 6
    return ImageFont.truetype(path, 30), textwrap.wrap(text, width=40)[:max_lines]


def render_card(
    output_path: str,
    index: int,
    total: int,
    headline: str,
    channel: str,
    label: str | None = None,
) -> str:
    """Draw one text card and save it as a PNG.

    Args:
        output_path (str): Where to save the PNG.
        index (int): Zero-based card number (chooses colours and layout seed).
        total (int): Number of fact cards, for the "FACT n / total" footer.
        headline (str): Main text, usually one sentence of the script.
        channel (str): Channel name shown at the top.
        label (str | None): Footer text; defaults to "FACT n / total".

    Returns:
        path (str): output_path
    """
    top, bottom = PALETTES[index % len(PALETTES)]
    t = np.linspace(0, 1, HEIGHT)[:, None, None]
    gradient = (np.array(top) * (1 - t) + np.array(bottom) * t).repeat(WIDTH, axis=1)
    image = Image.fromarray(gradient.astype("uint8"), "RGB")

    rng = random.Random(index)
    glow = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
    cx, cy = rng.randint(200, 880), rng.randint(500, 1400)
    ImageDraw.Draw(glow).ellipse(
        [cx - 380, cy - 380, cx + 380, cy + 380],
        fill=tuple(min(255, c + 60) for c in bottom),
    )
    image = Image.blend(image, glow.filter(ImageFilter.GaussianBlur(160)), 0.35)

    draw = ImageDraw.Draw(image)
    for _ in range(260):
        x, y = rng.randint(0, WIDTH), rng.randint(0, HEIGHT)
        r = rng.choice([1, 1, 1, 2, 2, 3])
        b = rng.randint(150, 255)
        draw.ellipse([x - r, y - r, x + r, y + r], fill=(b, b, b))

    small = ImageFont.truetype(_font_path(), 46)
    draw.text((WIDTH / 2, 150), channel.upper(), font=small, fill=(255, 255, 255), anchor="mm")
    draw.line([(WIDTH / 2 - 120, 195), (WIDTH / 2 + 120, 195)], fill=(255, 215, 0), width=5)

    # Headline sits in the upper third; captions are drawn in the centre
    font, lines = _fit_lines(draw, headline.upper(), 84, WIDTH - 160, 4)
    y = 300
    for line in lines:
        draw.text((WIDTH / 2, y), line, font=font, fill=(255, 255, 255), anchor="ma",
                  stroke_width=4, stroke_fill=(0, 0, 0))
        y += font.size + 18

    draw.text((WIDTH / 2, HEIGHT - 150), label or f"FACT {index + 1} / {total}", font=small,
              fill=(255, 215, 0), anchor="mm", stroke_width=3, stroke_fill=(0, 0, 0))

    image.save(output_path)
    return output_path


def render_caption(txt: str, **_) -> ImageClip:
    """Caption clip for SubtitlesClip: yellow text with a black outline, centred.

    Accepts and ignores the keyword arguments the TextClip generator passes.
    """
    canvas = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    font, lines = _fit_lines(draw, txt, 100, WIDTH - 120, 6)
    line_height = font.size + 20
    y = HEIGHT / 2 - line_height * len(lines) / 2
    for line in lines:
        draw.text((WIDTH / 2, y), line, font=font, fill="#FFFF00", anchor="ma",
                  stroke_width=5, stroke_fill="black")
        y += line_height
    return ImageClip(np.array(canvas), transparent=True)
