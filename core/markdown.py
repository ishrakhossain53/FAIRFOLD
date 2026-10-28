"""The minimal, escape-first Markdown renderer for employer-authored job text.

`design.md` 7.22 is the contract: the four long-text `jobs` columns store
Markdown source, and this module is the only thing that turns that source into
HTML. Arch Doc §5.1 records the storage decision next to the columns.

Why a hand-written subset instead of a Markdown library
-------------------------------------------------------

A general Markdown implementation accepts raw HTML, images, tables and
`javascript:` links by default; every one of those is a way for employer text to
inject markup into a candidate-facing page (`REQ-SEC-006`). Locking a third-party
renderer down to a safe subset costs a dependency, a sanitiser and a version
upgrade path. This product needs bold, italic, code, safe links, one level of
lists, headings, quotes and dividers -- about eighty lines of code -- so the
smaller, auditable surface wins.

The safety property is structural, not a filter applied afterwards:

1. **Escape first.** `html.escape()` runs on the whole input before any pattern
   is applied, so a `<script>` in a job description is already text by the time
   the renderer starts. Nothing below can introduce a tag except the constants in
   this file.
2. **Allowlist the URL.** A link is emitted only when its scheme is `http`,
   `https` or `mailto` and it survives a character check. Anything else stays
   literal text (`javascript:alert(1)` included).
3. **Placeholders, not nested substitution.** Code spans, links and emphasis are
   replaced with tokens and restored at the end. That is what keeps `**` from
   rewriting a URL or an attribute, and what makes `***x***` produce harmless
   literal asterisks instead of crossed tags.

Heading levels are shifted two down (`#` -> `h3`, `##` -> `h4`, `###` -> `h5`):
the rendered fragment always sits under the page's `h2`, and an `h1` inside a
posting would break the document outline. `design.md` 7.22 documents that rule.

This module deliberately imports no Django, for the same reason `ai.citation`
does: it is a pure function, so it can be tested without a database and reused
by the preview endpoint, the page and a future public board without a request.
"""

from __future__ import annotations

import html
import re
from urllib.parse import urlsplit

__all__ = ["render_markdown"]

#: `#`, `##`, `###` at the start of a line. Four or more hashes stay literal.
_HEADING_RE = re.compile(r"^\s{0,3}(#{1,3})\s+(.+?)\s*$")

#: A minus, asterisk or underscore rule on its own line.
_HR_RE = re.compile(r"^\s{0,3}(?:-{3,}|\*{3,}|_{3,})\s*$")

#: One level of unordered list. The marker needs a space so `-1` stays text.
_UL_RE = re.compile(r"^\s{0,3}[-*+]\s+(.+?)\s*$")

#: `1.` or `1)`; both are common in job ads. No nesting.
_OL_RE = re.compile(r"^\s{0,3}(\d{1,9})[.)]\s+(.+?)\s*$")

#: `> quoted` lines; the optional space is Markdown's own rule. The marker is
#: matched after escaping, where a real `>` is `&gt;`; a literal `&gt;` in the
#: source became `&amp;gt;` and therefore does not match.
_QUOTE_RE = re.compile(r"^\s{0,3}&gt;\s?(.*)$")

#: Inline code. Fenced blocks are not part of the subset.
_CODE_RE = re.compile(r"`([^`\n]+)`")

#: `[text](url)`. The URL stops at whitespace or a closing paren, so a
#: parenthesised URL is not linkified -- refusing is safer than guessing.
_LINK_RE = re.compile(r"\[([^\]\n]+)\]\(([^()\s]+)\)")

#: `**bold**`; the lookarounds refuse `** spaced **` and empty markers.
_BOLD_RE = re.compile(r"\*\*(?=\S)(.+?)(?<=\S)\*\*")

#: `*italic*`; underscores are deliberately NOT emphasis, so `snake_case` and
#: `DB_*` stay readable in a job description.
_ITALIC_RE = re.compile(r"(?<!\*)\*(?=\S)([^*\n]+?)(?<=\S)\*(?!\*)")

#: Placeholder for a rendered fragment. NUL cannot reach this module from a
#: database column and is stripped in `render_markdown()` before escaping, so a
#: literal `\x00<n>\x00` in the input cannot collide with a token.
_TOKEN_RE = re.compile("\x00(\\d+)\x00")

#: The only tags this module emits. Kept as a constant so a reviewer can see the
#: whole output surface in one place; tests assert that nothing else escapes.
ALLOWED_TAGS = frozenset(
    {
        "p",
        "br",
        "strong",
        "em",
        "code",
        "a",
        "ul",
        "ol",
        "li",
        "h3",
        "h4",
        "h5",
        "blockquote",
        "hr",
    }
)

ALLOWED_SCHEMES = frozenset({"http", "https", "mailto"})

#: Characters that have no business in an href. The value is escaped anyway, so
#: this is defence in depth rather than the only barrier.
_FORBIDDEN_URL_CHARS = frozenset("\"'`<>\\")


def _token(rendered: str, tokens: list[str]) -> str:
    """Store `rendered` and return the placeholder that stands in for it."""
    tokens.append(rendered)
    return f"\x00{len(tokens) - 1}\x00"


def _restore(text: str, tokens: list[str]) -> str:
    """Replace every placeholder with its fragment, recursively.

    A bold fragment can contain an italic or link token created while its inner
    text was processed, so this resolves nested placeholders rather than doing a
    single pass. Substitution always moves to an earlier token, so it terminates.
    """

    def replace(match: re.Match[str]) -> str:
        return _restore(tokens[int(match.group(1))], tokens)

    return _TOKEN_RE.sub(replace, text)


