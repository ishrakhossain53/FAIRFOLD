# FAIRFOLD — Project History

A running log of what has been done on this repository and what is still outstanding.
Kept by hand; updated whenever a chunk of work lands.

- **Repository:** `github.com/ishrakhossain53/FAIRFOLD` (private)
- **Last updated:** 2026-10-03
- **Current branch:** `ishrakhossain53-patch-1`
- **Project state:** documentation phase. No application code has been written yet.

---

## 1. Project baseline

Started from an initial documentation-only commit (`6c2632e Initial commit`, then
`67bd089 Initial Documentations`). The repository contains **no source code** — only
specifications, requirements, and supporting configuration.

| File | Lines | Role |
| --- | ---: | --- |
| `FAIRFOLD_Complete_Project_Document.md` | 2245 | **Canonical** product document — vision, personas, competitor analysis, journeys, model reference, roadmap, team roles, appendices |
| `FAIRFOLD_Project_Architecture_and_Requirements.md` | 2047 | **Canonical** specification — ADRs, 52 functional requirements, 50 non-functional requirements, 24-table SQL schema, sequence diagram, ops/runbook, risk register, acceptance criteria |
| `prd.md` | 1223 | **Canonical** product requirements — objectives, success metrics, FRs with phases, AI requirements, data model, API surface, pricing, release criteria, open questions |
| `design.md` | 1418 | Supplement — UI design system, 62 page specifications, 23 wireframes, frontend build tooling, implementation notes |
| `FAIRFOLD_Feasibility_and_Design.md` | 2778 | Supplement — feasibility study, user stories, UML diagrams, Gantt, data dictionary, accessibility, pre-development readiness review |
| `README.md` | 240 | Project overview, documentation index, setup |
| `.env.example` | 143 | 25 environment variables, all placeholders |
| `requirements.txt` / `requirements-dev.txt` | 52 / 24 | Pinned Python dependencies (planned stack) |
| `scripts/generate_secret_key.py` | 137 | Generates a per-developer `DJANGO_SECRET_KEY` + `ENCRYPTION_KEY` into `.env` |

**Key numbers of record** (verified 2026-10-03, re-verified after §2.20, §2.23, §2.24 and §2.25):

- **52 functional requirements**, `REQ-FR-001` … `REQ-FR-052` (Arch Doc §4.1)
  — was 41 until `REQ-FR-042`/`043` were added (§2.8), then 43 until
  `REQ-FR-044`–`050` were added (§2.14), then 50 until `REQ-FR-051`/`052` (§2.20)
- **50 non-functional requirements** in Arch Doc §4.2, in five groups:
  `REQ-SEC-001`–`014` (14), `REQ-COM-001`–`009` (9), `REQ-NFR-001`–`018` (18),
  `REQ-NFR-019`–`023` (5, code quality), and four operational `REQ-NFOR-001`, `-002`, `-024`, `-025`.
  ⚠️ `REQ-NFR` and `REQ-NFOR` interleave — a naive `REQ-NF` regex conflates them. Use `REQ-NFR-[0-9]+`.
- **24 database tables** in Arch Doc §5.1, with **35 foreign keys** declared (32 drawn in
  the ER diagram; 3 redundant `users` self-references intentionally omitted). The count
  went 34 → 35 when `data_deletion_requests.approved_by` was added in §2.25. `MESSAGES` is
  the one table whose FKs are `SET NULL` rather than `CASCADE` — see §2.17
- **10 AES-256-GCM encrypted fields** (PII at rest)
- **52 user stories / 217 story points**, MoSCoW **30 Must / 17 Should / 5 Could** —
  every one of the 52 FRs maps to at least one story (verified programmatically)
- **62 pages specified** in `design.md` §10; **36 have wireframes** (23 drawings), covering
  all 18 required screens and all 22 core-flow pages; 53 of 62 pages carry a requirement ID
- 5 roadmap phases: Phases 1–4 = weeks 1–12 (MVP), Phase 5 = week 13+ (optional)

---

## 2. Work completed

### 2.1 Security audit — `.env` and credential hygiene ✅

- **Result: no leak.** `.env` is not tracked and does not exist on disk.
  `.gitignore:12` ignores it, with a `!.env.example` negation on line 14.
- Only `.env.example` is tracked, and every value in it is a placeholder
  (e.g. `change-me-generate-a-real-key`, `devpassword`).
- Tracked files scanned for AWS keys, OpenAI keys, GitHub tokens, Slack tokens,
  Google API keys, PEM private-key headers, and JWTs — **no real credentials found**.
  `prd.md`, `design.md` and the rewritten `design.md` were each re-scanned on 2026-10-03: clean.
- `scripts/generate_secret_key.py` confirms the intended model: each developer generates
  their **own** secret and encryption keys, so keys must never be shared between machines.
- **Push state:** `git fetch` / `ls-remote` fail in this environment
  (`could not read Username for 'https://github.com'`), so live remote verification is not
  possible from the agent side. The user pushes manually.

### 2.2 Specification gap audit ✅

Both original documents were read end to end and checked against a 20-item academic /
engineering specification rubric. **8 content gaps** were identified; all but two are now closed.

### 2.3 `FAIRFOLD_Feasibility_and_Design.md` ✅

A companion document covering the diagramming, planning and feasibility gaps. Added as a
**standalone file** rather than as edits to the existing specs, because the canonical
documents use dense cross-references (`§5.6`, `§C.7`, …) that in-place edits would invalidate.

Contents: 5 Mermaid diagrams (use case, activity, class, ER, Gantt), all grammar-validated;
five-part feasibility study (§2.6.1–2.6.5); 49 user stories / 199 points with every FR traced;
data dictionary for the 6 core entities; methodology, Gantt, roles and risk register
(§2.7.1–2.7.4); navigation tree; WCAG 2.1 AA table; coverage checklist (§4).

Content from the canonical specs is **cited, not duplicated**, to prevent drift.

| Commit | Change |
| --- | --- |
| `5e74189` | Added as `FAIRFOLD_Academic_Submission.md` |
| `0486ee1` | Renamed to `FAIRFOLD_Feasibility_and_Design.md` (git recorded a 96% rename) |
| `b16b7a6` | Fixed the wireframe FR citation for the job-browse screen |
| `c7d8c00` | Added `HISTORY.md`; fixed a misaligned table row |
| `96993d4` | FR count 41 → 43; GAP-1/GAP-2 closed; story-point split reconciled; `resource_id` → UUID |
| `36ccdb6` | Synced to the expanded `design.md`; wireframes 3 → 23; recorded round-2 gaps |
| *(uncommitted)* | Round-2 gaps closed: FR count 43 → 50, stories 42 → 49, points 170 → 199 |
| *(uncommitted)* | Team roster replaced with the current five members across all six documents |
| *(uncommitted)* | Feasibility doc now lists prd.md and design.md in its document table and reference convention |
| *(uncommitted)* | Gantt re-based; `employer_team_members` added; message soft-delete; name-reveal and all 14 §19.2 items decided; versions bumped |
| *(uncommitted)* | FR count 43 → 50; stories 42 → 49; §2.4.1 round 2 closed; §3.9.1 rewritten; checklist rows 7, 9, 17 updated |

### 2.4 Corrections made during a self-audit ✅

| Item | Wrong | Correct |
| --- | ---: | ---: |
| Non-functional requirements | 46 | **50** |
| User stories | 33 | **42** |
| MoSCoW split (Must/Should/Could) | 21 / 14 / 4 | **26 / 13 / 3** |
| Foreign keys | 24 | **27** declared (25 drawn in the ER diagram) |
| Encrypted fields | 8 | **10** |

