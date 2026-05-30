"""Tests for the official DuckDB build (src/official_data/build.py)."""

from __future__ import annotations

import duckdb


def test_build_creates_expected_tables(official_db):
    db_path, _ = official_db
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        tables = {r[0] for r in con.execute("SHOW TABLES").fetchall()}
    finally:
        con.close()
    assert {"economic_long", "budget_long", "spending_detail", "demographic",
            "variable_catalog"} <= tables


def test_long_tables_have_rows(official_db):
    db_path, _ = official_db
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        eco = con.execute("SELECT COUNT(*) FROM economic_long").fetchone()[0]
        bud = con.execute("SELECT COUNT(*) FROM budget_long").fetchone()[0]
        var = con.execute("SELECT COUNT(*) FROM variable_catalog").fetchone()[0]
    finally:
        con.close()
    assert eco > 0
    assert bud > 0
    assert var >= 3  # unemployment_rate, real_gdp, deficit


def test_estimate_type_preserved(official_db):
    db_path, _ = official_db
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        row = con.execute(
            "SELECT estimate_type FROM economic_long "
            "WHERE variable='unemployment_rate' AND year=2023 AND vintage='2026-02'"
        ).fetchone()
    finally:
        con.close()
    assert row[0] == "actual"


def test_spending_detail_year_derived(official_db):
    db_path, _ = official_db
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        years = {r[0] for r in con.execute("SELECT year FROM spending_detail").fetchall()}
    finally:
        con.close()
    assert 2026 in years
