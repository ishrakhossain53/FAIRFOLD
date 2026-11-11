"""PDF text extraction (REQ-FR-012, batches 2.2-2.3).

No database and no Django: `candidates.extraction` is a pure function of bytes,
so these tests do not carry the ``django_db`` marker. The fixtures are the small
synthetic PDFs under ``tests/fixtures/resumes/`` — hand-written PDF objects with a
correct xref table, no real resume content (see that directory's README for how
they were made).

What is pinned here, on top of the happy path:

* one test per failure code (batch 2.3 "Done when"): each unsupported type,
  empty, malformed, password-protected, no-text-layer, too-large and
  too-many-pages has its own code and its own test;
* every failure message is user-safe — non-empty, no exception class name and no
  stack noise, because it is shown verbatim to the candidate;
* the result is deterministic: the same bytes give the same text.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from candidates.extraction import (
    EMPTY_FILE,
    FAILURE_MESSAGES,
    MALFORMED,
    NO_TEXT_LAYER,
    PASSWORD_PROTECTED,
    TOO_LARGE,
    TOO_MANY_PAGES,
    UNSUPPORTED_TYPE,
    extract_text,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "resumes"


def read(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def extract(name: str, **kwargs):
    import io

    return extract_text(io.BytesIO(read(name)), **kwargs)


class TestHappyPath:
    def test_extracts_text_from_a_text_pdf(self):
        result = extract("simple_text.pdf")

        assert result.ok
        assert result.page_count == 2
        assert "Backend Developer" in result.text
        assert "Django" in result.text

    def test_is_deterministic(self):
        first = extract("simple_text.pdf")
        second = extract("simple_text.pdf")

        assert first.text == second.text
        assert first.page_count == second.page_count

    def test_joins_pages_with_newlines(self):
        result = extract("three_pages.pdf")

        assert (
            result.text
            == "Page one of three.\nPage two of three.\nPage three of three."
        )


class TestFailureCodes:
    def test_unsupported_type(self):
        result = extract("unsupported.docx")

        assert result.failure is not None
        assert result.failure.code == UNSUPPORTED_TYPE

    def test_empty_file(self):
        result = extract("empty.pdf")

        assert result.failure.code == EMPTY_FILE

    def test_malformed_pdf(self):
        result = extract("truncated.pdf")

        assert result.failure.code == MALFORMED

    def test_password_protected(self):
        result = extract("encrypted.pdf")

        assert result.failure.code == PASSWORD_PROTECTED

    def test_no_text_layer(self):
        result = extract("scanned_no_text.pdf")

        assert result.failure.code == NO_TEXT_LAYER

    def test_too_many_pages(self):
        result = extract("three_pages.pdf", max_pages=2)

        assert result.failure.code == TOO_MANY_PAGES

    def test_too_large(self):
        result = extract("simple_text.pdf", max_bytes=10)

        assert result.failure.code == TOO_LARGE


class TestMessages:
    @pytest.mark.parametrize(
        "name",
        [
            "unsupported.docx",
            "empty.pdf",
            "truncated.pdf",
            "encrypted.pdf",
            "scanned_no_text.pdf",
        ],
    )
    def test_every_message_is_user_safe(self, name):
        result = extract(name)

        message = result.failure.message
        assert message
        # A safe message never leaks a class name or a traceback.
        assert "Traceback" not in message
        assert "Error" not in message
        assert "pdfminer" not in message.lower()

    def test_every_code_has_a_message_template(self):
        for code in (
            UNSUPPORTED_TYPE,
            EMPTY_FILE,
            MALFORMED,
            PASSWORD_PROTECTED,
            NO_TEXT_LAYER,
            TOO_LARGE,
            TOO_MANY_PAGES,
        ):
            assert code in FAILURE_MESSAGES
