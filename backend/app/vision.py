"""
Classical computer-vision pipeline for NARC-TRACE AI.

Deliberately NOT a deep-learning black box (see design notes #6): every step
here is an inspectable, explainable image-processing operation. That is what
lets /api/analyze return a step-by-step "why" breakdown instead of a bare
label.

Pipeline:
    decode -> quality checks (blur / glare / brightness)
           -> reference-card detection (contour + quad approximation)
           -> perspective correction (warp to a fixed canvas)
           -> calibration patch sampling (white / gray / black / check)
           -> linear colour correction (per-channel white balance + gain)
           -> sample-window (ROI) colour extraction, corrected
           -> BGR -> Lab conversion
           -> Delta-E distance to kit's positive/negative reference points
           -> classification + confidence + explainability trace
"""
import math
from dataclasses import dataclass, asdict
from typing import Optional, List, Tuple

import cv2
import numpy as np

from app.card_layout import (
    WHITE_PATCH, GRAY_PATCH, BLACK_PATCH, CHECK_PATCH, ROI_WINDOW,
    CHECK_PATCH_SRGB, WARP_WIDTH, WARP_HEIGHT, frac_rect_to_px,
)
from app.kits import KitProfile

MODEL_VERSION = "cv-pipeline-1.0"

BLUR_OK_THRESHOLD = 90.0        # Laplacian variance below this ~= blurred
GLARE_PIXEL_VALUE = 248         # 0-255 grayscale value considered "blown out"
GLARE_OK_FRACTION = 0.02        # more than 2% blown-out pixels in ROI is a problem
DARK_MEAN_THRESHOLD = 55.0      # mean brightness below this is "too dark"
BRIGHT_MEAN_THRESHOLD = 235.0   # mean brightness above this is "too bright / washed out"


def decode_image(raw_bytes: bytes) -> np.ndarray:
    arr = np.frombuffer(raw_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image — unsupported or corrupt file.")
    # Cap resolution for consistent, fast processing.
    h, w = img.shape[:2]
    max_dim = 1600
    if max(h, w) > max_dim:
        scale = max_dim / max(h, w)
        img = cv2.resize(img, (int(w * scale), int(h * scale)))
    return img


# ---------------------------------------------------------------- quality --

@dataclass
class QualityReport:
    blur_score: float
    blur_ok: bool
    glare_fraction: float
    glare_ok: bool
    mean_brightness: float
    brightness_ok: bool
    quality_score: int
    verdict: str
    issues: List[str]


def assess_quality(img: np.ndarray) -> QualityReport:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    blur_ok = blur_score >= BLUR_OK_THRESHOLD

    glare_fraction = float(np.mean(gray >= GLARE_PIXEL_VALUE))
    glare_ok = glare_fraction <= GLARE_OK_FRACTION

    mean_brightness = float(gray.mean())
    brightness_ok = DARK_MEAN_THRESHOLD <= mean_brightness <= BRIGHT_MEAN_THRESHOLD

    issues = []
    if not blur_ok:
        issues.append("Image is blurred — hold the phone steady and refocus.")
    if not glare_ok:
        issues.append("Glare/reflection detected on the frame — tilt the card or move out of direct light.")
    if mean_brightness < DARK_MEAN_THRESHOLD:
        issues.append("Frame is too dark — add light or move to a brighter area.")
    elif mean_brightness > BRIGHT_MEAN_THRESHOLD:
        issues.append("Frame is overexposed — reduce direct light on the card.")

    # Weighted composite score, 0-100.
    blur_component = max(0.0, min(1.0, blur_score / (BLUR_OK_THRESHOLD * 2)))
    glare_component = max(0.0, 1.0 - glare_fraction / (GLARE_OK_FRACTION * 4))
    if mean_brightness < DARK_MEAN_THRESHOLD:
        bright_component = mean_brightness / DARK_MEAN_THRESHOLD
    elif mean_brightness > BRIGHT_MEAN_THRESHOLD:
        bright_component = max(0.0, (255 - mean_brightness) / (255 - BRIGHT_MEAN_THRESHOLD))
    else:
        bright_component = 1.0
    quality_score = int(round(100 * (0.45 * blur_component + 0.35 * glare_component + 0.20 * bright_component)))
    quality_score = max(0, min(100, quality_score))

    if quality_score >= 85:
        verdict = "Ready for analysis."
    elif quality_score >= 60:
        verdict = "Usable, but retaking would improve confidence."
    else:
        verdict = "Not reliable enough — retake recommended."

    return QualityReport(blur_score, blur_ok, glare_fraction, glare_ok,
                          mean_brightness, brightness_ok, quality_score, verdict, issues)


# ----------------------------------------------------------- card & warp --

@dataclass
class CardDetection:
    found: bool
    corners: Optional[List[List[float]]]  # 4 points, TL,TR,BR,BL (image pixel coords)
    confidence: float
    method: str


def _order_quad(pts: np.ndarray) -> np.ndarray:
    """Order 4 points as TL, TR, BR, BL."""
    pts = pts.reshape(4, 2).astype(np.float32)
    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1).reshape(-1)
    tl = pts[np.argmin(s)]
    br = pts[np.argmax(s)]
    tr = pts[np.argmin(diff)]
    bl = pts[np.argmax(diff)]
    return np.array([tl, tr, br, bl], dtype=np.float32)


