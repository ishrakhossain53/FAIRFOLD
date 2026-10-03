"""Deterministic keyword bias pass.

The pass answers one question about a piece of text: does it contain any phrase
from the reviewed term list? It is deliberately small and deliberately literal.

Design constraints, each of which was decided against an alternative:

* **The term list is data, not code.** Terms are read from
  ``tests/bias/<version>/keyword_terms.json`` rather than hard-coded here,
  because the test set's manifest records a SHA of that file. Terms in Python
  would make that SHA meaningless and the test set unverifiable.
* **No single-word terms.** See ``GAP-001`` in the term list. ``energetic`` and
  ``mature`` are ordinary professional adjectives; substring-matching them
  would flag ordinary CVs, and a bias pass that cries wolf gets ignored.
* **Plain substring matching, no regex, no stemming.** Regexes would make
  matching depend on the input's punctuation. Every cost of that lands on the
  candidate, whose text the pipeline has no chance to normalise before this
  runs.
* **Apostrophes are folded.** Bangladeshi resumes mix ASCII, U+2019 and U+02BC.
  Without folding, ``women's`` silently misses ``women’s`` and the pass reports
  clean on exactly the phrasing it was written to catch.

What this module does NOT do, and must not grow to do without a version bump:

* It does not judge. A match is a *flag for human review*, not a finding.
* It does not measure bias in outcomes. The 76-case set cannot support a
  disparity claim (see the manifest's ``does_not_support``).
* It does not handle Bengali. See ``LIM-003`` in the term list.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SET_ROOT = REPO_ROOT / "tests" / "bias"

# Typographic apostrophes that appear in real resumes and that must match the
# ASCII form the term list is written in.
_APOSTROPHES = {
    "’": "'",  # right single quotation mark
    "ʼ": "'",  # modifier letter apostrophe
    "‘": "'",  # left single quotation mark
}


def normalise(text: str) -> str:
    """Fold case and apostrophe variants so matching is punctuation-independent.

    A candidate cannot be flagged or cleared by which apostrophe their word
    processor produced, so this is a correctness requirement rather than a
    tidy-up.
    """
    lowered = text.lower()
    for exotic, plain in _APOSTROPHES.items():
        lowered = lowered.replace(exotic, plain)
    return lowered


@dataclass(frozen=True)
class Term:
    """One reviewed phrase and the category it belongs to."""

    phrase: str
    group: str


@dataclass(frozen=True)
class Match:
    term: Term
    #: Character offset of the match in the *normalised* text, for logging an
    #: employer-facing explanation without re-searching.
    start: int


@dataclass
class ScanResult:
    """Outcome of scanning one piece of text."""

    text: str
    matches: list[Match] = field(default_factory=list)

    @property
    def flagged(self) -> bool:
        return bool(self.matches)

    @property
    def groups(self) -> set[str]:
        """Distinct term categories hit. A line can hit several at once."""
        return {m.term.group for m in self.matches}

    @property
    def phrases(self) -> list[str]:
        """Matched phrases, in the order they appear in the text."""
        return [m.term.phrase for m in sorted(self.matches, key=lambda m: m.start)]

    def explain(self) -> str:
        """Human-readable reason, for the audit trail and the employer badge.

        Names the phrases rather than a category label alone, because the whole
        product claim is that a decision never asserts something it cannot
        evidence. A flag with no quotable phrase is exactly that failure.
        """
        if not self.matches:
            return "no phrase from the reviewed term list was present"
        groups = ", ".join(sorted(self.groups))
        return f"phrases from the reviewed term list ({groups}): " + "; ".join(
            f'"{p}"' for p in self.phrases
        )


def load_terms(set_dir: Path | str | None = None) -> list[Term]:
    """Read the reviewed term list.

    Args:
        set_dir: directory holding ``keyword_terms.json``. Defaults to the
            committed set's latest version.

    Raises:
        FileNotFoundError: if the directory holds no term list. Raised rather
            than returning an empty list, because a pass with no terms flags
            nothing and reports a clean result -- the worst possible failure
            mode, and one that looks exactly like success.
    """
    directory = Path(set_dir) if set_dir else _latest_set_dir()
    path = directory / "keyword_terms.json"
    if not path.exists():
        raise FileNotFoundError(
            f"no keyword_terms.json in {directory}. A bias pass with no terms "
            f"flags nothing and reports success, so this must fail loudly."
        )
    document = json.loads(path.read_text(encoding="utf-8"))
    return [
        Term(phrase=phrase, group=group)
        for group, phrases in document["terms"].items()
        for phrase in phrases
    ]


def _latest_set_dir() -> Path:
    versions = sorted(
        (p for p in SET_ROOT.glob("v*") if (p / "keyword_terms.json").exists()),
        key=lambda p: [int(part) for part in p.name.lstrip("v").split(".")],
    )
    if not versions:
        raise FileNotFoundError(f"no versioned bias test set under {SET_ROOT}")
    return versions[-1]


def scan(text: str, terms: list[Term]) -> ScanResult:
    """Return every reviewed phrase present in ``text``.

    Terms are sorted longest-first so that overlapping phrases report the more
    specific one: ``women's society`` wins over a hypothetical ``women's``.
    """
    haystack = normalise(text)
    matches: list[Match] = []
    for term in sorted(terms, key=lambda t: len(t.phrase), reverse=True):
        needle = normalise(term.phrase)
        at = haystack.find(needle)
        if at != -1:
            matches.append(Match(term=term, start=at))
    return ScanResult(text=text, matches=sorted(matches, key=lambda m: m.start))


def scan_text(text: str, set_dir: Path | str | None = None) -> ScanResult:
    """Convenience wrapper for one-off callers that do not hold the term list."""
    return scan(text, load_terms(set_dir))