# FAIRFOLD — Project History

A running log of what has been done on this repository and what is still outstanding.
Kept by hand; updated whenever a chunk of work lands.

- **Repository:** `github.com/ishrakhossain53/FAIRFOLD` (private)
- **Last updated:** 2026-10-16
- **Current branch:** `v3`
- **Project state:** runnable locally and **executed** — the Docker stack boots end to end
  (§2.38). Still a scaffold: no Django model exists, so `migrate` creates zero tables and the
  product does not yet do anything. See §1.

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
the 33 tables are still DDL in Arch Doc §5.1 — so `migrate` creates zero tables and no endpoint
responds. The value of the scaffold is that a first `manage.py check` tests import and config
rather than starting from nothing.

⚠️ **It has not been executed.** Django is not installed in the environment where it was
written, so "the scaffold is correct" is unverified until CI runs `manage.py check`.

✅ **Correction 2026-10-16: it has now been executed.** The stack was built and run cold on
Docker 29.8.2 — `docker compose down -v`, then `up -d --wait` against an empty database —
and again from a fresh-clone emulation (`cp .env.example .env`, generated keys, no pre-existing
volumes). All six services reached healthy, `migrate` ran from an empty database, `seed`
populated it, `collectstatic` collected 159 files, gunicorn served on `0.0.0.0:8000`, and every
key endpoint returned 200. Seven defects blocked that and are fixed in `d4b4ef3` (§2.38); four
of them left the container reporting **healthy** while the application was unreachable, so the
Docker healthcheck alone was not evidence that anything worked. The build instructions are now
step-by-step in `README.md`.

**Correction 2026-10-04:** an earlier revision of this section said the same about **Docker**,
implying Docker was also unavailable. **It is not** — Docker 29.8.2 is installed here. The
real reason nothing was built is that building was **out of scope for that task**, not
impossible. Correcting it because "I couldn't" is a stronger and more misleading statement
than "I didn't", and the difference matters when someone reads this to decide what is
blocked.

|| File | Lines | Role |
|| --- | --- | --- |
|| `FAIRFOLD_Complete_Project_Document.md` | 2449 | **Canonical** product document — vision, personas, competitor analysis, journeys, model reference, roadmap, team roles, appendices |
|| `FAIRFOLD_Project_Architecture_and_Requirements.md` | 2692 | **Canonical** specification — ADRs, 63 functional requirements (REQ-FR-001–063), 50 non-functional requirements, 33-table SQL schema, 53 foreign keys, 27 indexes, sequence diagram, ops/runbook, risk register, acceptance criteria |
|| `prd.md` | 1282 | **Canonical** product requirements — objectives, success metrics, FRs with phases, AI requirements, data model, API surface, pricing, release criteria, open questions |
|| `design.md` | 2918 | Supplement — UI design system, 78 page specifications, **64 wireframes covering all 78 pages**, frontend build tooling, implementation notes |
|| `FAIRFOLD_Feasibility_and_Design.md` | 3011 | Supplement — feasibility study, user stories, UML diagrams, Gantt, data dictionary, accessibility, pre-development readiness review |
| `README.md` | 447 | Project overview, documentation index, setup |

| `.env.example` | 220 | Environment variables, all placeholders (214 before batch 1.22 added `S3_PUBLIC_ENDPOINT_URL`; the count in this table was corrected 2026-10-22) |
|| `requirements.txt` / `requirements-dev.txt` | 92 / 25 | Pinned Python dependencies (planned stack) |
|| `scripts/generate_secret_key.py` | 139 | Generates a per-developer `DJANGO_SECRET_KEY` + `ENCRYPTION_KEY` into `.env` |

**Key numbers of record** (verified 2026-10-03, re-verified after §2.20, §2.23, §2.24, §2.25, and §2.34 — **updated 2026-10-12 after §2.25 and §2.26 additions; re-verified 2026-10-13 after §2.37; re-verified 2026-10-16 after §2.38**):

- **63 functional requirements**, `REQ-FR-001` … `REQ-FR-063` (Arch Doc §4.1)
  — was 41 until `REQ-FR-042`/`043` were added (§2.8), then 43 until
  `REQ-FR-044`–`050` were added (§2.14), then 50 until `REQ-FR-051`/`052` (§2.20)
- **50 non-functional requirements** in Arch Doc §4.2, in five groups:
  `REQ-SEC-001`–`014` (14), `REQ-COM-001`–`009` (9), `REQ-NFR-001`–`018` (18),
  `REQ-NFR-019`–`023` (5, code quality), and four operational `REQ-NFOR-001`, `-002`, `-024`, `-025`.
  ⚠️ `REQ-NFR` and `REQ-NFOR` interleave — a naive `REQ-NF` regex conflates them. Use `REQ-NFR-[0-9]+`.
- **33 database tables** in Arch Doc §5.1, with **53 foreign keys** declared (43 drawn in
  the ER diagram; the other 10 are implied self-references intentionally omitted). The count
  went 34 → 35 when `data_deletion_requests.approved_by` was added in §2.25, and 51 → 53 when
  `job_skills` was added in batch 0.5 (D-6c). `MESSAGES` is
  the one table whose FKs are `SET NULL` rather than `CASCADE` — see §2.17
- **10 AES-256-GCM encrypted fields** (PII at rest)
- **63 user stories / 260 story points**, MoSCoW **37 Must / 21 Should / 5 Could** —
  every one of the 63 FRs maps to at least one story. **Verified programmatically by
  `scripts/verify_docs.py`**, which runs in CI (§2.26)
- **78 pages specified** in `design.md` §10; **64 have wireframes** (32 drawings), covering
  all 18 required screens and all 22 core-flow pages; 68 of 78 pages carry a requirement ID
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
52 FRs, 52 stories / 212 points** — all verified programmatically. **Superseded 2026-10-12: now 32 tables, 51 FKs, 63 FRs, 63 stories / 260 points.**

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
  machine-verified, 5/5 Mermaid diagrams parse, 0 dangling references. **Superseded 2026-10-12: now 32 tables, 51 FKs, 63 FRs, 63 stories / 260 points.**
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
  Should / 5 Could. 5/5 Mermaid diagrams parse, 0 dangling `REQ-FR-` references. **Superseded 2026-10-12: now 35 tables, 41 FKs, 65 FRs, 64 stories / 237 points — 30 Must / 24 Should / 10 Could.**
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
|| `design.md` §1 | Co-owner removed; Mohammad Abdul Ahad is sole owner |

---

### 2.28 Employer-first validation kit prepared ✅

Created the employer-first validation instrument in `validation/` to test employer-side assumptions about anonymised screening, alias-only shortlisting, AI explanation trust, assessment gating, candidate proxy stripping, and tab-switch proctoring. Includes hypotheses register (H-EM-001 to H-EM-005), participant plan, interview guides, WTP module, pre-commitment ladder, decision rules, and ethics guidelines. All thresholds marked PROPOSED. Study not yet run.

---

### 2.36 Update: prd.md PRD release criteria added Phase 3 validation gate

Created the employer-first validation instrument in `validation/` to test employer-side assumptions about anonymised screening, alias-only shortlisting, AI explanation trust, assessment gating, candidate proxy stripping, and tab-switch proctoring. Includes hypotheses register (H-EM-001 to H-EM-005), participant plan, interview guides, WTP module, pre-commitment ladder, decision rules, and ethics guidelines. All thresholds marked PROPOSED. Study not yet run.
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

The `build-and-push` job (gated on `main` only) failed with "Username and
password required" because `DOCKERHUB_USER` and `DOCKERHUB_TOKEN` repository
secrets were not set. Since the project is still in the **documentation phase**
with no image to ship, the entire `build-and-push` job now skips cleanly when
either secret is absent, rather than running the login step and failing the job.

**To enable pushes:** add `DOCKERHUB_USER` and `DOCKERHUB_TOKEN` as repository
secrets (Settings → Secrets and variables → Actions), then the build-and-push
step will run automatically.

---

### 2.36 Interview preparation & training documentation (I1–I5) ✅

Decisions I1–I5 (text-only practice, STAR rubric grading with cited feedback, coaching
data isolation, curated resource links, coaching evaluation set) are now fully documented
across the specification:

- **5 new FRs** (`REQ-FR-058` through `REQ-FR-063`) and **6 new user stories** (`US-071`
  through `US-076`) added to the Arch Doc §4.1 and Feasibility Doc §2.4.
- **5 new tables** in Arch Doc §5.1: `practice_questions`, `interview_coaching_sessions`,
  `scorecard_criteria`, `resources`, `attempt_resource_recommendations`.
- Schema counts are now **32 tables, 51 foreign keys, 25 indexes** (was 27 / 39 / 17). **Superseded 2026-10-12: unchanged (32 tables, 51 FKs, 25 indexes) — no new tables added beyond payments table for D2; §2.31.**
- **63 functional requirements** in the Arch Doc (was 57). **Superseded 2026-10-12: unchanged at 63 FRs (§2.31) — design.md pass added pages/wireframes but no new FRs.**
- **63 user stories / 260 story points**, MoSCoW **37 Must / 21 Should / 5 Could**. **Superseded 2026-10-12: unchanged at 63 stories / 260 points, 37 Must / 21 Should / 5 Could (§2.31) — design.md pass added pages/wireframes but no new stories.**
- Coaching isolation is enforced structurally: `interview_coaching_sessions` has **no FK**
  to `applications` or `jobs`; coaching scores never enter `match_score`, ranking, or
  shortlisting (I3). Acceptance test asserts no coaching table is JOINed to
  `rank_applications()`.
- Resources are reference-only links, never built content; link-health cron, named
  curation owner, 90-day review cadence, and the gap→resource→retake→Verified badge loop
  are all specified (I4).
- `scripts/verify_docs.py` updated: all **63 checks pass**. **Superseded 2026-10-12: now 67 checks (§2.31).** **Superseded 2026-10-13: now 70 checks (§2.37) — added W-number gap detection, ASM-001 count match, and employer-surface name-visibility ban.**

---

### 2.31 Doc-consistency pass (2026-10-12) — PII, pricing, counts, payments ✅

Following the design.md wireframe pass (§2.30), a consistency pass was run to fix regressions left after the 2026-10-05 business and interview revisions:

- **PII stripping expanded.** `REQ-FR-011` amended in the Arch Doc §4.1, `prd.md` §7.1, the Feasibility Doc scenario S-2 and the Complete Doc §C.14. Stripping now covers proxies from `REQ-FR-057` (institution names, employer names, age-revealing dates, URLs, photos). All references marked "amended 2026-10-12".
- **Pricing wording corrected.** Discovery-only visibility wording applied everywhere (was "priority in employer search" / "featured placement"); USD prices marked reference-only/unvalidated; BDT prices marked `[Planned: set after validation]`.
- **Counts updated (current-state only):** 57 → 63 FRs, 24 → 32 tables, 35 → 51 FKs, 52 → 63 stories / 217 → 260 points (MoSCoW 37 Must / 21 Should / 5 Could), 62 → 78 pages, 52 → 64 wireframes. README line 38, the Arch Doc v4.4 header, the Feasibility Doc `ASM-001`, and the HISTORY.md "Key numbers of record" block all updated. Historical log entries left as written with "superseded" notes.
- **Payment provider path.** bKash/SSLCommerz is the current path in BDT; Stripe deferred to Phase 5. README, `prd.md` §8.8 (encrypted-fields row), and the Complete Doc §C.14 all updated.
- **New verifier checks** added to `scripts/verify_docs.py`: stale-count cross-checks, discovery-only pricing wording ban (except in dated notes), REQ-FR-011↔REQ-FR-057 linkage, design.md keyword checks, and wireframe coverage check.

### 2.37 Doc-consistency pass (2026-10-13) — FR count, Verified badge, W36 gap, header ✅

- **FR count corrected.** `ASM-001` in the Feasibility Doc stated "65 requirements" but there are 63 FRs (`REQ-FR-001`–`REQ-FR-063`). Corrected all three references (lines 1051, 2881, 2972) to "63 requirements". Phase 1 test wording updated to "End of Phase 1: a developer who has not touched the codebase reviews every screen."
- **Verified Badge repositioned.** `design.md` §7.16 rewritten so the badge appears next to the candidate ALIAS (REQ-FR-054), never a name or photo. Removed the claim that it appears on the public job board (which lists jobs, not candidates). The badge now appears on the candidate's own profile and in employer candidate search results. Job-board "Verified" markers clarified as company-identity checks.
- **W36 gap explained.** `design.md` now includes a dated note (2026-10-13) explaining that W36 is intentionally unused — reserved for the "candidate self-scheduling" wireframe deferred to Phase 3 per `prd.md` §5.1.
- **HISTORY.md updated.** "Last updated" → 2026-10-13; new §2.37 section added.
- **New verifier checks added** for W-number gap detection, ASM-001 count match, and employer-facing surface name-visibility ban.

---

### 2.38 The stack runs — seven fixes, and four healthchecks that meant nothing (2026-10-16) ✅

The scaffold had never been executed (§1). It has now: built and run cold on Docker 29.8.2
against an empty database, then re-run from a fresh-clone emulation (`cp .env.example .env`,
generated keys, no pre-existing volumes). Seven defects prevented it. Each is fixed at its
cause, and each comment left in the code says *why*.

- **gunicorn ran with no arguments.** `docker-compose.yml` passed its command as a YAML *block
  scalar*: every flag on its own line, nothing continuing the command. The shell therefore ran
  `exec gunicorn config.wsgi:application` **alone**. gunicorn bound its default
  `127.0.0.1:8000`, so `ports: 8000:8000` forwarded to a socket that was not listening, and the
  flag lines never executed because `exec` had already replaced the shell. It failed in the most
  misleading way available: the container was **healthy**, because the image healthcheck curls
  `localhost:8000` *inside* the container, where gunicorn was in fact listening. Every flag now
  ends in a backslash and the entrypoint runs under `set -e`.
- **Nothing collected the static files.** `staticfiles/` is a named volume mounted over an empty
  directory in the image, and `collectstatic` had never run inside the container, so
  `/static/css/tailwind.css` was a 404 and every page rendered unstyled. It is now a step in the
  entrypoint — the only place the volume is visible, which is also why archiving it at image
  build time would not have helped.
- **`SENTRY_DSN` was required by Compose, but only production requires it.** It was
  `${SENTRY_DSN:?…}` while `.env.example` leaves the value empty, so the README's own first
  command — `cp .env.example .env && docker compose up` — died on an interpolation error before a
  single container started. It is now `${SENTRY_DSN:-}`: production asserts the DSN, development
  does not.
- **Celery beat crash-looped forever.** `celerybeat-schedule` defaults to the working directory
  `/app`, which is root-owned while the container runs as the non-root app user. The write raised
  `EACCES`, beat exited 1, and `restart: unless-stopped` restarted it into the same failure — a
  loop that never scheduled a task and that `docker compose ps` showed only as "restarting". The
  service now passes `--schedule=/app/run/celerybeat-schedule` into a `beat_data` volume, and the
  image creates and chowns `/app/run`.
- **The vendored JS was never built.** `/static/js/htmx.min.js` and `/static/js/chart.min.js` are
  gitignored outputs of `npm run build`, but `build` only compiled Tailwind — nothing produced
  them, so they were absent from the image and every `hx-*` interaction silently did nothing.
  `package.json` now has a `vendor` script, `build` runs it before `build:css`, and the Dockerfile
  copies `static/js/` forward from the assets stage (design.md §11.2).
- **`/api/v1/` returned 500.** `ApiRootView` applied `method_decorator(never_cache)` to a plain
  method of a class-based view, which raises `AttributeError` on every request. It now decorates
  `dispatch`.
- **`config.settings.local` ignored the environment.** `ALLOWED_HOSTS` and
  `CSRF_TRUSTED_ORIGINS` were hard-coded there, so editing them in `.env` changed nothing even
  though `.env.example` documents them. Both now read from the environment, with the previous
  literals as defaults.

**Read the healthchecks carefully.** Four of the seven left the container reporting *healthy*:
the published port was dead while the internal probe passed; a static 404 does not fail a probe;
a missing script is a silent no-op; and beat's crash loop was hidden by `restart: unless-stopped`.
A green `docker compose ps` was not evidence the application worked — the only trustworthy check
was to request each endpoint and read the response.

**`README.md` rewritten** as a step-by-step local setup from a fresh clone (six steps, from
`git clone` to `docker compose up -d --wait` and the seed command), with a troubleshooting table.
Build/test/format commands and the "there is no `config/settings/test.py`" rationale moved into
the Development section.

**Verification:** 115 tests pass; `flake8`, `isort`, `mypy`, `verify_docs.py` and
`verify_bias_set.py` clean; cold restart and fresh-clone emulation both reach six healthy
services with zero restarts.

**Documentation brought into line with it:** Arch Doc §6.1 / §6.2 record the Compose and
Dockerfile divergences above; Arch Doc §3.4 no longer lists HTMX `1.18` (a version that does not
exist — §2.30); the Complete Doc §C.7 corrects `SENTRY_DSN` and records that
`config.settings.local` now reads `ALLOWED_HOSTS` / `CSRF_TRUSTED_ORIGINS` from the environment;
design.md §11.2 shows the real `build` script and the corrected HTMX / Chart.js versions; both
canonical docs' `docker compose up -d db` examples are corrected to `postgres`, which is the
service actually declared; and the Feasibility Doc §5 item 4 — "the scaffold is not a running
system" — now records that `manage.py check` and a first `docker compose up` both pass, while
keeping the substance: no model exists, so nothing about the product itself is verified yet.

---

## 3. Gap status

| Gap | Original state | Now |
| --- | --- | --- |
| **A** — Requirement collection method | ❌ blocking | ✅ **closed** — Feasibility §1.3, `prd.md` §3.4, tagged [Done]/[Illustrative]/[Planned] (§2.20). Validation plan stays **[Planned]** until actually run |
| **B** — Real-world problem example | ❌ missing | ✅ **closed** — Amazon 2018 primary + iTutorGroup / HireVue / Mobley + 3 BD sources (§2.20). *Mobley* needs re-verification before public citation |
| **C** — Wireframes | ❌ none at all | ✅ **complete for low fidelity** — 52 wireframes (18 `S` + 5 `X` + 29 `W`) covering **all 62 pages**, including the four screening-integrity components (§2.30). Figma and hi-fi still open. **Superseded 2026-10-12: now 64 wireframes covering all 78 pages (§2.31).** |
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

**State on 2026-10-16:** ✅ **`origin/v3` is in sync with local `v3`.** The local-run fixes
(`0909c23 v3 - updated`, `d4b4ef3 bug fixes`, §2.38) and this documentation pass were pushed
together as `d4b4ef3..c6ebb5c  v3 -> v3`. The first attempt from this environment was rejected
(`No anonymous write access` — no `gh`, no credential helper, no `~/.netrc`, no
`~/.git-credentials`, no `~/.ssh`); after credentials were configured by hand the retry
succeeded. No unpushed commit remains.

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

---

### 2.28 Employer-first validation kit prepared ✅

Created the employer-first validation instrument in `validation/` to test employer-side assumptions about anonymised screening, alias-only shortlisting, AI explanation trust, assessment gating, candidate proxy stripping, and tab-switch proctoring. Includes hypotheses register (H-EM-001 to H-EM-005), participant plan, interview guides, WTP module, pre-commitment ladder, decision rules, and ethics guidelines. All thresholds marked PROPOSED. Study not yet run.

---

### 2.36 Update: prd.md PRD release criteria added Phase 3 validation gate

The validation study plan §1.3.4 was built but never run. Creating an employer-first validation kit to allow the founder to run recruiter interviews and decide go/adjust/stop before Phase 3 is built.

**What was created:**

- `validation/hypotheses.md` — 8 hypotheses (H-EM-001 to H-CAN-003) with evidence needed and disconfirming evidence
- `validation/participant_plan.md` — Recruitment plan for 5–6 recruiters, 3–5 candidates
- `validation/employer_interview_guide.md` — 45-minute interview protocol for recruiters
- `validation/willingness_to_pay.md` — Price sensitivity questionnaire (bdst method)
- `validation/pre_commitment_ask.md` — Ladder of commitments protocol (score ≥ stated interest)
- `validation/candidate_interview_guide.md` — 20-minute candidate protocol
- `validation/evidence_templates.md` — Note template, coding scheme, results table
- `validation/decision_rules.md` — Go/adjust/stop thresholds (PROPOSED, lock date 2026-10-20)
- `validation/ethics_data_handling.md` — Ethics protocol, GDPR principles, synthetic data spec
- `validation/demo_script.md` — Wireframe walkthrough, synthetic resume dataset

**What was updated:**

- README.md: "built, never run" → "kit prepared 2026-10-13, study not yet run"
- prd.md §19: Linked hypotheses to validation kit; marked inferred claims to be validated

