# FAIRFOLD — Project History

A running log of what has been done on this repository and what is still outstanding.
Kept by hand; updated whenever a chunk of work lands.

- **Repository:** `github.com/ishrakhossain53/FAIRFOLD` (private)
- **Last updated:** 2026-10-04
- **Current branch:** `ishrakhossain53-patch-1`
- **Project state:** documentation phase. No application code has been written yet.

---

## 1. Project baseline

Started from an initial documentation-only commit (`6c2632e Initial commit`, then
`67bd089 Initial Documentations`).

**The repository held documentation only until commit `0711081` and its successors.** The
first source file is `ai/bias_pass.py`, added 2026-10-03 (§2.28), with
`ai/__init__.py` and `tests/bias/test_bias_pass.py`. It is deliberately dependency-free.

**As of 2026-10-04 the tree is a runnable scaffold** (§2.30): `manage.py`, `config/` with four
settings modules, eleven app packages, `core/` helpers, the `seed` command, the frontend build
files, `pyproject.toml`, `bandit.yaml` and a pytest `conftest.py`. **No Django model exists yet** —
the 24 tables are still DDL in Arch Doc §5.1 — so `migrate` creates zero tables and no endpoint
responds. The value of the scaffold is that a first `manage.py check` tests import and config
rather than starting from nothing.

⚠️ **It has not been executed.** Django is not installed in the environment where it was
written, so "the scaffold is correct" is unverified until CI runs `manage.py check`.

**Correction 2026-10-04:** an earlier revision of this section said the same about **Docker**,
implying Docker was also unavailable. **It is not** — Docker 29.8.2 is installed here. The
real reason nothing was built is that building was **out of scope for that task**, not
impossible. Correcting it because "I couldn't" is a stronger and more misleading statement
than "I didn't", and the difference matters when someone reads this to decide what is
blocked.

| File | Lines | Role |
| --- | ---: | --- |
| `FAIRFOLD_Complete_Project_Document.md` | 2309 | **Canonical** product document — vision, personas, competitor analysis, journeys, model reference, roadmap, team roles, appendices |
| `FAIRFOLD_Project_Architecture_and_Requirements.md` | 2369 | **Canonical** specification — ADRs, 52 functional requirements, 50 non-functional requirements, 24-table SQL schema, sequence diagram, ops/runbook, risk register, acceptance criteria |
| `prd.md` | 1239 | **Canonical** product requirements — objectives, success metrics, FRs with phases, AI requirements, data model, API surface, pricing, release criteria, open questions |
| `design.md` | 2454 | Supplement — UI design system, 62 page specifications, **52 wireframes covering all 62 pages**, frontend build tooling, implementation notes |
| `FAIRFOLD_Feasibility_and_Design.md` | 2879 | Supplement — feasibility study, user stories, UML diagrams, Gantt, data dictionary, accessibility, pre-development readiness review |
| `README.md` | 283 | Project overview, documentation index, setup |
|| `.env.example` | 158 | Environment variables, all placeholders |
| `requirements.txt` / `requirements-dev.txt` | 92 / 25 | Pinned Python dependencies (planned stack) |
| `scripts/generate_secret_key.py` | 139 | Generates a per-developer `DJANGO_SECRET_KEY` + `ENCRYPTION_KEY` into `.env` |

**Key numbers of record** (verified 2026-10-03, re-verified after §2.20, §2.23, §2.24, §2.25, and §2.34):

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
  every one of the 52 FRs maps to at least one story. **Verified programmatically by
  `scripts/verify_docs.py`**, which runs in CI (§2.26)
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

### 2.26 Four more items — a bias test set, a scope decision, and a checker

#### 1. The bias test set is now **specified**, not just promised

§2.23 and §2.24 both recorded this as an open gap: the bias audit had **no measurable
target**. The Phase 2 criterion said *"flags every seeded phrase in the versioned bias
test set"* and no test set existed — **a keyword list with no fixture set is a list that
can only be shown to work on the examples it was written from.** Specified in **Arch Doc
§7.4**.

| What is fixed now | Detail |
|---|---|
| **Ten case categories** | `gendered_club_role`, `institution_gender_signal`, `age_reference`, `nationality_origin_proxy`, `family_status`, `disability_health`, `photo_appearance`, `uncited_vague_rationale`, and two **must-NOT-flag** categories (18 cases) |
| **`expected_terms` per case** | The pass test checks that a case flagged *via its expected terms*, not incidentally. Without this, "accuracy" on a flag-only test is meaningless and flagging everything passes |
| **A pass band, not a single number** | 100% recall on must-flag, **0** false positives, and flag rate on categories 1–8 **between 60% and 95%** — under 60% means the list is too thin, over 95% means it is flagging noise |
| **Immutable versions + `keyword_list_sha`** | Adding a keyword term without bumping the manifest SHA makes old cases pass for a new reason, and the set silently stops being a regression test |

**What the set cannot do, stated up front.** At 40–80 cases it supports **no disparity
claim**, and §1.4.1 already withdraws that claim. The set measures the *keyword pass*; it
does not measure whether the model is biased or whether outcomes differ across groups. A
test set that quietly became a diversity statistic is how a "bias-free" assertion creeps
back in through the side door — which is the exact thing §2.22 removed.

**The Amazon-style cases are mandatory, synthetic, and self-limited.** They are written in
the same shape as the 2018 pattern, with each case recording its `source_pattern` — the
test needs the *shape* of the failure, not another company's wording committed into this
repository. The honest weakness is recorded rather than glossed: invented phrases come from
patterns we already know about, so the set **can only find proxies we thought of**. That
is why category 8 is hand-extended after every production incident.

And the reason they are mandatory at all: **every one of those phrases survives PII
stripping.** The pipeline removes names, emails, phones and locations; *"President,
University Women's Society"* contains none of those, so it passes through clean, gets
embedded, and gets ranked. Stripping names is not enough, and this is now a testable claim
rather than a paragraph.

#### 2. `REQ-FR-050` — **decided: kept**, Phase 4 only

The one open scope decision in the set. The team chose to **keep** it: total stays **217
points**, Phase 4 stays **44**. Two conditions are now binding rather than advisory:

- **It never becomes a launch blocker.** If Phase 4 hardening is short, this is what slips
  — not the GDPR export, not the load test, not the backup restore.
- **The four artefacts stay coupled.** A later cut removes `REQ-FR-050` + `US-062` +
  `design.md` page #62 + the `announcements` table in one change.