Also: a **Mermaid grammar bug** (`UC43([Export personal data (GDPR)])` — the stadium shape
`([…])` cannot contain inner parentheses); **missing stories** for `REQ-FR-003`/`007`; a
**duplicate story ID** (`US-051` renumbered to `US-051`…`US-055`); and a **reference
convention** note explaining `§N.M` across three documents.

### 2.5 README ✅

Documentation table linking all six documents with a **role** column (Canonical vs Supplement)
and a "start here" line.

### 2.6 Wireframe cross-reference bug ✅

§3.9.1 cited `REQ-FR-022` ("Job Application") for the job browse screen — that requirement is
about *applying*, not *browsing*, which hid the GAP-1 hole. Corrected; all 23 other FR
citations in the table were re-verified.

### 2.7 `prd.md` added ✅ (team, 2026-10-03, commit `6a50343`)

A full PRD: objectives and success metrics, non-goals, personas, market positioning, phases
and MVP definition, FRs with priority and phase, AI requirements (PII stripping, matching
funnel, provider abstraction, graceful degradation, explainability), NFRs, security and
compliance, data model, architecture, API surface, UX and information architecture,
monetization, operations, risks, and a **14-item inconsistency register (§19.2)** that
usefully cross-checked every other document in the repo.

### 2.8 GAP-1 and GAP-2 closed ✅

`prd.md` §7.2–7.3 proposed `REQ-FR-042` (Job Browse and Search, High, Phase 1) and
`REQ-FR-043` (Candidate–Employer Messaging, Medium, Phase 3), each explicitly marked
*proposed*. **Approved by the team and promoted into the canonical Arch Doc §4.1** as a new
*Job Discovery & Messaging* group, with Given/When/Then acceptance criteria.

Three conditions were written into the requirements rather than left to implementation guesswork:

- **REQ-FR-042** — an employer name is not disclosed until the employer opts in; a public job
  board otherwise leaks company identity by default.
- **REQ-FR-043** — messages are excluded from all AI processing and never reach an external
  provider, and deleting one party **soft-deletes** rather than removes the counterparty's copy
  (the cascade problem in §3.7).

Downstream: FR count 41 → 43 everywhere; §2.2 gained a fifth group row; `US-023`/`US-050` now
carry real FR IDs; §3.9.1 row 4 cites FR-042.

### 2.9 Three drift bugs found and fixed ✅

The PRD's inconsistency register exposed real errors in documents written earlier:

| Bug | Was | Now |
| --- | --- | --- |
| **Phase story points did not reconcile** | 21 + 34 + 31 + 30 + 25 = **141**, against a stated 170-point total | Re-split to 28/41/37/36/28 = **170**, with a note that these are planning estimates to be re-estimated at sprint planning |
| **`AuditLogEntry.resource_id` type conflict** | `INTEGER` in the class diagram, ER diagram and data dictionary; Arch Doc §5.1 says `UUID` | `UUID` everywhere — core entities all use UUID PKs |
| **Gantt ran backwards** | Started `2026-01-05`, nine months before the documents were dated | **Fixed** — re-based to kickoff 2026-10-05 (§2.16) |

### 2.10 `design.md` added, then expanded ✅ (team, commits `34fbe78` + revision)

**First version (733 lines)** — a UI design specification: brand and voice with a verbatim
microcopy library, colour tokens with 16 verified contrast ratios, typography, spacing and
grid, app shell, 19 generic + 10 product-specific components, a state matrix, HTMX
interaction patterns, 13 accessibility rules, **62 page specifications**, 3 wireframes, and
implementation notes (CSS variables, Tailwind config, template tree, performance budget).

**Revision (1,323 lines)** — wireframes went from 3 to **23**, plus three new sections:

- **§6.6 Component State Sheet** — every component's states rendered as text
- **§10.0 Read This First: Markers and Coverage** — a marker legend, the 18-screen → page →
  wireframe map, a coverage summary, and **a new traceability-gap table** (see §2.12)
- **§10.6 Still Not Drawn** — the 26 pages with a spec but no wireframe
- Each wireframe now carries an **`A11y:` annotation line**, so accessibility is specified
  per screen rather than only as a general rule set

All of `design.md`'s own claims were independently verified against its page tables: 62 pages,
36 drawn, 22/22 core-flow pages drawn, 9 pages without a requirement ID, and the §10.6
26-page list — **all consistent**.

### 2.11 Wireframe gap closed ✅

The gap that was ⚠️ 3-of-18 is now **complete for low fidelity**: 23 wireframes (`S01`–`S18`
for the required screens, `X01`–`X05` for the remaining core-flow pages) covering 36 of 62
pages, including **all 18 required screens** and **all 22 core-flow pages**. `Feasibility
§3.9.1` was rewritten to match, and its coverage-checklist row moved from ⚠️ to ✅.

### 2.12 Second round of traceability gaps found ✅ then closed

The first gap pass worked from use cases and journeys. The second worked from `design.md`
§10, which names the requirement behind all 62 pages — and surfaced **7 further pages that
built a real feature with no functional requirement**: #19 certifications, #33 employer
onboarding, #34 employer dashboard, #49 team and roles, #50 billing and plan, #61 assessment
management, #62 broadcast announcement. Same failure mode as GAP-1/GAP-2; the first pass
missed them because they are supporting features rather than core journeys.

### 2.13 Round-2 gaps closed ✅

All seven are now in the Arch Doc §4.1 as a new *Employer Organisation, Billing & Content*
group, each with Given/When/Then criteria and a matching user story (`US-056`–`US-062`).

| Page | Requirement |
|---|---|
| #19 Certifications | `REQ-FR-044` Certification Management (Medium, P3) |
| #33 Employer onboarding | `REQ-FR-045` Employer Company Profile (High, P1) |
| #34 Employer dashboard | `REQ-FR-046` Employer Dashboard (Medium, P1) |
| #49 Team and roles | `REQ-FR-047` Employer Team and Roles (Medium, P1–4) |
| #50 Billing and plan | `REQ-FR-048` Billing and Plan Management (Medium, P5) |
| #61 Assessment management | `REQ-FR-049` Assessment Management (Medium, P3) |
| #62 Broadcast announcement | `REQ-FR-050` Broadcast Announcement (Low, P4, **optional**) |

Four conditions were written in rather than left to implementation guesswork:

- **REQ-FR-045** — a job cannot be activated until a company profile exists, which stops an
  anonymous employer from posting.
- **REQ-FR-047** — the last `employer_hr` cannot be demoted or removed, which would otherwise
  orphan the account.
- **REQ-FR-048** — subscription state updates on the Stripe **webhook**, not the browser
  redirect, so a failed webhook leaves the subscription unchanged rather than half-updated.
- **REQ-FR-050** — an empty audience match must report rather than silently succeed.

The Arch Doc now holds **50 FRs**, and all 50 map to at least one of the **49 stories**
(199 points). FR↔story↔page traceability now holds across all 62 pages except #1 and #2
(landing, pricing), which are marketing pages and correctly need no requirement.

### 2.14 Team roster replaced ✅

The four original team members were removed from every document and replaced with the
current five. Roles, not just names, were updated:

| Person | Role | Notes |
|---|---|---|
| Sardar Shihab | Full-Stack Engineer | Was frontend-only; now also takes backend endpoints |
| Arnob Biswas Antu | Frontend Engineer | Employer dashboard, application review, scheduling UI |
| Ishrak Hossain | Backend & AI Engineer | Also absorbs DevOps — the declared gap |
| Mohammad Abdul Ahad | UI/UX Designer | Owns the design system: tokens, components, WCAG 2.1 AA |
| Fahad Haque | UI/UX Designer | **New member** — wireframes and journey-map interaction design |