**Status:** ✅ Kit is ready. Interviews not yet run. Founder must confirm decision thresholds before 2026-10-20.

**Next steps:**

1. Founder confirms thresholds in decision_rules.md
2. Select target companies for recruitment
3. Begin interviews
4. Update results.md with actual data
5. Retag §1.3.4 activities from [Planned] to [Done] when complete

---

---

### 2.28 Employer-first validation kit prepared ✅

Created the employer-first validation instrument in `validation/` to test employer-side assumptions about anonymised screening, alias-only shortlisting, AI explanation trust, assessment gating, candidate proxy stripping, and tab-switch proctoring. Includes hypotheses register (H-EM-001 to H-EM-005), participant plan, interview guides, WTP module, pre-commitment ladder, decision rules, and ethics guidelines. All thresholds marked PROPOSED. Study not yet run.

---

### 2.36 Update: prd.md PRD release criteria added Phase 3 validation gate

Created the validation instrument at validation/ to test employer-side assumptions about anonymised screening, alias-only shortlisting, AI explanation trust, assessment gating, candidate proxy stripping, and tab-switch proctoring. Includes hypotheses register, participant plan, interview guides, WTP module, pre-commitment ladder, decision rules, and ethics guidelines. All thresholds marked PROPOSED. Study not yet run.

---

## 7. Batch log

### Batch 0.1: Reconcile repo state against HISTORY.md (2026-10-19)

Read-only audit. The only file written is `docs/AUDIT.md` (plus this entry and the progress
lines). No code was changed; nothing was committed.

**What was verified against the code (not from a zip):**

- Branch is `0.0-ready-to-began` (`0335ecb`), one commit ahead of `v3` (`7a7a6d9`). `v3` is
  4 commits ahead of local `main` (`6aaf7aa`) and 0 behind; `origin/main` (`e40f0fc`) already
  contains the `0.0-ready-to-began` work, and this working tree is byte-identical to `origin/main`.
  So the "zip named `main`" matches the current tree, while §1's "current branch is `v3`" is an
  ancestor.
- **Three models exist**, not zero: `accounts.User`, `core.AuditLogEntry`, `core.Skill`, each with
  a migration (`accounts/0001`, `core/0001`). The database holds `users`, `skills`,
  `audit_log_entries`. §1's "no Django model exists" is corrected by this batch (the source text is
  left as written; this entry is the correction).
- Full suite: **115 passed** (`pytest tests/ -q`, `DEBUG` unset); `tests/bias/` alone: **40 passed**.
  With the shell's ambient `DEBUG=True`, 14 `test_production_settings.py` tests fail — an environment
  artefact, not a code failure. Confirms §2.38's count.
- `manage.py check` → no issues; `manage.py makemigrations --check --dry-run` → "No changes detected".
- Endpoints probed inside the running container: `/`, `/api/demo/`, `/health/`, `/health/ready/`,
  `/api/v1/` → 200; the six mounted API prefixes → 401 (empty routers); `/api/v1/jobs/`,
  `/api/v1/gdpr/` and every §C.12 endpoint → 404.

**Commands run** (all from the repo root; see `docs/AUDIT.md` §"How this was verified" for settings
and env): `manage.py check`, `manage.py makemigrations --check --dry-run`,
`docker exec fairfold-postgres-1 psql … "\dt"`, `pytest tests/ -q`, `pytest tests/bias/ -q`,
`scripts/verify_docs.py`, `scripts/verify_bias_set.py`, and `docker exec … curl` over the endpoint list.

**Disagreements recorded** (full detail in `docs/AUDIT.md`): HISTORY's no-model/`v3` claims; the
`employer_admin`↔`employer_manager` role-name split (code vs REQ-FR-047/DDL, and doc-vs-doc);
JWT access 30 min vs REQ-FR-002's 15 min; rotation+blacklist vs REQ-FR-007 (and
`token_blacklist` not installed for REQ-FR-008); `users` field names (`date_joined`, no
`created_at`/`updated_at`/`mfa_secret`); the API index advertising unmounted `jobs`/`gdpr`; and the
un-run `core/tests.py` test.

**Known limitations of this entry.** It is an audit: no acceptance criterion is demonstrated, so no
TRACEABILITY status was promoted to `done`. Live remote sync (`git fetch`/`ls-remote`) was not
attempted — no credentials — so the branch comparison is local-ref-only. Docker and the database were
already running; the stack was not rebuilt cold.

### Batch 0.2: Baseline run and branch sync (2026-10-19)

Documented the repo baseline run with exact commands and real outputs in `docs/BASELINE.md`.
This batch verified the Docker stack, Django checks, migration/seed path, full pytest run,
docs validation, and endpoint probes without changing application code.

**What was verified:**

- `docker compose up -d --wait` → healthy stack on the local Docker environment
- `manage.py check` → no issues
- `manage.py makemigrations --check --dry-run` → no drift
- `manage.py migrate --noinput` against a throwaway DB → OK
- `manage.py seed` → successful seed output
- `pytest tests/ -v` → **115 passed in 2.86s**
- `scripts/verify_docs.py` and `scripts/verify_bias_set.py` → both passed
- `/health/`, `/health/ready/`, `/api/v1/` and related routes returned expected 200 responses

**Commands run:** `docker compose up -d --wait`, `unset DEBUG`, `export DJANGO_SETTINGS_MODULE=config.settings.ci`,
`.venv/bin/python manage.py check`, `.venv/bin/python manage.py makemigrations --check --dry-run`,
`.venv/bin/python manage.py migrate --noinput`, `.venv/bin/python manage.py seed`,
`.venv/bin/pytest tests/ -v`, `.venv/bin/flake8 ...`, `.venv/bin/black --check .`,
`.venv/bin/isort --check-only .`, `.venv/bin/mypy ...`, `.venv/bin/bandit -r . ...`,
`.venv/bin/pip-audit -r requirements.txt`, `.venv/bin/python scripts/verify_docs.py`,
`.venv/bin/python scripts/verify_bias_set.py`.

**Known limitations:** the formatter check and Bandit are environment-specific pre-existing issues:
`black --check .` reports one file would be reformatted, and `bandit` is incompatible with the host
Python 3.14 runtime (`B107` profile error). The batch itself is still a read-only verification pass.

**Git state:** branch `0.2-Baseline-run-passed` was created locally and pushed to `origin` with tracking configured; the remote branch exists and is synced to the current local branch metadata.

### Batch 0.3: Requirements traceability table (2026-10-19)

Rewrote `docs/TRACEABILITY.md` as the batch requires: one row per FR (63 rows, 63 distinct ids) with
priority, phase, owning app, the API route from Complete Doc §C.12, the table from Arch Doc §5.1,
status and evidence path, plus a blank "Planned batch" column. Added an NFR-group table (REQ-SEC 14,
REQ-COM 9, REQ-NFR 23, REQ-NFOR 4 = 50) with phase and verification method, and a section on the
`prd.md` §20 release criteria and the Phase 3 validation gate in `validation/decision_rules.md`. No
requirement text was changed.

**Sources read (not pasted):** Arch Doc §4.1 (FR table + group headings), §4.2 (NFR table), §5.1
(32 CREATE TABLE), §7.2 (test layout), §10 (phase acceptance criteria); Complete Doc §C.12 (API
list); `prd.md` §5.1, §12.3, §20, §21.2; `validation/decision_rules.md`; `docs/ROADMAP.md`.

**Commands run and results:**

- `grep -c 'REQ-FR-0' docs/TRACEABILITY.md` → 63; distinct ids 63; FR rows 63.
- `.venv/bin/python scripts/verify_docs.py` → exit 0, no FAIL (it does not read `docs/TRACEABILITY.md`).

**Known limitations.** No acceptance criterion is demonstrated by a test, so no FR status is `done`
and PROGRESS line 0.3 stays unchecked. Four FRs are `partial` on pre-existing code only
(FR-003, FR-015, FR-030, FR-039). `docs/DECISIONS.md` does not exist yet (it is batch 0.4), so the
D-series items are cited from `docs/ROADMAP.md` instead. Four §C.12 route gaps (apply, offers,
employer dashboard, billing/payments) and the missing coaching-app owner are recorded as gap notes,
not fixed here. Python/`pytest` were not run for this batch: it is a docs change with no code.

### Batch 0.5: Apply the accepted decisions to specs and settings (2026-10-19)

Applied D-2, D-3, D-6(a)–(c) and D-7 — the only decisions accepted in `docs/DECISIONS.md`. Spec-first:
the canonical docs were amended, then the settings/fixtures that must agree. No model, view or UI code
was written, and nothing was committed.

**D-2 — role vocabulary.** Adopt the requirement names. `core/fixtures/groups.json` and
`core/management/commands/seed.py` `ROLES` now say `employer_manager` and protect the last `employer_hr`;
the Complete Doc RBAC row and §C.8.3, `prd.md` §10.1 and `design.md` (members table + last-role warning)
were corrected to match REQ-FR-047. `accounts/models.py` and `employers/__init__.py` still say
`employer_admin`; renaming them is a code change, deferred (see limitations).

**D-3 — email verification.** Added `POST /api/v1/auth/verify-email/` and
`POST /api/v1/auth/verify-email/resend/` (stateless signed token, no new table) to Complete Doc §C.12,
`prd.md` §13 and the FR-001 row of `docs/TRACEABILITY.md`.

**D-6 — §5.1 schema holes.** (a) `candidate_resumes.status` + `processed_at` (REQ-FR-010/012/013);
(b) `applications.screening_status` / `screening_attempts` / `screening_started_at` / `screening_error`
— per-application state, no new table (REQ-FR-028); (c) a new `job_skills` join table with two FKs and
two indexes (REQ-FR-042). The table count moved 32 → 33, FKs 51 → 53, indexes 25 → 27, reconciled in
Arch Doc §5.1/§5.2, Complete Doc §8.2, `prd.md` §11, the Feasibility Doc §3.6–§3.8 and
`scripts/verify_docs.py`.

**D-7 — JWT.** `config/settings/base.py`: access token 30 → 15 minutes, and
`rest_framework_simplejwt.token_blacklist` added to `INSTALLED_APPS`; REQ-FR-007 amended so rotation
invalidates the previous refresh token (matching `prd.md` §10.1).

**Commands run and results:**

- `.venv/bin/python scripts/verify_docs.py` → exit 0, all checks passed (33 tables, 53 FKs, 27 indexes).
- `.venv/bin/python scripts/verify_bias_set.py` → exit 0, 2 versions internally consistent.
- `manage.py check` → "System check identified no issues (0 silenced)."
- `manage.py makemigrations --check --dry-run` → "No changes detected" (the `token_blacklist` app ships its own migrations).
- `.venv/bin/pytest tests/ -q` with `DEBUG` unset → **115 passed**; with the shell's ambient `DEBUG=True`, 14 `test_production_settings.py` tests fail — the same environment artefact recorded in batch 0.1.
- `black --check`, `isort --check-only` and `flake8` on the two changed Python files → clean.

**HISTORY corrections made by this entry.** The documentation-set table line counts (§1) and the
"Key numbers of record" table/FK counts were updated to the post-0.5 files. No other HISTORY entry was
edited.

**Known limitations.** `accounts/models.py:51` `ROLES` and its `has_role("employer_admin")` checks, and
the `employers/__init__.py` comment, still use the old role name, so the specs/fixture now lead the code;
there are no `tests/accounts` yet. This was the agreed scope for this docs-only batch and must be closed
in the code batch that builds the auth service. `docs/AUDIT.md` and `docs/BASELINE.md` are dated snapshots
of the pre-0.5 tree and were left unedited — their "32 tables" describes that state. No acceptance
criterion is demonstrated by a new test, so no TRACEABILITY status is promoted to `done` (FR-002/007 are
`partial`).


### Batch 1.1: User model characterization tests (2026-10-20)

**Entry reconstructed 2026-10-20.** This batch was implemented and committed as `032505f` but appended no
`## 7. Batch log` entry, and `docs/PROGRESS.md` was left unchecked. The text below is written from the
committed code plus a fresh re-run of its tests, not from a contemporaneous record.

**What changed.**

- `tests/accounts/test_user_model.py` (new, 29 tests) — pins `create_user`/`create_superuser` (email
  lower-casing, unusable password when none is given, active/staff/superuser defaults, empty email
  refused, explicit false superuser flags refused), duplicate email including a different case,
  `is_locked()` for `None`/future/past/exact-boundary/in-memory values, `has_role` and the
  `is_candidate`/`is_employer`/`is_employer_admin` properties, `__str__` returning the email and never
  the names, the UUID primary key and `USERNAME_FIELD`/`db_table`, `ROLES` against
  `core/fixtures/groups.json`, and the documented direct-`create()` bypass (no lower-casing; two rows
  differing only in case can coexist).
- `accounts/models.py` — **bug fixed and reported separately:** `ROLES` and the role properties still
  used the pre-D-2 name `employer_admin`, while the fixture already held `employer_manager` (the drift
  recorded in batch 0.5). The new fixture-comparison test fails against that pair; the commit changed
  `ROLES`, `is_employer` and `is_employer_admin` to `employer_manager`. No column or table change, so
  there is no migration.

**Commands run (2026-10-20 re-run; `DEBUG` unset, `config.settings.ci`).**

- `.venv/bin/pytest tests/accounts/test_user_model.py -q` → **29 passed**.
- `.venv/bin/python manage.py check` → "System check identified no issues (0 silenced)."
- `.venv/bin/python manage.py makemigrations --check --dry-run` → "No changes detected".

**Known limitations.** The direct-`create()` case-sensitivity test documents a wart rather than fixing
it: `email` is `unique=True`, and PostgreSQL compares that index case-sensitively, so only the
manager's lower-casing prevents duplicate addresses. A case-insensitive database constraint would be a
schema/spec decision and was not taken here. `first_name`/`last_name` remain plain `CharField`s although
the DDL marks them ENCRYPTED, and the DDL's `mfa_secret`, `created_at` and `updated_at` are not modelled
(pre-existing; recorded in `accounts/models.py`).


### Batch 1.2: Role helpers, permission classes, role-exclusivity (2026-10-20)

Implemented the role layer on top of the batch 1.1 characterization tests. Nothing was committed.

**What changed.**

- `accounts/models.py` — the four role names are now named constants (`CANDIDATE_ROLE`,
  `EMPLOYER_HR_ROLE`, `EMPLOYER_MANAGER_ROLE`, `INTERVIEWER_ROLE`); `ROLES` is built from them and the
  `is_candidate`/`is_employer`/`is_employer_admin` properties no longer spell role strings inline.
  `is_employer_admin` keeps its pre-D-2 name but checks the requirement's `employer_manager` group.
  `EMPLOYER_ROLES` (hr + manager) is the employer side of REQ-FR-045; `interviewer` is deliberately not
  in it, because REQ-FR-045 forbids only the candidate/employer conflict.
- `accounts/services.py` (new) — `assign_role(user, role)` adds a seeded group and refuses a role that
  would leave the user holding both the candidate and employer sides (REQ-FR-045). Unknown roles raise
  `ValueError`; conflicts raise `RoleConflictError` (a `ValueError`). The group is fetched with
  `get()`, never `get_or_create()`, so a typo cannot create a fifth role. The check and insert run in
  one transaction with `select_for_update()` on the user row, so two concurrent assignments cannot
  both pass the check. The error message names groups, never the person.
- `accounts/permissions.py` (new) — `IsCandidate`, `IsEmployer`, `IsEmployerAdmin`, `IsPlatformAdmin`.
  Role classes delegate to the model's `is_*` properties; `IsPlatformAdmin` checks `is_staff or
  is_superuser` (D-2: `admin` is a flag, not a group). All four deny anonymous and inactive users.
  They read group membership rather than `has_perm` because the seeded groups carry no permission
  codenames; inventing one would be a spec change.
- `tests/accounts/conftest.py`, `tests/accounts/test_role_assignment.py`,
  `tests/accounts/test_permissions.py` (new) — every role is asserted against every permission class
  (16 cases, plus a meta-test that the matrix has no missing combination); the four conflicting pairs
  are asserted in both directions with the database re-read after the refusal; seeded-group tests load
  `core/fixtures/groups.json` rather than creating groups themselves.

**Commands run and results.**

- `pytest tests/accounts/test_user_model.py -q` (prerequisite 1.1) → **29 passed**.
- `pytest tests/accounts/ -q` → **84 passed**.
- `pytest tests/ -q` with `DEBUG` unset → **199 passed**.
- `manage.py check` → "System check identified no issues (0 silenced)."
- `manage.py makemigrations --check --dry-run` → "No changes detected" (with the usual `fairfold_test`
  does-not-exist RuntimeWarning from the migration-history probe; no model change).
- `flake8 accounts/ tests/accounts/ --max-line-length=120 --extend-exclude='*/migrations/*'` → exit 0.
- `black --check accounts/ tests/accounts/` → clean after one reformat of `test_permissions.py`;
  `isort --check-only accounts/ tests/accounts/` → clean.
- `mypy accounts/ tests/accounts/ --ignore-missing-imports` → "Success: no issues found in 16 source files".
- `scripts/verify_docs.py` → all checks passed; `scripts/verify_bias_set.py` → 2 versions consistent.
- `bandit -r accounts/ -c bandit.yaml ...` → **exit 2**, "[main] ERROR Unknown test found in profile:
  B105". This is the pre-existing `bandit.yaml` / installed-bandit incompatibility recorded in batch
  0.2, not caused by this batch; bandit could not be run.
- `black --check .` still reports `scripts/verify_docs.py` would be reformatted — pre-existing, untouched.

**Docs.** `docs/PROGRESS.md` line 1.2 is marked `(pending my test output)` — the tests above passed
locally, but the batch is not marked `[x]` until the maintainer pastes their own run.
`docs/TRACEABILITY.md`: REQ-FR-038 and REQ-FR-045 moved from `not started` to `partial`, with the
missing acceptance criteria named in the evidence cell.

**Known limitations.** There is no test for the concurrent-assignment race (the row lock is reasoned,
not exercised); the `interviewer` exemption from REQ-FR-045 is an interpretation that should be
confirmed; the permission classes are not wired to any view yet (out of scope); `employers/__init__.py`
still says "last-`employer_admin`" and `core/management/commands/seed.py` keeps its own `ROLES` copy,
both noted as observations rather than changed here. `docs/PROGRESS.md` line 1.1 also remains
unchecked even though `tests/accounts/test_user_model.py` passes (29 tests); its tracking was not
updated by that batch.

### Batch 1.3: Registration service (2026-10-20)

**Entry reconstructed 2026-10-20.** This batch was committed as `1044225` but appended no
`## 7. Batch log` entry, and `docs/PROGRESS.md` was left unchecked. The text below is written from the
committed code plus a fresh re-run of its tests, not from a contemporaneous record.

**What changed.**

- `accounts/services.py` — `register_user(email, password, first_name, last_name, role)` (REQ-FR-001).
  It normalises the address exactly as `UserManager` stores it (strip, lowercase the whole address),
  validates it with `validate_email`, runs every `AUTH_PASSWORD_VALIDATORS` entry with a provisional
  user so the name/email-similarity rule applies, and creates the account with
  `User.objects.create_user` so the password is hashed and `email_verified` stays `False`.
  `SELF_ASSIGNABLE_ROLES = ("candidate", "employer_hr")` is the signup split from design.md page 6;
  `employer_manager` is a later promotion and `interviewer` an invitation (REQ-FR-047), so both raise
  `RoleNotSelfAssignableError`. The user, the `assign_role` membership and one `AuditLogEntry`
  (`action="user_registered"`, `details={"role": role}`) are written in one transaction, so a missing
  seeded group or failed audit insert leaves no half-created account. A duplicate address returns
  `None` instead of raising, so the future API can answer identically to success and avoid becoming an
  account-enumeration oracle; an `IntegrityError` from the unique index is absorbed only when the
  address is confirmed taken.
- `config/settings/base.py` — `PASSWORD_HASHERS` pinned explicitly with
  `Argon2PasswordHasher` first (REQ-SEC-001). `ci.py`/`local.py` override it with MD5 for speed, so the
  pin is asserted against `config.settings.base` directly.
- `accounts/models.py` — comment corrected from `settings.AUTH_PASSWORD_HASHERS` to
  `settings.PASSWORD_HASHERS`; no behaviour change.
- `tests/accounts/test_registration.py` (new, 34 tests) — success for both self-assignable roles;
  unverified account; hashed password; email strip/lower-case; malformed/missing email; duplicate
  (including different case and a duplicate that appears after the pre-check); weak, numeric, common
  and name-similar passwords; empty password; forbidden roles (`employer_manager`, `interviewer`,
  `admin`, the form label `employer`, empty, wrong case); transaction rollback on a failed role
  assignment and on a missing seeded group; exactly one audit entry that holds no email or name.
