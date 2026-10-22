"""UI tests for registration and email verification (REQ-FR-001, pages #6/#11).

These sit on top of the service tests (`test_registration.py`,
`test_email_verification.py`) and the API tests (`test_auth_api.py`). They assert
what the server-rendered pages add:

* the form is a real HTML form -- it posts to `/register/` and works without the
  HTMX attributes, which are the enhancement and not the mechanism;
* every state of design.md page #11 is a page: pending, success, expired, invalid;
* a duplicate address and a new one land on the same page with the same copy, so
  the public form is not an enumeration oracle;
* the pending page masks the address and the full address is nowhere in its
  source, because the resend reads it from the session instead of a hidden field;
* the verification page never caches the token or leaks it in a referrer, and
  the token is never echoed into the body;
* the resend action answers identically for a known address, an unknown one, a
  verified account and a request inside the cooldown.

Celery is deliberately not eager in CI, so dispatches are captured by patching
`.delay`; `transaction.on_commit` needs
`django_capture_on_commit_callbacks(execute=True)` or the assertion is vacuous.
"""

from __future__ import annotations

import re

import pytest
from django.core.cache import cache
from django.test import Client

from accounts.models import User
from accounts.services import make_verification_token, resend_throttle_cache_key
from accounts.tasks import send_verification_email
from accounts.views import (
    PENDING_EMAIL_SESSION_KEY,
    PENDING_SENT_AT_SESSION_KEY,
    mask_email,
)

pytestmark = pytest.mark.django_db

REGISTER_URL = "/register/"
CHECK_EMAIL_URL = "/register/check-email/"
VERIFY_URL = "/verify-email/"
RESEND_URL = "/verify-email/resend/"

STRONG_PASSWORD = "Wanderlust7Quartz-Meadow"


@pytest.fixture(autouse=True)
def _clean_cache():
    """Clear resend cooldowns between tests.

    The cooldown lives in Redis and is not rolled back with the database; a
    registration in one test would otherwise throttle the next test's resend.
    """
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def dispatched(monkeypatch):
    """Record verification-email dispatches instead of using the broker."""
    calls: list[str] = []

    def _delay(user_id: str) -> None:
        calls.append(user_id)

    monkeypatch.setattr(send_verification_email, "delay", _delay)
    return calls


def payload(**overrides) -> dict:
    body = {
        "role": "candidate",
        "first_name": "Ada",
        "last_name": "Lovelace",
        "email": "ada@example.com",
        "password": STRONG_PASSWORD,
        "consent": "on",
    }
    body.update(overrides)
    return body


def register(client: Client, **overrides):
    return client.post(REGISTER_URL, payload(**overrides))


def set_pending(client: Client, email: str) -> None:
    """Put an address in the client's session the way `register` would.

    A local store, not `client.session[...] = ...` twice: the property returns a
    new `SessionStore` on every access once the cookie exists, so saving the
    second one would write an empty session over the first.
    """
    session = client.session
    session[PENDING_EMAIL_SESSION_KEY] = email
    session.save()


def element_ids(html: str) -> list[str]:
    return re.findall(r'\bid="([^"]+)"', html)


def assert_unique_ids(html: str) -> None:
    """A duplicate id breaks every `aria-describedby` and `<label for>` on the page.

    This is not pedantry: a multi-line `{# … #}` is *not* a Django comment (the
    comment regex does not cross newlines), so a note containing `id="…"` is
    rendered as HTML and silently duplicates an id. The register templates hit
    exactly that during this batch; this assertion is the guard.
    """
    found = element_ids(html)
    duplicates = sorted({value for value in found if found.count(value) > 1})
    assert duplicates == []


class TestMaskEmail:
    @pytest.mark.parametrize(
        ("email", "expected"),
        [
            ("ada@example.com", "a***@example.com"),
            ("a@x.io", "a***@x.io"),
        ],
    )
    def test_keeps_the_first_letter_and_the_domain(self, email, expected):
        assert mask_email(email) == expected

    def test_the_local_part_is_never_fully_visible(self):
        masked = mask_email("ada.lovelace@example.com")

        assert "ada" not in masked
        assert masked.endswith("@example.com")

    @pytest.mark.parametrize("broken", ["hostname-only", "", "@example.com"])
    def test_a_value_without_both_halves_reveals_nothing(self, broken):
        assert mask_email(broken) == "***"


