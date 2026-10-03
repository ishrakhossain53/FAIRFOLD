"""Candidate dashboard, resume upload, journey mapping and profile.

Routes are declared per feature as that feature lands. An empty `urlpatterns`
would make `include()` mount a prefix with nothing under it, which returns 404
for every URL a page template links to.
"""

from django.urls import path  # noqa: F401 -- added per route below

app_name = "candidates"

urlpatterns: list = []
