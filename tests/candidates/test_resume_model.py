"""Model tests for `CandidateResume` (REQ-FR-010/012, batch 1.18).

The DDL is the specification, so these tests pin the parts that are easy to get
wrong when transcribing it:

* the row is `pending` before any bytes exist, and the phase-2 statuses are
  accepted;
* `ck_resume_status` is enforced by **PostgreSQL**, not only by the model's
  `choices` -- `objects.create()` skips `full_clean()`, so a test through the
  ORM would pass even if the constraint were missing;
* `status_reason` is how a `rejected` resume explains itself;
* a resume cannot exist without a candidate, and deleting the candidate takes
  the resumes with it;
* `__str__` exposes neither the storage key nor the original filename, because
  an admin list renders it.

Key generation (UUID-based, extension from the allow-list) and the presign
endpoint are batch 1.19; scanning is 1.20. They are not asserted here.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from accounts.models import User
from candidates.models import CandidateProfile, CandidateResume

pytestmark = pytest.mark.django_db

ALL_STATUSES = [
    CandidateResume.Status.PENDING,
    CandidateResume.Status.UPLOADED,
    CandidateResume.Status.SCANNING,
    CandidateResume.Status.CLEAN,
    CandidateResume.Status.REJECTED,
    CandidateResume.Status.PROCESSING,
    CandidateResume.Status.EXTRACTED,
    CandidateResume.Status.EMBEDDED,
    CandidateResume.Status.FAILED,
]


@pytest.fixture
def candidate():
    return User.objects.create_user("candidate@example.com", "not-used-in-these-tests")


@pytest.fixture
def profile(candidate):
    return CandidateProfile.objects.create(user=candidate)


def make_resume(profile, **overrides):
    """A row with only the DDL-required column set, plus any overrides."""
    values = {
        "candidate": profile,
        "file_key": "resumes/8f14e45fceea167a5a36dedd4bea2543.pdf",
    }
    values.update(overrides)
    return CandidateResume.objects.create(**values)


def test_defaults_match_the_ddl(profile):
    resume = make_resume(profile)

    assert resume.status == CandidateResume.Status.PENDING
    assert resume.status_reason == ""
    assert resume.processed_at is None
    assert resume.file_size is None
    assert resume.mime_type == ""
    assert resume.extracted_text == ""
    assert resume.raw_text_hash == ""
    assert resume.created_at is not None


def test_every_documented_status_is_accepted(profile):
    for status in ALL_STATUSES:
        resume = make_resume(profile, status=status)
        resume.refresh_from_db()
        assert resume.status == status


def test_a_rejected_resume_carries_its_reason(profile):
    resume = make_resume(
        profile,
        status=CandidateResume.Status.REJECTED,
        status_reason="clamav unavailable",
    )
    resume.refresh_from_db()

    assert resume.status == CandidateResume.Status.REJECTED
    assert resume.status_reason == "clamav unavailable"


def test_an_undefined_status_is_rejected_by_the_database(profile):
    # `objects.create()` never calls `full_clean()`, so this only fails if the
    # CHECK constraint exists in PostgreSQL.
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            make_resume(profile, status="infected")


def test_file_key_is_required(profile):
    # `CharField` turns a missing value into "" on its own, so the database
    # NOT NULL only shows up when NULL is sent explicitly.
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            CandidateResume.objects.create(candidate=profile, file_key=None)


def test_a_resume_cannot_exist_without_a_candidate():
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            CandidateResume.objects.create(file_key="resumes/orphan.pdf")


def test_a_candidate_may_have_several_resumes(profile):
    first = make_resume(profile)
    second = make_resume(profile, file_key="resumes/second.pdf")

    assert set(profile.resumes.all()) == {first, second}


def test_deleting_the_candidate_deletes_their_resumes(profile):
    resume = make_resume(profile)

    profile.delete()

    assert not CandidateResume.objects.filter(pk=resume.pk).exists()


def test_newest_resume_is_listed_first(profile):
    older = make_resume(profile)
    newer = make_resume(profile, file_key="resumes/newer.pdf")
    now = timezone.now()
    CandidateResume.objects.filter(pk=older.pk).update(
        created_at=now - timedelta(hours=1)
    )
    CandidateResume.objects.filter(pk=newer.pk).update(created_at=now)

    assert list(CandidateResume.objects.all()) == [newer, older]


def test_str_exposes_neither_the_key_nor_the_original_filename(profile):
    resume = make_resume(
        profile,
        file_key="resumes/8f14e45fceea167a5a36dedd4bea2543.pdf",
        original_filename="Ada Lovelace CV.pdf",
    )

    rendered = str(resume)

    assert "Ada Lovelace" not in rendered
    assert resume.file_key not in rendered
    assert rendered == f"Resume {resume.pk}"