class TestRegisterPage:
    def test_renders_an_html_form_for_anonymous_visitors(self):
        response = Client().get(REGISTER_URL)

        assert response.status_code == 200
        content = response.content.decode()
        assert 'method="post"' in content
        assert f'action="{REGISTER_URL}"' in content
        assert 'name="first_name"' in content
        assert 'name="last_name"' in content
        assert 'name="email"' in content
        assert 'name="password"' in content
        assert 'name="consent"' in content

    def test_the_two_self_assignable_roles_are_offered_by_group_name(self):
        content = Client().get(REGISTER_URL).content.decode()

        assert 'value="candidate"' in content
        assert 'value="employer_hr"' in content
        assert "Looking for work" in content
        assert "Hiring" in content

    def test_a_privileged_role_cannot_be_offered(self):
        content = Client().get(REGISTER_URL).content.decode()

        assert 'value="employer_manager"' not in content
        assert 'value="interviewer"' not in content

    def test_a_landing_cta_preselects_the_matching_role(self):
        # The landing page's "I'm hiring" / "I'm looking for work" links carry
        # `?role=…`; the visitor should not have to answer the same question twice.
        content = Client().get(REGISTER_URL + "?role=employer_hr").content.decode()

        assert re.search(r'value="employer_hr"[^>]*checked', content)

    def test_an_unknown_or_privileged_role_is_ignored(self):
        for value in ("employer_manager", "not-a-role"):
            content = Client().get(REGISTER_URL, {"role": value}).content.decode()

            assert re.search(r'value="candidate"[^>]*checked', content)
            assert not re.search(r'value="employer_hr"[^>]*checked', content)
            assert 'value="employer_manager"' not in content

    def test_the_password_is_masked_and_marked_for_password_managers(self):
        content = Client().get(REGISTER_URL).content.decode()

        assert 'type="password"' in content
        assert 'autocomplete="new-password"' in content

    def test_the_page_uses_the_shared_base_template(self):
        content = Client().get(REGISTER_URL).content.decode()

        assert 'id="main"' in content
        assert "Skip to main content" in content

    def test_the_form_carries_a_csrf_token(self):
        content = Client().get(REGISTER_URL).content.decode()

        assert "csrfmiddlewaretoken" in content

    def test_the_htmx_attributes_are_on_the_same_form(self):
        content = Client().get(REGISTER_URL).content.decode()

        assert f'hx-post="{REGISTER_URL}"' in content
        assert 'hx-target="#register-panel"' in content

    def test_no_error_summary_before_the_first_submit(self):
        content = Client().get(REGISTER_URL).content.decode()

        assert 'id="error-summary"' not in content


class TestMarkup:
    def test_the_register_page_has_no_duplicate_ids(self):
        assert_unique_ids(Client().get(REGISTER_URL).content.decode())

    def test_the_register_page_with_errors_has_no_duplicate_ids(self, role_groups):
        content = register(Client(), consent="", email="not-an-email").content.decode()

        assert_unique_ids(content)

    def test_the_pending_page_has_no_duplicate_ids(self, role_groups):
        client = Client()
        register(client)

        assert_unique_ids(client.get(CHECK_EMAIL_URL).content.decode())

    def test_the_verification_page_has_no_duplicate_ids(self, make_user):
        user = make_user()
        client = Client()
        set_pending(client, user.email)

        assert_unique_ids(
            client.get(VERIFY_URL, {"token": "not-a-token"}).content.decode()
        )


