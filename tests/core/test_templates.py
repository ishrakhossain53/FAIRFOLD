"""Rendered pages must not leak template syntax or template-comment prose.

Django's ``{# ... #}`` is a comment only when both delimiters are on the **same
line**. A multi-line one is not an error: it is rendered as literal text, so it
appears at the top of every page that extends ``base.html``. That shipped once
(five blocks in ``base.html``, one in ``errors/500.html``) and put build notes
above the header on every page.

A unit test on the template source would have to re-implement Django's
tokenizer, so these render the pages instead: the symptom is text in the
response, which is exactly what a visitor saw.
"""

import pathlib
import re

import pytest
from django.conf import settings
from django.contrib.staticfiles import finders
from django.test import Client

# Pages a visitor can reach without an account. They all extend base.html, which
# is where the leak lived.
PUBLIC_PAGES = ["/", "/register/", "/login/"]

# Template syntax that must never survive rendering. `{%` and `{{` are here for
# the same reason as `{#`: if one reaches the browser, the template engine did
# not treat it as markup.
LEAK_MARKERS = ["{#", "{%", "{{"]

# Prose from the comments that leaked, asserted separately so a future
# single-line comment cannot quietly reintroduce the same visible text.
LEAKED_PROSE = [
    "Built by `npm run build`",
    "Skip link. The first focusable element",
    "Flash messages are an aria-live region",
    "Chart.js is loaded ONLY on pages",
]


@pytest.mark.django_db
@pytest.mark.parametrize("path", PUBLIC_PAGES)
def test_public_pages_render_no_template_syntax(path):
    response = Client().get(path)

    assert response.status_code == 200
    body = response.content.decode()
    for marker in LEAK_MARKERS:
        assert marker not in body, f"{path} leaked {marker!r} into the response"


@pytest.mark.django_db
@pytest.mark.parametrize("path", PUBLIC_PAGES)
def test_public_pages_render_no_template_comment_prose(path):
    response = Client().get(path)

    body = response.content.decode()
    for prose in LEAKED_PROSE:
        assert prose not in body, f"{path} rendered template-comment prose"


@pytest.mark.django_db
def test_every_static_asset_referenced_by_base_is_findable():
    # The favicon `{% static %}` link in base.html was a 404 on every page: the
    # reference existed, the file did not, and nothing fails when collectstatic
    # finds one fewer file than the template names. Checking the finders catches
    # the whole class (css, js, img) without depending on a running server.
    source = (pathlib.Path(settings.BASE_DIR) / "templates/base.html").read_text()
    referenced = set(re.findall(r"{%\s*static\s+'([^']+)'\s*%}", source))

    assert referenced, "base.html should reference static assets"
    missing = sorted(name for name in referenced if finders.find(name) is None)
    assert not missing, f"static files referenced by base.html are missing: {missing}"
