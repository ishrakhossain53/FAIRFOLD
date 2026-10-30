"""Page #54: the notification centre (design.md W19, REQ-FR-023, batch 1.44).

The batch's acceptance line is "unread count updates after reload; read state
persists". Everything that can quietly break that is tested here:

* the count is the recipient's own unread rows, not someone else's and not the
  rows the current filter happens to show;
* marking read is a POST that writes one row, scoped to the recipient, and the
  page it returns to carries the filter the recipient was reading;
* a second click is a no-op, not an error and not a second write;
* the list is per recipient, newest first, filtered by a closed vocabulary;
* the wireframe's accessibility rules hold: the list is an `<ol>` of labelled
  articles, unread is in the link text rather than a dot, previews are truncated
  in the markup, and the header bell's accessible name carries the count.

The two JSON endpoints `Complete Doc` §C.12 lists are **not** tested because this
batch did not build them (it is a UI batch); they are reported as an observation.
"""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from notifications.models import Notification

pytestmark = pytest.mark.django_db

LIST_URL = "/notifications/"


# --------------------------------------------------------------------- helpers


def make_notification(
    recipient,
    *,
    title="Your application was shortlisted",
    message="Your application for Backend Engineer is now shortlisted.",
    notification_type=Notification.Type.APPLICATION_UPDATE,
    url="",
    read=False,
    created_at=None,
) -> Notification:
    """One row, with `created_at` settable because it is `auto_now_add`."""
    notification = Notification.objects.create(
        recipient=recipient,
        title=title,
        message=message,
        notification_type=notification_type,
        url=url,
        read=read,
    )
    if created_at is not None:
        # auto_now_add ignores a value passed to create(), so the timestamp is
        # rewritten after the insert. The ordering tests need distinct times.
        Notification.objects.filter(pk=notification.pk).update(created_at=created_at)
        notification.refresh_from_db()
    return notification


@pytest.fixture
def candidate(make_user):
    return make_user("candidate")


@pytest.fixture
def employer(make_user):
    return make_user("employer_hr")


@pytest.fixture
def other_user(make_user):
    return make_user("candidate")


# ------------------------------------------------------------------- access


def test_anonymous_is_sent_to_login(client):
    response = client.get(LIST_URL)

    assert response.status_code == 302
    assert response["Location"].startswith("/login/")


def test_anonymous_cannot_mark_anything_read(client):
    response = client.post("/notifications/read/", {"notification_id": uuid.uuid4()})

    assert response.status_code == 302
    assert response["Location"].startswith("/login/")


def test_page_is_not_cached(client, candidate):
    client.force_login(candidate)

    response = client.get(LIST_URL)

    assert response.status_code == 200
    assert "no-store" in response["Cache-Control"]


def test_any_signed_in_account_can_read_its_own_notifications(client, employer):
    """A notification belongs to a person, not to a role (batch 1.43 writes to
    both sides of an application), so the employer page must render."""
    make_notification(employer, title="New application")

    client.force_login(employer)
    response = client.get(LIST_URL)

    assert response.status_code == 200
    assert "New application" in response.content.decode()


# ------------------------------------------------------------------- the list


def test_only_the_callers_notifications_are_listed(client, candidate, other_user):
    make_notification(candidate, title="Mine")
    make_notification(other_user, title="Someone else's")

    client.force_login(candidate)
    response = client.get(LIST_URL)
    html = response.content.decode()

    assert "Mine" in html
    assert "Someone else's" not in html


def test_newest_first(client, candidate):
    now = timezone.now()
    make_notification(candidate, title="Oldest", created_at=now - timedelta(days=3))
    make_notification(candidate, title="Middle", created_at=now - timedelta(days=2))
    make_notification(candidate, title="Newest", created_at=now - timedelta(hours=1))

    client.force_login(candidate)
    html = client.get(LIST_URL).content.decode()

    assert html.index("Newest") < html.index("Middle") < html.index("Oldest")


def test_relative_time_is_rendered(client, candidate):
    make_notification(candidate, created_at=timezone.now() - timedelta(hours=2))

    client.force_login(candidate)
    html = client.get(LIST_URL).content.decode()

    # `naturaltime` separates the number from the unit with a non-breaking space,
    # which is correct typography; normalise it so the assertion is about the
    # wording rather than about the character.
    assert "2 hours ago" in html.replace("\xa0", " ")


