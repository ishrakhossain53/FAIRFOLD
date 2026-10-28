"""Candidate operations shared by the API and the template pages.

Two rules live here because each has more than one caller:

* **Resume deletion** (batches 1.21/1.22). `DELETE /api/v1/candidates/resumes/{id}/`
  and the Resume manager's Delete action both mean "row, bytes and audit entry go
  together, and the audit entry holds no PII". A second copy in `views.py` would
  be a second place to forget the audit write.
* **The per-employer alias** (REQ-FR-054, D-4, batch 1.35). The employer inbox
  (1.40/1.42), notifications and exports must all show the same label for the
  same candidate, and the label must be created exactly once under concurrency.
  `alias_for()` is the single write path, and `aliases_for()` is the batch read a
  page uses instead of one lookup per row.

This is not a generic "services layer"; it holds operations with a rule that
would otherwise be duplicated.
"""

from __future__ import annotations

import secrets
from typing import TYPE_CHECKING

from django.db import IntegrityError, transaction

from candidates.models import CandidateAlias, CandidateResume
from candidates.uploads import discard_object
from core.models import AuditLogEntry

if TYPE_CHECKING:  # pragma: no cover - typing only, avoids a runtime app import
    from collections.abc import Iterable
    from uuid import UUID

    from candidates.models import CandidateProfile
    from employers.models import EmployerProfile

# Recorded when a candidate deletes a resume. The action is a machine code and
# `details` carries the row's status at deletion, never the filename, the
# storage key or the candidate: `AuditLogEntry` must not hold PII (REQ-FR-041
# keeps the trail after the personal data is gone, so the trail is the one place
# erasure must not leave a copy).
RESUME_DELETED_ACTION = "resume.deleted"
RESUME_AUDIT_RESOURCE_TYPE = "candidate_resume"


def delete_resume(resume: CandidateResume, *, actor) -> None:
    """Hard-delete `resume`: row and audit entry in one transaction, then bytes.

    Called only with a row the caller has already established belongs to
    `actor`; ownership is a lookup in both callers, not a check here, so an
    accidental call cannot delete a row by id alone.

    The object delete happens after the commit and is best effort (see
    `candidates.uploads.discard_object`): an object left behind is an orphan
    with an unguessable key, not a readable file.
    """
    resume_id = resume.pk
    file_key = resume.file_key
    status_at_deletion = resume.status

    with transaction.atomic():
        resume.delete()
        AuditLogEntry.objects.create(
            actor=actor,
            action=RESUME_DELETED_ACTION,
            resource_type=RESUME_AUDIT_RESOURCE_TYPE,
            resource_id=resume_id,
            details={"status": status_at_deletion},
            result="success",
        )

    discard_object(file_key)


# ---------------------------------------------------------------------------
# Per-employer candidate alias (REQ-FR-054, D-4, batch 1.35)
# ---------------------------------------------------------------------------

#: `C-` plus six symbols. The DDL's example is `C-7H2X9`, and the prefix makes a
#: label recognisable in a sentence ("C-7H2X9 applied") without implying a name.
ALIAS_PREFIX = "C-"
ALIAS_LENGTH = 6

#: Crockford-style alphabet: no `0`/`O`, `1`/`I`/`L`, `U`. A candidate reading an
#: alias over the phone should not have to guess which glyph was meant, and `U`
#: is dropped so a random string cannot spell an unfortunate word.
ALIAS_ALPHABET = "23456789ABCDEFGHJKMNPQRSTVWXYZ"

#: A collision is a 1-in-32^6 event per attempt; ten attempts is far beyond the
#: point where a second attempt is plausible, and a bounded loop means a broken
#: random source raises instead of spinning.
ALIAS_ATTEMPTS = 10


class AliasGenerationError(RuntimeError):
    """No free alias was found in `ALIAS_ATTEMPTS` tries.

    This is not a user error and must not be swallowed: it means either the
    random source is broken or one employer has filled the namespace. The caller
    returns a server error rather than showing a candidate a duplicate label.
    """


def _new_alias() -> str:
    """One random label. Not derived from the candidate, the employer or time."""
    return ALIAS_PREFIX + "".join(
        secrets.choice(ALIAS_ALPHABET) for _ in range(ALIAS_LENGTH)
    )


