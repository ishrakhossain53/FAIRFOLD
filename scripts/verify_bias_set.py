#!/usr/bin/env python3
"""Validate every versioned bias test set's internal consistency.

    python3 scripts/verify_bias_set.py [--version v1.0.1]

The set is only worth anything if it is self-consistent, and self-consistency is
checkable: every expected term must exist in the term list, no must-not-flag case
may contain a term, category counts must match the targets in Arch Doc 7.4.3, and
the manifest's keyword_list_sha must match the file it hashes.

Versions are immutable, so EVERY directory is checked, not just the newest. A
stale older version that nobody maintains is exactly the thing a reader would
trust by accident.

What this deliberately does NOT check is whether the bias pass works -- that is
`tests/bias/test_bias_pass.py`. This proves the fixtures are coherent; that proves
the pass behaves. Exits non-zero on any failure so it runs in CI.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SET = ROOT / "tests" / "bias"

# Categories 1-10, fixed in Arch Doc 7.4.3. These are the spec, not a description
# of whatever happens to be in the files.
BASE_TARGETS = {
    "gendered_club_role": 12,
    "institution_gender_signal": 8,
    "age_reference": 8,
    "nationality_origin_proxy": 6,
    "family_status": 6,
    "disability_health": 4,
    "photo_appearance": 4,
    "uncited_vague_rationale": 10,
    "legitimate_skill_match": 12,
    "necessary_context": 6,
}

# Categories 11-13, added with the numeric rule layer in v1.0.1 to close LIM-001
# (no numeric age) and LIM-002 (no graduation-year proximity).
NUMERIC_TARGETS = {
    "numeric_age": 9,
    "graduation_year_proximity": 8,
    "numeric_near_miss": 10,
}

#: Versions that predate the numeric layer and therefore lack 11-13.
VERSIONS_WITHOUT_NUMERIC = {"v1.0.0"}

MUST_NOT_FLAG_CATEGORIES = {
    "legitimate_skill_match",
    "necessary_context",
    "numeric_near_miss",
}


def targets_for(version: str) -> dict[str, int]:
    if version in VERSIONS_WITHOUT_NUMERIC:
        return dict(BASE_TARGETS)
    return {**BASE_TARGETS, **NUMERIC_TARGETS}


def normalise(text: str) -> str:
    """Fold typographic apostrophes so 'women's' does not miss 'women’s'."""
    return (
        text.lower()
        .replace("’", "'")
        .replace("ʼ", "'")
        .replace("‘", "'")
    )


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

    for name in ("manifest.json", "keyword_terms.json", "proxy_cases.jsonl",
                 "negative_cases.jsonl", "rationale_cases.jsonl"):
        if not (d / name).exists():
            r.check(False, f"{version}: {name} is missing")
            return

    terms_doc = json.loads((d / "keyword_terms.json").read_text(encoding="utf-8"))
    manifest = json.loads((d / "manifest.json").read_text(encoding="utf-8"))

    all_terms: dict[str, str] = {}
    for group, values in terms_doc["terms"].items():
        for t in values:
            all_terms[t] = group

    proxy = load_jsonl(d / "proxy_cases.jsonl")
    negative = load_jsonl(d / "negative_cases.jsonl")
    rationale = load_jsonl(d / "rationale_cases.jsonl")
    cases = proxy + negative + rationale

    targets = targets_for(version)
    must_not_flag_categories = {
        c for c in targets if c in MUST_NOT_FLAG_CATEGORIES
    }

    # --- identity ---------------------------------------------------------
    ids = [c["id"] for c in cases]
    dupes = [k for k, v in Counter(ids).items() if v > 1]
    r.check(not dupes, f"{version}: case ids are unique", ", ".join(dupes) or f"{len(ids)} cases")

    required = {"id", "category", "text", "must_flag", "expected_terms", "note"}
    missing = [c.get("id", "?") for c in cases if not required <= set(c)]
    r.check(not missing, f"{version}: every case has all required fields", ", ".join(missing) or "ok")

    # --- spec conformance -------------------------------------------------
    counts = Counter(c["category"] for c in cases)
    bad = [f"{k}: {counts[k]} != {v}" for k, v in targets.items() if counts[k] != v]
    unknown = set(counts) - set(targets)
    r.check(not bad, f"{version}: category counts match the spec", "; ".join(bad) or "ok")
    r.check(not unknown, f"{version}: no categories outside the spec", ", ".join(sorted(unknown)) or "ok")

    wrong_flag = [
        c["id"] for c in cases
        if c["must_flag"] == (c["category"] in must_not_flag_categories)
    ]
    r.check(not wrong_flag, f"{version}: must_flag agrees with the category's definition",
            ", ".join(wrong_flag) or "ok")

    # --- numeric rules declared where the categories exist ------------------
    has_numeric = "numeric_age" in targets
    rules = terms_doc.get("numeric_rules", {})
    rule_families = {k for k in rules if not k.startswith("_") and isinstance(rules[k], dict)}
    if has_numeric:
        r.check(bool(rule_families), f"{version}: numeric_rules declared",
                ", ".join(sorted(rule_families)) or "MISSING")
        r.check(manifest.get("rules_layer") is True,
                f"{version}: manifest records the rules layer")
    else:
        r.check(not rule_families, f"{version}: no numeric rules (pre-numeric-layer version)",
                ", ".join(sorted(rule_families)) or "ok")

    # --- terms exist ------------------------------------------------------
    known = {normalise(t) for t in all_terms}
    rule_ids = {
        rid
        for fam in rules.values() if isinstance(fam, dict)
        for rid in fam
        if not rid.startswith("_") and isinstance(fam[rid], dict)
    }
    unknown_terms = [
        f"{c['id']}->{t!r}"
        for c in cases
        for t in c["expected_terms"]
        if normalise(t) not in known and t not in rule_ids
    ]
    r.check(not unknown_terms, f"{version}: every expected_terms entry is a declared term or rule",
            "; ".join(unknown_terms) or f"{len(all_terms)} terms, {len(rule_ids)} rules")

    # --- the crucial one: negatives must be clean -------------------------
    # A must-not-flag case containing a term is a contradiction in the fixture:
    # the pass cannot both be required to flag nothing and have something to flag.
    terms_norm = {normalise(t): t for t in all_terms}
    polluted = []
    for c in negative:
        hay = normalise(c["text"])
        hits = sorted(orig for norm, orig in terms_norm.items() if norm in hay)
        if hits:
            polluted.append(f"{c['id']} contains {hits}")
    r.check(not polluted, f"{version}: no must-not-flag case contains a term in the list",
            "; ".join(polluted) or f"{len(negative)} negatives clean")

    # --- positives must actually carry their terms (phrases only) ---------
    # Rule-backed cases are checked by the pass suite, which can evaluate a
    # regex and a recency window; a substring test would be meaningless here.
    absent = []
    for c in cases:
        if not c["must_flag"]:
            continue
        hay = normalise(c["text"])
        missing_t = [t for t in c["expected_terms"]
                     if normalise(t) in known and normalise(t) not in hay]
        if missing_t:
            absent.append(f"{c['id']} missing {missing_t}")
    r.check(not absent, f"{version}: every phrase-backed must-flag case contains its term",
            "; ".join(absent) or "ok")

    untagged = [
        c["id"] for c in cases
        if c["must_flag"] and c["category"] not in must_not_flag_categories
        and not c["expected_terms"]
    ]
    r.check(not untagged, f"{version}: every must-flag case declares at least one expected term",
            ", ".join(untagged) or "ok")

    # --- manifest ---------------------------------------------------------
    sha = hashlib.sha256((d / "keyword_terms.json").read_bytes()).hexdigest()
    r.check(manifest.get("keyword_list_sha") == sha,
            f"{version}: manifest keyword_list_sha matches keyword_terms.json",
            f"manifest={str(manifest.get('keyword_list_sha'))[:16]}... actual={sha[:16]}...")
    r.check(manifest.get("version") == version.lstrip("v"),
            f"{version}: manifest version matches the directory", str(manifest.get("version")))
    r.check(manifest.get("case_count") == len(cases),
            f"{version}: manifest case_count matches the files",
            f"manifest={manifest.get('case_count')} actual={len(cases)}")

    # --- exclusions and limitations ---------------------------------------
    negative_ids = {c["id"] for c in negative}
    dangling = [
        e["term"] for e in terms_doc.get("deliberately_excluded", [])
        if e.get("caught_by") not in negative_ids
    ]
    r.check(not dangling, f"{version}: every excluded term names an existing negative case",
            ", ".join(dangling) or f"{len(terms_doc.get('deliberately_excluded', []))} exclusions")

    lims = terms_doc.get("known_limitations", [])
    unaccounted = [
        l.get("id", "?") for l in lims
        if not (l.get("planned") or l.get("status"))
    ]
    r.check(not unaccounted, f"{version}: all {len(lims)} known limitations are scheduled or decided",
            ", ".join(unaccounted) or "ok")

    decided = [l for l in lims if l.get("status")]
    closed = [l for l in lims if l.get("severity") == "closed"]
    if decided:
        r.note(f"{len(decided)} of {len(lims)} limitations closed by decision: "
               f"{', '.join(l['id'] for l in decided)}")
    if closed:
        r.note(f"{len(closed)} closed by fix in this version: "
               f"{', '.join(l['id'] for l in closed)}")
    r.check(all(l.get("severity") for l in lims),
            f"{version}: every limitation records a severity")

    measured = manifest.get("measured")
    if measured is False:
        r.note("pass rate unmeasured (no implementation at this version)")
    else:
        r.note(f"measured {measured.get('date')}: {measured.get('flagged')}/{measured.get('cases')} "
               f"flagged, recall {measured.get('recall_must_flag')}, "
               f"{measured.get('false_positives')} false positives")

    if not r.failures:
        r.pass_(f"{version} is internally consistent", f"{len(cases)} cases")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--version", help="check one version, default: all")
    args = ap.parse_args()

    print("Bias test set consistency check")
    versions = sorted(
        (p.name for p in SET.glob("v*") if (p / "keyword_terms.json").exists()),
        key=lambda v: [int(x) for x in v.lstrip("v").split(".")],
    )
    if not versions:
        print(f"no versioned bias test set under {SET}")
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