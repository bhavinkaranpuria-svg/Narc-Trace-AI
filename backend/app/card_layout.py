"""
Shared geometry for the physical NCB Field Reference Card.

The card is a single rigid printed card the officer places in-frame next to
(or under) the reacted test kit. It carries four calibration patches
(white / 18%-gray / black / a known "check" colour) on the left half, used to
correct the photograph for ambient lighting and camera colour response, and a
cut-out "sample window" on the right half where the reacted test strip or
vial is positioned so its colour is read from the SAME photograph, under the
SAME calibration.

All patch positions are stored as fractions (0..1) of the *warped* card's
width/height so the generator (which renders a print-resolution PNG) and the
vision pipeline (which warps a photographed card to a small fixed canvas)
always agree on where each patch is, regardless of resolution.

Rects are (x0, y0, x1, y1).
"""

WARP_WIDTH = 900
WARP_HEIGHT = 450

WHITE_PATCH = (0.07, 0.18, 0.24, 0.50)
GRAY_PATCH = (0.27, 0.18, 0.44, 0.50)
BLACK_PATCH = (0.07, 0.56, 0.24, 0.88)
CHECK_PATCH = (0.27, 0.56, 0.44, 0.88)
ROI_WINDOW = (0.54, 0.14, 0.94, 0.80)

# Reference sRGB colour baked into the printed "check" patch — used to sanity
# check that calibration actually worked (a big residual error here means the
# correction itself can't be trusted, independent of the test result).
CHECK_PATCH_SRGB = (70, 110, 160)


def frac_rect_to_px(rect, width=WARP_WIDTH, height=WARP_HEIGHT):
    x0, y0, x1, y1 = rect
    return (int(x0 * width), int(y0 * height), int(x1 * width), int(y1 * height))
