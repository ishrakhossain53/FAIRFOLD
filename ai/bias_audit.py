"""Bias audit on a generated rationale, and the audit-trail payload it produces.

This is the seam between :mod:`ai.bias_pass` and the product. The pass answers
"does this text contain a signal"; this module answers the three questions the
product actually needs:

1. **Did the rationale pass or flag, and on what?**
2. **What exactly was checked**, so the panel can show "what was checked" rather
   than an unexplained badge (`design.md` 7.7).
3. **What goes in the audit row** -- ``REQ-COM-008`` and ``REQ-FR-030`` require a
   retained ``ai_decision``-class entry for every screening, rationale and bias
   check.

Why this module holds no Django import
--------------------------------------

``audit_log_entries`` is a table with ``action``, ``resource_type``, ``details``
(JSONB) and ``result``. This module builds the **payload** for that row and
returns it as a plain dict. The caller -- a Celery task or a view -- passes it to
the model. Two reasons for that split:

* The payload is testable without a database, which is why this project can prove
  the audit trail is *correct in shape* before a single migration is written.
* An audit entry that is computed by code nobody can run is not an audit trail.

The write is a two-line call, documented on :func:`record` below. That boundary is
deliberate and narrow: no other Django-specific behaviour belongs here.

Where the entry goes
--------------------

``audit_log_entries`` with ``resource_type = 'ai_decision'``. That value is what puts the
row in the **long-retention class** -- held with the application record for 2 years, 5 if
hired -- rather than the 90-day operational rotation. ``REQ-COM-008`` requires the trail
and ``REQ-FR-052`` already depends on the distinction; 90 days would destroy the only
evidence that a decision was not biased, which is the whole claim this product makes.

What this must never become
---------------------------

A pass that *blocks* the employer. ``design.md`` 7.7 says a flagged rationale
"excludes the candidate from bulk Shortlist top N until reviewed" -- that is a
queueing constraint on a bulk action, not a veto, and
``test_a_flag_is_not_a_veto`` pins that. ``REQ-FR-052`` is explicit that overrides
are not blocked and the human remains the decision-maker. A bias audit that stops
a recruiter is not a bias audit, it is an unappealable automated rejection -- the
failure this whole product exists to avoid.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ai.bias_pass import (
    REPO_ROOT,
    ScanContext,
    ScanResult,
    load_rules,
    load_terms,
    normalise,
    scan,
)

#: ``resource_type`` for every screening, rationale and bias check. Retained with
#: the application record (2y, 5y if hired) rather than rotating at 90 days, per
#: the two-retention-classes decision in prd.md 18.2. 90 days would destroy the
#: only evidence that a decision was not biased.
AUDIT_RESOURCE_TYPE = "ai_decision"

ACTION_SCREENED = "bias_audit"
ACTION_REVIEWED = "bias_audit_reviewed"

RESULT_PASS = "pass"
RESULT_FLAG = "flag"


@dataclass(frozen=True)
class BiasAudit:
    """The outcome of auditing one rationale."""

    result: ScanResult
    context: ScanContext
    #: SHA of the term/rule list the audit ran against, so an entry can be
    #: replayed against the exact rules that produced it.
    rules_version: str
    rationale_hash: str

    @property
    def flagged(self) -> bool:
        return self.result.flagged

    @property
    def outcome(self) -> str:
        return RESULT_FLAG if self.flagged else RESULT_PASS

    @property
    def checked(self) -> list[str]:
        """Every rule that ran, whether or not it fired.

        The panel shows this, so a reader can tell "checked and found nothing"
        from "not checked". Those look identical otherwise, and the second is
        indistinguishable from a clean result.
        """
        return sorted(set(self.result.rules_checked))

    @property
    def highlights(self) -> list[str]:
        """Quotable spans for the panel to highlight in the rationale."""
        return self.result.highlights

    @property
    def blocks_bulk_shortlist(self) -> bool:
        """A flag holds a candidate out of *bulk* shortlist until reviewed.

        It never blocks the employer from acting. See the module docstring and
        ``design.md`` 7.7.
        """
        return self.flagged


def _hash_text(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _set_version(set_dir: Path) -> str:
    import json

    manifest = set_dir / "manifest.json"
    if not manifest.exists():
        return "unknown"
    return json.loads(manifest.read_text(encoding="utf-8")).get("version", "unknown")


def audit_rationale(
    rationale: str,
    *,
    set_dir: Path | str | None = None,
    context: ScanContext | None = None,
    terms: list | None = None,
    rules: list | None = None,
) -> BiasAudit:
    """Run the bias pass over a generated rationale.

    Args:
        rationale: the AI-generated text. **Anonymised text only** -- PII is
            stripped before any external provider (``REQ-FR-030``), and this
            function must never be handed the pre-strip version.
        set_dir: bias set version directory. Defaults to the newest committed one.
        context: numeric-rule parameters. Supplied by the caller rather than read
            from the clock so an audit entry is reproducible.
        terms / rules: pre-loaded lists, so a caller auditing many rationales in
            one task parses the JSON once.

    Raises:
        FileNotFoundError: if an explicit ``set_dir`` holds no term list, or no
            versioned set exists at all. Loud, on purpose: an audit that silently
            finds nothing is indistinguishable from a clean result, and it would
            write a ``pass`` row into a retained audit trail.
    """
    # An explicit set_dir is honoured exactly, or it raises. It is NOT resolved
    # to "the newest one" as a fallback: an audit pointed at v1.0.1 that quietly ran
    # against v1.0.2 would stamp the row with a rules_version that does not describe
    # the rules that produced it, which is the one thing the version field exists to
    # prevent. A caller asking for a specific set and silently getting another is
    # worse than an exception.
    if set_dir is not None:
        directory = Path(set_dir)
        if not (directory / "keyword_terms.json").exists():
            raise FileNotFoundError(
                f"no keyword_terms.json in {directory}. Refusing to audit against a "
                f"different rules version than the one requested."
            )
    else:
        directory = _newest_set_dir()

    if terms is None or rules is None:
        terms = terms or load_terms(directory)
        rules = rules or load_rules(directory)

    ctx = context or ScanContext()
    outcome = scan(rationale, terms, rules, ctx)
    return BiasAudit(
        result=outcome,
        context=ctx,
        rules_version=_set_version(directory),
        rationale_hash=_hash_text(rationale),
    )


def _newest_set_dir() -> Path:
    root = REPO_ROOT / "tests" / "bias"
    versions = sorted(
        (p for p in root.glob("v*") if (p / "keyword_terms.json").exists()),
        key=lambda p: [int(part) for part in p.name.lstrip("v").split(".")],
    )
    if not versions:
        raise FileNotFoundError(f"no versioned bias test set under {root}")
    return versions[-1]


def audit_payload(
    audit: BiasAudit,
    *,
    resource_id: str,
    actor_id: str | None = None,
    action: str = ACTION_SCREENED,
) -> dict:
    """Build the ``audit_log_entries`` row payload for one audit.

    Every key maps to a real column in Arch Doc 5.1: ``action``, ``resource_type``,
    ``resource_id``, ``details`` (JSONB), ``result``. ``actor_id`` is left to the
    caller because the bias audit runs in a Celery task with no session user --
    and a null actor is meaningful, not an omission: it records that the audit was
    automatic rather than performed by a person.

    ``details`` carries everything needed to re-derive the flag later: which rules
    ran, what fired, the reference year and window in force, and a hash of the
    rationale. The hash rather than the text, because this table has a retention
    class and the rationale belongs to the application record.
    """
    return {
        "action": action,
        "resource_type": AUDIT_RESOURCE_TYPE,
        "resource_id": resource_id,
        "actor_id": actor_id,
        "result": audit.outcome,
        "details": {
            "pass_version": audit.rules_version,
            "rationale_hash": audit.rationale_hash,
            "checked": audit.checked,
            "matched_groups": sorted(audit.result.groups),
            "highlights": audit.highlights,
            "explanation": audit.result.explain(),
            "reference_year": audit.context.reference_year,
            "graduation_window_years": audit.context.graduation_window_years,
            "blocks_bulk_shortlist": audit.blocks_bulk_shortlist,
        },
    }


def review_payload(
    audit: BiasAudit,
    *,
    resource_id: str,
    actor_id: str,
    note: str | None = None,
) -> dict:
    """Build the payload for a human "Mark as reviewed" action (design.md 7.7).

    Separate from the audit payload because ``actor_id`` is now a real person: a
    review is an assertion that somebody looked, and the audit trail is the only
    record that they did. An empty note is allowed -- the employer may agree with
    the flag and just be acknowledging it.
    """
    payload = audit_payload(
        audit, resource_id=resource_id, actor_id=actor_id, action=ACTION_REVIEWED
    )
    payload["details"] = {
        **payload["details"],
        "reviewed_outcome": audit.outcome,
        "note": note or "",
    }
    return payload


def record(payload: dict) -> object:
    """Write one payload to ``audit_log_entries``. The Django boundary.

    The entire integration, by design::

        from core.models import AuditLogEntry

        AuditLogEntry.objects.create(**record(payload))

    Imported lazily so this module stays importable with no Django installed,
    which is what lets the audit trail be tested at all before Phase 1 exists.

    **Why ``core``.** ``prd.md`` 11.1 classes ``AuditLogEntry`` as a *Compliance*
    entity, but the app tree in Complete Doc 4.2 has no compliance app, and nothing in
    any document says which app owns it. ``core`` is the answer here because the model is
    cross-cutting: ``matching``, ``employers``, ``candidates`` and the GDPR routes all
    write to it, and a model imported from a leaf app would be a circular import waiting
    to happen. Recorded as an ownership decision rather than left implicit -- see
    ``HISTORY.md``.
    """
    from core.models import AuditLogEntry

    return AuditLogEntry.objects.create(**payload)