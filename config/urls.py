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
    path("assessments/", include("assessments.urls")),
    path("interviews/", include("interviews.urls")),
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