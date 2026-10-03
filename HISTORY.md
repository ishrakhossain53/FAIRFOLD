# MATCH_MINDS — Project History

A running log of what has been done on this repository and what is still outstanding.
Kept by hand; updated whenever a chunk of work lands.

- **Repository:** `github.com/ishrakhossain53/MATCH_MINDS` (private)
- **Last updated:** 2026-10-03
- **Current branch:** `ishrakhossain53-patch-1`
- **Latest commit:** `b16b7a6` — *docs: correct wireframe row 4 to reference GAP-1, not FR-022*
- **Project state:** documentation phase. No application code has been written yet.

---

## 1. Project baseline

Started from an initial documentation-only commit (`6c2632e Initial commit`, then
`67bd089 Initial Documentations`). The repository currently contains **no source code** —
only specifications, requirements, and supporting configuration.

| File | Lines | Role |
| --- | ---: | --- |
| `MATCH_MINDS_Complete_Project_Document.md` | 1914 | Canonical product document — vision, personas, competitor analysis, journeys, model reference, roadmap, team roles, appendices |
| `MATCH_MINDS_Project_Architecture_and_Requirements.md` | 1714 | Canonical specification — ADRs, 41 functional requirements, 50 non-functional requirements, 21-table SQL schema, sequence diagram, ops/runbook, risk register, acceptance criteria |
| `MATCH_MINDS_Feasibility_and_Design.md` | 1742 | Feasibility + design companion (added during this phase — see §2.3) |
| `README.md` | 200 | Project overview, documentation index, setup |
| `.env.example` | 142 | 25 environment variables, all placeholders |
| `requirements.txt` / `requirements-dev.txt` | 52 / 24 | Pinned Python dependencies (planned stack) |
| `scripts/generate_secret_key.py` | 136 | Generates a per-developer `DJANGO_SECRET_KEY` + `ENCRYPTION_KEY` into `.env` |

**Key numbers of record** (used throughout the docs; verified by re-counting):

- 41 functional requirements, `REQ-FR-001` … `REQ-FR-041` (Arch Doc §4.1)
- 50 non-functional requirements in §4.2, in five groups:
  `REQ-SEC-001`–`014` (14), `REQ-COM-001`–`009` (9), `REQ-NFR-001`–`018` (18),
  `REQ-NFR-019`–`023` (5, code quality), and four operational `REQ-NFOR-001`, `-002`, `-024`, `-025`.
  ⚠️ `REQ-NFR` and `REQ-NFOR` interleave — a naive `REQ-NF` regex conflates them. Use `REQ-NFR-[0-9]+`.
- 21 database tables in Arch Doc §5.1, with 27 foreign keys declared (25 drawn in the ER
  diagram; 2 redundant `users` self-references intentionally omitted)
- 10 AES-256-GCM encrypted fields (PII at rest)
- 5 roadmap phases: Phases 1–4 = weeks 1–12 (MVP), Phase 5 = week 13+ (optional)

---

## 2. Work completed

### 2.1 Security audit — `.env` and credential hygiene ✅

Requested: check the repository for leaked secrets and confirm the push state.

- **Result: no leak.** `.env` is not tracked and does not exist on disk.
  `.gitignore:12` ignores it, with a `!.env.example` negation on line 14.
- Only `.env.example` is tracked, and every value in it is a placeholder
  (e.g. `change-me-generate-a-real-key`, `devpassword`).
- Tracked files were scanned for AWS keys, OpenAI keys, GitHub tokens, Slack tokens,
  Google API keys, PEM private-key headers, and JWTs — **no real credentials found**.
- `scripts/generate_secret_key.py` confirms the intended model: each developer generates
  their **own** secret and encryption keys, so keys must never be shared between machines.
- **Push state:** confirmed from local refs. `git fetch` / `ls-remote` fail in this
  environment (`could not read Username for 'https://github.com'` — no GitHub credentials
  available), so live remote verification is not possible from the agent side. The user
  pushes manually.

### 2.2 Specification gap audit ✅

Both original documents were read end to end and checked against a 20-item academic /
engineering specification rubric (feasibility study, UML diagrams, user stories, Gantt chart,
data dictionary, navigation, accessibility, methodology, risk register, and so on).

**8 real content gaps** were identified. None were fixed by editing the canonical specs
in place — see §2.4 for why.

### 2.3 `MATCH_MINDS_Feasibility_and_Design.md` ✅

