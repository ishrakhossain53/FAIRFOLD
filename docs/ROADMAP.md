# FairFold development roadmap (micro-batch plan)

Built from the repository as uploaded (`FAIRFOLD-main.zip`, 203 files), not from a generic template.

## Is the micro-batch approach right?

Yes. Small numbered batches, tests with each one, and a human review and commit after each one is the
right way to build this with an AI agent, and it fits how the repo is already run (HISTORY.md is a
verified log, CI is strict). The plan below keeps that, but corrects an earlier draft that assumed a
less-built repo.

## What the repo actually contains

| Area | State (from reading the code) |
|---|---|
| Docs | Five long specs plus `validation/`. 63 FRs, 50 NFRs, 32-table DDL, 78 page specs. Very thorough. |
| Scaffold | Django project, 4 settings modules, 11 app packages, Docker Compose, Dockerfile, CI workflow, Tailwind/HTMX build. |
| `accounts` | **`User` model and migration exist** (UUID pk, email login, lockout fields, roles as groups). No endpoints, no tests. |
| `core` | `AuditLogEntry` and `Skill` models, migration, seed command, groups and skills fixtures, middleware, health endpoints, pagination, exception handler. |
| `ai` | `bias_pass.py` and `bias_audit.py` plus versioned bias test sets v1.0.0 and v1.0.1. **No `AIProvider` yet.** |
| Other 8 apps | `candidates`, `employers`, `matching`, `assessments`, `interviews`, `notifications`, `journey`, `api`: empty `models.py` (12 lines each), no endpoints. |
| Tests | `tests/bias/` and `tests/core/` only. Nothing for `accounts`. |
| Templates | `base.html`, `home.html`, error pages. No feature pages. |

### What I ran, and what I did not

- Ran: `tests/bias/` outside Django (**40 passed**), `scripts/verify_bias_set.py` (both versions consistent), `scripts/verify_docs.py` (exit 0 with warnings: mentions of "bias-free" to review, and 65 wireframes defined vs 61 referenced by a page row, while the README says 64).
- Did **not** run: the Docker stack, or any Django/database test. Those need PostgreSQL, Redis and ClamAV from Compose. HISTORY.md §2.38 says 115 tests passed on 2026-10-16. I have not reproduced that. Batch 0.2 does.
- The zip has no `.git` folder, so I could not see history or branches.

## Findings that change the plan

1. **HISTORY.md is partly stale.** It says "no Django model exists", but `accounts.User`, `core.AuditLogEntry` and `core.Skill` do. It also says current branch is `v3` while the zip is named `main`. Confirm you are working on the right branch.
2. **Batch 1.1 of the earlier draft is already done.** The custom user model exists. What is missing is tests, and the earlier draft's "role choices" does not match the design: roles are Django **groups**, not a field.
3. **No `AIProvider` exists**, although the earlier draft said to "audit and reuse" it. It is built in Phase 2 (batch 2.21).
4. **Several things the earlier draft would have built are not in the schema.** A screening-run table, resume upload/scan/processing status, and a job-to-skills link (REQ-FR-042 searches skills). Building them silently would break `verify_docs.py` and the canonical DDL. They are handled spec-first.
5. **The anonymised alias (REQ-FR-054) belongs in Phase 1.** The first employer-facing list would otherwise show candidate identity and need retrofitting. It is pulled forward (decision D-4).
6. **Tests are bundled with features.** A separate "write tests" batch after each model tends to be skipped or watered down.

## Decisions needed (answer these before Phase 1 code)

Batch 0.4 asks the agent to write a proposal for each; you answer; batch 0.5 applies them.

