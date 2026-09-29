"""
Renders the printable NCB Field Reference Card as a high-resolution PNG.

Run directly to (re)generate backend/assets/reference_card.png:
    python -m app.generate_reference_card
"""
import os
from PIL import Image, ImageDraw, ImageFont

from app.card_layout import (
    WHITE_PATCH, GRAY_PATCH, BLACK_PATCH, CHECK_PATCH, ROI_WINDOW,
    CHECK_PATCH_SRGB, frac_rect_to_px,
)

PRINT_WIDTH = 1800
PRINT_HEIGHT = 900
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")


def _font(size, bold=False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def generate(path=None):
    img = Image.new("RGB", (PRINT_WIDTH, PRINT_HEIGHT), "white")
    draw = ImageDraw.Draw(img)

    border = 10
    draw.rectangle(
        [border, border, PRINT_WIDTH - border, PRINT_HEIGHT - border],
        outline=(0, 0, 0), width=border,
    )

    title_font = _font(40, bold=True)
    label_font = _font(24)
    small_font = _font(20)

    draw.text((60, 40), "NCB FIELD REFERENCE CARD", font=title_font, fill=(0, 0, 0))
    draw.text((60, 92), "Calibration patches (left)  ·  Sample window (right)",
              font=small_font, fill=(60, 60, 60))

    def patch(rect_frac, color, label):
        x0, y0, x1, y1 = frac_rect_to_px(rect_frac, PRINT_WIDTH, PRINT_HEIGHT)
        draw.rectangle([x0, y0, x1, y1], fill=color, outline=(0, 0, 0), width=3)
        draw.text((x0, y1 + 8), label, font=label_font, fill=(0, 0, 0))

    patch(WHITE_PATCH, (255, 255, 255), "WHITE")
    patch(GRAY_PATCH, (128, 128, 128), "18% GRAY")
    patch(BLACK_PATCH, (20, 20, 20), "BLACK")
    patch(CHECK_PATCH, CHECK_PATCH_SRGB, "CHECK")

    x0, y0, x1, y1 = frac_rect_to_px(ROI_WINDOW, PRINT_WIDTH, PRINT_HEIGHT)
    draw.rectangle([x0, y0, x1, y1], outline=(0, 0, 0), width=6)
    for dx in (-1, 1):
        for dy in (-1, 1):
            cx = x0 if dx < 0 else x1
            cy = y0 if dy < 0 else y1
            draw.line([cx, cy, cx + dx * 30, cy], fill=(0, 0, 0), width=6)
            draw.line([cx, cy, cx, cy + dy * 30], fill=(0, 0, 0), width=6)
    tw = draw.textlength("PLACE REACTED KIT / STRIP HERE", font=label_font)
    draw.text(((x0 + x1) / 2 - tw / 2, y0 - 36), "PLACE REACTED KIT / STRIP HERE",
               font=label_font, fill=(0, 0, 0))

    draw.text((60, PRINT_HEIGHT - 60), "Keep card flat and fully in frame. Avoid direct glare on patches.",
               font=small_font, fill=(90, 90, 90))

    out_path = path or os.path.join(ASSETS_DIR, "reference_card.png")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    img.save(out_path)
    return out_path


if __name__ == "__main__":
    print(generate())