def _safe_url(raw: str) -> str | None:
    """Return an escaped href for an allowed URL, or None.

    `raw` has already been HTML-escaped, so it is unescaped once for parsing and
    re-escaped for the attribute. A relative link, an anchor and a protocol
    handler other than `http`, `https` and `mailto` are all refused: job text has
    no reason to point anywhere but the open web or an inbox.
    """
    candidate = html.unescape(raw).strip()
    if not candidate or _FORBIDDEN_URL_CHARS.intersection(candidate):
        return None
    if ":" not in candidate:
        return None

    try:
        parts = urlsplit(candidate)
    except ValueError:
        return None

    scheme = parts.scheme.lower()
    if scheme in {"http", "https"} and parts.netloc:
        return html.escape(candidate, quote=True)
    if scheme == "mailto" and candidate.split(":", 1)[1]:
        return html.escape(candidate, quote=True)
    return None


def _emphasis(text: str, tokens: list[str]) -> str:
    """Apply bold then italic, protecting each result with a token.

    Tokens are the reason `***x***` cannot produce crossed `<strong>`/`<em>`
    tags: the bold match is removed from the string before the italic pattern
    runs, so the leftover asterisk has nothing to pair with and stays literal.
    """

    def bold(match: re.Match[str]) -> str:
        inner = _emphasis(match.group(1), tokens)
        return _token(f"<strong>{inner}</strong>", tokens)

    def italic(match: re.Match[str]) -> str:
        inner = _emphasis(match.group(1), tokens)
        return _token(f"<em>{inner}</em>", tokens)

    return _ITALIC_RE.sub(italic, _BOLD_RE.sub(bold, text))


def _inline(text: str) -> str:
    """Render one line's inline syntax. Callers pass an escaped line."""
    tokens: list[str] = []

    def code(match: re.Match[str]) -> str:
        # The content is already escaped; no emphasis or link rule may see it.
        return _token(f"<code>{match.group(1)}</code>", tokens)

    def link(match: re.Match[str]) -> str:
        href = _safe_url(match.group(2))
        if href is None:
            # Not a link we are willing to emit: keep the source visible so the
            # author can see what did not work.
            return match.group(0)
        title = _emphasis(match.group(1), tokens)
        return _token(
            f'<a href="{href}" rel="noopener noreferrer">{title}</a>',
            tokens,
        )

    text = _LINK_RE.sub(link, _CODE_RE.sub(code, text))
    return _restore(_emphasis(text, tokens), tokens)


def _is_block_start(line: str) -> bool:
    """True when the line begins a block rather than continuing a paragraph."""
    if _HEADING_RE.match(line) or _HR_RE.match(line):
        return True
    if _QUOTE_RE.match(line):
        return True
    return bool(_UL_RE.match(line) or _OL_RE.match(line))


def _render_blocks(lines: list[str]) -> str:
    """Render complete lines into block-level HTML."""
    out: list[str] = []
    index = 0
    total = len(lines)

    while index < total:
        line = lines[index].rstrip()

        if not line.strip():
            index += 1
            continue

        heading = _HEADING_RE.match(line)
        if heading:
            level = len(heading.group(1))
            tag = f"h{level + 2}"
            out.append(f"<{tag}>{_inline(heading.group(2))}</{tag}>")
            index += 1
            continue

        if _HR_RE.match(line):
            out.append("<hr>")
            index += 1
            continue

        if _QUOTE_RE.match(line):
            quoted: list[str] = []
            while index < total:
                match = _QUOTE_RE.match(lines[index].rstrip())
                if not match:
                    break
                quoted.append(match.group(1))
                index += 1
            inner = _render_blocks(quoted)
            if inner:
                out.append(f"<blockquote>{inner}</blockquote>")
            continue

        unordered = _UL_RE.match(line)
        if unordered:
            items: list[str] = []
            while index < total:
                match = _UL_RE.match(lines[index].rstrip())
                if not match:
                    break
                items.append(f"<li>{_inline(match.group(1))}</li>")
                index += 1
            out.append("<ul>" + "".join(items) + "</ul>")
            continue

        ordered = _OL_RE.match(line)
        if ordered:
            items = []
            while index < total:
                match = _OL_RE.match(lines[index].rstrip())
                if not match:
                    break
                items.append(f"<li>{_inline(match.group(2))}</li>")
                index += 1
            out.append("<ol>" + "".join(items) + "</ol>")
            continue

        paragraph: list[str] = []
        while index < total:
            current = lines[index].rstrip()
            if not current.strip() or _is_block_start(current):
                break
            paragraph.append(_inline(current))
            index += 1
        # A single newline is a soft break and renders as `<br>`, matching the
        # `whitespace-pre-line` plain-text pages this renderer replaces.
        out.append("<p>" + "<br>\n".join(paragraph) + "</p>")

    return "\n".join(out)


def render_markdown(text: str | None) -> str:
    """Render the `design.md` 7.22 subset. Escapes first; returns safe HTML.

    Empty or whitespace-only input returns an empty string so callers can render
    their own "not written yet" state instead of an empty paragraph.
    """
    if not text or not text.strip():
        return ""

    # NUL is the token delimiter and cannot be stored in PostgreSQL TEXT anyway;
    # stripping it keeps a hand-crafted value from forging a placeholder.
    escaped = html.escape(text.replace("\x00", ""), quote=True)
    return _render_blocks(escaped.split("\n"))