| # | Decision | Evidence |
|---|---|---|
| D-1 | **Auth for template pages: session or JWT?** AD-002 promises "no auth-token complexity" but REQ-FR-002/007/008 specify JWT, and settings enable both JWT and session auth. Recommendation: sessions for HTMX pages, JWT for `/api/v1/`, one shared lockout/verification service so the rules exist once. | Arch Doc AD-002, §4.1; `config/settings/base.py` REST_FRAMEWORK |
| D-2 | **Role vocabulary.** `groups.json` has `candidate, employer_hr, employer_admin, interviewer`. REQ-FR-047 says `employer_manager, employer_hr, interviewer` and protects "the last `employer_hr`". REQ-FR-037/038/039/049/050 say "admin" but no admin group exists. Pick one list and update all places together. | `core/fixtures/groups.json`; Arch Doc §4.1 |
| D-3 | **Email verification has no endpoint** in the API list (§C.12), though REQ-FR-001/002 require it. Add `verify-email` and resend endpoints to the spec. | Complete Doc §C.12 |
| D-4 | **Alias in Phase 1** (see finding 5). Recommendation: yes. | REQ-FR-029, 054 |
| D-5 | **Encrypted fields: now or in Phase 4?** The DDL marks 10 fields ENCRYPTED (names, location, company name, filename, credential id...). `accounts/models.py` stores names in plain text "for now". Retrofitting encryption later needs a data migration; creating models encrypted from the start is cheaper but needs the key-rotation plan (Complete Doc §C.8) first. | `accounts/models.py` docstring; Arch Doc §5.1 |
| D-6 | **Schema holes to amend first:** resume upload/scan/processing status; where a screening run's state lives; how jobs link to skills; `users` has `date_joined` but the DDL says `created_at`/`updated_at`; `skills` exists both as JSONB on candidate_profiles and as a `candidate_skills` table. | Arch Doc §5.1 |
| D-7 | **JWT settings vs spec.** REQ-FR-002: access token 15 min; settings: 30 min. REQ-FR-007: old refresh token stays valid; settings: rotate and blacklist after rotation. `token_blacklist` is not in INSTALLED_APPS, but REQ-FR-008 needs it. | `SIMPLE_JWT`; Arch Doc §4.1 |
| D-8 | **Which branch is the truth,** `main` or `v3`? | HISTORY.md §4.9 |

Also check before Phase 4: `requirements.txt` includes `stripe` while REQ-FR-056 makes bKash/SSLCommerz the Phase 4 payment path and Stripe a Phase 5 option.

## How to run each batch

1. `git checkout -b batch/<id>-<slug>`
2. New agent session. Put `CLAUDE.md` (or `AGENTS.md`) in the repo root once; the agent reads it automatically.
3. Paste the batch prompt from `prompts/`.
4. Read the agent's scope plan. Correct it before it codes if it is off.
5. Read the report and the `git diff`. Run the tests yourself. Click through any UI.
6. Good: update the three progress files (`docs/PROGRESS.md`, `docs/TRACEABILITY.md`, `HISTORY.md`), commit, merge. Bad: discard the branch or reply with fixes for this batch only.

Rules of thumb: if a batch needs more than about one session of review, split it. If an agent reports a
contradiction in the docs, answer it and record the answer in the docs before continuing.

## Batch list

### Phase 0: Reconcile, baseline, decide

Know exactly what exists, prove it runs, and settle the contradictions that would otherwise be discovered halfway through a batch. Almost no product code is written here.

| ID | Batch | Type |
|---|---|---|
| 0.1 | Reconcile repo state against HISTORY.md | audit |
| 0.2 | Baseline run (Docker, tests, lint, docs checks) | audit |
| 0.3 | Requirements traceability table | docs |
| 0.4 | Propose decisions D-1 to D-8 (no code) | decision |
| 0.5 | Apply the accepted decisions to specs and settings | docs |

### Phase 1: Core recruitment platform (no AI)

A user can register, verify, sign in, maintain a profile, employers can post jobs, candidates can apply, employers can review and change status. Matches Arch Doc §10 Phase 1.

