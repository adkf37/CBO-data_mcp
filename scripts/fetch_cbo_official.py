#!/usr/bin/env python3
"""
fetch_cbo_official.py — Phase Official-01: Acquire the official US-CBO/cbo-data repo

Clones (or updates) the official Congressional Budget Office open-data repository
into ``data/cbo_official/``.  This vendored copy is the source for the normalized
catalog (``scripts/catalog_official.py``) and the DuckDB build
(``scripts/build_official_db.py``).

Usage:
    python scripts/fetch_cbo_official.py

The script degrades gracefully when offline: if the clone/pull fails it logs a
warning and leaves whatever data is already present in ``data/cbo_official/``.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REPO_URL = "https://github.com/US-CBO/cbo-data"
OFFICIAL_DIR = Path(__file__).parent.parent / "data" / "cbo_official"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------


def clone_or_update(repo_url: str, target: Path) -> bool:
    """Clone *repo_url* into *target*, or ``git pull`` if it already exists.

    Returns ``True`` if the working tree is usable afterwards (freshly cloned,
    updated, or an existing copy left in place), ``False`` only when there is no
    usable data at all.
    """
    if (target / ".git").exists():
        log.info("%s already exists — running git pull …", target)
        try:
            subprocess.run(
                ["git", "-C", str(target), "pull", "--ff-only"],
                check=True,
                capture_output=True,
                text=True,
            )
            log.info("git pull succeeded.")
        except subprocess.CalledProcessError as exc:
            log.warning(
                "git pull failed (%s); proceeding with existing data.",
                (exc.stderr or "").strip(),
            )
        return True

    target.parent.mkdir(parents=True, exist_ok=True)
    log.info("Cloning %s → %s …", repo_url, target)
    try:
        subprocess.run(
            ["git", "clone", "--depth=1", repo_url, str(target)],
            check=True,
            capture_output=True,
            text=True,
        )
        log.info("Clone succeeded.")
        return True
    except subprocess.CalledProcessError as exc:
        log.warning("Clone failed (%s).", (exc.stderr or "").strip())
        # If a partial/previous non-git copy exists with a catalog, still usable.
        if (target / "catalog.json").exists():
            log.warning("Proceeding with existing data in %s.", target)
            return True
        return False


def main() -> int:
    ok = clone_or_update(REPO_URL, OFFICIAL_DIR)
    if not ok:
        log.error(
            "No official CBO data available at %s and clone failed. "
            "Connect to the internet and re-run.",
            OFFICIAL_DIR,
        )
        return 1

    catalog = OFFICIAL_DIR / "catalog.json"
    if catalog.exists():
        log.info("Official catalog present: %s", catalog)
    else:
        log.warning("catalog.json not found under %s.", OFFICIAL_DIR)

    log.info(
        "Done. Next: run `python scripts/catalog_official.py` to build "
        "data/official_catalog.json."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
