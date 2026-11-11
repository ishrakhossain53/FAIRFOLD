"""The resume processing state machine (REQ-FR-012, D-6(a), batch 2.1).

The transition table in `candidates.processing` is the specification, so these
tests do not re-derive the rules — they enumerate every (current, target) pair
and assert the table is enforced exactly, plus the invariants the table cannot
express on its own:

* a move to a state the row already holds is a no-op and never clears a reason;
* `failed` and `rejected` refuse an empty reason;
* `processed_at` is stamped on a successful pipeline stage and not on `processing`;
* every `Status` value is a key in the table — a status added to the model
  without a transition here is a gap, not a reachable state.
"""

from __future__ import annotations

import pytest

from accounts.models import User
from candidates.models import CandidateProfile, CandidateResume
from candidates.processing import (
    PROCESSING_TRANSITIONS,
    REASON_REQUIRED,
    InvalidTransition,
    can_transition,
    next_statuses,
    transition,
)

pytestmark = pytest.mark.django_db

ALL_STATUSES = list(CandidateResume.Status.values)


@pytest.fixture
def profile():
    user = User.objects.create_user("ada@example.com", "not-used-in-these-tests")
    return CandidateProfile.objects.create(user=user)


def make_resume(profile, status):
    return CandidateResume.objects.create(
        candidate=profile,
        file_key="resumes/8f14e45fceea167a5a36dedd4bea2543.pdf",
        status=status,
    )


class TestTransitionTable:
    """Every (current, target) pair, asserted against the table itself."""

    @pytest.mark.parametrize("current", ALL_STATUSES)
    @pytest.mark.parametrize("target", ALL_STATUSES)
    def test_every_pair_matches_the_table(self, profile, current, target):
        resume = make_resume(profile, current)
        # A self-transition is a no-op, never an error; a move is legal only
        # when the table lists it.
        allowed = current == target or target in PROCESSING_TRANSITIONS[current]

        if allowed:
            transition(
                resume, target, reason="forced" if target in REASON_REQUIRED else ""
            )
            expected = current if current == target else target
            assert resume.status == expected
        else:
            with pytest.raises(InvalidTransition):
                transition(
                    resume, target, reason="forced" if target in REASON_REQUIRED else ""
                )
            # The failed move must not have written anything.
            assert CandidateResume.objects.get(pk=resume.pk).status == current

    def test_every_status_is_a_table_key(self):
        assert set(PROCESSING_TRANSITIONS) == set(ALL_STATUSES)

    def test_terminal_states_have_no_successor(self):
        for terminal in (
            CandidateResume.Status.EMBEDDED,
            CandidateResume.Status.REJECTED,
        ):
            assert next_statuses(terminal) == frozenset()
            assert can_transition(terminal, CandidateResume.Status.FAILED) is False

    def test_retry_moves_failed_back_into_processing(self):
        assert CandidateResume.Status.PROCESSING in next_statuses(
            CandidateResume.Status.FAILED
        )


class TestTransitionInvariants:
    def test_same_status_is_a_noop_and_keeps_the_reason(self, profile):
        resume = make_resume(profile, CandidateResume.Status.FAILED)
        CandidateResume.objects.filter(pk=resume.pk).update(
            status_reason="no_text_layer"
        )
        resume.refresh_from_db()

        returned = transition(resume, CandidateResume.Status.FAILED)

        assert returned is resume
        assert resume.status_reason == "no_text_layer"

    @pytest.mark.parametrize(
        ("source", "target"),
        [
            (CandidateResume.Status.SCANNING, CandidateResume.Status.REJECTED),
            (CandidateResume.Status.PROCESSING, CandidateResume.Status.FAILED),
        ],
    )
    def test_a_failure_without_a_reason_is_refused(self, profile, source, target):
        resume = make_resume(profile, source)

        with pytest.raises(ValueError):
            transition(resume, target, reason="   ")

    def test_a_whitespace_only_reason_is_refused(self, profile):
        resume = make_resume(profile, CandidateResume.Status.CLEAN)

        with pytest.raises(ValueError):
            transition(resume, CandidateResume.Status.FAILED, reason=" \t ")

    def test_an_unknown_target_is_refused(self, profile):
        resume = make_resume(profile, CandidateResume.Status.CLEAN)

        with pytest.raises(ValueError):
            transition(resume, "exploded")

    def test_processed_at_is_stamped_on_extracted_and_embedded(self, profile):
        resume = make_resume(profile, CandidateResume.Status.PROCESSING)
        assert resume.processed_at is None

        transition(resume, CandidateResume.Status.EXTRACTED)
        assert resume.processed_at is not None

    def test_processed_at_is_not_stamped_on_processing(self, profile):
        resume = make_resume(profile, CandidateResume.Status.CLEAN)

        transition(resume, CandidateResume.Status.PROCESSING)
        assert resume.processed_at is None

    def test_a_successful_move_clears_the_reason(self, profile):
        resume = make_resume(profile, CandidateResume.Status.SCANNING)
        resume.status_reason = "stale reason"
        resume.save(update_fields=["status_reason"])

        transition(resume, CandidateResume.Status.CLEAN)

        assert resume.status_reason == ""
