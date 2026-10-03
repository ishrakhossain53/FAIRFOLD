# MATCH_MINDS — Project History

A running log of what has been done on this repository and what is still outstanding.
Kept by hand; updated whenever a chunk of work lands.

- **Repository:** `github.com/ishrakhossain53/MATCH_MINDS` (private)
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
| `MATCH_MINDS_Complete_Project_Document.md` | 1914 | **Canonical** product document — vision, personas, competitor analysis, journeys, model reference, roadmap, team roles, appendices |
| `MATCH_MINDS_Project_Architecture_and_Requirements.md` | 1732 | **Canonical** specification — ADRs, 43 functional requirements, 50 non-functional requirements, 21-table SQL schema, sequence diagram, ops/runbook, risk register, acceptance criteria |
| `prd.md` | 891 | **Canonical** product requirements — objectives, success metrics, FRs with phases, AI requirements, data model, API surface, pricing, release criteria, open questions |
| `MATCH_MINDS_Feasibility_and_Design.md` | 1814 | Supplement — feasibility study, user stories, UML diagrams, Gantt, data dictionary, accessibility |
| `design.md` | 733 | Supplement — UI design system, 62 page specifications, wireframes, implementation notes |
| `README.md` | 204 | Project overview, documentation index, setup |
| `.env.example` | 142 | 25 environment variables, all placeholders |
| `requirements.txt` / `requirements-dev.txt` | 52 / 24 | Pinned Python dependencies (planned stack) |
| `scripts/generate_secret_key.py` | 136 | Generates a per-developer `DJANGO_SECRET_KEY` + `ENCRYPTION_KEY` into `.env` |

**Key numbers of record** (re-counted and verified 2026-10-03):

- **43 functional requirements**, `REQ-FR-001` … `REQ-FR-043` (Arch Doc §4.1)
  — was 41 until `REQ-FR-042`/`043` were added; see §2.8
- **50 non-functional requirements** in Arch Doc §4.2, in five groups:
  `REQ-SEC-001`–`014` (14), `REQ-COM-001`–`009` (9), `REQ-NFR-001`–`018` (18),
  `REQ-NFR-019`–`023` (5, code quality), and four operational `REQ-NFOR-001`, `-002`, `-024`, `-025`.
  ⚠️ `REQ-NFR` and `REQ-NFOR` interleave — a naive `REQ-NF` regex conflates them. Use `REQ-NFR-[0-9]+`.
- **21 database tables** in Arch Doc §5.1, with 27 foreign keys declared (25 drawn in the ER
  diagram; 2 redundant `users` self-references intentionally omitted)
- **10 AES-256-GCM encrypted fields** (PII at rest)
- **42 user stories / 170 story points**, MoSCoW **26 Must / 13 Should / 3 Could**
- **62 pages specified** in `design.md` §10; 24 flagged ★ as MVP-critical
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
  `prd.md` and `design.md` were re-scanned on 2026-10-03 when added: also clean.
- `scripts/generate_secret_key.py` confirms the intended model: each developer generates
  their **own** secret and encryption keys, so keys must never be shared between machines.
- **Push state:** `git fetch` / `ls-remote` fail in this environment
  (`could not read Username for 'https://github.com'` — no GitHub credentials), so live
  remote verification is not possible from the agent side. The user pushes manually.

### 2.2 Specification gap audit ✅

Both original documents were read end to end and checked against a 20-item academic /
engineering specification rubric. **8 real content gaps** were identified and addressed
across §2.3–2.8 below.

### 2.3 `MATCH_MINDS_Feasibility_and_Design.md` ✅

A companion document covering the diagramming, planning and feasibility gaps. Added as a
**standalone file** rather than as edits to the existing specs, because the canonical
documents use dense cross-references (`§5.6`, `§C.7`, …) that in-place edits would invalidate.

Contents:

- **5 Mermaid diagrams**, each validated against real Mermaid 11 grammar: use case, activity,
  class, ER, and Gantt
- **Feasibility study** in five parts, §2.6.1–2.6.5: technical, economic, legal, operational, schedule
- **42 user stories** / **170 story points**, MoSCoW-classified, every FR traced to ≥1 story
- **Data dictionary** for the 6 core entities
- **Methodology** (§2.7.1, Scrum), **Gantt chart** (§2.7.2), **team roles** (§2.7.3),
  **risk register** (§2.7.4)