| ID | Batch | Type |
|---|---|---|
| 1.1 | User model characterization tests | backend+tests |
| 1.2 | Role helpers, permission classes, role-exclusivity | backend+tests |
| 1.3 | Registration service | backend+tests |
| 1.4 | Email verification tokens and email task | backend+tests |
| 1.5 | Registration and verification API | backend+tests |
| 1.6 | Registration and verification UI | ui |
| 1.7 | Login service with lockout | backend+tests |
| 1.8 | JWT login, refresh, logout and revocation API | backend+tests |
| 1.9 | Login, logout and access-denied UI | ui |
| 1.10 | Password reset and change (service + API) | backend+tests |
| 1.11 | Password reset UI | ui |
| 1.12 | Current-user endpoint | backend+tests |
| 1.13 | Authorization matrix and security headers | tests |
| 1.14 | Candidate profile model | backend+tests |
| 1.15 | Candidate profile API | backend+tests |
| 1.16 | Candidate onboarding and profile UI | ui |
| 1.17 | S3-compatible dev storage | infra |
| 1.18 | Resume model (spec first) | backend+tests |
| 1.19 | Presigned upload API | backend+tests |
| 1.20 | Upload completion, MIME validation and ClamAV scan | backend+tests |
| 1.21 | Resume list and detail API | backend+tests |
| 1.22 | Resume upload UI | ui |
| 1.23 | Employer profile model | backend+tests |
| 1.24 | Employer onboarding API | backend+tests |
| 1.25 | Employer onboarding UI | ui |
| 1.26 | Job model | backend+tests |
| 1.27 | Create draft job API | backend+tests |
| 1.28 | Edit and delete draft jobs | backend+tests |
| 1.29 | Activate, pause and close jobs | backend+tests |
| 1.30 | Employer job management UI | ui |
| 1.31 | Public job list and detail API | backend+tests |
| 1.32 | Search, filters, ordering and pagination | backend+tests |
| 1.33 | Public job board UI | ui |
| 1.34 | Application model | backend+tests |
| 1.35 | Per-employer candidate alias service | backend+tests |
| 1.36 | Apply to a job API | backend+tests |
| 1.37 | Apply UI | ui |
| 1.38 | Candidate application history API | backend+tests |
| 1.39 | Candidate application list and detail UI | ui |
| 1.40 | Employer application inbox API | backend+tests |
| 1.41 | Application status actions | backend+tests |
| 1.42 | Employer application review UI | ui |
| 1.43 | Notification model and delivery | backend+tests |
| 1.44 | Notification list and unread UI | ui |
| 1.45 | Phase 1 end-to-end test | tests |
| 1.46 | Phase 1 closeout | audit |

### Phase 2: AI screening pipeline

Privacy-first resume processing, reproducible ranking, evidence-cited rationales, reviewable filters and auditable human decisions. AI stays advisory throughout.

| ID | Batch | Type |
|---|---|---|
| 2.1 | Resume processing states (spec first) | backend+tests |
| 2.2 | PDF text extraction service | backend+tests |
| 2.3 | Extraction edge cases | backend+tests |
| 2.4 | Process endpoint and Celery task | backend+tests |
| 2.5 | Extraction status UI | ui |
| 2.6 | PII test dataset and accuracy harness | tests |
| 2.7 | Deterministic PII redaction | backend+tests |
| 2.8 | NER and proxy stripping | backend+tests |
| 2.9 | Persist sanitised text and audit the strip | backend+tests |
| 2.10 | Bias test set v1.0.2 (proxy cases) | tests |
| 2.11 | Embedding service | backend+tests |
| 2.12 | pgvector columns and migration | backend+tests |
| 2.13 | Resume embedding task | backend+tests |
| 2.14 | Job embedding task | backend+tests |
| 2.15 | Similarity and deterministic ranking fixtures | backend+tests |
| 2.16 | Hard-filter rules and versioning | backend+tests |
| 2.17 | rank_applications service | backend+tests |
| 2.18 | Reviewable not_matched candidates | backend+tests |
| 2.19 | Ranked applications API | backend+tests |
| 2.20 | Ranked results UI | ui |
| 2.21 | AIProvider abstraction and OpenRouter client | backend+tests |
| 2.22 | Offline fallback and provider-error handling | backend+tests |
| 2.23 | Outbound PII gate | backend+tests |
| 2.24 | Rationale schema and validation | backend+tests |
| 2.25 | Rationale generation for one application | backend+tests |
| 2.26 | Integrate the bias audit | backend+tests |
| 2.27 | Store rationale with audit entry | backend+tests |
| 2.28 | Evidence traceability tests | tests |
| 2.29 | Rationale detail UI | ui |
| 2.30 | Decide where screening-run state lives (spec first) | decision |
| 2.31 | Server-side cost estimator | backend+tests |
| 2.32 | Preflight and explicit confirmation | backend+tests |
| 2.33 | Batch screening task | backend+tests |
| 2.34 | Progress, failure and retry states | backend+tests |
| 2.35 | Screening UI | ui |
| 2.36 | Screening end-to-end test | tests |
| 2.37 | Override rule and reason (REQ-FR-052) | backend+tests |
| 2.38 | Override dialog UI | ui |
| 2.39 | Controlled identity reveal at shortlist | backend+tests |
| 2.40 | Candidate sees match score and evidence | backend+tests |
| 2.41 | Bias flags and warnings in the recruiter UI | ui |
| 2.42 | Review of not_matched in the UI | ui |
| 2.43 | Phase 2 closeout and capacity check | audit |

