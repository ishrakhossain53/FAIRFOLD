"""Application status actions (REQ-FR-023, REQ-FR-052, batch 1.41).

Complete Doc §C.12:

    POST   /api/v1/applications/{id}/shortlist/    # Shortlist a candidate
    POST   /api/v1/applications/{id}/reject/       # Reject a candidate

and its note: **actions, not a `PATCH status`**, because a generic field write
could skip the transition check and the audit entry.

What these tests pin down, in the order the invariants appear in AGENTS.md:

* **the transition table is the contract.** `prd.md` §11.3 and `design.md` §7.4
  give `applied -> screened -> shortlisted -> interview -> offered -> hired`,
  with `rejected` reachable from any stage. Every (status, action) pair is
  exercised, so a status added to the model without a decision fails here
  instead of becoming silently reachable.
* **a filter never rejects** (Gap G3). `not_matched` is a filter outcome, a
  person writes `rejected`, `decided_by` names that person, and `ai.screening`
  has no column that could write `status`.
* **shortlisting consults the assessment gate in the backend** (REQ-FR-051), not
  only in the page: `pending` and `failed` are a 409 with the documented
  sentence, and no status change.
* **every effective decision writes an audit entry** with statuses only -- no
  candidate name, alias, email or reason text.
* **a repeated decision is a no-op** (Arch Doc §4.3 rule 2): 200, one entry.
* **ownership is the lookup.** Another employer's application and an id that
  exists nowhere are the same 404.
* **the response is the inbox row**, still by alias: shortlisting does not
  reveal the candidate's identity (that reveal is a separate audited action).
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from ai.screening import SCORING_FIELDS
from candidates.models import CandidateProfile
from core.models import AuditLogEntry
from employers.models import EmployerProfile
from matching.models import Application, Job
from matching.services import (
    DECISION_ACTIONS,
    DECISION_CHANGED,
    DECISION_CONFLICT,
    DECISION_GATE_BLOCKED,
    DECISION_NOOP,
    NOT_MATCHED_SHORTLIST_DETAIL,
    SHORTLIST_GATE_DETAIL,
    decide_application,
)

pytestmark = pytest.mark.django_db

Status = Application.Status
Gate = Application.AssessmentGateStatus

# The body `EmployerApplicationListSerializer` returns (batch 1.40). Written out
# rather than derived, so a field added without a decision fails here.
EXPECTED_FIELDS = {
    "id",
    "candidate",
    "status",
    "status_display",
    "match_score",
    "screening_status",
    "created_at",
}

NO_PROFILE_DETAIL = "No employer profile yet. Complete onboarding first."


def api_client(user) -> APIClient:
    """A real JWT client for `user`; no forced authentication."""
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(user)}")
    return client


def shortlist_url(application) -> str:
    return f"/api/v1/applications/{application.pk}/shortlist/"


def reject_url(application) -> str:
    return f"/api/v1/applications/{application.pk}/reject/"


def entries_for(application):
    """The application's audit trail, oldest first."""
    return AuditLogEntry.objects.filter(
        resource_type="application", resource_id=application.pk
    ).order_by("created_at")


@pytest.fixture
def employer(make_user):
    return make_user("employer_hr")


@pytest.fixture
def profile(employer):
    return EmployerProfile.objects.create(user=employer, company_name="Acme Ltd")


@pytest.fixture
def other_profile(make_user):
    return EmployerProfile.objects.create(
        user=make_user("employer_hr"), company_name="Beta Ltd"
    )


@pytest.fixture
def job(profile):
    return Job.objects.create(
        employer=profile,
        title="Backend Engineer",
        status=Job.Status.ACTIVE,
    )


@pytest.fixture
def candidate(make_user):
    """A profile whose identity is recognisable in the raw response."""
    user = make_user(
        "candidate",
        email="distinctive-candidate@example.com",
        first_name="Zubaida",
        last_name="Rahman",
    )
    return CandidateProfile.objects.create(
        user=user,
        title="Backend developer",
        location="Dhaka",
        skills=["Python", "PostgreSQL"],
    )


@pytest.fixture
def application(job, candidate):
    return Application.objects.create(job=job, candidate=candidate)


