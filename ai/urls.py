"""AI provider abstraction, bias auditing and the rationale path.

Routes are declared per feature as that feature lands. An empty `urlpatterns`
would make `include()` mount a prefix with nothing under it, which returns 404
for every URL a page template links to.
"""

from django.urls import path

app_name = "ai"

urlpatterns: list = []
