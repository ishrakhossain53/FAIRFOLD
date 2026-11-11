"""CI-gated tests for the versioned PII test dataset and accuracy harness (batch 2.6).

Spec: ``FAIRFOLD_Project_Architecture_and_Requirements.md`` §4.1 (REQ-FR-011,
REQ-FR-057), AD-005, and §10 Phase 2 (95%+ accuracy on the test dataset).

These tests verify:

1. Dataset integrity: manifest SHA, category coverage, case counts, and no
   overlap between ``pii_spans`` and ``keep_spans``.
2. Harness honesty: the trivial baseline produces 0.0 recall and 1.0 keep-set
   survival, and an over-redacting blank stripper fails the keep-set check.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from tests.pii.harness import (
    CATEGORIES,
    SET_ROOT,
    evaluate_stripper,
    load_cases,
    load_manifest,
    trivial_baseline,
)

SET_DIR = SET_ROOT / "v1.0.0"


def test_manifest_matches_committed_dataset():
    manifest = load_manifest(SET_DIR)
    cases = load_cases(SET_DIR)
    raw_bytes = (SET_DIR / "resumes.jsonl").read_bytes()
    actual_sha = hashlib.sha256(raw_bytes).hexdigest()

    assert manifest["version"] == "1.0.0"
    assert manifest["dataset_sha"] == actual_sha
    assert manifest["case_count"] == len(cases) == 20
    assert manifest["synthetic"] is True


def test_every_category_is_represented_in_the_dataset():
    manifest = load_manifest(SET_DIR)
    cases = load_cases(SET_DIR)

    assert set(manifest["category_counts"]) == set(CATEGORIES)
    for cat in CATEGORIES:
        count = sum(
            1 for case in cases for span in case["pii_spans"] if span["category"] == cat
        )
        assert count == manifest["category_counts"][cat]
        assert count >= 10, f"category {cat!r} has too few spans ({count})"


def test_every_span_exists_in_its_case_text_and_never_collides_with_keep_spans():
    cases = load_cases(SET_DIR)
    for case in cases:
        text_low = case["text"].lower()
        for span in case["pii_spans"]:
            assert (
                span["value"].lower() in text_low
            ), f"{case['id']}: PII span {span['value']!r} not in text"
        for keep in case["keep_spans"]:
            assert (
                keep.lower() in text_low
            ), f"{case['id']}: keep span {keep!r} not in text"
            for span in case["pii_spans"]:
                pval = span["value"].lower()
                kval = keep.lower()
                assert (
                    pval not in kval and kval not in pval
                ), f"{case['id']}: PII {pval!r} collides with keep {kval!r}"


def test_trivial_baseline_reports_zero_recall_and_full_keep_survival():
    """The trivial no-op stripper must score 0% recall and 100% keep survival."""
    manifest = load_manifest(SET_DIR)
    report = evaluate_stripper(trivial_baseline, set_dir=SET_DIR)

    assert report.case_count == manifest["case_count"] == 20
    assert report.total_pii_spans == manifest["pii_span_count"] == 229
    assert report.total_keep_spans == manifest["keep_span_count"] == 134
    assert report.redacted_pii_spans == 0
    assert report.missed_pii_spans == 229
    assert report.recall == 0.0
    assert report.precision == 0.0
    assert report.keep_survival == 1.0
    assert len(report.missed_pii) == 229
    assert report.corrupted_keep == []

    for cat in CATEGORIES:
        assert report.per_category[cat].recall == 0.0


def test_over_redacting_stripper_fails_keep_set_and_precision():
    """A stripper that wipes everything gets 1.0 recall but 0.0 keep survival."""
    report = evaluate_stripper(
        lambda _text, _profile=None: "[REDACTED]", set_dir=SET_DIR
    )

    assert report.recall == 1.0
    assert report.keep_survival == 0.0
    assert report.over_redacted_keep_spans == 134
    assert len(report.corrupted_keep) == 134
    # Precision is penalised by the 134 false positives: 229 / (229 + 134) < 0.95.
    assert report.precision == pytest.approx(229 / (229 + 134))
    assert report.precision < 0.70


def test_missing_dataset_fails_loudly():
    with pytest.raises(FileNotFoundError):
        load_cases(Path("/nonexistent-pii-set"))
    with pytest.raises(FileNotFoundError):
        load_manifest(Path("/nonexistent-pii-set"))
