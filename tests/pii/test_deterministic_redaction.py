"""Unit and harness tests for deterministic PII redaction (REQ-FR-011, REQ-FR-057, batch 2.7).

Tests cover:
1. Per-category unit tests: emails, Bangladeshi and international phone numbers,
   URLs (without trailing punctuation eating into prose), national IDs and
   passports, dates of birth, structured postal addresses, and known profile
   name/location.
2. Keep-set preservation: skills, role titles, degree fields, and experience
   durations survive untouched.
3. Evaluation harness run on ``tests/pii/v1.0.0`` measuring deterministic-layer
   recall and precision.
"""

from __future__ import annotations

import pytest

from ai.pii import PLACEHOLDERS, redact_deterministic
from tests.pii.harness import DETERMINISTIC_CATEGORIES, SET_ROOT, evaluate_stripper

SET_DIR = SET_ROOT / "v1.0.0"


class TestEmailRedaction:
    @pytest.mark.parametrize(
        "email",
        [
            "candidate@example.com",
            "farhan.siddique+jobs@proton.example.com",
            "sabrina_97@analytics.com.bd",
        ],
    )
    def test_replaces_email_with_typed_placeholder(self, email):
        res = redact_deterministic(f"Reach me at {email} for details.")
        assert email not in res.text
        assert PLACEHOLDERS["email"] in res.text
        assert res.counts["email"] == 1


class TestPhoneRedaction:
    @pytest.mark.parametrize(
        "phone",
        [
            "+880 1711-234567",
            "+8801911887766",
            "+880-1511-445566",
            "01819-334455",
            "01612 998877",
            "01312556677",
            "+44 20 7946 0958",
            "+1-415-555-0192",
        ],
    )
    def test_replaces_bangladeshi_and_international_phones(self, phone):
        res = redact_deterministic(f"Mobile: {phone} (available weekdays).")
        assert phone not in res.text
        assert PLACEHOLDERS["phone"] in res.text
        assert res.counts["phone"] == 1

    def test_does_not_redact_ordinary_throughput_or_year_numbers(self):
        text = "Sustained 120 req/s across 6 replicas since 2021."
        res = redact_deterministic(text)
        assert res.text == text
        assert res.counts["phone"] == 0


class TestUrlRedaction:
    @pytest.mark.parametrize(
        "url",
        [
            "https://linkedin.com/in/tariqul-chowdhury-dev",
            "http://ashraful-talukder.example.net",
            "www.linkedin.com/in/tanvir-mahmud",
            "linkedin.com/in/fariha-zaman",
            "github.com/imran-patwary",
        ],
    )
    def test_replaces_urls_and_preserves_trailing_sentence_punctuation(self, url):
        res = redact_deterministic(f"See portfolio at {url}.")
        assert url not in res.text
        assert res.text == f"See portfolio at {PLACEHOLDERS['url']}."
        assert res.counts["url"] == 1


class TestNationalIdRedaction:
    @pytest.mark.parametrize(
        "snippet,secret",
        [
            ("NID: 19952691234567890", "19952691234567890"),
            ("National ID: 8234567890", "8234567890"),
            ("Smart NID: 4612398745", "4612398745"),
            ("NID No: 19961592837461234", "19961592837461234"),
            ("Passport No: BD0823419", "BD0823419"),
            ("Bare 17-digit 19947788990011223 in text", "19947788990011223"),
        ],
    )
    def test_replaces_nid_and_passport_numbers(self, snippet, secret):
        res = redact_deterministic(snippet)
        assert secret not in res.text
        assert PLACEHOLDERS["national_id"] in res.text
        assert res.counts["national_id"] == 1


class TestDateOfBirthRedaction:
    @pytest.mark.parametrize(
        "dob_line,secret",
        [
            ("Date of Birth: 14 June 1995", "14 June 1995"),
            ("DOB: 12/03/1997", "12/03/1997"),
            ("Born on 1996-11-05", "1996-11-05"),
            ("Born: 08/09/1993", "08/09/1993"),
        ],
    )
    def test_replaces_date_of_birth_patterns(self, dob_line, secret):
        res = redact_deterministic(dob_line)
        assert secret not in res.text
        assert PLACEHOLDERS["age_date"] in res.text
        assert res.counts["age_date"] == 1


class TestAddressAndKnownPiiRedaction:
    def test_replaces_structured_postal_address_and_known_profile_pii(self):
        text = (
            "Tariqul Islam Chowdhury\n"
            "Address: House 14, Road 7, Dhanmondi, Dhaka-1209, Dhaka, Bangladesh\n"
            "Senior Backend Engineer with 5 years of experience in Python and Django."
        )
        res = redact_deterministic(
            text,
            known_name="Tariqul Islam Chowdhury",
            known_location="Dhaka, Bangladesh",
        )
        assert "Tariqul Islam Chowdhury" not in res.text
        assert "House 14, Road 7, Dhanmondi, Dhaka-1209" not in res.text
        assert "Dhaka, Bangladesh" not in res.text
        assert PLACEHOLDERS["name"] in res.text
        assert PLACEHOLDERS["address"] in res.text
        assert "Senior Backend Engineer" in res.text
        assert "5 years of experience in Python and Django." in res.text
        assert res.counts["name"] == 1
        assert res.counts["address"] == 2


class TestDeterministicHarnessEvaluation:
    def test_deterministic_categories_reach_full_recall_and_preserve_keep_set(self):
        report = evaluate_stripper(
            lambda text, profile=None: redact_deterministic(text, profile=profile).text,
            set_dir=SET_DIR,
        )
        # All 5 deterministic categories (email, phone, address, national_id, url)
        # achieve 100% recall (119/119), plus 20/22 known names and 14/33 DOBs = 153/229.
        assert report.category_recall(DETERMINISTIC_CATEGORIES) == 1.0
        for cat in DETERMINISTIC_CATEGORIES:
            assert (
                report.per_category[cat].recall == 1.0
            ), f"{cat} missed: {[m for m in report.missed_pii if m.category == cat]}"
        assert report.redacted_pii_spans == 153
        assert report.total_pii_spans == 229
        assert report.keep_survival == 1.0
        assert report.precision == 1.0
