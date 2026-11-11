"""Evaluation harness for the versioned PII and proxy stripping dataset.

Spec: ``FAIRFOLD_Project_Architecture_and_Requirements.md`` §4.1 (REQ-FR-011,
REQ-FR-057), AD-005, and §10 Phase 2 (95%+ accuracy on the test dataset).

What this harness measures
--------------------------
Each case in ``tests/pii/<version>/resumes.jsonl`` is a synthetic resume with:

* ``pii_spans`` — labelled substrings (by category) that **must not** survive
  in the stripped text. A span whose value is absent (case-insensitively) from
  the stripped output counts as a true positive (TP); one that survives is a
  false negative (FN).
* ``keep_spans`` — skills, role titles, degree levels/fields, and experience
  durations that **must** survive in the stripped text. A keep-span that
  survives counts as a true negative (TN); one that is stripped or corrupted is
  a false positive (FP, over-redaction).

From these counts the harness computes:

* ``recall`` = TP / (TP + FN), overall and per category
* ``precision`` = TP / (TP + FP) (0.0 when TP + FP == 0)
* ``keep_survival`` = TN / (TN + FP)

The harness takes any callable ``stripper(text: str, profile: dict | None) -> str``
so it can evaluate the trivial no-op baseline (batch 2.6), the deterministic
regex layer alone (batch 2.7), and the full regex + spaCy NER + proxy pipeline
(batch 2.8) on the exact same immutable dataset.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

REPO_ROOT = Path(__file__).resolve().parents[2]
SET_ROOT = REPO_ROOT / "tests" / "pii"

CATEGORIES = (
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
)

DETERMINISTIC_CATEGORIES = frozenset(
    {"email", "phone", "address", "national_id", "url"}
)

NER_PROXY_CATEGORIES = frozenset(
    {"name", "age_date", "institution", "employer", "photo"}
)

StripperFn = Callable[[str, dict[str, str] | None], str]


def trivial_baseline(text: str, profile: dict[str, str] | None = None) -> str:
    """Trivial baseline stripper that returns the input text unchanged.

    Used in batch 2.6 to prove the harness reports 0% recall (and 100% keep-set
    survival) when nothing is stripped.
    """
    return text


@dataclass(frozen=True)
class SpanMiss:
    """A labelled PII span that survived stripping, or a keep-span that did not."""

    case_id: str
    category: str
    value: str


@dataclass(frozen=True)
class CategoryMetrics:
    """Recall breakdown for a single PII category."""

    category: str
    total: int
    redacted: int
    missed: int

    @property
    def recall(self) -> float:
        if self.total == 0:
            return 1.0
        return self.redacted / self.total


@dataclass
class HarnessReport:
    """Complete evaluation report across a versioned PII dataset."""

    version: str
    case_count: int
    total_pii_spans: int
    redacted_pii_spans: int
    total_keep_spans: int
    survived_keep_spans: int
    per_category: dict[str, CategoryMetrics] = field(default_factory=dict)
    missed_pii: list[SpanMiss] = field(default_factory=list)
    corrupted_keep: list[SpanMiss] = field(default_factory=list)

    @property
    def missed_pii_spans(self) -> int:
        return self.total_pii_spans - self.redacted_pii_spans

    @property
    def over_redacted_keep_spans(self) -> int:
        return self.total_keep_spans - self.survived_keep_spans

    @property
    def recall(self) -> float:
        """Overall PII recall: TP / (TP + FN)."""
        if self.total_pii_spans == 0:
            return 1.0
        return self.redacted_pii_spans / self.total_pii_spans

    @property
    def precision(self) -> float:
        """Overall precision against keep-set false positives: TP / (TP + FP)."""
        denom = self.redacted_pii_spans + self.over_redacted_keep_spans
        if denom == 0:
            return 0.0
        return self.redacted_pii_spans / denom

    @property
    def keep_survival(self) -> float:
        """Fraction of keep-set spans (skills, experience, roles) that survived."""
        if self.total_keep_spans == 0:
            return 1.0
        return self.survived_keep_spans / self.total_keep_spans

    def category_recall(self, categories: frozenset[str] | set[str]) -> float:
        """Aggregate recall across a subset of categories (e.g. deterministic only)."""
        total = sum(
            m.total for cat, m in self.per_category.items() if cat in categories
        )
        redacted = sum(
            m.redacted for cat, m in self.per_category.items() if cat in categories
        )
        if total == 0:
            return 1.0
        return redacted / total


def latest_set_dir() -> Path:
    versions = sorted(
        (p for p in SET_ROOT.glob("v*") if (p / "resumes.jsonl").exists()),
        key=lambda p: [int(part) for part in p.name.lstrip("v").split(".")],
    )
    if not versions:
        raise FileNotFoundError(f"no versioned PII test set under {SET_ROOT}")
    return versions[-1]


def load_cases(set_dir: Path | str | None = None) -> list[dict]:
    directory = Path(set_dir) if set_dir else latest_set_dir()
    path = directory / "resumes.jsonl"
    if not path.exists():
        raise FileNotFoundError(f"no resumes.jsonl in {directory}")
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def load_manifest(set_dir: Path | str | None = None) -> dict:
    directory = Path(set_dir) if set_dir else latest_set_dir()
    path = directory / "manifest.json"
    if not path.exists():
        raise FileNotFoundError(f"no manifest.json in {directory}")
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate_stripper(
    stripper: StripperFn,
    *,
    set_dir: Path | str | None = None,
) -> HarnessReport:
    """Run ``stripper`` across the dataset and return measured recall/precision."""
    directory = Path(set_dir) if set_dir else latest_set_dir()
    manifest = load_manifest(directory)
    cases = load_cases(directory)

    cat_totals: Counter[str] = Counter()
    cat_redacted: Counter[str] = Counter()
    missed_pii: list[SpanMiss] = []
    corrupted_keep: list[SpanMiss] = []

    total_keep = 0
    survived_keep = 0

    for case in cases:
        case_id = case["id"]
        profile = case.get("profile") or {}
        stripped = stripper(case["text"], profile)
        stripped_low = stripped.lower()

        for span in case["pii_spans"]:
            cat = span["category"]
            val = span["value"]
            cat_totals[cat] += 1
            if val.lower() not in stripped_low:
                cat_redacted[cat] += 1
            else:
                missed_pii.append(SpanMiss(case_id=case_id, category=cat, value=val))

        for keep_val in case["keep_spans"]:
            total_keep += 1
            if keep_val.lower() in stripped_low:
                survived_keep += 1
            else:
                corrupted_keep.append(
                    SpanMiss(case_id=case_id, category="keep", value=keep_val)
                )

    per_category = {
        cat: CategoryMetrics(
            category=cat,
            total=cat_totals[cat],
            redacted=cat_redacted[cat],
            missed=cat_totals[cat] - cat_redacted[cat],
        )
        for cat in CATEGORIES
    }

    total_pii = sum(cat_totals.values())
    redacted_pii = sum(cat_redacted.values())

    return HarnessReport(
        version=manifest.get("version", directory.name.lstrip("v")),
        case_count=len(cases),
        total_pii_spans=total_pii,
        redacted_pii_spans=redacted_pii,
        total_keep_spans=total_keep,
        survived_keep_spans=survived_keep,
        per_category=per_category,
        missed_pii=missed_pii,
        corrupted_keep=corrupted_keep,
    )
