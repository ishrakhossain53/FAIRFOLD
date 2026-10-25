"""Page #36's live Markdown preview and page #37's rendering (design.md 7.22).

What these assert beyond "the fragment contains HTML":

* the preview is employer-only, POST-only and subject to the same onboarding
  redirect as the form, so it cannot be used as a public renderer;
* it writes nothing: no row changes and no audit entry, including on the create
  page where no job exists yet;
* the response keeps the section's id and HTMX attributes, because the page
  replaces it with `outerHTML` -- a fragment without them would preview once and
  then stop listening;
* the preview and page #37 render the same source through the same include, so
  page #37 cannot show a different result from the one the employer approved;
* untrusted text is escaped in both surfaces (REQ-SEC-006).
"""

from __future__ import annotations

import pytest
from django.test import Client

from core.models import AuditLogEntry
from employers.models import EmployerProfile
from matching.models import Job

pytestmark = pytest.mark.django_db

PREVIEW_URL = "/employer/jobs/preview/"
NEW_URL = "/employer/jobs/new/"

MARKDOWN_BODY = {
    "description": "## The role\n\nWe **own** the *screening* API. `Python`.",
    "responsibilities": "- Build the ranker\n- Review evidence",
    "requirements": "1. Five years\n2. PostgreSQL",
    "nice_to_have": "> Experience with pgvector",
}


def edit_url(job_id) -> str:
    return f"/employer/jobs/{job_id}/edit/"


def overview_url(job_id) -> str:
    return f"/employer/jobs/{job_id}/"


@pytest.fixture
def employer(make_user):
    return make_user("employer_hr", email="hr@example.com")


@pytest.fixture
def profile(employer):
    return EmployerProfile.objects.create(user=employer, company_name="Acme Ltd")


@pytest.fixture
def job(profile):
    return Job.objects.create(
        employer=profile,
        title="Backend Engineer",
        description="Build and run the screening API.",
        location="Dhaka",
    )


def client_for(user) -> Client:
    client = Client()
    client.force_login(user)
    return client


class TestAccess:
    def test_anonymous_is_redirected_to_login(self):
        response = Client().post(PREVIEW_URL, MARKDOWN_BODY)

        assert response.status_code == 302
        assert response["Location"].startswith("/login/")

    def test_a_candidate_is_403(self, make_user):
        response = client_for(make_user("candidate")).post(PREVIEW_URL, MARKDOWN_BODY)

        assert response.status_code == 403

    def test_an_employer_without_a_profile_is_sent_to_onboarding(self, make_user):
        response = client_for(make_user("employer_hr")).post(PREVIEW_URL, MARKDOWN_BODY)

        assert response.status_code == 302
        assert response["Location"] == "/employer/onboarding/"

    def test_a_platform_admin_is_403(self):
        from accounts.models import User

        admin = User.objects.create_superuser("admin@example.com")

        response = client_for(admin).post(PREVIEW_URL, MARKDOWN_BODY)

        assert response.status_code == 403

    def test_get_is_405(self, employer, profile):
        response = client_for(employer).get(PREVIEW_URL)

        assert response.status_code == 405