The fifth member splits what was one person's job in two: **Mohammad Abdul Ahad** takes the
design system (tokens, component library, accessibility — the parts already specified in
`design.md` §3, §6, §9, §11.1), and **Fahad Haque** takes the wireframes and journey-map
interaction design (§10.5). `design.md` now lists both as owner and co-owner.

Also updated: the three "4-person team" claims in the feasibility study became 5-person,
the DevOps gap line in all three docs, and the minimal-viable answer for the outstanding
requirement-collection question.

### 2.16 Gantt re-based to the document date ✅

The chart started `2026-01-05`, nine months before the documents were dated, so it ran
backwards. Re-based to **kickoff Monday 2026-10-05** — the first working day after this
specification set was completed (`prd.md` and `design.md` are dated October 2026).

| Milestone | Weeks | Ends |
|---|---|---|
| Phase 1 — Foundation | 1–3 | Fri 2026-10-23 |
| Phase 2 — AI Integration | 4–6 | Fri 2026-11-13 |
| Phase 3 — Candidate AI | 7–9 | Fri 2026-12-04 |
| Phase 4 — Hardening | 10–12 | Fri 2026-12-25 |

> ⚠️ **The Phase 4 milestone lands on Christmas Day.** A 5-person student team losing
> ~2 weeks a year to holidays will not finish a 12-week plan starting in October without
> slipping. The doc now says so, and suggests either starting earlier or planning a
> **demo at the end of Phase 3 (early December)** with the hardened build as a January
> continuation. The phase *durations* are the commitment; the dates are a plan.

### 2.17 Two schema holes closed ✅

Both were found while auditing what `REQ-FR-042`–`050` had opened up.

**`messages` cascade.** `REQ-FR-043` mandated soft-delete, but all three FKs in Arch Doc
§5.1 were `ON DELETE CASCADE` and there was no `deleted_at` column — the requirement and
the DDL contradicted each other. `application_id`, `sender_id` and `recipient_id` are now
`ON DELETE SET NULL`, with `deleted_at` and `deleted_by_user` added plus two indexes. On
erasure the row is **retained** with `content` blanked and the party references nulled, so
the counterparty keeps a thread with a visible gap rather than losing it silently.
`INTERVIEWS` still cascades deliberately — an interview has no separable half.

**No team-member table.** `REQ-FR-047` requires inviting, re-roling and removing
colleagues, but `EmployerProfile.user` is `OneToOneField`, so **an employer company could
have exactly one person** — the requirement was unimplementable. Added
`employer_team_members` (the 22nd table) with `UNIQUE(employer_id, user_id)`, a `CHECK`
constraint limiting `role` to the three defined employer roles, and `invite_status`.
Propagated to the Complete Doc model list, `prd.md` §11.1–11.2, the class diagram, the ER
diagram, and the data dictionary (two new sections). Counts updated: **22 tables, 30 FKs,
28 relationships drawn.**

### 2.18 Candidate name reveal decided — at shortlist ✅

`design.md` §12 and `prd.md` §19.2 item 4 both left this open, and it changes pages #40
and #41. **Decided: reveal at shortlist.** Rationale — anonymised screening *is* the
product's core claim, so identity must stay hidden for exactly as long as the ranking
decision is being made, and no longer.

Written into `REQ-FR-029` and `REQ-FR-030` rather than left as a UI note: employers see
anonymised text only while screening; on shortlist the name becomes visible **to that
employer only** and the reveal writes an audit entry; unrevealed PII is never sent to an
external AI provider.

### 2.19 All 14 `prd.md` §19.2 items resolved ✅

| # | Decision |
|---|---|
| 1–2 | Complete Doc is canonical for pricing |
| 3 | Closed — `REQ-FR-042`/`043` |
| 4 | Reveal at shortlist (§2.18) |
| 5 | **Two retention classes** — `access` audit entries rotate at 90 days; `ai_decision` entries are retained with the application (2y, 5y if hired). 90 days would destroy the only evidence a hiring decision was unbiased |
| 6 | Closed — `resource_id` is `UUID` |
| 7 | **Both** — Django sessions for the HTMX UI, short-lived JWT for the API |
| 8 | Configuration, not assumption — free model IDs live in `.env`; the offline fallback preserves $0-cost |
| 9 | Django 5.2 LTS |
| 10 | Closed — Gantt re-based (§2.16) |
| 11 | Closed — 41/41/45/39/33 = 199 |
| 12 | **Claim narrowed** — see below |
| 13 | Interview recording removed from the Professional tier, in both documents |
| 14 | Offer letter stays Low/Phase 5 |

**Item 12 changed a claim the docs could not support.** Three documents asserted the bias
audit "flags 100% of biased language in test dataset" — as an acceptance criterion in the
Arch Doc and Complete Doc, and in the Phase 2 milestone. **No versioned test set exists**,
so that number is unverifiable and would fail CI forever. Replaced with the deterministic
keyword pass as the only checkable target; the LLM pass is now explicitly **advisory** and
may not block auto-shortlist. Building the test set is a Phase 2 task.

### 2.15 Fixes to `design.md` itself ✅

Three stale or wrong items inside the revised file:

- `REQ-FR-042 (proposed)` → `REQ-FR-042`, since it was promoted to the Arch Doc
- Four traceability-gap rows said *"Add an FR to the PRD"* — but functional requirements live
  in the **Arch Doc §4.1**, not the PRD. Corrected, with the next free IDs named.
- A cross-reference to *"the PRD, Section 19, item 4"* → made precise as
  ``prd.md §19.2 item 4 (PII retention)``

### 2.20 The PRD addendum applied — Parts A–E ✅

A structured addendum was supplied on 2026-10-03 with three parts of new material, three
proposed gaps and one documentation bug. It carried an honesty rule of its own — every
statement tagged **[Done]** / **[Illustrative]** / **[Planned]** — and that rule was kept
intact rather than flattened into confident prose.

| Part | What it was | Where it went | Effect |
|---|---|---|---|
| **A** — requirement collection | How requirements were actually gathered | Feasibility §1.3.1–1.3.5, new `prd.md` §3.4 | Closes gap **A** — the last 🔴 blocker |
| **B** — real-world evidence | Amazon 2018, iTutorGroup, HireVue, Mobley, three BD sources | Feasibility §1.2.1–1.2.2, `prd.md` §1.2 | Closes gap **B**; produced Gap G3 |
| **C** — existing products | Overlap by job-to-be-done; name clash | Feasibility §1.4.1–1.4.3, `prd.md` §4.1–4.3 | New naming risk **RSK-011**; "different not better" wording adopted |
| **D** — gaps G1–G3 | Two pain points with no requirement; one filter that could not be reviewed | Arch Doc §4.1, §5.1, §9, §10; `prd.md` §6.3, §7.3, §11, §13, §17.4 | `REQ-FR-051`, `REQ-FR-052`, amendment to `REQ-FR-029`, extension of `REQ-FR-035` |
| **E** — sources | Citation list | Carried inline with each claim | — |

**Gap A closed honestly, not conveniently.** The last open item in the whole specification
was *"state how requirements were gathered — do not claim research that was not
conducted."* It is now filled in from the Product Owner's own account (lived experience of
a hiring process decided by internal lobbying with no skills check, corroborated by friends
who joined the team and by a university senior), with **[Planned]** used to mark the
validation plan that has **not** been run. Fabricating an N for the tables would have closed
the item faster and destroyed the document.