A new companion document was created covering every gap. It was added as a **standalone
file** rather than as edits to the existing specs, because the canonical documents use
dense cross-references (`§5.6`, `§C.7`, …) that in-place edits would invalidate.

Contents:

- **5 Mermaid diagrams**, each validated against real Mermaid 11 grammar (build script at
  `/tmp/mmv`): use case diagram, activity diagram, class diagram, ER diagram, Gantt chart
- **Feasibility study** in five parts, §2.6.1–2.6.5: technical, economic, legal, operational,
  and schedule feasibility
- **42 user stories** / **170 story points**, MoSCoW-classified **26 Must / 13 Should / 3 Could**,
  with every one of the 41 functional requirements traced to at least one story
- **Data dictionary** for the 6 core entities
- **Methodology** (§2.7.1, Scrum), **Gantt chart** (§2.7.2), **team roles** (§2.7.3),
  **risk register** (§2.7.4)
- Navigation tree, WCAG 2.1 AA accessibility table, and a final coverage checklist (§4)

Content from the canonical specs is **cited, not duplicated**, to prevent the two documents
drifting apart.

**File history (rename preserved in git):**

| Commit | Change |
| --- | --- |
| `5e74189` | Added as `MATCH_MINDS_Academic_Submission.md` (1,739 lines) |
| `0486ee1` | Renamed to `MATCH_MINDS_Feasibility_and_Design.md` (git recorded a 96% rename) and linked from the README |
| `b16b7a6` | Fixed the wireframe FR citation for the job-browse screen |

The rename was also a reframe: coursework language ("rubric", "examiner",
"submission checklist") was replaced with engineering language, so the document is useful to
anyone auditing the build later rather than only to an assessor.

### 2.4 Corrections made during a self-audit ✅

The new document was audited against the source specs before hand-off. Several numbers in
the first draft were wrong and were corrected:

| Item | Wrong | Correct |
| --- | ---: | ---: |
| Non-functional requirements | 46 | **50** |
| User stories | 33 | **42** |
| MoSCoW split (Must/Should/Could) | 21 / 14 / 4 | **26 / 13 / 3** |
| Foreign keys | 24 | **27** declared (25 drawn in the ER diagram) |
| Encrypted fields | 8 | **10** |

Other fixes in the same pass:

- **Mermaid grammar bug.** `UC43([Export personal data (GDPR)])` — the stadium shape
  `([…])` cannot contain inner parentheses. Rewritten as
  `UC43([Export personal data — GDPR Art. 20])` and
  `UC44([Approve data deletion — GDPR Art. 17])`. All 5 diagrams now parse cleanly.
- **Missing stories.** Added stories for `REQ-FR-003` and `REQ-FR-007`, which had no coverage.
- **Duplicate story ID.** The admin story block collided on `US-051`; renumbered to
  `US-051` … `US-055`.
- **Traceability gaps documented, not invented.** §2.4.1 now records GAP-1 and GAP-2
  (below) rather than fabricating requirement IDs to paper over them.
- **Reference convention.** Added a note explaining how to read `§N.M` across the three
  documents, which previously collided ambiguously:
  `§N.M` in **Arch Doc**, `§N.M` in **Complete Doc**, and a bare `§N.M` = the feasibility
  and design document.

### 2.5 README ✅

- Added a **Documentation** table near the top linking all three specifications.
- Briefly sketched a `docs/` tree entry, then removed it because the directory does not exist.

### 2.6 Wireframe cross-reference bug ✅

The wireframe table in §3.9.1 cited `REQ-FR-022` ("Job Application") for the
job browse / search results screen — but that requirement is about *applying*, not
*browsing*, which hid the GAP-1 traceability hole. Corrected to `**GAP-1** ⚠️ (no FR exists)`.
All 23 other FR citations in that table were re-verified as valid.

---

## 3. Outstanding work

### 3.1 🔴 Requirement collection method — `Feasibility & Design §1.3` (line 97) — *blocks*

A table of how requirements were gathered. **4 of its 5 rows are still `?`.** Only
"Competitor analysis / 11 systems" is filled in. This section cannot be completed without
real facts, and fabricating an interview study would be academic misconduct.

Needed from the team:

- **A1** Which methods were actually used: stakeholder review, candidate interviews,
  recruiter interviews, survey, observation?
- **A2** Per method: sample size `N`, channel (LinkedIn / personal network / local IT firms /
  alumni), and date.