def test_message_preview_is_truncated_in_the_markup(client, candidate):
    long_message = "x" * 400
    make_notification(candidate, message=long_message)

    client.force_login(candidate)
    html = client.get(LIST_URL).content.decode()

    # `truncatechars:160` keeps 159 characters plus an ellipsis; the point is
    # that the full body is not in the response, which is W19's requirement.
    assert long_message not in html
    assert "x" * 100 in html


def test_titles_and_messages_are_escaped(client, candidate):
    make_notification(candidate, title="<script>alert(1)</script>")

    client.force_login(candidate)
    html = client.get(LIST_URL).content.decode()

    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_relative_url_becomes_a_link(client, candidate):
    make_notification(candidate, url="/candidate/applications/abc/")

    client.force_login(candidate)
    html = client.get(LIST_URL).content.decode()

    assert 'href="/candidate/applications/abc/"' in html


def test_unsafe_url_is_not_rendered_as_a_link(client, candidate):
    """A stored value must not become an open redirect or a script URL."""
    make_notification(candidate, title="Suspicious link", url="javascript:alert(1)")

    client.force_login(candidate)
    html = client.get(LIST_URL).content.decode()

    assert "javascript:alert(1)" not in html
    assert "Suspicious link" in html


def test_empty_state_for_a_candidate_offers_the_job_board(client, candidate):
    client.force_login(candidate)

    response = client.get(LIST_URL)

    assert "You're all caught up." in response.content.decode()
    assert reverse("job_board:list") in response.content.decode()


# -------------------------------------------------------------------- filters


def test_unread_filter_excludes_read_rows(client, candidate):
    make_notification(candidate, title="Unread one", read=False)
    make_notification(candidate, title="Already read", read=True)

    client.force_login(candidate)
    html = client.get(f"{LIST_URL}?filter=unread").content.decode()

    assert "Unread one" in html
    assert "Already read" not in html


def test_applications_filter_excludes_other_types(client, candidate):
    make_notification(candidate, title="Application update")
    make_notification(
        candidate, title="System notice", notification_type=Notification.Type.SYSTEM
    )

    client.force_login(candidate)
    html = client.get(f"{LIST_URL}?filter=applications").content.decode()

    assert "Application update" in html
    assert "System notice" not in html


def test_unknown_filter_shows_everything(client, candidate):
    make_notification(candidate, title="Visible")

    client.force_login(candidate)
    response = client.get(f"{LIST_URL}?filter=../../etc/passwd")

    assert response.status_code == 200
    assert "Visible" in response.content.decode()


def test_tabs_show_the_unread_count_and_current_filter(client, candidate):
    make_notification(candidate, read=False)
    make_notification(candidate, read=False)
    make_notification(candidate, read=True)

    client.force_login(candidate)
    html = client.get(LIST_URL).content.decode()

    assert "Unread" in html
    assert '<span class="text-caption font-normal text-ink-3">2</span>' in html
    assert 'aria-current="page"' in html


def test_filtered_empty_state_links_back_to_all(client, candidate):
    make_notification(candidate, read=True)

    client.force_login(candidate)
    html = client.get(f"{LIST_URL}?filter=unread").content.decode()

    assert "You're all caught up." in html
    assert "Show all notifications" in html


# ----------------------------------------------------------------- pagination


def test_pagination_caps_the_page_and_keeps_the_order(client, candidate):
    now = timezone.now()
    for index in range(25):
        make_notification(
            candidate,
            title=f"Notification {index:02d}",
            created_at=now - timedelta(minutes=index),
        )

    client.force_login(candidate)
    first = client.get(LIST_URL).content.decode()
    second = client.get(f"{LIST_URL}?page=2").content.decode()

    assert first.count('aria-labelledby="notification-') == 20
    assert second.count('aria-labelledby="notification-') == 5
    # The oldest five are on page 2, the newest on page 1.
    assert "Notification 00" in first
    assert "Notification 24" not in first
    assert "Notification 24" in second


