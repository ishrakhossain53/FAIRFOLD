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
| `MATCH_MINDS_Project_Architecture_and_Requirements.md` | 1750 | **Canonical** specification — ADRs, 50 functional requirements, 50 non-functional requirements, 21-table SQL schema, sequence diagram, ops/runbook, risk register, acceptance criteria |
| `prd.md` | 919 | **Canonical** product requirements — objectives, success metrics, FRs with phases, AI requirements, data model, API surface, pricing, release criteria, open questions |
| `design.md` | 1328 | Supplement — UI design system, 62 page specifications, 23 wireframes, implementation notes |
| `MATCH_MINDS_Feasibility_and_Design.md` | 1893 | Supplement — feasibility study, user stories, UML diagrams, Gantt, data dictionary, accessibility |
| `README.md` | 205 | Project overview, documentation index, setup |
| `.env.example` | 142 | 25 environment variables, all placeholders |
| `requirements.txt` / `requirements-dev.txt` | 52 / 24 | Pinned Python dependencies (planned stack) |
| `scripts/generate_secret_key.py` | 136 | Generates a per-developer `DJANGO_SECRET_KEY` + `ENCRYPTION_KEY` into `.env` |

**Key numbers of record** (verified 2026-10-03):

- **50 functional requirements**, `REQ-FR-001` … `REQ-FR-050` (Arch Doc §4.1)
  — was 41 until `REQ-FR-042`/`043` were added (§2.8), then 43 until
  `REQ-FR-044`–`050` were added (§2.14)
- **50 non-functional requirements** in Arch Doc §4.2, in five groups:
  `REQ-SEC-001`–`014` (14), `REQ-COM-001`–`009` (9), `REQ-NFR-001`–`018` (18),
  `REQ-NFR-019`–`023` (5, code quality), and four operational `REQ-NFOR-001`, `-002`, `-024`, `-025`.
  ⚠️ `REQ-NFR` and `REQ-NFOR` interleave — a naive `REQ-NF` regex conflates them. Use `REQ-NFR-[0-9]+`.
- **21 database tables** in Arch Doc §5.1, with 27 foreign keys declared (25 drawn in the ER
  diagram; 2 redundant `users` self-references intentionally omitted)
- **10 AES-256-GCM encrypted fields** (PII at rest)
- **49 user stories / 199 story points**, MoSCoW **27 Must / 17 Should / 5 Could** —
  every one of the 50 FRs maps to at least one story (verified programmatically)
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

### 2.3 `MATCH_MINDS_Feasibility_and_Design.md` ✅

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
| `5e74189` | Added as `MATCH_MINDS_Academic_Submission.md` |
| `0486ee1` | Renamed to `MATCH_MINDS_Feasibility_and_Design.md` (git recorded a 96% rename) |
| `b16b7a6` | Fixed the wireframe FR citation for the job-browse screen |
| `c7d8c00` | Added `HISTORY.md`; fixed a misaligned table row |
| `96993d4` | FR count 41 → 43; GAP-1/GAP-2 closed; story-point split reconciled; `resource_id` → UUID |
| `36ccdb6` | Synced to the expanded `design.md`; wireframes 3 → 23; recorded round-2 gaps |
| *(uncommitted)* | Round-2 gaps closed: FR count 43 → 50, stories 42 → 49, points 170 → 199 |
| *(uncommitted)* | Team roster replaced with the current five members across all six documents |
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
| **Gantt runs backwards** | Starts `2026-01-05`, but the documents are dated September 2026 | Left as an explicit placeholder (see §4.5) — the chart cannot be dated until the real kickoff is known |

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

### 2.15 Team roster replaced ✅

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

### 2.14 Fixes to `design.md` itself ✅

Three stale or wrong items inside the revised file:

- `REQ-FR-042 (proposed)` → `REQ-FR-042`, since it was promoted to the Arch Doc
- Four traceability-gap rows said *"Add an FR to the PRD"* — but functional requirements live
  in the **Arch Doc §4.1**, not the PRD. Corrected, with the next free IDs named.
- A cross-reference to *"the PRD, Section 19, item 4"* → made precise as
  ``prd.md §19.2 item 4 (PII retention)``

---

## 3. Gap status

| Gap | Original state | Now |
| --- | --- | --- |
| **A** — Requirement collection method | ❌ blocking | ❌ **still open.** `prd.md` §19.1 item 1 confirms it was built without one |
| **B** — Real-world problem example | ❌ missing | ❌ **still open.** `prd.md` §19.1 item 2 |
| **C** — Wireframes | ❌ none at all | ✅ **complete for low fidelity** — 23 wireframes, all 18 screens, all 22 core-flow pages. Figma and hi-fi still open |
| **D** — GAP-1 / GAP-2 | ⚠️ documented, no FR | ✅ **closed** — `REQ-FR-042`/`043` in the Arch Doc |
| **E** — Round-2 page gaps | *(not previously found)* | ✅ **closed** — `REQ-FR-044`–`050`, 7 stories added (§2.12, §2.13) |

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

