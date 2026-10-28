"""The job-text Markdown renderer (design.md 7.22, REQ-SEC-006).

The renderer is the one place employer-authored text becomes HTML, so these
tests are written from the attacker's side as well as the author's:

* every supported construct renders the documented tag;
* raw HTML never becomes markup, even inside a code span or a link title;
* only the scheme allowlist produces an `<a>`, and a refused URL stays literal;
* the output contains only the tags in `ALLOWED_TAGS` -- no attribute can be
  injected because no user-controlled string ever lands in a tag name, and the
  only attribute is an href that passed `_safe_url`.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser

from django.template import Context, Template

from core.markdown import ALLOWED_TAGS, render_markdown


class _TagCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tags: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        self.tags.append(tag)


def tags_in(html: str) -> set[str]:
    collector = _TagCollector()
    collector.feed(html)
    return set(collector.tags)


class TestBlocks:
    def test_paragraphs_and_soft_breaks(self):
        assert render_markdown("One line\ntwo lines") == (
            "<p>One line<br>\ntwo lines</p>"
        )
        assert render_markdown("First\n\nSecond") == ("<p>First</p>\n<p>Second</p>")

    def test_headings_shift_two_levels(self):
        assert render_markdown("# Title") == "<h3>Title</h3>"
        assert render_markdown("## Section") == "<h4>Section</h4>"
        assert render_markdown("### Detail") == "<h5>Detail</h5>"
        # Four hashes are not in the subset and stay literal.
        assert render_markdown("#### Too deep") == "<p>#### Too deep</p>"

    def test_unordered_list(self):
        assert render_markdown("- one\n- two") == ("<ul><li>one</li><li>two</li></ul>")

    def test_ordered_list_accepts_dot_and_parenthesis(self):
        assert render_markdown("1. one\n2. two") == (
            "<ol><li>one</li><li>two</li></ol>"
        )
        assert render_markdown("1) one\n2) two") == (
            "<ol><li>one</li><li>two</li></ol>"
        )

    def test_blockquote(self):
        assert render_markdown("> quoted") == ("<blockquote><p>quoted</p></blockquote>")

    def test_blockquote_can_hold_a_list(self):
        assert render_markdown("> - a\n> - b") == (
            "<blockquote><ul><li>a</li><li>b</li></ul></blockquote>"
        )

    def test_horizontal_rule(self):
        assert render_markdown("---") == "<hr>"
        assert render_markdown("before\n\n---\n\nafter") == (
            "<p>before</p>\n<hr>\n<p>after</p>"
        )

    def test_blank_input_is_empty(self):
        assert render_markdown("") == ""
        assert render_markdown("   \n\n ") == ""
        assert render_markdown(None) == ""


class TestInline:
    def test_bold_italic_and_code(self):
        assert render_markdown("**bold**") == "<p><strong>bold</strong></p>"
        assert render_markdown("*italic*") == "<p><em>italic</em></p>"
        assert render_markdown("`code`") == "<p><code>code</code></p>"

    def test_nested_emphasis_keeps_its_order(self):
        assert render_markdown("**a *b* c**") == (
            "<p><strong>a <em>b</em> c</strong></p>"
        )

    def test_underscores_are_not_emphasis(self):
        assert render_markdown("snake_case_name") == "<p>snake_case_name</p>"

    def test_code_span_is_not_formatted(self):
        assert render_markdown("`**not bold** <b>`") == (
            "<p><code>**not bold** &lt;b&gt;</code></p>"
        )

    def test_unmatched_markers_stay_literal(self):
        assert render_markdown("**open") == "<p>**open</p>"
        assert render_markdown("*open") == "<p>*open</p>"

    def test_italic_inside_a_link_title(self):
        assert render_markdown("[**bold**](https://example.com)") == (
            '<p><a href="https://example.com" rel="noopener noreferrer">'
            "<strong>bold</strong></a></p>"
        )


class TestLinks:
    def test_https_and_mailto_are_linkified(self):
        assert render_markdown("[docs](https://example.com/a?b=1&c=2)") == (
            '<p><a href="https://example.com/a?b=1&amp;c=2" '
            'rel="noopener noreferrer">docs</a></p>'
        )
        assert render_markdown("[mail](mailto:jobs@example.com)") == (
            '<p><a href="mailto:jobs@example.com" '
            'rel="noopener noreferrer">mail</a></p>'
        )

    def test_dangerous_and_relative_urls_stay_literal(self):
        for source in (
            "[x](javascript:alert)",
            "[x](JavaScript:alert)",
            "[x](data:text/html;base64,PHNjcmlwdD4=)",
            "[x](/employer/jobs/)",
            "[x](//evil.example)",
        ):
            rendered = render_markdown(source)
            assert "<a " not in rendered, source

    def test_a_quote_in_a_url_is_refused(self):
        rendered = render_markdown('[x](https://example.com/"onmouseover=alert)')

        assert "<a " not in rendered
        assert "&quot;" in rendered

    def test_html_in_a_link_title_is_escaped(self):
        rendered = render_markdown(
            "[<img src=x onerror=alert(1)>](https://example.com)"
        )

        assert "<img" not in rendered
        assert "&lt;img" in rendered

    def test_protocol_relative_link_is_not_turned_into_an_anchor(self):
        assert "<a " not in render_markdown("[x](www.example.com)")


class TestUntrustedHtml:
    def test_script_tag_is_text(self):
        rendered = render_markdown("<script>alert('x')</script>")

        assert rendered == ("<p>&lt;script&gt;alert(&#x27;x&#x27;)&lt;/script&gt;</p>")

    def test_event_handler_attribute_never_renders(self):
        rendered = render_markdown('<img src=x onerror="alert(1)">')

        assert "<img" not in rendered
        assert "onerror" in rendered  # visible as text, not as an attribute
        assert "&lt;img" in rendered

    def test_only_allowlisted_tags_are_emitted(self):
        source = """
            # H
            **b** *i* `c` [l](https://example.com)
            - a
            1. b
            > q
            ---
            <script>alert(1)</script>
            <a href="https://evil.example">x</a>
        """
        rendered = render_markdown(source)

        assert tags_in(rendered) <= ALLOWED_TAGS
        assert "script" not in tags_in(rendered)

    def test_placeholder_delimiter_cannot_be_forged(self):
        # NUL is the token delimiter; a stored value containing it must not be
        # able to point at an internal replacement (and PostgreSQL TEXT would
        # reject it anyway).
        rendered = render_markdown("\x000\x00 **bold**")

        assert "\x00" not in rendered
        assert "<strong>bold</strong>" in rendered


class TestTemplateFilter:
    def test_filter_marks_the_result_safe(self):
        rendered = Template("{% load markdown_extras %}{{ text|markdown }}").render(
            Context({"text": "**strong** & <script>"})
        )

        # Autoescaping applies to the input string; the filter's own output is
        # already escaped HTML and is not escaped a second time.
        assert rendered == ("<p><strong>strong</strong> &amp; &lt;script&gt;</p>")
        assert not re.search(r"<p>&lt;p&gt;", rendered)