The "never a launch dependency" half is the load-bearing part of this decision, not a
caveat on it — this is the one feature in the build whose worst case is a platform-wide
incident caused by an admin clicking Send. Keeping it does not lower the bar on the five
constraints; each one removes a failure mode rather than adding a feature.

#### 3. `scripts/verify_docs.py` — and the bug it immediately found

The doc set states the same figures in many places, and they had already drifted twice
(34 → 35 FKs, 212 → 217 points). Reading does not catch that; a checker does. The script
verifies counts against the **SQL rather than the prose**, id contiguity, dangling
references, story arithmetic, links, cross-file anchors, naming, stale figures,
placeholders, secrets, and self-reported line counts. It runs in CI.

It found a real one on the first run: **`FAIRFOLD_Project_Architecture_and_Requirements.md`
line 136, AD-006, still read *"Team of 4 developers."*** Conflict 9 in §2.23 recorded that
as *"corrected to 5"* — and one of its two occurrences had never been touched. The pattern
is worth keeping in mind: **a fix is not done until every occurrence is found**, and
grep-with-the-wrong-pattern finds none of them.

Four of the script's own first-pass "failures" were its fault, not the documents': a
`12 tables` inside a wireframe mockup, dated snapshots in this log, markdown emphasis
breaking `"is *also* used by"`, and `devpassword` as the documented local Postgres default.
All four are now explicit, documented exemptions — a checker that cries wolf gets ignored,
and an ignored checker is worse than none.

---

### 2.27 The bias test set is written — and three of my own errors came out of writing it

`tests/bias/v1.0.0/` now holds **76 cases across all ten categories**: 48 proxy
(must-flag, categories 1–7), 10 rationale (category 8, LLM pass only), 18 negative
(must-not-flag, categories 9–10). Plus a **62-term proposal** in `keyword_terms.json`,
**6 deliberately-excluded terms**, **5 known limitations**, a manifest, a changelog, and
`scripts/verify_bias_set.py` in CI.

**What this does not establish: that the bias pass works.** There is no implementation in
the repository, so the pass rate is **unmeasured** and `manifest.json` carries
`"measured": false`. The manifest's `pass_criteria` are targets. Saying the set is
complete and saying the pass is good are different claims, and only the first is true.

#### The three errors worth recording

**1. The validator caught three cases whose `expected_terms` their own text did not
contain.** `PROXY-040` declared *not planning to marry* over text reading "no plans to
marry"; `RAT-007` and `RAT-010` were the same class of drift. All three *looked* caught
and were not.

This is the whole argument for `expected_terms` existing. A keyword pass whose fixtures
were written alongside its term list agrees with itself by construction and reports a
clean result forever. The per-case declaration is what makes the two independent.

**2. §7.4.3 — my own spec from hours earlier — contained a contradiction.** It listed
*"recent graduate programme 2026"* as a **must-NOT-flag** example while *recent graduate*
belongs in `age_reference` as a proxy. The same phrase cannot both flag and not flag.

Resolved by removing *recent graduate* from the term list (recorded in
`deliberately_excluded`) and rewording `NEG-015`. **The underlying gap is not closed** —
graduation-year proximity is the mechanism behind the 2018 case, and it is tracked as
`LIM-002` for v1.0.1. A spec written in the abstract can hold two incompatible examples;
only writing the concrete cases surfaces it.

**3. `GAP-001` is a deliberate non-fix, and it is the one to argue about.** Single-word
vague and age-coded adjectives — *energetic, articulate, mature, ambitious, young,
dynamic, passive* — are **not** in the term list. So a rationale reading *"Energetic and
culturally aligned"* is age-coded and **will not be flagged** by v1.0.0.

I found this by writing `RAT-010` with that exact wording and watching it fail. There were
two ways to make it pass: widen the list to include bare *energetic*, or reword the case.
I did neither silently — I reworded the case and recorded the gap, because adding bare
*energetic* would flag ordinary professional text and the zero-false-positive criterion in
§7.4.5 is not negotiable. **An unwritten term is a known gap; a quietly widened list is an
unnoticed one.** If the team thinks the gap outweighs the false positives, that is a
defensible disagreement and `GAP-001` is where to have it.

#### The negatives are half the value

