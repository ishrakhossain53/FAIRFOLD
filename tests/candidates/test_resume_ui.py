"""Resume manager page (design.md page #17, wireframe S03, REQ-FR-010).

What the server-rendered page adds on top of the API tests
(`test_resume_list_detail_api.py`), and what these tests pin down:

* candidate-only: anonymous is redirected to login with a `next`, every other
  authenticated role is 403, and a candidate without a profile is sent to
  onboarding (REQ-FR-009 precedes REQ-FR-010);
* the list is the caller's rows and nothing else, and the storage key never
  reaches the HTML -- a key in a page is a key in a screenshot;
* the uploader is wired to the three API routes by `reverse()`, not by a
  hand-written path, and carries the size limit the server enforces;
* Delete is a confirmation page whose POST is the only mutation, it is
  owner-only, and it removes the row, the stored object and writes the audit
  entry;
* the accessibility hooks S03 asks for exist in the markup: a real `<button>`
  for the file picker, `role="progressbar"` with `aria-valuenow`, a polite live
  region, and the percentage as text;
* with JavaScript off there is an explicit <noscript> message, not a silent
  dead dropzone.

The upload itself (`PUT` to storage, progress, polling) is browser code and is
verified manually; `static/js/resume-upload.js` is asserted to exist and be
referenced so a rename cannot quietly break the page.
"""

from __future__ import annotations

import re
import uuid

import pytest
from django.conf import settings
from django.test import Client
from django.urls import reverse

from candidates.models import CandidateProfile, CandidateResume
from candidates.services import RESUME_DELETED_ACTION
from core.models import AuditLogEntry

pytestmark = pytest.mark.django_db

RESUMES_URL = "/candidate/resumes/"
DELETE_URL = "/candidate/resumes/delete/"

PASSWORD = "Wanderlust7Quartz-Meadow"


@pytest.fixture
def candidate(make_user):
    return make_user(
        "candidate",
        email="ada@example.com",
        password=PASSWORD,
        email_verified=True,
    )


@pytest.fixture
def profile(candidate):
    return CandidateProfile.objects.create(
        user=candidate,
        title="Backend developer",
        bio="Django and PostgreSQL.",
        location="Dhaka",
        remote_ok=False,
    )


@pytest.fixture
def signed_in(candidate):
    client = Client()
    client.force_login(candidate)
    return client


def make_resume(profile, **overrides) -> CandidateResume:
    fields = {
        "candidate": profile,
        "file_key": f"resumes/{profile.id}/{uuid.uuid4().hex}.pdf",
        "original_filename": "cv_2026.pdf",
        "file_size": 2048,
        "mime_type": "application/pdf",
    }
    fields.update(overrides)
    return CandidateResume.objects.create(**fields)


def delete_url(resume) -> str:
    return f"{DELETE_URL}?resume={resume.id}"


class TestAccess:
    def test_anonymous_is_sent_to_login_with_a_next(self):
        response = Client().get(RESUMES_URL)

        assert response.status_code == 302
        assert response["Location"].startswith("/login/")
        assert "next=" in response["Location"]

    @pytest.mark.parametrize("role", ["employer_hr", "employer_manager", "interviewer"])
    def test_a_non_candidate_role_is_forbidden(self, make_user, role):
        user = make_user(role)
        client = Client()
        client.force_login(user)

        assert client.get(RESUMES_URL).status_code == 403

    def test_a_platform_admin_without_the_candidate_group_is_forbidden(self, make_user):
        user = make_user(is_staff=True)
        client = Client()
        client.force_login(user)

        assert client.get(RESUMES_URL).status_code == 403

    def test_a_candidate_without_a_profile_is_sent_to_onboarding(self, signed_in):
        response = signed_in.get(RESUMES_URL)

        assert response.status_code == 302
        assert response["Location"] == "/candidate/onboarding/"


