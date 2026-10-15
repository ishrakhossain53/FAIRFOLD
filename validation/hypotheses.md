# Hypotheses Register — Employer-First Validation Kit

**Document:** `validation/hypotheses.md`  
**Date:** 2026-10-13  
**Purpose:** Central register of assumptions to test with recruiters and employers before Phase 3.  
**Status:** PROPOSED — founder must confirm or change before the first interview.

---

## How to use this register

Each hypothesis has:

- **ID (H-XX):** Short identifier for cross-referencing
- **Statement:** The assumption to test
- **Evidence needed:** What counts as supporting evidence
- **Disconfirming evidence:** What would refute or weaken the hypothesis
- **Dependent requirement:** The REQ-FR or ASM ID that relies on this claim

---

## H-EM-001: Employers want anonymised screening

**Statement:** Employers are willing to screen candidates without seeing their identity (name, email, photo, current employer) until shortlist.

**Evidence needed:** Recruiters describe using blind/anonymous screening tools; express willingness to hide identities during initial screening; articulate the benefit beyond "privacy."

**Disconfirming evidence:** "I need to see who they worked for to judge"; "I can't make a decision without knowing their background"; "This adds steps I don't need."

**Dependent requirement:** REQ-FR-011 (PII stripping), REQ-FR-029 (anonymised list), REQ-FR-057 (proxy stripping), REQ-FR-054 (candidate alias)

---

## H-EM-002: Alias-only views are acceptable during screening

**Statement:** Recruiters accept per-employer candidate aliases (e.g., "C-7H2X9") instead of names during the screening phase.

**Evidence needed:** Recruiters acknowledge or express comfort with aliases; describe how aliases would help their process; do not request real names during initial screening.

**Disconfirming evidence:** "I need to recognize familiar names"; "I can't track candidates without names"; "Aliases confuse me."

**Dependent requirement:** REQ-FR-054 (per-employer candidate alias)

---

## H-EM-003: Employers will pay for FairFold screening

**Statement:** Employers (particularly software companies and BPOs in Bangladesh) are willing to pay monthly fees for AI-assisted screening on the free tier.

**Evidence needed:** Recruiters express budget willingness for a $100–$1,500/month pricing band; compare favorably to current tools; acknowledge cost savings in time/reduced bias risk.

**Disconfirming evidence:** "Too expensive for our budget"; "Free alternatives are good enough"; "We can't justify this expense."

**Dependent requirement:** REQ-FR-028 (cost estimate confirmation), REQ-FR-056 (local BDT payments), complete pricing section in prd.md §15.2

---

## H-EM-004: AI shortlist explanations are trusted

**Statement:** Recruiters will accept and act on AI-generated rationales that cite evidence from candidates' resumes and flag bias risk.

**Evidence needed:** Recruiters describe using AI explanations to understand scores; express trust in cited evidence; accept bias audit flags as valid signals.

**Disconfirming evidence:** "I don't trust AI to explain"; "The rationale sounds made up"; "I need my own judgment, not AI's."

**Dependent requirement:** REQ-FR-030 (evidence-cited rationale), REQ-COM-008 (audit trail), bias audit considerations in prd.md §4.2

---

## H-EM-005: Assessment gating is acceptable

**Statement:** Employers will use skill assessments as a required step before shortlisting, and will accept that candidates cannot be shortlisted on score alone if they fail.

**Evidence needed:** Recruiters describe needing skills verification; accept that assessments must be passed; understand the gate prevents poor hire decisions.

**Disconfirming evidence:** "Assessments take too long"; "I can shortlist without them"; "This blocks good candidates."

**Dependent requirement:** REQ-FR-051 (employer-required assessment gate), REQ-FR-052 (override visibility)

---

## H-CAN-001: Candidates accept proxy stripping

**Statement:** Job seekers will apply through a platform that removes institution names, employer names, age-revealing dates, and other proxy identifiers from their resumes before AI processing.

**Evidence needed:** Candidates describe this as acceptable or preferable; do not express concern about losing context; understand it enables fairer screening.

**Disconfirming evidence:** "My university name is important for the role"; "I need to show my experience"; "Without my employer, it's useless."

**Dependent requirement:** REQ-FR-011, REQ-FR-057 (expanded proxy stripping)

---

## H-CAN-002: Candidates accept tab-switch proctoring consent

**Statement:** Job seekers consent to having their tab-switch and window-blur events recorded during assessments, understanding this is for integrity monitoring only.

**Evidence needed:** Candidates agree to the consent screen; accept that this does not involve video/audio/facial tracking; understand it never auto-fails an attempt.

**Disconfirming evidence:** "I won't do it if it tracks me"; "This is invasive"; "Why do you need to know this?"

**Dependent requirement:** REQ-FR-055 (light tab-switch proctoring)

---

## H-CAN-003: Text coaching and curated resources add value

**Statement:** Candidates find the text-only interview practice, STAR rubric feedback, and curated resource links helpful for job applications.

**Evidence needed:** Candidates describe using coaching sessions; express that feedback improved their answers; value the resource recommendations.

**Disconfirming evidence:** "The coaching is not useful"; "Resources are irrelevant"; "I don't need this help."

**Dependent requirement:** REQ-FR-058–063 (interview practice, coaching, training resources)

---

## Cross-reference index

| Hypothesis ID | REQ-FR | ASM | Wireframe(s) |
|---|---|---|---|
| H-EM-001 | 011, 029, 057 | — | W30, W37 |
| H-EM-002 | 054 | — | W37, W38 |
| H-EM-003 | 028, 029, 053, 056 | — | W14, W40, W50 |
| H-EM-004 | 030 | — | W13, W41 |
| H-EM-005 | 051, 052 | — | W39, W42 |
| H-CAN-001 | 057 | — | W30, W31, W71 |
| H-CAN-002 | 055 | — | W34, W74 |
| H-CAN-003 | 058–063 | — | W33, W77, W78 |

---

## Status tracking

This table is updated as interviews proceed and evidence is collected.

| Hypothesis ID | Interviewed | Verdict | Evidence count | Notes |
|---|---|---|---|---|
| | | | | |
| | | | | |
| | | | | |
| | | | | |