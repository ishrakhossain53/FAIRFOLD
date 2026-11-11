"""Deterministic and NER/proxy PII redaction pipeline (REQ-FR-011, REQ-FR-057, AD-005).

The pipeline strips personal identifiers and demographic proxies before resume
text is stored in ``candidate_resumes.extracted_text``, embedded, or sent to any
external AI provider. No employer opt-out exists in the MVP (REQ-FR-057).

Two layers run in sequence:

1. **Deterministic redaction (batch 2.7)** — regex patterns for email addresses,
   phone numbers (Bangladeshi ``+880``/``01[3-9]`` and international formats),
   URLs and profile links, national ID / passport numbers, dates of birth,
   structured postal addresses, and the candidate's own profile name and
   location (known-PII).
2. **NER and proxy stripping (batch 2.8)** — photo references, explicit ages,
   age-revealing graduation/cohort years and date ranges (converted to
   durations alongside ``[DATE]``), institution names, employer names, and
   spaCy ``en_core_web_sm`` NER for ``PERSON``, ``ORG``, ``GPE`` and ``LOC``
   guarded by a keep-set vocabulary of skills, degree fields and role titles so
   professional qualifications survive intact.

Every replacement uses a typed placeholder from ``REQ-FR-057`` and Arch Doc
Flow 3 (``[CANDIDATE_NAME]``, ``[CANDIDATE_EMAIL]``, ``[CANDIDATE_PHONE]``,
``[CANDIDATE_LOCATION]``, ``[NATIONAL_ID]``, ``[URL]``, ``[DATE]``,
``[INSTITUTION]``, ``[EMPLOYER]``, ``[PHOTO]``) and increments the per-category
counter so batch 2.9 can write an ``AuditLogEntry`` with category counts and
zero raw PII.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PLACEHOLDERS: dict[str, str] = {
    "name": "[CANDIDATE_NAME]",
    "email": "[CANDIDATE_EMAIL]",
    "phone": "[CANDIDATE_PHONE]",
    "address": "[CANDIDATE_LOCATION]",
    "national_id": "[NATIONAL_ID]",
    "url": "[URL]",
    "age_date": "[DATE]",
    "institution": "[INSTITUTION]",
    "employer": "[EMPLOYER]",
    "photo": "[PHOTO]",
}

ALL_CATEGORIES: tuple[str, ...] = tuple(PLACEHOLDERS.keys())

DEFAULT_REFERENCE_YEAR = 2026

# ---------------------------------------------------------------------------
# Layer 1: Deterministic regexes (batch 2.7)
# ---------------------------------------------------------------------------

# 1. Email addresses (run before URLs so domain suffixes are not misread).
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

# 2. URLs: explicit http(s)://, www., or bare linkedin.com / github.com links.
# Excludes markdown image targets (`![...](...)`) via negative lookbehind so
# photo syntax is left intact for the photo rule in batch 2.8.
_URL_RE = re.compile(
    r"(?<!\]\()(?:\b(?:https?://|www\.)[^\s,;)\]>]+|\b(?:linkedin\.com/in/|github\.com/)[A-Za-z0-9._/-]+)",
    re.IGNORECASE,
)

# 3. Phone numbers: Bangladeshi (+880 1X..., 01X...) and international (+1, +44).
_BD_PHONE_RE = re.compile(r"(?:\+?880[\s.-]?|(?<!\d)0)1[3-9]\d{2}[\s.-]?\d{6}\b")
_INTL_PHONE_RE = re.compile(r"\+(?:1|44)(?:[\s.-]?\d{2,4}){2,4}\b")

# 4. National IDs (10/13/17-digit NID, Smart NID) and Passport numbers.
_LABELLED_NID_RE = re.compile(
    r"\b(?:(?:smart\s+)?n\.?i\.?d\.?(?:\s+no\.?)?|national\s+id(?:\s+no\.?)?|passport(?:\s+no\.?)?)"
    r"\s*[:#.-]?\s*(?:[A-Z]{1,2}\d{7,9}|\d{10}|\d{13}|\d{17})\b",
    re.IGNORECASE,
)
_BARE_NID_RE = re.compile(r"(?<![+\d])\b(?:\d{13}|\d{17})\b")

# 5. Deterministic dates of birth (DOB / Date of Birth / Born on).
_DOB_RE = re.compile(
    r"\b(?:d\.?\s?o\.?\s?b\.?|date\s+of\s+birth|born(?:\s+on)?)\s*[:#.-]?\s*"
    r"(?:\d{1,2}[/\-.]\d{1,2}[/\-.](?:19|20)\d{2}"
    r"|(?:19|20)\d{2}[/\-.]\d{1,2}[/\-.]\d{1,2}"
    r"|\d{1,2}\s+[A-Za-z]{3,9}\s+(?:19|20)\d{2})\b",
    re.IGNORECASE,
)

# 6. Structured street/postal addresses ending in a 4-digit postal code (e.g. Dhaka-1209).
_POSTAL_ADDRESS_RE = re.compile(
    r"\b(?:(?:House|Flat|Plot|Holding|Apartment|Road)\s+[A-Za-z0-9/#-]+"
    r"(?:,\s*[A-Za-z0-9\s/.-]+)*,\s*[A-Za-z]+[-\s]\d{4}"
    r"|\d+\s+[A-Za-z0-9\s/.-]+,\s*[A-Za-z]+[-\s]\d{4})\b",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Layer 2: Proxy & NER patterns (batch 2.8)
# ---------------------------------------------------------------------------

# Photo references: markdown image syntax, bracketed photo placeholders, or
# "Photo: filename" / "Profile photo attached" / "Photograph: attached...".
_PHOTO_RE = re.compile(
    r"!\[[^\]]*\]\([^)]+\)"
    r"|\[[^\]]*\b(?:photo|photograph|headshot|portrait|avatar)\b[^\]]*\]"
    r"|\b(?:profile\s+)?(?:photo|photograph)\s*(?::\s*[^\n|,;]+|attached(?:\s+with\s+application)?)",
    re.IGNORECASE,
)

# Explicit stated age ("26 years old", "25 yrs old", "Age: 28", "Aged 29").
_STATED_AGE_RE = re.compile(
    r"\b(?:\d{2}\s*(?:years?\s*old|yrs?\s*old|yo\b)|(?:age|aged)\s*:?\s*\d{2})\b",
    re.IGNORECASE,
)

# Graduation, cohort or secondary exam completion years ("Graduated in 2019",
# "Class of 2020", "Cohort of 2021", "Passed HSC in 2016"). Converted to a
# `[DATE]` placeholder plus a relative duration so experience context survives
# without the age-revealing calendar year.
_GRADUATION_YEAR_RE = re.compile(
    r"\b(?:graduated(?:\s+in)?|class\s+of|cohort\s+of|"
    r"(?:passed|completed)\s+(?:hsc|ssc|o[-\s]?level|a[-\s]?level)(?:\s+in)?)"
    r"\s+((?:19|20)\d{2})\b",
    re.IGNORECASE,
)

# Calendar year ranges ("2019 - 2023", "2020–2024") converted to `[DATE] (N years)`.
_YEAR_RANGE_RE = re.compile(r"\b((?:19|20)\d{2})\s*[-–—]\s*((?:19|20)\d{2})\b")

# Educational institutions: universities, colleges, schools, institutes of
# technology, and well-known Bangladeshi university acronyms.
_INSTITUTION_RE = re.compile(
    r"\b(?:"
    r"University\s+of\s+[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*"
    r"|(?:[A-Z][A-Za-z'.-]+(?:\s+(?:of|and|for|the|[A-Z][A-Za-z'.-]+))*)\s+"
    r"(?:University(?:\s+of\s+[A-Z][A-Za-z]+(?:\s+(?:and|of)\s+[A-Z][A-Za-z]+)*)?(?:\s*,\s*Bangladesh|-Bangladesh)?"
    r"|Institute\s+of\s+[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*"
    r"|School\s+and\s+College"
    r"|Girls'\s+(?:College|High\s+School|School|University)"
    r"|Women's\s+(?:College|University)"
    r"|Medical\s+College"
    r"| Cadet\s+College"
    r"|College)"
    r"|\b(?:BUET|CUET|RUET|KUET|SUST|IUT|NSU|AIUB|UIU|DIU|EWU|IUB|AUST|BUP|MIST)\b"
    r")"
)

# Corporate employer names carrying a legal-entity suffix (Limited, Ltd., PLC, Inc., Corp., LLC).
# Supports camelCase brand prefixes such as "bKash Limited".
_ORG_TOKEN = r"(?:[A-Z][A-Za-z0-9&'.-]*|[a-z][A-Z][A-Za-z0-9&'.-]*)"
_CORPORATE_EMPLOYER_RE = re.compile(
    rf"\b{_ORG_TOKEN}(?:\s+(?:{_ORG_TOKEN}|\([A-Z]{{2,5}}\)|\d+)){{0,5}}\s+"
    r"(?:Limited|Ltd\.?|PLC|Inc\.?|Corp\.?|LLC)(?!\w)"
)

# Contextual employer names after "at" in Experience/Employment clauses when the
# company name has no legal suffix (e.g. "at Selise Digital Platforms",
# "at Enosis Solutions", "at Dynamic Solution Innovators", "at Optimizely Bangladesh").
_CONTEXTUAL_EMPLOYER_RE = re.compile(
    rf"(?<=\bat\s)({_ORG_TOKEN}(?:\s+{_ORG_TOKEN}){{1,4}})"
)

# Referee / Reference person lines ("Reference: Dr. Mahmudul Hasan", "Referee: Mr. Rezaul Karim").
_REFEREE_PERSON_RE = re.compile(
    r"\b((?:Reference|Referee)\s*:\s*)(?:(?:Dr|Mr|Ms|Mrs|Prof)\.?\s+)?"
    r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})"
)

# Lazy-loaded spaCy model and protected keep-set vocabulary.
_NLP: Any | None = None
_PROTECTED_TERMS: frozenset[str] | None = None

_BASE_PROTECTED_TERMS = {
    # Technical skills, frameworks, tools
    "python",
    "django",
    "django rest framework",
    "drf",
    "fastapi",
    "flask",
    "postgresql",
    "postgres",
    "mysql",
    "mongodb",
    "sqlite",
    "sql",
    "redis",
    "celery",
    "docker",
    "kubernetes",
    "terraform",
    "linux",
    "nginx",
    "typescript",
    "javascript",
    "react",
    "next.js",
    "vue.js",
    "angular",
    "svelte",
    "tailwindcss",
    "tailwind css",
    "htmx",
    "html",
    "css",
    "pytorch",
    "spacy",
    "pandas",
    "numpy",
    "pgvector",
    "pytest",
    "selenium",
    "apache airflow",
    "prometheus",
    "git",
    "rest apis",
    "rest api",
    "ci/cd",
    "etl",
    "etl pipelines",
    "nlp",
    "machine learning",
    "deep learning",
    "data science",
    "microservices",
    # Degree levels and academic fields
    "b.sc.",
    "b.sc",
    "m.sc.",
    "m.sc",
    "bba",
    "mba",
    "b.a.",
    "m.a.",
    "ph.d.",
    "computer science",
    "computer science and engineering",
    "software engineering",
    "electrical and electronic engineering",
    "industrial and production engineering",
    "electrical",
    "electronic",
    "industrial",
    "production",
    "computer",
    "science",
    "engineering",
    "finance",
    "financial",
    "data engineering",
    # Common role words
    "engineer",
    "developer",
    "scientist",
    "analyst",
    "architect",
    "manager",
    "director",
    "professor",
    "senior",
    "lead",
    "backend",
    "frontend",
    "full-stack",
    "software",
    "systems",
    "automation",
    "devops",
    "platform",
    "security",
    "quality assurance",
    "quality",
    "assurance",
    "qa",
    # Redaction placeholder tokens (never re-redact inside a placeholder)
    "candidate_name",
    "candidate_email",
    "candidate_phone",
    "candidate_location",
    "national_id",
    "url",
    "date",
    "institution",
    "employer",
    "photo",
}


def _protected_terms() -> frozenset[str]:
    """Return lower-cased skill, role, and degree terms that NER must never redact."""
    global _PROTECTED_TERMS
    if _PROTECTED_TERMS is not None:
        return _PROTECTED_TERMS

    terms = set(_BASE_PROTECTED_TERMS)
    skills_path = (
        Path(__file__).resolve().parents[1] / "core" / "fixtures" / "skills.json"
    )
    if skills_path.exists():
        try:
            rows = json.loads(skills_path.read_text(encoding="utf-8"))
            for row in rows:
                fields = row.get("fields", {})
                canonical = fields.get("canonical_name", "")
                if canonical:
                    terms.add(canonical.lower())
                for alias in fields.get("aliases", []) or []:
                    terms.add(str(alias).lower())
        except (OSError, json.JSONDecodeError):
            pass

    _PROTECTED_TERMS = frozenset(terms)
    return _PROTECTED_TERMS


def get_nlp() -> Any:
    """Lazy-load ``en_core_web_sm`` once per process without network access.

    Only ``tok2vec`` and ``ner`` are needed for entity extraction; disabling the
    dependency parser and lemmatizer cuts per-resume latency in half without
    changing NER spans.
    """
    global _NLP
    if _NLP is None:
        import spacy

        _NLP = spacy.load("en_core_web_sm", disable=["parser", "lemmatizer"])
    return _NLP


def _is_protected_span(span_text: str) -> bool:
    """True when ``span_text`` is a skill, degree field, role title, or placeholder."""
    if "[" in span_text or "]" in span_text:
        return True
    cleaned = " ".join(span_text.split()).strip(" .,;:()[]{}-").lower()
    if not cleaned or len(cleaned) < 2:
        return True
    protected = _protected_terms()
    if cleaned in protected:
        return True
    # Also protect spans composed entirely of protected tokens (e.g. "Senior Backend Engineer",
    # "B.Sc. in Computer Science and Engineering", "Django REST Framework").
    tokens = [
        tok.strip(".,;:()")
        for tok in cleaned.split()
        if tok.strip(".,;:()") not in {"in", "and", "of", "for", "with", "the", "&"}
    ]
    if tokens and all(tok in protected for tok in tokens):
        return True
    return False


@dataclass(frozen=True)
class RedactionResult:
    """Sanitised text and per-category redaction counts (never raw PII)."""

    text: str
    counts: dict[str, int] = field(default_factory=dict)

    @property
    def total_redactions(self) -> int:
        return sum(self.counts.values())


def _apply_pattern(
    text: str,
    pattern: re.Pattern[str],
    category: str,
    counts: dict[str, int],
) -> str:
    placeholder = PLACEHOLDERS[category]

    def _repl(_match: re.Match[str]) -> str:
        counts[category] = counts.get(category, 0) + 1
        return placeholder

    return pattern.sub(_repl, text)


def _apply_url_pattern(text: str, counts: dict[str, int]) -> str:
    placeholder = PLACEHOLDERS["url"]

    def _repl(match: re.Match[str]) -> str:
        raw = match.group(0)
        trimmed = raw.rstrip(".,;:)")
        cut = len(trimmed)
        trailing = raw[cut:]
        counts["url"] = counts.get("url", 0) + 1
        return placeholder + trailing

    return _URL_RE.sub(_repl, text)


def _redact_known_literal(
    text: str,
    literal: str,
    category: str,
    counts: dict[str, int],
) -> str:
    cleaned = " ".join(literal.split()).strip()
    if len(cleaned) < 2:
        return text
    tokens = [re.escape(tok) for tok in cleaned.split()]
    pattern = re.compile(r"\b" + r"\s+".join(tokens) + r"\b", re.IGNORECASE)
    return _apply_pattern(text, pattern, category, counts)


def redact_deterministic(
    text: str,
    *,
    known_name: str = "",
    known_location: str = "",
    profile: Mapping[str, str] | None = None,
) -> RedactionResult:
    """Run the deterministic regex and known-PII redaction layer (batch 2.7).

    Replaces emails, phones (Bangladeshi and international), URLs, national IDs,
    dates of birth, structured postal addresses, and the candidate's own profile
    name and location with typed placeholders.
    """
    if profile is not None:
        known_name = known_name or str(profile.get("name", "") or "")
        known_location = known_location or str(profile.get("location", "") or "")

    counts: dict[str, int] = {cat: 0 for cat in ALL_CATEGORIES}
    out = text

    # 1. Emails
    out = _apply_pattern(out, _EMAIL_RE, "email", counts)

    # 2. URLs
    out = _apply_url_pattern(out, counts)

    # 3. Phone numbers (run before bare NIDs so +880XXXXXXXXXX is a phone, not 13 digits)
    out = _apply_pattern(out, _BD_PHONE_RE, "phone", counts)
    out = _apply_pattern(out, _INTL_PHONE_RE, "phone", counts)

    # 4. National IDs / passports
    out = _apply_pattern(out, _LABELLED_NID_RE, "national_id", counts)
    out = _apply_pattern(out, _BARE_NID_RE, "national_id", counts)

    # 5. Dates of birth
    out = _apply_pattern(out, _DOB_RE, "age_date", counts)

    # 6. Structured postal addresses + candidate's known profile location
    out = _apply_pattern(out, _POSTAL_ADDRESS_RE, "address", counts)
    if known_location:
        out = _redact_known_literal(out, known_location, "address", counts)

    # 7. Candidate's known profile name
    if known_name:
        out = _redact_known_literal(out, known_name, "name", counts)

    return RedactionResult(text=out, counts=counts)


def _strip_graduation_and_year_ranges(
    text: str,
    counts: dict[str, int],
    *,
    reference_year: int,
) -> str:
    """Replace graduation years and calendar year ranges with durations + [DATE]."""
    placeholder = PLACEHOLDERS["age_date"]

    def _grad_repl(match: re.Match[str]) -> str:
        counts["age_date"] = counts.get("age_date", 0) + 1
        try:
            year = int(match.group(1))
            years_ago = max(0, reference_year - year)
            return f"{placeholder} ({years_ago} years ago)"
        except ValueError:
            return placeholder

    def _range_repl(match: re.Match[str]) -> str:
        counts["age_date"] = counts.get("age_date", 0) + 1
        try:
            start_y = int(match.group(1))
            end_y = int(match.group(2))
            duration = max(0, end_y - start_y)
            unit = "year" if duration == 1 else "years"
            return f"{placeholder} ({duration} {unit})"
        except ValueError:
            return placeholder

    out = _GRADUATION_YEAR_RE.sub(_grad_repl, text)
    out = _YEAR_RANGE_RE.sub(_range_repl, out)
    return out


def _strip_contextual_employers(text: str, counts: dict[str, int]) -> str:
    """Strip employer names after 'at <Org Name>' when not an institution or skill."""
    placeholder = PLACEHOLDERS["employer"]

    def _repl(match: re.Match[str]) -> str:
        candidate_org = match.group(1)
        if _is_protected_span(candidate_org):
            return candidate_org
        if _INSTITUTION_RE.search(candidate_org):
            return candidate_org
        counts["employer"] = counts.get("employer", 0) + 1
        return placeholder

    return _CONTEXTUAL_EMPLOYER_RE.sub(_repl, text)


def _apply_spacy_ner(text: str, counts: dict[str, int], nlp: Any) -> str:
    """Run spaCy NER for PERSON, ORG, GPE and LOC, respecting keep-set terms."""
    doc = nlp(text)
    replacements: list[tuple[int, int, str, str]] = []

    for ent in doc.ents:
        label = ent.label_
        if label not in {"PERSON", "ORG", "GPE", "LOC"}:
            continue
        if (ent.start_char > 0 and text[ent.start_char - 1] == "[") or (
            ent.end_char < len(text) and text[ent.end_char] == "]"
        ):
            continue
        span_text = ent.text
        if _is_protected_span(span_text):
            continue

        if label == "PERSON":
            cat = "name"
        elif label == "ORG":
            low = span_text.lower()
            if any(
                kw in low
                for kw in ("university", "college", "school", "institute", "academy")
            ):
                cat = "institution"
            else:
                cat = "employer"
        else:
            cat = "address"

        replacements.append((ent.start_char, ent.end_char, PLACEHOLDERS[cat], cat))

    if not replacements:
        return text

    # Apply from right to left so character offsets remain valid.
    chars = list(text)
    for start, end, placeholder, cat in sorted(
        replacements, key=lambda item: item[0], reverse=True
    ):
        chars[start:end] = list(placeholder)
        counts[cat] = counts.get(cat, 0) + 1
    return "".join(chars)


def strip_pii(
    text: str,
    *,
    known_name: str = "",
    known_location: str = "",
    profile: Mapping[str, str] | None = None,
    reference_year: int = DEFAULT_REFERENCE_YEAR,
    nlp: Any | None = None,
) -> RedactionResult:
    """Full PII and proxy stripping pipeline (REQ-FR-011, REQ-FR-057, batches 2.7–2.8).

    Runs the deterministic regex layer first, then strips photo references,
    stated ages, graduation/cohort years and date ranges (converted to
    durations), institutions, employers, referee names, and residual NER
    ``PERSON`` / ``ORG`` / ``GPE`` / ``LOC`` entities while protecting skills,
    degree levels/fields and role titles.
    """
    det = redact_deterministic(
        text,
        known_name=known_name,
        known_location=known_location,
        profile=profile,
    )
    counts = dict(det.counts)
    out = det.text

    # 1. Photo references
    out = _apply_pattern(out, _PHOTO_RE, "photo", counts)

    # 2. Stated ages and graduation/cohort years (converted to durations)
    out = _apply_pattern(out, _STATED_AGE_RE, "age_date", counts)
    out = _strip_graduation_and_year_ranges(out, counts, reference_year=reference_year)

    # 3. Educational institutions (before employer and NER passes so "BRAC University"
    # is tagged as [INSTITUTION] rather than [EMPLOYER]).
    out = _apply_pattern(out, _INSTITUTION_RE, "institution", counts)

    # 4. Corporate and contextual employer names
    out = _apply_pattern(out, _CORPORATE_EMPLOYER_RE, "employer", counts)
    out = _strip_contextual_employers(out, counts)

    # 5. Referee / Reference person names
    def _ref_repl(match: re.Match[str]) -> str:
        counts["name"] = counts.get("name", 0) + 1
        return f"{match.group(1)}{PLACEHOLDERS['name']}"

    out = _REFEREE_PERSON_RE.sub(_ref_repl, out)

    # 6. spaCy NER pass for any remaining PERSON, ORG, GPE, LOC spans
    model = nlp if nlp is not None else get_nlp()
    out = _apply_spacy_ner(out, counts, model)

    return RedactionResult(text=out, counts=counts)
