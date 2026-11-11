"""Tests for spaCy NER and proxy stripping (batch 2.8, REQ-FR-011, REQ-FR-057, AD-005).

Verifies that ``ai.pii.strip_pii``:
* Lazy-loads ``en_core_web_sm`` once per process via ``get_nlp()`` and accepts a
  stub ``nlp`` callable in unit tests without network calls.
* Strips educational institutions, corporate and contextual employer names,
  age-revealing graduation/cohort years and date ranges (converted to relative
  durations alongside ``[DATE]``), stated ages, photo references, referee
  names, and residual NER ``PERSON`` / ``ORG`` / ``GPE`` / ``LOC`` spans.
* Preserves the keep-set (technical skills, role titles, degree levels and
  academic fields, and experience durations).
* Achieves >= 95% overall recall and 100% keep-set survival on the immutable
  ``tests/pii/v1.0.0`` evaluation dataset, matching the figures recorded in
  ``tests/pii/v1.0.0/manifest.json``.
"""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import patch

import pytest

import ai.pii as pii_module
from ai.pii import PLACEHOLDERS, get_nlp, strip_pii
from tests.pii.harness import (
    CATEGORIES,
    NER_PROXY_CATEGORIES,
    evaluate_stripper,
    load_manifest,
)


@dataclass
class _StubEnt:
    text: str
    start_char: int
    end_char: int
    label_: str


@dataclass
class _StubDoc:
    ents: list[_StubEnt]


class TestLazyNlpLoading:
    def test_get_nlp_loads_spacy_model_once_and_caches(self) -> None:
        sentinel = object()
        with patch.object(pii_module, "_NLP", None):
            with patch("spacy.load", return_value=sentinel) as mock_load:
                first = get_nlp()
                second = get_nlp()

        assert first is sentinel
        assert second is sentinel
        mock_load.assert_called_once_with(
            "en_core_web_sm", disable=["parser", "lemmatizer"]
        )

    def test_strip_pii_accepts_injected_stub_nlp_without_calling_get_nlp(self) -> None:
        def stub_nlp(text: str) -> _StubDoc:
            target = "Nusrat Jahan"
            idx = text.find(target)
            if idx == -1:
                return _StubDoc(ents=[])
            return _StubDoc(
                ents=[
                    _StubEnt(
                        text=target,
                        start_char=idx,
                        end_char=idx + len(target),
                        label_="PERSON",
                    )
                ]
            )

        with patch.object(
            pii_module, "get_nlp", side_effect=AssertionError("should not load")
        ):
            res = strip_pii(
                "Supervised by Nusrat Jahan on Python microservices.",
                nlp=stub_nlp,
            )

        assert "Nusrat Jahan" not in res.text
        assert PLACEHOLDERS["name"] in res.text
        assert "Python" in res.text
        assert res.counts["name"] == 1


