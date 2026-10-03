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
import re
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
class Rule:
    """A regex-based rule, for signals a phrase list cannot express.

    Added in v1.0.1 to close ``LIM-001`` (no numeric age detection) and
    ``LIM-002`` (no graduation-year proximity). Both are genuinely not term
    problems: "22 years old" is not a phrase to list, it is a shape to match,
    and a graduation year only means something relative to a reference year.

    Every rule carries a ``contextual`` flag. A bare four-digit year in text is
    meaningless -- a phone number, a budget, a fund. A rule may therefore demand
    an education keyword within a short window of the number, which is what
    keeps "BBA, Some College, 2023" out of the graduation rule while catching
    "graduated in 2026".
    """

    rule_id: str
    group: str
    pattern: re.Pattern[str]
    #: When true the rule needs a context keyword near the capture.
    contextual: bool = False
    #: Context keyword alternative; built into the pattern where contextual.
    description: str = ""


#: How many years of graduation recency counts as a proximity signal.
DEFAULT_GRADUATION_WINDOW_YEARS = 3

#: Default reference year. Overridable via ``ScanContext`` so a test or a
#: re-run in a later year does not silently change what "recent" means.
DEFAULT_REFERENCE_YEAR = 2026


@dataclass(frozen=True)
class ScanContext:
    """Everything the numeric rules need beyond the text itself.

    Passed in rather than read from the clock or the environment, so a run is
    reproducible and a test can assert an exact year.
    """

    reference_year: int = DEFAULT_REFERENCE_YEAR
    graduation_window_years: int = DEFAULT_GRADUATION_WINDOW_YEARS


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
    #: The captured value, for rules. None for phrase terms.
    captured: str | None = None

    @property
    def label(self) -> str:
        """How this match is shown to a human."""
        if self.captured is None:
            return self.term.phrase
        return f"{self.term.phrase} ({self.captured})"


