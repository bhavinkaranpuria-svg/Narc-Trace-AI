#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
pip install -r requirements.txt
python3 -m app.generate_reference_card
echo ""
echo "Reference card generated at backend/assets/reference_card.png — print it."
echo "Starting API on http://localhost:8000  (docs at /docs)"
echo ""
uvicorn app.main:app --reload --port 8000