class TestProxyStrippingCategories:
    @pytest.mark.parametrize(
        "raw_institution",
        [
            "Bangladesh University of Engineering and Technology",
            "North South University",
            "University of Dhaka",
            "BRAC University",
            "Islamic University of Technology",
            "Notre Dame College",
            "Viqarunnisa Noon School and College",
            "BUET",
            "NSU",
        ],
    )
    def test_strips_educational_institutions(self, raw_institution: str) -> None:
        text = (
            f"Education: B.Sc. in Computer Science and Engineering from "
            f"{raw_institution}. Skills: Python, Django."
        )
        res = strip_pii(text)
        assert raw_institution not in res.text
        assert PLACEHOLDERS["institution"] in res.text
        assert res.counts["institution"] >= 1
        assert "B.Sc. in Computer Science and Engineering" in res.text
        assert "Python" in res.text

    @pytest.mark.parametrize(
        "raw_employer",
        [
            "bKash Limited",
            "Grameenphone Ltd.",
            "BRAC Bank PLC",
            "Pathao Ltd.",
            "TigerIT Bangladesh Ltd.",
            "Chaldal Limited",
        ],
    )
    def test_strips_corporate_employers(self, raw_employer: str) -> None:
        text = (
            f"Experience: Senior Backend Engineer at {raw_employer} for 4 years "
            f"building PostgreSQL and Celery services."
        )
        res = strip_pii(text)
        assert raw_employer not in res.text
        assert PLACEHOLDERS["employer"] in res.text
        assert res.counts["employer"] >= 1
        assert "Senior Backend Engineer" in res.text
        assert "4 years" in res.text

    def test_strips_contextual_employer_without_legal_suffix(self) -> None:
        text = (
            "Experience: Full-Stack Software Developer at Selise Digital Platforms "
            "for 3 years working with React and TypeScript."
        )
        res = strip_pii(text)
        assert "Selise Digital Platforms" not in res.text
        assert PLACEHOLDERS["employer"] in res.text
        assert res.counts["employer"] >= 1
        assert "Full-Stack Software Developer" in res.text
        assert "3 years" in res.text

    def test_converts_graduation_year_and_date_range_to_durations(self) -> None:
        text = (
            "Graduated in 2019 with B.Sc. in Computer Science. "
            "Worked 2020 - 2024 as Backend Engineer."
        )
        res = strip_pii(text, reference_year=2026)
        assert "2019" not in res.text
        assert "2020" not in res.text
        assert "2024" not in res.text
        assert f"{PLACEHOLDERS['age_date']} (7 years ago)" in res.text
        assert f"{PLACEHOLDERS['age_date']} (4 years)" in res.text
        assert res.counts["age_date"] == 2

    @pytest.mark.parametrize(
        "age_phrase",
        [
            "26 years old",
            "Age: 28",
            "Aged 31",
            "24 yrs old",
        ],
    )
    def test_strips_stated_age_phrases(self, age_phrase: str) -> None:
        text = f"Candidate summary ({age_phrase}): 4 years of Python experience."
        res = strip_pii(text)
        assert age_phrase.lower() not in res.text.lower()
        assert PLACEHOLDERS["age_date"] in res.text
        assert "4 years" in res.text

    @pytest.mark.parametrize(
        "photo_snippet",
        [
            "![Candidate Photo](headshot_tanvir.jpg)",
            "[Passport-size photograph attached]",
            "[Candidate headshot: portrait.png]",
            "Photo: resume_photo.png",
            "Profile photo attached",
        ],
    )
    def test_strips_photo_references(self, photo_snippet: str) -> None:
        text = f"{photo_snippet} | Skills: Python, Docker, Kubernetes."
        res = strip_pii(text)
        assert photo_snippet not in res.text
        assert PLACEHOLDERS["photo"] in res.text
        assert res.counts["photo"] >= 1
        assert "Python" in res.text
        assert "Kubernetes" in res.text

    def test_strips_referee_and_ner_person_and_location(self) -> None:
        text = (
            "Based in Chattogram, Bangladesh. "
            "Reference: Dr. Mahmudul Hasan, Professor."
        )
        res = strip_pii(text)
        assert "Mahmudul Hasan" not in res.text
        assert "Chattogram" not in res.text
        assert PLACEHOLDERS["name"] in res.text
        assert PLACEHOLDERS["address"] in res.text


class TestHarnessAccuracyGateOnV100:
    def test_strip_pii_meets_95_percent_recall_and_preserves_keep_set(self) -> None:
        report = evaluate_stripper(
            lambda text, profile: strip_pii(text, profile=profile).text
        )

        # Spec gate (Arch Doc §10 Phase 2): >= 95% overall recall on the test dataset.
        assert report.recall >= 0.95, f"missed spans: {report.missed_pii}"
        assert report.recall == 1.0
        assert report.precision >= 0.95
        assert (
            report.keep_survival == 1.0
        ), f"corrupted keep spans: {report.corrupted_keep}"
        assert report.category_recall(NER_PROXY_CATEGORIES) >= 0.95

        for category in CATEGORIES:
            assert (
                report.per_category[category].recall >= 0.95
            ), f"category {category} recall below 0.95: {report.per_category[category]}"

    def test_manifest_measured_block_matches_live_evaluation(self) -> None:
        manifest = load_manifest()
        measured = manifest["measured"]
        report = evaluate_stripper(
            lambda text, profile: strip_pii(text, profile=profile).text
        )

        assert measured["cases"] == report.case_count
        assert measured["total_pii_spans"] == report.total_pii_spans
        assert measured["redacted_pii_spans"] == report.redacted_pii_spans
        assert measured["recall"] == round(report.recall, 4)
        assert measured["precision"] == round(report.precision, 4)
        assert measured["keep_survival"] == round(report.keep_survival, 4)
