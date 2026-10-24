"""The evidence-cited rationale contract, and the validator that enforces it.

`REQ-FR-030` is the product's differentiating claim: every rationale names the
resume text behind each assertion. That claim is only true if something rejects a
rationale that does not. This module is that something. `Arch Doc §7.5` records
the contract it enforces; `Complete Doc §C.4` records where the payload is stored.

Why this module imports no Django
---------------------------------

The same reason `ai.bias_pass` and `ai.bias_audit` do: the citation check is the
single highest-risk file in the product (`RSK-002`, Arch Doc §8), so it must be
runnable in CI, in a Celery worker and from a management command without a
database. A validator that needs a database is a validator that gets skipped in
the one environment where it matters.

What "evidence" means here
--------------------------

An evidence span is a **verbatim substring of the sanitised resume text**, compared
after collapsing runs of whitespace and case-folding. Not character offsets: the
text is re-stripped and re-wrapped between storage and reading, so an offset
recorded today points at the wrong characters tomorrow. Not fuzzy matching either:
near-miss matching is how a paraphrase passes as a quote, which is exactly the
hallucination (`RSK-002`) this file exists to stop.

The three checks that do the work
---------------------------------

1. **Every claim's evidence occurs in the text** (after normalisation). Invented
   evidence fails here.
2. **A span shorter than `MIN_EVIDENCE_CHARS` is rejected.** `"the"` is a
   substring of every resume; without a floor, fabricated evidence can pass by
   citing a stop word.
3. **A "missing" skill must not occur in the text as a whole word.** `Rust` is
   missing from a resume that says "trusted by"; it is not missing from one that
   says "Rust". Whole-word matching is what keeps `C++` and `.NET` usable.

A validation failure raises `CitationError` carrying *every* problem, not the
first: a generator told one thing at a time burns a provider call per round trip.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Mapping

#: Shortest span that can count as evidence, after normalisation.
#:
#: Twelve characters is roughly two short words. Below that a span is either a
#: stop word (`"the"`) or a token that occurs in almost every resume (`"Python"`),
#: and neither demonstrates the claim it is attached to.
MIN_EVIDENCE_CHARS = 12

#: Characters treated as word characters beyond `\w` for the "missing skill"
#: check, so `C++`, `C#` and `.NET` match as whole skills rather than as
#: substrings of `"C"`, `"C"` and `"NET"`.
_EXTRA_WORD_CHARS = "+#."

_TOP_LEVEL_KEYS = ("summary", "claims", "missing_skills")
_CLAIM_KEYS = ("claim", "evidence", "skills")
_MISSING_KEYS = ("skill", "reason")


class CitationError(ValueError):
    """A rationale that asserts something the resume text does not support.

    `problems` holds every failure found in one pass, so the caller can log the
    whole list and the generator can be re-prompted once rather than once per
    defect. The message is assembled from the same list and contains no resume
    text: this exception reaches logs, and logs do not hold candidate data.
    """

    def __init__(self, problems: list[str]) -> None:
        self.problems = list(problems)
        super().__init__("; ".join(self.problems))


def normalise(text: str) -> str:
    """Collapse whitespace and case-fold, for comparison only.

    Deliberately nowhere near the stored value: the rationale keeps the model's
    casing, and the resume keeps its own line breaks. This is the form the two
    are compared in, nothing else.
    """
    return " ".join(str(text).split()).casefold()


@dataclass(frozen=True)
class Claim:
    """One matched-skill assertion and the resume text that supports it."""

    claim: str
    evidence: str
    skills: tuple[str, ...]


@dataclass(frozen=True)
class MissingSkill:
    """A skill the resume does not evidence, and why it is listed as missing."""

    skill: str
    reason: str = ""


@dataclass(frozen=True)
class Rationale:
    """A validated rationale: the only shape the product stores or displays.

    **Serialised as JSON text into `applications.match_rationale`.** The DDL has
    one `TEXT` column, and page #41 needs claim-level structure to render an
    evidence highlight per claim. Adding a second JSONB column would duplicate
    the same payload and let the two copies drift. `to_text()` is what the bias
    pass scans and what `rationale_hash` hashes, so the audit re-derives the same
    value the reader sees.
    """

    summary: str
    claims: tuple[Claim, ...] = field(default_factory=tuple)
    missing_skills: tuple[MissingSkill, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        """The stored payload. Key order is stable so a diff of two rationales is
        readable."""
        return {
            "summary": self.summary,
            "claims": [
                {
                    "claim": claim.claim,
                    "evidence": claim.evidence,
                    "skills": list(claim.skills),
                }
                for claim in self.claims
            ],
            "missing_skills": [
                {"skill": missing.skill, "reason": missing.reason}
                for missing in self.missing_skills
            ],
        }

    def to_json(self) -> str:
        """The value written to `Application.match_rationale`."""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    def to_text(self) -> str:
        """A plain-text rendering, used by the bias pass and the audit hash.

        The bias audit scans prose, so it is handed prose rather than JSON: JSON
        keys (`"skills"`, `"claim"`) would be scanned as if they were rationale
        wording, and the pass would report terms from the schema rather than from
        the argument.
        """
        lines = [f"Summary: {self.summary}"]
        for claim_ in self.claims:
            skills = ", ".join(claim_.skills)
            lines.append(
                f'- {claim_.claim} (skills: {skills}) Evidence: "{claim_.evidence}"'
            )
        if self.missing_skills:
            missing = "; ".join(
                f"{item.skill} — {item.reason}" if item.reason else item.skill
                for item in self.missing_skills
            )
            lines.append(f"Missing skills: {missing}")
        return "\n".join(lines)


def _contains_whole_word(haystack_normalised: str, needle_normalised: str) -> bool:
    """Whether `needle` occurs in `haystack` as a whole skill name.

    Both arguments must already be normalised. The lookarounds treat `+`, `#` and
    `.` as part of a skill name, so `C++` does not match inside `C++Builder` and
    `Rust` does not match inside `trusted`.
    """
    pattern = (
        r"(?<![\w"
        + re.escape(_EXTRA_WORD_CHARS)
        + r"])"
        + re.escape(needle_normalised)
        + r"(?![\w"
        + re.escape(_EXTRA_WORD_CHARS)
        + r"])"
    )
    return re.search(pattern, haystack_normalised) is not None


def _coerce(payload: Mapping[str, Any], problems: list[str]) -> Rationale | None:
    """Structural validation. Returns `None` when the shape is unusable.

    Structural failures are separated from citation failures because they mean
    different things: a missing `claims` key is a broken generator, while a claim
    whose evidence is not in the resume is a hallucination. Both are refused, but
    a reader of the log should be able to tell them apart.
    """
    if not isinstance(payload, Mapping):
        problems.append("the rationale payload must be an object")
        return None

    extra = sorted(set(payload) - set(_TOP_LEVEL_KEYS))
    if extra:
        problems.append(f"unknown top-level keys: {', '.join(extra)}")
    missing_keys = [key for key in _TOP_LEVEL_KEYS if key not in payload]
    if missing_keys:
        problems.append(f"missing top-level keys: {', '.join(missing_keys)}")
    if extra or missing_keys:
        return None

    summary = payload["summary"]
    if not isinstance(summary, str) or not summary.strip():
        problems.append("summary must be a non-empty string")

    raw_claims = payload["claims"]
    claims: list[Claim] = []
    if not isinstance(raw_claims, list) or not raw_claims:
        problems.append("claims must be a non-empty list")
    else:
        for index, raw_claim in enumerate(raw_claims):
            label = f"claim {index + 1}"
            if not isinstance(raw_claim, Mapping):
                problems.append(f"{label} must be an object")
                continue

            extra_keys = sorted(set(raw_claim) - set(_CLAIM_KEYS))
            if extra_keys:
                problems.append(f"{label} has unknown keys: {', '.join(extra_keys)}")
            absent_keys = [key for key in _CLAIM_KEYS if key not in raw_claim]
            if absent_keys:
                problems.append(f"{label} is missing: {', '.join(absent_keys)}")
                continue

            claim_text = raw_claim["claim"]
            if not isinstance(claim_text, str) or not claim_text.strip():
                problems.append(f"{label} claim must be a non-empty string")
                claim_text = ""

            evidence = raw_claim["evidence"]
            if not isinstance(evidence, str) or not evidence.strip():
                problems.append(f"{label} evidence must be a non-empty string")
                evidence = ""

            raw_skills = raw_claim["skills"]
            skills: list[str] = []
            if not isinstance(raw_skills, list) or not raw_skills:
                problems.append(f"{label} skills must be a non-empty list")
            else:
                for raw_skill in raw_skills:
                    if not isinstance(raw_skill, str) or not raw_skill.strip():
                        problems.append(f"{label} has an empty skill name")
                        continue
                    skills.append(raw_skill.strip())

            claims.append(
                Claim(
                    claim=claim_text.strip(),
                    evidence=evidence.strip(),
                    skills=tuple(skills),
                )
            )

    raw_missing = payload["missing_skills"]
    missing: list[MissingSkill] = []
    if not isinstance(raw_missing, list):
        problems.append("missing_skills must be a list")
    else:
        for index, raw_item in enumerate(raw_missing):
            label = f"missing skill {index + 1}"
            if not isinstance(raw_item, Mapping):
                problems.append(f"{label} must be an object")
                continue

            extra_keys = sorted(set(raw_item) - set(_MISSING_KEYS))
            if extra_keys:
                problems.append(f"{label} has unknown keys: {', '.join(extra_keys)}")
            if "skill" not in raw_item:
                problems.append(f"{label} is missing: skill")
                continue

            skill = raw_item["skill"]
            if not isinstance(skill, str) or not skill.strip():
                problems.append(f"{label} skill must be a non-empty string")
                continue

            reason = raw_item.get("reason", "")
            if not isinstance(reason, str):
                problems.append(f"{label} reason must be a string")
                reason = ""

            missing.append(MissingSkill(skill=skill.strip(), reason=reason.strip()))

    return Rationale(
        summary=summary.strip() if isinstance(summary, str) else "",
        claims=tuple(claims),
        missing_skills=tuple(missing),
    )


def parse_rationale(
    payload: Mapping[str, Any] | str,
    *,
    source_text: str,
) -> Rationale:
    """Validate `payload` against the sanitised resume text and return it.

    `source_text` is the **sanitised** text stored on the resume, never the raw
    upload: a citation that quotes a stripped name would prove the model saw PII
    it was never sent (`REQ-FR-030`).

    Raises:
        CitationError: with every problem found, if the payload is malformed or
            any claim is unsupported by the text.
    """
    problems: list[str] = []

    if isinstance(source_text, str) and not source_text.strip():
        problems.append(
            "no sanitised resume text to check citations against; refusing to "
            "validate a rationale that cannot be evidenced"
        )
        raise CitationError(problems)

    data: Any = payload
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except ValueError:
            raise CitationError(["the rationale payload is not valid JSON"]) from None

    rationale = _coerce(data, problems)

    if rationale is not None and not problems:
        normalised_source = normalise(source_text)
        for index, claim_ in enumerate(rationale.claims, start=1):
            evidence = normalise(claim_.evidence)
            if len(evidence) < MIN_EVIDENCE_CHARS:
                problems.append(
                    f"claim {index} evidence is shorter than "
                    f"{MIN_EVIDENCE_CHARS} characters, which cannot demonstrate "
                    f"a claim"
                )
            elif evidence not in normalised_source:
                problems.append(
                    f"claim {index} cites evidence that does not occur in the "
                    f"sanitised resume text"
                )

        for index, missing in enumerate(rationale.missing_skills, start=1):
            if _contains_whole_word(normalised_source, normalise(missing.skill)):
                problems.append(
                    f"missing skill {index} lists {missing.skill!r} as missing, "
                    f"but the resume text contains it"
                )

    if problems:
        raise CitationError(problems)
    assert rationale is not None  # _coerce returns None only with a problem
    return rationale


def load_rationale(stored: str) -> Rationale:
    """Rebuild a stored payload from `applications.match_rationale`.

    Structural checks only: the source text is not available at read time, and
    re-verifying citations on every page render would make a stored rationale
    disappear the day the resume is re-processed. Validation happens once, when
    the rationale is generated; this function only refuses to hand the caller a
    malformed object.
    """
    try:
        payload = json.loads(stored)
    except (TypeError, ValueError):
        raise CitationError(["stored match_rationale is not valid JSON"]) from None

    problems: list[str] = []
    rationale = _coerce(payload, problems)
    if problems or rationale is None:
        raise CitationError(problems or ["stored match_rationale is malformed"])
    return rationale
