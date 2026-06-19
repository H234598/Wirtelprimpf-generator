#!/usr/bin/env python3
"""Generate deterministic Wirtelprimpf applet image assets."""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = ROOT / "files" / "wirtelprimfgenerator@H234598" / "assets"


def lerp(a: int, b: int, t: float) -> int:
    return round(a + (b - a) * t)


def gradient(size: tuple[int, int], left: tuple[int, int, int], right: tuple[int, int, int]) -> Image.Image:
    width, height = size
    image = Image.new("RGBA", size)
    pixels = image.load()
    for x in range(width):
        t = x / max(1, width - 1)
        color = tuple(lerp(left[i], right[i], t) for i in range(3)) + (255,)
        for y in range(height):
            pixels[x, y] = color
    return image


def rounded_mask(size: tuple[int, int], radius: int) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius=radius, fill=255)
    return mask


def add_stars(draw: ImageDraw.ImageDraw, points: list[tuple[int, int, int]], color: tuple[int, int, int, int]) -> None:
    for x, y, radius in points:
        draw.line((x - radius, y, x + radius, y), fill=color, width=max(1, radius // 2))
        draw.line((x, y - radius, x, y + radius), fill=color, width=max(1, radius // 2))


def save_panel_icon(name: str, bg_left: tuple[int, int, int], bg_right: tuple[int, int, int], accent: tuple[int, int, int]) -> None:
    scale = 4
    size = 128
    image = gradient((size * scale, size * scale), bg_left, bg_right)
    mask = rounded_mask(image.size, 26 * scale)
    image.putalpha(mask)
    draw = ImageDraw.Draw(image)

    pad = 5 * scale
    draw.rounded_rectangle(
        (pad, pad, image.width - pad, image.height - pad),
        radius=24 * scale,
        outline=accent + (255,),
        width=3 * scale,
    )
    center = (64 * scale, 67 * scale)
    cat_radius = 34 * scale
    draw.ellipse(
        (
            center[0] - cat_radius,
            center[1] - cat_radius,
            center[0] + cat_radius,
            center[1] + cat_radius,
        ),
        fill=(255, 248, 225, 255),
    )
    draw.polygon(
        [
            (42 * scale, 40 * scale),
            (50 * scale, 17 * scale),
            (62 * scale, 42 * scale),
        ],
        fill=(255, 248, 225, 255),
    )
    draw.polygon(
        [
            (76 * scale, 42 * scale),
            (91 * scale, 19 * scale),
            (94 * scale, 48 * scale),
        ],
        fill=(255, 248, 225, 255),
    )
    draw.arc((28 * scale, 27 * scale, 102 * scale, 101 * scale), 130, 355, fill=accent + (255,), width=4 * scale)
    draw.arc((20 * scale, 35 * scale, 97 * scale, 111 * scale), 190, 34, fill=(86, 210, 220, 255), width=3 * scale)
    draw.line((52 * scale, 66 * scale, 24 * scale, 58 * scale), fill=(34, 28, 41, 255), width=2 * scale)
    draw.line((75 * scale, 66 * scale, 103 * scale, 58 * scale), fill=(34, 28, 41, 255), width=2 * scale)
    draw.ellipse((52 * scale, 58 * scale, 59 * scale, 69 * scale), fill=(34, 28, 41, 255))
    draw.ellipse((72 * scale, 58 * scale, 79 * scale, 69 * scale), fill=(34, 28, 41, 255))
    draw.polygon([(65 * scale, 72 * scale), (58 * scale, 80 * scale), (72 * scale, 80 * scale)], fill=(223, 94, 112, 255))
    draw.arc((78 * scale, 74 * scale, 119 * scale, 123 * scale), 205, 331, fill=(255, 248, 225, 255), width=8 * scale)
    add_stars(
        draw,
        [(31 * scale, 54 * scale, 4 * scale), (105 * scale, 39 * scale, 4 * scale), (96 * scale, 90 * scale, 3 * scale)],
        accent + (255,),
    )

    image = image.resize((size, size), Image.Resampling.LANCZOS)
    image.save(ASSET_DIR / name, "PNG")


def banner_base(left: tuple[int, int, int], right: tuple[int, int, int]) -> Image.Image:
    scale = 2
    size = (1200 * scale, 260 * scale)
    image = gradient(size, left, right)
    draw = ImageDraw.Draw(image, "RGBA")
    for offset in range(-size[1], size[0], 68 * scale):
        draw.line((offset, size[1], offset + size[1], 0), fill=(255, 255, 255, 24), width=2 * scale)
    draw.rounded_rectangle((2 * scale, 2 * scale, size[0] - 3 * scale, size[1] - 3 * scale), radius=36 * scale, outline=(255, 210, 94, 150), width=2 * scale)
    return image


def save_generator_atelier() -> None:
    scale = 2
    image = banner_base((34, 29, 82), (38, 125, 150))
    draw = ImageDraw.Draw(image, "RGBA")
    draw.rounded_rectangle((78 * scale, 58 * scale, 430 * scale, 205 * scale), radius=18 * scale, fill=(18, 18, 32, 230), outline=(255, 210, 94, 190), width=2 * scale)
    for i, color in enumerate(((255, 107, 107), (80, 212, 198), (255, 210, 94))):
        y = (86 + i * 38) * scale
        draw.rounded_rectangle((116 * scale, y, 322 * scale, y + 12 * scale), radius=6 * scale, fill=color + (230,))
        draw.ellipse((350 * scale, y - 8 * scale, 384 * scale, y + 26 * scale), fill=color + (230,))
    draw.polygon([(760 * scale, 210 * scale), (900 * scale, 70 * scale), (1045 * scale, 210 * scale)], fill=(255, 245, 218, 235))
    draw.arc((690 * scale, 45 * scale, 1100 * scale, 245 * scale), 205, 340, fill=(255, 210, 94, 210), width=7 * scale)
    add_stars(draw, [(690 * scale, 82 * scale, 10 * scale), (1030 * scale, 68 * scale, 9 * scale), (980 * scale, 178 * scale, 6 * scale)], (255, 210, 94, 230))
    image = image.filter(ImageFilter.UnsharpMask(radius=1.0, percent=110, threshold=3))
    image.resize((1200, 260), Image.Resampling.LANCZOS).save(ASSET_DIR / "settings-generator-atelier.png", "PNG")


def save_generator_machine() -> None:
    scale = 2
    image = banner_base((25, 40, 72), (115, 66, 107))
    draw = ImageDraw.Draw(image, "RGBA")
    for i in range(5):
        x = (120 + i * 116) * scale
        draw.rounded_rectangle((x, 74 * scale, x + 82 * scale, 172 * scale), radius=16 * scale, fill=(255, 248, 225, 220), outline=(80, 212, 198, 220), width=2 * scale)
        draw.line((x + 18 * scale, 118 * scale, x + 64 * scale, 118 * scale), fill=(34, 29, 82, 210), width=4 * scale)
    for angle in range(0, 360, 45):
        cx, cy = 870 * scale, 130 * scale
        r1, r2 = 32 * scale, 84 * scale
        a = math.radians(angle)
        draw.line((cx + math.cos(a) * r1, cy + math.sin(a) * r1, cx + math.cos(a) * r2, cy + math.sin(a) * r2), fill=(255, 210, 94, 210), width=5 * scale)
    draw.ellipse((800 * scale, 60 * scale, 940 * scale, 200 * scale), outline=(255, 210, 94, 230), width=8 * scale)
    draw.ellipse((838 * scale, 98 * scale, 902 * scale, 162 * scale), fill=(80, 212, 198, 230))
    add_stars(
        draw,
        [(1015 * scale, 64 * scale, 8 * scale), (1062 * scale, 145 * scale, 6 * scale), (745 * scale, 180 * scale, 5 * scale)],
        (255, 248, 225, 220),
    )
    image.resize((1200, 260), Image.Resampling.LANCZOS).save(ASSET_DIR / "settings-generator-machine.png", "PNG")


def save_about_story() -> None:
    scale = 2
    image = banner_base((46, 34, 82), (151, 91, 63))
    draw = ImageDraw.Draw(image, "RGBA")
    draw.rounded_rectangle((95 * scale, 58 * scale, 365 * scale, 205 * scale), radius=20 * scale, fill=(255, 248, 225, 235))
    for x in (140, 180, 220, 260, 300):
        draw.line((x * scale, 84 * scale, x * scale, 180 * scale), fill=(34, 29, 82, 55), width=2 * scale)
    draw.arc((650 * scale, 38 * scale, 1060 * scale, 235 * scale), 188, 352, fill=(80, 212, 198, 215), width=7 * scale)
    draw.polygon([(805 * scale, 55 * scale), (870 * scale, 118 * scale), (785 * scale, 204 * scale), (720 * scale, 130 * scale)], fill=(255, 210, 94, 225))
    draw.polygon([(900 * scale, 88 * scale), (968 * scale, 132 * scale), (912 * scale, 205 * scale), (846 * scale, 154 * scale)], fill=(255, 248, 225, 210))
    add_stars(draw, [(555 * scale, 70 * scale, 8 * scale), (1080 * scale, 92 * scale, 8 * scale), (610 * scale, 176 * scale, 6 * scale)], (255, 210, 94, 230))
    image.resize((1200, 260), Image.Resampling.LANCZOS).save(ASSET_DIR / "settings-about-story.png", "PNG")


def save_about_book() -> None:
    scale = 2
    image = banner_base((26, 54, 77), (103, 78, 132))
    draw = ImageDraw.Draw(image, "RGBA")
    draw.rounded_rectangle((115 * scale, 70 * scale, 520 * scale, 200 * scale), radius=18 * scale, fill=(255, 248, 225, 230), outline=(255, 210, 94, 190), width=2 * scale)
    draw.line((318 * scale, 78 * scale, 318 * scale, 192 * scale), fill=(34, 29, 82, 90), width=3 * scale)
    for y in (98, 126, 154):
        draw.rounded_rectangle((150 * scale, y * scale, 286 * scale, (y + 8) * scale), radius=4 * scale, fill=(34, 29, 82, 120))
        draw.rounded_rectangle((350 * scale, y * scale, 486 * scale, (y + 8) * scale), radius=4 * scale, fill=(34, 29, 82, 120))
    draw.ellipse((770 * scale, 65 * scale, 975 * scale, 205 * scale), outline=(80, 212, 198, 220), width=7 * scale)
    draw.arc((720 * scale, 35 * scale, 1040 * scale, 235 * scale), 205, 335, fill=(255, 210, 94, 220), width=7 * scale)
    add_stars(draw, [(725 * scale, 82 * scale, 9 * scale), (1045 * scale, 92 * scale, 10 * scale), (1005 * scale, 184 * scale, 6 * scale)], (255, 248, 225, 230))
    image.resize((1200, 260), Image.Resampling.LANCZOS).save(ASSET_DIR / "settings-about-book.png", "PNG")


def main() -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    save_panel_icon("panel-icon.png", (34, 29, 82), (22, 24, 42), (255, 210, 94))
    save_panel_icon("panel-icon-moon.png", (20, 50, 82), (84, 59, 118), (80, 212, 198))
    save_panel_icon("panel-icon-spark.png", (50, 34, 85), (132, 70, 62), (255, 139, 92))
    panel64 = Image.open(ASSET_DIR / "panel-icon.png").resize((64, 64), Image.Resampling.LANCZOS)
    panel64.save(ASSET_DIR / "panel-icon-64.png", "PNG")
    save_generator_atelier()
    save_generator_machine()
    save_about_story()
    save_about_book()


if __name__ == "__main__":
    main()