def make_application(job, candidate, *, status, **extra) -> Application:
    return Application.objects.create(
        job=job, candidate=candidate, status=status, **extra
    )


# ------------------------------------------------------------- permission


def test_anonymous_cannot_shortlist(application):
    response = APIClient().post(shortlist_url(application))
    assert response.status_code == 401
    application.refresh_from_db()
    assert application.status == Status.APPLIED


def test_a_candidate_cannot_shortlist(application, candidate):
    response = api_client(candidate.user).post(shortlist_url(application))
    assert response.status_code == 403
    application.refresh_from_db()
    assert application.status == Status.APPLIED


def test_an_interviewer_cannot_reject(application, make_user):
    interviewer = make_user("interviewer")
    response = api_client(interviewer).post(reject_url(application))
    assert response.status_code == 403
    application.refresh_from_db()
    assert application.status == Status.APPLIED


def test_an_admin_without_the_employer_group_cannot_reject(application, make_user):
    admin = make_user()
    response = api_client(admin).post(reject_url(application))
    assert response.status_code == 403
    assert not entries_for(application).exists()


def test_an_employer_without_a_profile_gets_the_onboarding_404(application, make_user):
    employer = make_user("employer_hr")
    response = api_client(employer).post(shortlist_url(application))
    assert response.status_code == 404
    assert response.json()["detail"] == NO_PROFILE_DETAIL
    application.refresh_from_db()
    assert application.status == Status.APPLIED
    assert not entries_for(application).exists()


def test_another_employers_application_is_a_404(application, other_profile):
    """Same answer as an id that exists nowhere: no enumeration."""
    response = api_client(other_profile.user).post(shortlist_url(application))
    assert response.status_code == 404
    assert response.json()["detail"] == "Application not found."
    application.refresh_from_db()
    assert application.status == Status.APPLIED
    assert not entries_for(application).exists()


def test_an_unknown_application_is_a_404(profile, application):
    response = api_client(profile.user).post(
        "/api/v1/applications/00000000-0000-0000-0000-000000000000/shortlist/"
    )
    assert response.status_code == 404


def test_the_actions_are_post_only(application, profile):
    client = api_client(profile.user)
    assert client.get(shortlist_url(application)).status_code == 405
    assert client.get(reject_url(application)).status_code == 405


# --------------------------------------------------------------- shortlist


def test_shortlisting_an_applied_application(application, profile):
    response = api_client(profile.user).post(shortlist_url(application))

    assert response.status_code == 200
    assert response.json()["status"] == Status.SHORTLISTED
    assert response.json()["status_display"] == "Shortlisted"

    application.refresh_from_db()
    assert application.status == Status.SHORTLISTED
    assert application.decided_by == profile.user
    assert application.shortlisted_at is not None
    # No ranking exists in Phase 1, so this is not an override.
    assert application.decision_override is False
    assert application.decision_override_reason == ""


def test_shortlisting_a_screened_application(application, profile):
    application.status = Status.SCREENED
    application.save(update_fields=["status"])

    response = api_client(profile.user).post(shortlist_url(application))

    assert response.status_code == 200
    application.refresh_from_db()
    assert application.status == Status.SHORTLISTED


@pytest.mark.parametrize(
    "gate",
    [Gate.PENDING, Gate.FAILED],
)
def test_the_assessment_gate_blocks_shortlisting(application, profile, gate):
    """REQ-FR-051: the rule is in the service, not only the button."""
    application.assessment_gate_status = gate
    application.save(update_fields=["assessment_gate_status"])

    response = api_client(profile.user).post(shortlist_url(application))

    assert response.status_code == 409
    assert response.json()["detail"] == SHORTLIST_GATE_DETAIL
    application.refresh_from_db()
    assert application.status == Status.APPLIED
    assert application.decided_by is None
    assert not entries_for(application).exists()


@pytest.mark.parametrize("gate", [Gate.NOT_REQUIRED, Gate.PASSED])
def test_a_satisfied_gate_allows_shortlisting(application, profile, gate):
    application.assessment_gate_status = gate
    application.save(update_fields=["assessment_gate_status"])

    response = api_client(profile.user).post(shortlist_url(application))

    assert response.status_code == 200
    application.refresh_from_db()
    assert application.status == Status.SHORTLISTED


