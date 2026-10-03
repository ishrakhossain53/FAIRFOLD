#!/usr/bin/env python3
"""Validate the versioned bias test set's internal consistency.

    python3 scripts/verify_bias_set.py

The set is only worth anything if it is self-consistent, and self-consistency is
checkable: every expected term must exist in the term list, no must-not-flag case
may contain a term, category counts must match the targets in Arch Doc 7.4, and
the manifest's keyword_list_sha must match the file it hashes.

What this deliberately does NOT check is whether the bias pass works. There is no
implementation yet (the repo has no source). This proves the fixture set is
coherent; the pass rate claim waits for the pass.

Exits non-zero on any failure so it can run in CI alongside verify_docs.py.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SET = ROOT / "tests" / "bias"
VERSION = "v1.0.0"
D = SET / VERSION

# The category targets fixed in Arch Doc 7.4.3. These are the spec, not a
# description of whatever happens to be in the files.
TARGETS = {
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
MUST_FLAG_CATEGORIES = set(TARGETS) - {"legitimate_skill_match", "necessary_context"}

# Categories 1-8 carry proxy phrases. 9-10 are must-not-flag by definition.
FLAG_RATE_CATEGORIES = MUST_FLAG_CATEGORIES


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
        if not line or line.startswith("//"):
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{path}:{line_no} is not valid JSON: {exc}") from exc
    return rows


class Result:
    def __init__(self) -> None:
        self.failures: list[str] = []

    def check(self, ok: bool, label: str, detail: str = "") -> bool:
        print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f" — {detail}" if detail else ""))
        if not ok:
            self.failures.append(f"{label}: {detail}" if detail else label)
        return ok


def main() -> int:
    print("Bias test set consistency check")
    print("=" * 60)
    r = Result()

    for name in ("manifest.json", "keyword_terms.json", "proxy_cases.jsonl",
                 "negative_cases.jsonl", "rationale_cases.jsonl"):
        if not (D / name).exists():
            print(f"  FAIL  {name} is missing from {D}")
            return 1

    terms_doc = json.loads((D / "keyword_terms.json").read_text(encoding="utf-8"))
    manifest = json.loads((D / "manifest.json").read_text(encoding="utf-8"))

    all_terms: dict[str, str] = {}
    for group, values in terms_doc["terms"].items():
        for t in values:
            all_terms[t] = group

    proxy = load_jsonl(D / "proxy_cases.jsonl")
    negative = load_jsonl(D / "negative_cases.jsonl")
    rationale = load_jsonl(D / "rationale_cases.jsonl")
    cases = proxy + negative + rationale

    # --- identity ---------------------------------------------------------
    ids = [c["id"] for c in cases]
    dupes = [k for k, v in Counter(ids).items() if v > 1]
    r.check(not dupes, "case ids are unique", ", ".join(dupes) or f"{len(ids)} cases")

    required = {"id", "category", "text", "must_flag", "expected_terms", "note"}
    missing = [c.get("id", "?") for c in cases if not required <= set(c)]
    r.check(not missing, "every case has all required fields", ", ".join(missing) or "ok")

    # --- spec conformance -------------------------------------------------
    counts = Counter(c["category"] for c in cases)
    bad = [f"{k}: {counts[k]} != {v}" for k, v in TARGETS.items() if counts[k] != v]
    unknown = set(counts) - set(TARGETS)
    r.check(not bad, "category counts match the Arch Doc 7.4.3 targets", "; ".join(bad) or " ".join(f"{k}={v}" for k, v in TARGETS.items()))
    r.check(not unknown, "no categories outside the spec", ", ".join(unknown) or "ok")

    wrong_flag = [c["id"] for c in cases
                  if c["must_flag"] != (c["category"] in MUST_FLAG_CATEGORIES)]
    r.check(not wrong_flag, "must_flag agrees with the category's definition", ", ".join(wrong_flag) or "ok")

    # --- terms exist ------------------------------------------------------
    unknown_terms: list[str] = []
    for c in cases:
        for t in c["expected_terms"]:
            if normalise(t) not in {normalise(x) for x in all_terms}:
                unknown_terms.append(f"{c['id']}->{t!r}")
    r.check(not unknown_terms, "every expected_terms entry exists in keyword_terms.json",
            "; ".join(unknown_terms) or f"{len(all_terms)} terms")

    # --- the crucial one: negatives must be clean -------------------------
    # A must-not-flag case containing a term is a contradiction in the fixture:
    # the pass cannot both be required to flag nothing and have something to flag.
    polluted = []
    terms_norm = {normalise(t): t for t in all_terms}
    for c in negative:
        hay = normalise(c["text"])
        hits = sorted(orig for norm, orig in terms_norm.items() if norm in hay)
        if hits:
            polluted.append(f"{c['id']} contains {hits}")
    r.check(not polluted, "no must-not-flag case contains a term in the list",
            "; ".join(polluted) or f"{len(negative)} negatives clean")

    # --- positives must actually carry their terms ------------------------
    absent = []
    for c in cases:
        if not c["must_flag"]:
            continue
        hay = normalise(c["text"])
        missing_t = [t for t in c["expected_terms"] if normalise(t) not in hay]
        if missing_t:
            absent.append(f"{c['id']} missing {missing_t}")
    r.check(not absent, "every must-flag case contains its expected_terms",
            "; ".join(absent) or "ok")

    untagged = [c["id"] for c in cases
                if c["category"] in FLAG_RATE_CATEGORIES and not c["expected_terms"]]
    r.check(not untagged, "every proxy case declares at least one expected term", ", ".join(untagged) or "ok")

    # --- the flag-rate band ------------------------------------------------
    # This is arithmetic on the fixture, NOT a measurement of the pass. It is the
    # share of must-flag cases the pass would have to catch, and it is stated so a
    # future report cannot quietly quote a percentage from some other denominator.
    total_must = sum(1 for c in cases if c["category"] in FLAG_RATE_CATEGORIES)
    print(f"\n  NOTE  {total_must} must-flag cases across categories 1-8; "
          f"{len(negative)} must-not-flag cases")
    print(f"  NOTE  pass criteria (Arch Doc 7.4.5): recall 1.0, false positives 0, "
          f"flag rate on categories 1-8 in [0.60, 0.95]")
    print(f"  NOTE  no bias_pass implementation exists yet — the set is coherent, "
          f"the pass rate is unmeasured\n")

    # --- manifest ---------------------------------------------------------
    sha = hashlib.sha256((D / "keyword_terms.json").read_bytes()).hexdigest()
    r.check(manifest.get("keyword_list_sha") == sha,
            "manifest keyword_list_sha matches keyword_terms.json",
            f"manifest={manifest.get('keyword_list_sha', '')[:16]}... actual={sha[:16]}...")

    r.check(manifest.get("version") == VERSION.replace("v", ""),
            "manifest version matches the directory", str(manifest.get("version")))
    r.check(manifest.get("case_count") == len(cases),
            "manifest case_count matches the files",
            f"manifest={manifest.get('case_count')} actual={len(cases)}")

    excluded = {e["term"] for e in terms_doc.get("deliberately_excluded", [])}
    near_miss = [c["id"] for c in negative if c.get("note", "").startswith("THE case")
                 or "deliberate near-miss" in c.get("source_pattern", "")]
    print(f"\n  NOTE  {len(excluded)} terms deliberately excluded, each with a "
          f"negative case citing it")
    r.check(all(e.get("caught_by") in {c["id"] for c in negative} for e in terms_doc.get("deliberately_excluded", [])),
            "every excluded term names a negative case that enforces the exclusion")

    lims = terms_doc.get("known_limitations", [])
    r.check(all(l.get("planned") for l in lims),
            f"all {len(lims)} known limitations have a planned version")

    print("\n" + "=" * 60)
    if r.failures:
        print(f"{len(r.failures)} FAILURE(S):")
        for f in r.failures:
            print(f"  - {f}")
        return 1
    print("Bias test set is internally consistent.")
    print("The pass rate remains UNMEASURED until a bias pass implementation exists.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
