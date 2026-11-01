"""Country and city/district reference data for the location selects.

The country list and the city list are derived from the same GeoNames source and
share the same ISO 3166-1 alpha-2 key, so a city can never be attached to a
country the form does not offer. Neither list is a table (Arch Doc §5.1 has no
``countries`` or ``cities`` table); see ``core/reference.py`` for why.

``cities.json`` is loaded lazily and cached for the process. The HTMX endpoint
reads one country at a time, so the full 1.5 MB file is parsed once rather than
per request.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from core.geo.countries import COUNTRIES

_COUNTRY_NAMES: dict[str, str] = dict(COUNTRIES)


def country_name(code: str) -> str:
    """Return the display name for an ISO 3166-1 alpha-2 code, or ``""``."""
    return _COUNTRY_NAMES.get(code, "")


@lru_cache(maxsize=1)
def _cities() -> dict[str, list[dict[str, str]]]:
    path = Path(__file__).with_name("cities.json")
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def cities_for(code: str) -> tuple[dict[str, str], ...]:
    """Return the city/district rows for a country code, in display order.

    Each row is ``{"name": ..., "region": ...}``. The region is the first-level
    administrative area (division, state or nation) and is only used to make two
    same-named places distinguishable in the select; the stored job value is the
    name alone.
    """
    return tuple(_cities().get(code, ()))
