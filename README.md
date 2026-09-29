# NARC-TRACE AI

**Intelligent, tamper-evident field drug testing — a working prototype for SIH26231
("Digital Companion for Field Drug Testing", Ministry of Home Affairs / NCB).**

This is not a mockup. The computer-vision pipeline, the calibration math, the
hash-chain, and the RSA signing are all real and independently testable —
see [`backend/app/_selftest.py`](backend/app/_selftest.py), which synthesizes
photographed test cards and runs them through the exact same code path the
API uses.

```
Existing test kit  →  Smartphone photo (kit + reference card, one frame)
                              │
                    ┌─────────▼─────────┐
                    │   SEE             │  blur / glare / brightness checks
                    │   quality gate    │  reference-card contour detection
                    └─────────┬─────────┘
                    ┌─────────▼─────────┐
                    │   CORRECT         │  perspective-warp the card
                    │   calibration     │  white/gray/black patch sampling
                    └─────────┬─────────┘  → linear colour correction
                    ┌─────────▼─────────┐
                    │   DECIDE          │  sample-window colour → CIELAB
                    │   classification  │  ΔE distance to kit reference points
                    └─────────┬─────────┘  → positive / negative / inconclusive
                    ┌─────────▼─────────┐     (or "cannot determine")
                    │   PROVE           │  SHA-256 hash, RSA-PSS signature,
                    │   integrity       │  hash-chain link to previous record
                    └─────────┬─────────┘
                    ┌─────────▼─────────┐
                    │   TRACE           │  SQLite ledger, audit log, QR
                    │   record + audit  │  verification, dashboard
                    └───────────────────┘
```

## Quickstart

Two terminals.

```bash
# Terminal 1 — backend (FastAPI, port 8000)
cd backend
./run.sh
```

```bash
# Terminal 2 — frontend (Next.js, port 3000)
cd frontend
./run.sh
```

Open `http://localhost:3000`. The backend's interactive API docs are at
`http://localhost:8000/docs`.

The first `./run.sh` in `backend/` generates a printable reference card at
`backend/assets/reference_card.png` and prints its path — print it (or view
it on a second screen) and photograph it with something colourful in the
sample window to try the pipeline for real. You can also download it from
the running app at `http://localhost:8000/api/reference-card`, or from the
running frontend via the "Print the reference card" link on the New Test
page.

## Why a physical reference card, and why it looks like this

Colorimetric field kits are read under wildly inconsistent phone cameras and
lighting. Rather than trying to train that variance away, the card carries
its own ground truth into every photo: four calibration patches (white /
18%-gray / black / a known "check" colour) on the left, and a cut-out
**sample window** on the right where the reacted kit or strip is placed —
in the *same frame*, under the *same light*, calibrated by the *same
patches*. That's what makes both the card detection and the colour
correction in `backend/app/vision.py` genuinely robust to skewed angles and
uneven lighting instead of a demo-only trick — see the self-test for
before/after numbers.

The **check patch** exists purely so the system can catch its own
calibration failing: if the corrected check-patch colour doesn't land close
to its known value, the classifier refuses to call a result rather than
silently trusting a bad correction (feature: it can say "cannot determine").

## What's real vs. what's a placeholder

Everything in the pipeline — quality gating, card detection, perspective
correction, colour calibration, ΔE classification, hashing, signing, the
hash chain, QR verification — is fully implemented and runs end to end.

**The one thing that is explicitly a placeholder:** the per-kit reference
CIELAB colours in [`backend/app/kits.py`](backend/app/kits.py) (`KIT_PROFILES`).
These describe what a "positive" and "negative" colour reaction is expected
to look like once corrected. Right now they're plausible demo values so the
classifier has something to compare against. In a real deployment they'd be
replaced with figures from controlled reagent trials against each
NCB-approved kit batch — the architecture (kit-profile registry, per-batch
drift monitoring hooks) is already there to receive validated data; the data
itself isn't ours to invent.

