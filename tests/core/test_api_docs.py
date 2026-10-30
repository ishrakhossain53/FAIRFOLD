"""The API docs page must not depend on assets the CSP blocks.

`/api/docs/` is a development aid (it is only routed when `DEBUG` is on), but it
was unusable: drf-spectacular's default template loads Swagger UI from
cdn.jsdelivr.net, and `CONTENT_SECURITY_POLICY` allows only `'self'`, so the
browser blocked the stylesheet, the two scripts and the favicon and rendered an
empty page. The assets are now vendored from the pinned `swagger-ui-dist`
devDependency by `npm run vendor`.

These tests guard the two halves of that fix: the setting must point at this
site, and the files the setting names must be present to collect. A future
upgrade that silently restores the CDN default would otherwise only be noticed
in a browser console.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.test import RequestFactory
from drf_spectacular.views import SpectacularSwaggerView

SWAGGER_ASSETS = (
    "swagger-ui.css",
    "swagger-ui-bundle.js",
    "swagger-ui-standalone-preset.js",
    "favicon-32x32.png",
)


def test_swagger_ui_is_served_from_this_site():
    dist = settings.SPECTACULAR_SETTINGS["SWAGGER_UI_DIST"]

    assert dist == f"{settings.STATIC_URL}vendor/swagger-ui"
    assert not dist.startswith(("http://", "https://"))


def test_every_vendored_swagger_asset_exists():
    root = Path(settings.BASE_DIR) / "static" / "vendor" / "swagger-ui"

    assert [name for name in SWAGGER_ASSETS if not (root / name).is_file()] == []


def test_the_docs_page_references_the_local_assets():
    view = SpectacularSwaggerView.as_view(url_name="schema")

    # `schema` is only routed when DEBUG is on, and the test settings run with
    # DEBUG off, so the view is exercised directly rather than through the URL.
    with patch("drf_spectacular.views.reverse", return_value="/api/schema/"):
        response = view(RequestFactory().get("/api/docs/"))

    response.render()
    html = response.content
    if isinstance(html, bytes):
        html = html.decode()

    assert "/static/vendor/swagger-ui/swagger-ui.css" in html
    assert "/static/vendor/swagger-ui/swagger-ui-bundle.js" in html
    assert "cdn.jsdelivr.net" not in html