def detect_reference_card(img: np.ndarray) -> CardDetection:
    h, w = img.shape[:2]
    frame_area = h * w
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 40, 120)
    edges = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=2)

    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    best = None
    best_area = 0
    for c in contours:
        area = cv2.contourArea(c)
        # Card should be a meaningfully large but not full-frame region.
        if area < 0.05 * frame_area or area > 0.92 * frame_area:
            continue
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) != 4:
            continue
        if not cv2.isContourConvex(approx):
            continue
        if area > best_area:
            best_area = area
            best = approx

    if best is None:
        return CardDetection(found=False, corners=None, confidence=0.0, method="contour+quad")

    quad = _order_quad(best)
    # Confidence heuristic: how close the quad's area fraction is to a
    # plausible in-hand card size, plus how rectangular the angles are.
    area_fraction = best_area / frame_area
    area_score = 1.0 - min(1.0, abs(area_fraction - 0.35) / 0.45)

    def angle(p0, p1, p2):
        v1 = p0 - p1
        v2 = p2 - p1
        cos = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-6)
        return math.degrees(math.acos(np.clip(cos, -1, 1)))

    angles = [angle(quad[i - 1], quad[i], quad[(i + 1) % 4]) for i in range(4)]
    rect_score = 1.0 - min(1.0, sum(abs(a - 90) for a in angles) / 180.0)

    confidence = max(0.0, min(1.0, 0.5 * area_score + 0.5 * rect_score))
    return CardDetection(found=True, corners=quad.tolist(), confidence=round(confidence, 3),
                          method="contour+quad")


def warp_card(img: np.ndarray, corners: List[List[float]]) -> np.ndarray:
    src = np.array(corners, dtype=np.float32)
    dst = np.array([
        [0, 0], [WARP_WIDTH - 1, 0], [WARP_WIDTH - 1, WARP_HEIGHT - 1], [0, WARP_HEIGHT - 1],
    ], dtype=np.float32)
    M = cv2.getPerspectiveTransform(src, dst)
    return cv2.warpPerspective(img, M, (WARP_WIDTH, WARP_HEIGHT))


def _patch_mean_bgr(warped: np.ndarray, rect_frac) -> Tuple[float, float, float]:
    x0, y0, x1, y1 = frac_rect_to_px(rect_frac, WARP_WIDTH, WARP_HEIGHT)
    # Sample the centre 60% of the patch to avoid edge/border contamination.
    mx, my = int((x1 - x0) * 0.2), int((y1 - y0) * 0.2)
    region = warped[y0 + my:y1 - my, x0 + mx:x1 - mx]
    mean = region.reshape(-1, 3).mean(axis=0)
    return float(mean[0]), float(mean[1]), float(mean[2])  # B, G, R


# ------------------------------------------------------------- colour ops --

def bgr_to_lab(bgr: Tuple[float, float, float]) -> Tuple[float, float, float]:
    px = np.uint8([[[np.clip(bgr[0], 0, 255), np.clip(bgr[1], 0, 255), np.clip(bgr[2], 0, 255)]]])
    lab = cv2.cvtColor(px, cv2.COLOR_BGR2LAB)[0][0]
    L = lab[0] * 100.0 / 255.0
    a = lab[1] - 128.0
    b = lab[2] - 128.0
    return float(L), float(a), float(b)


def delta_e76(lab1, lab2) -> float:
    return math.sqrt(sum((c1 - c2) ** 2 for c1, c2 in zip(lab1, lab2)))


@dataclass
class Calibration:
    white_bgr: Tuple[float, float, float]
    black_bgr: Tuple[float, float, float]
    gray_bgr: Tuple[float, float, float]
    check_bgr_corrected: Tuple[float, float, float]
    check_deltae: float
    gains: Tuple[float, float, float]
    offsets: Tuple[float, float, float]
    trustworthy: bool


def compute_calibration(warped: np.ndarray) -> Calibration:
    white_bgr = _patch_mean_bgr(warped, WHITE_PATCH)
    black_bgr = _patch_mean_bgr(warped, BLACK_PATCH)
    gray_bgr = _patch_mean_bgr(warped, GRAY_PATCH)
    check_bgr_raw = _patch_mean_bgr(warped, CHECK_PATCH)

    # Per-channel linear stretch so photographed white -> 255, photographed black -> 0.
    gains = tuple(255.0 / max(1.0, (white_bgr[i] - black_bgr[i])) for i in range(3))
    offsets = tuple(-black_bgr[i] * gains[i] for i in range(3))

    def correct(bgr):
        return tuple(max(0.0, min(255.0, bgr[i] * gains[i] + offsets[i])) for i in range(3))

    check_corrected = correct(check_bgr_raw)
    check_expected_bgr = (CHECK_PATCH_SRGB[2], CHECK_PATCH_SRGB[1], CHECK_PATCH_SRGB[0])
    check_deltae = delta_e76(bgr_to_lab(check_corrected), bgr_to_lab(check_expected_bgr))

    return Calibration(
        white_bgr=white_bgr, black_bgr=black_bgr, gray_bgr=gray_bgr,
        check_bgr_corrected=check_corrected, check_deltae=round(check_deltae, 2),
        gains=tuple(round(g, 4) for g in gains), offsets=tuple(round(o, 2) for o in offsets),
        trustworthy=check_deltae <= 16.0,
    )


