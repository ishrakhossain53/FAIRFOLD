# Country and city reference data

`countries.py` and `cities.json` are generated, not hand-edited.

| | |
|---|---|
| Source | [GeoNames](https://www.geonames.org/export/) — `countryInfo.txt`, `admin1CodesASCII.txt`, `cities15000.zip` |
| Licence | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) — attribution is the "GeoNames" name and this link |
| Generator | `scripts/build_city_data.py` |
| Generated | 2026-10-30 |
| Contents | 250 ISO 3166-1 alpha-2 countries (Bangladesh first); 34,073 populated places with at least 15,000 people, keyed by country |

Why bundled rather than an API: the job form must work offline, the list must not
change under a test because a remote service changed, and an outbound call from
the employer form would need a new `connect-src` host in the CSP. The file is
served through the HTMX endpoint, not shipped to the browser whole.

`cities15000` only contains places above 15,000 people. A village or a small
district seat is not in the list; `address_line` is where an employer narrows the
location further. The city select is therefore a convenience, not a closed
taxonomy, and the API accepts a city string that is not in this file (the form
does not, because the browser can only submit one of its options).

To refresh:

```bash
.venv/bin/python scripts/build_city_data.py
```

The script writes both files and prints the counts. Review the diff: a renamed
country or a changed city list is a data change, not a code change. CI does not
run the generator; it only imports the committed output.
