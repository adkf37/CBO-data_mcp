# ─── Stage 1: build ──────────────────────────────────────────────────────────
ARG CBO_DATA_IMAGE=us-central1-docker.pkg.dev/cbo-data-mcp/cloud-run-source-deploy/cbo-data-mcp@sha256:f8f10d649685ba503d333113bea887518d5e909d08bbacefd17ff689f7a94f9e
FROM ${CBO_DATA_IMAGE} AS baseline_data

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

# Preserve the currently deployed, known-good dataset for application releases.
# The upstream program-detail repository no longer contains data/processed CSVs,
# so rebuilding that catalog during every deploy currently produces no data.
# Refresh data deliberately, then advance CBO_DATA_IMAGE to the validated image.
COPY --from=baseline_data /app/data /app/data

# Cloud Run injects PORT; gunicorn binds to it.
ENV PORT=8080
EXPOSE 8080

CMD exec gunicorn \
      --bind "0.0.0.0:${PORT}" \
      --workers 1 \
      --timeout 120 \
      --access-logfile - \
      web.app:app