class TestPreview:
    def test_it_renders_the_documented_subset(self, employer, profile):
        response = client_for(employer).post(PREVIEW_URL, MARKDOWN_BODY)
        content = response.content.decode()

        assert response.status_code == 200
        assert response["Content-Type"].startswith("text/html")
        assert "<h4>The role</h4>" in content  # # -> h3, ## -> h4
        assert "<strong>own</strong>" in content
        assert "<em>screening</em>" in content
        assert "<code>Python</code>" in content
        assert "<ul><li>Build the ranker</li><li>Review evidence</li></ul>" in content
        assert "<ol><li>Five years</li><li>PostgreSQL</li></ol>" in content
        assert "<blockquote><p>Experience with pgvector</p></blockquote>" in content
        # The point of the preview is that the Markdown source is gone: if this
        # assertion ever fails, the panel is showing raw source instead of HTML.
        assert "**own**" not in content

    def test_the_response_keeps_the_htmx_contract(self, employer, profile):
        content = client_for(employer).post(PREVIEW_URL, MARKDOWN_BODY).content.decode()

        assert 'id="job-preview"' in content
        assert f'hx-post="{PREVIEW_URL}"' in content
        assert 'hx-include="#job-form"' in content
        assert 'hx-swap="outerHTML"' in content
        assert (
            'hx-trigger="input delay:500ms from:#job-form, ' 'change from:#job-form"'
        ) in content

    def test_untrusted_html_is_escaped(self, employer, profile):
        content = (
            client_for(employer)
            .post(
                PREVIEW_URL,
                {
                    "description": '<script>alert("x")</script> **ok**',
                    "requirements": '<img src=x onerror="alert(1)">',
                },
            )
            .content.decode()
        )

        assert "<script>" not in content
        assert "<img" not in content
        assert "&lt;script&gt;" in content
        assert "&lt;img" in content
        assert "<strong>ok</strong>" in content

    def test_a_dangerous_link_stays_literal(self, employer, profile):
        content = (
            client_for(employer)
            .post(PREVIEW_URL, {"description": "[click](javascript:alert)"})
            .content.decode()
        )

        assert "<a " not in content
        assert "[click](javascript:alert)" in content

    def test_empty_fields_show_the_empty_state(self, employer, profile):
        content = (
            client_for(employer)
            .post(PREVIEW_URL, {"description": "  ", "requirements": ""})
            .content.decode()
        )

        assert "Nothing to preview yet." in content

    def test_it_writes_nothing(self, employer, profile, job):
        before = AuditLogEntry.objects.count()

        client_for(employer).post(PREVIEW_URL, MARKDOWN_BODY)

        assert AuditLogEntry.objects.count() == before
        job.refresh_from_db()
        assert job.description == "Build and run the screening API."


class TestPage36Editor:
    def test_the_four_fields_have_a_toolbar_and_a_preview(self, employer, profile, job):
        content = client_for(employer).get(edit_url(job.pk)).content.decode()

        assert content.count('data-markdown-action="bold"') == 4
        assert content.count('role="group"') == 4
        assert 'aria-label="Bold, Description"' in content
        assert 'id="job-preview"' in content
        assert "Markdown works" in content

    def test_the_create_page_also_gets_the_editor(self, employer, profile):
        content = client_for(employer).get(NEW_URL).content.decode()

        assert content.count('data-markdown-action="bold"') == 4
        assert 'id="job-preview"' in content
        assert "Nothing to preview yet." in content

    def test_the_edit_page_previews_the_saved_source(self, employer, profile, job):
        Job.objects.filter(pk=job.pk).update(
            description="**Build** the API.",
            responsibilities="- Rank\n- Review",
        )

        content = client_for(employer).get(edit_url(job.pk)).content.decode()

        assert "<strong>Build</strong>" in content
        assert "<ul><li>Rank</li><li>Review</li></ul>" in content


class TestPage37Rendering:
    def test_all_four_fields_render_markdown(self, employer, profile, job):
        Job.objects.filter(pk=job.pk).update(**MARKDOWN_BODY)

        content = client_for(employer).get(overview_url(job.pk)).content.decode()

        assert "<h4>The role</h4>" in content
        assert "<strong>own</strong>" in content
        assert "<ul><li>Build the ranker</li><li>Review evidence</li></ul>" in content
        assert "<ol><li>Five years</li><li>PostgreSQL</li></ol>" in content
        assert "<blockquote><p>Experience with pgvector</p></blockquote>" in content

    def test_plain_text_still_renders(self, employer, profile, job):
        content = client_for(employer).get(overview_url(job.pk)).content.decode()

        assert "<p>Build and run the screening API.</p>" in content

    def test_an_empty_field_keeps_the_plain_empty_state(self, employer, profile, job):
        content = client_for(employer).get(overview_url(job.pk)).content.decode()

        assert "Not written yet." in content

    def test_untrusted_html_is_escaped_on_the_overview(self, employer, profile, job):
        payload = '<script>alert("x")</script>'
        Job.objects.filter(pk=job.pk).update(description=payload)

        content = client_for(employer).get(overview_url(job.pk)).content.decode()

        assert payload not in content
        assert "&lt;script&gt;" in content
