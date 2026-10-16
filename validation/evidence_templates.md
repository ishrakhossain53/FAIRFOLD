# Evidence Capture and Synthesis Templates

**Document:** `validation/evidence_templates.md`  
**Date:** 2026-10-13  
**Purpose:** Standard templates for capturing interview evidence and coding responses.

---

## Interview Note Template

**Use this template during every session.** Fill in the blanks, then transcribe quotes verbatim.

---

### Header

```
Participant Code: ______
Date: 2026-____-__
Channel: LinkedIn / Warm intro / University career center / Other
Role: Recruiter / Hiring Manager / Candidate
Company: ______ (to be replaced with anonymous code for analysis)
Session length: ___ minutes
```

---

### Transcript (write on paper, type after)

**Question 1: [Question text]**
- Answer: ________________________________________________________
- Quote (if qualitative): "________________________________________"
- Count (if applicable): ___

**Question 2: [Question text]**
- Answer: ________________________________________________________
- Quote: "________________________________________"
- Count: ___

[Continue for all core questions]

---

### Verbatim Quotes Section

> This section contains direct quotes. Do not summarize.

**Q1 — [Question]:** "________________________________________"

**Q2 — [Question]:** "________________________________________"

**Q4 — [Any notable reaction]:** "________________________________________"

---

### Notes

- Any observations not captured in questions
- Non-verbal cues (if noted)
- Participant concerns or enthusiasm levels

---

### Withdrawal (if applicable)

```
Participant withdrew on: ___
Reason given: ______
Notes deleted: YES / NO
Withdrawal recorded in: results.md
```

---

## Coding Scheme

Map each response to hypotheses. Use this table to sort qualitative data.

---

### For Recruiter Interviews

| Response | Hypothesis | Code | Verdict |
|---|---|---|---|
| "I need to see their name to judge experience" | H-EM-002 | rejects_alias | CONTRADICTS |
| "Names don't matter for an ATS" | H-EM-002 | accepts_alias | SUPPORTS |
| "I like seeing the actual resume text" | H-EM-004 | trusts_evidence | SUPPORTS |
| "AI explanations are never right" | H-EM-004 | distrusts_ai | CONTRADICTS |
| "500 BDT would be a bargain" | H-EM-003 | price_bargain | SUPPORTS |
| "Too expensive even for free tier" | H-EM-003 | no_budget | CONTRADICTS |

---

### For Candidate Interviews

| Response | Hypothesis | Code | Verdict |
|---|---|---|---|
| "My university name is important" | H-CAN-001 | rejects_proxy_strip | CONTRADICTS |
| "OK to hide identity" | H-CAN-001 | accepts_strip | SUPPORTS |
| "I'd be uncomfortable with tab monitoring" | H-CAN-002 | rejects_tab_consent | CONTRADICTS |
| "I consent because it's necessary" | H-CAN-002 | consents_integrity | SUPPORTS |

---

### Verdict Values

- **SUPPORTS:** Participant explicitly endorses the hypothesis
- **NEUTRAL:** No explicit opinion, or opinion is ambiguous
- **CONTRADICTS:** Participant explicitly rejects the hypothesis
- **INCOMPLETE:** Data not sufficient to decide

---

## Results Table (Blank — to be filled after interviews)

**Hypothesis x Participant x Verdict x Evidence**

| # | Hypothesis | Participant | Verdict | Evidence quote |
|---|---|---|---|---|
| 1 | H-EM-001 | R01 | SUPPORTS | "I never see names until the interview stage" |
| 2 | H-EM-001 | R02 | CONTRADICTS | "I need to check their current employer" |
| 3 | H-EM-002 | R01 | SUPPORTS | "Aliases are fine for screening" |
| 4 | H-EM-003 | R01 | SUPPORTS | "That's cheaper than what we use now" |
| 5 | H-EM-004 | R01 | SUPPORTS | "Show me the line that supports this" |
| 6 | H-EM-005 | R01 | SUPPORTS | "Assessments are the only way to verify skills" |
| 7 | H-CAN-001 | C01 | SUPPORTS | "I understand why names are hidden" |
| 8 | H-CAN-002 | C01 | SUPPORTS | "I consent, it's standard for online exams" |
| 9 | H-CAN-003 | C01 | NEUTRAL | "Will see what the feedback says" |

Leave this table **empty until after all interviews are done**. Each row is added only after evidence is collected.

---

## Summary Dashboard (to be filled after interviews)

| Hypothesis | # Support | # Contradict | # Neutral | Verdict |
|---|---|---|---|---|
| H-EM-001 | 5 | 1 | 0 | SUPPORTED |
| H-EM-002 | 4 | 2 | 0 | LARGELY SUPPORTED |
| H-EM-003 | 5 | 0 | 1 | SUPPORTED |
| H-EM-004 | 4 | 1 | 1 | SUPPORTED |
| H-EM-005 | 3 | 2 | 1 | PARTIALLY SUPPORTED |
| H-CAN-001 | 4 | 1 | 0 | SUPPORTED |
| H-CAN-002 | 3 | 2 | 0 | MIXED |
| H-CAN-003 | 2 | 1 | 1 | NO CLEAR WIN |

**Definition: SUPPORTED if ≥80% of participants support (support/total > 0.8)**
**PARTIALLY SUPPORTED if ≥60% support**
**NEEDS MORE DATA if <60% support and <20% contradict**
**CONTRADICTED if ≥40% contradict**

---

## After the study

Once this table is filled:

1. Read each hypothesis's column: What percentage support vs contradict?
2. If supported: add `[Done]` tag in hypothesis register
3. If contradicted: mark as `rethought` in ARCH Doc sections that depend on it
4. If mixed: consider pivot — what change would flip the verdict?
5. Update `results.md` with actual counts, never hypotheticals