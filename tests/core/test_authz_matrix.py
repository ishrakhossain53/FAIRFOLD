"""Authorization matrix for every registered route (batch 1.13, REQ-SEC-010).

The matrix below is the contract: for each route, the status an anonymous
visitor, a candidate, an employer and a platform admin must receive. The test
does not snapshot whatever the code happens to return -- it states the answer
and fails when the code disagrees.

Two properties make this fail closed:

* **Route discovery is independent of the matrix.** Every route the URL
  resolver exposes is collected and compared with the matrix in both
  directions. Adding a route without a rule fails here, and so does leaving a
  rule for a route that no longer exists. A test that only walks the matrix
  would keep passing while a new endpoint shipped unprotected.
* **Parameterised routes need an explicit sample.** A path with `<...>` needs a
  concrete object id to request, and guessing one would make the expected
  status depend on which row exists. `PARAMETERISED_SAMPLES` names the sample
  used for each template; a template with no entry fails, so a new
  parameterised route is still a decision rather than a silent skip. The only
  automatic exception is DRF's `<drf_format_suffix:format>` duplicate, which
  resolves to the same view as its parent path.

Deliberate exclusions, all documented in `docs/AUTHZ_MATRIX.md`:

* `django-admin/` is one row. Its ~80 generated CRUD patterns all pass through
  the same staff check, and listing each model's history/delete URLs would make
  the matrix unreadable without adding a distinct rule.
* `static/` and `media/` are development-only mounts, not application routes.
* `api/schema/` and `api/docs/` exist only with `DEBUG` on (see
  `config/urls.py`); they are not part of the production surface.

Actors are Django sessions, not JWTs, because the same `Client` then exercises
the template pages and the API through the authenticator each surface actually
uses. The API's 401 is produced by `SessionAuthentication`'s unauthenticated
path, which is the same `NotAuthenticated` response the JWT authenticator
returns; `tests/accounts/test_me_api.py` covers the JWT path separately.
"""

from __future__ import annotations

import pytest
from django.conf import settings
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.core.management import call_command
from django.http import HttpResponse
from django.test import Client
from django.urls import URLPattern, URLResolver, get_resolver, include, path

from accounts.models import User

pytestmark = pytest.mark.django_db

ACTORS = ("anonymous", "candidate", "employer", "admin")