class TestRegister:
    def test_creates_an_unverified_account_and_redirects(
        self, role_groups, dispatched, django_capture_on_commit_callbacks
    ):
        client = Client()

        with django_capture_on_commit_callbacks(execute=True):
            response = register(client)

        assert response.status_code == 302
        assert response["Location"] == CHECK_EMAIL_URL
        user = User.objects.get(email="ada@example.com")
        assert user.email_verified is False
        assert user.is_candidate is True
        assert user.check_password(STRONG_PASSWORD) is True
        assert dispatched == [str(user.pk)]

    def test_remembers_the_address_in_the_session(self, role_groups):
        client = Client()

        register(client)

        assert client.session[PENDING_EMAIL_SESSION_KEY] == "ada@example.com"
        assert client.session[PENDING_SENT_AT_SESSION_KEY]

    def test_the_normalised_address_is_what_is_stored(self, role_groups):
        register(Client(), email="  Ada@Example.COM  ")

        assert User.objects.filter(email="ada@example.com").exists()

    def test_the_employer_choice_assigns_the_employer_group(self, role_groups):
        register(Client(), role="employer_hr")

        user = User.objects.get(email="ada@example.com")
        assert user.is_employer is True
        assert user.is_candidate is False

    def test_a_duplicate_address_takes_the_same_path_as_a_new_one(
        self, role_groups, dispatched, django_capture_on_commit_callbacks
    ):
        client = Client()

        with django_capture_on_commit_callbacks(execute=True):
            first = register(client)
            second = register(client)

        # The whole anti-enumeration contract: status and destination are equal,
        # and the second request sends nothing.
        assert second.status_code == first.status_code == 302
        assert second["Location"] == first["Location"] == CHECK_EMAIL_URL
        assert User.objects.filter(email="ada@example.com").count() == 1
        assert len(dispatched) == 1

    def test_a_duplicate_lands_on_the_same_pending_page(self, role_groups):
        client = Client()
        register(client)

        response = client.post(REGISTER_URL, payload(), follow=True)

        assert response.status_code == 200
        assert "Check your email" in response.content.decode()
        assert "a***@example.com" in response.content.decode()

    @pytest.mark.parametrize(
        ("overrides", "message"),
        [
            ({"consent": ""}, "You must accept the Privacy Policy and Terms"),
            ({"password": "short"}, "at least 12 characters"),
            ({"first_name": ""}, "This field is required"),
            ({"email": "not-an-email"}, "Enter a valid email address"),
            ({"role": "employer_manager"}, "Choose whether you are looking for work"),
        ],
    )
    def test_invalid_submissions_re_render_with_the_error(
        self, role_groups, overrides, message
    ):
        response = register(Client(), **overrides)

        assert response.status_code == 200
        content = response.content.decode()
        assert 'id="error-summary"' in content
        assert message in content
        assert User.objects.count() == 0

    def test_the_summary_is_an_alert_that_can_take_focus(self, role_groups):
        content = register(Client(), consent="").content.decode()

        assert 'role="alert"' in content
        assert 'tabindex="-1"' in content
        assert 'id="error-summary"' in content

    def test_the_summary_links_to_every_failed_field(self, role_groups):
        content = register(Client(), consent="", email="not-an-email").content.decode()

        assert 'href="#id_email"' in content
        assert 'href="#id_consent"' in content

    def test_the_role_group_is_reachable_from_the_summary(self, role_groups):
        content = register(Client(), role="employer_manager").content.decode()

        # RadioSelect ids are `id_role_0…`; the fieldset carries the link target.
        assert 'id="id_role"' in content
        assert 'href="#id_role"' in content

    def test_a_duplicate_with_a_weak_password_reports_the_password(self, role_groups):
        client = Client()
        register(client)

        response = register(client, password="short")

        assert response.status_code == 200
        assert "at least 12 characters" in response.content.decode()

    def test_csrf_is_enforced(self, role_groups):
        # The real protection for an anonymous form: without a token the POST must
        # not create an account.
        client = Client(enforce_csrf_checks=True)

        response = client.post(REGISTER_URL, payload())

        assert response.status_code == 403
        assert User.objects.count() == 0

    def test_the_password_is_never_echoed_back(self, role_groups):
        content = register(Client(), password="short").content.decode()

        assert 'value="short"' not in content
        assert STRONG_PASSWORD not in content


class TestHtmxEnhancement:
    def test_an_invalid_post_swaps_the_panel_not_the_page(self, role_groups):
        response = Client().post(
            REGISTER_URL, payload(consent=""), HTTP_HX_REQUEST="true"
        )

        assert response.status_code == 200
        content = response.content.decode()
        assert 'id="register-panel"' in content
        assert 'id="error-summary"' in content
        assert "<html" not in content
        assert "<h1" not in content

    def test_a_valid_post_asks_for_a_full_navigation(
        self, role_groups, django_capture_on_commit_callbacks
    ):
        with django_capture_on_commit_callbacks(execute=True):
            response = Client().post(REGISTER_URL, payload(), HTTP_HX_REQUEST="true")

        # A 302 would be swapped into the form panel by HTMX; a full navigation
        # is what the pending page needs.
        assert response.status_code == 204
        assert response["HX-Redirect"] == CHECK_EMAIL_URL


