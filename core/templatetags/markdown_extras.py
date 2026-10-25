"""Template filter wrapper for `core.markdown`.

The filter exists so a template never calls a renderer directly and then forgets
`mark_safe` (or, worse, marks the raw source safe). `render_markdown()` returns
HTML built from escaped input and constant tags, so marking its result safe is
the intended contract; `design.md` 7.22 records it.
"""

from __future__ import annotations

from django import template
from django.utils.safestring import SafeString, mark_safe

from core.markdown import render_markdown

register = template.Library()


@register.filter(name="markdown")
def markdown_filter(value: str | None) -> SafeString:
    """Render job text as the documented Markdown subset."""
    return mark_safe(render_markdown(value))