# method -> expected status per actor. GET is used for pages and reads; POST with
# an empty body for endpoints whose only verb is POST. A path that answers more
# than one verb carries a `methods` map instead of a single `method`; see
# `method_specs`. The body is deliberately
# invalid: these tests are about who gets past the permission layer, not about
# what a valid payload does. A protected endpoint answers 401 before a serializer
# ever runs, so an empty body cannot mask a missing permission.
AUTHZ_MATRIX: dict[str, dict] = {
    # ---- project pages -------------------------------------------------
    "/": {
        "method": "get",
        "anonymous": 200,
        "candidate": 200,
        "employer": 200,
        "admin": 200,
    },
    "/api/demo/": {
        "method": "get",
        "anonymous": 200,
        "candidate": 200,
        "employer": 200,
        "admin": 200,
    },
    "/health/": {
        "method": "get",
        "anonymous": 200,
        "candidate": 200,
        "employer": 200,
        "admin": 200,
    },
    "/health/ready/": {
        "method": "get",
        "anonymous": 200,
        "candidate": 200,
        "employer": 200,
        "admin": 200,
    },
    # ---- public auth pages (design.md pages #6, #7, #9-#11) ------------
    "/register/": {
        "method": "get",
        "anonymous": 200,
        "candidate": 200,
        "employer": 200,
        "admin": 200,
    },
    # No pending address in a fresh client session: the page redirects to
    # registration rather than rendering an empty "we sent a link" panel.
    "/register/check-email/": {
        "method": "get",
        "anonymous": 302,
        "candidate": 302,
        "employer": 302,
        "admin": 302,
    },
    # No token: the documented invalid state is 400, not 200.
    "/verify-email/": {
        "method": "get",
        "anonymous": 400,
        "candidate": 400,
        "employer": 400,
        "admin": 400,
    },
    # POST-only; no session address, so it redirects to registration.
    "/verify-email/resend/": {
        "method": "post",
        "anonymous": 302,
        "candidate": 302,
        "employer": 302,
        "admin": 302,
    },
    # A signed-in user is sent to their landing page instead of the form.
    "/login/": {
        "method": "get",
        "anonymous": 200,
        "candidate": 302,
        "employer": 302,
        "admin": 302,
    },
    # POST-only by design: a GET logout would be a CSRF-able action.
    "/logout/": {
        "method": "post",
        "anonymous": 302,
        "candidate": 302,
        "employer": 302,
        "admin": 302,
    },
    "/forgot-password/": {
        "method": "get",
        "anonymous": 200,
        "candidate": 200,
        "employer": 200,
        "admin": 200,
    },
    # No uid/token: the documented "this link has expired" state is 400.
    "/reset-password/": {
        "method": "get",
        "anonymous": 400,
        "candidate": 400,
        "employer": 400,
        "admin": 400,
    },
    # ---- candidate portal pages (design.md pages #14 and #16) ----------
    # Candidate-only. Anonymous goes to /login/ with a `next`; an authenticated
    # employer, interviewer or admin gets 403 and no profile is created for them.
    "/candidate/onboarding/": {
        "method": "get",
        "anonymous": 302,
        "candidate": 200,
        "employer": 403,
        "admin": 403,
    },
    # The candidate actor has no profile in this fixture, so page #16 forwards
    # them to onboarding. That redirect is the documented empty state.
    "/candidate/profile/": {
        "method": "get",
        "anonymous": 302,
        "candidate": 302,
        "employer": 403,
        "admin": 403,
    },
    # POST-only inline edit. With no profile there is nothing to edit: the view
    # sends the candidate to onboarding before it looks at the section field.
    "/candidate/profile/edit/": {
        "method": "post",
        "anonymous": 302,
        "candidate": 302,
        "employer": 403,
        "admin": 403,
    },
    # Page #17 (batch 1.22). Same shape as `/candidate/profile/`: the candidate
    # actor has no profile in this fixture, so the page forwards to onboarding.
    "/candidate/resumes/": {
        "method": "get",
        "anonymous": 302,
        "candidate": 302,
        "employer": 403,
        "admin": 403,
    },
    # Delete confirmation and the POST that performs it, on one fixed path. With
    # no `resume` parameter there is nothing to confirm, so the candidate gets the
    # 404 the view gives an unknown id.
    "/candidate/resumes/delete/": {
        "methods": {
            "get": {
                "anonymous": 302,
                "candidate": 404,
                "employer": 403,
                "admin": 403,
            },
            "post": {
                "anonymous": 302,
                "candidate": 404,
                "employer": 403,
                "admin": 403,
            },
        },
    },
    # Pages #28/#29 (REQ-FR-023, batch 1.39). Candidate-only. The fixture
    # candidate has no profile, so the tracker forwards to onboarding; the detail
    # of the nil UUID is the owner-scoped lookup's 404.
    "/candidate/applications/": {
        "method": "get",
        "anonymous": 302,
        "candidate": 302,
        "employer": 403,
        "admin": 403,
    },
    "/candidate/applications/00000000-0000-0000-0000-000000000000/": {
        "method": "get",
        "anonymous": 302,
        "candidate": 404,
        "employer": 403,
        "admin": 403,
    },
    # ---- employer portal pages (design.md page #33, batch 1.25) --------
    # Employer-only. Anonymous goes to /login/ with a `next`; a candidate,
    # interviewer or admin gets 403. The employer actor has no profile in this
    # fixture, so the GET renders onboarding and an empty POST re-renders it
    # with the required-field error.
    "/employer/onboarding/": {
        "methods": {
            "get": {
                "anonymous": 302,
                "candidate": 403,
                "employer": 200,
                "admin": 403,
            },
            "post": {
                "anonymous": 302,
                "candidate": 403,
                "employer": 200,
                "admin": 403,
            },
        },
    },
    # The company page forwards an employer without a profile to onboarding.
    # That redirect is the documented empty state.
    "/employer/company/": {
        "method": "get",
        "anonymous": 302,
        "candidate": 403,
        "employer": 302,
        "admin": 403,
    },
    # POST-only edit. With no profile there is nothing to edit: the view sends
    # the employer to onboarding before it binds the form.
    "/employer/company/edit/": {
        "method": "post",
        "anonymous": 302,
        "candidate": 403,
        "employer": 302,
        "admin": 403,
    },
    # ---- employer job management (pages #35-#37, batch 1.30) -----------
    # The employer actor has no profile in this fixture, so every page below
    # forwards to onboarding (302) before it looks at anything else. That is the
    # documented empty state, not a permission decision.
    "/employer/jobs/": {
        "method": "get",
        "anonymous": 302,
        "candidate": 403,
        "employer": 302,
        "admin": 403,
    },
    "/employer/jobs/new/": {
        "methods": {
            "get": {
                "anonymous": 302,
                "candidate": 403,
                "employer": 302,
                "admin": 403,
            },
            "post": {
                "anonymous": 302,
                "candidate": 403,
                "employer": 302,
                "admin": 403,
            },
        },
    },
    # Page #36's live Markdown preview (design.md 7.22). Read-only: it renders
    # the posted strings and never looks up a job, so the profile redirect is
    # the only thing between an employer and the fragment.
    "/employer/jobs/preview/": {
        "method": "post",
        "anonymous": 302,
        "candidate": 403,
        "employer": 302,
        "admin": 403,
    },
    # Page #37. Without a profile the redirect happens before the job lookup,
    # so the nil UUID never has to exist for this row to be meaningful. The
    # owner path and the 404 for another employer are in
    # tests/employers/test_job_management_ui.py.
    "/employer/jobs/00000000-0000-0000-0000-000000000000/": {
        "method": "get",
        "anonymous": 302,
        "candidate": 403,
        "employer": 302,
        "admin": 403,
    },
    # Page #36 in edit mode. POST is a draft save, not a state action: the
    # status is never writable from the form (REQ-FR-027).
    "/employer/jobs/00000000-0000-0000-0000-000000000000/edit/": {
        "methods": {
            "get": {
                "anonymous": 302,
                "candidate": 403,
                "employer": 302,
                "admin": 403,
            },
            "post": {
                "anonymous": 302,
                "candidate": 403,
                "employer": 302,
                "admin": 403,
            },
        },
    },
    # Page #36's auto-save (HTMX). Same guard order as the edit page.
    "/employer/jobs/00000000-0000-0000-0000-000000000000/autosave/": {
        "method": "post",
        "anonymous": 302,
        "candidate": 403,
        "employer": 302,
        "admin": 403,
    },
    # The four §4.3 actions, POST-only. The matrix's empty body never reaches
    # the transition: the profile redirect comes first, and for an owner the
    # service refuses an off-matrix move with the API's 409.
    "/employer/jobs/00000000-0000-0000-0000-000000000000/activate/": {
        "method": "post",
        "anonymous": 302,
        "candidate": 403,
        "employer": 302,
        "admin": 403,
    },
    "/employer/jobs/00000000-0000-0000-0000-000000000000/pause/": {
        "method": "post",
        "anonymous": 302,
        "candidate": 403,
        "employer": 302,
        "admin": 403,
    },
    "/employer/jobs/00000000-0000-0000-0000-000000000000/close/": {
        "method": "post",
        "anonymous": 302,
        "candidate": 403,
        "employer": 302,
        "admin": 403,
    },
    "/employer/jobs/00000000-0000-0000-0000-000000000000/delete/": {
        "method": "post",
        "anonymous": 302,
        "candidate": 403,
        "employer": 302,
        "admin": 403,
    },
    # Page #41 (S13), the AI assessment column. The matrix requests the nil
    # UUID, which exists nowhere, so the employer actor gets the same 404 another
    # employer would for a real application. The 200 path is proved by
    # tests/employers/test_application_rationale_ui.py, which builds a job.
    "/employer/applications/00000000-0000-0000-0000-000000000000/": {
        "method": "get",
        "anonymous": 302,
        "candidate": 403,
        "employer": 404,
        "admin": 403,
    },
    # Django admin: anonymous and non-staff are redirected to its login page.
    # This is the only route where the admin actor sees something the employer
    # does not, and it is enforced by `is_staff`, not by a role group.
    "/django-admin/": {
        "method": "get",
        "anonymous": 302,
        "candidate": 302,
        "employer": 302,
        "admin": 200,
    },
    # ---- API index and public auth endpoints ---------------------------
    "/api/v1/": {
        "method": "get",
        "anonymous": 200,
        "candidate": 200,
        "employer": 200,
        "admin": 200,
    },
    "/api/v1/auth/register/": {
        "method": "post",
        "anonymous": 400,
        "candidate": 400,
        "employer": 400,
        "admin": 400,
    },
    "/api/v1/auth/verify-email/": {
        "method": "post",
        "anonymous": 400,
        "candidate": 400,
        "employer": 400,
        "admin": 400,
    },
    "/api/v1/auth/verify-email/resend/": {
        "method": "post",
        "anonymous": 400,
        "candidate": 400,
        "employer": 400,
        "admin": 400,
    },
    "/api/v1/auth/login/": {
        "method": "post",
        "anonymous": 400,
        "candidate": 400,
        "employer": 400,
        "admin": 400,
    },
    "/api/v1/auth/refresh/": {
        "method": "post",
        "anonymous": 400,
        "candidate": 400,
        "employer": 400,
        "admin": 400,
    },
    "/api/v1/auth/logout/": {
        "method": "post",
        "anonymous": 400,
        "candidate": 400,
        "employer": 400,
        "admin": 400,
    },
    "/api/v1/auth/password/reset/": {
        "method": "post",
        "anonymous": 400,
        "candidate": 400,
        "employer": 400,
        "admin": 400,
    },
    "/api/v1/auth/password/reset/confirm/": {
        "method": "post",
        "anonymous": 400,
        "candidate": 400,
        "employer": 400,
        "admin": 400,
    },
    # ---- authenticated API ---------------------------------------------
    # Authenticated for every role: an account belongs to its owner, not to a
    # group. Anonymous is 401 (not 403) because no credential was supplied.
    "/api/v1/auth/password/change/": {
        "method": "post",
        "anonymous": 401,
        "candidate": 400,
        "employer": 400,
        "admin": 400,
    },
    "/api/v1/auth/me/": {
        "method": "get",
        "anonymous": 401,
        "candidate": 200,
        "employer": 200,
        "admin": 200,
    },
    # Candidate-only. 404 is the documented "not onboarded yet" state: the
    # candidate passed the permission check, while the employer/admin did not.
    "/api/v1/candidates/me/": {
        "method": "get",
        "anonymous": 401,
        "candidate": 404,
        "employer": 403,
        "admin": 403,
    },
    # Candidate-only. One path, two verbs (batch 1.21 put `GET` beside 1.19's
    # `POST`), so the row carries a per-method map. `POST` gets 400 for a
    # candidate because the empty body fails validation before the profile
    # lookup; a valid body with no profile is 404
    # (tests/candidates/test_resume_upload_api.py). `GET` gets 404 for a
    # candidate because this fixture has no profile yet, and the list is
    # 404-until-onboarding like `/me/` (tests/candidates/test_resume_list_detail_api.py).
    "/api/v1/candidates/resumes/": {
        "methods": {
            "get": {
                "anonymous": 401,
                "candidate": 404,
                "employer": 403,
                "admin": 403,
            },
            "post": {
                "anonymous": 401,
                "candidate": 400,
                "employer": 403,
                "admin": 403,
            },
        },
    },
    # Candidate-only, by object id. The sample id exists nowhere, so the
    # candidate gets the same 404 an unowned id gets -- ownership and existence
    # are one answer by design.
    "/api/v1/candidates/resumes/00000000-0000-0000-0000-000000000000/complete/": {
        "method": "post",
        "anonymous": 401,
        "candidate": 404,
        "employer": 403,
        "admin": 403,
    },
    # Candidate-only and owner-only, same 404 answer for "not yours" and "no such
    # row" (batch 1.21).
    "/api/v1/candidates/resumes/00000000-0000-0000-0000-000000000000/": {
        "methods": {
            "get": {
                "anonymous": 401,
                "candidate": 404,
                "employer": 403,
                "admin": 403,
            },
            "delete": {
                "anonymous": 401,
                "candidate": 404,
                "employer": 403,
                "admin": 403,
            },
        },
    },
    # Candidate application history (REQ-FR-023, batch 1.38). Candidate-only and
    # owner-scoped. The fixture candidate has no profile, so the list answers the
    # documented 404-before-onboarding (same as `/me/`) and the nil UUID is a 404
    # from the ownership filter. The 200 path is in
    # tests/matching/test_application_list_detail_api.py.
    "/api/v1/candidates/applications/": {
        "method": "get",
        "anonymous": 401,
        "candidate": 404,
        "employer": 403,
        "admin": 403,
    },
    "/api/v1/candidates/applications/00000000-0000-0000-0000-000000000000/": {
        "method": "get",
        "anonymous": 401,
        "candidate": 404,
        "employer": 403,
        "admin": 403,
    },
    # Employer-only. 404 is the documented "not onboarded yet" state: the
    # employer passed the permission check, while the candidate/interviewer and
    # admin did not. PATCH is covered by
    # tests/employers/test_employer_profile_api.py.
    "/api/v1/employers/me/": {
        "method": "get",
        "anonymous": 401,
        "candidate": 403,
        "employer": 404,
        "admin": 403,
    },
    # Draft-job creation (REQ-FR-025, batch 1.27). The employer actor has no
    # company profile in this fixture, so the permission check passes and the
    # onboarding check answers 404 -- the same shape as the profile endpoint
    # above. The empty POST body never reaches the serializer for any of the
    # denied actors. Body validation and ownership are covered by
    # tests/employers/test_job_create_api.py.
    "/api/v1/jobs/": {
        "method": "post",
        "anonymous": 401,
        "candidate": 403,
        "employer": 404,
        "admin": 403,
    },
    # Public job board (REQ-FR-042, batch 1.31). Open by design: the project
    # default is IsAuthenticated, so `AllowAny` here is a decision. The detail
    # sample is the nil UUID, which exists nowhere, so every actor gets the same
    # 404; a non-active job answers identically (Complete Doc §C.12).
    "/api/v1/jobs/public/": {
        "method": "get",
        "anonymous": 200,
        "candidate": 200,
        "employer": 200,
        "admin": 200,
    },
    "/api/v1/jobs/public/00000000-0000-0000-0000-000000000000/": {
        "method": "get",
        "anonymous": 404,
        "candidate": 404,
        "employer": 404,
        "admin": 404,
    },
    # Public job-board pages #4 and #5 (REQ-FR-042, batch 1.33). Anonymous by
    # design, like the API above. The detail sample is the nil UUID, so the
    # active-only query returns the same 404 for every actor.
    "/jobs/": {
        "method": "get",
        "anonymous": 200,
        "candidate": 200,
        "employer": 200,
        "admin": 200,
    },
    "/jobs/00000000-0000-0000-0000-000000000000/": {
        "method": "get",
        "anonymous": 404,
        "candidate": 404,
        "employer": 404,
        "admin": 404,
    },
    # Candidate-only POST from page #5 (REQ-FR-022, batch 1.37). Anonymous gets
    # the login redirect; the nil UUID is a 404 after the guard passes; the other
    # roles are refused before the job lookup.
    "/jobs/00000000-0000-0000-0000-000000000000/apply/": {
        "method": "post",
        "anonymous": 302,
        "candidate": 404,
        "employer": 403,
        "admin": 403,
    },
    # Job detail and the three state actions (REQ-FR-026/027, batches 1.28/1.29).
    # Same shape as the collection: the employer actor has no company profile in
    # this fixture, so the onboarding check answers 404 after the permission
    # check passes. Ownership (another employer's id is also 404), the 409
    # transitions and the draft-only rules are covered by
    # tests/employers/test_job_edit_delete_api.py and test_job_lifecycle_api.py.
    "/api/v1/jobs/00000000-0000-0000-0000-000000000000/": {
        "methods": {
            "get": {
                "anonymous": 401,
                "candidate": 403,
                "employer": 404,
                "admin": 403,
            },
            "patch": {
                "anonymous": 401,
                "candidate": 403,
                "employer": 404,
                "admin": 403,
            },
            "delete": {
                "anonymous": 401,
                "candidate": 403,
                "employer": 404,
                "admin": 403,
            },
        },
    },
    "/api/v1/jobs/00000000-0000-0000-0000-000000000000/activate/": {
        "method": "post",
        "anonymous": 401,
        "candidate": 403,
        "employer": 404,
        "admin": 403,
    },
    "/api/v1/jobs/00000000-0000-0000-0000-000000000000/pause/": {
        "method": "post",
        "anonymous": 401,
        "candidate": 403,
        "employer": 404,
        "admin": 403,
    },
    "/api/v1/jobs/00000000-0000-0000-0000-000000000000/close/": {
        "method": "post",
        "anonymous": 401,
        "candidate": 403,
        "employer": 404,
        "admin": 403,
    },
    # Candidate-only apply (REQ-FR-022, batch 1.36). The nil UUID is a 404 after
    # the role check; a candidate in this fixture has no profile, but the job
    # lookup runs first, so the answer is still 404 rather than 409.
    "/api/v1/jobs/00000000-0000-0000-0000-000000000000/apply/": {
        "method": "post",
        "anonymous": 401,
        "candidate": 404,
        "employer": 403,
        "admin": 403,
    },
    # DRF router roots for apps whose viewsets have not landed yet. They inherit
    # the global IsAuthenticated default; they must not become public just
    # because they list nothing.
    "/api/v1/accounts/": {
        "method": "get",
        "anonymous": 401,
        "candidate": 200,
        "employer": 200,
        "admin": 200,
    },
    "/api/v1/candidates/": {
        "method": "get",
        "anonymous": 401,
        "candidate": 200,
        "employer": 200,
        "admin": 200,
    },
    "/api/v1/employers/": {
        "method": "get",
        "anonymous": 401,
        "candidate": 200,
        "employer": 200,
        "admin": 200,
    },
    "/api/v1/assessments/": {
        "method": "get",
        "anonymous": 401,
        "candidate": 200,
        "employer": 200,
        "admin": 200,
    },
    "/api/v1/interviews/": {
        "method": "get",
        "anonymous": 401,
        "candidate": 200,
        "employer": 200,
        "admin": 200,
    },
    "/api/v1/notifications/": {
        "method": "get",
        "anonymous": 401,
        "candidate": 200,
        "employer": 200,
        "admin": 200,
    },
}

