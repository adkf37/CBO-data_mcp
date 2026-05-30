#!/usr/bin/env python3
"""
build_official_db.py — Phase Official-02: Build the official CBO DuckDB database

Thin CLI wrapper around ``src.official_data.build.build_database``.  Reads the
vendored CSVs (``data/cbo_official/``) and the normalized catalog
(``data/official_catalog.json``) and writes ``data/cbo_official.duckdb``.

Usage:
    python scripts/build_official_db.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.official_data.build import build_database  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def main() -> int:
    stats = build_database()
    log.info("DuckDB build complete. Row counts:")
    for table, n in stats.items():
        log.info("  %-18s %d rows", table, n)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