- `tests/accounts/test_password_hashing.py` (new, 3 tests) — base settings try Argon2 first, the
  hasher is Argon2**id** (`argon2.low_level.Type.ID`), and CI keeps its MD5 override.

**Commands run (2026-10-20 re-run; `DEBUG` unset, `config.settings.ci`).**

- `.venv/bin/pytest tests/accounts/test_registration.py -q` → **34 passed**.
- `.venv/bin/pytest tests/accounts/test_password_hashing.py -q` → **3 passed**.
- `.venv/bin/python manage.py check` → "System check identified no issues (0 silenced)."
- `.venv/bin/python manage.py makemigrations --check --dry-run` → "No changes detected".

**Known limitations.** The HTTP endpoint, forms and verification email are out of scope for this batch;
the views that call `register_user` and queue the email landed in 1.5/1.6. The audit entry records the
role only — consent is required by the form but not stored (Arch Doc §5.1 has no column). Email
uniqueness is still enforced only by the manager's lower-casing plus a case-sensitive unique index (see
batch 1.1). The similarity validator's provisional user is never saved, which is intentional but means
an update path must repeat the check.


### Batch 1.4: Email verification tokens and email task (2026-10-20)

Implemented the stateless verification token, the sending task and the resend throttle. No endpoints
or templates (out of scope). Nothing was committed.

**What changed.**

- `accounts/services.py` — new verification section (REQ-FR-001, decision D-3). `make_verification_token`
  signs `urlsafe_base64(<user id>)` with `django.core.signing.TimestampSigner` under the dedicated salt
  `accounts.email_verification`; the token therefore carries a timestamp and an HMAC, and the literal
  user id is not readable in the link. `verify_email(token)` unsigns with
  `settings.EMAIL_VERIFICATION_TOKEN_MAX_AGE_SECONDS`, decodes the id, then flips `email_verified` under
  `select_for_update()` inside one transaction. Expired tokens raise `VerificationTokenExpired`,
  tampered/malformed/unknown-account tokens raise `InvalidVerificationToken`, and a second use (or a
  fresh token for an already-verified account) raises `EmailAlreadyVerified`; all three are
  `ValueError` subclasses and their messages never contain the token, id or email. `queue_verification_email`
  starts the per-user cooldown and dispatches through `transaction.on_commit`, so a worker cannot run
  before the user row commits. `resend_verification_email` is throttled with `cache.add` on
  `email-verification:resend:<user id>`, which is atomic in Redis; the key is written before dispatch so
  a provider outage does not become a retry loop.
- `accounts/tasks.py` — `send_verification_email(user_id)` (`@shared_task(ignore_result=True)`) looks the
  account up by id, skips missing/malformed/verified/inactive accounts, generates a fresh token at send
  time, URL-quotes it into `settings.EMAIL_VERIFICATION_URL`, and sends one plain-text email through the
  configured backend. It takes an id, not an address, so the broker payload holds no PII; it returns
  nothing so the token cannot leak into a Celery result.
- `config/settings/base.py` — `EMAIL_VERIFICATION_URL` (placeholder `http://localhost:8000/verify-email/`
  until the batch 1.6 route exists), `EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS` (45, from design.md X02
  "available in 0:45") and `EMAIL_VERIFICATION_TOKEN_MAX_AGE_SECONDS` (24 h default; REQ-FR-001 does not
  state a lifetime). No `CREATE TABLE` change: D-3 chose the stateless token, so the 33-table DDL is
  untouched and there is no migration.
- `.env.example` — the three new variables, documented.
- `tests/accounts/test_email_verification.py` (new, 26 tests) — valid token; literal-id-is-not-a-token;
  second use; fresh token for a verified account; expired (signing clock patched, not slept); tampered;
  malformed/empty; deleted account; one email in `mailoutbox` with a working link; no email for verified,
  inactive, malformed-id or unknown-id; first resend; in-cooldown resend; cooldown expiry; per-user
  isolation; verified account; signup starts the cooldown; resend reaches the outbox; dispatch is
  deferred to `transaction.on_commit`. The resend class uses `django_db(transaction=True)` because the
  default TestCase wrapping never commits and `on_commit` would never run.

**Commands run and results.**

- `pytest tests/accounts/test_email_verification.py -q` → **26 passed**.
- `pytest tests/accounts/ -q` → **147 passed**.
- `pytest tests/ -q` with `DEBUG` unset → **262 passed**.
- `manage.py check` → "System check identified no issues (0 silenced)."
- `manage.py makemigrations --check --dry-run` → "No changes detected" (same pre-existing
  `fairfold_test` does-not-exist RuntimeWarning as batch 1.2; no model change).
- `flake8 accounts/ tests/accounts/ config/ --max-line-length=120 --extend-exclude='*/migrations/*'`
  → exit 0.
- `black --check accounts/ tests/accounts/ config/settings/base.py` → clean;
  `isort --check-only ...` → clean (3 files skipped by project config).
- `mypy accounts/ --ignore-missing-imports` → "Success: no issues found in 12 source files".
- First full run without unsetting the ambient `DEBUG=True` produced 14 failures in
  `tests/core/test_production_settings.py` (production settings correctly refused `DEBUG=True`). That is
  the environment warning from AGENTS.md, not a code failure; rerunning with `DEBUG` unset gave 262 passed.

**Docs.** `docs/PROGRESS.md` line 1.4 is `(pending my test output)` — not `[x]` until the maintainer
pastes their own run. `docs/TRACEABILITY.md`: REQ-FR-001 moved `not started` → `partial`, REQ-FR-002
stays `partial` with the new verification evidence; the missing endpoints/UI/login are named in the cells.
One older HISTORY line was edited to correct a fact: the file table near the top now says
`.env.example` is 168 lines (was 159), because this batch added nine lines and `verify_docs.py` asserts
that count.

**Known limitations.** The token lifetime (24 h) and the verification page path are not stated in the
docs; both are settings with defaults that should be confirmed before batch 1.6. `queue_verification_email`
is not called from `register_user` yet — batch 1.5 wires it, and if the broker is down the non-robust
`on_commit` callback will raise after the account is committed. There is no test for two concurrent
verifications (the row lock is reasoned, not exercised) and no test that a real worker consumes the task
from Redis (Celery is deliberately not eager in CI). `config/settings/production.py` still never sets
`EMAIL_BACKEND` to an anymail backend, so production would inherit the console backend even though
`EMAIL_BACKEND_URL` is required; pre-existing, out of scope, recorded as an observation.


### Batch 1.5: Registration and verification API (2026-10-20)

Implemented the three documented auth endpoints on top of the 1.3/1.4 services:
`POST /api/v1/auth/register/`, `POST /api/v1/auth/verify-email/` and
`POST /api/v1/auth/verify-email/resend/` (Complete Doc §C.12, decision D-3).
No model or migration change; 33 tables / 53 FKs / 27 indexes unchanged. Nothing
was committed.

**Spec amendments came first.** The batch could not be written against the docs as
they stood, and five points were put to the maintainer, who answered "do the
recommended thing" on each:

* **Names were missing from the registration form.** `users.first_name` /
  `last_name` are `NOT NULL` in §5.1 and `register_user` requires them, but design
  page #6/S01 and §C.12 listed only email/password/role. Chosen: the API requires
  both names and the pages gain the two fields. Amended
  `FAIRFOLD_Project_Architecture_and_Requirements.md` REQ-FR-001, Complete Doc
  §C.12, `prd.md` §7.1 and `design.md` page #6 + the S01 wireframe (and the S01
  `autocomplete` note). `design.md` grew by four lines, so the file-length row in
  this file's documentation table was corrected 2914 → 2918.
* **Role values on the wire** are the group names `candidate` and `employer_hr`
  (`SELF_ASSIGNABLE_ROLES`), not the page labels "Looking for work"/"Hiring". The
  UI maps its labels; the API does not invent an alias.
* **Resend is anonymous** and takes `{"email": ...}`, always 202 with one generic
  body — the caller is on page #11 with no session and no credential.
* **Throttle rates** are the documented unauthenticated rate, 100/hour per IP
  (Complete Doc §5.5, amended to name the two scopes). No new number was invented;
  `THROTTLE_REGISTER` / `THROTTLE_VERIFY_EMAIL` override it. The per-account
  45-second resend cooldown remains the finer limit.
* **400s carry a `code`** (`token_expired` / `invalid_token`) so page #11 can show
  the expired state instead of "link invalid". DRF drops an exception's code, so
  the view returns the body explicitly; `core.exceptions` is unchanged.

**What changed.**

* `accounts/serializers.py` (new) — `RegisterSerializer` (email, first/last name,
  password, role), `VerifyEmailSerializer`, `ResendVerificationEmailSerializer`,
  and the response serializers the schema needs. `NormalisedEmailField` lowercases
  the whole address exactly as `users.email` is stored, so the response echoes the
  stored value and the resend lookup matches it. The password is validated with
  the same `validate_password` and the same provisional user the service builds,
  only so a weak password is a 400 keyed to `password`; `register_user` still
  validates again and remains the authority. `password` keeps whitespace
  (`trim_whitespace=False`); DRF's default would hash a different string from the
  one the client typed.
* `accounts/api_views.py` (new) — three `APIView`s with `permission_classes = []`
  and `authentication_classes = []` (the global default is `IsAuthenticated`; no
  auth class also means no CSRF, which is right for a route with no ambient
  authority). Register calls `register_user` explicitly rather than through
  `serializer.save()`: DRF 3.17 asserts a non-`None` instance and the service
  returns `None` for a duplicate, which is the anti-enumeration contract. The view
  returns the identical 201 body on both paths and queues the email only when an
  account was created. Verify maps the three service outcomes (expired /
  invalid / already verified → 200). Resend discards the service boolean and
  answers 202 for every outcome.
* `accounts/auth_urls.py` (new), `api/urls.py` — the `auth/` prefix from §C.12
  (`accounts.api_urls` stays at `accounts/`; one module mounted twice would expose
  every route twice). The API index now lists `"auth": "/api/v1/auth/"`.
* `config/settings/base.py` — the `register` and `verify_email` throttle scopes.
* `tests/accounts/test_auth_api.py` (new, 42 tests) — 201 + unverified account +
  role + audit entry with no PII; one dispatch per signup, by id; duplicate
  status/body equality, no second email, existing account untouched; 400s for
  every missing field, malformed email, weak password, whitespace-only name and
  non-self-assignable role; password not trimmed; anonymous access for all three
  views; verify success, second use, expired (`token_expired`), tampered and
  deleted-account (`invalid_token`), missing token; resend known/unknown/cooldown/
  verified/normalised address; throttling (201,201,429 and 400,400,429) and the
  shared error shape; schema generation with the three paths, the register field
  set, `writeOnly` password and the role enum.

**Commands run in this environment** (PostgreSQL/Redis from Compose, `DEBUG`
unset, `config.settings.ci`; the maintainer accepted this run without a separate
paste — see the acceptance note under batch 1.6):

* `.venv/bin/pytest tests/accounts/test_auth_api.py -q` → **42 passed**.
* `.venv/bin/pytest tests/accounts/ -q` → **189 passed**.
* `.venv/bin/pytest tests/ -q` → **304 passed**.
* `manage.py check` → "System check identified no issues (0 silenced)."
* `manage.py makemigrations --check --dry-run` → "No changes detected" (the
  pre-existing `fairfold_test`-does-not-exist RuntimeWarning remains; no model
  change).
* `flake8 accounts/ tests/accounts/ config/ api/ --max-line-length=120
  --extend-exclude='*/migrations/*'` → exit 0; `black --check` → 28 files
  unchanged; `isort --check-only` → skipped 3, otherwise clean; `mypy accounts/
  --ignore-missing-imports` → "Success: no issues found in 15 source files".
* `python scripts/verify_docs.py` → exit 0 (76 checks pass);
  `python scripts/verify_bias_set.py` → "All 2 version(s) internally consistent."
* `bandit` → **could not run**: bandit 1.7.10 on Python 3.14 reports "Exception
  occurred when executing tests against …" for every file, including untouched
  ones (`core/models.py`), and rejects the documented skip list with "Unknown test
  found in profile: B105". Pre-existing environment/tooling fault, not caused by
  this batch.

**Docs.** `docs/PROGRESS.md` 1.5 is `(pending my test output)`. `docs/TRACEABILITY.md`
REQ-FR-001 stays `partial`: the endpoints and the registration→`queue_verification_email`
path are implemented and tested, but the status does not move to `done` until the
maintainer pastes their own passing output (rule 9); the page belongs to 1.6 and is
not one of the FR's acceptance criteria. One older HISTORY line was edited to
correct a fact: the documentation table's `design.md` length, 2914 → 2918, because
this batch added the two name fields to the S01 wireframe.

**Known limitations.**

* No CSRF token is required on the three routes (no auth class). That is correct
  for cookie-less anonymous calls; if these endpoints ever accept a session, they
  must be moved behind `SessionAuthentication`.
* The duplicate path returns earlier than the create path (no password hashing),
  so response time can reveal that an address exists even though the body cannot.
  Not addressed; the service's design notes already accept the body-level
  guarantee only.
* If the cache or broker is down, registration commits the account and then 500s
  in `queue_verification_email`; a retry returns the duplicate 201 without an
  email. The resend endpoint is the recovery path. `on_commit` dispatch is not
  retried.
* `/api/schema/` is still mounted only with `DEBUG` on (`config/urls.py`), so the
  schema test calls `SchemaGenerator` directly rather than taking the URL out of
  the settings production shares.
* No test for two concurrent verifications or two concurrent registrations of the
  same address; both are reasoned (row lock, unique constraint) but not exercised.
* `THROTTLE_REGISTER` / `THROTTLE_VERIFY_EMAIL` are not in `.env.example` or
  Complete Doc §C.7, matching the existing `THROTTLE_LOGIN`/`THROTTLE_SCREENING`
  precedent; they are settings-only overrides.

**Observations (out of scope).**

* `verify_docs.py`'s "Verified/Promoted beside name" check is a same-line regex; it
  matched REQ-FR-001 only because the line contained both "unverified" and "first
  name". The wording was changed to "**Given** no account" to keep the check's
  intent (no identity marker beside a candidate name on employer surfaces) without
  weakening the requirement. The check itself should be tightened.
* The documentation-table rows in this file start with `||`, so the line-count
  check skips them (only two claims were checked in this run). The `design.md`
  number was corrected by hand rather than by the checker.
* `.env.example` still documents a `test` settings module; AGENTS.md states there
  is no `config/settings/test.py`.
* `docs/PROGRESS.md` 1.4 is still `(pending my test output)` although the batch is
  committed; left as the maintainer left it.

### Batch 1.6: Registration and verification UI (2026-10-20)

Built design.md §10 page #6 (register, S01) and page #11 (pending, success,
expired, invalid — X02) on top of the 1.3–1.5 services. No model or migration
change; 33 tables / 53 FKs / 27 indexes unchanged. Nothing was committed. No
requirement, column, API endpoint or role was added.

**Routes.** The canonical docs do not fix page URLs, so they are recorded here:
`/register/`, `/register/check-email/`, `/verify-email/` and
`/verify-email/resend/`, mounted at the site root from the new
`accounts/public_urls.py`. `/verify-email/` is not a preference: it is the value
`EMAIL_VERIFICATION_URL` already had, and `accounts.tasks.verification_link`
builds the mailed link from it.

**What changed.**

