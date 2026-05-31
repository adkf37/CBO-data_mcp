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

# git is needed by catalog_data.py to clone the CBO data repo
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# Copy source
COPY src/       ./src/
COPY web/       ./web/
COPY scripts/   ./scripts/
COPY main.py    .

# Download CBO data at image-build time.
RUN python scripts/catalog_data.py

# Build the official US-CBO/cbo-data datasets (economic, budget, demographic)
# into a baked DuckDB store so the official_* tools work in production. The
# vendored raw clone is removed afterwards to keep the final image small; only
# data/cbo_official.duckdb and data/official_catalog.json are needed at runtime.
RUN python scripts/fetch_cbo_official.py \
    && python scripts/catalog_official.py \
    && python scripts/build_official_db.py \
    && rm -rf data/cbo_official

# Cloud Run injects PORT; gunicorn binds to it.
ENV PORT=8080
EXPOSE 8080

CMD exec gunicorn \
      --bind "0.0.0.0:${PORT}" \
      --workers 1 \
      --timeout 120 \
      --access-logfile - \
      web.app:app