- **A3** The ~3 findings that actually shaped design decisions.
- **A4** Which functional requirement each finding produced. A candidate mapping can be
  proposed for correction.
- **A5** What was *not* done — honest blanks are fine and should be stated plainly.

Minimum viable answer: *"stakeholder review, 4 team members."*

### 3.2 🟡 Real-world problem example — `§1.2` (line 83)

A concrete, sourced real-world case of recruitment bias is still missing.

Recommended: the **Amazon 2018 CV-screening tool** — the model was trained on a decade of
mostly male CVs and learned to downgrade CVs containing the word "women's"; the effort was
eventually abandoned. Pair it with one line on how MATCH_MINDS differs (PII stripping plus a
full audit trail) so it does not read as "we read this article."

Needs only a yes/no from the team to proceed.

### 3.3 🟡 Wireframes — `§3.9.1` (line 1601)

The **specification table of 18 screens** (screen name, actor, source FRs) exists; the
**visuals** do not. Asif Salman Zarar (UI/UX) owns this. Three routes:

1. Export from the design tool into `docs/wireframes/` (the directory does not exist yet).
2. Paste/export the files into the repository root for review.
3. Generate low-fidelity ASCII wireframes for all 18 screens, clearly labelled
   *"low-fidelity, not final UI"* — **fastest to unblock**, but a stopgap.

Route 3 is offered as the quickest way to close the gap; not yet chosen.

### 3.4 🟢 Close GAP-1 and GAP-2 — optional, needs a yes/no

| Gap | Feature | Evidence it is already planned | Problem |
| --- | --- | --- | --- |
| **GAP-1** | Candidate job browse / search | Use case `UC16`; candidate journey step 5; user story `US-023` | No FR covers search, filtering, or job listing |
| **GAP-2** | Candidate ↔ employer messaging | `Message` model (Complete Doc §C.11); use case `UC31`; named as a differentiator in the executive summary; user story `US-050` | No FR covers sending, receiving, or read state |

Both are real product features rather than scope creep — GAP-2 in particular is called out in
the executive summary. The next free IDs are **`REQ-FR-042`** (job search) and
**`REQ-FR-043`** (messaging).

If the team confirms both are planned, the work is:

1. Add `REQ-FR-042` and `REQ-FR-043` with Given/When/Then acceptance criteria to
   Arch Doc §4.1
2. Update `Feasibility & Design §2.4.1` and the affected user stories / use cases
3. Re-run the FR-coverage check (currently 41/41; would become 43/43)

⚠️ **This would be the first edit to a canonical specification file.** The diff will be
shown for review before anything is committed.

### 3.5 Gantt chart dates — 🟡 illustrative only

The Gantt chart starts at `2026-01-05` with weekends excluded. **These are placeholders.**
Replace them with the real semester start/end dates and any exam or submission deadlines.

### 3.6 Schema design issue — 🟡 flagged, unfixed

Noted in `Feasibility & Design §3.7`: the `APPLICATIONS` foreign key **cascades** down to
`MESSAGES` and `INTERVIEWS` rows that belong to *other* users. Deleting one party to a
conversation therefore deletes the whole conversation for both sides.

Suggested fix: change those FKs to `ON DELETE SET NULL` and add a soft-delete flag on
`MESSAGES`, so a single user's erasure request does not wipe a counterparty's records
(also relevant to the GDPR requirements).

### 3.7 Push state

Everything committed through `b16b7a6` has been merged into `main` upstream (PR #8).
`git fetch` / `ls-remote` cannot be verified from this environment (no GitHub credentials),
so confirm on GitHub before assuming anything is synced.

---

## 4. Conventions worth remembering

- **Never fabricate** research, statistics, interview counts, or credentials. An honest
  "not done" beats an invented study.
- **Never push without explicit go-ahead**, and never push directly to `main`.
- Per-developer secrets: keys from `scripts/generate_secret_key.py` are machine-specific and
  must not be committed or shared.
- Reference convention: `Arch Doc §N.M` / `Complete Doc §N.M` / bare `§N.M` = feasibility and
  design doc.
- Mermaid diagrams must be validated before commit:
  `cd /tmp/mmv && node extract.js && node check2.mjs`

---

## 5. Commit history

```
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

Upstream `main` also contains merge commits `18d5713` (PR #6), `bc47ae0` (PR #7), and
`ed05fef` (PR #8), which fold this branch's work into `main`.