**Round 3 found a different class of gap than rounds 1 and 2.** Rounds 1 and 2 worked
*outwards from the specification* — use cases, journeys, then pages — and found
*capabilities with no requirement*. Round 3 worked *inwards from the problem* and found
*requirements that do not answer the problem that started the project*: pain point P2 (no
skills check) and P5 (the selection could be bypassed) had no requirement at all. That is
harder to see, because the document looks complete.

| Gap | Finding | Resolution |
|---|---|---|
| **G1** | Assessments were candidate-initiated only, so an employer could shortlist on a resume with no skill evidence | `REQ-FR-051` Employer-Required Skill Assessment (High, Phase 3) |
| **G2** | Nothing recorded a shortlist or rejection that went **against** the ranking — anonymised ranking is worthless if it can be quietly ignored | `REQ-FR-052` Override Visibility and Record (High, Phase 2–3) + override rate on `REQ-FR-035` |
| **G3** | A hard-filter `not_matched` had no reason, no version and no route back — the exact shape of *EEOC v. iTutorGroup*, where a hard-coded age filter *was* the discriminating mechanism | Amendment to `REQ-FR-029`; `jobs.screening_config_version`; a `CHECK` constraint on overrides |

Three decisions inside those are worth remembering because each could reasonably have gone
the other way:

- **An override is recorded, not blocked.** REQ-FR-052 requires a written reason and an
  `ai_decision`-class audit entry, but the employer can still do it. A human stays the
  decision-maker. What the requirement buys is that an informal decision becomes *visible
  and countable* — which is the most "bias-free" the product can honestly be.
- **A filter may produce `not_matched`, never `rejected`.** Only a person can reject a
  candidate. This makes `prd.md` §8.1 true at the schema level.
- **Filter rules are versioned, not just recorded**, so "which rule excluded this?" is
  answerable a year later after the job has been edited five times.

**Schema:** +1 table (`job_assessment_requirements`), +9 columns on `jobs` and
`applications`, +1 `CHECK` constraint, +2 indexes. Counts updated: **23 tables, 33 FKs,
52 FRs, 52 stories / 212 points** — all verified programmatically.

**The housekeeping bug was real.** `prd.md` said "50 FRs" in the header and 50 in §19.2
item 3, but the 2026-10-03 update note under *Source documents* still said *"now holds 43
FRs, not 41"* — a leftover from earlier the same day that was never updated when seven more
requirements landed. Replaced with three dated notes (a) 042/043, (b) 044–050, (c) 051/052
so each increment is auditable and the next one has an obvious place to go. Logged as
`prd.md` §19.2 item 15. A second bug found at the same time: `Complete Doc` §C.11 still had
`AuditLogEntry.resource_id = IntegerField` while every core entity uses a UUID — corrected.

**A "bias-free" claim that could not be supported was replaced, not repeated.** Part C.3's
status column was adopted verbatim — three of seven differentiation claims are *Designed,
not yet measured*. `prd.md` §4.2 now carries approved wording that claims *different*
rather than *better*. The claim went further in §2.22: the word was removed from the
product subtitle in every document rather than being kept and annotated.

---

### 2.21 🔴 The working name was contested — ✅ resolved: the product is **FairFold**

Found while applying Part C, not by the plan. Recorded because the *reasoning* is worth
more than the rename.

**Why the old name was abandoned.** Verified 2026-10-03 (web search + DNS resolution):

| Finding | Evidence |
|---|---|
| **MatchMindAI** (matchmindai.com) already markets an AI-powered recruitment platform matching candidates to jobs | Search result; domain resolves to a live host |
| **"MatchMinds"** is *also* used by an AI-powered recruitment platform | Public post describing itself as "an AI-powered recruitment platform and the next frontier in hiring" |
| **"MatchMinds"** is additionally used by an unrelated Android football-prediction app, and by an unrelated teammate-recommendation system | Two further commercial uses of the same string |

Three unrelated commercial spaces, one of them recruitment. "Match Mind" is also
descriptive of what every ATS does, which makes it hard to register as a word mark and hard
to defend even once registered.

**Replacement candidates screened the same day:**

| Candidate | Meaning | Domains with no DNS record | Outcome |
|---|---|---|---|
| **FairFold** | fair + a folded resume | fairfold.com, fairfold.ai | ✅ **Selected** |
| **Niyoti** (নিয়তি) | Bengali for impartiality; matches both the thesis and the BD beachhead | niyoti.app, niyoti.io | Not chosen — a common Bengali given name, so a bare word mark is hard to own |
| **SightFold** | you can *see* the reasoning | sightfold.com | Not chosen — coined, so colder as a brand |
| **Evidencefold** | evidence-cited rationale | evidencefold.com | Not chosen — long and clunky in a logo |

Rejected in the same sweep: Meritfold (already a UK public-sector bid product), Sightline,
Clearscreen, Showwork, Foldwork, Talentfold, Skillfold, Plainfold, Proofhire, Openrank,
Rankfold, Foldscore, Meritly, Fairhire — all taken.

**Why FairFold works.** "Fair" states the intent. "Fold" carries the résumé being opened
and read — the moment the product intervenes on. It names the *artefact* rather than the
feature, which is the thing a competitor cannot copy by adding a checkbox. No living
commercial use of the string was found.

**What changed.** `MATCH MINDS` → `FAIRFOLD` and `Match Minds` → `FairFold` across all
seven documents, `.env.example`, `.gitignore` and `scripts/generate_secret_key.py`; the
three `MATCH_MINDS_*.md` files renamed via `git mv`; every internal link repaired. The
three `MatchMinds` references left in place are in the risk sections and describe *other*
people's products — renaming those would have made the risk register say FairFold
conflicts with FairFold.

**Two caveats that survive the decision.** "No DNS record" is not proof a domain is
available — a parked or newly-registered domain may simply have no A record. And a web
search is not a trademark clearance.

**🟡 Residual, now legal rather than naming.** **RSK-011** stays on the register,
downgraded from **High/High to Medium/Low**: commission a formal trademark search in
Bangladesh and every target export market, register `fairfold.com` / `fairfold.ai` before
any public announcement, and file the word mark in classes 42 and 35 per market. **None of
that has been done.** `design.md` §12 item 5 is unblocked for logo work but carries the
caveat that nothing should go on public collateral until the search returns.

---

### 2.22 "Bias-free" removed from the product subtitle

The second flag. Every document described the product as an "AI-Powered, **Bias-Free**
Recruitment Platform" and the README opened with "Eliminates unconscious bias". None of
that is measured. The bias audit and disparity analysis that would support it
(`prd.md` §8.7) have not run, and item 12 of §19.2 had already narrowed a related claim
for exactly this reason.

**Replaced with "AI-Powered, Explainable Recruitment Platform"** in all five places the
subtitle appeared, plus two prose uses ("bias-free ranking" → "evidence-cited ranking").
The difference matters: *explainable* is a claim about **process** — every score carries
cited evidence, every action writes an audit entry, and it can be checked on any given
decision today. *Bias-free* is a claim about **outcomes**, across a population, over time,
which nothing in this repository can support yet.

"bias-free" now survives only where it is attributed to a competitor's marketing or
labelled explicitly as the aspiration §8.7 would have to earn. Both the README banner and
`prd.md` §4.2 say so in writing, with a do-not-reintroduce instruction.

This is the same discipline as §2.19 item 12: **narrow the claim until the evidence
exists, rather than shipping a promise and hoping.** A tagline that has to be walked back
after a discrimination complaint costs more than it ever won.

---

### 2.23 Pre-development readiness review — 9 conflicts fixed, 5 new gaps opened

