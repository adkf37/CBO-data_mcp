#!/usr/bin/env python3
"""
catalog_data.py — Task 01: Catalog CBO Data Repository

Clones (or updates) the CBO baseline detail data repository into data/raw/,
then produces data/catalog.json with a machine-readable entry for every
distinct CSV file type found in the processed dataset.

Usage:
    python scripts/catalog_data.py

Output:
    data/catalog.json   — machine-readable catalog of all file types
"""

import json
import logging
import re
import subprocess
import sys
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REPO_URL = "https://github.com/adkf37/Data_friendly_CBO_Baseline_Detail"
RAW_DIR = Path(__file__).parent.parent / "data" / "raw"
CATALOG_PATH = Path(__file__).parent.parent / "data" / "catalog.json"
PROCESSED_SUBDIR = "data/processed"
SCHEMAS_SUBDIR = "docs/schemas"

# Regex: filename stem ends with _{YYYY}_{MM} or _{YYYY}
VINTAGE_RE = re.compile(r"^(.+?)_(\d{4})(?:_(\d{2}))?$")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------


def clone_or_update(repo_url: str, target: Path) -> None:
    """Clone repo into *target* or, if it already exists, run git pull."""
    if (target / ".git").exists():
        log.info("data/raw/ already exists — running git pull …")
        try:
            subprocess.run(
                ["git", "-C", str(target), "pull", "--ff-only"],
                check=True,
                capture_output=True,
                text=True,
            )
            log.info("git pull succeeded.")
        except subprocess.CalledProcessError as exc:
            log.warning("git pull failed (%s); proceeding with existing data.", exc.stderr.strip())
    else:
        log.info("Cloning %s → %s …", repo_url, target)
        try:
            subprocess.run(
                ["git", "clone", "--depth=1", repo_url, str(target)],
                check=True,
                capture_output=True,
                text=True,
            )
            log.info("Clone succeeded.")
        except subprocess.CalledProcessError as exc:
            log.warning(
                "Clone failed (%s). Proceeding with whatever data is already in data/raw/.",
                exc.stderr.strip(),
            )


# ---------------------------------------------------------------------------
# Vintage extraction
# ---------------------------------------------------------------------------


def extract_file_type_and_vintage(stem: str) -> tuple[str, str | None]:
    """
    Split a CSV stem into (file_type, vintage).

    Examples
    --------
    "medicaid_2026_02"   → ("medicaid",   "2026-02")
    "aatf_0_2023_05"     → ("aatf_0",     "2023-05")
    "snap_2019_05"       → ("snap",       "2019-05")
    "premium_tax_credit_2024_07" → ("premium_tax_credit", "2024-07")
    """
    m = VINTAGE_RE.match(stem)
    if not m:
        return stem, None
    file_type = m.group(1)
    year = m.group(2)
    month = m.group(3)
    vintage = f"{year}-{month}" if month else year
    return file_type, vintage


# ---------------------------------------------------------------------------
# Schema parsing
# ---------------------------------------------------------------------------

# Common column schema shared by all datasets (from docs/schemas/README.md)
_COMMON_COLUMNS = [
    {"name": "program", "type": "string",
     "description": "CBO program name inferred from the source workbook filename."},
    {"name": "category", "type": "string",
     "description": "Line-item label as it appears in the source worksheet after header normalization."},
    {"name": "fiscal_year", "type": "integer",
     "description": "Federal fiscal year to which the value applies (Oct 1 – Sep 30)."},
    {"name": "value", "type": "float",
     "description": "Parsed numeric value from the source cell."},
    {"name": "unit", "type": "string",
     "description": "Unit of measure for the value column, sourced from the parse plan."},
    {"name": "source_file", "type": "string",
     "description": "Original CBO workbook filename from data/raw/."},
    {"name": "source_sheet", "type": "string",
     "description": "Worksheet name within the source workbook."},
    {"name": "is_total", "type": "boolean",
     "description": "true if the category label contains the word 'total' or 'subtotal'."},
]


