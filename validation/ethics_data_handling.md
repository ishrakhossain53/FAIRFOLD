# Ethics and Data Handling

**Document:** `validation/ethics_data_handling.md`  
**Date:** 2026-10-13  
**Purpose:** Ensure ethical research practices and proper data handling for the validation study.

---

## 1. Personal Data Collected

### What we collect

| Data type | Source | Purpose | Retention |
|---|---|---|---|
| Participant notes | Interview notes | Research analysis | 2 years after study completion |
| Demographics (optional) | Participant self-report | Context for findings | 2 years |
| Contact info | Participant-provided email | Follow-up, consent withdrawal | Deleted after study |
| Screening responses | Interview responses | Hypothesis testing | 2 years |

### What we do NOT collect

- **No real candidate resumes** — all demos use synthetic data
- **No company-sensitive information** without explicit permission
- **No recordings** — written notes only
- **No personal identifiers in results** — all quoted as "a recruiter at a software company"

---

## 2. Storage

All validation data is stored:

- **Location:** Encrypted files in the FairFold project repository
- **Access:** Only the research team (4 members)
- **Format:** Plain text notes, spreadsheet in `validation/results.md`
- **Backups:** Git version-controlled (no PII in git history)

### File structure

```
validation/
├── consent_forms/           # Signed consents (if any)
├── notes/                   # Raw interview notes
├── results.md               # Anonymized results table
└── analysis/                # Summaries (no PII)
```

---

## 3. Anonymization

### Note anonymization

Before sharing findings:

1. Replace company names with "Company A", "Company B", etc.
2. Replace names with "Recruiter 1", "Recruiter 2", etc.
3. Remove any identifying details (specific technologies, exact locations)
4. Aggregate quotes: "5 of 6 participants mentioned..."

### Results table anonymization

All rows in `results.md` use anonymous codes:

| Field | Example |
|---|---|
| Code | R01, C01 |
| Company | Company A, Company B |
| Notes | "Looks at company culture fit" (not "Looks at my old company") |

---

## 4. No Real Candidate Data in Demos

**All demos must use synthetic resumes.**

### Synthetic resume spec

These are NOT real applications:

- **Name:** `[CANDIDATE_NAME]`
- **Email:** `[EMAIL]`
- **Phone:** `[PHONE]`
- **Institution:** `[INSTITUTION]`
- **Employer:** `[EMPLOYER]`
- **Dates:** `[DATE]` or fake dates (e.g., 2020–2023)
- **Skills:** Generic, not specific to real person
- **Projects:** Hypothetical, not real work

### Generated examples

Example synthetic candidate:

```
[CANDIDATE_NAME]
Backend Developer
[EMAIL] | [PHONE]

EXPERIENCE
[EMPLOYER_A] — Backend Developer (2020–2023)
- Built APIs with Python/Django
- Deployed services on AWS
- Led code reviews for 3 junior devs

[INSTITUTION] — BSc Computer Science (2016–2020)

SKILLS
Python, Django, PostgreSQL, Docker, AWS
```

---

## 5. Consent Form Requirements

### What participants must sign/write

Before any session:

1. **Informed consent** — they understand the purpose
2. **Voluntary participation** — they can stop anytime
3. **No recording** — written notes only
4. **Withdrawal right** — can request deletion at any time
5. **No compensation** — participation is volunteer

### Consent script (read aloud)

> "This is a FairFold research session about hiring processes. It will last 20–30 minutes for recruiters or 20 minutes for job seekers. We will write down your answers, and we may quote you in aggregate without using your name. This is NOT a hiring process, and nothing we discuss affects any job applications. You can stop at any time or ask us to delete your notes. Do you consent to participate?"

---

## 6. Withdrawal Process

If a participant withdraws:

1. Destroy all notes for that session
2. Record only: "Withdrawal: date, code" in `results.md`
3. Do not count toward total sample size

### Withdrawal note in results.md

```
Withdrawal
Date: 2026-10-25
Code: R04
Reason: Not given
```

---

## 7. Data Retention Schedule

| Time after study completion | Action |
|---|---|
| 0–2 years | Full anonymized data retained |
| 2–5 years | Minimal data retained (aggregated results) |
| 5+ years | Data deleted unless needed for legal reasons |

---

## 8. GDPR Compliance Check

Even though this is Bangladesh-first, follow GDPR principles:

| Requirement | Status |
|---|---|
| Right to be informed | ✅ Consent form explains everything |
| Right of access | ✅ Can request all data we have |
| Right to rectification | ✅ Can correct any data with source |
| Right to erasure | ✅ Deletion upon request |
| Right to restrict processing | ✅ Can pause sharing |
| Right to data portability | ✅ Can receive copy in plain text |
| Right to object | ✅ Can opt out of any analysis |

---

## 9. No Commercial Use of Responses

**Participant responses cannot be used for:**

- Marketing copy
- Sales pitches
- Product claims
- Anything that presents them as a customer

All quotes in reports are:
- Presented as "participant opinion"
- Attributed only as "some recruiters" or "some candidates"
- Never quoted by role/department/company

---

## 10. Summary for Participants

At the start of each session, tell participants:

> "Your participation helps us build a fairer hiring platform. Everything you share is anonymous, and no real candidate data is used in demos. Your insights will shape how this product works, but your identity will never be connected to your responses."

---

## Questions to ask participants

If they raise data concerns:

> "What specific privacy concern do you have?"

> "Is there data you've shared in past research that you've regretted?"

> "What would make you more comfortable participating?"

Document any concerns raised and how they were addressed.