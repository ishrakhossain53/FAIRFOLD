"""Reference data that has no table in the schema.

Complete Doc §C.8.3 seeds four things: Django groups, the skill taxonomy, score
bands, and countries/industries. Only **two** of those are tables in Arch Doc
§5.1 — `auth_group` (Django's own) and `skills`. There is no `score_bands`,
`countries` or `industries` table.

Three tables were **not** added to close that gap, deliberately. A table implies
something this product does not do: no user edits these values at runtime,
nothing joins to them, and they never vary per deployment. Schema designed to
match a fixture list rather than to a requirement is how a 24-table schema
becomes a 27-table one that nobody chose.

`SCORE_BANDS` is the borderline case and is deliberately a constant: design.md
§3.4 calls the bands "provisional" pending a calibrated model. When they are
calibrated, the change is an edit to this file plus a `calibrated: True` flip,
which a reviewer sees as a two-line diff. A table would make the same change a
data migration — heavier and slower to review for no gain.

**The trade-off, stated plainly:** because these are constants, changing a
threshold needs a deploy rather than an admin edit. That is the right cost while
the bands are uncalibrated and the wrong one afterwards. Revisit if a
non-engineer ever needs to change them.

What the seed command does with this module: calls :func:`validate`, so an empty
or inconsistent list fails at ``manage.py seed`` rather than producing an empty
``<select>`` in a form.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Score bands (design.md §3.4 — PROVISIONAL, not calibrated)
# ---------------------------------------------------------------------------
# `calibrated=False` is load-bearing: the UI must not present these as measured.
# REQ-FR-031 requires every score to be explainable, and a band presented as
# authoritative is a claim the product cannot currently back.

SCORE_BANDS: tuple[dict[str, Any], ...] = (
    {
        "label": "weak_match",
        "min_score": 0.00,
        "max_score": 0.45,
        "description": "Not matched",
        "calibrated": False,
    },
    {
        "label": "partial_match",
        "min_score": 0.45,
        "max_score": 0.65,
        "description": "Review the evidence",
        "calibrated": False,
    },
    {
        "label": "good_match",
        "min_score": 0.65,
        "max_score": 0.80,
        "description": "Worth a look",
        "calibrated": False,
    },
    {
        "label": "strong_match",
        "min_score": 0.80,
        "max_score": 1.00,
        "description": "Consider for interview",
        "calibrated": False,
    },
)


def band_for(score: float) -> dict[str, Any] | None:
    """Return the band containing ``score``, or ``None`` if out of range.

    Bounds are inclusive at the lower edge and exclusive at the upper one, so
    0.80 lands in ``strong_match`` and not in both. Overlapping bands would make
    the label on a given score ambiguous, which is precisely the kind of
    unexplained output REQ-FR-031 forbids.
    """
    for band in SCORE_BANDS:
        if band["min_score"] <= score < band["max_score"]:
            return band
    return None


def band_labels() -> tuple[str, ...]:
    """Band labels in ascending score order."""
    return tuple(str(band["label"]) for band in SCORE_BANDS)


def is_calibrated() -> bool:
    """True only once every band has been calibrated against real data.

    A view asserting ``not is_calibrated()`` should say so on screen. The
    alternative — showing provisional thresholds as fact — is the failure this
    flag exists to prevent.
    """
    return all(bool(band["calibrated"]) for band in SCORE_BANDS)


# ---------------------------------------------------------------------------
# Countries — ISO 3166-1 alpha-2
# ---------------------------------------------------------------------------
# BD first: the PRD's primary market is Bangladesh, so the common case is the
# first option rather than the twelfth.

COUNTRIES: tuple[tuple[str, str], ...] = (
    ("BD", "Bangladesh"),
    ("IN", "India"),
    ("PK", "Pakistan"),
    ("GB", "United Kingdom"),
    ("US", "United States"),
    ("CA", "Canada"),
    ("AE", "United Arab Emirates"),
    ("SG", "Singapore"),
    ("MY", "Malaysia"),
    ("AU", "Australia"),
    ("DE", "Germany"),
    ("NL", "Netherlands"),
)


# ---------------------------------------------------------------------------
# Industries
# ---------------------------------------------------------------------------
# Bangladesh's sectors lead. A generic Western list would make the two markets
# this product actually serves the ones needing scrolling.

INDUSTRIES: tuple[str, ...] = (
    "Software and IT",
    "Financial Services and Banking",
    "Telecommunications",
    "Garments and Textiles",
    "Pharmaceuticals",
    "Education and EdTech",
    "Healthcare and Diagnostics",
    "Engineering and Construction",
    "E-commerce and Retail",
    "Logistics and Supply Chain",
    "Agriculture",
    "Energy and Utilities",
    "Non-profit and NGO",
    "Media and Entertainment",
    "Hospitality and Tourism",
)


def validate() -> None:
    """Raise ``ValueError`` if the reference data is unusable.

    Called by the seed command and by tests. A missing band makes
    :func:`band_for` return ``None`` for every score and a missing industry
    renders an empty select — both failures far from the step where the mistake
    was made, and both silent, which is why they are checked.
    """
    if not SCORE_BANDS:
        raise ValueError("SCORE_BANDS is empty; every match score needs a band")

    if list(SCORE_BANDS) != sorted(SCORE_BANDS, key=lambda b: b["min_score"]):
        raise ValueError("SCORE_BANDS must be declared in ascending score order")

    labels = band_labels()
    if len(set(labels)) != len(labels):
        raise ValueError(f"duplicate band labels: {labels}")

    for lower, upper in zip(SCORE_BANDS, SCORE_BANDS[1:]):
        if lower["max_score"] != upper["min_score"]:
            raise ValueError(
                f"gap or overlap between {lower['label']!r} and {upper['label']!r}: "
                f"ends at {lower['max_score']}, next starts at {upper['min_score']}"
            )

    first, last = SCORE_BANDS[0], SCORE_BANDS[-1]
    if first["min_score"] != 0.0 or last["max_score"] != 1.00:
        raise ValueError(
            f"bands must span exactly 0.0 to 1.00; they span "
            f"{first['min_score']} to {last['max_score']}"
        )

    for band in SCORE_BANDS:
        if not band["description"]:
            raise ValueError(f"band {band['label']!r} has no description; the UI shows it")

    if not COUNTRIES:
        raise ValueError("COUNTRIES is empty; job location filters need options")
    bad_codes = [code for code, _ in COUNTRIES if len(code) != 2 or not code.isupper()]
    if bad_codes:
        raise ValueError(f"country codes must be ISO 3166-1 alpha-2: {bad_codes}")
    if len({name for _, name in COUNTRIES}) != len(COUNTRIES):
        raise ValueError("duplicate country names")

    if not INDUSTRIES:
        raise ValueError("INDUSTRIES is empty; employer onboarding needs options")
    if len(set(INDUSTRIES)) != len(INDUSTRIES):
        raise ValueError("duplicate industry names")