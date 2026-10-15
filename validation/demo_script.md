# Demo Script and Synthetic Data Specification

**Document:** `validation/demo_script.md`  
**Date:** 2026-10-13  
**Purpose:** Step-by-step walkthrough to show wireframes without using real PII.

---

## Demo Flow — Employer Screening

### 1. Employer Dashboard (W34, X05)

**Screen:** Dashboard shows KPI cards

> "This is your employer dashboard after you create a job. You see open roles, new applications, and screening progress."

> "Notice the AI screens used meter — you stay within your quota."

### 2. Job Overview (W37)

**Screen:** Job detail with pipeline view

> "Click on a job to see its overview. Here you see the funnel: 100 applied, 80 passed screen, 25 shortlisted, 5 interviewed."

> "Share link is visible — this is how candidates apply through your job posting."

### 3. Ranked Applications (W40, S12)

**Screen:** Table with candidates ranked by score

> "This is your ranked list. Two key things to notice:
1. **Alias Badge**: Candidates appear as 'C-7H2A1', 'C-9F2B3' — not their real names
2. **Score Chip**: Shows match score with label (Strong/Good/Partial/Low)
3. **Bias check status**: Passed or needs review
4. **Assessment gate pill**: Shows 'Pending', 'Passed', or 'Failed'"

> "Hover over the bias flag to see the issue."

### 4. Candidate Review (W41, S13)

**Screen:** Split view — left is Stripped Text View, right is Score Card

> "Click any candidate to see their details. **This is anonymized resume text** with placeholders:
- `[CANDIDATE_NAME]`
- `[INSTITUTION]`
- `[EMPLOYER_A]`

The AI generated a score of 72 (Good match). Below are the matched skills:
- Python — "Built Django REST APIs for 3 years"
- PostgreSQL — "Designed schema for 12 tables"

Missing skills:
- Kubernetes — no evidence found in the resume

**Why this score:** The AI explains its reasoning citing actual resume content."

### 5. Reveal Confirmation (W32, S63)

**Screen:** Modal confirming name reveal

> "If you want to see the candidate's real identity, click 'Reveal name'. This opens a confirmation dialog:
'You are revealing C-7H2A1 to TechCorp. This action is logged and visible only to this employer. This cannot be undone.'"

> "This action writes an audit entry. Only you can see their name after this."

### 6. Cost Estimate Modal (W34, S14)

**Screen:** Modal before processing

> "When you click 'Screen All', you see:
- Job: Backend Engineer
- Applications: 100
- Estimated cost: $0.00 (free tier)
- Method: similarity ranking + AI analysis

> "Nothing is processed until you confirm. On the free tier, this costs nothing."

---

## Demo Flow — Candidate Experience

### 1. Anonymised Resume Preview (W30, W71)

**Screen:** What the candidate sees after upload

> "After your resume uploads, you see this preview. All personal identifiers are removed:
- Name, email, phone → placeholders
- University → `[INSTITUTION]`
- Previous employer → `[EMPLOYER]`

> "This is what employers will see during screening. You confirm it looks right before submitting."

### 2. PII Stripping Preview (W31, W72)

**Screen:** Side-by-side comparison

> "Before applying, you can compare your original resume (your eyes only) with the anonymized version employers see.

> "You see exactly what was stripped and why — no surprises for either of you."

### 3. Shortlist Reveal Confirmation (W76, W32)

**Screen:** Candidate-side reveal

> "If you're shortlisted, you'll see: 'You've been shortlisted by TechCorp. They will now see your real identity. Do you confirm?'"

> "This gives you control over when your identity is revealed."

### 4. Interview Coaching (W33, W77/W78)

**Screen:** Practice interview with feedback

> "Choose a job role, get a practice question, type your answer, and click 'Get feedback'.

> "The AI analyzes your answer for:
- Structure (STAR format)
- Content (specifics, metrics)
- Gaps (missing context)

> "Then suggests a rewrite: 'Instead of \"improved speed\", say \"reduced query time from 5s to 1.2s, 76% faster\".'"

---

## Synthetic Resume Dataset

Use the following synthetic resumes in the demo files (`validation/synthetic_resumes/`).

### Resume 1: Backend Developer

