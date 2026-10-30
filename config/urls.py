"""Root URL configuration.

Two mounts, deliberately:

- ``/api/v1/`` — versioned DRF API. The version lives in the path, not in a
  header, so a URL pasted into a support ticket still identifies the version.
- everything else — server-rendered HTMX pages.

`APPEND_SLASH` stays True: with HTMX, a POST to a URL missing its trailing slash
is turned into a GET and the action silently does nothing. The apps that take
POSTs therefore declare their patterns with the slash.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "FairFold administration"
admin.site.site_title = "FairFold admin"
admin.site.index_title = "Operations"

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("api/v1/", include("api.urls")),
    path("accounts/", include("accounts.urls")),
    path("candidate/", include("candidates.urls")),
    path("employer/", include("employers.urls")),
    # Public job board, pages #4 and #5 (REQ-FR-042). A separate mount and
    # namespace from `/employer/`: these routes are anonymous and must not
    # acquire the portal's employer guard by being nested under it.
    path("jobs/", include("employers.public_urls")),
    path("assessments/", include("assessments.urls")),
    path("interviews/", include("interviews.urls")),
    # Notification centre, page #54 (W19, REQ-FR-023). Its own mount and
    # namespace: every signed-in account reads its own notifications, so nesting
    # it under `/candidate/` or `/employer/` would attach a role guard the page
    # must not have.
    path("notifications/", include("notifications.urls")),
    # Public auth pages at the root: `/register/` and `/verify-email/`
    # (design.md pages #6 and #11). `EMAIL_VERIFICATION_URL` points at the
    # latter, so the prefix is fixed by that setting, not a preference.
    path("", include("accounts.public_urls")),
    path("", include("core.urls")),
]

# Django's static-file view is for local development only. In production
# WhiteNoise serves `staticfiles/`; serving media from Django at all is a
# temporary measure for resume files awaiting the S3/MinIO backend.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# The API schema is served only with DEBUG on. drf-spectacular can expose
# internal paths, and the generated document is an aid, not a deliverable.
if settings.DEBUG:
    from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

    urlpatterns += [
        path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
        path(
            "api/docs/",
            SpectacularSwaggerView.as_view(url_name="schema"),
            name="swagger-ui",
        ),
    ]

# A deliberate 404 for an unmatched URL would otherwise render Django's default
# page, which leaks the URL pattern and the DEBUG flag in its wording.
handler404 = "core.views.error_404"
handler500 = "core.views.error_500"
handler403 = "core.views.error_403"