# Routes the walker must not ask the matrix about. Each entry is a decision, not
# a convenience: anything not listed here that appears in the resolver is an
# unclassified route and fails `test_every_registered_route_has_a_matrix_row`.
EXCLUDED_PREFIXES = ("static/", "media/", "api/schema/", "api/docs/")

# A concrete sample for each parameterised route, keyed by the template the
# resolver reports. The matrix uses the value as its key; a template with no
# entry still fails, so this is not a blanket skip. The id is the nil UUID on
# purpose: it exists nowhere, so an owning view's 404 is reproducible.
SAMPLE_UUID = "00000000-0000-0000-0000-000000000000"
PARAMETERISED_SAMPLES = {
    "/api/v1/candidates/resumes/<uuid:pk>/complete/": (
        f"/api/v1/candidates/resumes/{SAMPLE_UUID}/complete/"
    ),
    "/api/v1/candidates/resumes/<uuid:pk>/": (
        f"/api/v1/candidates/resumes/{SAMPLE_UUID}/"
    ),
    "/api/v1/candidates/applications/<uuid:pk>/": (
        f"/api/v1/candidates/applications/{SAMPLE_UUID}/"
    ),
    "/candidate/applications/<uuid:application_id>/": (
        f"/candidate/applications/{SAMPLE_UUID}/"
    ),
    "/employer/applications/<uuid:application_id>/": (
        f"/employer/applications/{SAMPLE_UUID}/"
    ),
    "/employer/jobs/<uuid:job_id>/": (f"/employer/jobs/{SAMPLE_UUID}/"),
    "/employer/jobs/<uuid:job_id>/edit/": (f"/employer/jobs/{SAMPLE_UUID}/edit/"),
    "/employer/jobs/<uuid:job_id>/autosave/": (
        f"/employer/jobs/{SAMPLE_UUID}/autosave/"
    ),
    "/employer/jobs/<uuid:job_id>/activate/": (
        f"/employer/jobs/{SAMPLE_UUID}/activate/"
    ),
    "/employer/jobs/<uuid:job_id>/pause/": (f"/employer/jobs/{SAMPLE_UUID}/pause/"),
    "/employer/jobs/<uuid:job_id>/close/": (f"/employer/jobs/{SAMPLE_UUID}/close/"),
    "/employer/jobs/<uuid:job_id>/delete/": (f"/employer/jobs/{SAMPLE_UUID}/delete/"),
    "/api/v1/jobs/<uuid:job_id>/": "/api/v1/jobs/00000000-0000-0000-0000-000000000000/",
    "/api/v1/jobs/public/<uuid:job_id>/": (
        "/api/v1/jobs/public/00000000-0000-0000-0000-000000000000/"
    ),
    "/jobs/<uuid:job_id>/": "/jobs/00000000-0000-0000-0000-000000000000/",
    "/jobs/<uuid:job_id>/apply/": ("/jobs/00000000-0000-0000-0000-000000000000/apply/"),
    "/api/v1/jobs/<uuid:job_id>/apply/": (
        "/api/v1/jobs/00000000-0000-0000-0000-000000000000/apply/"
    ),
    "/api/v1/jobs/<uuid:job_id>/activate/": "/api/v1/jobs/00000000-0000-0000-0000-000000000000/activate/",
    "/api/v1/jobs/<uuid:job_id>/pause/": "/api/v1/jobs/00000000-0000-0000-0000-000000000000/pause/",
    "/api/v1/jobs/<uuid:job_id>/close/": "/api/v1/jobs/00000000-0000-0000-0000-000000000000/close/",
}