## API summary

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/kits` | List configured kit profiles |
| GET | `/api/reference-card` | Download the printable calibration card (PNG) |
| POST | `/api/analyze` | Run the pipeline on 1–3 frames; returns quality, calibration, classification, explainability, consensus. Does **not** persist anything. |
| POST | `/api/records` | Confirm an analysis into a signed, hash-chained evidence record |
| GET | `/api/records` | List records (filter by kit / classification / operator) |
| GET | `/api/records/{id}` | Full record incl. canonical fields used for hashing |
| GET | `/api/records/{id}/qr` | Verification QR (base64 PNG) |
| GET | `/api/audit/{id}` | Audit timeline for a record |
| GET | `/api/dashboard/stats` | Aggregate counts for the dashboard |
| POST | `/api/verify` | Recompute hash, check signature, check chain link. Accepts `override_fields` to simulate tampering (the "tamper challenge" demo — see the Verify page in the UI) |

Full request/response schemas: `http://localhost:8000/docs`.

## Project structure

```
backend/
  app/
    main.py               FastAPI app — all endpoints
    vision.py              quality / card detection / calibration / classification
    card_layout.py         shared geometry between the card generator & vision pipeline
    generate_reference_card.py   renders the printable card
    crypto_utils.py         SHA-256, RSA-PSS signing, hash-chain helpers
    database.py             SQLite: records, audit log
    kits.py                 kit profile registry (see placeholder note above)
    schemas.py               request models
    _selftest.py              synthesizes test photos, runs the real pipeline, checks results
  assets/reference_card.png   (generated by run.sh)
  data/                        SQLite DB + RSA keypair (generated on first run, gitignored)
frontend/
  app/
    page.js                 New Test — capture, analyze, confirm & sign
    dashboard/page.js        stats + records table
    records/[id]/page.js      full evidence report + audit timeline
    verify/page.js             verification + tamper challenge
  components/                 shared UI (explainability panel, evidence record card, ...)
  lib/api.js                   backend client
```

## Design choices worth knowing for Q&A

- **Classical CV over a black-box model** — every step is inspectable and
  the "why" panel in the UI is a direct readout of the pipeline's
  intermediate values (ΔE distances, calibration residual, quality
  sub-scores), not a post-hoc explanation bolted onto a neural net.
- **The system can refuse to answer.** Two independent gates —
  image-quality floor and calibration-check-patch residual — route low-trust
  frames to `cannot_determine` before classification even runs, and a narrow
  positive/negative margin routes to `inconclusive` after it does.
- **Hash chain, not blockchain.** Each record's hash is computed over its
  own fields *plus* the previous record's hash
  (`crypto_utils.hash_record_fields`), so altering or deleting any record
  breaks the chain for everything after it. `POST /api/verify` demonstrates
  this directly — see the Verify page's tamper challenge.
- **Multi-frame consensus** is supported (`/api/analyze` accepts up to 3
  images); the highest-quality frame becomes the canonical evidence image,
  and per-frame agreement is shown alongside it.
- **Officer-vs-AI (blind mode):** the officer's own call can be recorded
  *before* the AI result is shown, and both are stored and compared —
  this is an assistive tool, not an autonomous one, matching the problem
  statement's "presumptive result" framing.

## Honest limitations (not yet built)

These were deliberately scoped out of this prototype rather than faked:

- **Anti-spoof / replay detection** (design idea #10) — no liveness or
  capture-session attestation yet; the API currently accepts any uploaded
  image.
- **Android Keystore / hardware-backed signing** — the RSA keypair here is a
  single server-side demo key generated on first run
  (`backend/data/keys/`). A real deployment signs per-device, in hardware.
- **Offline-first durable queue** — `capture_mode: "offline"` is recorded on
  the record, but the ephemeral pre-confirmation store (`PENDING_ANALYSES`
  in `main.py`) is in-memory and won't survive an app restart; a real client
  needs to persist the captured frame + draft record locally until sync.
- **Kit-batch drift monitoring, federated learning, lab-feedback retraining
  loop** — architecturally anticipated (the kit registry and model-version
  field are there to support it) but not implemented.

## Regenerating the reference card

```bash
cd backend
python3 -m app.generate_reference_card
```

## Running the pipeline self-test

```bash
cd backend
python3 -m app._selftest
```

This synthesizes photographed cards (with perspective skew, and separately
with degraded lighting/focus) and confirms the real pipeline classifies them
correctly — or correctly refuses to.
#   N a r c - T r a c e - A I  
 