class TestPage:
    def test_renders_the_heading_and_the_two_sections(self, signed_in, profile):
        response = signed_in.get(RESUMES_URL)

        assert response.status_code == 200
        html = response.content.decode()
        assert "<h1" in html and "Resumes" in html
        assert "Upload a resume" in html
        assert "Your resumes" in html

    def test_the_uploader_points_at_the_api_routes(self, signed_in, profile):
        html = signed_in.get(RESUMES_URL).content.decode()

        assert f'data-upload-url="{reverse("api:candidates:resume-list")}"' in html
        # The object routes carry a `{id}` placeholder the script substitutes;
        # `reverse()` with the nil UUID is templated in the view, so the path is
        # still owned by the URLconf.
        assert 'data-complete-url="/api/v1/candidates/resumes/{id}/complete/"' in html
        assert 'data-detail-url="/api/v1/candidates/resumes/{id}/"' in html

    def test_the_uploader_carries_the_server_size_limit(
        self, signed_in, profile, settings
    ):
        settings.MAX_UPLOAD_SIZE_BYTES = 2 * 1024 * 1024

        html = signed_in.get(RESUMES_URL).content.decode()

        assert 'data-max-bytes="2097152"' in html
        assert "maximum 2 MB" in html

    def test_only_the_callers_resumes_are_listed(self, signed_in, profile, make_user):
        mine = make_resume(profile, original_filename="mine.pdf")

        other_profile = CandidateProfile.objects.create(user=make_user("candidate"))
        make_resume(other_profile, original_filename="theirs.pdf")

        html = signed_in.get(RESUMES_URL).content.decode()

        assert "mine.pdf" in html
        assert "theirs.pdf" not in html
        assert str(mine.id) in html

    def test_the_storage_key_is_never_rendered(self, signed_in, profile):
        resume = make_resume(profile)

        html = signed_in.get(RESUMES_URL).content.decode()

        assert resume.file_key not in html
        assert "file_key" not in html

    def test_a_rejected_resume_shows_its_reason(self, signed_in, profile):
        make_resume(
            profile,
            status=CandidateResume.Status.REJECTED,
            status_reason="clamav unavailable",
        )

        html = signed_in.get(RESUMES_URL).content.decode()

        assert "Rejected" in html
        assert "clamav unavailable" in html

    def test_a_pending_resume_cannot_be_replaced(self, signed_in, profile):
        resume = make_resume(profile, status=CandidateResume.Status.PENDING)

        html = signed_in.get(RESUMES_URL).content.decode()

        assert f"?replace={resume.id}" not in html
        assert f"{DELETE_URL}?resume={resume.id}" in html

    def test_a_clean_resume_can_be_replaced_and_deleted(self, signed_in, profile):
        resume = make_resume(profile, status=CandidateResume.Status.CLEAN)

        html = signed_in.get(RESUMES_URL).content.decode()

        assert f"?replace={resume.id}" in html
        assert f"{DELETE_URL}?resume={resume.id}" in html

    def test_the_filename_is_escaped(self, signed_in, profile):
        make_resume(profile, original_filename='<script>alert("x")</script>.pdf')

        html = signed_in.get(RESUMES_URL).content.decode()

        assert "<script>alert" not in html
        assert "&lt;script&gt;" in html

    def test_the_replace_intent_is_carried_to_the_uploader(self, signed_in, profile):
        resume = make_resume(profile, status=CandidateResume.Status.CLEAN)

        html = signed_in.get(f"{RESUMES_URL}?replace={resume.id}").content.decode()

        assert "Replace a resume" in html
        assert f'data-replace-id="{resume.id}"' in html

    def test_a_replace_id_the_candidate_does_not_own_is_ignored(
        self, signed_in, profile, make_user
    ):
        other_profile = CandidateProfile.objects.create(user=make_user("candidate"))
        theirs = make_resume(other_profile)

        html = signed_in.get(f"{RESUMES_URL}?replace={theirs.id}").content.decode()

        assert "Replace a resume" not in html
        assert 'data-replace-id=""' in html

    def test_a_malformed_replace_id_is_ignored(self, signed_in, profile):
        html = signed_in.get(f"{RESUMES_URL}?replace=not-a-uuid").content.decode()

        assert "Replace a resume" not in html

    def test_the_page_says_what_happens_without_javascript(self, signed_in, profile):
        html = signed_in.get(RESUMES_URL).content.decode()

        assert "<noscript>" in html
        assert "Uploading needs JavaScript" in html

    def test_the_a11y_hooks_s03_asks_for_exist(self, signed_in, profile):
        html = signed_in.get(RESUMES_URL).content.decode()

        # The picker is a real button, not a div with a click handler.
        assert re.search(r"<button[^>]*data-choose-file", html)
        # The bar is a progressbar with a live value, and the percentage is text.
        assert 'role="progressbar"' in html
        assert 'aria-valuenow="0"' in html
        assert "data-progress-percent" in html
        # Processing steps announce themselves politely.
        assert 'aria-live="polite"' in html

    def test_the_upload_script_is_referenced_and_exists(self, signed_in, profile):
        html = signed_in.get(RESUMES_URL).content.decode()

        assert 'src="/static/js/resume-upload.js"' in html
        assert (settings.BASE_DIR / "static/js/resume-upload.js").is_file()


