# Validation instrument — Employer-first kit (prepared 2026-10-13)

This directory holds the **employer-first validation kit** for requirement-validation:
consent forms, interview guides, willingness-to-pay module, and the results table.

---

## ⚠️ Nothing here has been collected

**Study not yet run.** `validation/results.md` is empty by design
and every cell is marked. Do not fill any of it from memory, from assumption, or from
"what we would expect" — an invented finding is worse than no finding, because §1.2.2
and the academic report both cite evidence, and a fabricated count would propagate into
a claim nobody can trace back to a person.

The kit fixes the sample size, the channel and the questions **before** anyone collects
data, so that nobody can later describe a result that was never collected. Keeping that
promise is the entire reason this directory exists.

---

## Hypotesis Register

**Purpose.** Each validation activity tests an employer-side assumption that gates Phase 3
build. The register is in `validation/hypotheses.md`.

**Assumption IDs (employer-side).**  
| ID | Assumption | Requirement | ASM entry |
|---|---|---|---|
| H-EM-001 | Employers want anonymised screening | REQ-FR-054 | ASM-2.1 |
| H-EM-002 | Employers accept alias-only view until shortlist | REQ-FR-053 | ASM-2.3 |
| H-EM-003 | Hiring managers trust AI shortlist explanations | REQ-FR-049 | ASM-2.2 |
| H-EM-004 | Assessment gating is acceptable | REQ-FR-052 | ASM-2.4 |
| H-EM-005 | Recruiters will pay for the service (Starter tier) | REQ-FR-056 | ASM-2.5 |

**Candidate-side assumptions.**  
| ID | Assumption |
|---|---|
| H-CN-001 | Job seekers accept proxy stripping |
| H-CN-002 | Job seekers accept tab-switch monitoring |
| H-CN-003 | Text coaching adds value |

---

## What is in here

| File | What it is | Who uses it |
|---|---|---|
| `hypotheses.md` | Central register of all assumptions to test | Researcher |
| `participant_plan.md` | Screener, recruiting channels, consent script | Interviewer |
| `employer_interview_guide.md` | 45-minute guide for recruiters | Interviewer |
| `candidate_interview_guide.md` | 20-minute guide for job seekers | Interviewer |
| `willingness_to_pay.md` | Joanne Pedersen price sensitivity table | Interviewer |
| `pre_commitment_ask.md` | Ladder of real commitments | Interviewer |
| `decision_rules.md` | Success thresholds and gate rules | Founder |
| `evidence_templates.md` | Note template, coding scheme, results table | Interviewer |
| `ethics_data_handling.md` | Consent, storage, anonymisation | Researcher |
| `demo_script.md` | Walkthrough without real PII | Interviewer |
| `results.md` | The recording sheet, **empty** | The person who ran sessions |

---

## Rules for whoever runs this

1. **Read the consent form aloud**, not just hand it over. Several participants will not
   read it, and the ones who cannot read it well are disproportionately the ones the
   product is for.
2. **Record answers, not conclusions.** The sheet asks for a quote or a count. "They
   seemed to distrust it" is a conclusion and it is unusable.
3. **Do not correct participants.** If someone says screening is fine, that is the data.
4. **Do not lead.** The guides are ordered so the leading questions come last. Do not
   add a fifth "but wouldn't you agree…" — that is the single easiest way to turn this
   exercise into confirmation of the PRD.
5. **Do not run past the stated sample sizes.** 3–5 candidates, 5–6 recruiters. Beyond
   that the material stops being themes and starts being a dataset nobody has time to
   analyse, and a half-analysed set of 20 interviews is worth less than a complete set
   of 9.
6. **Withdraw anything.** A participant can ask for their notes to be deleted at any
   point, including after the session. Delete them and note the withdrawal in
   `results.md` without recording why.

---

## Sample sizes are small, and that is deliberate

Target is a small honest evidence base, not a study. At n=5 recruiters, **no
percentage from this exercise may be published as a market fact.** Report as "of N
participants". Anything else turns five conversations into a statistic, which is the
mistake this project has already had to correct once — the withdrawn "bias-free" claim
(`HISTORY.md` §2.22) began as an unmeasured assertion.

---

## After it runs

1. Fill `results.md` — counts and quotes only.
2. In `HISTORY.md`, add a section citing the real counts.
3. In `prd.md` §19, replace **[Planned]** tags with measured values where data supports them,
   or delete unsupported assertions.
4. If data contradicts a requirement, **the requirement changes**, not the reading of
   the data. That is the whole reason this is recorded before collection rather than after.