### Phase 3: Candidate AI features and remaining workflows

Skills and journey, assessments with the screening gate, interview coaching, messaging, and employer operations. One feature at a time; stop when a prerequisite is incomplete.

| ID | Batch | Type |
|---|---|---|
| 3.1 | Skill catalog and alias mapping | backend+tests |
| 3.2 | Candidate skills API and UI | backend+tests |
| 3.3 | Certification management | backend+tests |
| 3.4 | Structured education and career records | backend+tests |
| 3.5 | Career timeline (data + UI) | backend+tests |
| 3.6 | Skill evolution chart | backend+tests |
| 3.7 | Job-specific narrative | backend+tests |
| 3.8 | Assessment models | backend+tests |
| 3.9 | Assessment authoring (API + UI) | backend+tests |
| 3.10 | Attach a required assessment to a job | backend+tests |
| 3.11 | Gate computation and shortlist block (backend) | backend+tests |
| 3.12 | Gate status UI | ui |
| 3.13 | Assessment attempts (backend) | backend+tests |
| 3.14 | Assessment taking and results UI | ui |
| 3.15 | Coaching models | backend+tests |
| 3.16 | Text coaching feedback | backend+tests |
| 3.17 | Coaching UI | ui |
| 3.18 | Curated resources and retake loop | backend+tests |
| 3.19 | Messaging models | backend+tests |
| 3.20 | Messaging permissions, read state and notifications | backend+tests |
| 3.21 | Message thread UI | ui |
| 3.22 | Employer dashboard (API + UI) | backend+tests |
| 3.23 | Analytics and override rate (API + UI) | backend+tests |
| 3.24 | Job share links and embed (API + UI) | backend+tests |
| 3.25 | Interview pack generation (API + UI) | backend+tests |
| 3.26 | Interview scheduling (API + UI) | backend+tests |
| 3.27 | Interview feedback (API + UI) | backend+tests |
| 3.28 | Offer letter drafts (API + UI) | backend+tests |
| 3.29 | Employer team and roles (API + UI) | backend+tests |
| 3.30 | Admin user management and dashboard (API + UI) | backend+tests |
| 3.31 | Audit log search and CSV export (API + UI) | backend+tests |
| 3.32 | Broadcast announcements (optional) | backend+tests |
| 3.33 | Phase 3 closeout | audit |

### Phase 4: Security and production readiness

Prove each production control individually. Report every release criterion as passed, failed or not yet verified.

| ID | Batch | Type |
|---|---|---|
| 4.1 | Permission and ownership audit | audit |
| 4.2 | TOTP MFA for employer admins (API + UI) | backend+tests |
| 4.3 | Field-level encryption | backend+tests |
| 4.4 | Verify encryption in a database dump | tests |
| 4.5 | Authenticated file serving | backend+tests |
| 4.6 | Rate limits | backend+tests |
| 4.7 | Security headers and CSP verification | tests |
| 4.8 | GDPR data export (API + UI) | backend+tests |
| 4.9 | GDPR account deletion (API + UI) | backend+tests |
| 4.10 | Error reporting and PII-free logs | backend+tests |
| 4.11 | /metrics/ endpoint | backend+tests |
| 4.12 | CI hardening | infra |
| 4.13 | Payment provider abstraction (bKash/SSLCommerz) | backend+tests |
| 4.14 | Backup and restore drill | infra |
| 4.15 | Staging deploy and rollback | infra |
| 4.16 | Load test | tests |
| 4.17 | Release checklist | audit |

### Phase 5: Optional advanced features

Only after the MVP and the production controls are stable.

| ID | Batch | Type |
|---|---|---|
| 5.1 | Reconcile payment architecture | decision |
| 5.2 | Subscription state, webhooks and billing UI | backend+tests |
| 5.3 | Bengali localisation | ui |
| 5.4 | Remaining languages | ui |
| 5.5 | Installable PWA | ui |
| 5.6 | WebSocket notifications | backend+tests |