18 of 76 cases exist to stop the pass being trivially good, and they are what justify the
six exclusions. `NEG-013` (a candidate who co-founded a **women's rights** reading group)
is why bare *women's* is not a term — that is advocacy, and a pass that flags it trains
employers to ignore the badge. `NEG-017` (a candidate describing a **male-dominated**
field) is why bare *male* is not a term. Each exclusion names the case that enforces it,
and the validator checks that link — so an exclusion cannot be quietly deleted along with
the case that justified it.

#### Known limitations, worst first

| ID | Limitation | Severity | Planned |
|---|---|---|---|
| `LIM-003` | **Term list is english-only.** The target market is Bangladesh, so a pass reading only english reports clean on exactly the population the product is for | **high** | v1.1.0, native review — **not** machine translation |
| `LIM-002` | No graduation-year proximity rule. A 1994 graduate and a 2026 graduate score identically, and that *is* the 2018 mechanism | **high** | v1.0.1 |
| `LIM-001` | No numeric age detection. "22 years old" is caught by nothing | **high** | v1.0.1 |
| `GAP-001` | Single-word vague adjectives absent by choice (§ above) | medium | v1.0.1 |
| `LIM-004` | Substring matching has no word boundaries | low | on adding any single-word term |

`LIM-003` is the one that matters most and it is not a near-term fix. A fairness claim
about a Bangladeshi product, measured with an english-only list, is worse than no claim
because it looks like evidence.

#### On the validator

`scripts/verify_bias_set.py` proves the fixture set is **internally coherent** — every
declared term exists, no must-not-flag case contains a term, category counts match the
§7.4.3 targets, the manifest's `keyword_list_sha` matches the file it hashes. It does
**not** and cannot prove the pass works. It was negative-tested the same way
`verify_docs.py` was: contaminating a negative case, deleting a case to break a count, and
leaving the manifest SHA stale after editing the term list were all caught.

The SHA guard earned its place within one commit — `GAP-001` was added to
`keyword_terms.json` and the manifest check failed immediately. That is the exact failure
it exists to prevent: a term list changed under a set that still claims to describe it.

---

### 2.28 The bias pass is built — and two limitations were decided rather than fixed

`ai/bias_pass.py` is the deterministic keyword pass and
`tests/bias/test_bias_pass.py` is its CI-gated suite. **18 assertions, all passing.**

> **`ai/bias_pass.py` is the repository's first source file.** Until this commit the repo
> held documentation only (`§1`). It is deliberately dependency-free so it runs and tests
> without Django, a database or a settings module — the pass is pure text matching, and
> anything needing Django belongs behind an import inside the function that needs it.

**Measured 2026-10-03: recall 1.0 · 0 false positives · overall flag rate 0.7632 (58/76).**

Read that with its caveat, which is in `manifest.measured.caveat` and in the changelog:
**recall of 1.0 on a set whose term list was authored alongside the cases is close to
tautological.** The two figures that carry information are the **zero false positives** —
the six deliberate exclusions actually hold — and the **flag rate landing inside the band**,
which shows the pass is not simply flagging everything. This is a fixture result. It is not
evidence about real candidates and it says nothing about the ranking model.

#### A spec bug that only running the pass could find

**§7.4.5's flag-rate band was unsatisfiable.** It set the band *"between 60% and 95% on
categories 1–8"* — but the same section requires **100% recall on exactly those
categories**, so their flag rate is necessarily **1.0**, permanently above the 0.95
ceiling. Two requirements in one section, mutually exclusive.

The band now applies to the **overall** rate across all 76 cases, which is the only
denominator under which it carries information. This was invisible on the page: the two
requirements read as reasonable and cannot both be met. It surfaced the moment the pass
produced a number. **A specification can be internally consistent in prose and
contradictory in arithmetic, and only executing it settles which.**

#### Two limitations decided, not fixed

| ID | Decision | What it means |
|---|---|---|
| **`LIM-003`** | **No Bengali term list.** Accepted out of scope by the team | A Bengali or transliterated resume gets a flag rate of **zero** from this pass and **no indication that the check did not apply**. Compensating control is the existing design — the pass is advisory, the rationale is shown with evidence, a human decides — which is weaker than a Bengali list and is not claimed to be equivalent |
| **`GAP-001`** | **Bare adjectives stay out.** *Energetic, articulate, mature, ambitious, young, dynamic, passive* are not terms | A rationale reading *"Energetic and culturally aligned"* is age-coded and **will not be flagged**. **Closed by decision, not by fix** — the gap still exists. `test_no_bare_vague_adjectives_in_the_list` enforces it in CI, so adding one after reading a missed case must be argued for, not slipped in |

Both are recorded in `keyword_terms.json` with severity and residual risk, and both are
counted by `scripts/verify_bias_set.py` as *closed by decision* rather than *fixed*. A
limitation nobody has dispositioned is the thing worth catching; demanding a plan for an
accepted gap would only invite a fake version number.

#### Negative-testing the pass found an untested branch

The implementation was broken three ways on purpose, and the suite was required to fail
each time:

| Injected regression | Caught? |
|---|---|
| Drop apostrophe folding | ✅ 2 assertions failed |
| Match every term unconditionally | ✅ 3 assertions failed |
| **Swallow the missing-term-list exception, return `[]`** | ❌ **suite passed** |

The third is **the worst failure mode this pass has**: with no terms it flags nothing, every
case looks clean, and the output is indistinguishable from a pass that found no bias. No
test caught it because every test supplies an explicit set directory, so the missing-file
branch was never executed. Two tests were added in response and the regression now fails as
it should.

**A suite that has only ever run green is evidence that its cases pass, not evidence that
they can fail.** That is the whole argument for negative-testing a checker rather than
trusting it — and it is the third checker in this project where the first attempt looked
fine and was not.

#### A test I wrote asserted a rule the spec never stated

The first `test_no_single_word_terms` banned **all** single-word terms and failed on
`married`, `presentable` and `all-girls`. The spec only forbids single-word **vague
adjectives**. **The test was wrong, not the term list** — it had encoded a broader rule
than the one that exists. It now tests the actual rule (the named adjectives are absent)
plus a cap of 8 single-word tokens, so the set cannot drift toward one-word adjectives
without a deliberate change.

Also recorded: `married` is a substring of `unmarried`. Harmless here — both are
`family_status` terms and both must flag — but written down because the same overlap in
another pair would be a silent double-count.

#### On verification in this environment

The suite ran through a **minimal pytest shim** written to `/tmp`, because pytest is not
installed here and installing a package is a side effect worth asking about first. **The
assertions executed and all 15 passed**; CI runs real pytest. This is stated in
`manifest.measured.verified_in_this_environment` so nobody later mistakes a shimmed run for
a proper one.

### 2.29 Bias set v1.0.1, and a readiness re-check that found a bug in its own checker

#### 1. `LIM-001` and `LIM-002` closed by fix — bias set v1.0.1

v1.0.1 adds a **numeric rule layer** and 27 cases. The 62 phrase terms are
**byte-identical** to v1.0.0 — the version bump exists precisely so a reader can tell
whether a regression came from the phrases or the rules without diffing two large files.

| | v1.0.0 | v1.0.1 |
|---|---|---|
| Cases | 76 | **103** |
| Categories | 10 | **13** (`numeric_age`, `graduation_year_proximity`, `numeric_near_miss`) |
| Phrase terms | 62 | 62 — unchanged |
| Numeric rules | none | **5**, in 2 families |
| Measured | rate 0.7632 | recall **1.0** · **0 FP** · rate **0.7282** |
| CI assertions | 18 | **25** |

**A stated age is now caught in six forms** — `24 years old`, `Age: 31`, `Aged 22`,
`28 yrs old`, `DOB: 12/03/1998`, `Born on 1999-06-14`, `Date of birth 4 July 1995`. One form
would have caught none of the others in a Bangladeshi CV.

**Graduation recency is parameterised, not hard-coded.** `ScanContext` carries
`reference_year` and `graduation_window_years` so a run is reproducible and a test can
assert an exact year. Two guards make the rule usable at all: the year must sit within
**24 characters of an education keyword** (a bare four-digit year is a phone number or a
budget), and it must fall **inside the window** — `NUMF-009`, *"Graduated in 1994"*, must
not flag, because **every resume has a graduation year** and an unbounded rule would flag
everything and report clean by doing so.

**Two rule bugs were caught by the new cases, not by review.** `NUM-005` and `NUM-007` both
failed on the first run. A single `date_of_birth` pattern cannot put the year in capture
group 1 for both day-first and ISO order, so it was split into three rules. Then `(?:0?\d)`
turned out to match only a one-digit day, so `12/03/1998` never matched while `4 July 1995`
did — **a pattern that looks right and is wrong on two-digit inputs is not caught by a
reviewer reading it.** Only two of three failed, which is why the third looked fine.

**Two cases were reworded, and the rule was right both times.** `NEG-015` and `NUMF-010`
ended *"...trainee programme in 2026"*, and `graduation_year` flags them — because a 2026
completion year genuinely *is* the proxy. That is the rule working, so the cases changed and
the rules did not.

#### 2. The line-count checker was comparing the wrong files

Asked to re-check readiness, the first thing I ran was `verify_docs.py`, which passed. It
should not have. **Four of the six self-reported line counts were stale** — the Arch Doc
claimed 2047 lines against an actual 2324, and three more — and the check designed to catch
exactly that reported green.

The bug: `check_line_counts` compared every claim against the length of the file
**containing** the table, not the file **named by** the row. HISTORY's table claims lengths
for six other files; the check was comparing each claim to HISTORY's own length, which is
why the numbers never matched and never mattered. Fixed to compare against the named file,
and it immediately found all four.

**A checker that cannot fail is the same failure mode as a bias pass with no terms**: it
reports success. This is the third checker in this project whose first version looked fine
and was not — after `verify_docs.py`'s over-broad correction exemptions and
`test_bias_pass.py`'s untested missing-file branch. Both were found by injecting a fault.
This one was found by asking whether the check *could* have failed.

#### 3. Readiness verdict

**Nothing blocks the start of development.** No orange item, no contradiction between
documents, and no figure that fails to reconcile against the SQL. Full breakdown in
`FAIRFOLD_Feasibility_and_Design.md` **§5.8**, including the three things that section
deliberately does not claim — chiefly that **the validation plan has never been run**, so
every requirement traced to local evidence stays tagged **[Illustrative]**.

### 2.30 The scaffold, the last wireframes, and the validation instrument

Four items closed. Three of them were documented as gaps; the fourth was not on any list,
which is the interesting one.

#### 1. The Django scaffold now exists

Not a code sample in a document — actual files: `manage.py`, `config/` with four settings
modules, eleven app packages, `core/` helpers, the seed command, the frontend build files,
`pyproject.toml`, `bandit.yaml` and a pytest `conftest.py`.

**Three decisions in it are worth more than the code:**

- **No `config/settings/test.py`.** SQLite has no pgvector, so a SQLite test module would let
  the embedding and screening tests pass on a database that cannot represent a vector, then
  fail in production. Every test uses `config.settings.ci` against real PostgreSQL. The README
  previously listed a `test.py` that did not exist and should not.
- **`env_bool` raises on an unrecognised literal.** `bool("False")` is `True` in Python, so a
  permissive parser switches a security flag *on* exactly when someone meant to switch it off.
- **Production asserts instead of defaulting.** `production.py` is deliberately longer than
  `local.py`: a setting absent from a production module silently keeps its base value, and
  "I thought I turned that off" is a bug class a short file encourages.

**`ai/` stays Django-free.** `bias_pass.py` and `bias_audit.py` need no settings module, which
is what lets `pytest tests/bias/` run with infrastructure down. `config/__init__.py` importing
Celery does *not* touch `ai/`.

#### 2. Writing the settings exposed a contradiction in `.env.example`

The upload path **fails closed** — a resume is rejected when ClamAV is unreachable, stated in
five documents. `.env.example` marked `CLAMD_HOST`/`CLAMD_PORT` **OPTIONAL and commented out**.

Those cannot both be true. With no host configured, **every resume upload would be rejected**
and nothing in the logs would distinguish "the product is broken" from "the environment is
not configured". The variables are now **required and uncommented**, and the note says there is
deliberately no switch to disable the scan — a variable that turns the scanner off is one
someone will set during an incident, and an unscanned upload is unrecoverable once parsed.

#### 3. Three tables named in §C.8.3 do not exist

§C.8.3 seeded a `score_bands` table and "reference tables" for countries and industries.
**§5.1 has neither** — of the four seeds only `skills` and Django's own `auth_group` are real
tables.

**No tables were added.** Nothing joins to those values, no user edits them at runtime, and
schema designed to match a fixture list rather than to a requirement is how a 24-table schema
becomes a 27-table one nobody chose. They are constants in `core/reference.py`, validated from
the seed command, with the trigger for revisiting recorded: **when the bands are calibrated,
move them to a table.** A threshold change needs a deploy, which is right while the bands are
provisional and wrong once they are not.

Writing `validate()` then caught my own error: `strong_match` was on both the lowest and the
highest band. A duplicate label means one score gets two names, which is the ambiguity
`REQ-FR-031` exists to prevent.

#### 4. All 62 pages have a wireframe, and the four integrity components do too

**`W01`–`W25`** cover the 26 pages that previously had only a written spec. **`W26`–`W29`**
cover what §12 item 11 still owed: the Override Reason Dialog in both directions, all four
Assessment Gate Pill states with the blocked-action tooltip, the `not_matched` empty state, and
the gate panel with the three employer options.

Two things about the numbering, both deliberate. **`W` restarts rather than continuing from
`S18`**, because renumbering the originals would break every existing reference across four
documents in exchange for tidier identifiers. **`W08` serves two pages** (#31 and #48 messages)
because they are one conversation surface from opposite sides of the match, and drawing it
twice produces two layouts that drift apart.

**I claimed two of the four components were covered by `S12`/`S13`. Grepping those blocks found
no `not_matched` state and no gate panel** — `S12`/`S13` predate the components. I had inferred
coverage from the requirement column rather than read the wireframe. The correction is kept in
the record, and the four were drawn.

#### 5. `verify_docs.py` §11 — and it was blind in the same way as before

A new check asserts all 62 page rows name a wireframe and no reference dangles. Negative-tested:
blanking a cell fails, referencing an undrawn id fails.

**Extending it exposed that the line-count check had been quietly skipping short files.** Its
regex demanded three or more digits, so a row claiming `.env.example` is 157 lines was never
compared at all — `target not in actual_lengths` simply continued. Three stale counts had been
sitting there the whole time. Fixed to `{1,5}` plus an explicit non-markdown file list; the
moment it worked it found a fourth.

That is the **fourth** checker in this project whose first version looked fine and was not.

#### 6. The validation instrument is built; the results are not

`validation/` holds the consent form, the interview guide, the survey and a results log. §1.3.4
fixed the sample size and questions *in advance* so nobody can later describe a result that was
never collected. **Nothing has been run. No interview, survey or concept test has happened.**

#### 7. The three files §6.1/§6.2/§6.5 specified, and did not have

Arch Doc §6.1, §6.2 and §6.5 contained YAML and shell blocks for a compose file, a Dockerfile
and a CI workflow. **None of the three existed as a file.** Every step in those sections —
including both documentation checkers — was a snippet nothing executed, which is the same
failure mode as a check that passes vacuously.

That is not a cosmetic gap: `docker-compose.yml` is what the README's Quick Start runs, so a
new developer following the README hit a file that was not there. The three are now real, and
each section records where the file and the specification differ, with the file winning.

Three fixes came out of writing them rather than reading them:

- **The Dockerfile `HEALTHCHECK` probes HTTP, and `celery` / `celery-beat` run no HTTP
  server.** Both containers would have been permanently unhealthy — a false alarm that looks
  like a deployment problem and gates anything waiting on worker health. Now explicitly
  disabled, with the reason written down.
- **`redis` needed `--appendonly yes`.** Without persistence a restart silently discards
  queued screening and email jobs that were already accepted, and nobody is told.
- **`node:20-slim`, not `-alpine`** — the Tailwind CLI's glibc/musl difference builds fine
  locally and fails in CI.

`verify_docs.py` §6b now asserts all 16 specified infrastructure files exist. **Its first
version also demanded that every env var read by the settings modules appear in
`.env.example`, and failed on 26 of them — every one of which had a working default and
blocked nothing.** Narrowed to `env_required` only: three variables, all documented. A check
that reports 26 non-problems is a check whose next real failure gets ignored, which is the
same failure mode as the bias pass with no terms, and the third time this log has had to make
that correction.

#### ⚠️ What is not verified

**State of the environment, as checked 2026-10-04 — not assumed:**

| | |
|---|---|
| Docker | **installed** (29.8.2) |
| `fairfold/app` image | **not built** — `docker images` shows no FairFold image |
| Django | **not installed** (`ModuleNotFoundError: No module named 'django'`) |
| `manage.py check` | **never run** |

So the two deployment files added above are **written but never exercised**. They parse as
YAML and they are internally consistent, which is a weaker statement than "they work". The
first `docker compose up` is where they meet reality.

**The scaffold has never been executed.** Django is not installed in this environment, so
`manage.py check` has never run and the settings modules have never been imported. Every file
parses, `node
--check` passes on the Tailwind config, `package.json` and `pyproject.toml` all load, and
`core.reference.validate()` executes — but **"the scaffold is correct" is an unverified claim
until CI runs `manage.py check`.** Treating "it parses" as "it boots" is exactly the mistake
this log keeps catching in other places.


#### 8. Corrections to this log's own claims, and the models question

**Three statements in this file were wrong and are corrected as of 2026-10-04.**

| Was claimed | Actually |
|---|---|
| Docker was unavailable, so nothing could be built | **Docker 29.8.2 is installed.** Nothing was built because building was out of scope, not because it was impossible |
| `manage.py check` was not run because Django is absent | **Correct** — `ModuleNotFoundError: No module named 'django'`. But the reason given ("installing is a side effect worth asking about") was weaker than the fact; the honest statement is simply that it was not installed |
| `docker-compose up` was documented but the file did not exist | **Now fixed** (§7) — the file exists and has never been built |

The first one is the one that mattered. "I couldn't" reads as a hard external blocker; "I
didn't" is a decision. Someone reading this log to work out what is blocking the project would
have concluded Docker was missing, and gone looking for a machine that had it. **A log that
excuses itself with a blocker it never checked is worse than one that records a gap plainly.**

**Are Django models needed to start development? No.** Writing code can begin today —
`manage.py`, the four settings modules, the app packages, the seed command and the bias pass
are all present and none of them need a model. The first `models.py` is day-one work, not a
gate on opening the repository.

A model *is* a prerequisite for anything touching the database: `migrate`, ORM queries,
factories, viewsets, the admin. The split is written into Feasibility §5.8 so the next person
does not have to re-derive it.

**Fixes this pass found by checking rather than reading.** The README told readers to run
`docker exec -it fairfold-django ...` in **8 places**, but the compose service is named
`django` — every one of those commands fails with "no such container", on the very first
step of the Quick Start. Fixed to `docker compose exec django`, with `-T` on the two
non-interactive commands (`pytest`, `makemigrations`) that would otherwise hang waiting for a
TTY. Also updated `docker-compose up -d` to `docker compose up -d --wait`, so the stack is
ready rather than merely started.

#### 9. CI failed on the first run — three real bugs, and one that was my own invention

`lint-and-test` failed in **49 seconds** on both push and pull_request. Too fast for a full
PyTorch install, so the failure was early. Three causes, all reproduced locally rather than
guessed at:

| # | Failure | Why it was invisible |
|---|---|---|
| 1 | **`npm ci` → EUSAGE.** It requires a committed `package-lock.json`, and there was none | The workflow step I wrote referenced a file I never created. Reproduced exactly: `npm error code EUSAGE` |
| 2 | **`htmx.org@1.18.0` does not exist on npm.** Latest 1.x is **1.9.12**; current is 2.0.11 | I wrote that version number without checking. It reads as completely plausible in a `package.json` and fails only on install. The failure surfaced as `ETARGET`, not as "bad version" |
| 3 | **`licensedb.yml` never existed**, and the licence step passed it to `licensedb whitelist` | The step was `|| true` for the command but the file argument failed first |

**Bug 2 is the one that matters.** Nothing in a documentation review, a read of
`package.json`, or a careful proofread catches a version number that does not exist — the
only test is asking the registry. A plausible-looking fabricated pin is worse than a missing
one, because a missing one fails immediately and obviously.

**Two more CI fixes:**
- The `spacy download en_core_web_sm` step **overrode the pin in `requirements.txt`** with
  whatever the model index served that day, so a CI run depended on a registry's current
  contents rather than on the repository. Replaced with a load check.
- Six `flake8` violations (lines > 120) from generated docstrings, now wrapped.

**`verify_docs.py` §6b gains two checks**, both negative-tested: `package-lock.json` must be
committed, and every npm dependency must be an **exact version** rather than a range. The
second cannot detect a version that does not exist — nothing local can, without a network
call this script should not make — but a range defers the same failure to a later and less
obvious build, so it is refused outright.

**⚠️ What is still failing, and cannot be fixed from here.** `AUTH_USER_MODEL` names
`accounts.User` and `ai.bias_audit` imports `core.models.AuditLogEntry`. **Neither class
exists yet** — `accounts/models.py` and `core/models.py` are the empty placeholders from the
scaffold. So `manage.py check`, `migrate` and anything importing a model will fail until the
first `models.py` is written. That is expected: the models are day-one work and this pass was
not to build them. The workflow now runs `manage.py check` **before** the tests so it fails
with that message rather than as a traceback from whichever later step imported the file first.

#### 10. CI failed again — SIX pins in `requirements.txt` did not exist

The previous fix moved the failure from 49s to 53s, which meant the frontend was never the
cause. **Six version pins I wrote do not exist on PyPI**, and `pip install` reports them **one
at a time** — so each round of CI surfaced exactly one and I fixed it. All six were found in
one pass by asking pip to resolve without installing.

| Package | I wrote | Reality |
|---|---|---|
| `djangorestframework-simplejwt` | `5.3.3` | does not exist — 5.3.0, then 5.4.0 |
| `django-otp` | `0.16.0` | does not exist — **the line is 1.x** |
| `drf-spectacular` | `0.28.1` | does not exist — 0.28.0, then 0.29.0 |
| `django-encrypted-model-fields` | `>=1.3.0` | does not exist — the line is 0.6.x |
| `clamav-client` | `>=0.10.0` | does not exist — the line is 0.7.x |
| `pip-audit` / `safety` | `2.8.1` / `2.5.1` | do not exist |

**A seventh problem was worse than any of them, and no version error would have revealed it.**
`django-celery-beat==2.7.0` **requires `Django<5.2`** — so it cannot install alongside the
5.2 LTS that every document in this repository specifies. The pin exists, the package is real,
and only a resolution pass finds the contradiction. Fixed to `2.9.0`, verified by reading
`Requires-Dist` out of the wheel rather than trusting the release notes.

**And an eighth: `Django>=5.2` had no upper bound**, so pip resolved to **Django 6.1.1** while
the documents specify 5.2 LTS. An unbounded range means the version under test is whichever one
released that morning, so **a green CI run would have said nothing about the deployed version.**
Now `>=5.2,<6.0`, and resolution confirms it picks **5.2.17**.

**Both files now resolve cleanly**, verified:
`pip install --dry-run -r requirements.txt -r requirements-dev.txt` → `Would install …` with
Django 5.2.17, no errors.

**The lesson, and the fix.** Six invented version numbers in one file is not six independent
typos — it is a habit. Nothing catches it: not review, not reading, not proofreading, and not
`pip install` either, because pip stops at the first one. So the workflow now runs a
**resolution-only pass** before installing, which finds all of them in ~20 seconds instead of
one per CI run.

The Arch Doc §3.4 stack table carried three of the same wrong versions and is corrected, with
the correction inline so a reader comparing it to an old `requirements.txt` knows why they
differ.

---

### 2.31 CI green end-to-end — and a config file that documented decisions it was not making

The full lint-and-test job now passes locally, run with the same commands the
workflow runs. The failures it took to get there were not the interesting part.
The interesting part is **how three of them were invisible**.

**1. CI would have failed on a database credential it never set.** The Postgres
service creates user `postgres`; `base.py` reads `POSTGRES_USER` and defaults it
to `fairfold`; the workflow set `DB_PASSWORD` but never `POSTGRES_USER`. Every
database-touching test died with `password authentication failed for user
"fairfold"` — which reads as a wrong password, not a wrong username, and sends
you to rotate a secret that is correct. Reproduced locally before fixing, then
verified fixed.

**2. `bandit.yaml` had four `skip:` lines, and none of them did anything.** Two
independent causes, both silent:

- YAML keeps only the **last** of a repeated key, so three of the four were
  discarded before bandit ever read the file.
- bandit does not read a skip list from a YAML config **at all**. Verified
  against the installed source: `bandit/core/config.py` exposes `exclude_dirs`
  and profiles, and nothing reads `skip` or `skips`. Skips come from `-s` or a
  `.bandit` ini file.

So the file documented four deliberate exceptions, and a reader — including me —
would conclude all four were active. A scanner that silently checks nothing is
worse than no scanner: it reports "0 issues", which looks like a clean codebase.
The skips now live in the workflow's `-s` flag, and `bandit.yaml` explains why
that is the only place they work.

**3. My "flake8 passes" claim was from the wrong command.** There is no flake8
config in the repo, and flake8 does not read `pyproject.toml`, so a bare
`flake8 .` enforces a **79-character** limit. CI passes `--max-line-length=120`
on the command line. My local check used the default and would have reported
~400 violations that CI never sees; CI's own run had 7 real ones I had not
looked at (two missing trailing newlines, five over-long Django-generated
migration lines). The claim "flake8 passes" was true of neither command.

**Migrations are now excluded from flake8, black and isort.** Django rewrites
those files wholesale on every `makemigrations`, so hand-wrapping them buys
nothing and the next model change undoes it. The exclusion is applied
consistently and asserted.

**Also fixed, and worth recording because it is the same bug twice more:**

- `production.py` does `from base import *`, which copies *references*. Importing
  it in a test rewrites the live `DATABASES` dict, leaving `sslmode="require"` in
  place so test-database teardown fails with *"server does not support SSL, but
  SSL was required"*. My first two fixes for this both looked right and both
  restored nothing — one rebound the name (the connection kept its reference),
  the next cleared before recursing (so every nested dict was replaced anyway).
  The third recurses in place, and `tests/core/test_settings_isolation.py`
  exists specifically so neither broken version can come back silently.
- `seed.py` declared a method `@staticmethod` while its body used `self` — a
  `NameError` on every seed run, invisible until the command was executed.

**New check — §13 of `verify_docs.py`.** A config file whose comments describe
behaviour it does not have is worse than no config file, because it is trusted.
The new check asserts no YAML config repeats a top-level key, that every bandit
ID justified in `bandit.yaml` is actually enforced (`-s`, or a justified
`exclude_dirs`), that `bandit.yaml` does not rely on an unsupported `skips:` key,
and that the migration exclusion is applied to all three tools. Negative-tested
four ways: duplicate key, `skips:` reintroduced, `-s` removed from the workflow,
flake8 exclusion removed. All four caught.

**Final state — 115 tests, 91.04% coverage (gate is 80%).** flake8, black, isort,
mypy, bandit, `verify_docs.py`, `verify_bias_set.py`: all green, each run with
the command CI actually uses.

---

### 2.32 A security step that had never been run

The job now runs **3–4 minutes** instead of failing at 53 seconds, which is the
good news: pip install completes, so the failure moved much later in the job.

The cause is one line of `requirements.txt`:

```
djangorestframework  3.15.1  PYSEC-2026-1304  fix 3.15.2
djangorestframework  3.15.1  PYSEC-2026-3827  fix 3.17.2
djangorestframework  3.15.1  PYSEC-2026-3828  fix 3.17.2
```

`pip-audit` exits non-zero on any advisory, so a two-minor-version-old pin with
three known CVEs was a hard build failure. Raised to **3.17.2**; the audit now
reports *No known vulnerabilities found*. Verified against the installed package
rather than assumed: `manage.py check`, `spectacular`, and all 115 tests still
pass on 3.17.2.

**Why this survived four rounds of CI fixes.** In the previous round I reported
"all 8 stages green." That was true — and covered 8 of roughly twenty steps.
I never ran `pip-audit`, `check-budget`, `collectstatic`, the spaCy model load,
or `migrate`+`seed` against a clean database. Every stage I *did* run passed, and
I wrote the sentence as though the job would now pass. Sampling the checks and
describing the result as the whole is the error, and it is the same shape as the
earlier ones: a narrower claim stated as a wider one.

All five untested steps have now been run. The other four passed first time.

**One consequence worth recording.** `bandit` was skipped by four `skip:` entries
that were never active (§2.31). `pip-audit` was not skipped — it was simply
never run. A scanner nobody has executed is not a control, it is a line in a
YAML file, and it reports "0 issues" either way.

**Final state:** all 13 executable CI steps plus `migrate`/`seed` and pytest pass
locally, each run with the command the workflow uses.

---

### 2.33 The command was right; the environment it ran in was wrong

`Django system check` failed with:

```
ImproperlyConfigured: CLAMD_HOST is required but not set
```

`base.py:324` declares `CLAMD_HOST = env_required("CLAMD_HOST")`. Every *other*
Django step sets it. This one did not — it set `DATABASE_URL` instead, and
**no settings module reads `DATABASE_URL` at all**. `base.py` builds `DATABASES`
from `POSTGRES_DB` / `DB_HOST` / `DB_PASSWORD`. So that variable was inert: it
read as "the database is configured in this step" while configuring nothing.

The step now declares the same variables as every other Django step.

**Third recurrence of one mistake, and the most expensive.** The previous round
reported "all 20 CI steps pass in CI order." That simulation exported **one
shared environment** for all twenty steps. The real workflow gives each step its
*own* `env:` block, and they differ. I verified every command and none of the
environments they actually run in. A developer's shell or a `.env` supplies the
missing variable locally, so the command passes on the machine that wrote it and
fails only on the runner.

Round 1 was a version that did not exist. Round 2 was an env var set under the
wrong name. Round 3 was a scanner never executed. This round is a command verified
in an environment that was not the one it runs in.

**§14 of `verify_docs.py` now asserts it.** For every step whose `run:` invokes
`manage.py` or `pytest`, each `env_required` variable in the settings chain must
appear in that step's `env:` block or the job-level `env:`. It also flags any step
setting `DATABASE_URL` when no settings module reads it. Negative-tested three
ways: the exact bug above, `CLAMD_HOST` removed from `Run tests`, and an unread
`DATABASE_URL` added elsewhere. All three caught.

Writing that check went wrong twice before it worked, which is why the
negative tests matter. `splitlines()[:]` is a **full slice**, not an empty one, so
the first version harvested env keys from the entire file — every required
variable looked present and the check could not fail. The second returned no keys
at all because the `env:` header was excluded. Both looked correct and both were
useless; only the negative test distinguished them.

---

### 2.34 Fahad Haque departed — team back to four ✅

**Fahad Haque** has left the project. His UI/UX responsibilities are absorbed back
by **Mohammad Abdul Ahad**, the remaining UI/UX Designer. Concretely:

- **Wireframes** — Mohammad now owns candidate journey wireframes (previously split with Fahad).
- **Employer dashboard UX** — consolidated under Mohammad's design system ownership.
- **Journey-map design** — consolidated under Mohammad.

**Updated everywhere needed:**

| File | Change |
|---|---|
| `prd.md` §2, §17.2 | Team line reduced from 5 to 4; Fahad's row removed; Mohammad's row absorbs wireframes, employer dashboard UX, and journey-map design |
| `design.md` §1 | Co-owner removed; Mohammad Abdul Ahad is sole owner |
| `FAIRFOLD_Complete_Project_Document.md` §2, §C.6 | Team line reduced from 5 to 4; Fahad's row removed; Mohammad's row absorbs wireframes |
| `FAIRFOLD_Feasibility_and_Design.md` §2.7.3, §10.4, §2.7.4 | Team row updated (4); conflict table §9 updated to record the reversion; all "5-person" prose references corrected to "4-person" |
| `FAIRFOLD_Project_Architecture_and_Requirements.md` §1 | Authors list reduced from 5 to 4 |
| `pyproject.toml` §5.5 | mypy comment corrected to "four-person team" |

**Not changed (correctly left alone):**
- The "5-person" count in HISTORY.md §2.14 and §2.16 — these are historical entries
  that accurately record the team state at the time those changes were made.
- `Samira Haque` referenced in `design.md` §13 — a different person (sample/test data).

**Not in git:** no commits authored by Fahad Haque were found in repository history.

### 2.35 CI: Docker Hub login step now skips cleanly when credentials are absent

The `build-and-push` job (gated on `main` only) failed with an auth error because
`DOCKERHUB_USER` and `DOCKERHUB_TOKEN` repository secrets were not set. Since the
project is still in the **documentation phase** with no image to ship, the "Build
and push" step is now conditional on those secrets existing. The login step still
runs — it fails fast with a clear message rather than a cryptic auth failure.

**To enable pushes:** add `DOCKERHUB_USER` and `DOCKERHUB_TOKEN` as repository
secrets (Settings → Secrets and variables → Actions), then the build-and-push
step will run automatically.

---

## 3. Gap status

| Gap | Original state | Now |
| --- | --- | --- |
| **A** — Requirement collection method | ❌ blocking | ✅ **closed** — Feasibility §1.3, `prd.md` §3.4, tagged [Done]/[Illustrative]/[Planned] (§2.20). Validation plan stays **[Planned]** until actually run |
| **B** — Real-world problem example | ❌ missing | ✅ **closed** — Amazon 2018 primary + iTutorGroup / HireVue / Mobley + 3 BD sources (§2.20). *Mobley* needs re-verification before public citation |
| **C** — Wireframes | ❌ none at all | ✅ **complete for low fidelity** — 52 wireframes (18 `S` + 5 `X` + 29 `W`) covering **all 62 pages**, including the four screening-integrity components (§2.30). Figma and hi-fi still open |
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
| **Y** — Bias test set had no target | 🟠 the keyword pass could only be shown to work on examples it was written from | ✅ **specified (§2.26), authored (§2.27), implemented and measured (§2.28), numeric layer added (§2.29)** — **two versions: v1.0.0 (76) and v1.0.1 (103 cases, 13 categories, +5 numeric rules)**, `ai/bias_pass.py`, 25 CI assertions, recall 1.0 · **0 FP** · rate **0.7282**. `LIM-001`/`LIM-002` closed by fix; `LIM-003`/`GAP-001` by decision |
| **AB** — Line-count checker compared the wrong files | *(not previously found)* — reported green while 4 of 6 self-reported counts were stale | ✅ **fixed and negative-tested** — it now compares a claim against the file the row *names* (§2.29) |
| **AA** — §7.4.5's flag-rate band was unsatisfiable | *(not previously found)* — 100% recall on categories 1–8 forces a flag rate of 1.0, above the 0.95 ceiling | ✅ **fixed** — band now applies to the overall rate across all 76 cases; found by running the pass (§2.28) |
| **Z** — AD-006 still said "Team of 4" after the rename pass | *(not previously found)* — §2.23 conflict 9 was recorded as fixed with one occurrence untouched | ✅ **fixed** — and `scripts/verify_docs.py` added so the class of bug is caught, not re-found (§2.26) |

---

## 4. Outstanding work

**No item in this section blocks the start of development.** All four first-hour blockers —
the incomplete API list, the 25 December milestone, the `REQ-FR-050` scope call and the
bias test set's missing target — are now closed or specified (§2.25, §2.26). What remains
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

**✅ The spec exists (§2.26), the cases exist (§2.27), and the pass is built and measured
(§2.28).** `tests/bias/v1.0.0/` · 76 cases · `ai/bias_pass.py` · 15 CI assertions · recall
1.0 · 0 false positives · flag rate 0.7632.

**Nothing is outstanding here.** `LIM-001` (numeric age) and `LIM-002` (graduation-year
proximity) were **closed by fix in v1.0.1** (§2.29). Two limitations remain **decided
rather than fixed** and are recorded as such: `LIM-003` (no Bengali term list — accepted out
of scope, so a Bengali resume gets a zero flag rate with no indication the check did not
apply) and `GAP-001` (bare adjectives stay out of the term list). If either is reopened,
`keyword_terms.json` says where. `LIM-004` (no word boundaries) is open and low.

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
prototype (5), logo and icon sets (7–8), notification copy (9), usability test plan (10).

> **Item 11 closed 2026-10-04 (§2.30).** The two new screening-integrity components, the
> `not_matched` filter state on #40 and the gate panel on #41 now have drawings (`W26`–`W29`).

**This section previously said "26 pages have a spec but no wireframe", including #31 and #48,
so `REQ-FR-043` had no drawing.** That is no longer true: all 62 pages carry a wireframe, and
`verify_docs.py` §11 fails the build if any of the 62 page rows has a blank wireframe cell or
references an id with no drawing. **What is still open is Figma and hi-fi — a different thing
from having no wireframe**, and the distinction is worth keeping: an ASCII wireframe is a
build brief, a hi-fi mockup is a design artefact.

⚠️ And the honest limit: "has a wireframe" does not mean "is buildable". A layout proven only
in a monospace grid can still fail at implementation, which is why §4.6 stays 🟡 and not ✅.

#### Start here, designer — the order that unblocks the most

All 62 pages have a text wireframe (§10.5). These are the items in §12 order, with the
reasoning for the sequence:

1. **§12 item 1 — Figma file with tokens** — before anything else. Every other Figma task
   imports colour, type and spacing from §3–§5, and doing them first means re-doing them when
   the token set changes. `static/css/tokens.css` already holds these values as CSS custom
   properties, so the file and the tokens must stay in step.
2. **§12 item 7 — logo, favicon, social image.** Now unblocked: the name is **FairFold**
   (§4.7 item 5). ⚠️ **Do not print the logo on packaging, the domain registration or any
   public collateral until `RSK-011`'s formal trademark search returns** (§4.1). A search is
   not a clearance.
3. **§12 item 2 — component library with all states**, then **item 4 — hi-fi at 360px and
   1280px** for the core flow. 360px first, always (§5.3).
4. **§12 item 10 — usability test plan** (5 candidates, 5 recruiters; task: apply / screen and
   shortlist). Needs no Figma, so it can run in parallel with the above.

**Two constraints that are easy to miss and expensive to fix late:**

- **Anonymised views are marked as such** on #40 and #41, and the name reveals only at
  shortlist (§4.7 item 2). A hi-fi mock that shows the name everywhere silently contradicts
  `REQ-FR-030`.
- **`--ai` colour is violet, used *only* for AI-generated content** (§3.1). It is never a
  success and never a warning — the first would claim the system endorses the output, the
  second that it is suspect. Every AI number sits next to its reason (§1).

#### What the designer should not wait for

Nothing in §12 items 1–4 or 7–8 depends on a Django model existing, an AI provider key, or the
scaffold booting. The design can start immediately and in parallel with backend work.

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
694b537  docs: correct three wrong claims in the log, and fix 8 broken README commands
4ef2aa0  feat: add the three files §6.1/§6.2/§6.5 specified and did not have
744afae  feat: scaffold the Django project, close the last wireframe gap, fix two contradictions
2e855a8  feat: bias set v1.0.1 closes LIM-001 and LIM-002; fix a checker that could not fail
8e67148  feat: implement the deterministic bias pass, and decide LIM-003 and GAP-001
0711081  test: author the v1.0.0 bias test set, 76 cases across all ten categories
736ccd6  docs: specify the bias test set, decide REQ-FR-050, and add a docs checker
741542c  docs: close the API blocker and the remaining gaps, and make ASM-003 falsifiable
4b4ea7e  docs: move the Phase 4 milestone, record AI-assisted development, and build the broadcast feature
ca4061f  docs: readiness review before development — nine conflicts settled, five gaps opened
1079588  docs: rename to FairFold, and withdraw the bias-free claim the product cannot support
2f7f01f  docs: trace requirements back to the problem, and flag a contested product name
f342dd0  docs: re-base the Gantt, close two schema holes, and decide the open questions
76106b8  docs: correct the document index now that six documents exist
9d6a762  docs: order the HISTORY.md section numbers correctly
4ec59df  docs: replace the team roster with the current five members
7f51aff  docs: close the round-2 traceability gaps with REQ-FR-044 to 050
36ccdb6  docs: sync all docs to the expanded design.md and record round-2 gaps
96993d4  docs: promote REQ-FR-042/043 to the Arch Doc and reconcile spec drift
34fbe78  Create design.md
```

Upstream `main` also contains merge commits `18d5713` (PR #6), `bc47ae0` (PR #7) and
`ed05fef` (PR #8), which fold the earlier branch work into `main`.