The question asked was *is the documentation complete enough to start building?* The
answer is a new section — `FAIRFOLD_Feasibility_and_Design.md` **§5, Pre-Development
Readiness Review** — which consolidates the file inventory, the verification run, every
conflict, and the open list in one place.

**Nine conflicts were found and settled.** All nine were contradictions between two
documents, or between a document and the code. None was a missing idea.

| # | Conflict | Settled as |
|---|---|---|
| 1 | Django project package: Complete Doc implied `fairfold/`, everything else assumed `config/` | **`config/`**; all lint/test/coverage commands corrected |
| 2 | SQLite fallback offered in settings comments, but pgvector does not exist in SQLite | **No SQLite fallback.** Postgres + pgvector for local and CI; SQLite only for tests touching no `VectorField` |
| 3 | A 7-key Redis cache strategy was specified in two documents with **no Redis cache backend in `requirements.txt`** | **`django-redis` added** |
| 4 | `django-ratelimit` defaults to local-memory cache, so under gunicorn every worker enforced its own limit — not a limit | Documented as **must** use the Redis cache |
| 5 | `drf-spectacular` sat in dev deps while `prd.md` §13 serves the schema in production | **Moved to `requirements.txt`** |
| 6 | Stack-matrix version drift (DRF 3.14 vs 3.15.1; "Django Templates 5.x" in a version column) | Corrected to match `requirements.txt` |
| 7 | Free employer tier missing from the pricing table | **Added** — the `subscriptions` table already implemented it |
| 8 | Free plan described as a "Trial" | **"Not time-limited"** — the schema has no expiry column |
| 9 | "a focused team of 4" | Corrected to **5** |

**The rule used to settle them: the executable artefact wins.** The SQL schema,
`requirements.txt` and `.env.example` can be checked; prose cannot. Where two documents
merely disagreed and neither was executable, the canonical document's version was applied
and the stale one corrected.

**Two of these would have failed on day one of a build.** Conflict 1 breaks
`manage.py`, `pytest` and `flake8` immediately. Conflict 2 fails at the first migration,
because a `VECTOR(384)` column cannot be created in SQLite. Conflict 3 means the
documented cache strategy simply cannot be implemented.

**The rename had missed the infrastructure.** The previous commit replaced
`Match Minds` and `MATCH MINDS` case-sensitively but **missed every lowercase
`matchminds`** — 26 occurrences, and they were the ones that mattered: Docker service
names, `POSTGRES_DB` and `POSTGRES_USER`, the CI database `matchminds_test`, container
names used in every README command, image tags `matchminds/app`, staging and production
hostnames, the pytest coverage target, and the email sender domain. A repo-wide,
case-insensitive sweep is now recorded as the rule in §5.2.

**Five new gaps opened** by this review — **O** frontend build tooling unspecified, **P**
`libmagic`/`ClamAV` are OS packages never checked in the Dockerfile, **Q** `torch>=2.3.0`
pulls the multi-gigabyte CUDA wheel by default and contradicts the 2–4 vCPU assumption,
**R** no migration/seed-fixture strategy, **S** the double-shift assumption is unvalidated
(`ASM-002`).

**Verdict: complete enough to start Phase 1.** Two blockers remain, both cheap: the
incomplete API list in `Complete Doc §C.12`, and the Phase 4 milestone falling on
25 December.

---

### 2.24 Three answers and a fourth question — milestone moved, AI recorded, `REQ-FR-050` fixed

**1. Phase 4 milestone → Thu 2026-12-24.** ✅ Option A chosen. The one day of Phase 4
work moves into the Phase 3 buffer and the team is off on 25 December. Kept: the original
reasoning, because "25 December is a holiday regardless of staffing" is the reusable part.
Double shifts never touched the calendar — they fixed capacity, which was a different
problem.

**2. The team is using AI to produce code, and that is why 217 points fits 12 weeks.**
Recorded as §2.6.4.2 with assumption `ASM-003` and risk **RSK-012** (High/High).

The throughput claim is well founded — Django models, serializers, migrations and admin
registrations are where the typing was, not the judgement. The claim that also needs
saying out loud is that **AI raises throughput, not correctness**, and for *this*
product the distinction is the whole business. The differentiator is that FairFold does
not assert anything it cannot evidence, so a confidently-wrong codebase is a worse
outcome here than a visibly incomplete one.

Four controls are now written down rather than assumed:

- Acceptance criteria in Arch Doc §4.1 are written **before** the test. A test derived
  from the implementation agrees by construction and proves nothing.
- No generated code merges without a human reading it. The 80% coverage gate is a
  backstop, not a plan.
- Auth, encryption, PII stripping and the `chk_override_has_reason` constraint are a
  **no-AI-review-list** — a named human reads those.
- Add a licence scan to CI; `bandit`, `pip-audit` and `safety` are already there.

`ASM-003` is deliberately split in two, because only one half is an optimisation: the
throughput half and the review-capacity half. If the second fails, the answer is to drop
the throughput assumption — **never** to reduce review.

**3. What goes wrong if `REQ-FR-050` is kept?** The question found the most serious defect
in the specification. **`REQ-FR-050` had no database table at all.** It was approved in
scope, given page #62 and an endpoint, and had nowhere to store the announcement, its
audience, its schedule or who it received it. `notifications` cannot substitute — it has
one `recipient_id`, so it records that someone *was notified* but never *what was
announced, to whom, or whether it was sent*.

Fixed, plus four problems the original criteria never covered:

| What goes wrong | Severity | Fix |
|---|---|---|
| No data model | 🔴 Blocks the feature | `announcements` table added |
| A **wrong** audience is a confidentiality incident, not a UI bug — the criteria only caught the *empty* case | 🔴 High | Role re-checked at send + `resolve-audience` preflight |
| A bulk send shares a provider and domain with verification and password-reset mail, so a burst can rate-limit the domain **and break account access for everyone** | 🔴 High | Separate sending subaddress + hourly cap |
| `REQ-FR-041` hard-deletes user data, but a snapshot audience will email a since-deleted account | 🟡 | Audience resolved at **send** time, suppression list, `skipped_count` |
| A Celery retry double-sends, and a broadcast cannot be recalled | 🟡 | `idempotency_key` unique, set before the task runs |

**Re-estimated 3 → 8 points.** The original estimate was for the *page*, not the feature.
Phase 4 moves 39 → 44; total 212 → **217**. Recommendation: keep, as a Phase 4 item and
never as a launch dependency. If cut, `REQ-FR-050` + `US-062` + page #62 + the
`announcements` table go together, and that coupling is written into the requirement so a
partial cut cannot leave a phantom table.

**4. What is wrong overall, and what can be fixed without writing code** — the standing
answer is §5 of the feasibility document. As of this commit:

- **🔴 24 tables, 34 FKs, 13 indexes, 52 FRs, 52 stories / 217 points** — all
  machine-verified, 5/5 Mermaid diagrams parse, 0 dangling references.
- **One blocker left: the API list.** `REQ-FR-050`'s five endpoints were written today;
  `REQ-FR-042` (public browse/search), `REQ-FR-040/041` (GDPR export/delete), `REQ-FR-047`
  (teams) and `REQ-FR-049` (assessment authoring) are still unwritten. **That is ~90
  minutes of documentation work and nothing else is blocking a build.**
- **Six gaps open that need no decision** (O–R, plus the two new component screens) —
  frontend build tooling, `libmagic`/ClamAV OS packages, the `torch` CUDA wheel, and the
  migration/seed strategy. All are documentation or first-hour-of-Phase-1 work.
- **Five items need a person, not a document:** trademark filing, the Phase 2 bias test
  set, SCCs / cross-border transfer, Figma work, and the `REQ-FR-050` keep-or-cut call.