class TestDeleteConfirmation:
    def test_get_shows_the_filename_and_does_not_delete(
        self, signed_in, profile, resume_storage
    ):
        resume = make_resume(profile)

        response = signed_in.get(delete_url(resume))

        assert response.status_code == 200
        html = response.content.decode()
        assert "cv_2026.pdf" in html
        assert "Delete this resume?" in html
        assert CandidateResume.objects.filter(pk=resume.pk).exists()

    def test_cancel_is_the_first_control(self, signed_in, profile):
        resume = make_resume(profile)

        # Compare the controls inside the delete form, not the copy: "Delete
        # resume" also appears in the page title, and the header's logout button
        # is an earlier `type="submit"` on the page.
        html = signed_in.get(delete_url(resume)).content.decode()
        form_start = html.find('action="/candidate/resumes/delete/"')
        form = html[form_start:]

        cancel = form.find("data-cancel-focus")
        delete = form.find('type="submit"')
        assert cancel != -1
        assert delete != -1
        assert cancel < delete

    def test_another_candidates_resume_is_404(self, signed_in, profile, make_user):
        other_profile = CandidateProfile.objects.create(user=make_user("candidate"))
        theirs = make_resume(other_profile)

        response = signed_in.get(delete_url(theirs))

        assert response.status_code == 404

    def test_a_malformed_id_is_404(self, signed_in, profile):
        response = signed_in.get(f"{DELETE_URL}?resume=nope")

        assert response.status_code == 404

    def test_no_resume_id_is_404(self, signed_in, profile):
        response = signed_in.get(DELETE_URL)

        assert response.status_code == 404

    def test_anonymous_is_sent_to_login(self, profile):
        resume = make_resume(profile)

        response = Client().get(delete_url(resume))

        assert response.status_code == 302
        assert response["Location"].startswith("/login/")

    def test_an_employer_is_forbidden(self, make_user, profile):
        user = make_user("employer_hr")
        client = Client()
        client.force_login(user)
        resume = make_resume(profile)

        assert client.get(delete_url(resume)).status_code == 403


class TestDeleteAction:
    def test_post_deletes_row_object_and_writes_the_audit_entry(
        self, signed_in, candidate, profile, put_object
    ):
        resume = make_resume(profile, status=CandidateResume.Status.CLEAN)
        stored = put_object(resume.file_key, b"%PDF-1.4\n%%EOF\n")

        response = signed_in.post(DELETE_URL, {"resume": str(resume.id)})

        assert response.status_code == 302
        assert response["Location"] == RESUMES_URL
        assert not CandidateResume.objects.filter(pk=resume.pk).exists()
        assert not stored.exists()

        entry = AuditLogEntry.objects.get(action=RESUME_DELETED_ACTION)
        assert entry.actor == candidate
        assert entry.resource_id == resume.pk
        assert entry.details == {"status": "clean"}

    def test_the_confirmation_message_is_shown_after_the_redirect(
        self, signed_in, profile, resume_storage
    ):
        resume = make_resume(profile)

        response = signed_in.post(DELETE_URL, {"resume": str(resume.id)}, follow=True)

        assert b"Resume deleted." in response.content

    def test_another_candidates_resume_is_404_and_survives(
        self, signed_in, profile, make_user
    ):
        other_profile = CandidateProfile.objects.create(user=make_user("candidate"))
        theirs = make_resume(other_profile)

        response = signed_in.post(DELETE_URL, {"resume": str(theirs.id)})

        assert response.status_code == 404
        assert CandidateResume.objects.filter(pk=theirs.pk).exists()

    def test_a_post_without_a_csrf_token_is_rejected(self, candidate, profile):
        resume = make_resume(profile)
        client = Client(enforce_csrf_checks=True)
        client.force_login(candidate)

        response = client.post(DELETE_URL, {"resume": str(resume.id)})

        assert response.status_code == 403
        assert CandidateResume.objects.filter(pk=resume.pk).exists()