- Navigation tree, WCAG 2.1 AA table, and a final coverage checklist (§4)

Content from the canonical specs is **cited, not duplicated**, to prevent drift.

| Commit | Change |
| --- | --- |
| `5e74189` | Added as `MATCH_MINDS_Academic_Submission.md` |
| `0486ee1` | Renamed to `MATCH_MINDS_Feasibility_and_Design.md` (git recorded a 96% rename); linked from README |
| `b16b7a6` | Fixed the wireframe FR citation for the job-browse screen |
| `c7d8c00` | Added `HISTORY.md`; fixed a misaligned table row |
| *(uncommitted)* | FR count 41 → 43; GAP-1/GAP-2 closed; story-point split reconciled; `resource_id` INTEGER → UUID; §3.9.1 rewritten around `design.md` |

The rename was also a reframe: coursework language ("rubric", "examiner",
"submission checklist") was replaced with engineering language, so the document is useful to
anyone auditing the build later rather than only to an assessor.

### 2.4 Corrections made during a self-audit ✅

Several numbers in the first draft were wrong and were corrected before hand-off:

| Item | Wrong | Correct |
| --- | ---: | ---: |
| Non-functional requirements | 46 | **50** |
| User stories | 33 | **42** |
| MoSCoW split (Must/Should/Could) | 21 / 14 / 4 | **26 / 13 / 3** |
| Foreign keys | 24 | **27** declared (25 drawn in the ER diagram) |
| Encrypted fields | 8 | **10** |

Other fixes in the same pass:

- **Mermaid grammar bug.** `UC43([Export personal data (GDPR)])` — the stadium shape
  `([…])` cannot contain inner parentheses. Rewritten with an em dash instead.
- **Missing stories.** Added stories for `REQ-FR-003` and `REQ-FR-007`, which had no coverage.
- **Duplicate story ID.** The admin block collided on `US-051`; renumbered to `US-051` … `US-055`.
- **Traceability gaps documented, not invented.** §2.4.1 recorded GAP-1 and GAP-2 rather than
  fabricating requirement IDs to paper over them.
- **Reference convention.** Added a note on how to read `§N.M` across the documents.

### 2.5 README ✅

Documentation table linking every spec, with a **role** column (Canonical vs Supplement)
and a "Start here" line pointing at `prd.md`, the Arch Doc, or this history file.

### 2.6 Wireframe cross-reference bug ✅

§3.9.1 cited `REQ-FR-022` ("Job Application") for the job browse / search screen — but that
requirement is about *applying*, not *browsing*, which hid the GAP-1 hole. Corrected.
All 23 other FR citations in that table were re-verified as valid.

### 2.7 `prd.md` and `design.md` added ✅ (team, 2026-10-03)

Two new canonical/supplement documents arrived in commits `6a50343` and `34fbe78`. Both were
audited for secrets (clean) and for consistency with the existing specs.

**`prd.md` (891 lines)** — a full PRD: objectives and success metrics, non-goals, personas,
market positioning, phases and MVP definition, FRs with priority and phase, AI requirements
(PII stripping, matching funnel, provider abstraction, graceful degradation, explainability),
NFRs, security and compliance, data model, architecture, API surface, UX and information
architecture, monetization, operations and delivery, risks, and a 14-item inconsistency
register (§19.2) that usefully cross-checked the other documents.

**`design.md` (733 lines)** — a UI design specification: brand and voice with a verbatim
microcopy library, colour tokens with **16 verified contrast ratios**, typography, spacing
and grid, app shell, 19 generic + 10 product-specific components, a state matrix, HTMX
interaction patterns, 13 accessibility rules, **62 page specifications**, 3 wireframes,
and implementation notes (CSS variables, Tailwind config, template tree, performance budget).

### 2.8 GAP-1 and GAP-2 closed ✅

`prd.md` §7.2–7.3 proposed `REQ-FR-042` (Job Browse and Search, High, Phase 1) and
`REQ-FR-043` (Candidate–Employer Messaging, Medium, Phase 3), each explicitly marked
*proposed*, and `design.md` already built pages #4, #5, #31 and #48 on top of them.
**Approved by the team and promoted into the canonical Arch Doc §4.1** as a new
*Job Discovery & Messaging* group.

Three conditions were written into the requirements rather than left to implementation guesswork:

