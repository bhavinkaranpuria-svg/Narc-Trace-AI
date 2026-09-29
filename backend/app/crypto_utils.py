"""
Tamper-evidence layer: canonical hashing, RSA digital signatures, and a
hash chain linking every record to the one before it (design notes #11/#12).

Key management: for this prototype, a single RSA keypair is generated on
first run and persisted under backend/data/keys/. In a real deployment each
officer/device would hold its own key in protected hardware storage (e.g.
Android Keystore) rather than a shared server key — see README.
"""
import hashlib
import json
import os
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives import hashes, serialization

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
KEYS_DIR = os.path.join(DATA_DIR, "keys")
PRIVATE_KEY_PATH = os.path.join(KEYS_DIR, "device_private.pem")
PUBLIC_KEY_PATH = os.path.join(KEYS_DIR, "device_public.pem")

GENESIS_HASH = "0" * 64


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(obj: dict) -> bytes:
    """Stable, whitespace-free JSON encoding so hashing is deterministic
    regardless of key insertion order."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def hash_record_fields(fields: dict) -> str:
    return sha256_bytes(canonical_json(fields))


def _ensure_keypair():
    os.makedirs(KEYS_DIR, exist_ok=True)
    if os.path.exists(PRIVATE_KEY_PATH) and os.path.exists(PUBLIC_KEY_PATH):
        return
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with open(PRIVATE_KEY_PATH, "wb") as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ))
    with open(PUBLIC_KEY_PATH, "wb") as f:
        f.write(key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ))


def load_private_key():
    _ensure_keypair()
    with open(PRIVATE_KEY_PATH, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None)


def load_public_key():
    _ensure_keypair()
    with open(PUBLIC_KEY_PATH, "rb") as f:
        return serialization.load_pem_public_key(f.read())


def public_key_fingerprint() -> str:
    pub = load_public_key()
    raw = pub.public_bytes(encoding=serialization.Encoding.DER,
                            format=serialization.PublicFormat.SubjectPublicKeyInfo)
    return sha256_bytes(raw)[:16]


def sign_hash(hash_hex: str) -> str:
    key = load_private_key()
    sig = key.sign(
        hash_hex.encode("utf-8"),
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
        hashes.SHA256(),
    )
    import base64
    return base64.b64encode(sig).decode("ascii")


def verify_signature(hash_hex: str, signature_b64: str) -> bool:
    import base64
    key = load_public_key()
    try:
        key.verify(
            base64.b64decode(signature_b64),
            hash_hex.encode("utf-8"),
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256(),
        )
        return True
    except Exception:
        return False