def test_a_not_matched_application_must_be_reviewed_first(application, profile):
    """Gap G3: the documented way back is `review/`, not a direct shortlist."""
    application.status = Status.NOT_MATCHED
    application.not_matched_reason = "experience_level"
    application.save(update_fields=["status", "not_matched_reason"])

    response = api_client(profile.user).post(shortlist_url(application))

    assert response.status_code == 409
    assert response.json()["detail"] == NOT_MATCHED_SHORTLIST_DETAIL
    application.refresh_from_db()
    assert application.status == Status.NOT_MATCHED
    assert not entries_for(application).exists()


@pytest.mark.parametrize("status", [Status.INTERVIEW, Status.OFFERED, Status.HIRED])
def test_shortlisting_later_stages_is_a_conflict(application, profile, status):
    application.status = status
    application.save(update_fields=["status"])

    response = api_client(profile.user).post(shortlist_url(application))

    assert response.status_code == 409
    application.refresh_from_db()
    assert application.status == status
    assert not entries_for(application).exists()


def test_a_repeated_shortlist_is_a_no_op(application, profile):
    """Arch Doc §4.3 rule 2, applied to the application lifecycle."""
    client = api_client(profile.user)
    first = client.post(shortlist_url(application))
    assert first.status_code == 200
    application.refresh_from_db()
    stamped = application.shortlisted_at

    second = client.post(shortlist_url(application))

    assert second.status_code == 200
    assert second.json() == first.json()
    application.refresh_from_db()
    assert application.shortlisted_at == stamped
    assert entries_for(application).count() == 1


def test_a_repeated_shortlist_does_not_rewrite_decided_by(
    application, profile, make_user
):
    """A no-op writes nothing, including who decided."""
    first_decider = make_user("employer_manager")
    application.status = Status.SHORTLISTED
    application.decided_by = first_decider
    application.shortlisted_at = timezone.now() - timedelta(days=1)
    application.save(update_fields=["status", "decided_by", "shortlisted_at"])

    response = api_client(profile.user).post(shortlist_url(application))

    assert response.status_code == 200
    application.refresh_from_db()
    assert application.decided_by == first_decider
    assert not entries_for(application).exists()


# ------------------------------------------------------------------ reject


@pytest.mark.parametrize(
    "status",
    [
        Status.APPLIED,
        Status.SCREENED,
        Status.NOT_MATCHED,
        Status.SHORTLISTED,
        Status.INTERVIEW,
        Status.OFFERED,
    ],
)
def test_rejecting_from_any_open_stage(application, profile, status):
    """prd.md §11.3: `rejected` is reachable from any stage."""
    application.status = status
    application.save(update_fields=["status"])

    response = api_client(profile.user).post(reject_url(application))

    assert response.status_code == 200
    assert response.json()["status"] == Status.REJECTED
    application.refresh_from_db()
    assert application.status == Status.REJECTED
    assert application.decided_by == profile.user


def test_a_hired_application_cannot_be_rejected(application, profile):
    application.status = Status.HIRED
    application.save(update_fields=["status"])

    response = api_client(profile.user).post(reject_url(application))

    assert response.status_code == 409
    assert response.json()["detail"] == DECISION_ACTIONS["reject"].conflict_detail
    application.refresh_from_db()
    assert application.status == Status.HIRED
    assert not entries_for(application).exists()


def test_a_repeated_reject_is_a_no_op(application, profile):
    client = api_client(profile.user)
    assert client.post(reject_url(application)).status_code == 200

    response = client.post(reject_url(application))

    assert response.status_code == 200
    application.refresh_from_db()
    assert application.status == Status.REJECTED
    assert entries_for(application).count() == 1


def test_a_rejected_application_cannot_be_shortlisted(application, profile):
    application.status = Status.REJECTED
    application.save(update_fields=["status"])

    response = api_client(profile.user).post(shortlist_url(application))

    assert response.status_code == 409
    application.refresh_from_db()
    assert application.status == Status.REJECTED


# ------------------------------------------------- the transition table