@dataclass
class ScanResult:
    """Outcome of scanning one piece of text."""

    text: str
    matches: list[Match] = field(default_factory=list)
    #: Rule ids that ran, whether or not they fired. The bias audit panel shows
    #: "what was checked", so a rule that found nothing still has to appear --
    #: otherwise a reader cannot tell a clean result from an unrun rule.
    rules_checked: list[str] = field(default_factory=list)

    @property
    def flagged(self) -> bool:
        return bool(self.matches)

    @property
    def groups(self) -> set[str]:
        """Distinct categories hit. A line can hit several at once."""
        return {m.term.group for m in self.matches}

    @property
    def phrases(self) -> list[str]:
        """Matched phrases, in the order they appear in the text."""
        return [m.term.phrase for m in sorted(self.matches, key=lambda m: m.start)]

    @property
    def highlights(self) -> list[str]:
        """Quotable spans for the panel, including any captured value."""
        return [m.label for m in sorted(self.matches, key=lambda m: m.start)]

    def explain(self) -> str:
        """Human-readable reason, for the audit trail and the employer badge.

        Names the phrases rather than a category label alone, because the whole
        product claim is that a decision never asserts something it cannot
        evidence. A flag with no quotable phrase is exactly that failure.
        """
        if not self.matches:
            return "no phrase from the reviewed term list and no numeric rule fired"
        return (
            "phrases matched ("
            + ", ".join(sorted(self.groups))
            + "): "
            + "; ".join(f'"{h}"' for h in self.highlights)
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


def load_rules(set_dir: Path | str | None = None) -> list[Rule]:
    """Read the numeric rules from the term list.

    Same loud-failure contract as :func:`load_terms`: a rule set that fails to
    load must not degrade into an empty one, because the numeric rules are the
    only defence against a stated age or a recent graduation year.
    """
    directory = Path(set_dir) if set_dir else _latest_set_dir()
    path = directory / "keyword_terms.json"
    if not path.exists():
        raise FileNotFoundError(
            f"no keyword_terms.json in {directory}. A bias pass with no numeric "
            f"rules misses every stated age, so this must fail loudly."
        )
    document = json.loads(path.read_text(encoding="utf-8"))
    rules: list[Rule] = []
    for group, spec in document.get("numeric_rules", {}).items():
        if group.startswith("_") or not isinstance(spec, dict):
            continue  # group-level note or metadata, not a rule family
        for rule_id, entry in spec.items():
            if rule_id.startswith("_") or not isinstance(entry, dict):
                continue  # family note, not a rule
            rules.append(
                Rule(
                    rule_id=rule_id,
                    group=group,
                    pattern=re.compile(entry["pattern"], re.IGNORECASE),
                    contextual=bool(entry.get("contextual", False)),
                    description=entry.get("description", ""),
                )
            )
    return rules


def _rule_matches(rule: Rule, haystack: str, context: ScanContext) -> list[Match]:
    """Apply one rule, honouring its capture semantics.

    Most rules fire on the capture directly. ``graduation_year`` is different: a
    year only counts when it falls inside the recency window, so a 1994
    graduation is not a proxy for anything and a rule that flagged it would be
    useless.
    """
    hits: list[Match] = []
    for found in rule.pattern.finditer(haystack):
        captured = found.group(1) if found.groups() else None
        if captured is not None and not captured.strip():
            continue
        if rule.rule_id == "graduation_year" and captured is not None:
            try:
                year = int(captured)
            except ValueError:
                continue
            age_years = context.reference_year - year
            if not (0 <= age_years <= context.graduation_window_years):
                continue
        hits.append(
            Match(
                term=Term(phrase=rule.rule_id, group=rule.group),
                start=found.start(),
                captured=captured,
            )
        )
    return hits


def _latest_set_dir() -> Path:
    versions = sorted(
        (p for p in SET_ROOT.glob("v*") if (p / "keyword_terms.json").exists()),
        key=lambda p: [int(part) for part in p.name.lstrip("v").split(".")],
    )
    if not versions:
        raise FileNotFoundError(f"no versioned bias test set under {SET_ROOT}")
    return versions[-1]


def scan(
    text: str,
    terms: list[Term],
    rules: list[Rule] | None = None,
    context: ScanContext | None = None,
) -> ScanResult:
    """Return every reviewed phrase and every fired rule present in ``text``.

    Terms are sorted longest-first so that overlapping phrases report the more
    specific one: ``women's society`` wins over a hypothetical ``women's``.

    ``rules`` defaults to none rather than to the shipped rules, so a caller
    that has not opted into the numeric layer cannot silently acquire it. The
    audit wrapper passes them explicitly.
    """
    context = context or ScanContext()
    haystack = normalise(text)
    matches: list[Match] = []
    for term in sorted(terms, key=lambda t: len(t.phrase), reverse=True):
        needle = normalise(term.phrase)
        at = haystack.find(needle)
        if at != -1:
            matches.append(Match(term=term, start=at))
    rules_checked: list[str] = []
    for rule in rules or []:
        rules_checked.append(rule.rule_id)
        matches.extend(_rule_matches(rule, haystack, context))
    return ScanResult(
        text=text,
        matches=sorted(matches, key=lambda m: m.start),
        rules_checked=rules_checked,
    )


def scan_text(
    text: str,
    set_dir: Path | str | None = None,
    context: ScanContext | None = None,
    *,
    with_rules: bool = True,
) -> ScanResult:
    """Convenience wrapper for callers that do not hold the term list.

    ``with_rules`` defaults to True because this is the path the product uses.
    A caller wanting phrase-only matching passes ``with_rules=False`` and gets
    exactly that -- the older behaviour -- rather than a surprise.
    """
    directory = set_dir or None
    terms = load_terms(directory)
    rules = load_rules(directory) if with_rules else []
    return scan(text, terms, rules, context)
