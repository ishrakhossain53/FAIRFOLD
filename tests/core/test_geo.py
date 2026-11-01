"""The bundled country and city reference data (REQ-FR-025, batch 1.50).

The generator (`scripts/build_city_data.py`) is not run in CI, so these tests
guard the committed output: a truncated JSON file or a country tuple that no
longer matches the dataset would otherwise surface as an empty city select.
"""

from __future__ import annotations

from core.geo import COUNTRIES, cities_for, country_name


def test_country_codes_are_unique_two_letter_and_uppercase():
    codes = [code for code, _ in COUNTRIES]

    assert len(codes) == len(set(codes))
    assert all(len(code) == 2 and code.isalpha() and code.isupper() for code in codes)


def test_bangladesh_is_the_first_option():
    # The PRD's primary market; the form's common case should not require a
    # scroll past 249 other countries.
    assert COUNTRIES[0] == ("BD", "Bangladesh")


def test_retired_country_codes_are_not_offered():
    codes = {code for code, _ in COUNTRIES}

    assert "AN" not in codes  # Netherlands Antilles
    assert "CS" not in codes  # Serbia and Montenegro


def test_bangladesh_has_cities_and_dhaka_is_one():
    names = [row["name"] for row in cities_for("BD")]

    assert len(names) > 50
    assert "Dhaka" in names


def test_every_city_row_has_a_name():
    for code, _ in COUNTRIES:
        for row in cities_for(code):
            assert row["name"]
            assert set(row) == {"name", "region"}


def test_an_unknown_country_has_no_cities_and_no_name():
    assert cities_for("ZZ") == ()
    assert country_name("ZZ") == ""
    assert country_name("BD") == "Bangladesh"
