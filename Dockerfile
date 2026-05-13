# ─── Stage 1: build ──────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# Install dependencies into a prefix so they can be copied in the final stage
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ─── Stage 2: final image ────────────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy source
COPY src/       ./src/
COPY web/       ./web/
COPY scripts/   ./scripts/
COPY main.py    .

# Copy data catalogue if it already exists locally (preferred — avoids a
# network download at image-build time).  If the data/ directory is absent
# from the build context the COPY will be skipped gracefully; the catalog
# script will run instead via the CMD entrypoint wrapper below.
COPY data/ ./data/

# Download CBO data if the catalog is not already present in the image.
# This runs once during `docker build` (or `gcloud run deploy --source`).
RUN if [ ! -f data/catalog.json ]; then \
      echo "Catalog not found — downloading CBO data..." && \
      python scripts/catalog_data.py; \
    else \
      echo "Catalog found — skipping download."; \
    fi

# Cloud Run injects PORT; gunicorn binds to it.
ENV PORT=8080
EXPOSE 8080

CMD exec gunicorn \
      --bind "0.0.0.0:${PORT}" \
      --workers 1 \
      --timeout 120 \
      --access-logfile - \
      web.app:app