Minimum viable answer: *"stakeholder review, 5 team members."*

### 4.2 🟡 Real-world problem example — `§1.2` (line ~83)

A concrete, sourced real-world case of recruitment bias is still missing.

Recommended: the **Amazon 2018 CV-screening tool** — the model was trained on a decade of
mostly male CVs and learned to downgrade CVs containing the word "women's"; the effort was
eventually abandoned. Pair it with one line on how MATCH_MINDS differs (PII stripping plus a
full audit trail) so it does not read as "we read this article."

Needs only a yes/no from the team to proceed.

### 4.3 ~~Seven pages with no functional requirement~~ ✅ closed

Found by the page-level design audit, now written into the Arch Doc as `REQ-FR-044`–`050`
with matching stories `US-056`–`US-062`. Full list in §2.13.

**One decision remains: is `REQ-FR-050` (broadcast announcement, page #62) worth building?**
It is deliberately marked optional. If not, remove the FR, `US-062` and the page together —
keeping one of the three would break traceability again.

### 4.4 🟡 Design tooling — `design.md` §12

The content decisions are all recorded as text, which is enough to brief a build. Still
outstanding, and all owned by Mohammad Abdul Ahad (UI/UX):

- Figma file and Figma components (items 1, 2) — decisions are in §3–§7, §6.6, §11.1
- High-fidelity mockups, mobile 360px and desktop 1280px (item 4)
- Interactive Journey Map prototype (item 5) — `S08` draws the four states, nothing is clickable
- Logo set, favicon, social image, icon set (items 7, 8)
- Microcopy for emails and notifications (item 9) — in-app copy is drafted in §2.3
- Usability test plan: 5 candidates, 5 recruiters (item 10)

**26 pages have a spec but no wireframe** (`design.md` §10.6). These reuse components already
drawn in `S01`–`S18`, so they are lower risk — but note **#31 and #48 are the two messaging
pages**, so the `REQ-FR-043` UI has no drawing even though the requirement now exists.

### 4.5 🟢 Unconfirmed design decisions — `design.md` §12

1. Score-band thresholds, once the scoring model is calibrated
2. **When the candidate's name is revealed to the employer** — also open in `prd.md` §19.2 item 4.
   This one changes pages #40 and #41 and is a genuine privacy decision, not a cosmetic one.
3. Whether dark mode ships in the MVP
4. Whether Bengali ships at launch (the PRD defers it to Phase 5)
5. Final brand name styling, logo and accent colour

### 4.6 🟡 Missing API endpoints — `Complete Doc §C.12`

Flagged by `prd.md` and now noted in both the Arch Doc and the feasibility doc:
public job browse/search endpoints for `REQ-FR-042`, and GDPR export/delete endpoints for
`REQ-FR-040`/`041`. Must be added before the build starts.

### 4.7 Gantt chart dates — 🟡 illustrative only

The Gantt starts `2026-01-05` with weekends excluded, but the documents are dated
September 2026 — the chart currently runs backwards. Replace with real semester dates,
including any exam or submission deadlines.

### 4.8 Schema design issue — 🟡 flagged, unfixed

Noted in `Feasibility §3.7`: the `APPLICATIONS` foreign key **cascades** down to `MESSAGES`
and `INTERVIEWS` rows belonging to *other* users. Deleting one party to a conversation deletes
it for both sides. `REQ-FR-043` now mandates soft-delete for messages, but the FK definitions
in Arch Doc §5.1 still need changing to `ON DELETE SET NULL`.

### 4.9 Other inconsistencies logged in `prd.md` §19.2

The PRD's 14-item register is a good backlog of smaller decisions. The ones with real
engineering consequences:

- **#4** — PII retention is undefined: where the *original resume file* and *un-stripped text*
  live, and who can see them, is not specified anywhere
- **#5** — Audit logs rotate at 90 days (`REQ-COM-008`) while candidate data is retained
  2 years; AI Act accountability may need decision evidence longer than 90 days
- **#6** — `AuditLogEntry.resource_id` type conflict. **Fixed** (§2.9); the Arch Doc was correct
- **#7** — Auth model: sessions vs JWT are both specified. Proposed split is sessions for the
  HTMX UI, JWT for the API
- **#12** — The bias audit claims "100% flagged on test dataset", but no versioned test set
  exists yet. Needs building in Phase 2
- **#13** — The Professional tier lists interview recording and analysis, but video recording
  is out of scope
- **#1, #2** — Pricing conflicts between the Complete Doc and the feasibility doc

### 4.10 Push state

The user pushes manually; `git fetch` / `ls-remote` cannot be verified from this environment
(no GitHub credentials). Confirm on GitHub before assuming anything is synced.

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
(uncommitted)  docs: update all docs for the expanded design.md; record round-2 gaps
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
