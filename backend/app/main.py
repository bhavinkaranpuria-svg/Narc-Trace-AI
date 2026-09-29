import base64
import io
import json
import os
import uuid
from datetime import datetime, timezone
from typing import List, Optional

import qrcode
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from app import vision, crypto_utils, database as db
from app.kits import KIT_PROFILES, get_kit, list_kits
from app.schemas import RecordCreateRequest, VerifyRequest

app = FastAPI(title="NARC-TRACE AI", version="0.1.0",
              description="Digital companion for field drug testing.")

# In production, set ALLOWED_ORIGINS to a comma-separated list of exact
# frontend origins (e.g. "https://narc-trace.vercel.app"). Defaults to "*"
# for local development only — lock this down before exposing real data.
_origins_env = os.environ.get("ALLOWED_ORIGINS", "*")
_allow_origins = ["*"] if _origins_env.strip() == "*" else [o.strip() for o in _origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

db.init_db()

# Ephemeral store: an /api/analyze preview must be confirmed via /api/records
# before it becomes a durable, signed evidence record. This mirrors the real
# officer flow (capture -> review AI read -> confirm/sign) without forcing a
# second image upload. Demo-only: production would persist this to encrypted
# local storage so it survives offline app restarts (see README).
PENDING_ANALYSES = {}
MAX_PENDING = 200


def _quality_dict(q):
    from dataclasses import asdict
    return asdict(q)


def _classification_dict(c):
    if c is None:
        return None
    from dataclasses import asdict
    return asdict(c)


@app.get("/api/health")
def health():
    return {"status": "ok", "model_version": vision.MODEL_VERSION,
            "public_key_fingerprint": crypto_utils.public_key_fingerprint()}


@app.get("/api/kits")
def kits():
    return {"kits": list_kits()}


@app.get("/api/reference-card")
def reference_card():
    path = os.path.join(os.path.dirname(__file__), "..", "assets", "reference_card.png")
    if not os.path.exists(path):
        raise HTTPException(404, "Reference card asset not generated yet.")
    return FileResponse(path, media_type="image/png", filename="ncb_reference_card.png")


@app.post("/api/analyze")
async def analyze(
    images: List[UploadFile] = File(...),
    kit_id: str = Form(...),
    manual_corners: Optional[str] = Form(None),
    officer_assessment: Optional[str] = Form(None),
):
    try:
        kit = get_kit(kit_id)
    except KeyError:
        raise HTTPException(400, f"Unknown kit_id '{kit_id}'")

    corners = json.loads(manual_corners) if manual_corners else None

    frames = []
    raw_bytes_list = []
    for upload in images:
        raw = await upload.read()
        raw_bytes_list.append(raw)
        img = vision.decode_image(raw)
        result = vision.run_pipeline(img, kit, manual_corners=corners)
        frames.append(result)

    # Pick the best-quality frame as the canonical evidence image.
    best_idx = max(range(len(frames)), key=lambda i: frames[i].quality.quality_score)
    best = frames[best_idx]
    canonical_bytes = raw_bytes_list[best_idx]

    classifications = [f.classification for f in frames if f.classification]
    consensus = vision.consensus(classifications) if len(frames) > 1 else None

    analysis_id = str(uuid.uuid4())
    if len(PENDING_ANALYSES) > MAX_PENDING:
        PENDING_ANALYSES.pop(next(iter(PENDING_ANALYSES)))
    PENDING_ANALYSES[analysis_id] = {
        "image_bytes": canonical_bytes,
        "kit_id": kit_id,
        "kit_name": kit.name,
        "best_frame": best,
        "frame_count": len(frames),
        "consensus": consensus,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    officer_vs_ai = None
    if officer_assessment and best.classification:
        officer_vs_ai = {
            "officer": officer_assessment,
            "ai": best.classification.label,
            "agree": officer_assessment == best.classification.label,
        }

    return {
        "analysis_id": analysis_id,
        "kit": {"id": kit.id, "name": kit.name},
        "frame_count": len(frames),
        "quality": _quality_dict(best.quality),
        "card": {
            "found": best.card.found,
            "confidence": best.card.confidence,
            "method": best.card.method,
            "corners": best.card.corners,
        },
        "calibration": (
            {
                "check_patch_deltae": best.calibration.check_deltae,
                "trustworthy": best.calibration.trustworthy,
                "gains": best.calibration.gains,
            } if best.calibration else None
        ),
        "classification": _classification_dict(best.classification),
        "consensus": consensus,
        "officer_vs_ai": officer_vs_ai,
        "model_version": vision.MODEL_VERSION,
    }


@app.post("/api/records")
def create_record(payload: RecordCreateRequest):
    pending = PENDING_ANALYSES.get(payload.analysis_id)
    if not pending:
        raise HTTPException(404, "Analysis not found or expired — run /api/analyze again.")

    best = pending["best_frame"]
    if best.classification is None:
        raise HTTPException(400, "This analysis has no classification result (card not detected or quality too low) — cannot create a record from it.")

    image_hash = crypto_utils.sha256_bytes(pending["image_bytes"])
    record_id = db.next_record_id()
    prev_hash = db.get_last_record_hash()
    created_at = datetime.now(timezone.utc).isoformat()

    reasons = best.classification.reasons

    fields = {
        "id": record_id,
        "case_id": payload.case_id,
        "sample_id": payload.sample_id,
        "operator_id": payload.operator_id,
        "kit_id": pending["kit_id"],
        "kit_name": pending["kit_name"],
        "created_at": created_at,
        "gps_lat": payload.gps_lat,
        "gps_lng": payload.gps_lng,
        "gps_accuracy": payload.gps_accuracy,
        "gps_mock_suspected": payload.gps_mock_suspected,
        "capture_mode": payload.capture_mode,
        "classification": best.classification.label,
        "confidence": best.classification.confidence,
        "quality_score": best.quality.quality_score,
        "officer_assessment": payload.officer_assessment,
        "distance_to_negative": best.classification.distance_to_negative,
        "distance_to_positive": best.classification.distance_to_positive,
        "calibration_trustworthy": best.calibration.trustworthy if best.calibration else False,
        "check_patch_deltae": best.calibration.check_deltae if best.calibration else None,
        "card_detection_confidence": best.card.confidence,
        "model_version": vision.MODEL_VERSION,
        "image_hash": image_hash,
        "prev_hash": prev_hash,
        "frame_count": pending["frame_count"],
        "consensus": pending["consensus"],
    }

    record_hash = crypto_utils.hash_record_fields(fields)
    signature = crypto_utils.sign_hash(record_hash)
    pub_fp = crypto_utils.public_key_fingerprint()

    row = {
        "id": record_id,
        "case_id": payload.case_id,
        "sample_id": payload.sample_id,
        "operator_id": payload.operator_id,
        "kit_id": pending["kit_id"],
        "kit_name": pending["kit_name"],
        "created_at": created_at,
        "gps_lat": payload.gps_lat,
        "gps_lng": payload.gps_lng,
        "gps_accuracy": payload.gps_accuracy,
        "gps_mock_suspected": 1 if payload.gps_mock_suspected else 0,
        "capture_mode": payload.capture_mode,
        "classification": best.classification.label,
        "confidence": best.classification.confidence,
        "quality_score": best.quality.quality_score,
        "officer_assessment": payload.officer_assessment,
        "distance_to_negative": best.classification.distance_to_negative,
        "distance_to_positive": best.classification.distance_to_positive,
        "calibration_trustworthy": 1 if (best.calibration and best.calibration.trustworthy) else 0,
        "check_patch_deltae": best.calibration.check_deltae if best.calibration else None,
        "card_detection_confidence": best.card.confidence,
        "model_version": vision.MODEL_VERSION,
        "image_hash": image_hash,
        "record_hash": record_hash,
        "prev_hash": prev_hash,
        "signature": signature,
        "public_key_fingerprint": pub_fp,
        "sync_status": "local" if payload.capture_mode == "offline" else "synced",
        "reasons_json": json.dumps(reasons),
        "fields_json": json.dumps(fields, sort_keys=True),
    }
    db.insert_record(row)

    for action, detail in [
        ("Test created", f"Case {payload.case_id} / Sample {payload.sample_id}"),
        ("Image captured", f"{pending['frame_count']} frame(s), image hash {image_hash[:12]}…"),
        ("AI classification generated", f"{best.classification.label} (confidence {best.classification.confidence})"),
        ("Officer confirmed", payload.officer_assessment or "(no independent officer call recorded)"),
        ("Record signed", f"key {pub_fp}"),
        ("Record synchronized" if payload.capture_mode == "online" else "Captured offline — pending sync", ""),
    ]:
        db.insert_audit(record_id, action, detail)

    del PENDING_ANALYSES[payload.analysis_id]

    qr_b64 = _build_qr({"record_id": record_id, "hash": record_hash[:20], "sig_fp": pub_fp})

    return {**row, "reasons": reasons, "qr_base64": qr_b64}


def _build_qr(payload: dict) -> str:
    qr = qrcode.QRCode(border=2, box_size=6)
    qr.add_data(json.dumps(payload, separators=(",", ":")))
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


@app.get("/api/records")
def records(kit_id: Optional[str] = None, classification: Optional[str] = None,
            operator_id: Optional[str] = None, limit: int = 200):
    return {"records": db.list_records(kit_id, classification, operator_id, limit)}


@app.get("/api/records/{record_id}")
def get_record(record_id: str):
    rec = db.get_record(record_id)
    if not rec:
        raise HTTPException(404, "Record not found")
    rec = dict(rec)
    rec["reasons"] = json.loads(rec.get("reasons_json") or "[]")
    rec["fields"] = json.loads(rec.get("fields_json") or "{}")
    return rec


@app.get("/api/records/{record_id}/qr")
def get_record_qr(record_id: str):
    rec = db.get_record(record_id)
    if not rec:
        raise HTTPException(404, "Record not found")
    qr_b64 = _build_qr({"record_id": rec["id"], "hash": rec["record_hash"][:20],
                         "sig_fp": rec["public_key_fingerprint"]})
    return {"record_id": record_id, "qr_base64": qr_b64}


@app.get("/api/audit/{record_id}")
def audit(record_id: str):
    if not db.get_record(record_id):
        raise HTTPException(404, "Record not found")
    return {"record_id": record_id, "entries": db.get_audit(record_id)}


@app.get("/api/dashboard/stats")
def dashboard_stats():
    return db.stats()


@app.post("/api/verify")
def verify(payload: VerifyRequest):
    rec = db.get_record(payload.record_id)
    if not rec:
        raise HTTPException(404, "Record not found")

    fields = json.loads(rec["fields_json"])
    tampered = False
    if payload.override_fields:
        fields = {**fields, **payload.override_fields}
        tampered = True

    computed_hash = crypto_utils.hash_record_fields(fields)
    stored_hash = rec["record_hash"]
    hash_match = computed_hash == stored_hash

    signature_to_check = payload.override_signature or rec["signature"]
    signature_valid = crypto_utils.verify_signature(computed_hash, signature_to_check)

    prev = db.get_record_by_rowid_prev(payload.record_id)
    expected_prev_hash = prev["record_hash"] if prev else crypto_utils.GENESIS_HASH
    chain_intact = fields.get("prev_hash") == expected_prev_hash

    overall = hash_match and signature_valid and chain_intact

    checks = {
        "computed_hash": computed_hash,
        "stored_hash": stored_hash,
        "hash_match": hash_match,
        "signature_valid": signature_valid,
        "chain_intact": chain_intact,
        "prev_hash_expected": expected_prev_hash,
        "prev_hash_recorded": fields.get("prev_hash"),
    }

    return {
        "record_id": payload.record_id,
        "overall": "VERIFIED" if overall else "INTEGRITY FAILED",
        "simulated_tamper": tampered,
        "checks": checks,
    }
