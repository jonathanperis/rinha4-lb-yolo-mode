#!/usr/bin/env python3
"""Generate social preview and raster icon assets for the Pages site."""

from __future__ import annotations

import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "docs" / "public"

BG = (16, 20, 24)
BG2 = (9, 12, 17)
PANEL = (31, 39, 46)
LINE = (75, 91, 102)
TEXT = (234, 230, 217)
MUTED = (171, 184, 194)
SUBTLE = (128, 143, 154)
CYAN = (96, 211, 238)
VIOLET = (181, 118, 240)
COPPER = (231, 169, 83)
GREEN = (96, 221, 154)
MARK_BG = (15, 16, 17)
MARK_BAR = (85, 85, 85)
MARK_DOT = (196, 196, 196)

FONT = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
FONT_BOLD = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
FONT_MONO = Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf")
FONT_MONO_BOLD = Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf")


def font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size=size)


def rounded(draw: ImageDraw.ImageDraw, xy: tuple[int, int, int, int], radius: int, fill, outline=None, width: int = 1) -> None:
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def draw_gradient_bg(img: Image.Image) -> None:
    px = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            t = (x * 0.35 + y * 0.65) / (w * 0.35 + h * 0.65)
            r = int(BG[0] * (1 - t) + BG2[0] * t)
            g = int(BG[1] * (1 - t) + BG2[1] * t)
            b = int(BG[2] * (1 - t) + BG2[2] * t)
            # radial violet/cyan glows
            d1 = math.hypot((x - 105) / 620, (y - 60) / 400)
            d2 = math.hypot((x - 1020) / 550, (y - 90) / 360)
            v = max(0.0, 1.0 - d1) * 0.17
            c = max(0.0, 1.0 - d2) * 0.13
            r = min(255, int(r + VIOLET[0] * v + CYAN[0] * c))
            g = min(255, int(g + VIOLET[1] * v + CYAN[1] * c))
            b = min(255, int(b + VIOLET[2] * v + CYAN[2] * c))
            px[x, y] = (r, g, b)


def draw_grid(draw: ImageDraw.ImageDraw, w: int, h: int) -> None:
    for x in range(0, w, 48):
        draw.line((x, 0, x, h), fill=(237, 237, 220, 12), width=1)
    for y in range(0, h, 48):
        draw.line((0, y, w, y), fill=(237, 237, 220, 14), width=1)


def draw_mark(draw: ImageDraw.ImageDraw, x: int, y: int, size: int, shadow: bool = True) -> None:
    if shadow:
        draw.rounded_rectangle((x + 12, y + 14, x + size + 12, y + size + 14), radius=int(size * 0.22), fill=(0, 0, 0, 68))
    rounded(draw, (x, y, x + size, y + size), int(size * 0.22), MARK_BG, outline=(86, 94, 104), width=max(1, size // 36))
    scale = size / 64
    def pts(seq):
        return [(x + int(px * scale), y + int(py * scale)) for px, py in seq]
    # Approximate title-mark slash paths as polygons so the raster/preview match the SVG favicon.
    draw.polygon(pts([(12, 42), (25, 16), (32, 16), (19, 42)]), fill=MARK_BAR)
    draw.polygon(pts([(32, 42), (45, 16), (52, 16), (39, 42)]), fill=MARK_BAR)
    draw.ellipse((x + int(43 * scale), y + int(39 * scale), x + int(53 * scale), y + int(49 * scale)), fill=MARK_DOT)


def draw_social_preview() -> None:
    w, h = 1200, 630
    img = Image.new("RGB", (w, h), BG)
    draw_gradient_bg(img)
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    draw_grid(od, w, h)

    # bottom fade
    for yy in range(h - 220, h):
        alpha = int(175 * ((yy - (h - 220)) / 220))
        od.line((0, yy, w, yy), fill=(5, 8, 12, alpha), width=1)

    draw_mark(od, 78, 70, 92)
    od.text((190, 85), "rinha4-lb-yolo-mode", font=font(FONT_MONO_BOLD, 34), fill=TEXT)
    od.text((192, 132), "ASM default · C baseline · fdpass/proxy", font=font(FONT_MONO, 20), fill=MUTED)

    # huge hero headline
    od.text((78, 210), "YOLO", font=font(FONT_BOLD, 112), fill=TEXT)
    od.text((78, 316), "LOAD BALANCER", font=font(FONT_BOLD, 70), fill=TEXT)
    od.text((82, 402), "Promoted x86-64 ASM path for Rinha4 runs.", font=font(FONT, 29), fill=MUTED)

    # right topology card
    rounded(od, (760, 160, 1118, 500), 34, (30, 38, 45, 218), outline=(91, 109, 122, 150), width=2)
    od.text((800, 198), "transport/lb", font=font(FONT_MONO_BOLD, 22), fill=CYAN)
    lines = [
        ("latest", "ASM default", GREEN),
        ("asm-ci-<sha>", "pinned lane", CYAN),
        ("c-ci-<sha>", "baseline", COPPER),
        ("LB_MODE", "proxy · fdpass", VIOLET),
    ]
    y = 248
    for label, value, color in lines:
        rounded(od, (796, y - 5, 1096, y + 44), 15, (18, 23, 28, 180), outline=(72, 88, 100, 120), width=1)
        od.text((818, y + 7), label, font=font(FONT_MONO_BOLD, 18), fill=color)
        od.text((968, y + 7), value, font=font(FONT_MONO, 16), fill=MUTED)
        y += 61

    # accent rails
    od.line((78, 552, 1118, 552), fill=(96, 211, 238, 120), width=2)
    for x, color in [(78, CYAN), (384, VIOLET), (690, COPPER), (996, GREEN)]:
        od.ellipse((x - 6, 546, x + 6, 558), fill=color + (255,))
    od.text((78, 575), "GitHub Pages · benchmark reports · immutable GHCR images", font=font(FONT_MONO, 20), fill=SUBTLE)

    img = Image.alpha_composite(img.convert("RGBA"), overlay)
    out = PUBLIC / "social-preview.png"
    img.convert("RGB").save(out, optimize=True)
    print(out)


def draw_icons() -> None:
    # Fallback PNG/Apple icons use the exact same title-mark motif.
    for name, size in [("favicon.png", 256), ("favicon-32x32.png", 32), ("apple-touch-icon.png", 180)]:
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        draw_mark(d, 0, 0, size, shadow=False)
        img.save(PUBLIC / name)
        print(PUBLIC / name)

    ico = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    draw_mark(ImageDraw.Draw(ico), 0, 0, 256, shadow=False)
    ico.save(PUBLIC / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print(PUBLIC / "favicon.ico")


def main() -> None:
    PUBLIC.mkdir(parents=True, exist_ok=True)
    draw_social_preview()
    draw_icons()


if __name__ == "__main__":
    main()
