FROM python:3.12-slim

# libglib2.0-0: required at import time by opencv-python-headless.
# fonts-dejavu-core: used by the reference-card generator (PIL falls back
# to a worse built-in font without it, but still works).
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Pre-generate the printable reference card into the image.
RUN python -m app.generate_reference_card

# SQLite DB + RSA keypair live here — mount a volume at /app/data in
# production or they will not survive a container replacement.
RUN mkdir -p /app/data

ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
