"""The unread count behind the header bell (design.md §5.4, W19, batch 1.44).

The bell lives in `templates/base.html`, so its count has to be available to
every page that extends the base. Passing it from each view would mean every new
page can forget it, and the one that forgets shows a bell with no badge -- a bug
that looks like "no notifications" rather than like a missing argument. A
context processor computes it in one place.

**Anonymous requests cost nothing and query nothing.** The header only renders
the bell for a signed-in user, and `request.user` on an anonymous request is
`AnonymousUser`, whose `is_authenticated` is False. Email templates are rendered
without a request (context processors receive `None`) and therefore also return
zero without touching the database.

**One count query per authenticated page render.** The alternative -- a cached
counter -- invents a cache-invalidation problem for a number that has to be
correct at the moment the page is shown: a stale badge is exactly the failure
W19's "unread count updates after reload" acceptance line rules out.
"""

from __future__ import annotations

from django.http import HttpRequest

from notifications.models import Notification


def unread_notification_count(request: HttpRequest | None) -> dict[str, int]:
    """Add `unread_notification_count` to every template context.

    The value is the number of the caller's unread rows across all types, which
    is the same number the page's "Unread" tab shows.
    """
    if request is None:
        return {"unread_notification_count": 0}

    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {"unread_notification_count": 0}

    return {
        "unread_notification_count": Notification.objects.filter(
            recipient=user, read=False
        ).count()
    }