- **REQ-FR-042** states an employer name is not disclosed until the employer opts in — a public
  job board otherwise leaks company identity by default.
- **REQ-FR-043** states messages are excluded from all AI processing and never reach an external
  provider, and that deleting one party **soft-deletes** rather than removes the counterparty's
  copy (the cascade problem in §3.7).

Downstream updates: FR count 41 → 43 everywhere; §2.2 gained a fifth group row; `US-023` and
`US-050` now carry real FR IDs instead of ⚠️ markers; §2.4.1 rewritten as *found, and now closed*;
§3.9.1 row 4 cites FR-042.

### 2.9 Three drift bugs found and fixed ✅

The PRD's inconsistency register exposed real errors in documents written earlier:

| Bug | Was | Now |
| --- | --- | --- |
| **Phase story points did not reconcile** | 21 + 34 + 31 + 30 + 25 = **141**, but §2.4 stated a 170-point total | Re-split to 28/41/37/36/28 = **170**, with a note that the figures are a planning estimate to be re-estimated at sprint planning |
| **`AuditLogEntry.resource_id` type conflict** | `INTEGER` in the class diagram, ER diagram and data dictionary; Arch Doc §5.1 says `UUID` | `UUID` everywhere, matching the Arch Doc — core entities all use UUID PKs |
| **Gantt runs backwards** | Starts `2026-01-05`, but the documents are dated September 2026 | Left as an explicit placeholder (see §4.3) — the chart cannot be dated until the real kickoff is known |

### 2.10 §3.9.1 rewritten around `design.md` ✅

The section previously said wireframes were *"not present in this repository"* — stale as soon
as `design.md` landed. It now states accurately:

- **18 of 18** required screens have a written page specification in `design.md` §10
- **3 of 18** have a wireframe visual: #40 ranked applications, #41 candidate review, #29 application detail
- A per-screen table showing spec status and wireframe status for each of the 18
- What `design.md` delivers beyond wireframes (7 rows, mostly ✅)
- What remains open in `design.md` §12 (Figma file, component library with states, hi-fi mockups, logo/icon sets, Journey Map prototype, a11y annotations)

§3.9.3 (accessibility) was also updated: the design-system responsibility note now points at
`design.md` §3.1/§3.2/§9/§11.1 and the shipped `chart_with_table.html` component, instead of
describing work that had not been done.

---

## 3. What the new documents changed about the gap list

| Gap | Before `prd.md` / `design.md` | Now |
| --- | --- | --- |
| **A** — Requirement collection method | ❌ blocking | ❌ **still open**; `prd.md` §19.1 item 1 confirms it was built without one |
| **B** — Real-world problem example | ❌ missing | ❌ **still open**; `prd.md` §19.1 item 2 |
| **C** — Wireframes | ❌ none at all | ⚠️ **3 of 18** have visuals; all 18 have page specs; design system complete |
| **D** — GAP-1 / GAP-2 | ⚠️ documented, no FR | ✅ **closed** — `REQ-FR-042`/`043` now in the Arch Doc |

---

## 4. Outstanding work

### 4.1 🔴 Requirement collection method — `Feasibility §1.3` (line ~97) — *blocks*

A table of how requirements were gathered. **4 of its 5 rows are still `?`.** Only
"Competitor analysis / 11 systems" is filled in. `prd.md` §19.1 item 1 confirms this was
never collected, and asks the team to state what was actually done.

**Cannot be completed without real facts, and fabricating an interview study would be
academic misconduct.** Needed from the team:

- **A1** Which methods were actually used: stakeholder review, candidate interviews,
  recruiter interviews, survey, observation?
- **A2** Per method: sample size `N`, channel (LinkedIn / personal network / local IT firms /
  alumni), and date.
- **A3** The ~3 findings that actually shaped design decisions.
- **A4** Which functional requirement each finding produced. A candidate mapping can be
  proposed for correction.
- **A5** What was *not* done — honest blanks are fine and should be stated plainly.

Minimum viable answer: *"stakeholder review, 4 team members."*

### 4.2 🟡 Real-world problem example — `§1.2` (line ~83)

A concrete, sourced real-world case of recruitment bias is still missing.

Recommended: the **Amazon 2018 CV-screening tool** — the model was trained on a decade of
mostly male CVs and learned to downgrade CVs containing the word "women's"; the effort was
eventually abandoned. Pair it with one line on how MATCH_MINDS differs (PII stripping plus a
full audit trail) so it does not read as "we read this article."

