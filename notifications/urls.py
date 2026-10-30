"""Template routes for the notification centre (design.md page #54, W19).

Mounted at `/notifications/` by `config.urls`. The namespace is
`notification_center`, not `notifications`: `notifications.api_urls` already
declares the `notifications` namespace under `/api/v1/notifications/`, and
Django's resolver keeps one entry per namespace name. Giving the HTML page its
own namespace keeps `reverse()` unambiguous for both the API and the pages --
the same split `candidate_portal`/`candidates` uses.

`read/` takes the notification id in the POST body rather than in the path. A
`<uuid:notification_id>/read/` route would be parameterised, and the
authorization matrix deliberately refuses to guess a sample value for those
(tests/core/test_authz_matrix.py); a fixed path keeps the whole page covered by
three matrix rows.
"""

from __future__ import annotations

from django.urls import path

from notifications import views

app_name = "notification_center"

urlpatterns = [
    path("", views.notification_list, name="list"),
    path("read/", views.mark_read, name="read"),
    path("read-all/", views.mark_all_read, name="read-all"),
]