---

### 2.25 The four items closed — review list, `ASM-003`, the API list, and gaps O–R

Four items were open from §2.23–§2.24. All four are now closed. Two of the closures
changed something downstream rather than just ticking a box, and one of them found a
defect that only appeared because the work was done in the right order.

#### 1. The no-AI-review-list is now eight files, not four topics

§2.24 listed auth, encryption, PII stripping and `chk_override_has_reason`. That was a
list of *topics*, and a topic cannot be reviewed — "auth" is nine files. The list is now
eight concrete paths (`Feasibility §2.6.4.2`):

| # | Path | Why it is on the list | Enforced by |
|---|---|---|---|
| 1 | `accounts/` — auth, MFA, lockout, JWT issuance and rotation | A wrong answer here is an authentication bypass. Every other control is downstream of this | Integration tests per path; `bandit` |
| 2 | `candidates/` — PII stripping and resume encryption | The product's core claim is that names do not reach the employer. A silent stripping regression sends personal data to the wrong reader | Round-trip tests asserting the encrypted value never decrypts to plaintext in a template |
| 3 | `ai/` — **rationale citation check** | Flagged as the single highest-risk file in the product: it produces the evidence a human uses to reject a candidate, and an uncited or fabricated citation is exactly the failure the product claims to prevent | The citation check is itself the test; human reads the diff |
| 4 | `ai/` — bias-audit keyword pass | A missed proxy term is invisible by construction — the output looks fine | Versioned bias test set (Phase 2) |
| 5 | `matching/` — embeddings, pgvector, Stage-1 filters | A ranking bug is not an error message, it is a different shortlist | Golden-set comparison of top-N against a stored expected list |
| 6 | `employers/` — shortlist, reject, assessment gate | Employer actions are the decisions the product is accountable for; `REQ-FR-051`/`052` gates live here | Constraint tests |
| 7 | All migrations | Schema drift is invisible until a deploy. `makemigrations --check` in CI is now part of this (§2.25 item 4) | CI |
| 8 | Any Celery task that sends or mutates | A retry double-sends, and an email cannot be recalled | `idempotency_key`, task tests |

> The list is not "risky files" — it is **files where a wrong answer is invisible.** That
> is the criterion, and it is stated so that a new file can be tested against it instead of
> argued onto or off the list by seniority.

The review obligation was also promoted: it is no longer one of four *controls* alongside
bandit and pip-audit, it is a **mandate**. The scanning tools stay; they are a backstop,
not the plan.

#### 2. `ASM-003` corrected — it was not falsifiable

The old text read *"AI assistance increases development throughput without reducing review
capacity."* Two problems, both mine:

- **The second half cannot fail.** No measurement distinguishes "review capacity held" from
  "review quietly got thinner". A test that cannot fail is not a test, and calling it one
  invited exactly the silent-deferral failure `ASM-002`/`RSK-012` describe.
- **The basis column asserted a conclusion.** It said the throughput half *"is well
  founded"* — which is the finding, stated as the evidence. Plausible-for-boilerplate is
  what we actually know, because nobody has measured this team's output yet.

Rewritten: **`ASM-003` — AI assistance raises delivery capacity for the 217 points.**
Basis: *plausible for boilerplate; **unmeasured***. **Tested at the end of Phase 1**
(41 points / 3 weeks) against the story points actually accepted. If it fails, the 217
reverts to a double-shift-hours calculation and Phase 2 is re-scoped — **never** by
reducing review.

`ASM-001` was added so the ID series starts at 001: *the 52 requirements are the right MVP
scope.* Tested at the end of Phase 1; if it fails, **cut `REQ-FR-050` first** — it is the
only requirement whose removal is clean, because its three artefacts are coupled by
design.

#### 3. The API blocker is closed, and writing it found two schema holes

All five missing groups written into `Complete Doc §C.12`: `jobs/public/` (`REQ-FR-042`),
`gdpr/export/*` + `gdpr/deletion/*` (`REQ-FR-040/041`), `employers/team/*` (`REQ-FR-047`),
`assessments/*` authoring (`REQ-FR-049`). Details worth keeping:

- **Public job browse** withholds the employer name by default, and returns **404, not
  403**, for a hidden draft — a 403 confirms that a private job exists.
- **GDPR export/delete is admin-approved, not self-service.** Deletion needs a typed
  confirmation, a defined cascade order, and audit rows that are **never** deleted.
- **Team management** forbids removing or demoting the last `employer_hr`, enforced in the
  serializer inside the same transaction as the update.
- **Assessment authoring has no DELETE route.** Deactivation only — a deleted assessment
  would orphan every candidate attempt. Reordering takes an explicit `question_ids` list
  rather than a positional patch.

**Two columns appeared only because the endpoints were written, not because the schema was
read.** This is the useful part:

| Hole | Why the endpoint needed it | Now |
|---|---|---|
| `employer_profiles.show_company_name` | `GET /jobs/public/` must decide whether to expose an employer to an unauthenticated caller, and a stored per-employer preference is the only honest way — inferring it from "is this the default" makes anonymity a side effect of lazy data entry | `show_company_name BOOLEAN DEFAULT FALSE` |
| `data_deletion_requests.approved_by` | Erasure is admin-approved, so *who* approved and *when* is the entire audit value. The ER diagram also drew `UNIQUE (user_id, status)` that the DDL did not have | `approved_by BIGINT REFERENCES users(id)` + `UNIQUE (user_id, status)` |

The second is the more interesting one: **the ER diagram and the `CREATE TABLE`
disagreed, and both had previously been described as verified.** A diagram is prose with
boxes; the DDL is the artefact. FK count 34 → **35**.

#### 4. Gaps O–R closed, and gap P was wrong when first written

| Gap | Closed as |
|---|---|
| **O** | `package.json` (Tailwind 3.4, HTMX 1.18, Chart.js 4.4) and `tailwind.config.js` are now specified as real files in `design.md` §11.2; `npm ci && npm run build` runs in CI **and** in a throwaway Docker stage, so Node never reaches the runtime image. HTMX and Chart.js are vendored to `static/js/` because the CSP allows no third-party script host. CI asserts the built CSS against the 30 KB budget — a wrong `content` glob produces a near-empty stylesheet, which passes every other check in the job |
| **P** | **`clamav: clamav/clamav:1.4` service added to `docker-compose` and to CI**, plus `sudo apt-get install -y libmagic1` in CI. `CLAMD_HOST`/`CLAMD_PORT` wired into the Django, Celery and test environments |
| **Q** | `--extra-index-url https://download.pytorch.org/whl/cpu` and `torch>=2.3.0,<3.0.0` in `requirements.txt`; stack matrix and Dockerfile comment updated |
| **R** | `Complete Doc §C.8.1–C.8.3`: the generated-vs-hand-written rule, three non-negotiables (never edit a merged migration; **`makemigrations --check --dry-run` in CI**; no `RunPython` calling an external service), the three operations that belong in Celery instead, and the seed set (auth groups, `skills` taxonomy, score bands, reference tables) with an explicit list of what is *not* seeded |

> **Correction to gap P, kept in the record.** The gap was written as *"`libmagic` and
> `ClamAV` are OS packages not yet checked in the Dockerfile."* **That was wrong** —
> `libmagic1` and `clamav-daemon` were already in the Dockerfile. The real gap was
> narrower and worse: there was **no ClamAV daemon anywhere to connect to**, in Compose or
> CI, on a path that *rejects* uploads when ClamAV is unreachable. So every resume upload
> would have failed. Recorded because the original wording would have sent a reviewer to
> verify something that was already correct, and because "I checked and it was already
> fine" is a result worth having.

