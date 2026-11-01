"""Generate the country options and city/district list used by the job form.

Source data (GeoNames, CC BY 4.0 — https://www.geonames.org/export/):

* ``countryInfo.txt``        ISO 3166-1 alpha-2 codes and country names
* ``admin1CodesASCII.txt``   first-level region names (division/state/nation)
* ``cities15000.zip``        populated places with at least 15,000 people

Run it with network access::

    .venv/bin/python scripts/build_city_data.py

It writes ``core/geo/countries.py`` and ``core/geo/cities.json``. A cached copy
of the three downloads can be reused with ``--source-dir`` (the directory must
contain ``countryInfo.txt``, ``admin1CodesASCII.txt`` and ``cities15000.txt``,
the unzipped form).

The output is committed. CI does not run this script: the form must work
offline and the list must not change under a test because a remote file changed.
Re-run it when a deliberate refresh is wanted, and review the diff.
"""

from __future__ import annotations

import argparse
import json
import tempfile
import urllib.request
import zipfile
from collections import defaultdict
from datetime import date
from pathlib import Path

BASE_URL = "https://download.geonames.org/export/dump"
COUNTRIES_URL = f"{BASE_URL}/countryInfo.txt"
ADMIN1_URL = f"{BASE_URL}/admin1CodesASCII.txt"
CITIES_URL = f"{BASE_URL}/cities15000.zip"

# GeoNames still ships two codes that ISO 3166-1 retired. Offering "Serbia and
# Montenegro" or "Netherlands Antilles" in a 2026 job form would be a mistake.
RETIRED = {"AN", "CS"}

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "core" / "geo"
COUNTRIES_FILE = OUT_DIR / "countries.py"
CITIES_FILE = OUT_DIR / "cities.json"


def download(url: str, destination: Path) -> None:
    print(f"downloading {url}")
    with urllib.request.urlopen(
        url, timeout=120
    ) as response:  # noqa: S310  # nosec B310
        destination.write_bytes(response.read())


def ensure_source(source_dir: Path) -> None:
    source_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "countryInfo.txt": COUNTRIES_URL,
        "admin1CodesASCII.txt": ADMIN1_URL,
    }
    for name, url in files.items():
        if not (source_dir / name).is_file():
            download(url, source_dir / name)
    cities = source_dir / "cities15000.txt"
    if not cities.is_file():
        archive = source_dir / "cities15000.zip"
        download(CITIES_URL, archive)
        with zipfile.ZipFile(archive) as bundle:
            bundle.extract("cities15000.txt", source_dir)
    for name in (*files, "cities15000.txt"):
        if not (source_dir / name).is_file():
            raise SystemExit(f"missing source file: {source_dir / name}")


def read_countries(source_dir: Path) -> list[tuple[str, str]]:
    countries: set[tuple[str, str]] = set()
    with (source_dir / "countryInfo.txt").open(encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("#") or not line.strip():
                continue
            fields = line.rstrip("\n").split("\t")
            if len(fields) < 5:
                continue
            code, name = fields[0].strip(), fields[4].strip()
            if len(code) == 2 and code.isalpha() and code.isupper():
                if code not in RETIRED:
                    countries.add((code, name))
    # Bangladesh first: the PRD's primary market, so the common case is the
    # first option; the rest alphabetical by name for a usable select.
    ordered = sorted(countries, key=lambda item: item[1])
    return [item for item in ordered if item[0] == "BD"] + [
        item for item in ordered if item[0] != "BD"
    ]


def read_admin1(source_dir: Path) -> dict[str, str]:
    regions: dict[str, str] = {}
    with (source_dir / "admin1CodesASCII.txt").open(encoding="utf-8") as handle:
        for line in handle:
            fields = line.rstrip("\n").split("\t")
            if len(fields) >= 2:
                regions[fields[0]] = fields[1]
    return regions


def read_cities(
    source_dir: Path, countries: list[tuple[str, str]]
) -> dict[str, list[dict[str, str]]]:
    valid = {code for code, _ in countries}
    regions = read_admin1(source_dir)
    # (name, region) -> (population, row), so a duplicate entry keeps the larger
    # place rather than the last line in the file.
    collected: dict[str, dict[tuple[str, str], tuple[int, dict[str, str]]]] = (
        defaultdict(dict)
    )
    with (source_dir / "cities15000.txt").open(encoding="utf-8") as handle:
        for line in handle:
            fields = line.rstrip("\n").split("\t")
            if len(fields) < 15:
                continue
            country = fields[8]
            if country not in valid:
                continue
            name = fields[1].strip()
            region = regions.get(f"{country}.{fields[10]}", "")
            population = int(fields[14] or 0)
            key = (name, region)
            current = collected[country].get(key)
            if current is None or population > current[0]:
                collected[country][key] = (
                    population,
                    {"name": name, "region": region},
                )

    result: dict[str, list[dict[str, str]]] = {}
    for country, rows in collected.items():
        result[country] = [
            row
            for _, row in sorted(
                rows.values(), key=lambda item: (item[1]["region"], item[1]["name"])
            )
        ]
    return dict(sorted(result.items()))


def write_countries(countries: list[tuple[str, str]]) -> None:
    lines = [
        '"""ISO 3166-1 alpha-2 country options (GeoNames countryInfo.txt).',
        "",
        "Generated by scripts/build_city_data.py on "
        f"{date.today().isoformat()}. Do not edit by hand.",
        "Source data: GeoNames, CC BY 4.0 (https://www.geonames.org/export/).",
        "Bangladesh is first because the PRD's primary market is Bangladesh.",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "COUNTRIES: tuple[tuple[str, str], ...] = (",
    ]
    for code, name in countries:
        escaped = name.replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'    ("{code}", "{escaped}"),')
    lines.append(")")
    lines.append("")
    COUNTRIES_FILE.write_text("\n".join(lines), encoding="utf-8")


def write_cities(cities: dict[str, list[dict[str, str]]]) -> None:
    CITIES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with CITIES_FILE.open("w", encoding="utf-8") as handle:
        json.dump(cities, handle, ensure_ascii=False, separators=(",", ":"))
        handle.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-dir",
        type=Path,
        help="directory holding the three GeoNames files (default: download)",
    )
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if args.source_dir:
        source_dir = args.source_dir
    else:
        source_dir = Path(tempfile.mkdtemp(prefix="fairfold-geonames-"))
    ensure_source(source_dir)

    countries = read_countries(source_dir)
    cities = read_cities(source_dir, countries)
    write_countries(countries)
    write_cities(cities)

    print(
        f"wrote {COUNTRIES_FILE.relative_to(ROOT)} ({len(countries)} countries) and "
        f"{CITIES_FILE.relative_to(ROOT)} "
        f"({sum(len(rows) for rows in cities.values())} places)"
    )


if __name__ == "__main__":
    main()