* `accounts/forms.py` (new) — `RegistrationForm`, the page's shape of the same
  rules as `RegisterSerializer`: role (`candidate` / `employer_hr` values, the
  page's "Looking for work" / "Hiring" labels), first and last name, email,
  password, required consent. It normalises the address identically and runs the
  same `validate_password` with the same provisional user, so a password the form
  accepts cannot be refused by the service. `consent` is required and **not
  stored** — Arch Doc §5.1 has no column for it (REQ-COM-004 asks for the
  checkbox; recording the acceptance needs a schema decision).
* `accounts/views.py` (new) — four views. `register` calls `register_user`
  directly (not the JSON API: a no-JavaScript form POST cannot consume a JSON
  body), queues the email only when a user was created, and answers a duplicate
  with the same redirect and the same pending page. `check_email` reads the
  address from the session (never a URL or hidden field) and masks it as
  `a***@example.com`. `verify_email_page` consumes `?token=` on GET and renders
  success (200), expired (400) or invalid (400). `resend_verification` is POST
  only, reads the session address, and answers with one generic sentence for a
  known address, an unknown one, a verified account and a request inside the
  cooldown. Every page is `@never_cache`; the verification response also sets
  `Cache-Control: no-store` and `Referrer-Policy: no-referrer`, and the token is
  never echoed into the body.
* `accounts/public_urls.py` (new), `config/urls.py` — `app_name =
  "accounts_public"`, one include at the root. Keeping it separate from
  `accounts/auth_urls.py` (JSON, `/api/v1/auth/`) and `accounts/api_urls.py`
  (mounted at `/accounts/`) avoids exposing one route under three prefixes.
* `config/settings/base.py` — added `django_htmx.middleware.HtmxMiddleware`.
  The dependency was already installed but unused; the views use `request.htmx`
  to decide between a panel swap and a normal redirect.
* `templates/accounts/` (new) — `register.html` (page #6), `_register_panel.html`
  (the HTMX target: error summary with `role="alert"` and `tabindex="-1"`, the
  form, and the password show/hide enhancement), `_field.html` (label, help text,
  control, always-present error paragraph so the static `aria-describedby` points
  at a real element), `check_email.html`, `_resend_panel.html` (plain POST plus a
  JS countdown; no hidden address) and `verify_email.html` (the three X02 states).
  The forms work with JavaScript disabled: the HTMX attributes are additive and
  `novalidate` makes the server-rendered summary the single set of error copy.
* `tests/accounts/test_registration_ui.py` (new, 59 tests) — page rendering and
  base-template use; successful registration (unverified account, one dispatch
  by id, session address, normalised email, both roles); duplicate
  status/destination equality and no second email; every invalid field
  (consent, password, name, email, role) re-renders the summary with a link to
  the field; CSRF enforcement; password never echoed; HTMX panel-vs-redirect
  behaviour; pending page masking and no full address in the page source; no
  session → signup; valid token, second use, tampered, expired and missing token;
  cache/referrer headers; session clearing on success; resend from a plain POST
  and HTMX, outside/inside the cooldown, unknown address, verified account,
  no session, GET → 405; `mask_email` edge cases; and no duplicate element ids on
  the register (clean and with errors), pending and verification states — the
  guard for a multi-line `{# … #}` being rendered as HTML, which happened in this
  batch before it was caught.

**Decisions taken without a doc amendment.** These are implementation choices,
not requirement changes, and are listed so they can be reversed explicitly:

* the resend page action is session-scoped rather than address-typed, so the
  pending page never prints the full address in its source;
* the displayed cooldown is set for a duplicate registration too, so the pending
  page cannot reveal that an address already existed;
* no "Have an account? Log in" link on page #6 yet — there is no login route
  until batch 1.7, and a link to a 404 is worse than its absence;
* verification happens on GET, because the emailed artifact is a link.

**Commands run in this environment** (PostgreSQL/Redis from Compose, `DEBUG`
unset, `config.settings.ci`; the maintainer accepted this run without a separate
paste — see the acceptance note under batch 1.6):

* `.venv/bin/pytest tests/accounts/test_registration_ui.py -q` → 59 passed.
* `.venv/bin/pytest tests/accounts/ -q` → 248 passed.
* `.venv/bin/pytest tests/ -q` → 363 passed.
* `.venv/bin/python manage.py check` → no issues.
* `.venv/bin/python manage.py makemigrations --check --dry-run` → "No changes
  detected" (plus the usual warning that the dropped `fairfold_test` database
  cannot be checked).
* flake8 (repo command), `black --check accounts/ config/ tests/accounts/`,
  `isort --check-only` on the same paths, `mypy … --ignore-missing-imports` →
  clean.
* `.venv/bin/python scripts/verify_docs.py` → exit 0.
* Not run: `black --check .` (fails on the pre-existing
  `scripts/verify_docs.py` formatting, untouched here), `bandit` (known broken
  under Python 3.14), `npm run build` (no `node_modules`; the built CSS and
  vendored htmx are gitignored), and any real browser or axe-core pass.

**Known limitations.**

* Without `npm install && npm run build`, `static/css/tailwind.css` and
  `static/js/htmx.min.js` do not exist: the pages render unstyled and the HTMX
  enhancement is inert. The no-JavaScript path still works, which is what the
  markup is built around.
* The expired/invalid resend action needs the address in the session. In a fresh
  browser (the link opened on a phone, say) the page falls back to "Create your
  account" instead of X02's "Send a new link". Adding an email field to that
  state, or a GET resend page, is the fix; it was not in this batch.
* Re-registering an existing unverified address sends no email (the 1.3
  anti-enumeration rule). The recovery is the pending page's Resend button, so the
  expired-in-another-browser fallback takes two steps.
* Verification on GET can be consumed by a link prefetcher (Outlook Safe Links,
  some mail scanners) before the user clicks. The worst case is an account marked
  verified without the click; the user still sees success. A confirm-then-POST
  step would prevent it, and design.md has no such state.
* Consent is required but not recorded; there is no column.
* `/privacy/` and `/terms/` are linked from the consent line and the footer but
  still 404 (the footer did this before this batch).
* `static/img/favicon.svg` does not exist, so every page requests a missing
  favicon (pre-existing).
* No browser, 360px-viewport or axe-core check was run here; those are manual.

**Observations (out of scope).**

* `black --check .` already failed on `scripts/verify_docs.py` before this batch;
  `git status` confirms the file was not touched.
* `templates/home.html` uses `text-body-lg` and `bg-primary-2`, which
  `tailwind.config.js` does not define — pre-existing, unrelated to these pages.
* The base template's "override at most two blocks" rule is respected:
  `register.html`, `check_email.html` and `verify_email.html` override `title`
  and `content` only.

**Acceptance (2026-10-20).** The maintainer instructed that batches 1.5 and 1.6 be
marked complete without a separate pasted test run, waiving rule 9 for these two.
`docs/PROGRESS.md` 1.5 and 1.6 were set to `[x]` and `docs/TRACEABILITY.md`
REQ-FR-001 to `done` on the strength of the run recorded above: 101 passed across
`test_auth_api.py` + `test_registration_ui.py`, 363 passed for the full suite,
`check` clean, `makemigrations --check` no changes, flake8/black/isort/mypy clean
and `verify_docs.py` exit 0. Nothing was committed. The two "evidence of record"
parentheticals above were corrected to record this waiver instead of implying a
maintainer paste that did not happen.

### Batch 1.1-1.4: tracking reconciliation (2026-10-20)

Documentation-only pass. The code and tests for batches 1.1-1.4 were already implemented and committed
(`032505f`, `613f0eb`, `1044225`, `1a0ced9`); what was missing was the bookkeeping, not the work. The
maintainer instructed that the four batches be checked and marked complete in `docs/PROGRESS.md`.

**What changed.**

- `docs/PROGRESS.md` — 1.1-1.4 changed from `[ ]` (1.2/1.4 still said "pending my test output") to
  `[x]`, each with the date and its targeted test count.
- `HISTORY.md` — added the missing `Batch 1.1` and `Batch 1.3` entries above. Both are explicitly marked
  as reconstructed from the commits and a fresh test run, because the batches wrote no entry at the
  time. This entry records the reconciliation itself.
- `docs/TRACEABILITY.md` — evidence cells for REQ-FR-003, REQ-FR-038 and REQ-FR-045 now name the tests
  that demonstrate the implemented part. No status was invented: REQ-FR-003, REQ-FR-038 and REQ-FR-045
  stay `partial` because their remaining acceptance criteria (5-attempt lockout/login service, admin
  user management, `EmployerProfile` onboarding and activation guard) are still unbuilt. REQ-FR-001 was
  already `done` from batches 1.3-1.6.
- No Python, template, fixture, migration or settings file was touched.

**Commands run** (`DEBUG` unset, PostgreSQL/Redis from Compose, `config.settings.ci`).

- `.venv/bin/pytest tests/accounts/test_user_model.py tests/accounts/test_role_assignment.py tests/accounts/test_permissions.py tests/accounts/test_registration.py tests/accounts/test_email_verification.py tests/accounts/test_password_hashing.py -q` → **147 passed**.
- Per file: `test_user_model.py` 29, `test_role_assignment.py` 19, `test_permissions.py` 36,
  `test_registration.py` 34, `test_email_verification.py` 26, `test_password_hashing.py` 3.
- `.venv/bin/pytest tests/ -q` → **363 passed**, 16 pre-existing drf-spectacular deprecation warnings.
- `.venv/bin/python manage.py check` → "System check identified no issues (0 silenced)."
- `.venv/bin/python manage.py makemigrations --check --dry-run` → "No changes detected" (plus the
  pre-existing `fairfold_test`-does-not-exist RuntimeWarning from the migration-history probe).
- `.venv/bin/flake8 accounts/ tests/accounts/ --max-line-length=120 --extend-exclude='*/migrations/*'`
  → exit 0; `black --check accounts/ tests/accounts/` → 25 files unchanged; `isort --check-only` on the
  same paths → no errors (3 files skipped by project config).
- `.venv/bin/python scripts/verify_docs.py` → exit 0 (33 tables, 53 FKs, 27 indexes asserted).

**Acceptance.** The maintainer waived rule 9 for this reconciliation exactly as for batches 1.5/1.6,
instructing that the batches be marked complete without a separate pasted run. The `[x]` marks rest on
the run recorded above, which the agent executed in this repository. Nothing was committed or pushed.

**Known limitations / open items.**

- The permission classes in `accounts/permissions.py` decide on group membership through the `is_*`
  model properties, not `has_perm`, because `core/fixtures/groups.json` seeds the groups with
  `"permissions": []` and the docs define roles without permission codenames. Adding codenames would be
  a spec change and needs a decision before any `has_perm`-based check is introduced.
- `config/settings/production.py` validates `EMAIL_BACKEND_URL` and sets `ANYMAIL`, but never sets
  `EMAIL_BACKEND` to an `anymail.backends.*` class, so production still inherits the console backend
  from `base.py`. Which ESP backend to pin (the stored URL has no scheme that identifies a provider) is
  a decision, so it was not guessed here. Recorded as an observation, not fixed.
- The concurrent-write races in `assign_role` and `verify_email` are guarded with
  `select_for_update()` but not exercised by a concurrency test.
- `tests/accounts/test_user_model.py` pins the case-sensitive unique index as a known wart; changing it
  is a schema decision.


### Batch 1.7: Login service with lockout (2026-10-20)

**What changed.** `accounts/services.py` gained `authenticate_with_lockout`, the single
credential check used by both the JSON API and the template login (D-1). It
implements REQ-FR-003: `MAX_FAILED_LOGIN_ATTEMPTS = 5`, `LOCKOUT_DURATION = 15 min`,
the counter and `locked_until` written under `select_for_update()`, a success that
resets both, and a lock that clears its own counter when it expires so one new wrong
password does not re-lock immediately. The fifth failure sets the lock, so the sixth
attempt is refused; this was confirmed with the maintainer before implementation.
Every refuse is a typed exception (`InvalidCredentials`, `EmailNotVerified`,
`AccountLocked`), and the first two are ordered so "verify your email" is only shown
after the correct password. `EmailNotVerified` and `InvalidCredentials` messages never
contain the address. A lock writes one `AuditLogEntry` (`action="account_locked"`,
`details={"reason": ..., "failed_attempts": 5}`) and nothing else: no email, name or
password reaches the audit table.

**Tests.** `tests/accounts/test_login_service.py` — 18 passed. A frozen
`django.utils.timezone.now` moves the model and the service together; no test sleeps.
Coverage: success (counter reset, `last_login`, case-insensitive address), wrong
password, unknown address (same error text), inactive account, unverified account,
unverified + wrong password (stays generic), fifth-failure lock, sixth attempt refused
with the right password, attempts while locked do not extend the lock, expiry, expiry
then a wrong password restarting the count, success before the threshold, and the
audit row with a PII-absence assertion.

### Batch 1.8: JWT login, refresh, logout and revocation API (2026-10-20)

**What changed.** `accounts/api_views.py` gained `LoginView` (anonymous, throttle
scope `login`, issues `RefreshToken.for_user`), `RefreshView` (subclass of
SimpleJWT's view, which already rotates and blacklists) and `LogoutView` (blacklists
the refresh token in the body, 204; invalid/blacklisted token is 401). Routes were
added to `accounts/auth_urls.py`. Login maps the service's exceptions to 401
`invalid_credentials`, 403 `email_not_verified` and 423 `account_locked` with
`retry_after` and the same mm:ss wording as the page. Serializers for the four
request/response shapes were added so drf-spectacular documents them. D-7's settings
were already applied in batch 0.5 (15-min access, 7-day refresh, rotation
blacklisting the old token, `token_blacklist` installed), so no settings change was
needed for this batch; a test pins them.

**Tests.** `tests/accounts/test_auth_tokens_api.py` — 22 passed. Token shape and PII
absence, `last_login`, generic 401 for wrong/unknown/inactive, 403 for unverified,
423 after five failures, 900-second access lifetime decoded from the JWT, rotation
returning a new pair, replay of the old refresh returning 401, logout then refresh
401, post-only/body-only logout, `login` throttle scope producing 429, and the three
operations present in the generated schema.

### Batch 1.9: Login, logout and access-denied UI (2026-10-20)

**What changed.** Page #7 (`design.md` S01, wireframe S01, A11y line: one `<h1>`,
visible labels, `autocomplete="email"` / `"current-password"`, lockout as
`role="alert"` announced once) is `templates/accounts/login.html`. `LoginForm` was
added to `accounts/forms.py`; `login_view`, `logout_view`, `role_landing_url` and
`post_login_url` to `accounts/views.py`; the routes to `accounts/public_urls.py`.
The page calls the same `authenticate_with_lockout` as the API and starts a **session**
(D-1, now recorded as accepted in `docs/DECISIONS.md`). `post_login_url` validates
`next` with `url_has_allowed_host_and_scheme` against the request host. No dashboard
route exists yet (pages #15 and #34 land in 1.16 and 1.30), so the role map
(candidate → `candidates:dashboard`, employer/interviewer → `employers:dashboard`)
falls back to `/` until those routes exist; the maintainer chose this over inventing a
page. `logout_view` is POST-only and flushes the server-side session. The existing
`templates/errors/403.html` is exercised through `core.views.error_403`; no new page
was needed.

**Tests.** `tests/accounts/test_login_ui.py` — 21 passed. Form rendering, session
start, generic failure for wrong/unknown/inactive, unverified copy, lockout countdown,
`next` honoured when local and rejected for five off-site forms (including
`//host` and `javascript:`), POST-only logout that clears the session, 403 rendering
and the handler wiring.

### Batch 1.10: Password reset and change (service + API) (2026-10-20)

**What changed.** `accounts/services.py` gained `request_password_reset`,
`make_password_reset_token`, `is_valid_password_reset_token`, `reset_password` and
`change_password`. Reset uses Django's `default_token_generator`, so the token is
bound to the current password hash and dies when used; the one-hour window is
`settings.PASSWORD_RESET_TIMEOUT = 3600` (REQ-FR-004). A reset clears the lockout and
blacklists every outstanding refresh token for the account, so a stolen session does
not survive a reset. `accounts/tasks.py` gained `send_password_reset_email`, which
builds the uid + token at send time and links to `PASSWORD_RESET_URL`.
`accounts/api_views.py` gained the three endpoints from Complete Doc §C.12, with a
`password_reset` throttle scope and the same 202/200 bodies for known and unknown
addresses. A successful change requires the current password and does not revoke
refresh tokens (the caller is the signed-in owner; D-7 makes rotation the revocation
point) — stated in the view docstring.

**Tests.** `tests/accounts/test_password_reset.py` — 29 passed. Valid/reset/expired
(via `override_settings(PASSWORD_RESET_TIMEOUT=-1)`)/reused/tampered/unknown-uid
tokens, weak password, lockout clear, refresh-token blacklisting, the emailed link
actually resets the password (parsed out of the `mailoutbox`), no-op task for an
unknown or inactive account, API non-enumeration (byte-identical body), 400
`invalid_token`, field-keyed validation errors, and the authenticated change route.

### Batch 1.11: Password reset UI (2026-10-20)

**What changed.** Pages #9 and #10 (`design.md` X02, wireframe X02) are
`templates/accounts/forgot_password.html` and `templates/accounts/reset_password.html`,
with `ForgotPasswordForm` and `SetNewPasswordForm` in `accounts/forms.py` and
`forgot_password` / `reset_password_page` in `accounts/views.py`, mounted at
`/forgot-password/` and `/reset-password/`. States: request form, "If that email
exists…", new-password form, expired/reused link (one state, one action), success.
The uid and token travel as query parameters from the email and then as hidden
fields, never in the form action; the page is `no-store` and `no-referrer`.

**Tests.** `tests/accounts/test_password_reset_ui.py` — 12 passed. Both pages render,
known and unknown addresses get the same sentence and only the known one queues mail,
valid/reused/invalid/unknown-uid links, mismatch, weak password, and the cache and
referrer headers.

### Batches 1.7-1.11: commands run (2026-10-20)

Run in this repository with `config.settings.ci`, PostgreSQL/Redis/ClamAV from Compose,
`DEBUG` unset (the shell used for these runs exported `DEBUG=True` by default; sourcing
it makes the 14 pre-existing `test_production_settings.py` tests fail with "DEBUG must
be False in production", which is the environment condition already documented in
README):

* `.venv/bin/pytest tests/accounts/test_login_service.py -q` → **18 passed**
* `.venv/bin/pytest tests/accounts/test_auth_tokens_api.py -q` → **22 passed**
* `.venv/bin/pytest tests/accounts/test_login_ui.py -q` → **21 passed**
* `.venv/bin/pytest tests/accounts/test_password_reset.py -q` → **29 passed**
* `.venv/bin/pytest tests/accounts/test_password_reset_ui.py -q` → **12 passed**
* the five files together → **102 passed**
* `.venv/bin/pytest tests/accounts/ -q` → **350 passed**
* `.venv/bin/pytest tests/ -q` → **465 passed**, 60 warnings (mostly JWT test-key length
  and a drf-spectacular `_UnionGenericAlias` deprecation; both pre-existing)
* `.venv/bin/python manage.py check` → "System check identified no issues (0 silenced)."
* `.venv/bin/python manage.py makemigrations --check --dry-run` → "No changes detected"
* flake8 (repo command) → exit 0
* `black --check .` → only `scripts/verify_docs.py` would be reformatted (pre-existing,
  untouched); the changed files are clean
* `isort --check-only .` → clean
* `mypy config/ core/ accounts/ candidates/ employers/ matching/ ai/
  --ignore-missing-imports` → "Success: no issues found in 77 source files"
* `.venv/bin/python scripts/verify_docs.py` → exit 0 (33 tables, 53 FKs, 27 indexes)
* `.venv/bin/python scripts/verify_bias_set.py` → exit 0

`docs/PROGRESS.md` for 1.7-1.11 is left at `[ ]` with "pending my test output" because
rule 9 of the batch requires the maintainer's pasted run before a batch is marked
complete. `docs/TRACEABILITY.md` sets REQ-FR-002/003/004/007/008 to `done` on the
strength of the runs above; flip any of them to `partial` if the pasted run differs.

**Known limitations.**

* The post-login landing is `/` for every role until batches 1.16 and 1.30 add the
  dashboard routes; `role_landing_url` already holds the correct targets and falls
  back. Chosen by the maintainer rather than inventing a page.
* No protected template view exists yet, so the "login-required redirect" is exercised
  through the login view's `next` handling and the `LOGIN_URL` setting, not through a
  real `@login_required` page.
* The template reset/request views have no per-IP throttle; only the API has the
  `password_reset` scope. Complete Doc §C.12's rate-limit note (line ~2035) is about
  broadcast mail separation, which is Phase 4 and untouched.
* Expired, reused, tampered and unknown-account reset links share one "This link has
  expired" state (design.md X02 has one state). The user cannot tell which happened.
* `RefreshView` and `LogoutView` have no throttle scope: the only documented scope is
  `login`, and inventing another was out of scope.
* A reset performs a `SELECT` over the account's outstanding tokens; fine at MVP
  volumes, but it is not paged.
* No browser, 360px-viewport or axe-core run was performed. The pages follow the
  existing token classes and the S01/X02 A11y notes but that is not the same as a
  manual pass.
* `docs/DECISIONS.md` records D-1 as accepted on the strength of the batch 1.9
  instruction; no separate signed decision exists.

### 2026-10-20 — Batches 1.7-1.11 marked done after a maintainer-requested re-run

The entries above left `docs/PROGRESS.md` at `[ ]` pending the maintainer's pasted test
output (rule 9). The maintainer asked for the tests to be run and the status updated, so
the five lines are now `[x]` with these results, all re-run on this date with `DEBUG`
unset and `DJANGO_SETTINGS_MODULE=config.settings.ci`:

* `pytest tests/accounts/test_login_service.py` -> 18 passed
* `pytest tests/accounts/test_auth_tokens_api.py` -> 22 passed
* `pytest tests/accounts/test_login_ui.py` -> 21 passed
* `pytest tests/accounts/test_password_reset.py` -> 29 passed
* `pytest tests/accounts/test_password_reset_ui.py` -> 12 passed
* the five files together -> 102 passed
* `pytest tests/ -q` -> 465 passed
* `manage.py check` -> no issues; `makemigrations --check --dry-run` -> "No changes detected"

This corrects the earlier statement in this log that the 1.7-1.11 lines were left open.
`docs/TRACEABILITY.md` already had REQ-FR-002/003/004/007/008 at `done`; no change there.

### Batch 1.12: Current-user endpoint (2026-10-20)

**Changed.** Added `GET`/`PUT /api/v1/auth/me/` (Complete Doc §C.12). `MeView`
acts on `request.user` only -- there is no user id in the path or body -- and
declares `permission_classes = [IsAuthenticated]` explicitly. `MeSerializer`
returns the whitelist `email`, `first_name`, `last_name`, `roles`: role names
from the D-2 `ROLES` tuple in fixture order, never `Group.pk` values and never
groups outside that tuple. `MeUpdateSerializer` accepts only `first_name` and
`last_name`, both required (strict PUT); the view writes them with
`save(update_fields=["first_name", "last_name"])` so no other column can be
written. Email changes stay out of scope, and undeclared keys in the body are
ignored. drf-spectacular now documents both operations (`Me`, `MeUpdate`).

**Docs updated with this batch.** Complete Doc §C.12 now records the response
and update contract (the docs previously named only the two verbs); README's
API Endpoints list shows both operations. `docs/TRACEABILITY.md` is unchanged:
the batch covers no REQ-FR, and §C.12 is the source of record. Two line counts
in this file's table (§ File) were corrected because those files changed:
`FAIRFOLD_Complete_Project_Document.md` 2433 -> 2442 and `README.md` 420 ->
421.

**Tests.** New `tests/accounts/test_me_api.py` (16 tests) covers own-data
scoping (including a `?user_id=` attempt), 401 on anonymous GET and PUT through
the real JWT authenticator, strict-PUT 400s, PATCH 405, stable role names, and
a whitelist test asserting `email`, `is_staff`, `is_superuser`, `mfa_enabled`,
`locked_until`, `failed_login_attempts`, `groups`, `roles` and
`email_verified` neither change nor appear in the response.

**Commands run and results.** Local workspace, `config.settings.ci`, `DEBUG`
unset: `pytest tests/accounts/test_me_api.py` -> 16 passed; `pytest
tests/accounts` -> 366 passed; `manage.py check` -> no issues;
`makemigrations --check --dry-run` -> "No changes detected"; flake8 -> exit 0;
black -> 31 files unchanged; isort -> exit 0; `mypy accounts/` -> no issues in
18 source files; `manage.py spectacular` -> exit 0; `pytest tests/` -> 481
passed. With the shell's ambient `DEBUG=True`, 14 pre-existing
`tests/core/test_production_settings.py` tests fail; unsetting `DEBUG` clears
them, and none of the 14 touches this batch.

**Known limitations.** No UI, no audit entry for a name change (no REQ-FR asks
for one), no PATCH. `roles` excludes non-role groups, so a user who holds only
an internal group gets `[]`. Accepted by the maintainer on 2026-10-20; the
`docs/PROGRESS.md` line was changed to `[x]` with this entry's numbers.

### Batch 1.13: Authorization matrix and security headers (2026-10-20)

**Changed.** Added `tests/core/test_authz_matrix.py` (34 tests): a matrix of 30
registered routes with the expected status for anonymous, candidate, employer
and admin, plus three fail-closed checks and one synthetic proof. The route
walker reads `django.urls.get_resolver()` independently of the matrix and
compares both directions, refuses parameterised routes outside `django-admin/`,
and asserts `DEFAULT_PERMISSION_CLASSES` is still `IsAuthenticated`. A route
added without a rule fails `test_every_registered_route_has_a_matrix_row`;
`test_a_route_added_without_a_rule_is_detected` proves that with a synthetic
URLconf. `django-admin/` is one row (its generated CRUD paths share one staff
check); `static/`, `media/`, `api/schema/` and `api/docs/` are excluded and the
reasons are in `docs/AUTHZ_MATRIX.md`.

Added `tests/core/test_security_headers.py` (10 tests): HSTS, nosniff,
`X-Frame-Options` and `Referrer-Policy` on four paths under production-like
settings, plus a plain-HTTP case proving HSTS is not sent before the redirect.

**CSP decision.** Arch Doc §6.3 put CSP at the Nginx edge, but the repository has
no nginx config file and Django 5.2 has no CSP support, so the header was not
present on any response the test suite could see. Per the maintainer's decision,
added `core.middleware.ContentSecurityPolicyMiddleware` and
`settings.CONTENT_SECURITY_POLICY` with a self-hosted policy:
`default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self'
'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self'; font-src
'self'`. No CDN host remains; `'unsafe-inline'` is still required by the two
inline `<script>` blocks and is not disguised as a nonce implementation. The
middleware leaves a response's own CSP intact. `production.py` now refuses an
empty policy, and `test_security_headers.py` asserts the header on every path.

**Docs updated.** New `docs/AUTHZ_MATRIX.md` records the matrix, the discovery
rules, the exclusions and the header contract. Complete Doc §5.5 now states the
self-hosted policy (and the §4.3 cross-reference points at §5.5, not §C.9).
Arch Doc §6.3 no longer tells Nginx to add a second CSP header; it points at the
Django setting instead. The § File line count for the Arch Doc was corrected from
2646 to 2649 because of that edit. `docs/TRACEABILITY.md` is unchanged: this
batch covers no REQ-FR (REQ-SEC-010 is summarised as an NFR group there).

**Commands run and results.** Local workspace, `config.settings.ci`, `DEBUG`
unset: `pytest tests/core/test_authz_matrix.py` -> 34 passed;
`pytest tests/core/test_security_headers.py` -> 10 passed;
`pytest tests/core/test_production_settings.py` -> 20 passed;
`pytest tests/core` -> 120 passed; `pytest tests/` -> 526 passed;
`manage.py check` -> no issues; `makemigrations --check --dry-run` ->
"No changes detected"; flake8 (project apps, migrations excluded) -> exit 0;
black on the changed files -> clean (repo-wide `black --check .` still flags the
pre-existing, untracked-by-this-batch `scripts/verify_docs.py`); isort -> exit
0; `mypy config/ core/ accounts/ candidates/
employers/ matching/ ai/` -> no issues in 77 source files; `verify_docs.py` ->
exit 0.

**Known limitations.** The matrix sends one representative method per route
(GET, or POST with an empty body); a new method on an existing path is not
discovered automatically. API actors use session authentication; the JWT path is
covered by `tests/accounts/test_me_api.py`. `django-admin/` internals are one
row by design. CSP retains `'unsafe-inline'`; nonces are a separate change.
Arch Doc §6.3 and Complete Doc §5.5 still say `Referrer-Policy:
strict-origin-when-cross-origin`, while `production.py` sets `same-origin` (the
stricter value, asserted by the test) -- a pre-existing doc/code mismatch left
for a decision. `Permissions-Policy: camera=(), microphone=()` is documented but
not set by Django and is not asserted. Accepted by the maintainer on 2026-10-20;
the `docs/PROGRESS.md` line was changed to `[x]` with this entry's numbers.

### Batch 1.14: Candidate profile model (2026-10-20)

**Changed.** Added `CandidateProfile` in `candidates/models.py` and its generated
migration `candidates/migrations/0001_initial.py`. The model is transcribed from
Arch Doc §5.1 `candidate_profiles` for REQ-FR-009:

- `user` is a non-null `OneToOneField` with `related_name="candidate_profile"`.
  The DDL leaves `user_id` nullable, but §5.2 draws `users (1) ──(1)──>
  candidate_profiles` and REQ-FR-009 creates the profile for a registered
  candidate; a profile with no owner is unreachable. This is the stricter
  reading, and the second-profile case is rejected by the database.
- `title` (200), `bio`, `location`, `remote_ok` are REQ-FR-009's four onboarding
  fields. Django's `blank=True`/empty-string convention is used instead of
  `NULL`, so "not provided" has one spelling rather than two.
- `skills`, `journey_timeline` and `match_scores` are `JSONField`s with
  `list`/`list`/`dict` defaults. `skills` is the denormalised search copy that
  `prd.md:756` and D-6(e) describe; `candidate_skills` (REQ-FR-014) is the
  source of truth once it lands. `match_scores` is the DDL's read cache, not the
  ranking input.
- `visibility_tier` (`standard`/`promoted`/`verified`) and `is_promoted` are
  present for REQ-FR-053/D3 discovery only. The model comment records that they
  must never enter `match_score` or `rank_applications()`.
- `resume_embedding VECTOR(384)` is deliberately absent. `docs/ROADMAP.md` batch
  2.12 owns the pgvector columns and the extension migration; adding the column
  now would make every test depend on an extension migration that does not exist
  yet.
- `location` is a plain `TextField`. D-5 (encrypt from creation vs defer) is
  still open; this follows `accounts.models.User.first_name`/`last_name`, and a
  note under D-5 in `docs/DECISIONS.md` records that the deferral applies to the
  new column too. Switching it later is a migration, not a rewrite.
- There is no `role` column: D-2 roles are groups. A test asserts that.

**Tests.** `tests/candidates/test_candidate_profile_model.py` has 12 tests:
one-to-one access from both sides, a second profile rejected, a profile without
a user rejected, the DDL defaults, per-row JSON defaults (not shared mutable
objects), cascade from user to profile, profile deletion not deleting the user,
the 200-character title limit, the three visibility values, `__str__` not
rendering the candidate's email, no `role` field, and the UUID key plus
`candidate_profiles` table name.

**Docs updated.** `docs/PROGRESS.md` records 1.14 as pending the maintainer's
output. `docs/TRACEABILITY.md` moves REQ-FR-009 from `not started` to `partial`
with the model and test paths; the onboarding endpoint and UI are 1.15/1.16.
`docs/DECISIONS.md` D-5 gains the implementation note above. No canonical doc
line counts changed.

**Commands run and results.** Local workspace, `config.settings.ci`, `DEBUG`
unset: `pytest tests/candidates/test_candidate_profile_model.py` -> 12 passed;
`pytest tests/` -> 538 passed, 107 warnings; `manage.py check` -> no issues;
`makemigrations --check --dry-run` -> "No changes detected"; black -> clean;
isort -> exit 0; flake8 (candidates + tests/candidates) -> exit 0;
`mypy candidates/` -> no issues in 10 source files.

**Known limitations.** D-5 is still open, so `location` is plain text; the model
does not enforce candidate-group membership (the 1.15 API must), there is no
onboarding API or UI yet, no admin registration (batch 3.30 owns the admin
surface), no `candidate_skills` table (REQ-FR-014) and no `resume_embedding`
(2.12). Accepted by the maintainer on 2026-10-20; the `docs/PROGRESS.md` line was
changed to `[x]` with this entry's numbers.

### Batch 1.12-1.14 acceptance (2026-10-20)

The maintainer confirmed that everything through batch 1.14 is done. The three
`docs/PROGRESS.md` lines were changed from `[ ]` to `[x]`, and the "stays `[ ]`"
sentence at the end of each of the three entries above was corrected in place.
That is the only edit to an older entry, and it corrects a fact rather than
rewriting history.

Re-ran the acceptance commands before marking:

- `pytest tests/accounts/test_me_api.py` -> 16 passed
- `pytest tests/core/test_authz_matrix.py tests/core/test_security_headers.py` -> 44 passed
- `pytest tests/candidates/test_candidate_profile_model.py` -> 12 passed
- `pytest tests/` -> 538 passed, 107 warnings
- `manage.py check` -> no issues
- `makemigrations --check --dry-run` -> "No changes detected"

### Batch 1.15: Candidate profile API and 1.16: Candidate onboarding/profile UI (2026-10-20)

**What changed.**

- **1.15 API.** `GET`/`PATCH /api/v1/candidates/me/` now exist
  (`candidates/api_views.py`, `candidates/serializers.py`,
  `candidates/api_urls.py`). The route is candidate-only through the existing
  `IsCandidate` permission; the target is always `request.user`, so there is no
  id in the path or body. `GET` returns 404 until onboarding. The response is
  exactly the four fields §C.12 names: `title`, `bio`, `location`, `remote_ok`.
  Because §C.12 has no profile `POST`, a non-empty `PATCH` is create-or-update;
  an empty `PATCH` on an absent profile is 404. The Complete Doc §C.12 now states
  that contract explicitly, and the HISTORY line-count table was corrected from
  2442 to 2448 for the added note. The README API list gained the two candidate
  routes and its line count was corrected from 421 to 425.
- **1.16 UI.** Pages #14 and #16 from design.md §10.2 / wireframe S02:
  `/candidate/onboarding/` creates the four fields, `/candidate/profile/` shows
  them with a completeness progressbar, and `/candidate/profile/edit/` updates
  one section at a time from a `<details>` inline form. Templates are
  `templates/candidates/onboarding.html`, `profile.html` and `_section.html`;
  the form classes are in `candidates/forms.py`; the views and the
  candidate-group/login guards are in `candidates/views.py`.
- **Entry point.** The candidate role landing changed from the not-yet-built
  `candidates:dashboard` to `candidate_portal:profile`, so login reaches the
  profile or, when it does not exist, onboarding. The three login-UI assertions
  that expected `/` were updated. The employer/interviewer landing is unchanged.
- **Authorization matrix.** Added `/candidate/onboarding/`,
  `/candidate/profile/`, `/candidate/profile/edit/` and
  `/api/v1/candidates/me/` to `tests/core/test_authz_matrix.py` and
  `docs/AUTHZ_MATRIX.md`. The API row proves candidate 404 vs employer/admin 403
  vs anonymous 401; the page rows prove anonymous redirect vs non-candidate 403.
- **Tests.** `tests/candidates/conftest.py` (role groups and `make_user`),
  `tests/candidates/test_profile_api.py` and
  `tests/candidates/test_profile_ui.py`. They cover ownership, the four role
  gates, validation, create/update, field whitelisting, per-section updates,
  unknown-section 400, escaping, and CSRF on a session POST.

**Contract decisions recorded in code.**

- `PATCH` writes only declared fields (`save(update_fields=...)`). Unknown keys
  (`user`, `id`, `skills`, `journey_timeline`, `match_scores`,
  `visibility_tier`, `is_promoted`, `email`) are ignored by DRF and cannot
  change the row.
- The profile UI never accepts a profile id. A second candidate's POST can only
  reach their own row; if they have none, it redirects them to onboarding.
- `remote_ok` counts as an answered completeness item once the profile exists,
  because `False` is a stored preference, not a missing value. Empty text fields
  are shown as "Not provided".

**Commands run and results (local workspace, `config.settings.ci`, `DEBUG`
unset; these are not a substitute for the maintainer's run).**

- `pytest tests/candidates/ tests/core/test_authz_matrix.py tests/accounts/test_login_ui.py -q` -> 120 passed
- `pytest tests/ -q` -> 591 passed, 161 warnings
- `python manage.py check` -> no issues
- `python manage.py makemigrations --check --dry-run` -> "No changes detected"
- `python manage.py spectacular --file /tmp/fairfold-schema.yaml` -> exit 0
- `flake8 candidates/ tests/candidates/ tests/core/test_authz_matrix.py accounts/views.py tests/accounts/test_login_ui.py --max-line-length=120` -> exit 0
- `black --check` and `isort --check-only` on the changed Python files -> clean
- `mypy candidates/ --ignore-missing-imports` -> no issues in 14 source files
- `python scripts/verify_docs.py` -> all checks passed (14 notes for a human)

**Known limitations.**

- `docs/PROGRESS.md` now marks 1.15 and 1.16 `[x]` (2026-10-20) on the
  maintainer's direction. The batch's rule 9 had left them `[ ]` pending a
  pasted run; the counts recorded are the local targeted/full runs above. If the
  maintainer's run differs, revert those two lines.
- The onboarding page is the **manual profile step** of page #14, not the full
  three-step wizard in the wireframe. Resume upload is batch 1.17 and skills is
  1.18; the page does not fake those steps. There is no stepper, so S02's
  `aria-current="step"` line has nothing to apply to yet. The profile page
  implements S02's inline-edit-per-section behaviour and completeness bar.
- The candidate dashboard (#15) is still absent; login lands on the profile.
- `location` remains plain text while D-5 is open.
- The compiled `static/css/tailwind.css` was not rebuilt in this workspace
  because `node_modules/` is absent. The templates use existing tokens and
  utilities; `npm run build` (or `npm run build:css`) is required before a
  browser check.
- There is no profile `POST`; API-only onboarding creates through a non-empty
  PATCH, as recorded in §C.12. Profile edits are not rate-limited beyond the
  project defaults.
- `CandidateProfile` is still not registered in Django admin (batch 3.30 owns
  that surface). No resume, skills, journey or dashboard columns are exposed by
  this batch.

### 2026-10-20 — Post-1.16 UI polish and DEBUG-only verification link

**What changed.**

- **Landing page.** `templates/home.html` is no longer the "FairFold Demo"
  verification page. It follows design.md X01 (page #1): hero, the two role
  CTAs, Private / Explainable / Affordable cards, a three-step "How it works",
  and a closing CTA. The CTAs link to `/register/?role=candidate` or
  `?role=employer_hr`; `accounts.views.register` now reads that query value and
  preselects the matching radio card. An unknown or privileged value is ignored
  and the form's candidate default applies. No statistics or claims beyond the
  documented privacy, explainability and advisory-AI behaviour were added.
- **Shared account navigation.** `templates/base.html` gained a header nav:
  anonymous visitors see "Log in" and "Create account"; a signed-in candidate
  sees "My profile" and "Log out"; other signed-in roles see only sign-out,
  because employer/interviewer portal pages do not exist yet.
- **Password reveal.** The reveal button in `accounts/_field.html` was only
  wired by a script inside the register panel, so it never appeared on the login
  page. The handler moved to `base.html` and re-initialises after an HTMX swap
  (`data-toggle-ready` prevents a doubled listener). The duplicate register-panel
  script was removed.
- **Pending page (#11).** Added a three-step explanation and a development box
  that shows a clickable verification link and its URL. `accounts.views.check_email`
  only builds that value when `settings.DEBUG` is on and the pending address
  belongs to an active, unverified account. `accounts.tasks.send_verification_email`
  also logs the link at INFO when `DEBUG` is on, because the console email
  backend prints into whichever process sends the message — often the Celery
  worker, not the Django terminal. Neither line runs in production.
- **Onboarding and profile (#14/#16).** Onboarding gained a two-column field
  layout, a bordered remote-work card, a privacy sentence and a "Back to home"
  link. The profile page gained an initials avatar, a completeness panel, a
  four-item checklist, a "Good to know" panel, a clearer empty state
  ("Not provided — use Edit …") and a provided tick per section. The inline-edit
  behaviour, section keys and accessible "Edit …" names are unchanged.
- **Auth and error pages.** Login gained an intro, a friendlier signup link and
  the working reveal button. Register gained an intro and a "Log in" link.
  Forgot/reset copy now states that the link is single-use and expires in an
  hour. The 403/404/500 pages gained decorative icons and clearer action buttons;
  the 500 reference remains selectable text. All copy added is behavioural, not
  a statistic.

**Commands run and results (local workspace, `config.settings.ci`, `DEBUG`
unset).**

- `pytest tests/accounts/test_registration_ui.py tests/accounts/test_email_verification.py -q` -> 89 passed
- `pytest tests/accounts/test_registration_ui.py -q` after the role-preselect tests -> 63 passed
- `pytest tests/candidates/ tests/accounts/test_login_ui.py tests/accounts/test_password_reset_ui.py tests/core/ -q` -> 15 failed, 203 passed because `DEBUG=True` was inherited from the shell; re-ran `env -u DEBUG pytest tests/core/ -q` -> 124 passed. The failures were in `test_production_settings.py` and were caused by the environment, not this change.
- `env -u DEBUG pytest tests/ -q` -> 597 passed, 161 warnings
- `manage.py check` -> no issues; `makemigrations --check --dry-run` -> "No changes detected"
- `flake8` on the four changed Python files -> exit 0; `black --check` and `isort --check-only` -> clean; `mypy accounts/ --ignore-missing-imports` -> no issues in 18 source files
- `python scripts/verify_docs.py` -> exit 0 (human notes only)
- `npm install` + `npm run build` -> `static/css/tailwind.css` 14,519 bytes; `npm run check-budget` -> under 30,720 bytes gzipped. The built CSS and vendored JS are gitignored, as before.
- `docker compose build` + `docker compose up -d --wait` -> all six services healthy (the Compose stack has no source bind mounts, so the image had to be rebuilt for a browser check).
- Manual HTTP check: `GET /` -> 200 and the new hero; `GET /register/?role=employer_hr` -> the employer radio is `checked`; registration -> 302 to `/register/check-email/`; the pending page renders "Development only" and a `token=` link; `GET` that link -> 200 "Email verified"; `GET /static/css/tailwind.css` -> 200, 14,519 bytes. `docker compose logs django` and `logs celery` both contain "Development verification link".

**Known limitations.**

- The verification link is deliberately `DEBUG`-only. With `DEBUG=False` the
  pending page contains no token (pinned by a test), and the task logs nothing
  (also pinned). This is not a replacement for a real email provider.
- The built `static/css/tailwind.css` and `static/js/*` are gitignored. A fresh
  checkout or a Docker build runs `npm run build`; a host-only browser check must
  run it once, or the new utilities will be missing.
- The landing page has no Jobs/Pricing/How-our-AI-works routes to link to, so it
  links only to pages that exist. The base footer's `/privacy/` and `/terms/`
  links still predate this pass and still 404.
- No new requirement, endpoint, model or role was introduced. The `?role=` value
  only preselects one of the two roles the registration form already offers.

### Batch 1.17: S3-compatible dev storage (2026-10-22)

**What changed.**

- **`docker-compose.yml`** — new `minio` service: `${MINIO_IMAGE:-quay.io/minio/minio:latest}`,
  `command: server /data --console-address ":9001"`, `MINIO_API_CORS_ALLOW_ORIGIN` fed from
  `S3_CORS_ALLOWED_ORIGINS`, a `minio_data` volume, published 9000/9001, and a
  `/minio/health/live` probe using the static `curl` the official image bundles. `django`
  depends on `minio: service_healthy` and runs `python manage.py ensure_storage` between
  `seed` and `collectstatic`. Both `django` and `celery` receive `AWS_ACCESS_KEY_ID`,
  `AWS_SECRET_ACCESS_KEY`, `AWS_STORAGE_BUCKET_NAME`, `AWS_S3_ENDPOINT_URL` and
  `AWS_S3_REGION_NAME`, derived from the `MINIO_*` values rather than duplicated in `.env`.
- **`config/settings/base.py`** — `AWS_*` and `S3_CORS_ALLOWED_ORIGINS` read from the
  environment. `STORAGES["default"]` becomes `storages.backends.s3.S3Storage` (path-style,
  SigV4, private, `file_overwrite=False`, `querystring_auth=True`) **only** when
  `AWS_STORAGE_BUCKET_NAME` is set; otherwise the filesystem backend is unchanged, which is
  what `.env.example` already promised.
- **`core/storage.py`** — `object_storage_configured`, `bucket_name`, `s3_client` (reuses
  `default_storage.connection` so the probe and the application cannot disagree about
  endpoint/region/signing), `cors_configuration`, `ensure_bucket`, `apply_cors`, `round_trip`.
  botocore failures become `StorageError` carrying only the S3 error code and the operation;
  no credentials and no request metadata reach a message that is printed or logged.
- **`core/management/commands/ensure_storage.py`** — idempotent bucket creation plus CORS,
  a no-op when no bucket is configured, `CommandError` on failure. **`check_storage.py`** —
  writes, reads back and deletes `healthchecks/<uuid>.txt` through `default_storage`.
- **`.env.example`** — `MINIO_IMAGE`, `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`,
  `MINIO_BUCKET`, `MINIO_PORT`, `MINIO_CONSOLE_PORT`, `S3_CORS_ALLOWED_ORIGINS`; the `AWS_*`
  block documented for host runs and for AWS/R2.
- **`README.md`** — the stack list, the entrypoint steps, `check_storage` in "Verify it is
  up", and troubleshooting for the registry 401, a credential mismatch against an existing
  `minio_data` volume, and ports 9000/9001. **Arch Doc §6.1** records the divergence.
- Out of scope and untouched: any resume model, endpoint or upload UI.

**Findings, verified rather than assumed.** `minio/minio` is gone from Docker Hub (registry
and Hub API both 404). `quay.io/minio/minio` and `quay.io/minio/mc` return `401` to anonymous
pulls while `quay.io/prometheus/busybox` pulls anonymously, so the images are gated rather
than the network. The stack therefore needs `docker login quay.io`, and `MINIO_IMAGE` exists
so a release tag can be pinned where reproducibility matters.

MinIO also answers `NotImplemented` to `PutBucketCors` (confirmed against a real MinIO
release), and enforces CORS at the server level. `ensure_storage` installs the bucket policy
on endpoints that support it (AWS S3, Cloudflare R2) and reports the fallback on MinIO
instead of failing the entrypoint or claiming success.

**Commands run and results (local workspace, `config.settings.ci`, `DEBUG`/`SENTRY_DSN`
unset).**

- `pytest tests/core/test_storage.py -v` (no bucket configured) -> 15 passed, 4 skipped
- `pytest tests/core/test_storage.py -v` (AWS_* pointed at a temporary real MinIO on port
  19000) -> 20 passed, 1 skipped
- `manage.py ensure_storage` -> bucket created, CORS reported as unsupported and delegated
  to `MINIO_API_CORS_ALLOW_ORIGIN`; second run -> "already present"; `manage.py check_storage`
  -> `storage round-trip verified: backend=storages.backends.s3.S3Storage
  bucket=fairfold-media ... bytes=35`
- `pytest tests/ -q` -> 614 passed, 4 skipped
- `manage.py check` -> no issues; `manage.py makemigrations --check --dry-run` -> "No changes
  detected"; `manage.py check --deploy --fail-level WARNING` (production settings) -> no issues
- `flake8` on the changed apps -> exit 0; `black --check` / `isort --check-only` on the five
  changed Python files -> clean; `mypy` -> no issues in 86 source files
- `python scripts/verify_docs.py` -> exit 0 after three line-count rows were refreshed
  (README 425→442, `.env.example` 174→201, Arch Doc 2649→2692)
- `docker compose config` -> seven services with the intended env and `depends_on`
- Preflight check against the same real MinIO with `MINIO_API_CORS_ALLOW_ORIGIN` set:
  `OPTIONS` for `PUT` from `http://localhost:8000` -> `204` +
  `Access-Control-Allow-Origin: http://localhost:8000`
- `docker compose up -d --build --wait` (with the local `.env` image override described below)
  -> seven services healthy including `minio`; the `django` entrypoint logged
  `bucket fairfold-media created; CORS (2 origin(s)): bucket CORS is not supported by this
  endpoint ...`; `docker compose exec django python manage.py check_storage` ->
  `storage round-trip verified ... bytes=35`; `GET /health/ready/` -> `{"status": "ok"}`;
  anonymous `GET http://localhost:9000/fairfold-media/` -> `403`; MinIO console -> `200`;
  `pytest tests/core/test_storage.py` against that live MinIO -> 20 passed, 1 skipped.
- A first full-suite run reported 15 failures in `test_production_settings.py`; the shell had
  `DEBUG=True` and `SENTRY_DSN` exported. Re-ran with them unset -> all 20 pass. Environment,
  not the change.

**Known limitations.**

- **The shipped image was never pulled from quay.** `quay.io/minio/minio` needs a login from
  this machine. The stack was therefore run end-to-end with a local, gitignored `.env`
  override — `MINIO_IMAGE=pgsty/minio:RELEASE.2026-06-18T00-00-00Z` — which proves the compose
  file, settings, entrypoint, bucket creation, CORS and round-trip against a real MinIO, but
  **not** against MinIO's own registry image. The committed default is still
  `quay.io/minio/minio:latest`; after `docker login quay.io`, delete the override (or set it to
  a release tag) and the same acceptance check applies unchanged. A community mirror is a
  local workaround, not an approved dependency.
- **CI has no MinIO service**, because the image cannot be pulled anonymously. The four
  `TestS3Integration` tests skip in CI; everything else runs. Closing that gap needs CI
  registry credentials or an approved alternative image.
- **Bucket-level CORS does not exist on MinIO.** The bucket policy is applied where the
  endpoint implements `PutBucketCors`; on MinIO the server-level allow-list is the mechanism.
- **`config/settings/production.py` still pins `FileSystemStorage`** and is unchanged. The
  production storage decision belongs with the resume model (1.18) and upload API (1.19).
- **Presigned URLs will not work in a browser yet.** Django signs
  `http://minio:9000/...`, a Compose-internal name; batch 1.19 must add a browser-reachable
  endpoint. This batch creates no upload path at all.
- **An existing `.env` needs the `MINIO_*` lines.** Compose deliberately fails with an
  interpolation error rather than defaulting a credential.
- No requirement, table, endpoint, column or role was added. Arch Doc §6.1 and the README
  were amended to describe infrastructure that already existed in the specification
  (REQ-FR-010, Complete Doc §C.6).

### 2026-10-22 — Verification link display is a setting, not a DEBUG check

**What changed (maintainer request).** The pending page (#11) used to render the
verification link only when `DEBUG` was on, which meant a run with `DEBUG=False`
(`config.settings.ci`, a UI test, a colleague's machine) could not finish onboarding
without a real mailbox. It is now controlled by `EMAIL_VERIFICATION_LINK_IN_UI`
(`config/settings/base.py`), which **defaults to `DEBUG`** so nothing changes for anyone
who does not set it.

- `accounts/views.py` — `check_email` reads the new setting; the context key is now
  `testing_verification_url`. It still only builds a link for an active, unverified
  account matching the pending session address.
- `templates/accounts/check_email.html` — copy changed from "Development only" to
  "Testing only" and states that `EMAIL_VERIFICATION_LINK_IN_UI` is what enables it.
  The page remains `never_cache`d, so the token is never written into a cacheable response.
- `config/settings/production.py` — **refuses to boot** with the flag on. The pending page
  can be requested by anyone who types an address, so an enabled flag is a way to verify an
  account you do not own; a default plus a warning is exactly the "I'll remember to turn it
  off" failure this project writes assertions for.
- `.env.example` documents the variable (commented, so the `DEBUG` default applies);
  `README.md` troubleshooting explains what to set when the link does not appear.
- Tests: `tests/accounts/test_registration_ui.py` now pins both directions — the flag
  shows the link with `DEBUG=False`, and `DEBUG=True` alone does not — and
  `tests/core/test_production_settings.py` asserts the production refusal.

**Commands run and results (local workspace, `config.settings.ci`, `DEBUG`/`SENTRY_DSN`
unset).**

- `pytest tests/accounts/test_registration_ui.py tests/core/test_production_settings.py -q`
  -> 84 passed
- `pytest tests/ -q` -> 615 passed, 4 skipped
- `flake8 accounts/ config/` -> exit 0; `black --check` + `isort --check-only` on the five
  changed Python files -> clean
- `python scripts/verify_docs.py` -> exit 0 after two line-count rows were refreshed
  (README 442→446, `.env.example` 201→208)
- `docker compose up -d --build --wait` -> seven services healthy; entrypoint logged
  `bucket fairfold-media already present`
- Live browser-equivalent check with `curl` (fresh cookie jar, candidate signup):
  `POST /register/` -> `302 /register/check-email/`; the pending page contained
  `Testing only`, `Shown because EMAIL_VERIFICATION_LINK_IN_UI`, and a `verify-email/?token=…`
  link. `.env` has `EMAIL_VERIFICATION_LINK_IN_UI=True` for this workspace.

**Known limitations.**

- This is a testing aid, not a product feature: the flag exposes a working verification
  link to whoever requests the pending page for an address, which is why production
  refuses it. It does not replace email delivery in any environment.
- The Celery task's "Development verification link" log line is still `DEBUG`-gated and
  is not controlled by the new setting. The two were left separate deliberately: the log
  writes a token to a log stream, and this change was about the page.
- `tests/bias/test_bias_audit.py:118` still trips flake8 `E203`; it is untouched by this
  change and is not part of the CI flake8 target list.

### 2026-10-22 — The pending page always shows the verification link

**What changed (maintainer request).** The link must be visible all the time, so the
`EMAIL_VERIFICATION_LINK_IN_UI` setting added earlier the same day is **removed** rather than
defaulted on. `/register/check-email/` now always renders the link for an unverified, active
account matching the pending session address — no `DEBUG` check, no setting, no environment
condition.

- `accounts/views.py` — `check_email` builds the token unconditionally; context key is
  `pending_verification_url`. The token-in-log line was removed: the page carries the link, so
  writing the token to a log stream no longer buys anything.
- `templates/accounts/check_email.html` — copy is "For testing — no need to open the email".
  The comment states the consequence and the requirement to re-gate before deployment.
- `config/settings/base.py`, `config/settings/production.py` — the setting and the production
  boot refusal are gone. **Production now boots and renders the link too.**
- `.env.example` — variable removed. `README.md` troubleshooting now says the block is expected
  and explains why it must not ship as-is.
- Tests: `tests/accounts/test_registration_ui.py` renders the link with `DEBUG=False`, and asserts
  an already-verified address still gets a link (corrected below: this entry first said the
  opposite). The production-refusal test was deleted with the assertion it covered.

**This is a deliberate security trade-off, recorded here on purpose.** The pending page can be
requested by anyone who types an address, so any visitor can verify an account they do not own.
That is acceptable for a not-yet-deployed, single-maintainer build and is **not** acceptable once
the app is reachable by other people. Before deployment the block must be re-gated (a `DEBUG`
check or an explicit setting that `production.py` refuses).

**Commands run and results (local workspace, `config.settings.ci`, `DEBUG`/`SENTRY_DSN`
unset).**

- `pytest tests/accounts/test_registration_ui.py tests/core/test_production_settings.py -q`
  -> 83 passed
- `pytest tests/ -q` -> 615 passed, 4 skipped
- `flake8 accounts/ config/` -> exit 0; `black`/`isort` on the five changed Python files -> clean
- `python scripts/verify_docs.py` -> exit 0 after refreshing two line-count rows
  (README 446→447, `.env.example` 208→201)
- `docker compose up -d --build --wait` -> services healthy; live `curl` signup + pending page
  shows the "For testing" block with a `token=` link
- `docker compose exec django python manage.py shell` with the Django test client and
  `override_settings(DEBUG=False)` against the running stack -> `status: 200`, the "For testing"
  block present, a `token=` link present. `DEBUG` no longer decides anything. (The earlier
  `settings.EMAIL_VERIFICATION_LINK_IN_UI` check is no longer applicable: the setting does not
  exist.)

**Known limitations.**

- Unrestricted public verification until the block is re-gated. Tracked as the single item to
  fix before any shared deployment.
- The Celery task still logs "Development verification link" under `DEBUG`; that log line is
  independent of the page and was left alone.

### 2026-10-22 — Multi-line template comments were rendering as page text

**What changed (maintainer report: stray text at the top of the UI).** Django's
``{# ... #}`` is a comment only when both delimiters sit on the **same line**. Six
comment blocks spanned several lines, so the template engine rendered them as literal
text above the header on every page. They are now ``{% comment %} ... {% endcomment %}``:

- `templates/base.html` — five blocks (stylesheet note, CSRF note, skip-link note,
  flash-message note, Chart.js note).
- `templates/errors/500.html` — the support-reference note.

**Favicon 404 fixed.** `base.html` linked `{% static 'img/favicon.svg' %}`, but
`static/img/` did not exist, so every page requested a 404. Added
`static/img/favicon.svg`: a monogram "F" in the `--primary` token colour, marked in the
file as a placeholder because design.md §2.4 lists the logo/favicon as not started and
§19 keeps public logo use behind the RSK-011 trademark search.

**Regression tests.** New `tests/core/test_templates.py` (7 tests) renders `/`,
`/register/` and `/login/` and fails if any of `{#`, `{%`, `{{` or the specific leaked
prose appears in the response. It also asks the staticfiles finders for every
`{% static %}` name in `base.html`, so a reference without a file fails here rather than
in a browser's console.

**Commands run and results (local workspace, `config.settings.ci`, `DEBUG`/`SENTRY_DSN`
unset).**

- `pytest tests/core/test_templates.py -q` -> 7 passed
- `pytest tests/ -q` -> 621 passed, 4 skipped
- `flake8 tests/core/test_templates.py` -> exit 0; `black --check`/`isort` -> clean
- `python scripts/verify_docs.py` -> exit 0
- `docker compose up -d --build --wait django` -> healthy
- Live checks with `curl`: `/`, `/register/`, `/login/` contain no `{#`/`{%`/`{{` and no
  comment prose; `/static/img/favicon.svg` -> `200 image/svg+xml`; a fresh signup's
  `/register/check-email/` renders the "For testing" block with a `token=` link; an HTML
  parser found no unclosed or stray tags on those pages.

**Known limitations / blockers.**

- `/privacy/` and `/terms/` are still 404: they are page #12 ("Privacy policy / Terms",
  REQ-COM-004, design.md W03), which is not implemented. The wireframe's retention
  durations are mockup content, while GAP-A03 ("Data retention policies with specific
  durations", High) is still open, and the repo has no contact address for a policy.
  Writing that page now would invent legal commitments, so it was left alone.
- The favicon is a placeholder monogram, not a brand asset.

### 2026-10-22 — Link was still hidden for an already-verified address (reported)

**What changed.** The maintainer reported the "For testing" block missing on
`/register/check-email/`. The screenshot showed a signed-in account (`s***@gmail.com`) whose
row is already `email_verified=True` (`saima@gmail.com`, joined 2026-10-20). `check_email`
filtered on `email_verified=False`, so a tester reusing an old account — the normal way to
return to that page — got no link and no email. The filter is gone: any **active** account on
the pending address gets a link, verified or not. Following a token for a verified account is
already the success state (`EmailAlreadyVerified`), so the extra link is harmless.

- `accounts/views.py` — `User.objects.filter(email=email, is_active=True)`; comment says why.
- Tests — `test_an_already_verified_address_gets_no_link` became
  `test_an_already_verified_address_still_gets_a_link` (and follows the token to the success
  page); added `test_a_deactivated_address_gets_no_link` for the one filter that remains.
- `README.md` — troubleshooting says the block also appears for an already-verified address.
- **Correction:** the earlier entry today ("The pending page always shows the verification
  link") said the tests assert a verified address gets *no* link. That was true then and is
  wrong now; the sentence was edited to say so rather than left contradicting the code.

**Commands run and results (local workspace, `config.settings.ci`, `DEBUG`/`SENTRY_DSN`
unset).**

- `pytest tests/accounts/test_registration_ui.py -q` -> 64 passed
- `pytest tests/ -q` -> 622 passed, 4 skipped
- `flake8`/`black`/`isort` on the changed files -> clean
- `python scripts/verify_docs.py` -> exit 0
- `docker compose up -d --build --wait django` -> healthy
- Live container check with the real reported account: `saima@gmail.com` (`verified: True`),
  session pointed at the pending page, `override_settings(DEBUG=False, ALLOWED_HOSTS=...)` ->
  `status: 200`, block present, `token=` present.

**Known limitations.** An account with `is_active=False` still gets no link (a token for it
would only fail), and the block is still a public verification bypass until it is re-gated
before deployment.

### Batch 1.18: Resume model (spec first) (2026-10-22)

**What changed.** D-6(a) had already added `candidate_resumes.status` + `processed_at` in batch
0.5, but that vocabulary stopped at `uploaded, processing, extracted, embedded, failed` and had
nowhere to record the scan gate that REQ-SEC-012 and gap P require. This batch amended the
canonical DDL first, then transcribed it.

- `FAIRFOLD_Project_Architecture_and_Requirements.md` §5.1 `candidate_resumes` — the single
  `status` column now carries the full lifecycle `pending, uploaded, scanning, clean, rejected,
  processing, extracted, embedded, failed` (`pending` = a presigned URL was issued, `uploaded` =
  the bytes are confirmed present); added `status_reason` (nullable, never PII) so a rejected or
  failed resume says why; `candidate_id` is now `NOT NULL`, matching §5.2's 1 → N relation. The
  block keeps its original line count, so cross-document `file:line` references do not shift.
- `FAIRFOLD_Complete_Project_Document.md` §C.8 model sketch — updated to `file_key` (key only,
  per REQ-FR-010), the new status vocabulary and `status_reason`.
- `prd.md` §11 — the D-6 note now names `status_reason` and the scan stage.
- `docs/DECISIONS.md` D-6 — implementation note recording the extension without reopening D-6(a).
- `candidates/models.py` — `CandidateResume` (`db_table = "candidate_resumes"`): non-null
  `candidate` FK with `related_name="resumes"`, key-only `file_key`, plain `original_filename`
  following the D-5 precedent, `extracted_text`/`raw_text_hash`, the nine `Status` choices and a
  `CheckConstraint` named `ck_resume_status` (the DDL's name), `status_reason`, `processed_at`,
  `created_at`. `__str__` renders only the id, never the key or the filename.
- `candidates/migrations/0002_candidateresume.py` — generated, not hand-written.
- `tests/candidates/test_resume_model.py` — 10 tests: defaults, every documented status, a
  rejected resume carrying its reason, an unknown status rejected **by PostgreSQL**, `file_key`'s
  NOT NULL, no resume without a candidate, N resumes per candidate, cascade delete, newest-first
  ordering, and `__str__` exposing neither key nor filename.
- `docs/PROGRESS.md`, `docs/TRACEABILITY.md` — batch state and REQ-FR-010/012 evidence.

**Commands run and results (local workspace, `config.settings.ci`, `DEBUG` unset).**

- `pytest tests/candidates/test_resume_model.py -q` → **10 passed**.
- `pytest tests/candidates/ -q` → **71 passed** (42 warnings, all from the short test JWT key).
- `pytest tests/ -q` with `DEBUG` and `SENTRY_DSN` unset → **632 passed, 4 skipped**; the same run
  with this shell's ambient `DEBUG=True`/`SENTRY_DSN` fails 15 `test_production_settings.py` tests,
  the environment artefact recorded in batch 0.5 and unrelated to this change.
- `manage.py check` → "System check identified no issues (0 silenced)."
- `manage.py makemigrations --check --dry-run` → "No changes detected" (with the usual
  `fairfold_test` does-not-exist RuntimeWarning from the migration-history probe).
- `python scripts/verify_docs.py` → exit 0, "All checks passed" (33 tables, 53 FKs, 27 indexes).
- `flake8 ... --max-line-length=120 --extend-exclude='*/migrations/*'` → exit 0.
- `black --check` and `isort --check-only` on the changed Python files → clean after one reformat
  of the test file. `isort --check-only .` → clean (migrations are skipped by config).
- `mypy candidates/ --ignore-missing-imports` → "Success: no issues found in 15 source files".
- `black --check .` → **fails on `scripts/verify_docs.py`**, a file this batch did not touch
  (pre-existing; not caused by this change).

**Known limitations.**

- `original_filename` is plain text: D-5 is still open, so this follows the `CandidateProfile.location`
  precedent rather than creating rows the §C.8.2 rotation procedure cannot read.
- No key generation, no presign endpoint, no scan, no extraction — batches 1.19, 1.20 and 2.10.
- `file_key` has no UNIQUE constraint because the DDL specifies none; uniqueness rests on the
  UUID in the key and is not enforced by the database.
- `docs/PROGRESS.md` was left `- [ ]` in this entry at the time, because the project rule is
  that a batch is only checked off after the maintainer pastes the test output. **Corrected
  2026-10-22:** the maintainer instructed the 1.18–1.20 lines be marked complete, so the line is
  now `[x]`; the local run above is the recorded result.

### Batch 1.19: Presigned upload API (2026-10-22)

**What changed.** REQ-FR-010's upload half: a candidate asks Django for a short-lived
presigned PUT and uploads straight to object storage, so no file bytes cross Django.

- `candidates/uploads.py` (new) — `build_resume_key()` returns
  `resumes/<candidate uuid>/<uuid4 hex><extension>`, with the extension looked up from the MIME
  allow-list rather than taken from the filename; `presign_resume_put()` signs a `put_object`
  with `Bucket`, `Key` and `ContentType` in the signature. Storage and botocore failures become
  `ResumeUploadUnavailable` without interpolating botocore text (it can carry request metadata).
- `candidates/serializers.py` — `ResumeUploadRequestSerializer` requires `content_type`,
  `file_size` and `original_filename`; rejects a type outside `RESUME_ALLOWED_MIME_TYPES` and a
  size above `MAX_UPLOAD_SIZE_BYTES`; strips any path from the filename. The response serializers
  describe `{id, status, upload{url, method, headers, expires_in}}` and deliberately do not echo
  the storage key or the filename.
- `candidates/api_views.py` — `CandidateResumeUploadView` with explicit `permission_classes =
  [IsCandidate]`. Validates, creates the `pending` row, then signs; if signing fails the row is
  deleted and the caller gets 503, so no `pending` row can exist without a URL that could fill it.
  The owner comes from `request.user` and the key from the service; `candidate`, `file_key` and
  `status` in the body are ignored.
- `candidates/api_urls.py` — `POST /api/v1/candidates/resumes/`. No `GET` yet: list/detail is
  batch 1.21.
- `config/settings/base.py` — `MAX_UPLOAD_SIZE_BYTES` default 5 MB → **10 MB**, matching
  REQ-SEC-012 (the 5 MB default was undocumented and contradicted the requirement); added
  `RESUME_ALLOWED_MIME_TYPES = {"application/pdf": ".pdf"}` (REQ-FR-012 reads PDF; DOCX would be
  a type nothing can extract yet) and `RESUME_PRESIGN_EXPIRES_SECONDS` (default 300).
- `.env.example` — documents `MAX_UPLOAD_SIZE_BYTES` and `RESUME_PRESIGN_EXPIRES_SECONDS`.
- `tests/candidates/test_resume_upload_api.py` (new) — 29 tests with a stubbed boto3 client:
  anonymous 401; employer/manager/interviewer/staff 403; no profile 404; allowed PDF creates a
  pending row and returns the upload target; two uploads get different keys; the key never
  contains the filename and takes its extension from the type, not the name; five denied types,
  oversize, non-positive size, every missing field and a blank filename are 400 with no row and
  no signing call; the body cannot choose the owner, key or status; the signed PUT carries the
  stored key and declared type; the expiry comes from settings; storage failure is 503 with no
  row left behind.
- `tests/core/test_authz_matrix.py` + `docs/AUTHZ_MATRIX.md` — the new route has a matrix row
  (anonymous 401, candidate 400 on the empty test body, employer/admin 403). The route-discovery
  test caught the missing row, which is why it exists.

**Commands run and results (local workspace, `config.settings.ci`, `DEBUG`/`SENTRY_DSN` unset).**

- `pytest tests/candidates/test_resume_upload_api.py -q` → **29 passed**.
- `pytest tests/candidates/ -q` → **100 passed**.
- `pytest tests/core/test_authz_matrix.py -q` → **39 passed** after the matrix row was added.
- `pytest tests/ -q` → **662 passed, 4 skipped**.
- `manage.py check` → "System check identified no issues (0 silenced)."
- `manage.py makemigrations --check --dry-run` → "No changes detected" (no model change in this
  batch).
- `python scripts/verify_docs.py` → exit 0 after the `.env.example` line count in the HISTORY
  file table was corrected 201 → 214.
- `flake8`, `black --check`, `isort --check-only` on the changed Python files → clean.
- `mypy candidates/ config/ --ignore-missing-imports` → "Success: no issues found in 25 source files".

**Known limitations.**

- The endpoint trusts the declared `file_size` and `content_type`; the stored object is not
  checked here. Size/MIME verification and ClamAV are batch 1.20, and until then a client can
  declare a PDF and PUT something else.
- No rate limit or per-candidate quota (REQ-SEC-008 is later). A candidate can create pending
  rows by repeating the request.
- No completion step, so a row stays `pending` after a successful PUT; nothing distinguishes
  "uploaded but not finished" from "URL never used" until 1.20.
- The presigned URL is only usable from a browser when `AWS_S3_ENDPOINT_URL` is reachable from
  the browser; the Compose-internal `http://minio:9000` problem recorded in batch 1.17 is
  unchanged here.
- `original_filename` is still plain text (D-5 open), and it is stored before any scan runs.

### Batch 1.20: Upload completion, MIME validation and ClamAV scan (2026-10-22)

**What changed.** REQ-FR-010's upload now has a finish line, and REQ-SEC-012's "MIME validation
+ virus scan" is enforced on the bytes that actually arrived rather than on what the browser
declared when the URL was signed.

- `FAIRFOLD_Complete_Project_Document.md` §C.12 — added
  `POST /api/v1/candidates/resumes/{id}/complete/`. The route did not exist in any canonical
  document, so this was amended first, before any code. No other doc referenced a line number
  past the insertion point; the HISTORY file table's own line count for this document was
  corrected 2448 → 2449.
- `candidates/uploads.py` — `inspect_upload(key, max_bytes=...)` reads the stored object's real
  size from the backend and the first `SNIFF_BYTES` (2048) through `python-magic`; it returns
  `(size, sniffed_mime)` and raises `UploadMissing` (nothing at the key yet, row stays `pending`),
  `UploadProblem` (empty, oversize, undetectable — message safe for `status_reason`), or
  `ResumeUploadUnavailable` (storage broken). `discard_object()` deletes a rejected object best
  effort; `mark_rejected()` writes `rejected` + reason then discards. Storage failures are
  narrowed to `OSError`/botocore/`StorageError`/`ImproperlyConfigured`; a 404/NoSuchKey/NotFound
  is told apart from a real storage outage.
- `candidates/scanner.py` (new) — clamd over `ClamdNetworkSocket.instream`, streaming the open
  storage handle so no temporary file is written. `MalwareDetected` carries ClamAV's signature
  name; every transport/protocol failure becomes `ScanUnavailable`. There is no "unknown" return
  and no setting to disable the scan: **fail closed**.
- `candidates/tasks.py` — `scan_resume(resume_id)` takes the id only (a broker dump carries no
  metadata), runs only while the row is `scanning` (idempotent, so a retry cannot overwrite a
  malware verdict), and settles to `clean` only on an explicit OK. Malware → `rejected` with
  `malware detected: <signature>`; daemon down → `rejected` / `antivirus unavailable`; missing or
  unreadable object → `rejected` / `stored file could not be read`.
- `candidates/api_views.py` — `CandidateResumeCompleteView`, explicit `[IsCandidate]`, ownership
  folded into the lookup (`candidate__user=request.user`) so an unowned id and a nonexistent id
  are both 404. `pending` → checks → `scanning` + `scan_resume.delay` → **202**. A failed check
  → **200** with `status: rejected` and `status_reason`; missing object → **409**, row stays
  `pending`; broker failure → row back to `pending` and **503** (never a row stuck in
  `scanning`). Already `scanning`/`clean`/`rejected` → **200** with the current row, no rescan;
  Phase 2 states (`processing`/`extracted`/`embedded`/`failed`) → **409**.
- `candidates/serializers.py` — `ResumeStatusSerializer` (`id`, `status`, `status_reason`) used by
  both the 200 and 202 bodies.
- `candidates/api_urls.py` — `resumes/<uuid:pk>/complete/` before the router.
- `tests/core/test_authz_matrix.py` + `docs/AUTHZ_MATRIX.md` — the first parameterised API route
  forced a harness extension: `PARAMETERISED_SAMPLES` maps each resolver template to the concrete
  path requested (the nil UUID). An unmapped template still fails, so the fail-closed property is
  kept. Matrix row: anonymous 401, candidate 404, employer/admin 403.
- `tests/candidates/conftest.py` — `resume_storage` (per-test `STORAGES` with a `tmp_path`
  location; overriding only `MEDIA_ROOT` does not reliably reset the cached `default_storage`)
  and `put_object`.
- `tests/candidates/test_resume_completion_api.py` (new, 21 tests) — access (anonymous 401,
  employer/manager/interviewer/staff 403, unknown id 404, another candidate's id 404 and
  untouched), valid PDF → 202 + queued, missing object → 409 + `pending`, empty/oversize/wrong
  magic/declared-mismatch → rejected with a reason and the object deleted, reason never contains
  the filename, settled states idempotent, Phase 2 states 409, queue failure → 503 + `pending`.
- `tests/candidates/test_resume_scan.py` (new, 12 tests) — unit: OK → clean, signature → rejected
  + deleted, daemon down → rejected, unreadable object → rejected, non-`scanning` row untouched,
  clean verdict not overwritten by a retry, unknown/malformed id no-ops; integration against the
  Compose clamd: clean PDF → clean, EICAR → rejected with `Eicar-Test-Signature`, skipped when no
  daemon is reachable.

**Commands run and results (local workspace, `config.settings.ci`, `DEBUG`/`SENTRY_DSN` unset).**

- `pytest tests/candidates/test_resume_completion_api.py tests/candidates/test_resume_scan.py
  tests/core/test_authz_matrix.py -q` → **73 passed** (first run had three real failures: a
  second candidate created without the candidate group got 403 instead of 404; an 8-byte PNG
  signature alone is sniffed as `text/plain` and needed the IHDR chunk; ClamAV reports OK for
  EICAR appended after a PDF trailer, so the integration test stores the bare test string).
- `pytest tests/candidates/ -q` → **133 passed**.
- `pytest tests/ -q` → **696 passed, 4 skipped** (the 4 skips are the pre-existing S3 tests with
  `AWS_STORAGE_BUCKET_NAME` unset).
- `manage.py check` → "System check identified no issues (0 silenced)."
- `manage.py makemigrations --check --dry-run` → "No changes detected".
- `python scripts/verify_docs.py` → exit 0, notes only.
- `flake8 candidates/ tests/candidates/ tests/core/ --max-line-length=120` → clean.
- `black` reformatted `candidates/uploads.py` and the new completion test; `black --check` on
  `candidates/ tests/candidates/ tests/core/` → clean. `isort --check-only` → clean.
- `mypy candidates/ --ignore-missing-imports` → "Success: no issues found in 17 source files".

**Known limitations.**

- A ClamAV outage is terminal for that resume: it becomes `rejected` (fail closed), and the
  candidate must upload again. A retry queue or an operator re-scan command is not in this batch.
- `status_reason` for malware includes ClamAV's signature name. That is not PII, but it is
  attacker-visible through the owner's own resume row; it is not exposed to employers.
- The declared `file_size` is still not compared with the stored size; only the configured limit
  is enforced. Exact equality was not a documented check and could reject a legal upload.
- `uploaded` remains in `ck_resume_status` but no code writes it: completion goes
  `pending → scanning` directly.
- The scan reads through `default_storage`; in production that must be the same bucket the
  presigned URL targets (true whenever `AWS_STORAGE_BUCKET_NAME` is set, which presigning already
  requires).
- `original_filename` is still stored as plain text before the scan runs (D-5 open), unchanged by
  this batch.
- The two real-clamd tests skip when the daemon is unreachable, so a CI runner without the
  Compose service does not exercise INSTREAM end to end.

**Checked off at the maintainer's instruction (2026-10-22).** `docs/PROGRESS.md` changed
1.18, 1.19 and 1.20 from `[ ]` to `[x]`, each with the date and the test result recorded above.
The 1.18 entry's older "stays `[ ]`" sentence was corrected in place for the same reason; no
other older entry was edited.

### Batch 1.21: Resume list, detail and delete API (2026-10-22)

**What changed.** The read side and the erasure side of REQ-FR-010's resume API.

- `candidates/api_views.py` — `CandidateResumeListView` gained `GET` (candidate-only,
  `StandardPagination`, the caller's rows only, newest first) beside the existing `POST`;
  `CandidateResumeDetailView` serves `GET` and `DELETE`. Detail and delete answer one 404
  sentence for "no such row" and "not yours", so ids cannot be enumerated.
- `candidates/serializers.py` — `ResumeSummarySerializer` is a metadata whitelist: id,
  filename, size, MIME type, status, status reason, created-at. No `file_key`, no signed URL,
  no `extracted_text`.
- DELETE is a **hard delete** (D-A): row and bytes, with a `resume.deleted` `AuditLogEntry`
  (`resource_type="candidate_resume"`, `details={"status": …}`, `result="success"`) written in
  the same transaction. No FK references `candidate_resumes`, so nothing dangles; the audit
  trail is what REQ-FR-041 keeps.
- Batch 1.22 moved that body into `candidates/services.py:delete_resume()`, so the API and the
  Resume manager share one implementation instead of two copies of the audit write.
- Spec/docs: §C.12 `DELETE` line, Arch Doc §5.1 deletion note, `docs/AUTHZ_MATRIX.md` rows
  (list, detail, delete) and matching `tests/core/test_authz_matrix.py` rows.
- `tests/candidates/test_resume_list_detail_api.py` (new) — 37 tests: list ownership,
  pagination and ordering; detail whitelist and PII absence; employer/interviewer/staff 403;
  anonymous 401; another candidate's id 404; delete removes row and object, writes the audit
  entry, and a later detail request is 404. The scan task returns quietly if the row is gone,
  so a delete during a scan does not recreate a status.

**Commands run and results.**

- `pytest tests/candidates/test_resume_list_detail_api.py -q` → **37 passed**.
- `pytest tests/candidates/test_resume_list_detail_api.py tests/core/test_authz_matrix.py -q`
  → **80 passed**.
- `pytest tests/ -q` → **736 passed, 4 skipped** (the 4 are the pre-existing S3 skips).
- `manage.py check` → no issues; `makemigrations --check --dry-run` → "No changes detected".
- `scripts/verify_docs.py` → exit 0; flake8, black, isort and mypy clean on the touched paths.

**Known limitations.** Deletion leaves no recoverable copy — that is the accepted decision, not
an accident. A `pending` row whose upload was abandoned can only be removed through this
endpoint.

### Batch 1.22: Resume upload UI and browser-reachable presigning (2026-10-22)

**What changed.** Page #17 (design.md §10.0 row 17, wireframe S03) and the setting that makes a
browser upload possible at all.

- `candidates/views.py` — `resumes` renders the page server-side (own rows, status labels, a
  rejection reason, the size limit, `?replace=<id>` only when that id belongs to the caller) and
  `resume_delete` (GET confirmation, POST mutation). A candidate without a profile is sent to
  onboarding, like page #16.
- `templates/candidates/resumes.html` — list, uploader, `<noscript>` message, progress region
  (`role="progressbar"`, `aria-valuenow`, the percentage as text, a polite live region), and the
  "Personal details are removed before AI screening" note.
  `templates/candidates/resume_confirm_delete.html` — Cancel first in the DOM and focused on
  load; the POST is the only mutation.
- `static/js/resume-upload.js` — presign → XHR PUT with `upload.onprogress` → complete → poll
  while `scanning` (2 s, 20 attempts) → reload. Replace deletes the old row only after the new
  one is `clean`, so a failed upload never leaves the candidate with nothing.
- `candidates/services.py` (new) — `delete_resume()`, shared by the API and the page.
- `config/settings/base.py` — CSP `connect-src` gained the storage origin: `connect-src 'self'`
  blocked the browser PUT while every server-side test still passed.
- **Batch 1.22a, same session, after the environment gap was reported:** the Compose endpoint
  `minio:9000` is not browser-resolvable, and the host is part of the SigV4 signature so a
  signed URL cannot be rewritten. `S3_PUBLIC_ENDPOINT_URL` plus
  `core/storage.py:presign_client()` sign for the browser-reachable host while server-side reads
  keep `AWS_S3_ENDPOINT_URL`; `docker-compose.yml` sets it to `http://localhost:9000` and its
  stale "batch 1.19 will need…" comment is replaced by the implementation.
- Spec first: Arch Doc §6.1 note (which already required a browser-reachable endpoint), Complete
  Doc env table and §C.9 CSP cell, `docs/AUTHZ_MATRIX.md`, `.env.example`.
- `tailwind.config.js` now scans `static/js/**/*.js`, because the script toggles status classes.
- `tests/candidates/test_resume_ui.py` — 32 tests (access, list ownership, storage key never
  rendered, filename escaping, replace ownership, a11y hooks, noscript, delete confirm/404/CSRF/
  audit); `tests/core/test_presign_endpoint.py` — 9 tests (endpoint selection, signed host, boot
  guard for a scheme-less value).
- Deliberate wireframe deviations, all in the template comment: PDF-only copy (the allow-list is
  PDF-only), two pipeline steps (PII stripping and extraction are Phase 2), no "Review" action
  (no file-serving endpoint or Resume Review page yet), Delete is a page rather than a
  `<dialog>` so it works without JavaScript.

**Commands run and results.**

- `pytest tests/candidates/test_resume_ui.py -q` → **32 passed**;
  `pytest tests/core/test_presign_endpoint.py tests/core/test_security_headers.py
  tests/candidates/test_resume_upload_api.py -q` → **47 passed**.
- `pytest tests/ -q` → **780 passed, 4 skipped**.
- Real MinIO check: server `127.0.0.1:9000`, public `localhost:9000`; the signed host was
  `localhost:9000`; `PUT` → **200**; the object was removed afterwards.
- `manage.py check` clean; `makemigrations --check --dry-run` → "No changes detected";
  `scripts/verify_docs.py` → exit 0; flake8 (CI scope), isort, black and mypy clean;
  `docker compose config -q` valid; Tailwind **4,464 B gzipped** against the 30,720 B budget.

**Known limitations.** The browser-only half (CORS preflight, live progress, drag-and-drop) is
a manual check; no automated test performs it. Uploads are not rate-limited. `bandit` cannot run
in this environment (1.7.10 rejects `B108` on Python 3.14); CI must confirm. A replacement adds
a second row until the new scan is `clean` — that is the safe-replace behaviour, not a leak.

**Corrected fact.** The file table earlier in this document said `.env.example` was 214 lines;
the file is 220 after this batch, so the count was corrected in place. No other older entry was
edited.

### Batch 1.23: Employer profile model (2026-10-22)

**What changed.** `EmployerProfile` and `employers/migrations/0001_initial.py` were already in the
working tree from the earlier 1.23 pass; this session verified them against Arch Doc §5.1 and the
tests, then built batches 1.24-1.25 on top. The model is one profile per user (non-null unique FK;
the DDL leaves `user_id` nullable, but §5.2 draws 1:1 and REQ-FR-045 creates it for a user), with
`company_name` TEXT, `industry` VARCHAR(100), nullable `company_size`, `show_company_name`
defaulting to `False` (REQ-FR-042), the three billing columns from the DDL, and `created_at`.
`company_name` and `stripe_customer_id` remain plain text because D-5 is still open; the model
docstring records the deferral and the test `test_company_name_is_plain_until_d5_is_accepted`
pins it. `__str__` returns the primary key, not the company name, so an admin list or log line
cannot render the column the DDL marks ENCRYPTED.

**Commands run and results.**

- `pytest tests/employers/test_employer_profile_model.py -q` -> **13 passed**.
- `manage.py check` -> "System check identified no issues (0 silenced)."
- `manage.py makemigrations --check --dry-run` -> "No changes detected". The command printed a
  `RuntimeWarning` because the local `fairfold_test` database did not exist outside pytest; the
  migration state check itself passed.
- Full suite after 1.24-1.25: `pytest tests/ -q` -> **855 passed, 4 skipped**.

**Known limitations.** D-5 is open, so `company_name` is not encrypted. The DDL's nullable
`user_id` is modelled as non-null unique; a profile with no owner would be unreachable. Billing
columns are stored but have no behaviour (Phase 5). No audit entry is written for profile
creation or editing; REQ-FR-045 does not ask for one and this batch did not invent one.

### Batch 1.24: Employer onboarding API (2026-10-22)

**What changed.** `GET`/`PATCH /api/v1/employers/me/` for the caller's own company profile.

- `employers/serializers.py` -- response whitelist (`company_name`, `industry`, `company_size`,
  `show_company_name`) and an update serializer with only the four documented columns. The owner,
  row id, timestamps and Phase-5 billing columns are not writable or returned.
- `employers/api_views.py` -- `EmployerMeView` with `IsEmployer` set explicitly. `GET` is 404
  before onboarding; `PATCH` is create-or-update, so the first PATCH carrying a non-blank
  `company_name` creates the row (there is no `POST` in §C.12). An empty PATCH on an absent
  profile stays 404; a create without a company name is 400. `update_fields` writes only the sent
  columns.
- `employers/api_urls.py` -- the fixed `me/` path before the router.
- The candidate/employer mutual-exclusion rule is still `accounts.services.assign_role` (batch
  1.2); `IsEmployer` reads the seeded employer groups and a candidate never reaches the view.

**Commands run and results.**

- `pytest tests/employers/test_employer_profile_api.py -q` -> **28 passed** (create/update,
  validation, whitelist, ownership, candidate/interviewer/admin 403, anonymous 401).
- `pytest tests/employers/ tests/core/test_authz_matrix.py -q` -> **121 passed**.
- `manage.py check` clean; `makemigrations --check --dry-run` -> "No changes detected".

**Known limitations.** The API accepts a blank `company_name` on an existing profile even though
creation requires one; the model column is `blank=True` because the DDL has no NOT NULL. Billing
fields stay unwritable. There is no audit entry for a profile change.

### Batch 1.25: Employer onboarding UI (2026-10-22)

**What changed.** Page #33 (design.md §10.3, wireframe W10) and the company edit page.

- `employers/forms.py` -- `EmployerProfileForm` over the four documented columns. `company_name`
  is required in the form (REQ-FR-045, W10's asterisk); `industry` is a text input because §5.1
  has no industry lookup table; `company_size` is a number input because the DDL stores one
  INTEGER and a band select would invent a range-to-integer mapping. The `show_company_name`
  toggle carries plain-language copy: hidden until opt-in, and it never affects candidate ranking.
- `employers/views.py` -- `employer_required` (login redirect first, then 403 for non-employers),
  `onboarding` (GET/POST), `company` (read + edit form) and `company_edit` (POST). The target is
  always `request.user`; there is no id in a URL or body. On an invalid edit the row is re-read so
  the summary shows stored values while the bound form keeps the user's attempt.
- `employers/urls.py` -- `employer_portal` namespace: `onboarding/`, `company/`,
  `company/edit/`.
- `templates/employers/` -- onboarding page, company page, shared form partial and shared error
  summary. The "Skip for now" link is a real equal-weight option that leaves no row.
- `templates/base.html` -- an employer-only "Company" link, so page #33 is reachable from the shell.
- `tests/core/test_authz_matrix.py` + `docs/AUTHZ_MATRIX.md` -- rows for the four page routes and
  the API route.

**Commands run and results.**

- `pytest tests/employers/test_employer_onboarding_ui.py -q` -> **29 passed** (access,
  onboarding, validation, escaping, edit, CSRF, ownership).
- `pytest tests/employers/ tests/core/test_authz_matrix.py -q` -> **121 passed**.
- `pytest tests/ -q` -> **855 passed, 4 skipped**.
- `manage.py check` clean; `makemigrations --check --dry-run` -> "No changes detected";
  `scripts/verify_docs.py` -> all checks passed (14 notes for human confirmation).
- `flake8` (CI scope) clean; `isort --check-only .` clean; `mypy` -> "Success: no issues found in
  96 source files". `black --check .` reports one pre-existing file, `scripts/verify_docs.py`
  (untouched by this batch); the touched files are clean. `bandit` cannot run in this environment
  because the installed version rejects `B105` from `bandit.yaml` (the same class of tooling
  problem recorded for 1.22); CI must confirm.

**Known limitations.** W10's logo, website and three-step stepper (Details / Team / Preferences)
are not built: §5.1 has no `logo`/`website` columns and team management is REQ-FR-047. The page is
a single company-details step with an honest "Skip for now" link. Industry and size use text and
number inputs rather than W10's selects, for the reasons above. There is no employer dashboard
(page #34) yet, so after saving the employer lands on the company page. Browser-only checks
(keyboard traversal, mobile 360px rendering, the Tailwind build output) are manual.

### Progress bookkeeping for 1.23-1.25 (2026-10-22)

**What changed.** The three `docs/PROGRESS.md` lines moved from `[ ]` to `[x]` after the user
asked for the update, on the strength of a fresh confirmation run rather than the earlier session
output. No code, test or traceability status changed. `docs/TRACEABILITY.md` keeps REQ-FR-042 and
REQ-FR-045 at `partial`: `company_name` stays plain text while D-5 is open, and the REQ-FR-045
job-activation guard cannot land before the `Job` model and its activation endpoint (1.26-1.29).

**Commands run and results.**

- `pytest tests/employers/ -q` -> **70 passed**.
- `pytest tests/employers/ tests/core/test_authz_matrix.py -q` -> **121 passed**.
- `pytest tests/ -q` -> **855 passed, 4 skipped** (the 4 skips are the pre-existing unset-S3
  storage tests).
- `scripts/verify_docs.py` -> exit 0, "All checks passed."

### Batches 2.26-2.29: bias-audit integration, rationale persistence, citation tests, page #41 (2026-10-22)

**What changed.** The four batches arrived with Phase-1 job titles (1.26-1.29) above Phase-2
bodies (2.26-2.29). The bodies were implemented, because they are the detailed, mutually
consistent chain; the titles name batches that do not exist yet. Two prerequisites were folded
in from the canonical DDL because 2.27 cannot persist anything without them:

- `matching/models.py` — `Job` (batch 1.26) and `Application` (batch 1.34) from Arch Doc §5.1,
  with `matching/migrations/0001_initial.py`. `jobs.description_embedding VECTOR(384)` is
  deliberately still absent: batch 2.12 owns the pgvector column *and* the extension migration,
  the same deferral `candidates/models.py` documents.
- `ai/citation.py` — the rationale contract from the new Arch Doc §7.5 and its validator
  (batch 2.28's subject, and the input 2.26/2.27 needed).
- `ai/screening.py` — `screen_application()` validates, audits, persists and records in that
  order, in one transaction; `bias_status_for()` reads the status back from the trail.
- `ai/bias_audit.py` — `audit_payload()` gained an optional `model=` keyword that adds
  `ai_model_used` to `details`. Additive: the 40 existing tests are untouched and pass.
- `employers/views.py`, `employers/urls.py`, `templates/employers/application_rationale.html` —
  page #41 (S13) rationale column at `/employer/applications/<uuid>/`.
- `tests/matching/test_job_application_models.py`, `tests/ai/test_citation.py`,
  `tests/ai/test_screening_audit.py`, `tests/employers/test_application_rationale_ui.py`.
- `tests/core/test_authz_matrix.py` + `docs/AUTHZ_MATRIX.md` — the new parameterised route needs
  a sample and a row; the matrix test is fail-closed and caught it.
- `pyproject.toml` — `matching` added to `coverage.source`, per the note already in that file
  ("as each app gains a models.py it must be added to source").

**Decisions recorded, not invented silently.**

1. **Bias status has no column.** §5.1 has none, so the status is the newest
   `audit_log_entries` row (`resource_type='ai_decision'`, `action='bias_audit'`) for the
   application. A review is scoped to the scoring row it followed, so a re-screen requires a
   new review. Recorded in Arch Doc §7.5 and as a comment in the `applications` DDL.
2. **`match_rationale` holds the validated payload as JSON text.** The DDL has one TEXT column
   and page #41 needs claim-level structure; a second JSONB column would duplicate the payload.
   `ai.citation.load_rationale()` is the only reader.
3. **Evidence is a verbatim substring, normalised for case and whitespace, ≥12 characters.**
   Offsets would break on re-stripping. The floor is what stops `"the"` counting as proof.
4. **Missing skills are matched as whole words** (`+`, `#`, `.` are word characters), so `Rust`
   is still missing from a resume that says `trusted`, and `C++`/`.NET` work.
5. **The writer cannot touch a decision field.** `SCORING_FIELDS` excludes `status`,
   `shortlisted_at`, `decided_by`, `decision_override` and `assessment_gate_status`; the audit
   verdict is advisory in the only place that writes a score.

Docs also corrected in passing: Complete Doc §C.4's `JobSkill` pointed at `candidates.Skill`,
but the taxonomy is `core.Skill`; and its `match_rationale` comment now points at §7.5.

**Commands run and results (on this machine).**

- `pytest tests/bias -q` **before** any change -> **40 passed** (the untouched baseline).
- `pytest tests/ai tests/matching tests/bias -q` -> **107 passed**; after the UI tests ->
  **119 passed**.
- `pytest tests/ -q --cov --cov-fail-under=80` -> **950 passed, 4 skipped**, total coverage
  **94%** (`ai/citation.py` 100%, `ai/screening.py` 100%, `matching/models.py` 100%).
- `manage.py check` -> "System check identified no issues (0 silenced)."
- `manage.py makemigrations --check --dry-run` -> "No changes detected".
- `flake8` (CI scope) -> clean. `isort --check-only .` -> clean. `mypy` (CI scope) ->
  "Success: no issues found in 100 source files".
- `black --check .` -> one file, the pre-existing `scripts/verify_docs.py` (not touched here).
- `scripts/verify_docs.py` -> exit 0, "All checks passed."

**Environment note.** `DEBUG=True` is exported in the interactive shell here (the harness has
`.env` loaded), and the full suite then reports 15 failures in
`tests/core/test_production_settings.py` — the documented consequence of sourcing `.env`.
With `env -u DEBUG`, all 20 pass. This is pre-existing and unrelated to these batches.

**Known limitations.** 2.29 is the rationale column of S13 only: the anonymised resume pane
(design.md 7.14, batch 2.9), the assessment-gate panel (REQ-FR-051) and the sticky decision bar
(REQ-FR-051/052) are not built, so page #41 is not yet a complete candidate-review screen. No
provider client or generation exists (2.21-2.25), so the payload is produced in tests, not in
production. No per-employer alias (1.35), so the page shows no alias badge. The batch titles in
the prompt (1.26-1.29) remain unimplemented apart from the two folded models.

### 2026-10-23 — Batch 1.27: create draft job API

`POST /api/v1/jobs/` (REQ-FR-025, Complete Doc §C.12). The endpoint is
`employers.JobCreateView`, mounted at `/api/v1/jobs/` by the new
`employers/job_urls.py`. It requires `IsEmployer` and a company profile, so an
employer who has not onboarded gets the same 404 as the profile endpoint;
candidates, interviewers and platform admins get 403, anonymous callers 401.

The body whitelist is `title`, `description`, `responsibilities`,
`requirements`, `nice_to_have`, `location`, `remote_allowed`,
`experience_level`. `status` is written by the view as `draft`, never read from
the body: REQ-FR-027 makes activation its own audited action, and a create call
that could publish would be a second path to it. `employer` comes from the
caller's `EmployerProfile`, so one employer cannot file a job under another's
name. `screening_questions`, `screening_config`, `cost_estimate`,
`ai_model_used` and the embedding keep their defaults — the first is Phase-2 AI
suggestion with no documented element shape, and the second is the Gap-G3 rule
set that must not be written outside its version bump.

Creation writes exactly one append-only entry: `action="job.created"`,
`resource_type="job"`, the job id, the actor, and `{"title", "status"}`. The
action string is the example named in `core/models.py` and Complete Doc §C.4.
No candidate data is present, and the test asserts the key set.

**Files.** `employers/serializers.py` (`JobCreateSerializer`, `JobSerializer`),
`employers/api_views.py` (`JobCreateView`; `_profile_for` renamed to
`employer_profile_for` so the jobs view can reuse it), `employers/job_urls.py`
(new), `api/urls.py` (mount), `tests/employers/test_job_create_api.py` (20
tests), `tests/core/test_authz_matrix.py` (row), `docs/AUTHZ_MATRIX.md`,
`docs/TRACEABILITY.md` (REQ-FR-025 -> `partial`), `docs/PROGRESS.md`.

**Commands run and results.**

- `pytest tests/employers/test_job_create_api.py -q` -> **20 passed**.
- `pytest tests/core/test_authz_matrix.py -q` -> **53 passed**.
- `pytest tests/employers/ tests/matching/ tests/core/test_authz_matrix.py -q`
  -> **175 passed**.
- `pytest tests/ -q` with the README CI environment (below) -> **971 passed, 4
  skipped**.
- `pytest tests/bias/ -q` -> **40 passed** (untouched).
- `manage.py check` -> "System check identified no issues (0 silenced)."
- `manage.py makemigrations --check --dry-run` -> "No changes detected".
- `flake8` (CI scope) -> clean. `isort --check-only .` -> clean. `mypy` (CI
  scope) -> "Success: no issues found in 101 source files".
- `black --check .` -> only the pre-existing `scripts/verify_docs.py` (not
  touched here).
- `bandit` with the CI arguments -> **cannot run in this environment** (corrected
  2026-10-24: the earlier wording said "exit 0" because `$?` was read from the
  `tail` in the pipeline, not bandit). bandit 1.7.10 on Python 3.14 fails to load
  its plugin set: it prints `[main] ERROR Unknown test found in profile: B104`
  (the unknown ID varies between runs) and exits 2, and even without `-s` it
  logs `Exception occurred when executing tests against employers/views.py`.
  Environment/tooling, not this change; CI must confirm.
- `scripts/verify_docs.py` -> exit 0, "All checks passed". `scripts/verify_bias_set.py`
  -> exit 0.

**Environment note for future batches.** This shell exports
`DJANGO_SETTINGS_MODULE=config.settings.local` (from `.env`), so `env -u DEBUG`
is *not* enough: `tests/conftest.py`'s `os.environ.setdefault` cannot override
it, collection runs against the local settings module, and
`tests/core/test_authz_matrix.py::test_no_parameterised_route_is_silently_uncovered`
fails because `config.urls` is imported at collection with `DEBUG=True` and
therefore carries the `static/` and `media/` patterns. That failure is a
consequence of the environment, not of this change: it reproduces with the new
route removed. The reliable invocation is `env -i` with the variables listed in
README "Running tests":

```
env -i PATH="$PATH" HOME="$HOME" LANG=C.UTF-8 \
  DJANGO_SETTINGS_MODULE=config.settings.ci \
  DJANGO_SECRET_KEY=test-only-not-a-real-key \
  ENCRYPTION_KEY=test-only-fernet-placeholder-0000000000= \
  DB_PASSWORD=devpassword DB_HOST=127.0.0.1 \
  REDIS_URL=redis://127.0.0.1:6379/0 \
  CELERY_BROKER_URL=redis://127.0.0.1:6379/0 \
  CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/1 CLAMD_HOST=127.0.0.1 \
  .venv/bin/pytest tests/ -q
```

**Known limitations.** No AI-suggested screening questions or skills
(REQ-FR-025's second clause, Phase 2), no `job_skills` rows, and no subscription
job quota (no `Subscription` model yet), so the free-plan three-job limit is not
enforced. `GET /api/v1/jobs/` answers 405 until its own batch; the jobs list is
page #35 (batch 1.30). Draft editing/deletion (1.28) and activation/pause/close
(1.29) are still open.

### 2026-10-24 — Batches 1.28 and 1.29: draft edit/delete, and the job lifecycle

**Spec first.** The batches needed endpoints no canonical document declared:
deleting a job, and pausing/closing one. `design.md` page #37 says
"edit/pause/close" and the §5.1 DDL has the four statuses, but Complete Doc
§C.12 listed only `activate/`. Rather than putting verbs behind an undeclared
resource, two amendments went in before code:

- Arch Doc **§4.3 Job Posting Lifecycle** — the normative transition matrix
  (`draft|paused -> active`, `active -> paused`, `active|paused -> closed`), the
  `409` cases, idempotency, the draft-only edit/delete rules, the cascade
  argument for deletion, and the audit action names.
- Complete Doc **§C.12** — `DELETE /api/v1/jobs/{id}/`,
  `POST /api/v1/jobs/{id}/pause/`, `POST /api/v1/jobs/{id}/close/`, and a note
  pointing at §4.3. No table, column, foreign key or FR changed, so the 33/53/27
  and 63 counts are untouched. `scripts/verify_docs.py` passes.

**Code.** `employers/api_views.py` gained `JobDetailView` (GET/PATCH/DELETE) and
`_JobStateView` with `JobActivateView`/`JobPauseView`/`JobCloseView`;
`employers/serializers.py` gained `JobUpdateSerializer`; `employers/job_urls.py`
routes them. Every write runs under `select_for_update()` inside one
transaction, so two racing actions cannot both audit a transition. Ownership is
still the caller's profile: another employer's id is a 404, not a 403 that would
confirm it exists. `job.updated` stores changed field **names**, `job.deleted`
the title, the state actions `{"from", "to"}` — no values, no candidate data.

`pyproject.toml`: `employers` added to `coverage.source`, as the note in that
file requires once an app has models; it measures 100%, and the total moved from
94% to 95%.

**Tests.** `tests/employers/test_job_edit_delete_api.py` (32) and
`tests/employers/test_job_lifecycle_api.py` (24), plus four matrix rows and four
`PARAMETERISED_SAMPLES` entries in `tests/core/test_authz_matrix.py`.

**Commands run and results** (README CI environment; see the 2026-10-23 entry for
why `env -u DEBUG` alone is not enough in this shell).

- `pytest tests/employers/test_job_edit_delete_api.py -q` -> **32 passed**.
- `pytest tests/employers/test_job_lifecycle_api.py -q` -> **24 passed**.
- `pytest tests/employers/ tests/core/test_authz_matrix.py -q` -> **217 passed**.
- `pytest tests/ -q --cov --cov-fail-under=80` -> **1033 passed, 4 skipped**,
  **95%** total (employers 100%, matching 100%).
- `pytest tests/bias/ -q` -> **40 passed** (untouched).
- `manage.py check` -> "System check identified no issues (0 silenced)."
- `manage.py makemigrations --check --dry-run` -> "No changes detected".
- `flake8` (CI scope) -> clean. `isort --check-only .` -> clean. `mypy` (CI
  scope) -> "Success: no issues found in 101 source files".
- `black --check .` -> only the pre-existing `scripts/verify_docs.py`.
- `scripts/verify_docs.py` -> "All checks passed."
- `bandit` -> **could not run**: bandit 1.7.10 on Python 3.14 fails to load its
  plugin set (`Unknown test found in profile: B104`, varying between runs) and
  exits 2; without `-s` it logs exceptions while executing tests. CI must
  confirm. The 2026-10-23 entry was corrected: it had reported "exit 0" from the
  pipeline's `tail`, not from bandit.

**Known limitations.** REQ-FR-027 stays `partial`: nothing yet serves `active`
jobs to candidates (public board, batch 1.31), so "job visible to candidates" is
not demonstrated. A published job cannot be edited (409 by design); no revisioned
edit flow exists. `PATCH` cannot touch `screening_questions`/`screening_config`
for the reasons in the 1.27 entry. `GET /api/v1/jobs/` (the list, page #35) is
still 405. No subscription quota, no scheduled close, no `job_skills`.

### 2026-10-24 — Batch 1.30: employer job management UI (pages #35, #36, #37)

**What changed.** The employer portal now manages jobs through HTML rather than
only through the API. Page #35 (`/employer/jobs/`) lists the caller's jobs with
one tab per §4.3 status and a count on each tab; page #36
(`/employer/jobs/new/`, `/employer/jobs/{id}/edit/`) creates and edits drafts;
page #37 (`/employer/jobs/{id}/`) shows the pipeline and offers the state
actions. All routes are namespaced `employer_portal` and guarded by
`employer_required` + a profile check.

**One state machine, two surfaces.** `employers/services.py` is new and holds
`change_job_status`, `delete_draft_job`, `record_job_audit` and `job_status`. The
1.28/1.29 API views were refactored to call them, so `POST
/api/v1/jobs/{id}/pause/` and the Pause button on page #37 run the same code:
same lock, same idempotent no-op, same 409 sentence, same audit entry. The
service is HTTP-free and raises `Job.DoesNotExist`; each surface maps that to its
own 404.

**What the pages do not have, deliberately.** Page #36's AI-suggested skills and
questions are Phase 2 (REQ-FR-025's second clause); structured skills need
`job_skills`, which has no model; screening questions are JSONB whose element
shape no document defines, so neither the API nor the form accepts them;
required assessments are REQ-FR-051 and have no model; page #37's share
link/embed points at the public job URL (batch 1.33) and its screening-rules
banner needs `screening_config` editing, so neither is rendered — a copy button
for a 404 is worse than no button. The five-step stepper is rendered as sections
with anchors: no step has its own validation, so a wizard would only hide fields.

**Auto-save.** `POST /employer/jobs/{id}/autosave/` posts the same `JobForm` on
`change` (600 ms debounce) and swaps the `role="status" aria-live="polite"`
region. It answers 200 even when the draft is invalid, because HTMX does not swap
a 4xx and a stale status line is the failure the page's a11y note is about; the
fragment then says "Not saved: <first error>". A published job is 409. No audit
entry is written for an unchanged or an invalid save.

**Fields assert the whitelist, not a copy of it.** `JobForm.Meta.fields` is the
`JobCreateSerializer` set. `status` and `employer` are not fields, so a body
carrying `status=active` cannot publish (covered by a test).

**Commands run and results** (README CI environment; see the 2026-10-23 entry for
why `env -u DEBUG` alone is not enough in this shell).

- `pytest tests/employers/test_job_management_ui.py -q` -> **54 passed**.
- `pytest tests/employers tests/core tests/matching -q` -> **421 passed, 4
  skipped**.
- `pytest tests/core/test_authz_matrix.py -q` -> **70 passed** (11 new cases).
- `pytest tests/ -q --cov --cov-fail-under=80` -> **1098 passed, 4 skipped**,
  **95%** total (`employers/views.py` 98%, `employers/services.py` 100%).
- `pytest tests/bias/ -q` -> included in the full run, **40 passed** (untouched).
- `manage.py check` -> "System check identified no issues (0 silenced)."
- `manage.py makemigrations --check --dry-run` -> "No changes detected".
- `flake8` (CI scope) -> clean. `isort --check-only .` -> clean. `mypy` (CI
  scope) -> "Success: no issues found in 102 source files".
- `black --check .` -> only the pre-existing `scripts/verify_docs.py`.
- `scripts/verify_docs.py` -> "All checks passed."
- `bandit` -> **could not run** for the reason in the 2026-10-23 entry (bandit
  1.7.10 on Python 3.14 cannot load its own plugin profile). CI must confirm.

**Known limitations.** `employers/views.py` lines 573-574 and 653-654 (the
`Job.DoesNotExist` branch taken when a job is deleted between the ownership fetch
and the row lock) are unreachable without a race and are not covered. Delete and
Close still ask for confirmation through an inline `onsubmit="return
confirm(...)"` rather than S11's `⋯` menu with a dialog; the server refuses a
non-draft delete regardless. No pagination on page #35: the spec does not give a
page size and an employer with many jobs would get one long table. REQ-FR-027
remains `partial` until the public board (1.31) serves `active` jobs.