def parse_schema_description(md_path: Path) -> str:
    """Extract the 'Purpose' section body from a per-dataset schema markdown file."""
    try:
        text = md_path.read_text(encoding="utf-8")
    except OSError:
        return ""

    # Look for "## Purpose" section and grab the text up to the next "##"
    purpose_re = re.compile(r"##\s+Purpose\s*\n+(.*?)(?=\n##|\Z)", re.DOTALL | re.IGNORECASE)
    m = purpose_re.search(text)
    if m:
        # Strip markdown blockquotes (>), strip leading/trailing whitespace
        raw = m.group(1).strip()
        cleaned = re.sub(r"^>\s?", "", raw, flags=re.MULTILINE).strip()
        return cleaned
    return ""


def columns_from_csv(csv_path: Path) -> list[dict]:
    """
    Return column metadata by reading the CSV header row only.
    Falls back to _COMMON_COLUMNS when the file is unreadable.
    """
    try:
        df = pd.read_csv(csv_path, nrows=0)
        return [{"name": col, "type": "unknown"} for col in df.columns]
    except Exception:
        return list(_COMMON_COLUMNS)


# ---------------------------------------------------------------------------
# Main cataloging logic
# ---------------------------------------------------------------------------


def build_catalog(raw_dir: Path) -> list[dict]:
    """
    Walk raw_dir/data/processed, group CSVs by file_type, and assemble catalog entries.
    """
    processed_dir = raw_dir / PROCESSED_SUBDIR
    schemas_dir = raw_dir / SCHEMAS_SUBDIR

    if not processed_dir.exists():
        log.warning("Processed data directory not found: %s", processed_dir)
        return []

    # Collect all CSV files
    csv_files = sorted(processed_dir.glob("*.csv"))
    log.info("Found %d CSV files in %s", len(csv_files), processed_dir)

    # Project root — used to compute relative paths for file_paths entries
    project_root = Path(__file__).parent.parent

    # Group by file_type
    groups: dict[str, dict] = {}
    # Keep the first Path object seen for each file_type so we can read its header
    first_csv: dict[str, Path] = {}

    for csv_path in csv_files:
        stem = csv_path.stem
        file_type, vintage = extract_file_type_and_vintage(stem)

        if file_type not in groups:
            groups[file_type] = {
                "file_type": file_type,
                "description": "",
                "columns": [],
                "vintages": [],
                "file_paths": [],
            }
            first_csv[file_type] = csv_path

        entry = groups[file_type]
        entry["file_paths"].append(str(csv_path.relative_to(project_root)))
        if vintage and vintage not in entry["vintages"]:
            entry["vintages"].append(vintage)

    # Enrich each group with schema/description info
    for file_type, entry in groups.items():
        vintages_sorted = sorted(entry["vintages"])
        entry["vintages"] = vintages_sorted

        # Try to find a matching schema markdown file for this exact file_type
        md_file: Path | None = None
        if schemas_dir.exists():
            # Filter candidates so we only accept .md files whose stem actually
            # maps back to this file_type (avoids e.g. aatf_0_*.md for aatf).
            candidates = []
            for p in sorted(schemas_dir.glob(f"{file_type}_*.md")):
                ft, _v = extract_file_type_and_vintage(p.stem)
                if ft == file_type:
                    candidates.append(p)
            if candidates:
                md_file = candidates[0]

        if md_file:
            entry["description"] = parse_schema_description(md_file)

        # Columns: read from the first available CSV for this file_type
        sample_csv = first_csv[file_type]
        entry["columns"] = columns_from_csv(sample_csv)

        if not entry["description"]:
            # Fall back to a generic description using the file_type name
            display_name = file_type.replace("_", " ").title()
            entry["description"] = (
                f"Tidy long-form CBO baseline data for the {display_name} program(s)."
            )

    catalog = sorted(groups.values(), key=lambda e: e["file_type"])
    log.info("Catalogued %d distinct file types.", len(catalog))
    return catalog


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Step 1: clone or update data/raw/
    clone_or_update(REPO_URL, RAW_DIR)

    # Step 2: build catalog
    catalog = build_catalog(RAW_DIR)

    if not catalog:
        log.error("No catalog entries produced — check that data/raw/ is populated.")
        sys.exit(1)

    if len(catalog) < 25:
        log.warning(
            "Only %d file types found; expected ≥ 25. Check data/raw/ contents.",
            len(catalog),
        )

    # Step 3: write catalog.json
    with CATALOG_PATH.open("w", encoding="utf-8") as fh:
        json.dump(catalog, fh, indent=2, ensure_ascii=False)
    log.info("Wrote %d entries to %s", len(catalog), CATALOG_PATH)


if __name__ == "__main__":
    main()
