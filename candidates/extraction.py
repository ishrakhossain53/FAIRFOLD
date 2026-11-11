"""PDF text extraction for resumes (REQ-FR-012, batches 2.2-2.3).

Pure by construction: :func:`extract_text` takes a binary file object and returns
an :class:`ExtractionResult`. It imports neither Django nor anything that touches
settings, storage or the network, so it runs in a Celery worker and in a unit
test with no database. ``pdfplumber`` is the one dependency, and it is only ever
called with bytes already in memory.

Every failure has a **code** and a **user-safe message**. The code is what gets
stored in ``candidate_resumes.status_reason`` (which must never hold PII or raw
text), and the page maps it back to the message. Keeping the message out of the
database means a copy change never needs a migration, and the reason a resume
failed can be localised later without touching stored rows.

The codes are the contract between this module, the processing task (batch 2.4)
and the resume page (batch 2.5): one code per failure, so a scanned PDF and a
damaged one never collapse into the same unhelpful "could not read".
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from io import BytesIO
from typing import BinaryIO

import pdfplumber
from pdfminer.pdfdocument import PDFPasswordIncorrect
from pdfplumber.utils.exceptions import PdfminerException

# Silence pdfminer's token-level DEBUG logging so raw resume text is never
# emitted to log handlers even if the root logger is lowered to DEBUG.
logging.getLogger("pdfminer").setLevel(logging.WARNING)

# The largest PDF we will read into memory, in bytes. The upload gate already
# rejects anything larger (settings.MAX_UPLOAD_SIZE_BYTES, default 10 MB), but
# this is the extraction-side ceiling so a file that slips past, or is replaced
# after scanning, cannot become a decompression bomb on the worker.
MAX_BYTES = 10 * 1024 * 1024

# The most pages we will extract. A resume is short; a hundreds-of-pages PDF is
# either a mistake or an attack, and neither needs its text extracted.
MAX_PAGES = 20

# ---------------------------------------------------------------------------
# Failure codes and their user-safe messages
# ---------------------------------------------------------------------------

UNSUPPORTED_TYPE = "unsupported_type"
EMPTY_FILE = "empty_file"
MALFORMED = "malformed"
PASSWORD_PROTECTED = "password_protected"
NO_TEXT_LAYER = "no_text_layer"
TOO_LARGE = "too_large"
TOO_MANY_PAGES = "too_many_pages"
EMBEDDING_FAILED = "embedding_failed"

#: ``code -> message template``. ``{max_mb}`` and ``{max_pages}`` are filled in
#: by :func:`extract_text` so the stored code stays independent of the limits.
FAILURE_MESSAGES: dict[str, str] = {
    UNSUPPORTED_TYPE: "This file type can't be read. Upload a PDF.",
    EMPTY_FILE: "This file is empty. Upload a PDF that contains your resume.",
    MALFORMED: (
        "We couldn't read this PDF. It may be damaged. Upload it again or "
        "export a new PDF."
    ),
    PASSWORD_PROTECTED: (
        "This PDF is password-protected. Remove the password and upload it again."
    ),
    NO_TEXT_LAYER: (
        "This PDF has no text we can read. If it is a scan or a photo, upload a "
        "text-based PDF instead."
    ),
    TOO_LARGE: "This PDF is larger than {max_mb} MB. Upload a smaller file.",
    TOO_MANY_PAGES: (
        "This PDF has more than {max_pages} pages. Upload a shorter resume."
    ),
    EMBEDDING_FAILED: (
        "We couldn't finish indexing your resume right now. Try again in a moment."
    ),
}


@dataclass(frozen=True)
class ExtractionFailure:
    """Why extraction stopped. `code` is stored; `message` is shown to the user."""

    code: str
    message: str


@dataclass(frozen=True)
class ExtractionResult:
    """The outcome of one extraction attempt.

    Exactly one of `text` / `failure` is meaningful: on success `text` holds the
    extracted pages joined with newlines and `failure` is ``None``; on failure
    `text` is ``""`` and `failure` names the code and the message. The raw text
    is otherwise never stored or logged (REQ-FR-011, batch 2.4).
    """

    text: str
    failure: ExtractionFailure | None = None
    page_count: int = 0

    @property
    def ok(self) -> bool:
        return self.failure is None


def _read_all(handle: BinaryIO, max_bytes: int) -> bytes | None:
    """Read `handle` into memory, or return ``None`` once it exceeds `max_bytes`.

    Reading up to the limit and then bailing is what keeps a 2 GB "PDF" from
    becoming a 2 GB string on the worker; the loop reads in fixed chunks rather
    than calling ``read()`` with a size we would have to trust the stream to
    honour.
    """
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = handle.read(64 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            return None
        chunks.append(chunk)
    return b"".join(chunks)


def _is_password_protected(exc: PdfminerException) -> bool:
    """True when pdfplumber's wrapper hid a ``PDFPasswordIncorrect``.

    pdfplumber wraps every pdfminer error in ``PdfminerException`` and leaves the
    real error in ``args[0]``, so the wrong-password signal has to be picked out
    rather than caught directly.
    """
    return bool(exc.args) and isinstance(exc.args[0], PDFPasswordIncorrect)


def _failure(code: str, **format_values: object) -> ExtractionResult:
    message = FAILURE_MESSAGES[code].format(**format_values)
    return ExtractionResult(text="", failure=ExtractionFailure(code, message))


def extract_text(
    file_obj: BinaryIO,
    *,
    max_bytes: int = MAX_BYTES,
    max_pages: int = MAX_PAGES,
) -> ExtractionResult:
    """Extract the text of a PDF resume from `file_obj`.

    A pure function of the bytes: the same input produces the same result, and a
    bad input produces a typed failure rather than a raised exception, because
    the caller's job is to record the code and show the message, not to catch
    twenty different errors.

    Detection order matters and is deliberate:

    1. too large, then empty, then not-a-PDF — the cheap checks that need no
       parser and cover the "decompression bomb" and "wrong file" cases;
    2. password-protected — pdfminer raises before any page is parsed, so this
       is distinguishable from "damaged";
    3. over the page limit — counted after the document opens;
    4. no text layer — a valid PDF whose pages extract to nothing.
    """
    data = _read_all(file_obj, max_bytes)
    if data is None:
        return _failure(TOO_LARGE, max_mb=round(max_bytes / (1024 * 1024), 1))
    if not data:
        return _failure(EMPTY_FILE)
    if not data.startswith(b"%PDF-"):
        # A DOCX, an image, or anything else the upload gate let through: the
        # header check is content-based, not the declared MIME type.
        return _failure(UNSUPPORTED_TYPE)

    try:
        with pdfplumber.open(BytesIO(data)) as pdf:
            page_count = len(pdf.pages)
            if page_count > max_pages:
                return _failure(TOO_MANY_PAGES, max_pages=max_pages)

            parts: list[str] = []
            for page in pdf.pages:
                text = page.extract_text() or ""
                if text.strip():
                    parts.append(text)
            text = "\n".join(parts).strip()
    except PdfminerException as exc:
        if _is_password_protected(exc):
            return _failure(PASSWORD_PROTECTED)
        return _failure(MALFORMED)
    except Exception:
        # Any parser failure that is not a password is, to the caller, "damaged":
        # a truncated xref, a broken stream, an unsupported encryption scheme.
        return _failure(MALFORMED)

    if not text:
        return _failure(NO_TEXT_LAYER)
    return ExtractionResult(text=text, page_count=page_count)
