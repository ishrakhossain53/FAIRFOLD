# Instruments — `FAIRFOLD_Feasibility_and_Design.md` §1.3.4

Recording instruments for the validation plan. The **questions are fixed here before
collection** so the same wording is used in every session and nobody can be asked a
different question later.

Rules: read the consent form aloud first. Record answers, not conclusions. Do not lead —
the leading questions are last in each guide for that reason, and adding a sixth is the
fastest way to turn this into confirmation of the PRD.

---

## A. Candidate interview guide (20–30 min, target **8–10**)

Recent graduates and early-career job seekers in Bangladesh.

### Warm-up, not recorded as data

- Introduce yourself and the project in one sentence. What it does, what you want to learn.
- Confirm consent was given and understood. Offer to stop at any time.

### Core questions

1. Tell me about the last role you applied for. What happened after you submitted?
2. Did anyone test your skills before deciding on an interview? How?
3. Did you ever feel the outcome depended on who you knew? What made you think so?
4. Did you receive any explanation or feedback? What would you have wanted?
5. Would you trust a score that shows evidence from your own resume? What would
   make you distrust it?

### Probes — use only if the participant leaves something unexplained

- "Can you say more about that?"
- "What did you mean by that?" *(recording the participant's own words is the point)*
- "What happened next?"

⚠️ **Do not ask** "Would you like an app that ranks you fairly?" — it invites agreement
and answers nothing.

### Close

- Anything about job hunting you think we have not asked about?
- Anything about the questions themselves?

### Record for each session

`results.md` → one row per participant: participant code, date, channel, and **one answer
or count per question**, quoted where the answer was qualitative.

---

## B. Recruiter / hiring-manager interview guide (20–30 min, target **5–6**)

HR staff at SMEs and startups.

### Core questions

1. Walk me through how you screened the last role you filled. How many applicants,
   how much time?
2. How often is a candidate suggested internally? What do you do with that
   suggestion?
3. Do you test skills before interviews? Why or why not?
4. What would make you comfortable letting software rank applicants? What would
   make you refuse?
5. If you wanted to shortlist someone ranked low, would you accept having to
   record a reason?

⚠️ **Do not mention FairFold's ranking, anonymity or override features before question 4.**
Asking Q5 first tells the participant the answer to Q4, and the whole guide is about
what they would do unprompted.

### Record for each session

As above, one row per participant, one entry per question.

---

## C. Concept test of the anonymised list (target **5–8**, both groups)

Uses the wireframes in `design.md` §10.5. Tasks, in order:

1. Find a role you would apply for.
2. Explain what this score means to you.
3. Decide whether you would trust it.
4. What would you want to see to change your mind?

Show, and say nothing about until asked: the **cost estimate** and the **shortlist reveal**
(§2.18 — the name appears at shortlist, and the reveal is audited).

What to record: what they said they thought the score meant, unprompted; the point at which
they asked "is this ranked by AI?"; whether they noticed the name being hidden at first and
what they said when they did.

⚠️ **A participant who does not notice the name is hidden has still given data.** Record it
as observed. Do not prompt them to notice.

---

## D. Survey — job seekers, 5 minutes, target **30+ responses**

1. In the last 2 years, how many roles did you apply for? *(number)*
2. For how many were you given a skills test before an interview? *(number)*
3. For how many did you receive any feedback after rejection? *(number)*
4. "Who you know mattered more than what you could do" in my experience. *(1–5 agree)*
5. I would apply through a platform that hides my name during screening. *(1–5 agree)*
6. I would trust a ranking if it showed evidence from my own resume. *(1–5 agree)*

Q4–6 use a 1–5 scale. Record the **distribution**, never a single mean: "of 34 responses,
22 chose 4 or 5" is reportable; "average agreement 3.8" on n=34 is not.

⚠️ **Questions 5 and 6 measure a stated intention.** People say they want fair tools and
then do not use them. Do not report them as demand. The only evidence of demand in this
plan is the concept test and the interviews, not the survey.

---

## What each instrument is actually for

| Instrument | Question it answers | What it cannot answer |
|---|---|---|
| Candidate interviews | Does the referral problem exist as users experience it | How common it is |
| Recruiter interviews | Whether they would accept AI ranking with a human override | Whether they use it |
| Concept test | Whether the anonymised list is understood | Whether it works at scale |
| Survey | Direction and rough distribution | Demand, or causality |

**None of them measures whether the AI is fair.** No instrument here can. The bias test set
(Arch Doc §7.4) measures the *keyword pass*; nothing in this directory measures *outcomes*,
and `manifest.json` says so in `does_not_support`. Anyone citing a validation-plan number
as evidence of fairness has misread it.