def method_specs(spec: dict) -> dict[str, dict]:
    """The per-method expectations of one matrix row.

    A row is either a single verb (`{"method": "post", "anonymous": ...}`) or an
    explicit map (`{"methods": {"get": {...}, "post": {...}}}`) for a path that
    answers more than one. The single-verb form is kept because most rows have
    one verb and the compact form reads better; the map exists so a second verb
    on an existing path is a decision rather than an untested route.
    """
    if "methods" in spec:
        return spec["methods"]
    return {spec["method"]: spec}


def matrix_cases() -> list[tuple[str, str]]:
    """Every (path, method) pair the matrix states an answer for."""
    return [
        (path, method)
        for path in sorted(AUTHZ_MATRIX)
        for method in method_specs(AUTHZ_MATRIX[path])
    ]


def registered_routes(urlpatterns=None) -> tuple[set[str], set[str]]:
    """Return (paths, parameterised) for every project route.

    Paths carry their leading slash so they compare directly with the matrix.
    `django-admin/` is returned as one path and not descended into.

    `patterns` exists so the fail-closed property can be tested with a synthetic
    URLconf: calling it with no argument walks the real project.
    """
    paths: set[str] = set()
    parameterised: set[str] = set()

    def walk(patterns, prefix: str = "") -> None:
        for pattern in patterns:
            route = prefix + str(pattern.pattern)
            path = "/" + route if route else "/"

            if isinstance(pattern, URLResolver):
                if route == "django-admin/":
                    # One row covers the whole admin, staff check included.
                    paths.add(path)
                    continue
                walk(pattern.url_patterns, route)
                continue

            assert isinstance(pattern, URLPattern)
            if route.startswith(EXCLUDED_PREFIXES):
                continue
            # DRF registers the same view twice, once with a format suffix.
            if "<drf_format_suffix:" in route:
                continue
            if "<" in route:
                parameterised.add(path)
                continue
            paths.add(path)

    walk(urlpatterns if urlpatterns is not None else get_resolver().url_patterns)
    return paths, parameterised