Needs only a yes/no from the team to proceed.

### 4.3 🟡 15 missing wireframes — `§3.9.1`

Three of 18 screens have visuals. The 15 without, listed per-screen in §3.9.1:

1 Registration/login · 2 Candidate onboarding + profile · 3 Resume upload ·
**4 Job browse / search** · 5 Job detail + apply · 6 Application tracker ·
8 Journey map · 9 Assessment taking · 10 Coaching feedback · 11 Employer job list +
create/edit · 14 Screening confirm + cost estimate · 15 Interview pack builder ·
16 Scheduling + feedback · 17 Analytics · 18 Admin users + audit log

Owner: Asif Salman Zarar (UI/UX). Options: export from the design tool into
`docs/wireframes/` (the directory does not exist yet), or have low-fi versions generated
in the style of `design.md` §10.5.

Also outstanding from `design.md` §12: the Figma file, a component library with all states,
high-fidelity mockups, logo and icon sets, the Journey Map prototype, and accessibility
annotations on key pages.

### 4.4 🟢 Unconfirmed design decisions — `design.md` §12

1. Score-band thresholds, once the scoring model is calibrated
2. **When the candidate's name is revealed to the employer** — also open in `prd.md` §19 item 4.
   This one changes pages #40 and #41 and is a genuine privacy decision, not a cosmetic one.
3. Whether dark mode ships in the MVP
4. Whether Bengali ships at launch (the PRD defers it to Phase 5)
5. Final brand name styling, logo and accent colour

### 4.5 🟡 Missing API endpoints — `Complete Doc §C.12`

Flagged by `prd.md` and now noted in both the Arch Doc and the feasibility doc:
public job browse/search endpoints for `REQ-FR-042`, and GDPR export/delete endpoints for
`REQ-FR-040`/`041`. Must be added before the build starts.

### 4.6 Gantt chart dates — 🟡 illustrative only

The Gantt starts `2026-01-05` with weekends excluded, but the documents are dated
September 2026 — the chart currently runs backwards. Replace with real semester dates,
including any exam or submission deadlines.

### 4.7 Schema design issue — 🟡 flagged, unfixed

Noted in `Feasibility §3.7`: the `APPLICATIONS` foreign key **cascades** down to
`MESSAGES` and `INTERVIEWS` rows belonging to *other* users. Deleting one party to a
conversation deletes it for both sides. `REQ-FR-043` now mandates soft-delete for
messages, but the underlying FK definitions in Arch Doc §5.1 still need changing to
`ON DELETE SET NULL`.

### 4.8 Other inconsistencies logged in `prd.md` §19.2

The PRD's 14-item register is a good backlog of smaller decisions. The ones with real
engineering consequences:

- **#4** — PII retention is undefined: Complete Doc §5.2 says PII is encrypted at rest,
  Arch Doc says original PII stays in `EncryptedCharField`, but it is not specified where
  the *original resume file* and *un-stripped text* live, or who can see them.
- **#5** — Audit logs rotate at 90 days (`REQ-COM-008`) while candidate data is retained
  2 years; AI Act accountability may need decision evidence longer than 90 days.
- **#6** — `AuditLogEntry.resource_id` type conflict. **Fixed** in the feasibility doc
  (§2.9); the Arch Doc was already correct.
- **#7** — Auth model: sessions vs JWT are both specified. Proposed split is sessions for
  the HTMX UI, JWT for the API.
- **#12** — The bias audit claims "100% flagged on test dataset", but no versioned test set
  exists yet. Needs building in Phase 2.
- **#13** — The Professional tier lists interview recording and analysis, but video
  recording is out of scope.
- **#1, #2** — Pricing conflicts between the Complete Doc and the feasibility doc.

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
- Mermaid diagrams must be validated before commit. Current harness lives at
  `/tmp/mmv2/check.mjs` (run `node check.mjs`) — **`/tmp` is wiped between sessions, so
  reinstall with `npm i mermaid@11 jsdom` if missing.** All 5 diagrams currently parse.
- When a spec count changes (FRs, stories, tables), grep the whole repo for the old number
  — it propagates into tables, checklists and cross-references.

---

## 6. Commit history

```
34fbe78  Create design.md
6a50343  Create prd.md
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