Gap **S** (`ASM-002`, double shifts) stays open **by design** — it has a test date (end of
Phase 2) and a stated fallback (re-scope, do not compress). An assumption with a test date
is not an unfinished item.

#### Standing numbers after this commit

- **🔴 24 tables, 35 FKs, 13 indexes, 52 FRs, 52 stories / 217 points** — 30 Must / 17
  Should / 5 Could. 5/5 Mermaid diagrams parse, 0 dangling `REQ-FR-` references.
- **🟠 Blockers blocking the start of development: none.** Both first-hour blockers (the
  API list, the 25 December milestone) are closed.
- **Five items still need a person, not a document:** trademark filing, the Phase 2 bias
  test set, SCCs / cross-border transfer, Figma work, and the `REQ-FR-050` keep-or-cut
  call.
- **Three assumptions are deliberately open**, each with a test date: `ASM-001` (end of
  Phase 1), `ASM-002` (end of Phase 2), `ASM-003` (end of Phase 1).

---

## 3. Gap status

| Gap | Original state | Now |
| --- | --- | --- |
| **A** — Requirement collection method | ❌ blocking | ✅ **closed** — Feasibility §1.3, `prd.md` §3.4, tagged [Done]/[Illustrative]/[Planned] (§2.20). Validation plan stays **[Planned]** until actually run |
| **B** — Real-world problem example | ❌ missing | ✅ **closed** — Amazon 2018 primary + iTutorGroup / HireVue / Mobley + 3 BD sources (§2.20). *Mobley* needs re-verification before public citation |
| **C** — Wireframes | ❌ none at all | ✅ **complete for low fidelity** — 23 wireframes, all 18 screens, all 22 core-flow pages. Figma and hi-fi still open |
| **D** — GAP-1 / GAP-2 | ⚠️ documented, no FR | ✅ **closed** — `REQ-FR-042`/`043` in the Arch Doc |
| **E** — Round-2 page gaps | *(not previously found)* | ✅ **closed** — `REQ-FR-044`–`050`, 7 stories added (§2.12, §2.13) |
| **F** — Gantt dates | 🟡 ran backwards | ✅ **re-based** to kickoff 2026-10-05 (§2.16) |
| **G** — `messages` cascade | 🟡 DDL contradicted FR-043 | ✅ **fixed** — `SET NULL` + soft delete (§2.17) |
| **H** — No team-member table | 🟡 FR-047 unimplementable | ✅ **added** `employer_team_members` (§2.17) |
| **I** — Name reveal undecided | 🟡 open | ✅ **decided: at shortlist** (§2.18) |
| **J** — 14 open §19.2 items | 🟡 open | ✅ **all resolved** (§2.19) |
| **K** — Requirements did not answer the original problem | *(not previously found)* | ✅ **closed** — G1 → `REQ-FR-051`, G2 → `REQ-FR-052`, G3 → `REQ-FR-029` amendment (§2.20) |
| **L** — FR count contradicted itself | 🟡 header 50 / note 43 / §19.2 50 | ✅ **fixed** — three dated notes, all now agree on 52 (§2.20, `prd.md` §19.2 item 15) |
| **M** — Product name contested | *(not previously found)* | ✅ **closed** — the old name was abandoned and the product renamed to **FairFold** (§2.21). **Domain owned**; residual trademark clearance on **RSK-011** at Medium/Low |
| **N** — "Bias-free" subtitle unverifiable | 🟡 claimed everywhere, measured nowhere | ✅ **closed** — subtitle is now "AI-Powered, **Explainable** Recruitment Platform" (§2.22) |
| **O** — Frontend build tooling unspecified | 🟡 stack names Tailwind/HTMX/Chart.js, no `package.json` or Tailwind config | ✅ **closed** — `package.json` + `tailwind.config.js` specified (`design.md` §11.2), Node 20 build stage in the Dockerfile, `npm ci && npm run build` + a 30 KB CSS budget in CI (§2.25) |
| **P** — No ClamAV service for a path that rejects uploads when ClamAV is unreachable | 🟡 pip clients pinned and OS libs already in the Dockerfile, but **no daemon in Compose or CI** — *the gap as first written misstated this* | ✅ **closed** — `clamav: clamav/clamav:1.4` service in Compose and CI, `libmagic1` in CI, `CLAMD_HOST`/`CLAMD_PORT` wired through (§2.25) |
| **Q** — `torch` pulls the CUDA wheel by default | 🟡 multi-gigabyte, contradicts the 2–4 vCPU assumption | ✅ **closed** — CPU extra-index and a `<3.0.0` pin in `requirements.txt` (§2.25) |
| **R** — No migration/seed strategy | 🟢 `C.8` had a plan, not a decision | ✅ **closed** — `C.8.1–C.8.3`: generated-vs-hand-written rule, `makemigrations --check` in CI, seed fixtures for groups/skills/score bands/reference (§2.25) |
| **S** — Double-shift capacity unvalidated | 🟡 new assumption `ASM-002` | ⏳ **open by design** — tested at the end of Phase 2; re-scope if it fails, do not compress (§2.6.4.1) |
| **T** — AI-assisted development degrades review | *(not previously found)* | ⚠️ **recorded, controlled** — `ASM-003` **corrected to be falsifiable** and `ASM-001` added; review obligation promoted from control to mandate; the no-AI-review-list is now eight paths with an enforced-by column (§2.25) |
| **U** — `REQ-FR-050` had no data model | 🔴 approved requirement, unimplementable | ✅ **fixed** — `announcements` table, 5 endpoints, five constraints, re-estimated 3 → 8 pts (§2.24) |
| **V** — Phase 4 milestone on Christmas Day | 🟡 25 Dec is a holiday | ✅ **fixed** — moved to Thu 2026-12-24 (§2.24) |
| **W** — API list incomplete | 🟠 blocker on the frontend build | ✅ **closed** — all five groups written (`Complete Doc §C.12`); writing them exposed two further schema holes (§2.25) |
| **X** — ER diagram and DDL disagreed on `UNIQUE (user_id, status)` | *(not previously found)* — both had been reported as verified | ✅ **fixed** — constraint added to the DDL, plus `data_deletion_requests.approved_by` and `employer_profiles.show_company_name` (§2.25) |

---

## 4. Outstanding work

**No item in this section blocks the start of development.** Both first-hour blockers —
the incomplete API list and the 25 December milestone — are closed (§2.25). What remains
needs a person rather than a document. The full picture, including the conflicts settled in
§2.23, is in `FAIRFOLD_Feasibility_and_Design.md` **§5 Pre-Development Readiness Review**.

### 4.1 🟡 Trademark clearance for FairFold — `prd.md` §4.3 · **RSK-011**

Full detail in §2.21. **The name is decided: FairFold.** The previous name was abandoned
because three unrelated commercial users already had it. FairFold had no living
commercial use in the same sweep, and `fairfold.com` / `fairfold.ai` returned no DNS record.

**✅ Domain — owned.** The team holds a domain and will run on a **temporary** one
first, moving to the primary at launch. That closes the registration half of this risk.

**What is left is legal work, not a creative decision — and none of it has been done:**

1. **Formal trademark search** in Bangladesh and every target export market. A web search,
   a DNS lookup and a domain registration are **not** a clearance — buying a domain does
   not confer the right to use a name in commerce.
2. **File the word mark** in class 42 (software/SaaS) and class 35 (recruitment services)
   in each market.

**Needs from the team:** commission items 1–2, or accept that risk knowingly. Logo work is
unblocked, but nothing should appear on public collateral until the search returns.

