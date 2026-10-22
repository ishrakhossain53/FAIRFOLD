"""ClamAV adapter for resume uploads (REQ-SEC-012, gap P, batch 1.20).

The rule this module exists to enforce: **fail closed**. `docs/DECISIONS.md`
and `.env.example` both say an upload is REJECTED when the daemon is
unreachable, rather than passed through unscanned. There is therefore no
"unknown" return value and no setting that turns the scan off — a transport
failure is :class:`ScanUnavailable`, and the caller must reject the resume.

The scanner talks the clamd INSTREAM protocol with the file handle already open,
so the bytes are never written to a temporary file on the worker.
"""

from __future__ import annotations

from typing import BinaryIO

from clamav_client.clamd import ClamdError, ClamdNetworkSocket
from django.conf import settings


class ScanUnavailable(RuntimeError):
    """The daemon could not be reached, or answered with an error.

    The caller must reject the resume; it must not mark it clean.
    """


class MalwareDetected(RuntimeError):
    """ClamAV matched a signature. `signature` is the name it reported."""

    def __init__(self, signature: str) -> None:
        self.signature = signature
        super().__init__(signature)


def scan_stream(handle: BinaryIO) -> None:
    """Scan `handle`; return ``None`` when the stream is clean.

    Raises :class:`MalwareDetected` with the signature name, or
    :class:`ScanUnavailable` for every transport or protocol failure. The
    signature name and the exception class are the only details kept: a
    clamd response is not PII, but it is also not something to write into
    `status_reason` wholesale.
    """
    client = ClamdNetworkSocket(
        host=settings.CLAMD_HOST,
        port=settings.CLAMD_PORT,
        timeout=settings.CLAMD_TIMEOUT,
    )
    try:
        report = client.instream(handle)
    except (OSError, ClamdError) as exc:
        # `CommunicationError` and `BufferTooLongError` both descend from
        # ClamdError; a refused socket is an OSError. None of them means "clean".
        raise ScanUnavailable("antivirus unavailable") from exc

    for _name, (status, detail) in report.items():
        if status == "FOUND":
            raise MalwareDetected(detail or "unknown signature")
        if status != "OK":
            # Defensive: an unexpected state is not evidence of cleanliness.
            raise ScanUnavailable("antivirus returned an unexpected state")
