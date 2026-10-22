"""Resume lifecycle operations shared by the API and the template pages.

Two surfaces own the same rule: `DELETE /api/v1/candidates/resumes/{id}/`
(batch 1.21) and the Resume manager's Delete action (batch 1.22). The rule is
"row, bytes and audit entry go together, and the audit entry holds no PII", so
it lives here rather than in either view. A second copy in `views.py` would be a
second place to forget the audit write.

Nothing else belongs in this module yet. It is not a generic "services layer";
it exists because this one operation has two callers.
"""

from __future__ import annotations

from django.db import transaction

from candidates.models import CandidateResume
from candidates.uploads import discard_object
from core.models import AuditLogEntry

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