class TestPendingPage:
    def test_shows_the_masked_address_and_the_resend_action(self, role_groups):
        client = Client()
        register(client)

        response = client.get(CHECK_EMAIL_URL)

        assert response.status_code == 200
        content = response.content.decode()
        assert "Check your email" in content
        assert "a***@example.com" in content
        assert "Resend email" in content
        assert 'action="/verify-email/resend/"' in content

    def test_the_full_address_is_not_in_the_page_source(self, role_groups):
        client = Client()
        register(client)

        content = client.get(CHECK_EMAIL_URL).content.decode()

        assert "ada@example.com" not in content

    def test_the_cooldown_is_shown_as_text(self, role_groups):
        client = Client()
        register(client)

        content = client.get(CHECK_EMAIL_URL).content.decode()

        assert "Available in 0:" in content
        assert 'data-cooldown="' in content

    def test_without_a_pending_address_it_returns_to_signup(self):
        response = Client().get(CHECK_EMAIL_URL)

        assert response.status_code == 302
        assert response["Location"] == REGISTER_URL


class TestDevelopmentVerificationLink:
    """DEBUG-only shortcut on the pending page (design.md X02, page #11).

    Local email goes to a console (often a Celery worker's), which is easy to
    miss. The page offers the link itself, but only while DEBUG is on. These
    tests pin both directions: the shortcut works, and production never renders
    a token into the pending page.
    """

    def test_debug_renders_a_link_that_verifies_the_account(
        self, role_groups, settings, dispatched
    ):
        settings.DEBUG = True
        client = Client()
        register(client)

        content = client.get(CHECK_EMAIL_URL).content.decode()

        assert "Development only" in content
        match = re.search(r'href="(http[^"]*token=[^"]+)"', content)
        assert match, "the pending page must offer the verification link"
        response = Client().get(match.group(1))
        assert response.status_code == 200
        assert User.objects.get(email="ada@example.com").email_verified is True

    def test_without_debug_the_page_contains_no_verification_token(
        self, role_groups, settings, dispatched
    ):
        settings.DEBUG = False
        client = Client()
        register(client)

        content = client.get(CHECK_EMAIL_URL).content.decode()

        assert "Development only" not in content
        assert "token=" not in content


class TestVerifyPage:
    def test_a_valid_token_verifies_the_account_and_lands_on_success(self, make_user):
        user = make_user()

        response = Client().get(VERIFY_URL, {"token": make_verification_token(user)})

        assert response.status_code == 200
        content = response.content.decode()
        assert "Email verified" in content
        assert "Continue to FairFold" in content
        user.refresh_from_db()
        assert user.email_verified is True

    def test_opening_the_link_twice_is_still_a_success(self, make_user):
        user = make_user()
        token = make_verification_token(user)
        client = Client()
        client.get(VERIFY_URL, {"token": token})

        response = client.get(VERIFY_URL, {"token": token})

        assert response.status_code == 200
        assert "Email verified" in response.content.decode()

    def test_a_tampered_token_is_an_invalid_state(self, make_user):
        user = make_user()

        response = Client().get(
            VERIFY_URL, {"token": make_verification_token(user) + "x"}
        )

        assert response.status_code == 400
        content = response.content.decode()
        assert "This link is not valid" in content
        user.refresh_from_db()
        assert user.email_verified is False

    def test_an_expired_token_is_an_expired_state(
        self, make_user, monkeypatch, settings
    ):
        monkeypatch.setattr(settings, "EMAIL_VERIFICATION_TOKEN_MAX_AGE_SECONDS", -1)
        user = make_user()

        response = Client().get(VERIFY_URL, {"token": make_verification_token(user)})

        assert response.status_code == 400
        assert "This link has expired" in response.content.decode()
        user.refresh_from_db()
        assert user.email_verified is False

    def test_a_missing_token_is_an_invalid_state(self):
        response = Client().get(VERIFY_URL)

        assert response.status_code == 400
        assert "This link is not valid" in response.content.decode()

    def test_the_token_is_never_echoed_into_the_page(self, make_user):
        token = make_verification_token(make_user())

        content = Client().get(VERIFY_URL, {"token": token}).content.decode()

        assert token not in content

    def test_the_response_is_not_cached_and_leaks_no_referrer(self, make_user):
        token = make_verification_token(make_user())

        response = Client().get(VERIFY_URL, {"token": token})

        assert response["Referrer-Policy"] == "no-referrer"
        # `never_cache` runs after the view and patches its header, so the exact
        # value is the union; what matters is that the response cannot be stored.
        assert "no-store" in response["Cache-Control"]

    def test_success_clears_the_pending_address(self, role_groups):
        client = Client()
        register(client)
        user = User.objects.get(email="ada@example.com")

        client.get(VERIFY_URL, {"token": make_verification_token(user)})

        assert PENDING_EMAIL_SESSION_KEY not in client.session
        # And the pending page now starts over instead of showing a stale address.
        assert client.get(CHECK_EMAIL_URL).status_code == 302

    def test_the_expired_state_offers_the_resend_action(self, make_user):
        user = make_user()
        client = Client()
        set_pending(client, user.email)

        response = client.get(VERIFY_URL, {"token": "not-a-token"})

        assert response.status_code == 400
        content = response.content.decode()
        assert "Send a new link" in content
        assert 'action="/verify-email/resend/"' in content

    def test_without_an_address_the_expired_state_offers_signup(self):
        response = Client().get(VERIFY_URL, {"token": "not-a-token"})

        assert response.status_code == 400
        assert "Create your account" in response.content.decode()
        assert 'action="/verify-email/resend/"' not in response.content.decode()