#: What every (status, action) pair must do. `changed`/`noop` are 200,
#: `conflict`/`gate_blocked` are 409. Kept next to the tests rather than imported
#: from `SHORTLIST_SOURCES`/`REJECT_SOURCES`, so the assertion is independent of
#: the code it checks -- the sources could otherwise be edited and the two would
#: agree by construction.
EXPECTED_MATRIX = {
    (Status.APPLIED, "shortlist"): "changed",
    (Status.SCREENED, "shortlist"): "changed",
    (Status.NOT_MATCHED, "shortlist"): "conflict",
    (Status.SHORTLISTED, "shortlist"): "noop",
    (Status.INTERVIEW, "shortlist"): "conflict",
    (Status.OFFERED, "shortlist"): "conflict",
    (Status.HIRED, "shortlist"): "conflict",
    (Status.REJECTED, "shortlist"): "conflict",
    (Status.APPLIED, "reject"): "changed",
    (Status.SCREENED, "reject"): "changed",
    (Status.NOT_MATCHED, "reject"): "changed",
    (Status.SHORTLISTED, "reject"): "changed",
    (Status.INTERVIEW, "reject"): "changed",
    (Status.OFFERED, "reject"): "changed",
    (Status.HIRED, "reject"): "conflict",
    (Status.REJECTED, "reject"): "noop",
}


def test_the_matrix_covers_every_status_and_action():
    """A new status must be given a decision, not inherit one."""
    covered = {(status, action) for status, action in EXPECTED_MATRIX}
    assert covered == {
        (status, action) for status in Status for action in DECISION_ACTIONS
    }


@pytest.mark.parametrize("status,action", sorted(EXPECTED_MATRIX))
def test_every_transition_matches_the_table(application, profile, status, action):
    application.status = status
    application.save(update_fields=["status"])
    url = (
        shortlist_url(application) if action == "shortlist" else reject_url(application)
    )

    response = api_client(profile.user).post(url)

    expected = EXPECTED_MATRIX[(status, action)]
    assert response.status_code == (200 if expected in ("changed", "noop") else 409)
    application.refresh_from_db()
    if expected == "changed":
        assert application.status == DECISION_ACTIONS[action].to_status
        assert entries_for(application).count() == 1
    else:
        assert application.status == status
        assert not entries_for(application).exists()


def test_the_service_reports_the_outcome_without_http(application, profile):
    """Batch 1.42's page reuses the rule and maps the outcome itself."""
    outcome, unchanged = decide_application(
        application_id=application.pk,
        employer=profile,
        action="shortlist",
        actor=profile.user,
    )
    assert outcome == DECISION_CHANGED
    assert unchanged.status == Status.SHORTLISTED

    again, _ = decide_application(
        application_id=application.pk,
        employer=profile,
        action="shortlist",
        actor=profile.user,
    )
    assert again == DECISION_NOOP

    application.status = Status.HIRED
    application.save(update_fields=["status"])
    refused, _ = decide_application(
        application_id=application.pk,
        employer=profile,
        action="shortlist",
        actor=profile.user,
    )
    assert refused == DECISION_CONFLICT

    application.status = Status.APPLIED
    application.assessment_gate_status = Gate.PENDING
    application.save(update_fields=["status", "assessment_gate_status"])
    blocked, _ = decide_application(
        application_id=application.pk,
        employer=profile,
        action="shortlist",
        actor=profile.user,
    )
    assert blocked == DECISION_GATE_BLOCKED


# ----------------------------------------------------------- audit trail


def test_a_shortlist_writes_one_audit_entry(application, profile):
    api_client(profile.user).post(shortlist_url(application))

    entry = entries_for(application).get()
    assert entry.action == "application.shortlisted"
    assert entry.resource_type == "application"
    assert entry.resource_id == application.pk
    assert entry.actor == profile.user
    assert entry.result == "success"
    assert entry.details == {"from": Status.APPLIED, "to": Status.SHORTLISTED}


def test_a_reject_writes_one_audit_entry(application, profile):
    api_client(profile.user).post(reject_url(application))

    entry = entries_for(application).get()
    assert entry.action == "application.rejected"
    assert entry.actor == profile.user
    assert entry.details == {"from": Status.APPLIED, "to": Status.REJECTED}


