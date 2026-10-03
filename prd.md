# FAIRFOLD — Product Requirements Document (PRD)

**Product:** FairFold — AI-Powered, Explainable Recruitment Platform
**Document type:** Product Requirements Document
**Version:** 1.2 (52 FRs · all §19.2 items resolved · §1.2 real-world evidence · §3.4 requirement collection method)
**Date:** October 2026
**Team:** Sardar Shihab (Full-Stack), Arnob Biswas Antu (Frontend), Ishrak Hossain (Backend & AI), Mohammad Abdul Ahad (UI/UX), Fahad Haque (UI/UX)
**Status:** Ready for review

> **Source documents consolidated here**
> | Short name | File | Contributes |
> |---|---|---|
> | Complete Doc | `FAIRFOLD_Complete_Project_Document.md` | Product vision, market, AI strategy, security, roadmap, pricing |
> | Arch Doc | `FAIRFOLD_Project_Architecture_and_Requirements.md` | ADRs, 52 FRs, 50 NFRs, schema, ops, risk register |
> | Feasibility Doc | `FAIRFOLD_Feasibility_and_Design.md` | Feasibility, user stories, diagrams, data dictionary, nav, a11y |
>
> Requirement IDs (`REQ-FR-###`, `REQ-NFR-###`, `REQ-SEC-###`, `REQ-COM-###`) are taken verbatim from the Arch Doc. Conflicts between source documents are listed in [Section 19](#19-open-questions-and-source-document-inconsistencies) rather than silently resolved.
>
> **Update 2026-10-03 (a):** `REQ-FR-042` and `REQ-FR-043`, marked **(proposed)** below, were approved by the team and promoted into the Arch Doc §4.1 as a new *Job Discovery & Messaging* group.
>
> **Update 2026-10-03 (b):** `REQ-FR-044`–`REQ-FR-050` were added from the page-level design audit (§7.4, §7.4b), taking the count from 43 to **50**.
>
> **Update 2026-10-03 (c):** `REQ-FR-051` and `REQ-FR-052` were approved and added (§7.3), taking the count from 50 to **52**. `REQ-FR-029` was amended and `REQ-FR-035` extended (§7.3). The Arch Doc, this header and [§19.2 item 3](#19-open-questions-and-source-document-inconsistencies) now all state the same number.
>
> The acceptance criteria in this PRD remain the source of intent; the Arch Doc wording is authoritative.

---

## Table of Contents

1. [Product Overview](#1-product-overview)
2. [Goals, Non-Goals and Success Metrics](#2-goals-non-goals-and-success-metrics)
3. [Users and Personas](#3-users-and-personas)
4. [Market Context and Positioning](#4-market-context-and-positioning)
5. [Scope and Release Plan](#5-scope-and-release-plan)
6. [Core User Flows](#6-core-user-flows)
7. [Functional Requirements](#7-functional-requirements)
8. [AI Requirements](#8-ai-requirements)
9. [Non-Functional Requirements](#9-non-functional-requirements)
10. [Security, Privacy and Compliance](#10-security-privacy-and-compliance)
11. [Data Model](#11-data-model)
12. [System Architecture and Tech Stack](#12-system-architecture-and-tech-stack)
13. [API Surface](#13-api-surface)
14. [UX Requirements and Information Architecture](#14-ux-requirements-and-information-architecture)
15. [Monetization](#15-monetization)
16. [Operations and Delivery](#16-operations-and-delivery)
17. [Roadmap, Team and Methodology](#17-roadmap-team-and-methodology)
18. [Risks, Assumptions and Dependencies](#18-risks-assumptions-and-dependencies)
19. [Open Questions and Source Document Inconsistencies](#19-open-questions-and-source-document-inconsistencies)
20. [Release Criteria](#20-release-criteria)
21. [Appendix: Glossary and Traceability](#21-appendix-glossary-and-traceability)

---

## 1. Product Overview

### 1.1 Summary

FairFold is a web-based recruitment platform with two portals:

- **Candidate Portal** — profile and resume management, skill assessments, AI interview coaching, and **AI-Powered Professional Journey Mapping** (a dynamic career timeline with skill evolution and per-job storytelling).
- **Employer Portal** — job posting, AI-assisted resume screening, explainable ranking, structured interview packs, interview scheduling and feedback, messaging, and analytics.

Personal data is stripped from resumes before any AI model sees them. Every AI decision is stored with an evidence-cited rationale and an immutable audit entry. A human always makes the final hiring decision.

### 1.2 Problem Statement

Hiring fails at the screening stage for two structural reasons:

1. **Screening inherits bias.** Human and automated screeners carry unconscious bias, and most commercial AI tools are black boxes that cannot explain a rejection to a candidate or an auditor.
2. **Candidates cannot show real capability.** A fixed resume format hides skill growth, impact, and informal learning.

Existing tools also exclude the SMB and emerging-market segment on price and complexity (for example Eightfold at $200K+/year and HireVue at $35K+/year; both take months to implement).

**This is not a hypothetical problem.** Four documented incidents, each of which
would have been reported by a user of this product:

1. **Amazon's recruiting engine (2014–2017).** Amazon built an internal tool that
   scored applicants from one to five stars, trained on roughly ten years of past
   resumes — most of them from men. It learned to downgrade resumes containing the
   word "women's" and resumes from two all-women's colleges. Engineers removed those
   specific terms but could not be confident the system would not find other proxies,
   so the project was shut down. *Source: Reuters, J. Dastin, 10 Oct 2018.* The lesson
   is that **"AI removes bias" is false by default** — a model trained on past hiring
   decisions reproduces the past, and deleting a few obvious words does not fix proxy
   bias.
2. **EEOC v. iTutorGroup** (settled Aug 2023, **$365,000** — the EEOC's first
   AI-hiring discrimination settlement). Application software was programmed to
   auto-reject women aged 55+ and men aged 60+, screening out more than 200
   applicants. The lesson is that **a hard filter discriminates as easily as a
   model** — no LLM was involved. This is the origin of Gap G3 below.
3. **HireVue** removed facial-expression analysis in January 2021 after bias and
   disability criticism. Supports the non-goal in §2.3.
4. **Mobley v. Workday** (N.D. Cal., filed 2023) — an age-discrimination collective
   action in which the *vendor*, not only the employers, was treated as potentially
   liable as an agent of the customers using its screening tools. Still ongoing;
   **re-verify before citing publicly.**

**Bangladesh context.** Peer-reviewed work on graduate employability here identifies
the same structural issues: Hossain & Arefin (2025, *EJCEEL* 3(2), 55–74) list
restricted professional connections among the obstacles to graduate employment,
alongside curriculum mismatch and language skills; Zaman (2025) reports unequal
network access and skills gaps from 21 structured interviews; a mixed-methods study
(n = 1,320 survey responses, 32 interviews) reports substantial technical and digital
skills mismatches.

> These sources establish that *network access and skill mismatch are recognised
> problems*. They do **not** measure how common internal lobbying in interview
> selection is. **No prevalence figure is stated anywhere in this document**, and none
> may be until the validation plan in [§3.4](#34-requirement-collection-method) has
> actually been run and its real numbers recorded.

**How FairFold differs from the Amazon case,** which is the point of recording it:
the system is not trained on historical hire/reject outcomes at all — it compares a
job description to anonymised resume content, so it never sees the outcome data that
carried the bias; every score carries the resume text that justifies it; a bias audit
runs on every rationale; and a human always decides.

**Action this triggers.** The Phase 2 versioned bias test set must include
Amazon-style proxy cases — women's-college names, "women's society captain",
gendered club roles. PII stripping removes names, emails and phone numbers and **none
of that text**, which is why stripping names is not sufficient.

Full detail and sources: Feasibility Doc §1.2.1 in
[`FAIRFOLD_Feasibility_and_Design.md`](FAIRFOLD_Feasibility_and_Design.md).

### 1.3 Solution

| Pillar | What the product does |
|---|---|
| **Privacy-first AI** | Names, emails, phones, locations and similar identifiers are removed (regex + spaCy NER) before any external AI call. |
| **Explainable ranking** | Every score carries an evidence-cited rationale (matched skills with resume evidence, missing skills, reasoning). Candidates can see their own breakdown. |
| **Bias audit trail** | Each rationale is checked for biased language; every AI action writes an append-only audit entry. |
| **Journey Mapping** | Resume becomes an interactive career timeline with skill evolution and narrative tailored to a target job. None of the eleven systems analysed in `prd.md` §4 offers this; Applied and Vervoe overlap partially, so it is **less unique than the Complete Doc originally claimed**. |
| **Accessible pricing** | Free-tier AI via OpenRouter, local embeddings, offline fallbacks. $0 AI cost on the free tier; transparent paid tiers. |

### 1.4 Differentiators vs. Market

| Competitor weakness | FairFold answer |
|---|---|
| Black-box scoring (Eightfold) | Evidence-cited rationale visible to employer and candidate |
| Facial analysis backlash, candidate refusal (HireVue) | Text-based AI only; no facial or emotion analysis |
| Keyword matching marketed as AI (SeekOut) | Semantic embeddings + LLM analysis on top candidates |
| Full profiles sent to third-party clouds | PII stripped before any AI call |
| Enterprise-only pricing | Free tier; $100–$5,000/mo employer plans |
| No candidate-side tooling in open-source ATS projects | Assessments, coaching and journey mapping for candidates |

---

## 2. Goals, Non-Goals and Success Metrics

### 2.1 Product Objectives

| # | Objective | Measure | Source |
|---|---|---|---|
| O1 | No PII reaches an AI provider | 100% of AI payloads pass the PII filter | REQ-SEC-002 |
| O2 | Every ranking is explainable | 100% of scores carry evidence-cited rationale | REQ-FR-030 |
| O3 | Screening bias is auditable | Every AI action has an immutable audit entry | REQ-COM-008 |
| O4 | Cost does not block adoption | $0.00 AI cost on the free tier | REQ-FR-028 |
| O5 | Candidates can prove skill, not just tenure | Assessments and journey map shipped | REQ-FR-016, FR-019 |

### 2.2 Success Metrics

| Metric | Target |
|---|---|
| Time-to-screen | < 5 minutes for 100 applications |
| AI cost per screening batch | $0.00 on free tier |
| Candidate satisfaction (NPS survey, from Phase 3) | > 80% would recommend |
| Bias audit pass rate | 100% of displayed rationales pass the audit |
| Data breach incidents | 0 |
| New employer onboarding time | < 1 week (self-serve) |
| SMB accessibility | Entry point under $100/month; free tier available |
| Platform uptime | 99.9% |
| Test coverage | ≥ 80% |

### 2.3 Non-Goals (Out of Scope)

From the Arch Doc §1.1 and Feasibility Doc §1.5:

- Native mobile apps (PWA is the Phase 4/5 path)
- Real-time video interview recording or hosting (Phase 3 offers async coaching only)
- Third-party profile scraping (for example LinkedIn)
- On-premises deployment for customers (Phase 5 Enterprise feature)
- Payroll and background checks
- Facial, voice or emotion analysis of candidates
- Fully automated hiring decisions (AI is advisory only)

---

## 3. Users and Personas

### 3.1 User Groups

| Group | Role/Django group | Primary need |
|---|---|---|
| Job seeker | `candidate` | Show capability beyond a rigid resume; understand why they were ranked |
| Recruiter / HR | `employer_hr` | Cut screening time and bias risk at low cost |
| Hiring manager | `employer_manager` | Review shortlisted candidates and analytics |
| Interviewer | `interviewer` | Structured questions and scoring rubric |
| Platform administrator | `admin` | Governance, audit, GDPR operations |
| Guest | `guest` | Browse public jobs, register |

### 3.2 Persona Sketches

| Persona | Context | Pain | What success looks like |
|---|---|---|---|
| **Candidate (early/mid-career, emerging market)** | Strong self-taught skills, thin resume | Rejected by keyword filters; gets no feedback | Uploads resume, sees a career timeline, takes an assessment, understands their score |
| **SMB recruiter** | One HR person, 100+ applicants per role, spreadsheets and email | No time, no budget for enterprise ATS | Clicks "Screen All", sees $0.00 cost, gets a ranked and explained shortlist in minutes |
| **Compliance-aware employer** | Hiring in or from the EU | Fear of regulatory exposure from black-box AI | Audit trail, human-in-the-loop, GDPR export/delete |
| **Admin** | Platform operator | Needs to investigate incidents and honor data requests | Searchable audit log, user management, export/delete workflows |

### 3.3 Initial Market

Beachhead: **Bangladesh and similar emerging markets**, where hiring is still manual and enterprise tools are inaccessible. Expansion: SMBs in developed markets priced out of Eightfold, HireVue and Phenom. (Risk RSK-008 covers the chance that this market does not convert.)

### 3.4 Requirement collection method

**Filled in 2026-10-03**, closing §19.1 item 1. The method is stated here in full;
the working detail — guides, survey questions and the traceability table — is in
Feasibility Doc §1.3.

**Every claim is tagged**, because §19.1 asked for exactly this: *"State what was
actually done; do not claim research that was not conducted."*

| Tag | Meaning |
|---|---|
| **[Done]** | It happened; the Product Owner can vouch for it. |
| **[Illustrative]** | A scenario written to explain a requirement. Not a research finding; must never be quoted as data. |
| **[Planned]** | A validation step that has **not** been run. |

**What was done [Done].** Requirements originated from the Product Owner's
first-hand experience of a hiring process in which interview selection was influenced
by internal lobbying and **no skills check was applied before shortlisting** —
around mid-2026, applying to a public university for a Cybersecurity Engineer role.
The same experience was shared by friends who later formed the project team, and
corroborated independently by a university senior. The team converted these
experiences into problem statements and then into requirements, using
problem-owner elicitation, group discussion and scenario-based elicitation. No
employer and no individual is named anywhere in this document.

**What was not done [Planned].** No formal recruiter interviews, no survey, no field
observation. Employer-side needs are *inferred* from the candidate-side view and from
published market analysis; they have **not** been validated with employers.

**Traceability.** Six pain points from that experience map onto objectives and
requirements that already exist:

| # | Pain point | Requirement | Covered? |
|---|---|---|---|
| P1 | Decided by who you knew, not what you could do | REQ-FR-011, REQ-FR-029 | Yes |
| P2 | No skills check before the interview | REQ-FR-019/020, REQ-FR-030 | Partly → **REQ-FR-051** (Gap G1) |
| P3 | No explanation, no feedback | REQ-FR-024, REQ-FR-030 | Yes |
| P4 | Nobody could challenge the outcome | REQ-COM-008, REQ-FR-039 | Yes |
| P5 | The selection could simply be **bypassed** | — | No → **REQ-FR-052** (Gap G2) |
| P6 | Thin resume, strong self-taught skills | REQ-FR-016–018 | Yes |

P5 is the one that mattered most and was completely unaddressed: anonymised ranking
is worthless if the ranking can be quietly ignored. P2 was partly addressed — the
assessments were candidate-initiated, so an employer could still shortlist on a
resume with no skill evidence at all.

**Validation plan — [Planned], not run.** Fixed now so no result can be claimed
before it is collected: 8–10 candidate interviews, 5–6 recruiter interviews, a
30+ response survey, and 5–8 concept tests against the wireframes. Full guides and
survey items are in Feasibility Doc §1.3.4. When it runs, the real counts replace
this section's honesty disclaimer and nothing else changes.

**The rest of the requirements.** Not everything came from a user, and saying so is
the point. REQ-FR-001–008 are security best practice; 009–024 come from competitor
gaps and are **not validated with candidates**; 025–036 come from competitor
shortfalls and are **not validated with recruiters**; 037–041 are legal requirements
(GDPR, EU AI Act); 042–052 come from the traceability audit and gaps G1–G3.

---

## 4. Market Context and Positioning

Eleven systems were analyzed (Complete Doc §2).

| Category | Systems | Key lesson |
|---|---|---|
| Enterprise | HireVue, Eightfold AI, SeekOut, Paradox, LinkedIn Recruiter, Manatal, Workable, Phenom, HackerEarth | Powerful but expensive, opaque, or single-slice |
| Open source | CandiSift, OpenCATS, candidacy, SkillAI, Vekt, others | CandiSift is the closest comparator (PII stripping, cost estimate before processing, evidence-cited breakdowns, bias-audit endpoint) but has no candidate portal and depends on paid Claude |

**Four gaps FairFold fills:** (1) Journey Mapping, (2) explainable and candidate-visible AI, (3) free-tier AI for screening, (4) powerful candidate-side tools at free or low cost.

### 4.1 Does something like this already exist?

**Yes, in pieces.** A second pass over the market on 2026-10-03, grouped by the job
each product does rather than by vendor:

| Category | Examples | What they do | Gap vs. FairFold |
|---|---|---|---|
| Blind / anonymised hiring | Applied, Vervoe, MeVitae, Pinpoint, GapJumpers | Hide identity during review; Applied replaces the CV sift with job-relevant questions and work samples reviewed anonymously | Priced and designed for organisations, not job seekers. No candidate-side career tooling. Little emerging-market focus |
| Skills assessment | TestGorilla, HackerRank, Codility, CodeSignal, Vervoe | Test skills against large libraries; TestGorilla has a free plan, paid plans from ~$135/month | Assess skills but do not rank anonymised resumes, and show no evidence-cited rationale to the candidate |
| AI video / game assessment | HireVue, Pymetrics (now Harver) | Enterprise screening at scale | Opaque and expensive; HireVue's earlier facial analysis drew sustained criticism |
| Enterprise AI sourcing | Eightfold, SeekOut, Phenom | Talent intelligence and pipelines | Enterprise pricing — $200K+/year for Eightfold. Priced the SMB segment out entirely |
| Open-source ATS | CandiSift, OpenCATS | PII stripping, evidence-cited breakdowns (CandiSift) | No candidate portal; depends on a paid LLM |

### 4.2 How FairFold is different — and where "better" must be proven

The status column matters more than the claim. Three of these seven are designs we
have made, not results we have produced.

| Dimension | Typical competitor | FairFold | Status of the claim |
|---|---|---|---|
| **Who it serves** | Employer only | **Both sides** — the candidate sees their own score, rationale, journey map and coaching | **Designed** |
| **Bias handling** | Marketed as "bias-free" | PII stripped before any AI call; bias audit on every rationale; a human always decides; immutable audit | **Designed — not yet measured** |
| **Explainability** | Score only, or a black box | Evidence-cited rationale shown to employer *and* candidate; "no evidence found" is an explicit outcome | **Designed** — REQ-FR-030 |
| **Cost** | Quote-based or enterprise | $0 AI cost on the free tier via local embeddings, free LLMs and an offline fallback | **Assumption** — depends on free-tier availability (RSK-001) |
| **Skills evidence** | A separate tool | Assessments and the Journey Map in one flow, with employer-required assessments (REQ-FR-051) | **Partly designed** — Gap G1 |
| **Market** | US/EU enterprise | Bangladesh and emerging-market SMEs first | **Unvalidated** — RSK-008 |
| **Compliance** | Varies | Audit trail, GDPR export/delete, EU AI Act human oversight | **Designed — verification in Phase 4** |

> **Approved wording, until measured.** The evidence supports *different* today.
> *"Better"* is a claim about outcomes and has to be earned against measured disparity
> data, which does not exist yet:
>
> *FairFold is designed to make screening explainable and auditable for both
> employers and candidates, at a price small employers can afford. Whether it reduces
> biased outcomes will be measured through the bias audit and disparity analysis
> described in §8.7.*
>
> **"Bias-free" is no longer the product subtitle.** It was removed from every document
> on 2026-10-03. No disparity measurement exists, so the claim was not defensible; the
> subtitle is now **"AI-Powered, Explainable Recruitment Platform"**, which is a
> statement about what the product *does* — every score carries cited evidence and
> every action writes an audit entry — rather than about what it *achieves*.
> "Bias-free" now appears in these documents only where it is attributed to a
> competitor's marketing, or labelled explicitly as the aspiration §8.7 would have to
> earn. **Do not reintroduce it into the subtitle or into marketing copy before the
> disparity analysis has run.**

### 4.3 ✅ Name decided — FairFold. 🟡 Trademark clearance still outstanding.

**Decided 2026-10-03: the product is FairFold.** The previous working name,
"Match Minds", was found to be contested and was abandoned. This section is kept
rather than deleted, because the reason for the decision is the useful part.

**Why the old name was dropped.** Checked 2026-10-03 by web search and DNS resolution:

| Finding | Evidence |
|---|---|
| **MatchMindAI** (matchmindai.com) already markets an AI-powered recruitment platform matching candidates to jobs | Search result; domain resolves to a live host |
| **"MatchMinds"** is *also* used by an AI-powered recruitment platform | Public post describing itself as "an AI-powered recruitment platform and the next frontier in hiring" |
| **"MatchMinds"** is additionally used by an unrelated Android football-prediction app, and by an unrelated teammate-recommendation system | Two further commercial uses of the same string |

The old name was contested in **three** unrelated commercial spaces, one of them
recruitment, and "Match Mind" is descriptive of what every ATS does — which makes it
hard to register as a word mark and hard to defend even once registered.

**Why FairFold.** "Fair" states the intent; "Fold" carries the résumé being opened
and read, which is the moment the product acts on. It is short, pronounceable in
English and Bangla, and it names the *artefact* the platform intervenes on rather
than the feature. Screening on the same day found **no living commercial use** of the
string, and `fairfold.com` and `fairfold.ai` returned no DNS record.

**What changed.** The four `MATCH_MINDS_*.md` files were renamed to `FAIRFOLD_*.md`,
and every internal link repaired. A web search for the old name now returns nothing
about this project.

**🟡 What is still open.** **RSK-011** remains on the register, downgraded from
High/High to **Medium/Low**, and it is now a legal task rather than a naming one:

1. ✅ **Domain — owned.** The team holds a domain and will run on a **temporary** one
   first, moving to the primary at launch.
2. ⬜ **Commission a formal trademark search** in Bangladesh and every target export
   market. This has **not** been done. A web search, a DNS lookup and a domain
   registration are **not** a clearance — buying a domain does not confer the right to
   use the name in commerce.
3. ⬜ **File the word mark** in the relevant classes (42 for software/SaaS, 35 for
   recruitment services) in each market.

**Two things the temporary-domain plan implies.** Every host-dependent value —
`ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, the Stripe webhook URL, the Sentry DSN,
absolute URLs in emails — must live in environment variables so the switch is a config
change and not a debugging session. And no SEO, email-sender reputation or social handle
should be built against the temporary host: verification emails establish SPF/DKIM for
*that* domain, and candidate links containing it will not survive the move.

**Two caveats that survive the decision.** "No DNS record" is not proof of
availability — a parked or newly-registered domain may simply have no A record yet.
And nothing here is legal advice: only a trademark attorney in each jurisdiction can
say whether FairFold is registrable and enforceable there.

---

## 5. Scope and Release Plan

### 5.1 Phases

| Phase | Weeks | Theme | Deliverable |
|---|---|---|---|
| **1 — Foundation** | 1–3 | Auth, profiles, jobs, applications (no AI) | `docker-compose up` runs the full stack; employer posts a job, candidate applies with a resume, employer sees it |
| **2 — AI Integration** | 4–6 | PII stripping, screening, rationale, bias audit | "Screen All" → $0.00 cost estimate → ranked candidates with evidence-cited rationale |
| **3 — Candidate AI** | 7–9 | Assessments, coaching, journey mapping | Candidate sees timeline, takes an assessment, gets coaching, sees match scores |
| **4 — Hardening** | 10–12 | Security, GDPR, monitoring, CI/CD | Security checks passed, production deploy on a single VPS |
| **5 — Advanced** | 13+ | i18n, Stripe billing, PWA, WebSockets, skill ontology | Optional; not required for MVP |

### 5.2 MVP Definition

**MVP = Phases 1–3 (~9 weeks)**, with Phase 4 hardening required before public launch (~12 weeks total). MVP means:

- Employer can post a job.
- Candidates can apply with a resume.
- AI screens and ranks applicants with explainable scores on the free tier.
- Candidates see their match scores and get interview coaching.

### 5.3 MoSCoW Summary (from user stories)

52 user stories, 217 story points: **30 Must, 17 Should, 5 Could**. See [Section 7](#7-functional-requirements) for the requirement-level priorities.

---

## 6. Core User Flows

### 6.1 Candidate Flow

```
Register (consent captured) → verify email → onboarding (upload resume or build profile)
   → PII stripped, text extracted, embedding generated
   → Dashboard: skills · Journey Map · assessments · coaching · applications
   → Browse/search jobs → Apply → match score + rationale visible
   → Interview coaching for that role (AI-generated Q pack)
   → Status updates: applied → screened → shortlisted → interview → offered/hired/rejected
```

### 6.2 Employer Flow

```
Register (MFA required for HR admin) → company profile
   → Create job (AI-suggested screening questions) → activate / share link
   → Applications arrive
   → "Screen All" → cost estimate ($0.00 on free tier) → explicit confirmation
   → Celery pipeline: hard filter → pgvector rank → LLM analysis of top N → bias audit
   → Ranked list; open any candidate for evidence-cited rationale + bias audit status
   → Shortlist / reject (human decision) → generate interview pack → schedule
   → Interviewers submit structured scorecards → offer (AI-drafted, editable)
   → Analytics: time-to-hire, drop-off, source, AI accuracy
```

### 6.3 AI Screening Pipeline (control flow)```
Employer clicks "Screen All"
  → quota check (no quota → show upgrade option, stop)
  → cost estimate shown → employer confirms (else nothing is written)
  → Celery task screen_applications(job_id)
      for each application:
        Stage 1  Hard filter (experience level, min years, location, remote)  [free, deterministic]
                 read jobs.screening_config + screening_config_version
                 fail → status = not_matched, not_matched_reason = <rule that fired>,
                        filter_rules_version = version that judged it  + audit entry
                        → stays LISTED and reviewable, never hidden, never "rejected"
        Stage 2  Ensure resume + job embeddings exist
        Stage 3  pgvector cosine ranking (384-dim)                    [free, local]
        Stage 4  Top N only: PII strip → LLM analysis (OpenRouter, offline fallback)
                 → evidence-cited rationale → bias audit
                 fail bias audit → flag for human review, exclude from auto-shortlist
        Stage 5  Assessment gate (REQ-FR-051) — no required assessment on the job
                 → assessment_gate_status = not_required
                 required and no completed attempt  → pending
                 required and attempt >= min_score → passed, else failed
        Persist match_score, rationale, ai_model_used, screened_at
        Write immutable AuditLogEntry (application.screened)
        Notify candidate that a score is available
  → Ranked list ready
```

**Employer decision step (REQ-FR-052).** Shortlisting or rejecting is always a human
action. When the decision goes **against** the ranking — shortlisting someone below
the cut-off, or rejecting someone above it — the system requires a written reason,
records `decision_override` / `decision_override_reason` / `decided_by`, and writes an
`ai_decision`-class audit entry retained with the application. It does **not** block
the decision: the employer remains the decision-maker (§8.1). What it does is make an
otherwise invisible decision visible, attributable and countable in the override-rate
chart (REQ-FR-035).

**Shortlist is blocked while the assessment gate is open.** A candidate with
`assessment_gate_status = 'pending'` cannot be shortlisted on their score alone; the
action is disabled and says why. A failed gate blocks it for the same reason. A job
with no required assessment is unchanged.

Cost property: the LLM sees only the top 5–10 candidates, so 100 applications cost roughly 5–10 AI calls, well inside the free tier.

---

## 7. Functional Requirements

Priority: **H** = High, **M** = Medium, **L** = Low. Phase = first phase in which it ships. Full Given/When/Then acceptance criteria are in Arch Doc §4.1; key behavior is summarized here.

### 7.1 Authentication and User Management

| ID | Requirement | Pri | Phase |
|---|---|---|---|
| REQ-FR-001 | Register with email, password, role; verification email sent; `email_verified=False` until verified | H | 1 |
| REQ-FR-002 | Login returns JWT access (15 min) + refresh (7 days); failed-attempt counter resets | H | 1 |
| REQ-FR-003 | Lock account for 15 min after 5 consecutive failed logins | H | 1 |
| REQ-FR-004 | Password reset via emailed link with 1-hour expiry | H | 1 |
| REQ-FR-005 | Enable TOTP MFA (secret generated, QR shown, secret stored encrypted) | M | 4 |
| REQ-FR-006 | Verify TOTP code to activate MFA | M | 4 |
| REQ-FR-007 | Refresh access token with a valid refresh token | H | 1 |
| REQ-FR-008 | Logout blacklists the refresh token; later use returns 401 | M | 1 |

### 7.2 Candidate Portal

| ID | Requirement | Pri | Phase |
|---|---|---|---|
| REQ-FR-009 | Create candidate profile (title, bio, location, remote_ok) | H | 1 |
| REQ-FR-010 | Resume upload straight from browser to S3 via presigned URL; Django stores only the key | H | 1 |
| REQ-FR-011 | Strip PII from resume (name, email, phone, location → placeholders); store anonymized text; audit entry | H | 2 |
| REQ-FR-012 | Extract resume text with pdfplumber; store anonymized | H | 2 |
| REQ-FR-013 | Generate 384-dim resume embedding (sentence-transformers) into pgvector | H | 2 |
| REQ-FR-014 | Add/edit/delete skills with level and source | H | 1 |
| REQ-FR-015 | Map skill aliases ("JS", "JavaScript") to one canonical skill | M | 3 |
| REQ-FR-016 | Journey Mapping: interactive career timeline (Chart.js) from parsed resume | H | 3 |
| REQ-FR-017 | Journey Mapping: skill-evolution chart showing when each skill was gained | M | 3 |
| REQ-FR-018 | Journey Mapping: AI narrative tailored to a specific job application | M | 3 |
| REQ-FR-019 | Take timed assessments; answers saved incrementally; auto-submit on timeout | M | 3 |
| REQ-FR-020 | Auto-score assessments; store score in `AssessmentAttempt` | M | 3 |
| REQ-FR-021 | Interview coaching: AI feedback on pasted practice answers (structure, content, gaps) | M | 3 |
| REQ-FR-022 | Apply to an active job; status `applied`; candidate and employer notified; one application per job per candidate | H | 1 |
| REQ-FR-023 | Track application status; notify on change | H | 1 |
| REQ-FR-024 | View match score (0–100) with evidence-cited rationale | H | 2–3 |
| **REQ-FR-042** | **Job browse and search**: keyword search, filters (location, remote, experience level), public job board, job detail page. *Was proposed here to close GAP-1 (the capability appeared in user stories, use cases and wireframes but had no FR); promoted into the Arch Doc §4.1 on 2026-10-03.* | H | 1 |

### 7.3 Employer Portal

| ID | Requirement | Pri | Phase |
|---|---|---|---|
| REQ-FR-025 | Create job; AI auto-suggests screening questions | H | 1 (suggestions: 2) |
| REQ-FR-026 | Edit draft job; audit entry | H | 1 |
| REQ-FR-027 | Activate job; visible to candidates | H | 1 |
| REQ-FR-028 | "Screen All": show cost estimate ($0.00 on free tier), require explicit confirmation, queue Celery batch | H | 2 |
| REQ-FR-029 | Ranked application list with scores; click through for rationale | H | 2 |
| REQ-FR-030 | Evidence-cited rationale: resume text per claim, missing skills listed, bias audit status shown | H | 2 |
| REQ-FR-031 | Generate AI interview pack (structured questions + scoring rubric), linked to the job | M | 3 |
| REQ-FR-032 | Schedule interview; invite sent; video URL generated; candidate notified | M | 3 |
| REQ-FR-033 | Interviewers submit structured scores, comments and recommendation | M | 3 |
| REQ-FR-034 | AI-drafted, editable offer letter | L | 5 |
| REQ-FR-035 | Analytics: time-to-hire, source of hire, drop-off, AI accuracy, **override rate** and `not_matched` review counts | M | 4 |
| REQ-FR-036 | Shareable job link and career-page embed code | M | 3 |
| **REQ-FR-043** | **Candidate–employer messaging**: send/receive messages scoped to an application, read state, in-app notification. *Was proposed here to close GAP-2 (the `Message` model and use case existed, and the Complete Doc lists real-time candidate communication as a feature, but no FR did); promoted into the Arch Doc §4.1 on 2026-10-03.* | M | 3 |
| **REQ-FR-051** | **Employer-required skill assessment**: attach an assessment to a job as a required step, with an optional pass mark. Shortlist is blocked while `assessment_gate_status` is `pending` or `failed`. Closes **Gap G1** — pain point P2, *"no skills check before the interview"*. Approved 2026-10-03. | H | 3 |
| **REQ-FR-052** | **Override visibility and record**: shortlisting below the employer's cut-off, or rejecting above it, requires a written reason and writes an `ai_decision`-class audit entry. Adds **override rate** to REQ-FR-035. Closes **Gap G2** — pain point P5, the selection could be bypassed. Approved 2026-10-03. | H | 2–3 |
| **REQ-FR-029** *(amended)* | **Reviewable hard filters**: `not_matched` candidates stay listed with the rule that fired and can be pulled into review; each application stores the `filter_rules_version` that judged it. Closes **Gap G3** — motivated by *EEOC v. iTutorGroup*, where a hard-coded age filter was the entire discriminating mechanism. Approved 2026-10-03. | H | 2 |

### 7.4 Administration and Compliance

| ID | Requirement | Pri | Phase |
|---|---|---|---|
| REQ-FR-037 | Admin dashboard: system metrics, user counts, AI usage | M | 4 |
| REQ-FR-038 | User management: list, filter, sort, edit roles, unlock, reset | H | 1–4 |
| REQ-FR-039 | Audit log search (action, resource, user, date range) with CSV export | H | 4 |
| REQ-FR-040 | GDPR data export as JSON; download link expires in 7 days | H | 4 |
| REQ-FR-041 | GDPR account deletion: admin-approved hard delete with audit entry and notification | H | 4 |
| REQ-FR-049 | Assessment management: create/edit assessments and questions, activate/deactivate without deleting existing attempts | M | 3 |
| REQ-FR-050 | Broadcast announcement: title, body, audience, channel, schedule, stored in an `Announcement` row; **recipient count resolved and shown before send**; suppression list excludes deleted/bounced users; role re-checked at send; bulk email capped per hour and sent from a subaddress separate from transactional mail; idempotent on retry. **Optional — highest blast radius per point in the spec.** See Feasibility §2.4.1 | L | 4 |

### 7.4b Employer Organisation and Billing

Added 2026-10-03 from the page-level design audit (`design.md` §10.0). Seven pages built
real features with no requirement behind them; all are now in the Arch Doc §4.1.

| ID | Requirement | Pri | Phase |
|---|---|---|---|
| REQ-FR-044 | Certification management: candidate adds/lists/edits/deletes certifications; `credential_id` stored encrypted; `verified` stays false until manually confirmed | M | 3 |
| REQ-FR-045 | Employer company profile: `EmployerProfile` created at onboarding; a job cannot be activated until one exists | H | 1 |
| REQ-FR-046 | Employer dashboard: pipeline KPIs, quota usage, bias-flagged applications for review; every KPI links to its list | M | 1 |
| REQ-FR-047 | Employer team and roles: invite, re-role, remove across `employer_manager` / `employer_hr` / `interviewer`; the last `employer_hr` cannot be removed; audit entry per change | M | 1–4 |
| REQ-FR-048 | Billing and plan: plan, usage, invoices; Stripe-hosted payment; subscription state updates on the **webhook**, not the browser redirect | M | 5 |

### 7.5 User Story Coverage

**52 user stories** (`US-001` to `US-065`) map onto the FRs above in Feasibility Doc §2.4.

Three rounds of gaps were found and closed:
- `US-023` (job search) and `US-050` (messaging) had no FR — now `REQ-FR-042` / `REQ-FR-043`
- Seven pages had features but no FR (`design.md` §10.0) — now `REQ-FR-044`–`REQ-FR-050`, covered by `US-056`–`US-062`
- Tracing the Product Owner's own experience back to requirements (§3.4) found two pain points with **no requirement at all** — now `REQ-FR-051` / `REQ-FR-052`, covered by `US-063`–`US-065`, plus the `REQ-FR-029` amendment

Rounds 1 and 2 worked **outwards from the specification** and found *capabilities with no
requirement*. Round 3 worked **inwards from the problem** and found *requirements that do
not answer the problem that started the project* — a harder class of gap to see, because
the document looks complete.

FR↔story↔page traceability now holds for all 62 pages except #1 and #2 (landing, pricing),
which are marketing pages and correctly need no requirement.

---

## 8. AI Requirements

### 8.1 Principles

1. **AI is advisory.** A human recruiter makes every accept/reject/shortlist decision (EU AI Act human oversight).
2. **Cheapest path first.** Deterministic rules, then local vector math, then free LLMs, and paid models only on explicit opt-in.
3. **Never block on AI.** Every AI task has an offline fallback; users see an "AI delayed" badge, not an error page (REQ-NFR-017).
4. **Show the cost first.** Employers see the estimated cost before confirming any AI batch (REQ-FR-028).
5. **Evidence or silence.** If no resume evidence supports a claim, the rationale says "no evidence found" instead of inventing one.

### 8.2 PII Stripping (pre-AI gate)

- **Phase 1 (MVP):** regex + spaCy NER (offline, free). Removes name, email, phone, address/location, LinkedIn URL, photo references, ID numbers. Keeps skills, experience, education, projects.
- **Phase 2 (later):** LLM-assisted PII detection with a separate, cheaper model.
- Replaced with placeholders (for example `[CANDIDATE_NAME]`) and generic labels (`[COMPANY_A]`, `[ROLE_B]`) keyed to a hashed `candidate_id`.
- Post-processing filter re-strips any PII that leaks into an LLM rationale and logs the leak attempt.
- Target: 100% of AI payloads pass the PII filter (REQ-SEC-002) — this one is checkable on a sample today.
- Bias detection: the deterministic keyword pass is the only checkable target, and only once a versioned test set exists (Phase 2). The LLM pass is advisory and may not block auto-shortlist.

### 8.3 Matching Funnel

| Step | Technology | Cost | Notes |
|---|---|---|---|
| 1. Hard filters | Deterministic rules | Free | Location, visa, min years, certifications, experience level |
| 2. Semantic ranking | `all-MiniLM-L6-v2` (384-dim) + pgvector cosine (`<=>`) | Free | Runs on CPU, offline |
| 3. Qualitative analysis | OpenRouter free models, top N only (5–10) | Free tier | Evidence-cited breakdown |
| 4. Bias audit | Deterministic keyword/pattern check (+ LLM where available) | Free | Flags e.g. "culture fit" without evidence, gendered or age-related terms |

### 8.4 Task → Model Mapping

| Task | Primary | Fallback |
|---|---|---|
| Resume / JD parsing | `openai/gpt-oss-20b:free` or `cohere/north-mini-code:free` | spaCy NER |
| Candidate–job match explanation | `google/gemma-4-26b-a4b-it:free` | pgvector score only |
| Interview question generation | `openrouter/free` | Role-category templates |
| Interview coaching | `cohere/north-mini-code:free` | Rule-based keyword coverage |
| Journey: skill extraction | `google/gemma-4-26b-a4b-it:free` | Skill-dictionary lookup |
| Journey: narrative | `openrouter/free` | Template narrative from extracted skills |
| Bias audit | `cohere/north-mini-code:free` | Deterministic keyword check |

Free-model availability changes; model names must be configuration, not code (see [Section 19](#19-open-questions-and-source-document-inconsistencies)).

### 8.5 Provider Abstraction

An `AIProvider` abstract base class (`chat_completion`, `embed`) with implementations `OpenRouterProvider` and `OfflineSpaCyProvider`. Switching to another aggregator or a self-hosted model (vLLM / Llama) must be a one-class change with no change to views or Celery tasks.

### 8.6 Graceful Degradation

| Level | Condition | Behavior |
|---|---|---|
| 0 | Quota > 50% remaining | Full LLM analysis + rationale + bias audit |
| 1 | 20–50% remaining | LLM rationale for top 5 only |
| 2 | < 20% remaining | pgvector-only scoring, no LLM |
| 3 | Quota exhausted / provider down | Offline spaCy + keyword matching only |

Additional rules: Redis tracks daily quota; 429 → Celery retry with backoff (5 s, 15 s, 45 s), then fall back to pgvector-only; 5xx → circuit breaker, fall back after 3 failures; fallback must activate within 30 seconds of an API failure (REQ-NFR-015). Candidates may be batched (about 5 per prompt) to cut call volume.

### 8.7 Explainability and Bias Requirements

- Every score shows: matched skills with resume evidence, missing skills, reasoning, model used, bias audit pass/fail.
- Candidates can view their own breakdown (REQ-FR-024).
- Rationale failing the bias audit is flagged for human review and excluded from auto-shortlisting.
- Each AI action writes `application.screened` (timestamp, model, prompt hash, rationale hash, `candidate_id`, no raw PII).
- Regular disparity analysis by demographic group where candidates opt in to provide data.

---

## 9. Non-Functional Requirements

Full list and measurement methods: Arch Doc §4.2 (50 NFRs). Condensed:

### 9.1 Performance

| ID | Requirement | Target |
|---|---|---|
| REQ-NFR-001 | Resume processing (extract + PII strip) | < 30 s |
| REQ-NFR-002 | Embedding generation | < 10 s per resume; 10 resumes < 60 s |
| REQ-NFR-003 | AI screening of 100 applications | < 5 min |
| REQ-NFR-004 | pgvector query (100 candidates) | < 2 s |
| REQ-NFR-005 | Server-rendered page load | < 2 s; Lighthouse ≥ 90 |
| REQ-NFR-006 | API p95 latency | < 500 ms |
| REQ-NFR-007 | Static assets | < 500 ms |

### 9.2 Scalability

| ID | Requirement | Target |
|---|---|---|
| REQ-NFR-008 | Concurrent authenticated users | 1,000 (Locust) |
| REQ-NFR-009 | Concurrent AI screening tasks | 50 |
| REQ-NFR-010 | DB connection pool | 100 max |
| REQ-NFR-012 | Horizontal scaling | Stateless app tier behind load balancer |
| REQ-NFR-013 | DB read scaling | pgBouncer + read replicas |

### 9.3 Availability and Reliability

| ID | Requirement | Target |
|---|---|---|
| REQ-NFR-014 | Uptime | 99.9% |
| REQ-NFR-015 | AI provider fallback activation | within 30 s |
| REQ-NFR-016 | DB recovery | RTO < 2 h, RPO < 15 min |
| REQ-NFR-017 | Graceful degradation | No user-facing crash on AI failure |
| REQ-NFR-018 | Self-healing | Auto-restart (Docker restart policies) |

### 9.4 Maintainability and Operability

| ID | Requirement | Target |
|---|---|---|
| REQ-NFR-019 | Test coverage | ≥ 80% (`--cov-fail-under=80`) |
| REQ-NFR-020/022 | black, flake8, isort | 100% compliant in CI |
| REQ-NFR-021 | Type safety | `mypy --strict` on new code |
| REQ-NFR-023 | API docs | Auto-generated (drf-spectacular) |
| REQ-NFOR-024 | Error tracking | 100% of exceptions to Sentry, `send_default_pii=False` |
| REQ-NFOR-025 | Logs | Structured JSON |
| REQ-NFOR-001 | Deployment rollback | < 5 min |
| REQ-NFOR-002 | Environment parity | Same containers dev/staging/prod |

### 9.5 Accessibility and Localization

- WCAG 2.1 AA (REQ-COM-007); axe-core and pa11y in CI; contrast ≥ 4.5:1 text, ≥ 3:1 UI; full keyboard operation; `prefers-reduced-motion` respected.
- **Charts need text alternatives.** Journey Map and analytics must offer a data table plus screen-reader summary; canvas-only charts are not acceptable.
- i18n: all strings wrapped in `gettext_lazy()` from day one; full translation in Phase 5 (Bengali first, then Indonesian, Portuguese, Spanish; RTL support for Arabic).

---

## 10. Security, Privacy and Compliance

### 10.1 Authentication and Authorization

| Control | Requirement |
|---|---|
| Password hashing | Argon2id (REQ-SEC-001); min 12 characters; breached-password check via HaveIBeenPwned k-anonymity |
| Sessions / tokens | HttpOnly, Secure, SameSite=Lax cookies; JWT 15-min access / 7-day refresh with rotation and blacklist on logout |
| MFA | TOTP via django-otp; **required** for employer admin accounts, optional for candidates (REQ-SEC-009) |
| RBAC | Groups: `admin`, `employer_hr`, `employer_manager`, `interviewer`, `candidate`, `guest`; default-deny |
| Lockout | 5 failures → 15 min; 10 → email verification to unlock |

### 10.2 Data Protection

| Area | Requirement |
|---|---|
| At rest | AES-256-GCM field encryption (location, first/last name, original filename, company name, Stripe IDs, credential ID, MFA secret); disk encryption; encrypted backups (30-day rolling) |
| Files | S3-compatible storage with SSE; UUID filenames; served only via authenticated, rate-limited Django views (no direct S3 URLs); 10 MB max; MIME check (python-magic); ClamAV scan |
| In transit | TLS 1.3 minimum; HSTS 1 year with preload; TLS to Redis/PostgreSQL where applicable |
| Secrets | Env vars / Docker secrets / secret manager; never in code or git; key rotation every 90 days |
| Trade-off | Encrypted columns are not searchable; non-sensitive denormalized copies (for example `skills`) support search |

### 10.3 Application Security

- OWASP Top 10 coverage; Django ORM only (no raw SQL in views); CSRF, auto-escaping, CSP, `X-Frame-Options: DENY`, `nosniff`, Referrer-Policy, Permissions-Policy (camera/mic blocked by default).
- Rate limits: 100 req/hr unauthenticated, 1,000 req/hr candidates, 5,000 req/hr employer HR, 20 req/min on AI endpoints.
- `pip-audit` and `bandit` block merges on critical/high findings (REQ-SEC-011).
- Pen testing: OWASP ZAP weekly in CI; quarterly manual tests; annual third-party test.

### 10.4 Compliance

| ID | Requirement | Standard |
|---|---|---|
| REQ-COM-001 | Data minimization | GDPR Art. 25 |
| REQ-COM-002 | Right to erasure (hard delete + audit entry) | GDPR Art. 17 |
| REQ-COM-003 | Data portability (JSON/PDF export) | GDPR Art. 20 |
| REQ-COM-004 | Consent checkbox at registration | GDPR Art. 7 |
| REQ-COM-005 | Configurable retention; automated purge via Celery Beat (default 2 years for candidates, 5 years for hired employee records) | GDPR Art. 5(1)(e) |
| REQ-COM-006 | Human-in-the-loop, transparency, bias monitoring | EU AI Act (employment AI is high-risk) |
| REQ-COM-007 | Accessibility | WCAG 2.1 AA |
| REQ-COM-008 | Append-only audit trail | GDPR Art. 30 |
| REQ-COM-009 | Privacy by design | GDPR Art. 25 |

### 10.5 Declared Legal Residuals

Employment-AI regulation is still evolving. Cross-border transfer (candidate data processed by an overseas LLM provider) needs a transfer mechanism such as Standard Contractual Clauses. LLM provider terms generally prohibit sending personal data, which makes PII stripping a **legal requirement**, not only a privacy feature. Both items are open (see [Section 19](#19-open-questions-and-source-document-inconsistencies)).

---

## 11. Data Model

Full SQL DDL: Arch Doc §5.1. Django models: Complete Doc §8.2 and Appendix C.11. Field-level data dictionary: Feasibility Doc §3.8.

### 11.1 Entities

| Domain | Entities |
|---|---|
| Accounts | `User` (auth, MFA, lockout state) |
| Candidate | `CandidateProfile`, `CandidateResume`, `Skill`, `CandidateSkill`, `Certification`, `AssessmentAttempt` |
| Employer | `EmployerProfile`, `EmployerTeamMember`, `Subscription` |
| Hiring | `Job`, `Application`, `InterviewPack`, `Interview`, `InterviewFeedback` |
| Assessment | `Assessment`, `AssessmentQuestion`, `JobAssessmentRequirement` *(REQ-FR-051, added 2026-10-03)* |
| Communication | `Notification`, `Message` |
| Compliance | `AuditLogEntry` (append-only), `DataExportRequest`, `DataDeletionRequest` |

### 11.2 Key Relationships

```
User 1─1 CandidateProfile / EmployerProfile
EmployerProfile 1─N EmployerTeamMember N─1 User     (REQ-FR-047)
CandidateProfile 1─N CandidateSkill N─1 Skill
CandidateProfile 1─N CandidateResume · Certification · AssessmentAttempt · Application
EmployerProfile  1─N Job · 1─1 Subscription
Job 1─N Application · InterviewPack · JobAssessmentRequirement N─1 Assessment
Application 1─N Interview · Message
Interview 1─N InterviewFeedback
Assessment 1─N AssessmentQuestion · AssessmentAttempt
UNIQUE(job_id, candidate_id) on Application
CHECK chk_override_has_reason on Application              (REQ-FR-052)
```

**24 tables, 35 foreign keys.** Added 2026-10-03: `job_assessment_requirements`
(2 FKs), `applications.decided_by` (1 FK) and `announcements` (1 FK, for `REQ-FR-050`,
which had no table at all — see Feasibility §2.4.1 round 4), then
`data_deletion_requests.approved_by` (1 FK, added while writing the `gdpr/deletion/`
endpoints — an erasure request that records no approver has no audit value).
`employer_profiles.show_company_name` was also added, for the same reason: the public
job endpoints need a stored per-employer choice rather than a guess.

### 11.3 Application Status Lifecycle

`applied → screened → shortlisted → interview → offered → hired`, with `rejected` reachable from any stage.

`not_matched` (added to the vocabulary 2026-10-03) is a **filter outcome, not a
decision**. It records which rule fired (`not_matched_reason`) and which rule set
version judged it (`filter_rules_version`). The candidate stays listed and reviewable,
and an employer can pull them back into review. **Only a person can reject a
candidate** — `prd.md` §8.1 is now true at the schema level, not just in prose.

Two fields record the integrity of the human decision:

| Field | Purpose |
|---|---|
| `assessment_gate_status` | `not_required` / `pending` / `passed` / `failed` — REQ-FR-051 |
| `decision_override` + `decision_override_reason` + `decided_by` | A shortlist or reject that went against the ranking — REQ-FR-052 |

`decision_override = TRUE` with an empty reason is rejected by a `CHECK` constraint, so
the rule holds even for a write that did not come through the UI.

### 11.4 Notes

- `resume_embedding` and `description_embedding` are `VECTOR(384)`; HNSW index required beyond ~10K rows.
- `AuditLogEntry` is never updated or deleted, and `actor_id` is `ON DELETE SET NULL` so the log survives user deletion.
- Raw PII is never stored in audit `details` or in Sentry payloads.

---

## 12. System Architecture and Tech Stack

### 12.1 Architecture Decisions (ADRs)

| ID | Decision |
|---|---|
| AD-001 | Full Python stack (Django 5.2+ LTS, DRF, Celery). No Rust. |
| AD-002 | Django Templates + HTMX + Tailwind for MVP frontend; React 18 + Vite reserved for Phase 5 (PWA, WebSockets). The DRF API is built from day one. |
| AD-003 | OpenRouter (`openrouter/free`) as primary AI provider behind an `AIProvider` abstraction with offline fallbacks. |
| AD-004 | PostgreSQL 17 + pgvector for semantic matching; local sentence-transformers embeddings. |
| AD-005 | PII stripped before any external processing; every stripping event audited. |
| AD-006 | Monolith first, with app-level boundaries; split into services only when scaling demands it. |
| AD-007 | Celery + Redis for async AI tasks; Celery Beat for scheduled jobs. |

### 12.2 Topology

```
Users ──HTTPS/TLS1.3──▶ Nginx (TLS, edge rate-limit, security headers, static)
                          │
         ┌────────────────┼─────────────────┐
         ▼                ▼                 ▼
   Django/Gunicorn   Celery workers     Celery Beat
   (templates, HTMX, (OpenRouter,       (quota reset, retention
    DRF API)          embeddings, NER)   purge, backup checks)
         └────────────────┼─────────────────┘
                          ▼
   PostgreSQL 17 (+pgvector, pgcrypto) · Redis 7 · S3/MinIO · Email provider
```

Celery workers have no internet egress except the AI provider. PostgreSQL and Redis are reachable only on the private Docker network.

### 12.3 Django Apps

`core`, `accounts`, `candidates`, `employers`, `matching`, `assessments`, `interviews`, `journey`, `notifications`, `ai`, `api`, `admin`.

### 12.4 Tech Stack

| Layer | Choice |
|---|---|
| Frontend | Django Templates, HTMX, TailwindCSS, Chart.js, django-htmx |
| Backend | Python ≥ 3.12, Django ≥ 5.2 LTS, DRF, drf-spectacular, SimpleJWT, django-otp, django-ratelimit |
| Data | PostgreSQL 17, pgvector, pgcrypto, Redis 7 |
| Async | Celery 5.4+, Celery Beat, django-celery-results, Flower |
| AI/ML | `openai` SDK (OpenRouter), sentence-transformers, spaCy, torch, pdfplumber |
| Storage | django-storages, boto3, MinIO or Cloudflare R2, python-magic, ClamAV |
| Security | argon2-cffi, cryptography, django-encrypted-model-fields |
| Email / billing | django-anymail (Resend/SendGrid/SES), Stripe (Phase 5) |
| Monitoring | Sentry, Prometheus, Grafana |
| Infra / CI | Docker, Docker Compose, Nginx, Gunicorn, Whitenoise, GitHub Actions |
| Quality | pytest, pytest-django, pytest-cov, factory-boy, black, flake8, isort, mypy, bandit, pip-audit |

### 12.5 Caching

| Key | TTL |
|---|---|
| `user_profile:{id}` | 1 h |
| `job_embeddings:{id}` | 24 h |
| `similarity_matrix:{job_id}` | 2 h |
| `rate_limit:{user}:{endpoint}` | 15 min |
| `openrouter_quota:{day}` | until midnight |
| `skill_taxonomy:v1` | 7 days |
| `ai_response:{hash}` | 6 h |

Invalidate on job update, resume re-upload, skill update, and daily quota reset.

---

## 13. API Surface

Base path `/api/v1/`. OpenAPI generated by drf-spectacular. Full list: Complete Doc §C.12.

| Area | Representative endpoints |
|---|---|
| Auth | `POST auth/register/`, `auth/login/`, `auth/refresh/`, `auth/logout/`, `auth/mfa/enable/`, `auth/mfa/verify/`, `auth/password/reset/`, `GET/PUT auth/me/` |
| Candidate | `GET/PATCH candidates/me/`, `candidates/skills/`, `candidates/resumes/` (+ `{id}/process/`), `candidates/certifications/`, `candidates/journey/` (+ `regenerate/`), `candidates/assessments/{id}/start/` and `answer/`, `candidates/applications/` |
| Employer / jobs | `GET/PATCH employers/me/`, `jobs/`, `jobs/{id}/activate/`, `jobs/{id}/screen/`, `jobs/{id}/applications/`, `jobs/{id}/interview-pack/`, `jobs/{id}/analytics/`, `jobs/{id}/share/` |
| **Screening integrity** *(new, 2026-10-03)* | `GET/POST jobs/{id}/required-assessments/`, `DELETE jobs/{id}/required-assessments/{req_id}/` (REQ-FR-051); `POST applications/{id}/shortlist/`, `POST applications/{id}/reject/` — both take `reason` and return `409` when the assessment gate is not passed (REQ-FR-051/052); `GET applications/?status=not_matched` (REQ-FR-029); `GET jobs/{id}/analytics/override-rate/` (REQ-FR-035) |
| Interviews | `interviews/`, `interviews/{id}/feedback/`, `interviews/{id}/pack/` |
| Communication | `notifications/`, `notifications/{id}/read/`, `messages/` |
| Admin | `admin/dashboard/`, `admin/users/`, `admin/audit-log/`, `admin/ai-quota/`, `admin/broadcast/` |

**The endpoint for a decision must not be a bare `PATCH applications/{id}/`.** A
shortlist or reject that goes against the ranking goes through `shortlist/` or
`reject/` so the `reason` field is **required by the serializer**, not by a front-end
form that can be bypassed. The `409` on a closed assessment gate is what makes
REQ-FR-051 a constraint rather than a hint.

| **Public discovery, GDPR, team, assessments, broadcast** | **Now complete** — `GET jobs/public/` + `{id}/`, `gdpr/export/*` and `gdpr/deletion/*`, `employers/team/*`, `assessments/*` authoring, `admin/announcements/*` |

✅ **Gap closed 2026-10-03.** All five endpoint groups were missing from `Complete Doc §C.12`
and are now written. Two of them exposed a further problem: `REQ-FR-042` requires an
employer disclosure opt-in and `REQ-FR-041` requires admin-approved erasure, and **neither
had a column to store it**. `employer_profiles.show_company_name` and
`data_deletion_requests.approved_by` were added, the latter with a `UNIQUE (user_id, status)`
constraint the ER diagram had been claiming existed but the DDL did not have.

---

## 14. UX Requirements and Information Architecture

### 14.1 Navigation

```
FAIRFOLD
├── Public: Home · Job board/search · Register · Login · Password reset
├── Candidate portal: Dashboard · Profile · Resume · Journey Map · Assessments
│                     · Coaching · Applications · Messages
├── Employer portal:  Dashboard · Jobs · Applications · Screening · Interviews
│                     · Feedback · Analytics · Team · Settings
└── Admin:            Overview · Users · Audit log · Compliance
```

Portals are strictly separated by Django group permissions.

### 14.2 Screens Required (18)

1 Register/login (incl. MFA) · 2 Candidate onboarding/profile · 3 Resume upload with progress · 4 Job browse/search · 5 Job detail + apply · 6 Application tracker · 7 Match score + rationale · 8 Journey map · 9 Timed assessment · 10 Coaching feedback · 11 Employer job list/create/edit · 12 Ranked application list · 13 Candidate review (rationale + bias audit) · 14 Screening confirm + cost estimate · 15 Interview pack builder · 16 Scheduling + feedback form · 17 Analytics dashboard · 18 Admin users + audit log.

**Low-fidelity wireframes are now delivered** for all 18 screens: `design.md` §10.5 draws 23 wireframes covering 36 of 62 pages, including every required screen and every core-flow page. High-fidelity mockups and the Figma file are still outstanding (`design.md` §12 items 1–4).

### 14.3 UX Rules

- Global header: logo, portal nav, notification bell, account menu. Desktop sidebar; mobile collapsible drawer. Badge counts on Applications and Messages.
- Any employer action that triggers AI **must** show a cost estimate and require explicit confirmation (safety affordance, not a preference).
- Show "AI analysis delayed, using semantic similarity only" badge when running in degraded mode.
- AI-derived content is labeled as AI-generated; the final decision control is always human.
- Design system (owned by UI/UX) defines accessible color tokens and focus styles once, not per component.

---

## 15. Monetization

Canonical source: Complete Doc §C.14 (see Section 19 for the conflicting version in the Feasibility Doc).

### 15.1 Candidate Tiers

| Tier | Price | Highlights | Limits |
|---|---|---|---|
| Free | $0 | Profile, resume upload, apply, basic match scores, 5 coaching sessions/mo, basic journey map | 5 applications/day, 5 AI interactions/day |
| Essential | $5/mo | Unlimited applications, 20 coaching sessions/mo, advanced journey charts, priority in employer search | 50 AI interactions/day |
| Professional | $20/mo | Unlimited coaching, per-application career story, 10 assessments/mo, interview pack builder, PDF export | 200 AI interactions/day |
| Premium | $50/mo | AI mentor, salary insights, 50 assessments/mo, featured placement, resume templates | Unlimited |

### 15.2 Employer Tiers

| Tier | Price | Highlights | Limits |
|---|---|---|---|
| Free | $0 | 3 jobs, 50 AI screens/mo, candidate pipeline list | Not time-limited (no expiry column exists in `subscriptions`) |
| Starter | $100/mo | 50 jobs, 500 AI screens/mo, basic analytics | ≤ 25 employees |
| Growth | $500/mo | 500 jobs, 5,000 screens/mo, advanced analytics, interview packs | ≤ 250 employees |
| Scale | $1,500/mo | Unlimited jobs, 15,000 screens/mo, custom model selection, API access | ≤ 1,000 employees |
| Enterprise | $5,000/mo | Unlimited; SSO (SAML/OIDC), white-label career site, on-prem option, 24/7 support | Unlimited |
| Self-hosted | $0 + support | Enterprise features on own infrastructure | Needs ops team |

Overage: $0.0001 per AI call beyond quota. Stripe billing ships in Phase 5; until then plan limits are enforced by `Subscription` quota fields.

### 15.3 Economics

Estimated cost to MVP is under $600/year excluding labor (VPS ~$20–50/mo, domain ~$15/yr, everything else open source or free tier). Marginal cost of an extra free user is close to zero because embeddings are local and every LLM task has a free fallback.

---

## 16. Operations and Delivery

### 16.1 Environments and Settings

`config/settings/`: `base`, `local`, `test`, `ci`, `production`. Environments: local, CI, staging, production, with a documented promotion process and drift prevention (Arch Doc §8.8). Environment variables are catalogued in Complete Doc §C.7.

### 16.2 CI/CD

GitHub Actions pipeline: flake8 → black → isort → mypy → bandit → pip-audit → pytest (coverage ≥ 80%) → OpenAPI schema → Docker build/push → deploy to staging → smoke test → deploy to production → health check. Manual `workflow_dispatch` rollback jobs for staging and production (target < 5 min).

### 16.3 Testing

Unit and integration (pytest, factory-boy), security (bandit, pip-audit, ZAP), load (Locust, 1,000 users, < 2 s), AI-provider contract tests, accessibility (axe-core, pa11y), i18n tests.

### 16.4 Monitoring and Alerting

| Metric | Threshold | Severity |
|---|---|---|
| Django 5xx rate | > 5% over 5 min | Critical |
| Celery failure rate | > 15% over 10 min | Critical |
| Audit log write failures | > 5 in 5 min | Critical (halt processing) |
| OpenRouter error rate | > 20% over 5 min | High (auto offline fallback) |
| pgvector latency | > 500 ms avg | Warning |
| DB pool | > 90% for 2 min | Warning |
| Redis memory | > 80% | Warning |
| Daily AI spend | > $5 | Warning |
| Failed logins | > 10 per IP / 15 min | Warning (block 1 h) |
| TLS expiry | < 30 days | Warning |

### 16.5 Disaster Recovery

| Component | RTO | RPO |
|---|---|---|
| PostgreSQL | 2 h | 15 min (WAL archiving, hourly base backup, monthly restore test) |
| File storage | 4 h | 0 |
| App containers | 15 min | 0 |
| Redis | 1 h | n/a (ephemeral) |
| Secrets | 5 min | 0 |

### 16.6 Incident Response and Releases

- P1 (response < 15 min), P2 (< 1 h), P3 (next business day); blameless post-mortem within 48 h of P1; GDPR 72-hour breach notification path.
- Semantic versioning; GitHub Flow; weekly Tuesday releases; canary (1% for 30 min) before full rollout; release retrospective within 72 h.
- Maintenance cadence (daily/weekly/monthly/quarterly/yearly) in Arch Doc §8.5.

---

## 17. Roadmap, Team and Methodology

### 17.1 Methodology

Scrum with 1-week sprints (about three sprints per phase). Definition of Done: code merged, tests pass, coverage ≥ 80%, security review, documentation updated.

### 17.2 Team

| Person | Role | Focus |
|---|---|---|
| Sardar Shihab | Full-Stack Engineer | Templates/HTMX, Tailwind, journey charts; backend endpoints as needed |
| Arnob Biswas Antu | Frontend Engineer | Employer dashboard, application review, scheduling UI |
| Ishrak Hossain | Backend & AI Engineer | Django, DRF, Celery, OpenRouter, PII stripping, pgvector, security (also covers DevOps) |
| Mohammad Abdul Ahad | UI/UX Designer | Design system, tokens, accessibility (WCAG 2.1 AA) |
| Fahad Haque | UI/UX Designer | Wireframes, employer dashboard UX, journey-map design |

**Known gap:** no dedicated DevOps role; the backend engineer absorbs it. This is the largest operational risk (RSK-009).

### 17.3 Milestones

| Milestone | End of week | Exit criterion |
|---|---|---|
| M1 | 3 | Phase 1 acceptance criteria met |
| M2 | 6 | Phase 2 acceptance criteria met; screening works end to end |
| M3 | 9 | Phase 3 acceptance criteria met; **MVP feature-complete** |
| M4 | 12 | Phase 4 acceptance criteria met; production-ready |
| M5 | 13+ | Optional advanced features |

### 17.4 Phase Acceptance Criteria (headline items)

- **Phase 1:** Compose stack starts; register/login with verification email; resume upload via presigned URL; job CRUD; duplicate applications blocked; security headers present; 80%+ coverage on models/auth/job CRUD; lint and security scans pass.
- **Phase 2:** PII stripping ≥ 95% accurate on test set; 384-dim embeddings; pgvector ranking < 2 s for 100 candidates; LLM rationale for top 10; deterministic bias keyword pass (accuracy target set once the versioned test set exists, Phase 2) **including Amazon-style proxy cases — women's-college names, "women's society captain", gendered clubs**; cost estimate shown first; audit entry per AI action; **`not_matched` results show the rule that fired, stay reviewable and carry `filter_rules_version` (REQ-FR-029); an override requires a written reason and writes an `ai_decision`-class audit entry (REQ-FR-052)**.
- **Phase 3:** Interactive timeline; skill-evolution chart; assessment taking and auto-scoring; coaching feedback; job-tailored narrative; match scores visible to candidates. **An employer can attach an assessment as a required step, and an applicant without a passing attempt cannot be shortlisted on score alone (REQ-FR-051); the gate status shows on the application row; removing a requirement leaves existing attempts intact; analytics shows override rate by user and job (REQ-FR-035).**
- **Phase 4:** MFA for employer admins; encrypted PII verified unreadable in backups; authenticated file serving only; rate limits enforced; Sentry clean of PII; `/metrics/` live; GDPR export and delete working; auto-deploy to staging; load test of 100 concurrent applicants < 5 s with < 1% errors.
- **Phase 5:** Stripe plan changes; Bengali plus 3 more languages; installable PWA; WebSocket coaching and notifications.

---

## 18. Risks, Assumptions and Dependencies

### 18.1 Risks

| ID | Risk | Prob. | Impact | Mitigation |
|---|---|---|---|---|
| RSK-001 | OpenRouter free tier removed or changed | Med | High | `AIProvider` abstraction; offline spaCy + pgvector; offline-first for matching |
| RSK-002 | LLM hallucination in rationale | Med | Med | Evidence-cited format; "no evidence found" rule; human review; bias audit |
| RSK-003 | Resume parsing accuracy < 80% | Med | Med | Manual profile edit; future IBM Granite Docling upgrade |
| RSK-004 | Data breach | Low | Critical | Defense in depth, encryption, PII stripping, quarterly pentests |
| RSK-005 | Competitor copies Journey Mapping | Low | Med | System-level integration, switching costs, data network effects |
| RSK-006 | EU AI Act non-compliance | Low | High | Human-in-the-loop docs, transparency, disparity analysis |
| RSK-007 | Outgrowing free tier | High (eventual) | Med | Cheap paid models → self-hosted vLLM; usage-based billing |
| RSK-008 | Bangladesh market does not convert | Med | High | Target BD plus global SMBs; self-hostable option |
| RSK-009 | No DevOps expertise | Med | Med | Docker Compose; managed services; freelance DevOps for Phase 4 |
| RSK-010 | Python/Django talent | Med | Med | Hire Python-experienced; train; use open-source community |
| R4 | Phase 3 too dense for 3 weeks | High | Med | Journey-mapping MVP isolated as must-have; skill evolution and storytelling separable |
| R7 | PII leakage to AI provider | Low | **High** | Two-layer stripping; treated as a **release blocker**, since leaked PII cannot be recalled |
| **RSK-011** | **Trademark clearance outstanding.** "FairFold" was selected on 2026-10-03 after the previous name was found to be contested by three unrelated commercial users. **The domain is owned** (temporary first, primary at launch), but a domain registration is not a trademark filing. See §4.3. | Med | Low | Commission a formal trademark search in Bangladesh and every target export market; file the word mark in classes 42 and 35 per market; keep all host-dependent config in environment variables so the domain switch needs no code change | Product Owner |
| **RSK-012** | **AI-assisted development degrades review quality.** AI raises throughput, not correctness — it yields confident, plausible, wrong code and tests written to match the implementation instead of the spec. For a product whose entire claim is that it asserts nothing it cannot evidence, a confidently-wrong codebase is the worst outcome available. | High | High | Acceptance criteria before tests; no generated code merges unread; `bandit`/`pip-audit`/`safety` in CI; auth, encryption, PII stripping and `chk_override_has_reason` on a no-AI-review-list; add a licence scan. `ASM-003` |

### 18.2 Assumptions

- Free OpenRouter models stay available at roughly 20 req/min and 50 req/day without payment details (verify before each phase).
- CPU-only inference for sentence-transformers is adequate on a 2–4 vCPU VPS.
- Recruiters accept a human-in-the-loop model and will use the cost-estimate confirmation step.
- Team has working Django experience.

**Added 2026-10-03**, from inputs the team gave on capacity and tooling:

- **`ASM-002`** — the team sustains double shifts for the full 12 weeks without attrition
  or quality degradation. If it fails, **re-scope; do not compress.**
- **`ASM-001`** — the 52 requirements are the right scope for an MVP. If it fails, cut
  `REQ-FR-050` first; it is the only requirement the team itself called optional.
- **`ASM-003`** — AI assistance raises delivery capacity for the 217 points. *Plausible
  for boilerplate; unmeasured.* **Tested at the end of Phase 1** by points actually
  delivered against the 41-point, 3-week phase. If it fails, drop the capacity assumption
  and re-plan — **never** answer a schedule problem by reducing review. See **RSK-012**.

> **Correction, 2026-10-03.** `ASM-003` previously read *"...without reducing review
> capacity."* That clause is not measurable, so it could never be falsified — a thing that
> cannot be falsified is not an assumption, it is a hope. The review obligation was never
> an assumption either; it is now a **mandate** — the no-AI-review-list in
> `FAIRFOLD_Feasibility_and_Design.md` §2.6.4.2, which names eight paths a named human
> must read before merge.

### 18.3 External Dependencies

OpenRouter, S3-compatible storage (MinIO/R2), email provider (Resend/SendGrid/SES), Sentry, Stripe (Phase 5), Piston or similar sandbox for coding assessments, Let's Encrypt, GitHub Actions.

---

## 19. Open Questions and Source Document Inconsistencies

Items to resolve before the PRD is frozen. Where one source was needed to proceed, the choice is noted.

### 19.1 Missing Inputs (team must supply)

| # | Item | Owner |
|---|---|---|
| 1 | ~~**Requirement collection method.**~~ **Closed 2026-10-03** — §3.4 and Feasibility Doc §1.3. Stated honestly and tagged: problem-owner elicitation from the Product Owner's own experience (**[Done]**), corroborated by friends who joined the team and by a university senior (**[Done]**), group discussion and scenario elicitation (**[Done]**), no recruiter interviews / survey / observation (**[Planned]**). The validation plan with its sizes and guides is in Feasibility Doc §1.3.4 and stays **[Planned]** until it is actually run. | — |
| 2 | ~~**Real-world problem example.**~~ **Closed 2026-10-03** — §1.2 and Feasibility Doc §1.2.1. Amazon's recruiting engine (Reuters, 10 Oct 2018) as the primary case, with *EEOC v. iTutorGroup* (Aug 2023, $365,000), HireVue (Jan 2021) and *Mobley v. Workday* as supporting cases, plus three Bangladesh sources. The iTutorGroup case directly produced **Gap G3**. **Note:** `Mobley v. Workday` was mid-litigation as of Jul 2026 and must be re-verified before public citation. | — |
| 3 | ~~**Wireframes** for the 18 screens.~~ **Resolved 2026-10-03** — delivered as low-fidelity text wireframes in `design.md` §10.5 (S01–S18). Still open: the Figma file, Figma components and high-fidelity mockups. | UI/UX designer |
| 4 | Legal position on cross-border data transfer (Standard Contractual Clauses) and on provider terms of service. | Legal / PM |
| 5 | ~~**Seven pages build features with no functional requirement.**~~ **Closed 2026-10-03** — added to the Arch Doc §4.1 as `REQ-FR-044`–`REQ-FR-050` (§7.4, §7.4b). All seven kept in scope; `REQ-FR-050` remains optional. **Resolved 2026-10-03 — kept**, then **re-examined the same day** at the team's request and the estimate was wrong: **3 → 8 story points**, because the feature had **no database table at all** and needed a suppression list, an audience matcher, an idempotency key and a separate sending subaddress. Now **8 points, Low priority, Phase 4**, with the `announcements` table added. Analysis and the full list of what goes wrong: Feasibility Doc §2.4.1. If it is ever cut, `REQ-FR-050`, `US-062`, `design.md` page #62 **and the `announcements` table** must go together. | Team |

### 19.2 Inconsistencies Between Sources

| # | Topic | Conflict | Treatment in this PRD |
|---|---|---|---|
| 1 | **Candidate pricing** | Complete Doc: Professional $20 and Premium $50. Feasibility Doc: "Pro" $50 only. | **Resolved 2026-10-03 — Complete Doc is canonical** (§15.1): Free $0, Essential $5, Professional $20, Premium $50. The Feasibility Doc's "Pro" tier was the stale one and no longer appears. |
| 2 | **Employer pricing** | Feasibility Doc omitted the Scale ($1,500) tier and listed a "Free" employer tier; Complete Doc §C.14 had no free employer row, but the `subscriptions` model defines one (`plan DEFAULT 'free'`, `max_jobs 3`, `ai_quota_remaining 50`). | **Resolved 2026-10-03 — Complete Doc is canonical** (§15.2), and §C.14 now carries the Free row to match the schema. Free is $0 / 3 jobs / 50 screens and is **not time-limited**: the schema has no trial-expiry column, so "Trial" was unsupported and was removed. |
| 3 | **Missing FRs** | Job search and messaging have use cases, models and stories but no FR. | **Closed 2026-10-03** — promoted into the Arch Doc §4.1 as REQ-FR-042 and REQ-FR-043 (new *Job Discovery & Messaging* group). See also §19.1 item 5, closed the same day with REQ-FR-044–050, and §19.2 item 16 below. **Arch Doc now holds 52 FRs.** |
| 4 | **PII retention** | Complete Doc §5.2 says PII is encrypted at rest; Arch Doc Flow 3 says original PII "stays in EncryptedCharField" while anonymized text is stored. Where the original resume file and un-stripped text live, and who can see them, is not specified. | **Resolved 2026-10-03 — reveal at shortlist.** Employers see **anonymised text only** while screening. On shortlist the name and contact details become visible **to that employer only**, and the reveal writes an audit entry. The original resume file and un-stripped text stay encrypted at rest and are **never** sent to an external AI provider. Written into `REQ-FR-029` and `REQ-FR-030`. |
| 5 | **Audit log retention vs. GDPR retention** | Audit logs rotate at 90 days (REQ-COM-008) while candidate data is retained 2 years and hired-employee data 5 years; AI-decision evidence may be needed longer than 90 days for AI Act accountability. | **Resolved 2026-10-03 — two retention classes.** `resource_type = 'access'` entries (who looked at what) rotate at 90 days and are operational only. Entries with `resource_type = 'ai_decision'` (every screening, rationale and bias check, per REQ-FR-030) are **retained with the application record** — 2 years, 5 years if hired. 90 days would have destroyed the only evidence that a hiring decision was unbiased. |
| 6 | **Audit log key type** | `AuditLogEntry.resource_id` was `INTEGER` in the Feasibility Doc while core entities use `UUID` primary keys. | **Resolved 2026-10-03** — `UUID` in the Feasibility Doc class diagram, ER diagram and data dictionary, matching Arch Doc §5.1. The Arch Doc was already correct. |
| 7 | **Auth model** | Sessions (Django) vs JWT are both specified; HTMX/templates would normally use sessions, while JWT is specified for the API/SPA. | **Resolved 2026-10-03 — both, for different consumers.** Django sessions (httpOnly, `SameSite=Lax`) for the server-rendered HTMX UI; short-lived JWT for the DRF API and any mobile client. Same user table, same permissions, one logout endpoint that revokes both. |
| 8 | **OpenRouter free-tier limits** | Quoted as "20 req/min, 50 req/day" and also "per IP"; free model IDs listed are as of September 2026. | **Resolved 2026-10-03 — configuration, not a design assumption.** Free model IDs and rate limits are settings, read from `.env`, not hard-coded; the offline fallback (REQ-FR-028) is what keeps $0-cost operation true if the free tier changes. Re-verify the numbers at implementation. |
| 9 | **Django version** | One line of the Complete Doc says ≥ 5.2 LTS with a note that 5.0 is EOL; others say "Django 5". | 5.2+ LTS used. |
| 10 | **Gantt dates** | The Gantt in the Feasibility Doc started 2026-01-05, nine months before the documents were dated. | **Resolved 2026-10-03** — re-based to a kickoff of Mon 2026-10-05, the first working day after the specs were completed. Feasibility Doc §2.7.2 now carries a milestone table and a warning that the Phase 4 milestone lands on Christmas Day. |
| 11 | **Phase story points** | Per-phase estimates (~21/34/31/30/25) did not sum to the stated 170 total. | **Resolved 2026-10-03** — re-split to 41/41/45/39/33 = 199, matching the 49 stories at their actual point values. Then re-split again on 2026-10-03 (c) to 41/49/50/39/33 = 212, then re-split once more the same day to **41/49/50/44/33 = 217** after `REQ-FR-050` was re-estimated from 3 to 8 points, adding the screening-integrity work to Phases 2 and 3. Still a planning estimate; re-estimate at sprint planning. |
| 12 | **Bias audit definition** | The bias audit is both a deterministic keyword check and an LLM check, and "100% flagged on test dataset" needs a defined, versioned test set. | **Resolved 2026-10-03 — the claim is narrowed until the set exists.** The deterministic keyword pass (gendered terms, "cultural fit" without evidence, age proxies) ships in Phase 2 and is the only thing that may be described as testable. The LLM pass is **advisory** and may not block auto-shortlist. "100% flagged on test dataset" is removed from acceptance criteria until a versioned set exists; building it is a Phase 2 task with Ishrak Hossain as owner. |
| 13 | **Interview coaching vs. "interview recording & analysis"** | The Professional tier listed recording and analysis, but video recording is out of scope (`prd.md` §2.3). | **Resolved 2026-10-03 — removed from the tier, in both documents.** Advertising a feature that is out of scope is worse than having a thinner tier. Complete Doc §C.14 and `prd.md` §15.2 now list interview coaching (REQ-FR-021) and interview pack builder (REQ-FR-031) instead. |
| 14 | **Offer letter priority** | REQ-FR-034 is Low priority, but the Complete Doc places offer generation in the core employer flow. | **Resolved 2026-10-03 — kept Low, Phase 5.** Generating and storing an offer letter is the highest-consequence AI output in the product and the one most likely to be misused. It does not belong in an MVP that cannot yet verify bias in its own output. |
| 15 | **FR count disagreed with itself** | The header said "50 FRs" and §19.2 item 3 said 50, but the 2026-10-03 update note under *Source documents* said *"the Arch Doc now holds **43** FRs, not 41"* — a leftover from the same day's earlier count that was never updated when seven more requirements landed. | **Fixed 2026-10-03 (c).** The single stale note is replaced by three dated notes — (a) FR-042/043, (b) FR-044–050, (c) FR-051/052 — so each increment is auditable and the next one has an obvious place to go. Header, all three notes and item 3 now agree on **52**. |
| 16 | **Requirements did not answer the original problem** | Found while tracing the Product Owner's own experience back to requirements (§3.4). Two of six pain points had **no requirement at all**: no employer-required skills check, and no record of a decision that overrode the ranking. Separately, a hard-filter `not_matched` result had no reason, no version and no route back — the shape of the *EEOC v. iTutorGroup* failure. | **Resolved 2026-10-03 — approved and implemented.** Gap **G1** → `REQ-FR-051` (High, Phase 3). Gap **G2** → `REQ-FR-052` (High, Phase 2–3) plus override rate on `REQ-FR-035`. Gap **G3** → amendment to `REQ-FR-029` plus `jobs.screening_config_version` and a `CHECK` constraint on overrides. New table `job_assessment_requirements`, 9 new columns, stories `US-063`–`US-065`. Analysis in Feasibility Doc §2.4.1. |
| 17 | **The working name was contested** | "Match Minds" was in commercial use by at least two AI recruitment products and two unrelated software products, and was descriptive enough of what every ATS does to be hard to trademark. | **Resolved 2026-10-03 — renamed to FairFold.** Four candidates were screened (Feasibility Doc §1.4.2); FairFold had no living commercial use and `fairfold.com` / `fairfold.ai` returned no DNS record. The four `MATCH_MINDS_*.md` files were renamed and all internal links repaired. **Residual, now legal rather than naming:** a formal trademark search in Bangladesh and each target export market, domain registration, and filing in classes 42 and 35 — none done yet. Tracked as **RSK-011** at Medium/Low, §4.3. |

---

## 20. Release Criteria

The product can go to public launch when all of the following hold:

1. Phases 1–4 acceptance criteria are met.
2. Zero critical/high findings in `pip-audit`, `bandit`, and the latest ZAP scan.
3. PII-leak test confirms 100% of sampled AI request bodies are PII-free (release blocker, R7).
4. Restore test from backup succeeded within the last 30 days.
5. Rollback tested on staging in < 5 minutes.
6. GDPR export and delete verified end to end.
7. axe-core reports no critical violations; Journey Map and analytics have text alternatives.
8. Load test: 100 concurrent applicants, < 5 s response, < 1% error rate.
9. Open questions 1–3 in Section 19.1 are closed.

---

## 21. Appendix: Glossary and Traceability

### 21.1 Glossary

| Term | Definition |
|---|---|
| **AI Provider** | Abstract interface (`ai.base.AIProvider`) wrapping OpenRouter or offline fallbacks |
| **Bias Audit** | Automated check of AI rationales for biased language (for example "cultural fit" without evidence, gendered or age-related terms) |
| **Hard Filter** | Deterministic pre-AI criteria (location, visa, certifications, min years, experience level) |
| **Journey Mapping** | AI-Powered Professional Journey Mapping: resume → interactive timeline with skill evolution, impact visualization and per-job storytelling |
| **PII Stripping** | Redacting personal identifiers before data reaches any external AI service |
| **pgvector** | PostgreSQL extension for vector storage and similarity search |
| **Rationale** | Evidence-cited explanation of why a candidate matched (or not) a job |
| **Screening** | Pipeline: hard filter → pgvector ranking → LLM analysis → bias audit |
| **HTMX** | Library giving server-rendered pages SPA-like interactivity |

### 21.2 Requirement Traceability (high level)

| Objective | Requirements | Verified by |
|---|---|---|
| O1 No PII to AI | REQ-FR-011, REQ-SEC-002, REQ-COM-001/009 | AI request-body inspection, audit log |
| O2 Explainable ranking | REQ-FR-024, REQ-FR-029, REQ-FR-030 | Acceptance tests on rationale content |
| O3 Auditable bias | REQ-COM-006/008, REQ-FR-039 | Audit entry per AI action; bias test set |
| O4 Zero-cost AI | REQ-FR-028, REQ-NFR-015/017 | Cost-estimate tests, degradation tests |
| O5 Prove skill | REQ-FR-016–021 | Phase 3 acceptance criteria |

### 21.3 Reference Map

| Need | Go to |
|---|---|
| Given/When/Then for any FR | Arch Doc §4.1 |
| Complete SQL schema | Arch Doc §5.1 |
| Docker Compose, Dockerfile, Nginx, Helm, CI YAML | Arch Doc §6 |
| Use case, activity, class and ER diagrams | Feasibility Doc §3.3–3.7 |
| User stories (US-001 to US-062) | Feasibility Doc §2.4 |
| Wireframes (all 18 required screens) | `design.md` §10.5 — map in §10.0, spec-only pages in §10.6 |
| Colour tokens, contrast ratios, components, a11y rules | `design.md` §3, §6, §7, §9 |
| Traceability audit: FR↔story↔page gaps, found and closed | Feasibility Doc §2.4.1 and `design.md` §10.0 |
| Full API list, env var table, pricing detail | Complete Doc §C.12, §C.7, §C.14 |
| Maintenance, incident, release procedures | Arch Doc §8.5–8.9 |

---

*End of PRD.*