class TestResend:
    def test_without_a_pending_address_it_returns_to_signup(self):
        response = Client().post(RESEND_URL)

        assert response.status_code == 302
        assert response["Location"] == REGISTER_URL

    def test_get_is_not_allowed(self):
        response = Client().get(RESEND_URL)

        assert response.status_code == 405

    def test_outside_the_cooldown_it_queues_another_email(
        self, make_user, dispatched, django_capture_on_commit_callbacks
    ):
        user = make_user()
        client = Client()
        set_pending(client, user.email)
        cache.delete(resend_throttle_cache_key(user))

        with django_capture_on_commit_callbacks(execute=True):
            response = client.post(RESEND_URL)

        assert response.status_code == 302
        assert dispatched == [str(user.pk)]

    def test_inside_the_cooldown_it_answers_the_same_without_sending(
        self, make_user, dispatched, django_capture_on_commit_callbacks
    ):
        user = make_user()
        client = Client()
        set_pending(client, user.email)
        cache.add(resend_throttle_cache_key(user), 1, timeout=45)

        with django_capture_on_commit_callbacks(execute=True):
            response = client.post(RESEND_URL, follow=True)

        assert response.status_code == 200
        assert "If that address needs verification" in response.content.decode()
        assert dispatched == []

    def test_an_unknown_address_gets_the_same_answer_and_sends_nothing(
        self, dispatched, django_capture_on_commit_callbacks
    ):
        client = Client()
        set_pending(client, "nobody@example.com")

        with django_capture_on_commit_callbacks(execute=True):
            response = client.post(RESEND_URL, follow=True)

        assert response.status_code == 200
        assert "If that address needs verification" in response.content.decode()
        assert dispatched == []

    def test_a_verified_account_gets_the_same_answer_and_sends_nothing(
        self, make_user, dispatched, django_capture_on_commit_callbacks
    ):
        user = make_user(email_verified=True)
        client = Client()
        set_pending(client, user.email)

        with django_capture_on_commit_callbacks(execute=True):
            response = client.post(RESEND_URL, follow=True)

        assert response.status_code == 200
        assert "If that address needs verification" in response.content.decode()
        assert dispatched == []

    def test_the_pending_page_shows_the_confirmation_after_a_plain_post(
        self, role_groups
    ):
        client = Client()
        register(client)

        response = client.post(RESEND_URL, follow=True)

        assert response.status_code == 200
        assert "If that address needs verification" in response.content.decode()

    def test_htmx_swaps_the_panel_with_the_same_sentence(self, role_groups):
        client = Client()
        register(client)

        response = client.post(RESEND_URL, HTTP_HX_REQUEST="true")

        assert response.status_code == 200
        content = response.content.decode()
        assert 'id="resend-panel"' in content
        assert "we've sent a new link" in content
        assert "<html" not in content