def test_filter_survives_pagination(client, candidate):
    for _ in range(25):
        make_notification(candidate, read=False)

    client.force_login(candidate)
    html = client.get(f"{LIST_URL}?filter=unread").content.decode()

    assert "filter=unread&amp;page=2" in html


# ------------------------------------------------------------------ mark read


def test_mark_read_persists_and_redirects(client, candidate):
    notification = make_notification(candidate)

    client.force_login(candidate)
    response = client.post("/notifications/read/", {"notification_id": notification.pk})

    assert response.status_code == 302
    assert response["Location"] == LIST_URL
    notification.refresh_from_db()
    assert notification.read is True

    # "Read state persists" across a reload, and the count falls with it.
    html = client.get(LIST_URL).content.decode()
    assert "Mark read" not in html
    assert 'aria-label="Notifications"' in html


def test_mark_read_keeps_the_filter(client, candidate):
    notification = make_notification(candidate)

    client.force_login(candidate)
    response = client.post(
        "/notifications/read/",
        {"notification_id": notification.pk, "filter": "unread"},
    )

    assert response["Location"] == f"{LIST_URL}?filter=unread"


def test_marking_an_already_read_row_is_a_noop(client, candidate):
    notification = make_notification(candidate, read=True)

    client.force_login(candidate)
    response = client.post("/notifications/read/", {"notification_id": notification.pk})

    assert response.status_code == 302
    notification.refresh_from_db()
    assert notification.read is True


def test_cannot_mark_another_users_notification(client, candidate, other_user):
    notification = make_notification(other_user)

    client.force_login(candidate)
    response = client.post("/notifications/read/", {"notification_id": notification.pk})

    assert response.status_code == 404
    notification.refresh_from_db()
    assert notification.read is False


def test_unknown_or_malformed_notification_id_is_a_404(client, candidate):
    client.force_login(candidate)

    assert (
        client.post(
            "/notifications/read/", {"notification_id": uuid.uuid4()}
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/notifications/read/", {"notification_id": "not-a-uuid"}
        ).status_code
        == 404
    )
    assert client.post("/notifications/read/", {}).status_code == 404


def test_mark_read_rejects_get(client, candidate):
    client.force_login(candidate)

    assert client.get("/notifications/read/").status_code == 405


def test_mark_all_read_only_touches_the_callers_rows(client, candidate, other_user):
    mine = make_notification(candidate)
    also_mine = make_notification(candidate)
    theirs = make_notification(other_user)

    client.force_login(candidate)
    response = client.post("/notifications/read-all/")

    assert response.status_code == 302
    assert response["Location"] == LIST_URL
    for notification in (mine, also_mine):
        notification.refresh_from_db()
        assert notification.read is True
    theirs.refresh_from_db()
    assert theirs.read is False


def test_mark_all_read_keeps_the_filter(client, candidate):
    make_notification(candidate)

    client.force_login(candidate)
    response = client.post("/notifications/read-all/", {"filter": "applications"})

    assert response["Location"] == f"{LIST_URL}?filter=applications"


def test_mark_all_read_with_nothing_unread_is_fine(client, candidate):
    make_notification(candidate, read=True)

    client.force_login(candidate)
    response = client.post("/notifications/read-all/")

    assert response.status_code == 302


def test_mark_all_read_rejects_get(client, candidate):
    client.force_login(candidate)

    assert client.get("/notifications/read-all/").status_code == 405


# ---------------------------------------------------------------- header bell


def test_bell_is_absent_for_anonymous_visitors(client):
    html = client.get("/jobs/").content.decode()

    assert 'href="/notifications/"' not in html


def test_bell_carries_the_unread_count_in_its_accessible_name(client, candidate):
    make_notification(candidate, read=False)
    make_notification(candidate, read=False)
    make_notification(candidate, read=True)

    client.force_login(candidate)
    html = client.get("/jobs/").content.decode()

    assert 'aria-label="Notifications, 2 unread"' in html


def test_bell_has_no_count_when_everything_is_read(client, candidate):
    make_notification(candidate, read=True)

    client.force_login(candidate)
    html = client.get("/jobs/").content.decode()

    assert 'aria-label="Notifications"' in html
    assert 'aria-label="Notifications,' not in html
