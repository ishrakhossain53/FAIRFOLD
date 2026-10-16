# Decision Rules — Phase 3 Validation Gate

**Document:** `validation/decision_rules.md`  
**Date:** 2026-10-13  
**Status:** PROPOSED — founder must confirm or change before the first interview

---

## ⚠️ LOCK DATE: 2026-10-20

These thresholds are set **before** any interviews begin. The founder must confirm or change them by this date. Changing thresholds after seeing data invalidates the validation.

---

## Success Thresholds by Hypothesis

Each hypothesis has a go/adjust/stop criterion. The Phase 3 validation gate requires **both employer and candidate hypotheses** to pass.

| Hypothesis | Threshold for Go | Threshold for Adjust | Threshold for Stop | Notes |
|---|---|---|---|---|
| H-EM-001 (anonymised screening) | ≥80% Support (≤1 contradict) | 60–79% Support | ≥40% Contradict | Key for employer adoption |
| H-EM-002 (alias views) | ≥80% Accept aliases | 60–79% Accept | ≥40% Reject | Blocks core screening UX |
| H-EM-003 (willingness to pay) | ≥80% at Bargain/Getting expensive at ≤1000 BDT | 60–79% | ≥40% Too expensive at 1000 BDT | Pricing confidence |
| H-EM-004 (trust AI explanations) | ≥70% Trust evidence-cited scores | 50–69% Trust | ≥30% Not trusting | AI advisory model relies on this |
| H-EM-005 (assessment gating) | ≥70% Find acceptable | 50–69% | ≥30% Too restrictive | Affects MVP scope |
| H-CAN-001 (proxy stripping) | ≥80% Acceptable | 60–79% | ≥40% Objection | Affects Phase 2 |
| H-CAN-002 (tab-switch consent) | ≥70% Consent | 50–69% | ≥30% Refuse | Affects Phase 3 |
| H-CAN-003 (coaching/resources) | ≥60% See value | <60% no clear win | N/A | Differentiator feature |

---

## How Thresholds Map to Sample Sizes

With target 5–6 recruiters and 3–5 candidates:

| Sample | 80% support | 70% support | 60% support |
|---|---|---|---|
| 5 participants | 4 say support | 4 say support | 3+ say support |
| 6 participants | 5 say support | 4+ say support | 4+ say support |

**Minimum evidence:** At least 5 recruiter interviews (3.3 recruiters = 60% support impossible to verify).

---

## Phase 3 Validation Gate Decision

**To proceed to Phase 3, ALL employer hypotheses (H-EM-001 to H-EM-005) must meet their Go threshold.**

Candidate hypotheses (H-CAN-001 to H-CAN-003) inform product decisions but do not block Phase 3.

| Scenario | Action |
|---|---|
| All employer hypotheses: Go | **Proceed to Phase 3** — build assessment gating, coaching, journey mapping |
| 1–2 employer hypotheses: Adjust | **Scope reduction** — remove features requiring adjusted hypotheses; reduce Phase 3 to 6 weeks |
| ≥3 employer hypotheses: Stop | **Project pause** — revisit assumptions; may rebuild employer-facing UX |

---

## What Changes Scope (Adjust)

If a hypothesis lands in the "Adjust" range:

1. **Feature modification:** The feature can proceed with changes
2. **Conditional implementation:** Build behind a feature flag
3. **Minimum viable version:** Strip to core functionality only

**Examples:**

- **H-EM-003 (pricing):** If at 60–79%, consider a simpler Free/Starter tier only
- **H-EM-005 (assessment gate):** If mixed, make it optional instead of required

---

## What Stops the Project (Stop)

If ≥3 employer hypotheses are in Stop range:

> "The core assumptions about what employers want have been violated. Continue only with major changes to the product model."

**This is NOT failure** — it's evidence. The project can pivot to:

- Different employer segment
- Different pricing model
- Different core value proposition

---

## Pre-commitment Scoring

Combined with the commitment ladder:

| Total commitments | Interpretation |
|---|---|
| 5–6 | Strong adoption signal |
| 3–4 | Moderate interest |
| 0–2 | Skepticism |

**If ≥30% of participants score ≥2** → Pricing and feature set validated

---

## Exit Questions That Feed This Table

Include these in every interview:

- "Is there anything we haven't covered that's important?"
- "What would make you stop using this tool after trying it?"
- "What would make you MORE likely to use it?"
- "Would you sign a letter of intent to purchase if this worked?"

---

## Revisions

Any change to this table:

1. Must be dated
2. Must cite reasons
3. Must be confirmed by founder in email or signed document
4. Cannot reference interview results

---

## Example post-interview decision

*After 6 recruiter interviews (R01–R06):*

| Hypothesis | Support | Contradict | Verdict |
|---|---|---|---|
| H-EM-001 | 4 | 1 | SUPPORTED |
| H-EM-002 | 5 | 1 | SUPPORTED |
| H-EM-003 | 5 | 0 | SUPPORTED |
| H-EM-004 | 3 | 2 | PARTIALLY SUPPORTED |
| H-EM-005 | 4 | 1 | SUPPORTED |

**Decision:** H-EM-004 is partially supported. AI explanations are trusted but some recruiters want more evidence. **Adjust:** Build richer explanation UI. **Proceed to Phase 3.**

---

## Open Questions for Founder

Before running interviews, confirm:

1. **Pricing floor:** What is the minimum viable price per month? [Planned: set after validation]
2. **Target companies to approach:** Which specific Bangladeshi software companies/BPOs first? [Planned: founder input]
3. **Go/No-Go on assessment gate:** If H-EM-005 fails, is Phase 3 viable without it? [Planned: founder decision]
4. **Commitment threshold:** How many pilot participants needed? [Planned: founder decision]

These can be updated in this file with an amendment note:

> **2026-10-14 amendment (Founder confirmation):** Pricing floor confirmed at 500 BDT. Companies: [list]. Commitment threshold: 2 pilots minimum.