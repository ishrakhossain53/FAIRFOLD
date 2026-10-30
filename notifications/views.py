"""Page #54: the notification centre (design.md W19, REQ-FR-023, batch 1.44).

The page is **per recipient**, because the `notifications` table is per recipient
(Arch Doc §5.1, batch 1.43): a row already names exactly one `user`, so every
query here starts from `request.user` and no route takes a user id. That is what
makes "another user cannot read my notifications" structural rather than a
comparison a later edit could drop -- the same reason the candidate application
pages scope their queryset instead of comparing owners after a fetch.

**Two filters, not the wireframe's four.** W19 draws `[All] [Unread 3]
[Applications] [Messages]`. The model's documented vocabulary (`Complete Doc`
§C.4) has five types and none of them is a message: messaging is REQ-FR-043,
Phase 3 (batch 3.20), and no row can carry that type yet. A tab that always
returns nothing is the state W28 was written to prevent, so the "Messages" tab is
omitted until the type exists. "Applications" maps to `application_update`, the
one type batches 1.43's apply/decision wiring writes.

**Marking read is a POST, not a link.** A GET that changes state is CSRF-able and
would be fired by a prefetch. The id travels in the body (like the resume delete
page) so the routes are fixed paths, which keeps each one covered by a single
authorization-matrix row instead of a parameterised sample.

**The documented JSON endpoints are not this batch.** `Complete Doc` §C.12 lists
`GET /api/v1/notifications/` and `POST /api/v1/notifications/{id}/read/`; batch
1.44 is a UI batch and the template pages do not consume the product's own API
(no page does). Those two endpoints remain unbuilt and are reported, not guessed
at here.
"""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST

from notifications.models import Notification

# The filter is a closed vocabulary, never free text: an unknown value is
# treated as "all" rather than as an empty list, so a hand-edited URL shows the
# recipient's notifications instead of looking like an empty inbox.
FILTERS: dict[str, str] = {
    "all": "All",
    "unread": "Unread",
    "applications": "Applications",
}

# W19 is a list, not a feed; 20 rows keeps a recipient with hundreds of
# notifications from rendering every preview on one request.
PAGE_SIZE = 20


def safe_link(url: str) -> str:
    """Return `url` only when it is a path on this site.

    `Notification.url` is written by `matching.services` as a relative page path
    (`/candidate/applications/<id>/`), but the column accepts any string and the
    template turns it into an `href`. Restricting rendering to a single-slash
    path keeps a bad value (an absolute host, `javascript:`, `//evil.example`)
    from becoming a link: a notification is not a place to discover an open
    redirect. An unusable value renders as a title with no link, which still
    tells the recipient what happened.
    """
    if url.startswith("/") and not url.startswith("//"):
        return url
    return ""


def _filter_name(request: HttpRequest) -> str:
    """The requested filter, or `all` when it is absent or unknown."""
    requested = request.POST.get("filter") or request.GET.get("filter") or "all"
    return requested if requested in FILTERS else "all"


def _list_url(filter_name: str) -> str:
    """The list page, with the filter kept when there is one to keep.

    Only a value from `FILTERS` can reach this function, so the redirect target
    is one of four fixed strings and never a caller-supplied URL.
    """
    url = reverse("notification_center:list")
    if filter_name != "all":
        return f"{url}?filter={filter_name}"
    return url


def _recipient_notifications(user):
    """The caller's notifications, newest first.

    The model's default ordering is already `-created_at`; `-id` is added so a
    page is stable when several rows share a timestamp (the same tie-break the
    candidate tracker uses).
    """
    return Notification.objects.filter(recipient=user).order_by("-created_at", "-id")


def _row(notification: Notification) -> dict:
    """The template's view of one notification.

    `link` is resolved here rather than in the template so the only way an
    `href` can be produced is through `safe_link()`. Everything else is rendered
    straight from the row; no candidate identity is added, and the message is
    already alias-only where the recipient is an employer (REQ-FR-054).
    """
    return {
        "notification": notification,
        "link": safe_link(notification.url),
    }


@never_cache
@login_required
@require_http_methods(["GET"])
def notification_list(request: HttpRequest) -> HttpResponse:
    """Page #54: the recipient's notifications, filtered and paginated.

    Any authenticated account can use this page. A notification belongs to a
    person, not to a role: candidates and employers both receive them (batch
    1.43 writes one copy for each side of an application), and an interviewer or
    platform admin may receive one later. Restricting the page by group would
    mean a recipient whose role changed can no longer read messages addressed to
    them -- and would make the header bell a dead control for those accounts.
    """
    filter_name = _filter_name(request)

    base = _recipient_notifications(request.user)
    queryset = base
    if filter_name == "unread":
        queryset = queryset.filter(read=False)
    elif filter_name == "applications":
        queryset = queryset.filter(
            notification_type=Notification.Type.APPLICATION_UPDATE
        )

    paginator = Paginator(queryset, PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page"))
    # Computed with the current page number: `get_elided_page_range()` defaults
    # to page 1, so calling it from the template would draw the same first-page
    # window on every page.
    page_range = paginator.get_elided_page_range(page_obj.number)

    # The badge counts every unread row, not the rows the current filter would
    # show: W19's "Unread 3" is the same number the header bell displays, and a
    # tab count that changed with the tab would be answering a different question.
    unread_count = base.filter(read=False).count()

    tabs = [
        {"key": key, "label": label, "count": unread_count if key == "unread" else None}
        for key, label in FILTERS.items()
    ]

    return render(
        request,
        "notifications/list.html",
        {
            "rows": [_row(notification) for notification in page_obj.object_list],
            "page_obj": page_obj,
            "page_range": page_range,
            "filter_name": filter_name,
            "tabs": tabs,
            "unread_count": unread_count,
            "total": paginator.count,
            # Distinguishes "nothing has ever happened" from "nothing matches
            # this filter", which are different pages: the first offers a way to
            # get started, the second a way back to the full list.
            "has_any": base.exists(),
        },
    )


@never_cache
@login_required
@require_POST
def mark_read(request: HttpRequest) -> HttpResponse:
    """Mark one of the caller's own notifications as read.

    The row is looked up by `recipient=request.user`, so another account's id is
    the same 404 as an id that exists nowhere and this route cannot be used to
    confirm that a notification exists. An already-read row is a no-op: pressing
    the button twice is not an error, and it must not rewrite `read` (or, later,
    anything else) on a second click.

    No audit entry is written. `AuditLogEntry` records decisions and state
    changes the product must be able to explain (AGENTS.md); "the recipient
    opened their own message" is neither, and the table is deliberately
    append-only with no PII.
    """
    raw_id = request.POST.get("notification_id", "")

    try:
        notification = Notification.objects.get(pk=raw_id, recipient=request.user)
    except (Notification.DoesNotExist, ValidationError, TypeError, ValueError):
        raise Http404("Notification not found.")

    if not notification.read:
        notification.read = True
        notification.save(update_fields=["read"])

    return redirect(_list_url(_filter_name(request)))


@never_cache
@login_required
@require_POST
def mark_all_read(request: HttpRequest) -> HttpResponse:
    """Mark every unread notification of the caller as read.

    W19's "Mark all as read" means all, not "all on this page": a button that
    leaves unread rows on page 2 is the kind of half-done action that teaches a
    recipient not to trust the count. The queryset is scoped to the recipient, so
    another account's rows are untouched.
    """
    Notification.objects.filter(recipient=request.user, read=False).update(read=True)
    return redirect(_list_url(_filter_name(request)))