def test_the_audit_entry_holds_no_identity_or_reason(application, profile):
    """`AuditLogEntry` is append-only and must never hold PII or rationale text."""
    reason = "Referred by Zubaida's former manager; strong Python"
    response = api_client(profile.user).post(
        reject_url(application), {"reason": reason}, format="json"
    )
    assert response.status_code == 200

    entry = entries_for(application).get()
    assert set(entry.details) == {"from", "to"}
    assert "Zubaida" not in str(entry.details)
    assert reason not in str(entry.details)


# ----------------------------------------------------------- reason field


def test_a_reason_is_accepted_and_does_not_claim_an_override(application, profile):
    """REQ-FR-052 makes the reason mandatory for overrides in Phase 2 only.

    There is no ranking cut-off in Phase 1 and no column for a non-override
    reason, so the field is validated and not persisted; what must not happen is
    a `decision_override` that nobody made.
    """
    response = api_client(profile.user).post(
        shortlist_url(application), {"reason": "Strong PostgreSQL work"}, format="json"
    )

    assert response.status_code == 200
    application.refresh_from_db()
    assert application.decision_override is False
    assert application.decision_override_reason == ""
    assert application.status == Status.SHORTLISTED


def test_the_body_cannot_name_a_status(application, profile):
    """The action decides the target state (Complete Doc §C.12)."""
    response = api_client(profile.user).post(
        shortlist_url(application), {"status": Status.HIRED}, format="json"
    )

    assert response.status_code == 200
    application.refresh_from_db()
    assert application.status == Status.SHORTLISTED


def test_a_reason_longer_than_a_sentence_is_still_accepted(application, profile):
    """No length rule is documented for the Phase 2 override reason."""
    response = api_client(profile.user).post(
        shortlist_url(application), {"reason": "x" * 500}, format="json"
    )
    assert response.status_code == 200


# ------------------------------------------------------- privacy of the row


def test_the_response_is_the_inbox_row_by_alias(application, profile):
    response = api_client(profile.user).post(shortlist_url(application))

    body = response.json()
    assert set(body) == EXPECTED_FIELDS
    assert set(body["candidate"]) == {
        "alias",
        "title",
        "location",
        "remote_ok",
        "skills",
    }
    assert body["id"] == str(application.pk)


def test_shortlisting_does_not_reveal_the_candidate(application, profile):
    """REQ-FR-029: the reveal is a separate audited action, not a side effect.

    Checked on the raw body, so a nested or renamed field still fails.
    """
    response = api_client(profile.user).post(shortlist_url(application))

    raw = response.content.decode()
    assert "Zubaida" not in raw
    assert "Rahman" not in raw
    assert "distinctive-candidate@example.com" not in raw
    assert str(application.candidate_id) not in raw


# ------------------------------------------------------------ G3: filters


def test_only_a_person_writes_rejected(application, profile):
    """Gap G3: the filter produced `not_matched`; the rejection is the person's."""
    application.status = Status.NOT_MATCHED
    application.not_matched_reason = "experience_level"
    application.filter_rules_version = 3
    application.save(
        update_fields=["status", "not_matched_reason", "filter_rules_version"]
    )

    response = api_client(profile.user).post(reject_url(application))

    assert response.status_code == 200
    application.refresh_from_db()
    assert application.status == Status.REJECTED
    assert application.decided_by == profile.user
    entry = entries_for(application).get()
    assert entry.actor == profile.user
    assert entry.details == {"from": Status.NOT_MATCHED, "to": Status.REJECTED}
    # The filter's own record is left intact: the exclusion reason is evidence,
    # not something a later decision overwrites.
    assert application.not_matched_reason == "experience_level"
    assert application.filter_rules_version == 3


def test_the_screening_writer_cannot_write_a_decision():
    """`ai.screening` updates `SCORING_FIELDS` only, so no filter can reject.

    This is the enforcement behind Gap G3 that a transition test cannot show: the
    table has no automatic source, and the only writer of the AI columns is
    forbidden from touching `status` or `decided_by`.
    """
    forbidden = {
        "status",
        "decided_by",
        "decision_override",
        "decision_override_reason",
    }
    assert forbidden.isdisjoint(SCORING_FIELDS)