def unclassified(routes: set[str]) -> set[str]:
    """Routes with no rule. Extracted so the fail-closed test can prove it."""
    return routes - set(AUTHZ_MATRIX) - set(PARAMETERISED_SAMPLES)


@pytest.fixture(autouse=True)
def _clean_cache():
    """Throttle counters live in Redis and survive the test transaction."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def actors():
    """One user per role, plus an admin who is staff but holds no role group.

    Groups come from `core/fixtures/groups.json` rather than being created here:
    the fixture is the source of truth for the D-2 role names, and a test that
    invented `employer_hr` would keep passing after the fixture lost it.
    """
    call_command("loaddata", "groups", verbosity=0)

    def user(email: str, *roles: str, **extra) -> User:
        created = User.objects.create_user(email, **extra)
        for role in roles:
            created.groups.add(Group.objects.get(name=role))
        return created

    return {
        "candidate": user("candidate@example.com", "candidate"),
        "employer": user("employer@example.com", "employer_hr"),
        # Deliberately no role group: `/django-admin/` must be gated by
        # `is_staff`, and the API must still treat this account as authenticated.
        "admin": User.objects.create_superuser("admin@example.com"),
    }


def test_every_registered_route_has_a_matrix_row():
    routes, _ = registered_routes()

    missing = sorted(unclassified(routes))
    assert not missing, (
        "route(s) with no authorization rule: "
        + ", ".join(missing)
        + " -- add a row to AUTHZ_MATRIX and docs/AUTHZ_MATRIX.md"
    )

    stale = sorted(set(AUTHZ_MATRIX) - routes - set(PARAMETERISED_SAMPLES.values()))
    assert not stale, "matrix rows for routes that no longer exist: " + ", ".join(stale)


def test_a_route_added_without_a_rule_is_detected():
    """The property the batch asks for, proved without editing the URLconf.

    A new route under an existing prefix would otherwise be the easiest thing to
    add without a rule: the matrix would keep passing because nothing walks the
    resolver.
    """

    def unreviewed(request):
        return HttpResponse("ok")

    synthetic = [
        path("", include([path("unreviewed/", unreviewed, name="unreviewed")])),
    ]

    routes, parameterised = registered_routes(synthetic)

    assert routes == {"/unreviewed/"}
    assert not parameterised
    assert unclassified(routes) == {"/unreviewed/"}


def test_no_parameterised_route_is_silently_uncovered():
    _, parameterised = registered_routes()

    unmapped = sorted(parameterised - set(PARAMETERISED_SAMPLES))
    assert not unmapped, (
        "route(s) contain a URL parameter and need a concrete sample in "
        "PARAMETERISED_SAMPLES and a row in AUTHZ_MATRIX: " + ", ".join(unmapped)
    )


def test_the_global_default_is_fail_closed():
    """The watch-out for this batch: an override is a decision, not a default."""
    assert settings.REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"] == [
        "rest_framework.permissions.IsAuthenticated"
    ]


@pytest.mark.parametrize("path,method", matrix_cases())
def test_route_matches_the_authorization_matrix(actors, path, method):
    spec = method_specs(AUTHZ_MATRIX[path])[method]

    for actor in ACTORS:
        client = Client()
        if actor != "anonymous":
            client.force_login(actors[actor])

        response = getattr(client, method)(path)

        assert response.status_code == spec[actor], (
            f"{method.upper()} {path} as {actor}: expected {spec[actor]}, "
            f"got {response.status_code}"
        )
