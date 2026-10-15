# Candidate-Side Short Interview Guide — 20 Minutes

**Document:** `validation/candidate_interview_guide.md`  
**Date:** 2026-10-13  
**Purpose:** Guide for understanding candidate reactions to transparency features. Target: 3–5 job seekers.

---

## Session Setup

- **Duration:** 20 minutes
- **Format:** Written notes only (no recording)
- **Participants:** Job seekers (recent graduates to 3 years experience)
- **Code assignment:** Assign anonymous code (C01, C02, etc.) after session ends

---

## Warm-up (3 minutes)

> "Thanks for participating. In 20 minutes, we'll show you some screens from a hiring platform and ask what you think."

> "Tell me about the last role you applied for. What happened after you submitted your resume?"

---

## Core Questions (15 minutes)

### 1. PII Stripping Preview (W31)

> "Here's what you would see when you upload your resume to FairFold. [Show W31 — PII Stripping Preview]."

> "We remove your name, email, phone, institution, employer names, and age-revealing dates. Everything is shown as placeholders like [CANDIDATE_NAME]. What's your reaction to this?"

**Probes:**
- "Is it important for employers to see where you studied or worked?"
- "Would this make you more or less likely to apply?"
- "What concerns would you have about your resume being hidden?"

### 2. Alias Use (W37, W38, W40)

> "When employers screen your application, they see your resume as 'C-7H2X9' — a per-employer alias. [Show W37 or W41]."

> "The employer sees this alias in their list, in candidate review, and in exports — never your real name until you're shortlisted. How would you feel about this?"

**Probes:**
- "Would you be comfortable with employers not knowing your identity initially?"
- "What could go wrong with this approach?"
- "Is there anything you'd want to change about how aliases work?"

### 3. Tab-Switch Consent Screen (W34, W74)

> "Before taking a skills assessment, you'll see this consent screen. [Show W34]."

> "It explains that we record tab-switch and window-blur events for integrity, but NO video, audio, or face tracking. You must consent before starting. How does this feel?"

**Probes:**
- "Is this level of monitoring acceptable?"
- "Would you still take the assessment with this warning?"
- "What would make you NOT consent?"

### 4. Text Coaching and Resources (W33, W75)

> "After an assessment, you can try interview practice with AI feedback. [Show W33]."

> "The feedback is in a card format: it shows which STAR criteria you met, which you missed, and suggests a rewrite. For skills you're missing, we show curated learning resources. What would you expect from this?"

**Probes:**
- "Would you use this feature?"
- "Is text-only feedback helpful enough?"
- "What kind of resources would be most useful for you?"

---

## Close (2 minutes)

> "Thank you. Before we end:

> 1. Is there anything about this process that would stop you from applying through FairFold?

> 2. What would make you MORE likely to use it?"

---

## Recording fields for results.md

| Field | Example |
|---|---|
| Code | C01 |
| Q1 Reaction to stripping | "Understands why, but misses context" |
| Q2 Alias acceptance | "OK as long as shortlist reveals name" |
| Q3 Consent feel | "Acceptable, but some won't like it" |
| Q4 Coaching expectation | "Need specific rewrite suggestions" |

---

## Warning: Do not prompt about hidden identity

**Do not ask:** "Did you notice the name was hidden?"

The point is to measure whether the feature is observed. Record "no" as a valid data point. The claim is about the design, not the participant's detection ability.

---

## Sample synthetic resume demo script

> "We'll use this sample resume to show you the flow — no real data. It's for a Backend Developer role. Notice how your name, email, and phone are replaced with placeholders. The institution 'Tech University' becomes [INSTITUTION], your employer 'Alpha Corp' becomes [EMPLOYER_A]."

> "Now see how your match score shows: 78 Good match because you used Docker, but missing Kubernetes. Would this help you understand why you might or might not get the role?"