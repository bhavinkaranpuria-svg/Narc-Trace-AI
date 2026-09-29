import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
DB_PATH = os.path.join(DATA_DIR, "narctrace.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS records (
    id TEXT PRIMARY KEY,
    case_id TEXT,
    sample_id TEXT,
    operator_id TEXT,
    kit_id TEXT,
    kit_name TEXT,
    created_at TEXT,
    gps_lat REAL,
    gps_lng REAL,
    gps_accuracy REAL,
    gps_mock_suspected INTEGER,
    capture_mode TEXT,
    classification TEXT,
    confidence REAL,
    quality_score INTEGER,
    officer_assessment TEXT,
    distance_to_negative REAL,
    distance_to_positive REAL,
    calibration_trustworthy INTEGER,
    check_patch_deltae REAL,
    card_detection_confidence REAL,
    model_version TEXT,
    image_hash TEXT,
    record_hash TEXT,
    prev_hash TEXT,
    signature TEXT,
    public_key_fingerprint TEXT,
    sync_status TEXT,
    reasons_json TEXT,
    fields_json TEXT
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id TEXT,
    timestamp TEXT,
    action TEXT,
    detail TEXT
);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def get_conn():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)


def get_last_record_hash() -> str:
    from app.crypto_utils import GENESIS_HASH
    with get_conn() as conn:
        row = conn.execute("SELECT record_hash FROM records ORDER BY rowid DESC LIMIT 1").fetchone()
        return row["record_hash"] if row else GENESIS_HASH


def next_record_id() -> str:
    with get_conn() as conn:
        row = conn.execute("SELECT COUNT(*) AS n FROM records").fetchone()
        n = row["n"] + 1
        return f"NCB-REC-{n:06d}"


def insert_record(rec: dict):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO records (
                id, case_id, sample_id, operator_id, kit_id, kit_name, created_at,
                gps_lat, gps_lng, gps_accuracy, gps_mock_suspected, capture_mode,
                classification, confidence, quality_score, officer_assessment,
                distance_to_negative, distance_to_positive, calibration_trustworthy,
                check_patch_deltae, card_detection_confidence, model_version,
                image_hash, record_hash, prev_hash, signature, public_key_fingerprint,
                sync_status, reasons_json, fields_json
            ) VALUES (
                :id, :case_id, :sample_id, :operator_id, :kit_id, :kit_name, :created_at,
                :gps_lat, :gps_lng, :gps_accuracy, :gps_mock_suspected, :capture_mode,
                :classification, :confidence, :quality_score, :officer_assessment,
                :distance_to_negative, :distance_to_positive, :calibration_trustworthy,
                :check_patch_deltae, :card_detection_confidence, :model_version,
                :image_hash, :record_hash, :prev_hash, :signature, :public_key_fingerprint,
                :sync_status, :reasons_json, :fields_json
            )
        """, rec)


def insert_audit(record_id: str, action: str, detail: str = ""):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO audit_log (record_id, timestamp, action, detail) VALUES (?, ?, ?, ?)",
            (record_id, now_iso(), action, detail),
        )


def get_audit(record_id: str):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM audit_log WHERE record_id = ? ORDER BY id ASC", (record_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_record(record_id: str):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM records WHERE id = ?", (record_id,)).fetchone()
        return dict(row) if row else None


def get_record_by_rowid_prev(record_id: str):
    """Return the record immediately before this one (by insertion order)."""
    with get_conn() as conn:
        row = conn.execute("SELECT rowid FROM records WHERE id = ?", (record_id,)).fetchone()
        if not row:
            return None
        prev = conn.execute(
            "SELECT * FROM records WHERE rowid < ? ORDER BY rowid DESC LIMIT 1", (row["rowid"],)
        ).fetchone()
        return dict(prev) if prev else None


def list_records(kit_id=None, classification=None, operator_id=None, limit=200):
    q = "SELECT * FROM records WHERE 1=1"
    params = []
    if kit_id:
        q += " AND kit_id = ?"
        params.append(kit_id)
    if classification:
        q += " AND classification = ?"
        params.append(classification)
    if operator_id:
        q += " AND operator_id = ?"
        params.append(operator_id)
    q += " ORDER BY rowid DESC LIMIT ?"
    params.append(limit)
    with get_conn() as conn:
        rows = conn.execute(q, params).fetchall()
        return [dict(r) for r in rows]


def stats():
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) AS n FROM records").fetchone()["n"]
        by_class = conn.execute(
            "SELECT classification, COUNT(*) AS n FROM records GROUP BY classification"
        ).fetchall()
        by_kit = conn.execute(
            "SELECT kit_id, kit_name, COUNT(*) AS n FROM records GROUP BY kit_id"
        ).fetchall()
        by_day = conn.execute(
            "SELECT substr(created_at, 1, 10) AS day, COUNT(*) AS n FROM records "
            "GROUP BY day ORDER BY day DESC LIMIT 14"
        ).fetchall()
        avg_conf = conn.execute("SELECT AVG(confidence) AS a FROM records").fetchone()["a"]
        avg_quality = conn.execute("SELECT AVG(quality_score) AS a FROM records").fetchone()["a"]
        return {
            "total": total,
            "by_classification": {r["classification"]: r["n"] for r in by_class},
            "by_kit": [dict(r) for r in by_kit],
            "by_day": [dict(r) for r in by_day],
            "avg_confidence": round(avg_conf, 3) if avg_conf else None,
            "avg_quality": round(avg_quality, 1) if avg_quality else None,
        }
