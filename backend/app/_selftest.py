"""Not part of the API — a one-off script to sanity-check the vision pipeline
by synthesizing a photographed card (with perspective skew + a painted-in
reaction colour) and running it through the real pipeline end to end."""
import cv2
import numpy as np
from app import vision
from app.kits import KIT_PROFILES
from app.card_layout import ROI_WINDOW, frac_rect_to_px, WARP_WIDTH, WARP_HEIGHT


def lab_to_bgr(lab):
    L, a, b = lab
    px = np.uint8([[[np.clip(L * 255 / 100, 0, 255), np.clip(a + 128, 0, 255), np.clip(b + 128, 0, 255)]]])
    bgr = cv2.cvtColor(px, cv2.COLOR_LAB2BGR)[0][0]
    return tuple(int(v) for v in bgr)


def synthesize(kit_id: str, which: str, skew=True, dim=False, blur=False):
    card = cv2.imread("assets/reference_card.png")
    ch, cw = card.shape[:2]
    kit = KIT_PROFILES[kit_id]
    lab = kit.positive_lab if which == "positive" else kit.negative_lab
    bgr = lab_to_bgr(lab)
    x0, y0, x1, y1 = frac_rect_to_px(ROI_WINDOW, cw, ch)
    pad = 20
    cv2.rectangle(card, (x0 + pad, y0 + pad), (x1 - pad, y1 - pad), bgr, -1)

    canvas = np.full((ch + 400, cw + 400, 3), 210, dtype=np.uint8)
    ox, oy = 200, 200
    canvas[oy:oy + ch, ox:ox + cw] = card
    true_corners = [[ox, oy], [ox + cw, oy], [ox + cw, oy + ch], [ox, oy + ch]]

    if skew:
        src = np.array(true_corners, dtype=np.float32)
        jitter = np.array([[15, -10], [-20, 25], [10, -15], [-5, 20]], dtype=np.float32)
        dst = src + jitter
        M = cv2.getPerspectiveTransform(src, dst)
        canvas = cv2.warpPerspective(canvas, M, (canvas.shape[1], canvas.shape[0]),
                                      borderValue=(210, 210, 210))

    if dim:
        canvas = (canvas.astype(np.float32) * 0.35).astype(np.uint8)
    if blur:
        canvas = cv2.GaussianBlur(canvas, (25, 25), 0)

    ok, buf = cv2.imencode(".jpg", canvas)
    return buf.tobytes()


def main():
    for kit_id in KIT_PROFILES:
        for which in ("positive", "negative"):
            raw = synthesize(kit_id, which)
            img = vision.decode_image(raw)
            result = vision.run_pipeline(img, KIT_PROFILES[kit_id])
            status = "OK " if (result.classification and result.classification.label == which) else "FAIL"
            print(f"[{status}] kit={kit_id:14s} expected={which:8s} "
                  f"card_conf={result.card.confidence:.2f} "
                  f"quality={result.quality.quality_score} "
                  f"-> got={result.classification.label if result.classification else None} "
                  f"conf={result.classification.confidence if result.classification else None}")

    print("\n-- degraded conditions (dark + blurred) should refuse to call it --")
    raw = synthesize("std-narcotic", "positive", dim=True, blur=True)
    img = vision.decode_image(raw)
    result = vision.run_pipeline(img, KIT_PROFILES["std-narcotic"])
    print("quality:", result.quality.quality_score, result.quality.verdict, result.quality.issues)
    print("classification:", result.classification.label if result.classification else None)


if __name__ == "__main__":
    main()