def apply_calibration(bgr: Tuple[float, float, float], cal: Calibration) -> Tuple[float, float, float]:
    return tuple(max(0.0, min(255.0, bgr[i] * cal.gains[i] + cal.offsets[i])) for i in range(3))


# -------------------------------------------------------- classification --

@dataclass
class ClassificationResult:
    label: str                # "positive" | "negative" | "inconclusive" | "cannot_determine"
    confidence: float         # 0..1
    distance_to_negative: float
    distance_to_positive: float
    sample_lab: Tuple[float, float, float]
    reasons: List[str]


def classify_sample(sample_lab, kit: KitProfile, quality: QualityReport, cal: Calibration) -> ClassificationResult:
    reasons = []

    if quality.quality_score < 55:
        reasons.append(f"Image quality score ({quality.quality_score}/100) is below the reliability floor.")
        return ClassificationResult("cannot_determine", 0.0,
                                     delta_e76(sample_lab, kit.negative_lab),
                                     delta_e76(sample_lab, kit.positive_lab),
                                     sample_lab, reasons)

    if not cal.trustworthy:
        reasons.append(f"Calibration check patch residual is high (ΔE={cal.check_deltae}) — colour correction is not trustworthy.")
        return ClassificationResult("cannot_determine", 0.0,
                                     delta_e76(sample_lab, kit.negative_lab),
                                     delta_e76(sample_lab, kit.positive_lab),
                                     sample_lab, reasons)

    d_neg = delta_e76(sample_lab, kit.negative_lab)
    d_pos = delta_e76(sample_lab, kit.positive_lab)
    total = d_neg + d_pos
    margin = abs(d_pos - d_neg) / total if total > 1e-6 else 0.0

    if min(d_neg, d_pos) > kit.no_match_deltae:
        reasons.append("Sample colour does not resemble either reference response for this kit.")
        return ClassificationResult("inconclusive", round(margin, 3), round(d_neg, 2), round(d_pos, 2),
                                     sample_lab, reasons)

    label = "positive" if d_pos < d_neg else "negative"
    reasons.append(f"Sample is closer to the {label} reference (ΔE={min(d_neg, d_pos):.1f}) "
                    f"than the alternative (ΔE={max(d_neg, d_pos):.1f}).")

    if margin < kit.min_confidence_margin:
        reasons.append(f"Margin between positive/negative distances is narrow ({margin:.2f}).")
        return ClassificationResult("inconclusive", round(margin, 3), round(d_neg, 2), round(d_pos, 2),
                                     sample_lab, reasons)

    confidence = min(1.0, margin / kit.min_confidence_margin * 0.55 + 0.25)
    if min(d_neg, d_pos) <= kit.strong_match_deltae:
        confidence = min(1.0, confidence + 0.2)
        reasons.append("Colour distance to the matched reference is within the strong-match band.")

    return ClassificationResult(label, round(confidence, 3), round(d_neg, 2), round(d_pos, 2),
                                 sample_lab, reasons)


# ------------------------------------------------------------- full run --

@dataclass
class FrameResult:
    quality: QualityReport
    card: CardDetection
    calibration: Optional[Calibration]
    classification: Optional[ClassificationResult]
    roi_bgr_corrected: Optional[Tuple[float, float, float]]


def run_pipeline(img: np.ndarray, kit: KitProfile,
                  manual_corners: Optional[List[List[float]]] = None) -> FrameResult:
    quality = assess_quality(img)

    if manual_corners is not None:
        card = CardDetection(found=True, corners=manual_corners, confidence=1.0, method="manual")
    else:
        card = detect_reference_card(img)

    if not card.found or card.confidence < 0.25:
        return FrameResult(quality, card, None, None, None)

    warped = warp_card(img, card.corners)
    cal = compute_calibration(warped)
    roi_bgr_raw = _patch_mean_bgr(warped, ROI_WINDOW)
    roi_bgr_corrected = apply_calibration(roi_bgr_raw, cal)
    sample_lab = bgr_to_lab(roi_bgr_corrected)
    classification = classify_sample(sample_lab, kit, quality, cal)

    return FrameResult(quality, card, cal, classification, roi_bgr_corrected)


def consensus(frame_classifications: List[ClassificationResult]) -> dict:
    labels = [c.label for c in frame_classifications if c is not None]
    if not labels:
        return {"label": "cannot_determine", "agreement": 0.0, "frame_labels": []}
    from collections import Counter
    counts = Counter(labels)
    top_label, top_count = counts.most_common(1)[0]
    agreement = top_count / len(labels)
    final = top_label if agreement >= 0.6 else "inconclusive"
    return {"label": final, "agreement": round(agreement, 2), "frame_labels": labels}
