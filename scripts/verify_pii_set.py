#!/usr/bin/env python3
"""Validate every versioned PII test set's internal consistency.

    python3 scripts/verify_pii_set.py [--version v1.0.0]

Mirrors ``scripts/verify_bias_set.py`` for ``tests/pii/`` (REQ-FR-011,
REQ-FR-057, batch 2.6). Versions are immutable, so every ``v*`` directory is
checked:

* ``manifest.json`` and ``resumes.jsonl`` exist and parse as JSON.
* Case IDs are unique and every case carries ``id``, ``profile``, ``text``,
  ``pii_spans``, ``keep_spans``, and ``note``.
* Every ``pii_span`` names a known category and its ``value`` occurs verbatim
  in the case's ``text``.
* Every ``keep_span`` is non-empty and occurs verbatim in the case's ``text``.
* No ``pii_span`` value overlaps as a substring of a ``keep_span`` (or vice
  versa) within the same case — a self-contradictory case would force any
  stripper to either miss PII or fail the keep-set check.
* ``manifest.json`` counts (``case_count``, ``pii_span_count``,
  ``keep_span_count``, ``category_counts``) and ``dataset_sha`` match
  ``resumes.jsonl``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SET = ROOT / "tests" / "pii"

ALLOWED_CATEGORIES = {
    "name",
    "email",
    "phone",
    "address",
    "national_id",
    "url",
    "age_date",
    "institution",
    "employer",
    "photo",
}


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{path}:{line_no} is not valid JSON: {exc}") from exc
    return rows


class Result:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.notes: list[str] = []

    def check(self, ok: bool, label: str, detail: str = "") -> bool:
        if not ok:
            print(f"    FAIL  {label}" + (f" — {detail}" if detail else ""))
            self.failures.append(f"{label}: {detail}" if detail else label)
        return ok

    def note(self, text: str) -> None:
        print(f"    NOTE  {text}")
        self.notes.append(text)

    def pass_(self, label: str, detail: str = "") -> None:
        print(f"    PASS  {label}" + (f" — {detail}" if detail else ""))


def check_version(version: str, r: Result) -> None:
    d = SET / version
    print(f"\n{'=' * 60}\n{version}\n{'=' * 60}")

    for name in ("manifest.json", "resumes.jsonl"):
        if not (d / name).exists():
            r.check(False, f"{version}: {name} is missing")
            return

    manifest = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
    cases = load_jsonl(d / "resumes.jsonl")

    ids = [c.get("id", "?") for c in cases]
    dupes = [k for k, v in Counter(ids).items() if v > 1]
    r.check(
        not dupes,
        f"{version}: case ids are unique",
        ", ".join(dupes) or f"{len(ids)} cases",
    )

    required = {"id", "profile", "text", "pii_spans", "keep_spans", "note"}
    missing = [c.get("id", "?") for c in cases if not required <= set(c)]
    r.check(
        not missing,
        f"{version}: every case has all required fields",
        ", ".join(missing) or "ok",
    )

    bad_cat: list[str] = []
    missing_pii_in_text: list[str] = []
    missing_keep_in_text: list[str] = []
    collisions: list[str] = []
    cat_counts: Counter[str] = Counter()

    for c in cases:
        cid = c["id"]
        text_low = c["text"].lower()
        for span in c["pii_spans"]:
            cat = span.get("category", "")
            val = span.get("value", "")
            cat_counts[cat] += 1
            if cat not in ALLOWED_CATEGORIES:
                bad_cat.append(f"{cid}:{cat!r}")
            if not val or val.lower() not in text_low:
                missing_pii_in_text.append(f"{cid}->{val!r}")

        for keep in c["keep_spans"]:
            if not keep or keep.lower() not in text_low:
                missing_keep_in_text.append(f"{cid}->{keep!r}")

        for span in c["pii_spans"]:
            pval = span.get("value", "").lower()
            if not pval:
                continue
            for keep in c["keep_spans"]:
                kval = keep.lower()
                if pval in kval or kval in pval:
                    collisions.append(f"{cid}: pii {pval!r} overlaps keep {kval!r}")

    r.check(
        not bad_cat,
        f"{version}: every pii_span category is in ALLOWED_CATEGORIES",
        "; ".join(bad_cat) or "ok",
    )
    r.check(
        not missing_pii_in_text,
        f"{version}: every pii_span value is present in its case text",
        "; ".join(missing_pii_in_text) or "ok",
    )
    r.check(
        not missing_keep_in_text,
        f"{version}: every keep_span value is present in its case text",
        "; ".join(missing_keep_in_text) or "ok",
    )
    r.check(
        not collisions,
        f"{version}: no pii_span overlaps with a keep_span in the same case",
        "; ".join(collisions) or "ok",
    )

    sha = hashlib.sha256((d / "resumes.jsonl").read_bytes()).hexdigest()
    r.check(
        manifest.get("dataset_sha") == sha,
        f"{version}: manifest dataset_sha matches resumes.jsonl",
        f"manifest={str(manifest.get('dataset_sha'))[:16]}... actual={sha[:16]}...",
    )
    r.check(
        manifest.get("version") == version.lstrip("v"),
        f"{version}: manifest version matches directory",
        str(manifest.get("version")),
    )
    r.check(
        manifest.get("case_count") == len(cases),
        f"{version}: manifest case_count matches resumes.jsonl",
        f"manifest={manifest.get('case_count')} actual={len(cases)}",
    )

    total_pii = sum(cat_counts.values())
    total_keep = sum(len(c["keep_spans"]) for c in cases)
    r.check(
        manifest.get("pii_span_count") == total_pii,
        f"{version}: manifest pii_span_count matches resumes.jsonl",
        f"manifest={manifest.get('pii_span_count')} actual={total_pii}",
    )
    r.check(
        manifest.get("keep_span_count") == total_keep,
        f"{version}: manifest keep_span_count matches resumes.jsonl",
        f"manifest={manifest.get('keep_span_count')} actual={total_keep}",
    )

    manifest_cats = manifest.get("category_counts", {})
    cat_mismatches = [
        f"{cat}: manifest={manifest_cats.get(cat)} actual={cat_counts[cat]}"
        for cat in sorted(ALLOWED_CATEGORIES | set(manifest_cats))
        if manifest_cats.get(cat) != cat_counts[cat]
    ]
    r.check(
        not cat_mismatches,
        f"{version}: manifest category_counts match resumes.jsonl",
        "; ".join(cat_mismatches) or "ok",
    )

    baseline = manifest.get("baseline")
    if isinstance(baseline, dict):
        r.note(
            f"baseline ({baseline.get('date')}): recall {baseline.get('recall')}, "
            f"keep_survival {baseline.get('keep_survival')} over {baseline.get('cases')} cases"
        )

    measured = manifest.get("measured")
    if isinstance(measured, dict):
        r.note(
            f"measured ({measured.get('date')}): recall {measured.get('recall'):.4f} "
            f"({measured.get('redacted_pii_spans')}/{measured.get('total_pii_spans')}), "
            f"precision {measured.get('precision'):.4f}, "
            f"keep_survival {measured.get('keep_survival'):.4f}"
        )

    if not r.failures:
        r.pass_(
            f"{version} is internally consistent",
            f"{len(cases)} cases, {total_pii} PII spans, {total_keep} keep spans",
        )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--version", help="check one version, default: all")
    args = ap.parse_args()

    print("PII test set consistency check")
    versions = sorted(
        (p.name for p in SET.glob("v*") if (p / "resumes.jsonl").exists()),
        key=lambda v: [int(x) for x in v.lstrip("v").split(".")],
    )
    if not versions:
        print(f"no versioned PII test set under {SET}")
        return 1
    if args.version:
        versions = [args.version]

    r = Result()
    for v in versions:
        check_version(v, r)

    print(f"\n{'=' * 60}")
    if r.failures:
        print(f"{len(r.failures)} FAILURE(S):")
        for f in r.failures:
            print(f"  - {f}")
        return 1
    print(f"All {len(versions)} version(s) internally consistent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