**Because the host will change,** keep `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, the Stripe
webhook URL and the Sentry DSN in environment variables so the switch is a config edit.
Do not build SEO or email-sender reputation against the temporary domain — verification
emails establish SPF/DKIM for *that* host.

### 4.2 🟡 Validation plan — `Feasibility §1.3.4` — **[Planned]**, not a blocker

The requirement-collection method is now honestly recorded, so §4.1 no longer blocks the
specification. What remains is **running** the validation: 8–10 candidate interviews, 5–6
recruiter interviews, a 30+ response survey, 5–8 concept tests. Sample sizes, channels and
full interview guides are already fixed in §1.3.4 so nobody has to invent them afterwards.

Until it runs, the method stays tagged **[Planned]**, and **no prevalence figure may be
stated for Bangladesh** — the local sources establish that network access and skill
mismatch are recognised problems, not how often internal lobbying decides an interview.

### 4.3 ✅ API list — closed 2026-10-03 — `Complete Doc §C.12`

**Was a 🟠 blocker on the start of development** (§5.5): the frontend cannot be built
against an incomplete API list. It sat open for roughly two hours after the requirement
was written, which is the lesson.

All five groups are now written: `REQ-FR-042` (public browse/search), `REQ-FR-040/041`
(GDPR export/delete), `REQ-FR-047` (team), `REQ-FR-049` (assessment authoring) and
`REQ-FR-050` (broadcast). **The lesson is now on the record twice** — the list is written in
the same session as the requirement, not after. Writing it found two schema holes that no
amount of re-reading §5.1 had surfaced (`employer_profiles.show_company_name`,
`data_deletion_requests.approved_by`, and a constraint the ER diagram had but the DDL did
not). Full detail in §2.25 and `Feasibility §5.7`.


### 4.4 🟡 Bias test set — Phase 2, now with required content

Deciding item 12 removed the unverifiable "100% flagged" claim rather than satisfying it.
Building a **versioned** bias test set is an explicit Phase 2 deliverable, owned by
Ishrak Hossain. Until it exists, the deterministic keyword pass has no measurable target.

**The set must include Amazon-style proxy cases** — women's-college names, "women's society
captain", gendered club roles. PII stripping removes names, emails and phone numbers and
**none** of that text, which is why stripping names alone is not sufficient. Added in §2.20
to Arch Doc §10 Phase 2 and `prd.md` §17.4.

### 4.5 ✅ Schedule — capacity solved, and the one open date is closed

**Updated 2026-10-03:** the team is working **double shifts**, so the plan is no longer
capacity-constrained (§2.6.4.1). The 212 points over 12 weeks that made this tight is
now comfortable — 217 after the `REQ-FR-050` re-estimate.

**And the 25 December problem is resolved.** Phase 4 now ends **Thu 2026-12-24**, team off
on the 25th (`Feasibility §2.7.2`, option A). One day of Phase 4 work moved into the
Phase 3 buffer. Nothing about this was a capacity problem: double shifts fixed capacity,
which is a different question from the calendar.

**What stays open is `ASM-002`, not the date.** Double shifts for twelve weeks is a
burnout and quality risk, and the failure mode is *silent* — deferred testing (which
threatens `REQ-NFR-019`'s 80% coverage gate) and undocumented scope cuts that leave the
spec describing something nobody built. Tested at the end of Phase 2; if it fails, re-scope
rather than compress. Tracked as **gap S**.

### 4.6 🟡 Design tooling — `design.md` §12

Content decisions are recorded as text, which briefs a build. Not started: the Figma file
and components (items 1–2), high-fidelity mockups (4), the interactive Journey Map
prototype (5), logo and icon sets (7–8), notification copy (9), usability test plan (10),
and screens for the two new screening-integrity components (11).

26 pages have a spec but no wireframe (`design.md` §10.6) — including **#31 and #48, the
two messaging pages**, so `REQ-FR-043` has no drawing even though the requirement exists.

### 4.7 🟢 Remaining design decisions — `design.md` §12

1. Score-band thresholds, once the scoring model is calibrated
2. ~~Name reveal~~ — **decided at shortlist** (§2.18)
3. Whether dark mode ships in the MVP
4. Whether Bengali ships at launch (the PRD defers it to Phase 5)
5. ~~Final brand name styling~~ — **unblocked 2026-10-03** — the name is FairFold (§2.21). Logo and accent-colour work can start; do not print on public collateral until **RSK-011** returns (§4.1)

### 4.8 🟢 Open questions the docs still record

- **No dedicated DevOps role.** Absorbed by Ishrak Hossain; recorded as the largest
  operational risk (R3 / RSK-009).
- **OpenRouter free-tier limits** are quoted from September 2026 and must be re-verified at
  implementation. They are configuration, not a design assumption, so this cannot break the
  $0-cost claim — the offline fallback covers it.
- **Pricing** is canonical in the Complete Doc; `prd.md` §15 and Complete Doc §C.14 should
  be checked against each other before any billing work.

### 4.9 Push state

The user pushes manually; `git fetch` / `ls-remote` cannot be verified from this
environment (no GitHub credentials). Confirm on GitHub before assuming anything is synced.

---

## 5. Conventions worth remembering

- **Never fabricate** research, statistics, interview counts, or credentials. An honest
  "not done" beats an invented study.
- **Never push without explicit go-ahead**, and never push directly to `main`.
- Per-developer secrets: keys from `scripts/generate_secret_key.py` are machine-specific and
  must not be committed or shared.
- Reference convention: `Arch Doc §N.M` / `Complete Doc §N.M` / bare `§N.M` = feasibility
  and design doc. Cite canonical specs; do not duplicate their content.
- **Functional requirements live in the Arch Doc §4.1, not the PRD.** The PRD proposes them.
- Mermaid diagrams must be validated before commit. Harness at `/tmp/mmv2/check.mjs`
  (`node check.mjs`) — **`/tmp` is wiped between sessions, so reinstall with
  `npm i mermaid@11 jsdom` if missing.** All 5 diagrams currently parse.
- When a spec count changes (FRs, stories, pages, wireframes), **grep the whole repo** for the
  old number and for stale phrases like *"not yet delivered"*. It propagates into tables,
  checklists and cross-references in every file.

---

## 6. Commit history

```
4b4ea7e  docs: move the Phase 4 milestone, record AI-assisted development, and build the broadcast feature
ca4061f  docs: readiness review before development — nine conflicts settled, five gaps opened
1079588  docs: rename to FairFold, and withdraw the bias-free claim the product cannot support
2f7f01f  docs: trace requirements back to the problem, and flag a contested product name
f342dd0  docs: re-base the Gantt, close two schema holes, and decide the open questions
34fbe78  Create design.md
6a50343  Create prd.md
96993d4  docs: promote REQ-FR-042/043 to the Arch Doc and reconcile spec drift
c7d8c00  docs: add HISTORY.md recording completed work and outstanding items
b16b7a6  docs: correct wireframe row 4 to reference GAP-1, not FR-022
0486ee1  docs: rename submission doc and link all three specs from README
a9f3817  Merge pull request #5
c9d335d  Merge pull request #4
ba51af9  Merge pull request #3
17f872c  Merge pull request #2
29eae4e  Merge branch 'docs/fill-academic-gaps' into ishrakhossain53-patch-1
5e74189  docs: add academic submission document covering rubric gaps
ea0e688  Merge pull request #1
070d520  Update license section in README
67bd089  Initial Documentations
6c2632e  Initial commit
```

Upstream `main` also contains merge commits `18d5713` (PR #6), `bc47ae0` (PR #7) and
`ed05fef` (PR #8), which fold the earlier branch work into `main`.
