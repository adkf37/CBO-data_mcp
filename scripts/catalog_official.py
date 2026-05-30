#!/usr/bin/env python3
"""
catalog_official.py — Phase Official-01: Normalize the official CBO catalog

Reads the vendored official repository at ``data/cbo_official/`` (its DCAT-style
``catalog.json`` plus each dataset's ``schema.json``) and emits a normalized
``data/official_catalog.json`` that the rest of this project understands.

The normalized catalog is intentionally kept *separate* from the existing
``data/catalog.json`` (third-party program-detail data) so the two data families
stay decoupled.

Usage:
    python scripts/catalog_official.py

Output:
    data/official_catalog.json
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

_PROJECT_ROOT = Path(__file__).parent.parent
OFFICIAL_DIR = _PROJECT_ROOT / "data" / "cbo_official"
OUTPUT_PATH = _PROJECT_ROOT / "data" / "official_catalog.json"
SOURCE_REPO = "https://github.com/US-CBO/cbo-data"
RAW_BASE = "https://raw.githubusercontent.com/US-CBO/cbo-data/main"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Classification helpers
# ---------------------------------------------------------------------------


def _domain_from_path(download_url: str) -> str:
    """Return 'economic', 'budget', or 'other' from a distribution path."""
    parts = download_url.replace("\\", "/").split("/")
    if "economic" in parts:
        return "economic"
    if "budget" in parts:
        return "budget"
    return "other"


def _format_for(dataset: str) -> str:
    """Return the storage shape for a dataset.

    - 'spending_detail' is wide (one row per budget account).
    - 'demographic' is multi-dimensional (year + demographic keys + measure).
    - everything else is the 3-column long format (date, variable, value).
    """
    if dataset == "spending_detail":
        return "spending_detail"
    if dataset == "demographic":
        return "demographic"
    return "long"


def _date_basis(file_type: str) -> str:
    """Coarse date basis derived from a distribution's ``file_type`` token.

    Examples: 'quarterly' -> 'quarterly', 'annual_fy' -> 'fiscal',
    'fiscal' -> 'fiscal', 'annual_cy'/'calendar' -> 'calendar'.
    """
    ft = (file_type or "").lower()
    if "quarter" in ft:
        return "quarterly"
    if "cy" in ft or "calendar" in ft:
        return "calendar"
    if "fy" in ft or "fiscal" in ft:
        return "fiscal"
    return "annual"


# ---------------------------------------------------------------------------
# Schema loading
# ---------------------------------------------------------------------------


def _load_schema(schema_relpath: Optional[str]) -> dict:
    if not schema_relpath:
        return {}
    schema_path = OFFICIAL_DIR / schema_relpath
    if not schema_path.exists():
        log.warning("schema not found: %s", schema_path)
        return {}
    with schema_path.open(encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Catalog normalization
# ---------------------------------------------------------------------------


def normalize_dataset(ds: dict) -> dict:
    identifier = ds["identifier"]
    fmt = _format_for(identifier)

    distributions = ds.get("distribution", []) or []
    domain = "other"
    files: list[dict] = []
    for dist in distributions:
        url = dist.get("downloadURL", "")
        if not url.lower().endswith(".csv"):
            continue
        if domain == "other":
            domain = _domain_from_path(url)
        file_type = dist.get("file_type", "")
        files.append(
            {
                "file_type": file_type,
                "vintage": dist.get("vintage"),
                "relpath": url.replace("\\", "/"),
                "raw_url": f"{RAW_BASE}/{url.replace(chr(92), '/')}",
                "date_basis": _date_basis(file_type),
            }
        )

    vintages = sorted({f["vintage"] for f in files if f["vintage"]}, reverse=True)
    file_types = sorted({f["file_type"] for f in files if f["file_type"]})

    schema = _load_schema(ds.get("schema_path"))

    entry = {
        "dataset": identifier,
        "domain": domain,
        "format": fmt,
        "title": ds.get("title", identifier),
        "description": ds.get("description", ""),
        "publication_id": ds.get("publication_id"),
        "landing_page": ds.get("landingPage"),
        "frequency": ds.get("frequency") or schema.get("frequency"),
        "date_format": schema.get("date_format"),
        "schema_path": ds.get("schema_path"),
        "notes": schema.get("notes") or {},
        "vintages": vintages,
        "file_types": file_types,
        "files": files,
    }

    # Attach shape-specific metadata for downstream tools.
    if fmt == "long":
        entry["variables"] = schema.get("fields", {})
    elif fmt == "demographic":
        entry["domains"] = schema.get("domains", {})
    elif fmt == "spending_detail":
        # spending_detail schema describes columns rather than variables.
        entry["columns"] = schema.get("fields", schema.get("columns", {}))

    return entry


def build_catalog() -> dict:
    catalog_path = OFFICIAL_DIR / "catalog.json"
    if not catalog_path.exists():
        raise FileNotFoundError(
            f"{catalog_path} not found. Run `python scripts/fetch_cbo_official.py` first."
        )
    with catalog_path.open(encoding="utf-8") as fh:
        raw = json.load(fh)

    datasets = [normalize_dataset(ds) for ds in raw.get("datasets", [])]
    datasets.sort(key=lambda d: (d["domain"], d["dataset"]))

    return {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_repo": SOURCE_REPO,
        "source_generated": raw.get("generated"),
        "dataset_count": len(datasets),
        "datasets": datasets,
    }


def main() -> int:
    catalog = build_catalog()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as fh:
        json.dump(catalog, fh, indent=2)
    log.info(
        "Wrote %s with %d datasets.", OUTPUT_PATH, catalog["dataset_count"]
    )
    for ds in catalog["datasets"]:
        log.info(
            "  %-22s domain=%-9s format=%-15s vintages=%d",
            ds["dataset"],
            ds["domain"],
            ds["format"],
            len(ds["vintages"]),
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