```markdown
[CANDIDATE_NAME]
Backend Developer | Remote

[CND_EMAIL]

EXPERIENCE

[EMPLOYER_A] — Senior Backend Developer (2020–2023)
- Built RESTful APIs with Python/Django serving 10K+ daily users
- Designed and optimized PostgreSQL schemas, reducing query time by 40%
- Led team of 3 junior developers through code reviews and pairing
- Implemented Redis caching layer that improved response times by 60%

[EMPLOYER_B] — Software Engineer (2018–2020)
- Developed microservices in Go for payment processing
- Reduced payment failure rate from 5.2% to 1.8% through improved validation
- Automated deployment pipeline saving 10 hours/week in ops time

SKILLS
Python, Django, PostgreSQL, Redis, Go, AWS, Docker

PROJECTS
- Open-source library for JWT authentication: 500+ stars on GitHub
- Personal blog on API design patterns: read by 2K developers/month

[INSTITUTION] — BSc Computer Science (2014–2018)
```

### Resume 2: Frontend Developer

```markdown
[CANDIDATE_NAME]
Frontend Engineer | Dhaka

[CND_EMAIL]

EXPERIENCE

[EMPLOYER_C] — Frontend Lead (2021–Present)
- Built responsive React applications with TypeScript for 50K+ users
- Implemented component library adopted by 3 product teams
- Reduced bundle size by 35% through code splitting and tree-shaking
- Mentored 4 junior frontend developers

[EMPLOYER_A] — Junior Frontend Developer (2019–2021)
- Developed UI components with React and Vue.js
- Collaborated with UX designers to implement pixel-perfect designs
- Improved page load time from 4.2s to 1.8s through optimization

SKILLS
React, TypeScript, Vue.js, HTML/CSS, Jest, Cypress

CERTIFICATIONS
- AWS Certified Developer (2022)
- Google Analytics Individual Qualification (2021)

[INSTITUTION] — BSc Software Engineering (2015–2019)
```

### Resume 3: Data Analyst

```markdown
[CANDIDATE_NAME]
Data Analyst | Chittagong

[CND_EMAIL]

EXPERIENCE

[EMPLOYER_B] — Data Analytics Lead (2020–Present)
- Built dashboards in Metabase used by 50+ stakeholders daily
- Automated weekly reporting, saving 15 hours of manual work
- Cleaned data pipelines, reducing data quality issues by 70%
- Trained 8 new analysts on SQL best practices

[EMPLOYER_C] — Junior Data Analyst (2018–2020)
- Created Excel models for financial forecasting
- Visualized data for monthly leadership reports
- Improved data entry accuracy by implementing validation rules

SKILLS
SQL, Python (pandas, numpy), Excel, Metabase, Tableau

PROJECTS
- COVID-19 dashboard for local health department (public, open data)
- University enrollment analysis tool (internal)

[INSTITUTION] — BSc Mathematics, MSc Statistics (2014–2018)
```

---

## Wireframes to Show (Employer side)

1. **W30** — Anonymised Resume Preview (candidate view)
2. **W37** — Employer Candidate List (alias badge visible)
3. **W40** — Ranked Applications (score chips, bias status)
4. **W41** — Candidate Review (stripped text + score card)
5. **W32** — Reveal Confirmation modal
6. **W34** — Assessment Consent (integrity panel)
7. **W39** — Assessment Consent (employer side)
8. **W14** — Cost Estimate Modal

## Wireframes to Show (Candidate side)

1. **W30** — Anonymised Resume Preview
2. **W31** — PII Stripping Preview
3. **W71** — Application flow (step 3)
4. **W74** — Assessment Consent
5. **W33** — Interview Practice Session
6. **W33** — Interview Practice Feedback
7. **W76** — Shortlist Reveal Confirmation

---

## Demo Notes

- **Never show real names** — always use `[CANDIDATE_NAME]` or the synthetic names above
- **Never show real emails** — use `[CND_EMAIL]` or `[EMAIL]`
- **Never show real companies** — use `[EMPLOYER_A]`, `[EMPLOYER_B]`, etc.
- **Explain placeholders:** "This is how the system protects your privacy"
- **Point out the AI badge:** ✦ "Generated by AI" appears on AI-written content
- **Point out bias flag:** ⚑ appears when rationale needs review

---

## Questions to ask during demo

> "What would make this view more useful for your screening process?"

> "Is there anything here that would cause you to hesitate?"

> "How does this compare to what you currently use?"

> "What would you change about how the alias system works?"

> "Is the cost estimate clear, or would you want more detail?"