def _stored_alias(
    employer: EmployerProfile,
    candidate: CandidateProfile,
) -> str | None:
    return (
        CandidateAlias.objects.filter(employer=employer, candidate=candidate)
        .values_list("alias", flat=True)
        .first()
    )


def alias_for(employer: EmployerProfile, candidate: CandidateProfile) -> str:
    """Return this employer's stable alias for this candidate, creating it once.

    **Concurrency.** Two requests that both miss the first lookup race to insert.
    The database decides: the loser gets an `IntegrityError` on
    `UNIQUE(employer, candidate)`, re-reads the winner's row and returns the same
    alias. The alternative -- `get_or_create()` -- would also work for the pair,
    but it cannot retry a collision on `UNIQUE(employer, alias)` for a *different*
    candidate, which is the other failure this function has to handle.

    The `except` is outside the `atomic()` block on purpose: once an
    `IntegrityError` has fired, the transaction is aborted until the savepoint is
    rolled back, so the re-read has to happen after the block exits.

    **Not a permission check.** The caller has already established that the
    employer may see this candidate (an application to one of its jobs). Passing
    an unrelated pair would create a label, not grant access to anything: there is
    no candidate data on this row.
    """
    existing = _stored_alias(employer, candidate)
    if existing is not None:
        return existing

    for _ in range(ALIAS_ATTEMPTS):
        try:
            with transaction.atomic():
                row = CandidateAlias.objects.create(
                    employer=employer,
                    candidate=candidate,
                    alias=_new_alias(),
                )
        except IntegrityError:
            # Either the pair was created by a concurrent request (return its
            # label) or the random alias is already used by another candidate in
            # this employer's namespace (try again).
            existing = _stored_alias(employer, candidate)
            if existing is not None:
                return existing
            continue
        return row.alias

    raise AliasGenerationError(
        f"No free candidate alias for employer {employer.pk} after "
        f"{ALIAS_ATTEMPTS} attempts."
    )


def aliases_for(
    employer: EmployerProfile,
    candidates: Iterable[CandidateProfile],
) -> dict[UUID, str]:
    """The aliases this employer already holds for `candidates`, in one query.

    **A batch read, not a second source of truth.** The employer inbox (batch
    1.40) and the employer pages that follow it render one alias per row, and
    calling `alias_for()` per row would be one lookup for every application on the
    page. Reading the page's aliases up front keeps that at one query; a candidate
    the employer has not met yet is simply absent from the mapping, and the caller
    falls back to `alias_for()`, which creates the label exactly once.

    **Scoped by employer.** The filter is on `employer`, so a row can only ever
    carry this employer's label; two employers that receive the same candidate get
    two rows. An empty input returns an empty mapping without touching the
    database, which is the normal state of a page with no applications.
    """
    candidate_ids = {candidate.pk for candidate in candidates}
    if not candidate_ids:
        return {}
    return dict(
        CandidateAlias.objects.filter(
            employer=employer, candidate_id__in=candidate_ids
        ).values_list("candidate_id", "alias")
    )


def candidate_for_employer(
    employer: EmployerProfile,
    candidate: CandidateProfile,
    *,
    alias: str | None = None,
) -> dict[str, object]:
    """The whitelist an employer-facing surface may render for a candidate.

    REQ-FR-029 and REQ-FR-054: no name, photo, contact detail or internal
    candidate UUID before shortlist. This is a whitelist rather than a
    `ModelSerializer` with `exclude`, because a new column on `CandidateProfile`
    must not become visible by default.

    `visibility_tier` and `is_promoted` are deliberately absent: they are paid
    discovery controls and must never appear in a job's screening surface
    (REQ-FR-053). `bio` and `journey_timeline` are free text the candidate wrote
    about themselves and are not needed to identify an application; a later
    detail page can add them with its own decision, not by inheritance.

    **`alias` is a cache hint, not a second source of truth.** The inbox (batch
    1.40) reads the aliases for one page in a single query and passes each row's
    value here, so a page of a hundred applications does not run a hundred
    lookups. When it is omitted -- the normal single-candidate call -- the alias
    is read or created by `alias_for()`. A caller cannot forge a label: the
    value only ever comes from `CandidateAlias`, filtered by the same employer.
    """
    return {
        "alias": alias if alias is not None else alias_for(employer, candidate),
        "title": candidate.title,
        "location": candidate.location,
        "remote_ok": candidate.remote_ok,
        "skills": list(candidate.skills),
    }
