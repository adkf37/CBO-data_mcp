"""
dates.py — Normalize the heterogeneous CBO ``date`` values.

The official datasets use several date conventions in a single ``date`` column:

- Quarterly economic:  ``2023q1``
- Annual economic:     ``2023`` (basis inferred from the file: fiscal vs calendar)
- Budget fiscal year:  ``FY2026``
- Budget calendar year: ``CY2026``

This module turns any of those into a normalized ``(year, quarter, basis, freq)``
tuple so the DuckDB tables can be range-filtered and ordered consistently.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

_QUARTER_RE = re.compile(r"^(\d{4})[qQ]([1-4])$")
_FY_RE = re.compile(r"^FY(\d{4})$", re.IGNORECASE)
_CY_RE = re.compile(r"^CY(\d{4})$", re.IGNORECASE)
_YEAR_RE = re.compile(r"^(\d{4})$")


@dataclass(frozen=True)
class Period:
    year: Optional[int]
    quarter: Optional[int]
    basis: str  # 'quarterly' | 'fiscal' | 'calendar' | 'unknown'
    freq: str  # 'quarterly' | 'annual'


def parse_period(date_str: object, default_basis: str = "annual") -> Period:
    """Parse a CBO ``date`` token into a normalized :class:`Period`.

    ``default_basis`` is taken from the file's ``date_basis`` (e.g. ``fiscal``
    or ``calendar``) and is used only when the token itself is ambiguous (a bare
    ``YYYY``).
    """
    s = "" if date_str is None else str(date_str).strip()

    m = _QUARTER_RE.match(s)
    if m:
        return Period(int(m.group(1)), int(m.group(2)), "quarterly", "quarterly")

    m = _FY_RE.match(s)
    if m:
        return Period(int(m.group(1)), None, "fiscal", "annual")

    m = _CY_RE.match(s)
    if m:
        return Period(int(m.group(1)), None, "calendar", "annual")

    m = _YEAR_RE.match(s)
    if m:
        basis = default_basis if default_basis in {"fiscal", "calendar"} else "annual"
        return Period(int(m.group(1)), None, basis, "annual")

    return Period(None, None, "unknown", "annual")
