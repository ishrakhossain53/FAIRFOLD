"""API views for application decisions (REQ-FR-052, REQ-FR-023, batch 1.41).

Two action endpoints, one implementation:

    POST /api/v1/applications/{id}/shortlist/
    POST /api/v1/applications/{id}/reject/

**Why actions and not `PATCH applications/{id}/`.** Complete Doc §C.12 is
explicit: the reason has to be enforceable by the serializer, and a generic field
write cannot refuse an action it does not know about. The §C.12 rules also mean
the only way to reach `shortlisted` or `rejected` is through a named verb, so a
decision is always auditable as a decision.

**Ownership is in the lookup, not a branch.** `job__employer` is part of the
query, so another employer's application id and an id that exists nowhere produce
the same `404`. The caller's own `EmployerProfile` is resolved first, so an
employer who has not onboarded gets the same `404` sentence as `/me/`.

**The response is the inbox row.** It reuses `EmployerApplicationListSerializer`,
so a client that has just shortlisted a row does not need a second parser and the
alias-only identity rule (REQ-FR-029, REQ-FR-054) has exactly one implementation.
The candidate's name is still withheld: reveal-on-shortlist is a separate, audited
action (`REQ-FR-030`, batch 2.x), not a side effect of this endpoint.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsEmployer
from employers.api_views import employer_profile_for
from matching.models import Application
from matching.serializers import (
    ApplicationDecisionSerializer,
    EmployerApplicationListSerializer,
)
from matching.services import (
    DECISION_ACTIONS,
    DECISION_CONFLICT,
    DECISION_GATE_BLOCKED,
    NOT_MATCHED_SHORTLIST_DETAIL,
    SHORTLIST_GATE_DETAIL,
    application_status,
    decide_application,
)


class _ApplicationDecisionView(APIView):
    """Shared implementation of the two decision actions.

    The subclasses differ only in the table row they name, so ownership, the
    reason body, the outcomes and the response shape are written once. `action`
    is the key into `matching.services.DECISION_ACTIONS`; it is *not* taken from
    the request, so a client cannot name a transition the URL does not offer.
    """

    permission_classes = [IsEmployer]

    #: Key into `DECISION_ACTIONS`.
    action: str = ""

    def conflict_detail(self, application: Application) -> str:
        """The sentence for a refusal. Subclasses narrow the generic one."""
        return DECISION_ACTIONS[self.action].conflict_detail

    def post(self, request, application_id) -> Response:
        # Resolve the profile first: it is the ownership key, and a caller with
        # no profile has nothing to own.
        profile = employer_profile_for(request.user)

        # The reason is validated and then deliberately not persisted (see
        # `ApplicationDecisionSerializer`). Validating it anyway means a Phase 2
        # client can send it today without a contract change.
        body = ApplicationDecisionSerializer(data=request.data)
        body.is_valid(raise_exception=True)

        try:
            outcome, application = decide_application(
                application_id=application_id,
                employer=profile,
                action=self.action,
                actor=request.user,
            )
        except Application.DoesNotExist:
            # Same 404 for "not yours" and "no such row": a distinguishable answer
            # would let one employer probe another's application ids.
            return Response(
                {"detail": "Application not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if outcome == DECISION_GATE_BLOCKED:
            # REQ-FR-051. 409 because the request is well formed and the account
            # is entitled; the application's gate is simply not satisfied.
            return Response(
                {"detail": SHORTLIST_GATE_DETAIL},
                status=status.HTTP_409_CONFLICT,
            )

        if outcome == DECISION_CONFLICT:
            return Response(
                {"detail": self.conflict_detail(application)},
                status=status.HTTP_409_CONFLICT,
            )

        # `DECISION_CHANGED` and `DECISION_NOOP` answer identically: a repeated
        # action is a no-op (Arch Doc §4.3 rule 2), and a 200 with the row is the
        # honest answer for a button that was already clicked.
        return Response(
            EmployerApplicationListSerializer(
                application, context={"employer": profile}
            ).data
        )


@extend_schema(
    request=ApplicationDecisionSerializer,
    responses={200: EmployerApplicationListSerializer},
    summary="Shortlist one application",
    description=(
        "Employer group only, owner only. `applied` or `screened` -> "
        "`shortlisted`; repeating it is a no-op. 409 while the assessment gate is "
        "`pending` or `failed` (REQ-FR-051), and 409 for a `not_matched` "
        "application, which must be pulled back into review first (Gap G3). "
        "Records `decided_by`, `shortlisted_at` and one `application.shortlisted` "
        "audit entry. The body is `{reason?}`, accepted and not yet persisted; "
        "the response is the inbox row, still by alias (REQ-FR-029/054)."
    ),
)
class ApplicationShortlistView(_ApplicationDecisionView):
    """`POST /api/v1/applications/{id}/shortlist/` -- REQ-FR-023, REQ-FR-052."""

    action = "shortlist"

    def conflict_detail(self, application: Application) -> str:
        """Gap G3 gets its own sentence: "illegal" and "review it first" are
        different problems, and the second one has a documented way out."""
        if application.status == application_status(Application.Status.NOT_MATCHED):
            return NOT_MATCHED_SHORTLIST_DETAIL
        return super().conflict_detail(application)


@extend_schema(
    request=ApplicationDecisionSerializer,
    responses={200: EmployerApplicationListSerializer},
    summary="Reject one application",
    description=(
        "Employer group only, owner only. Rejecting is possible from every stage "
        "except `hired` (prd.md §11.3: `rejected` is reachable from any stage), "
        "including `not_matched` -- only a person may reject (Gap G3). Repeating "
        "it is a no-op. Records `decided_by` and one `application.rejected` audit "
        "entry. The body is `{reason?}`, accepted and not yet persisted; the "
        "response is the inbox row, still by alias."
    ),
)
class ApplicationRejectView(_ApplicationDecisionView):
    """`POST /api/v1/applications/{id}/reject/` -- REQ-FR-023, REQ-FR-052.

    REQ-FR-052's override (`decision_override`, the `ai_decision` audit class and
    the required reason) is Phase 2, because it is defined relative to a ranking
    cut-off. This endpoint is the same decision without a ranking to be measured
    against, and it records who decided so the trail is complete either way.
    """

    action = "reject"
