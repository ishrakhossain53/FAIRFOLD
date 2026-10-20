# Progress

One line per batch. Update this file at the end of every batch, with verified facts only.

Legend: `[ ]` not started, `[~]` pre-filled or in progress, `[x]` done and verified by tests you ran, `[!]` blocked (give the reason).

Other places to update after each batch: `docs/TRACEABILITY.md` (requirement status) and `HISTORY.md` (dated entry under `## 7. Batch log`).

## Phase 0: Reconcile, baseline, decide

- [x] 0.1 Reconcile repo state against HISTORY.md . 2026-10-19: verified against the real repo on branch `0.0-ready-to-began`; 3 models + 2 migrations confirmed (`manage.py check` clean, no migration drift), **115/115 tests pass** with `DEBUG` unset, endpoints probed (see docs/AUDIT.md)
- [x] 0.2 Baseline run (Docker, tests, lint, docs checks) . 2026-10-19: `docker compose up -d --wait`, `manage.py check`, `pytest tests/ -v`, docs checks, and endpoint probes all succeeded; 115/115 tests passed, with only the documented pre-existing formatter/Bandit compatibility warnings
- [ ] 0.3 Requirements traceability table (pending my test output)
- [ ] 0.4 Propose decisions D-1 to D-8 (no code)
- [ ] 0.5 Apply the accepted decisions to specs and settings (pending my test output)

## Phase 1: Core recruitment platform (no AI)

- [ ] 1.1 User model characterization tests
- [ ] 1.2 Role helpers, permission classes, role-exclusivity (pending my test output)
- [ ] 1.3 Registration service
- [ ] 1.4 Email verification tokens and email task (pending my test output)
- [ ] 1.5 Registration and verification API
- [ ] 1.6 Registration and verification UI
- [ ] 1.7 Login service with lockout
- [ ] 1.8 JWT login, refresh, logout and revocation API
- [ ] 1.9 Login, logout and access-denied UI
- [ ] 1.10 Password reset and change (service + API)
- [ ] 1.11 Password reset UI
- [ ] 1.12 Current-user endpoint
- [ ] 1.13 Authorization matrix and security headers
- [ ] 1.14 Candidate profile model
- [ ] 1.15 Candidate profile API
- [ ] 1.16 Candidate onboarding and profile UI
- [ ] 1.17 S3-compatible dev storage
- [ ] 1.18 Resume model (spec first)
- [ ] 1.19 Presigned upload API
- [ ] 1.20 Upload completion, MIME validation and ClamAV scan
- [ ] 1.21 Resume list and detail API
- [ ] 1.22 Resume upload UI
- [ ] 1.23 Employer profile model
- [ ] 1.24 Employer onboarding API
- [ ] 1.25 Employer onboarding UI
- [ ] 1.26 Job model
- [ ] 1.27 Create draft job API
- [ ] 1.28 Edit and delete draft jobs
- [ ] 1.29 Activate, pause and close jobs
- [ ] 1.30 Employer job management UI
- [ ] 1.31 Public job list and detail API
- [ ] 1.32 Search, filters, ordering and pagination
- [ ] 1.33 Public job board UI
- [ ] 1.34 Application model
- [ ] 1.35 Per-employer candidate alias service
- [ ] 1.36 Apply to a job API
- [ ] 1.37 Apply UI
- [ ] 1.38 Candidate application history API
- [ ] 1.39 Candidate application list and detail UI
- [ ] 1.40 Employer application inbox API
- [ ] 1.41 Application status actions
- [ ] 1.42 Employer application review UI
- [ ] 1.43 Notification model and delivery
- [ ] 1.44 Notification list and unread UI
- [ ] 1.45 Phase 1 end-to-end test
- [ ] 1.46 Phase 1 closeout

## Phase 2: AI screening pipeline

- [ ] 2.1 Resume processing states (spec first)
- [ ] 2.2 PDF text extraction service
- [ ] 2.3 Extraction edge cases
- [ ] 2.4 Process endpoint and Celery task
- [ ] 2.5 Extraction status UI
- [ ] 2.6 PII test dataset and accuracy harness
- [ ] 2.7 Deterministic PII redaction
- [ ] 2.8 NER and proxy stripping
- [ ] 2.9 Persist sanitised text and audit the strip
- [ ] 2.10 Bias test set v1.0.2 (proxy cases)
- [ ] 2.11 Embedding service
- [ ] 2.12 pgvector columns and migration
- [ ] 2.13 Resume embedding task
- [ ] 2.14 Job embedding task
- [ ] 2.15 Similarity and deterministic ranking fixtures
- [ ] 2.16 Hard-filter rules and versioning
- [ ] 2.17 rank_applications service
- [ ] 2.18 Reviewable not_matched candidates
- [ ] 2.19 Ranked applications API
- [ ] 2.20 Ranked results UI
- [ ] 2.21 AIProvider abstraction and OpenRouter client
- [ ] 2.22 Offline fallback and provider-error handling
- [ ] 2.23 Outbound PII gate
- [ ] 2.24 Rationale schema and validation
- [ ] 2.25 Rationale generation for one application
- [ ] 2.26 Integrate the bias audit
- [ ] 2.27 Store rationale with audit entry
- [ ] 2.28 Evidence traceability tests
- [ ] 2.29 Rationale detail UI
- [ ] 2.30 Decide where screening-run state lives (spec first)
- [ ] 2.31 Server-side cost estimator
- [ ] 2.32 Preflight and explicit confirmation
- [ ] 2.33 Batch screening task
- [ ] 2.34 Progress, failure and retry states
- [ ] 2.35 Screening UI
- [ ] 2.36 Screening end-to-end test
- [ ] 2.37 Override rule and reason (REQ-FR-052)
- [ ] 2.38 Override dialog UI
- [ ] 2.39 Controlled identity reveal at shortlist
- [ ] 2.40 Candidate sees match score and evidence
- [ ] 2.41 Bias flags and warnings in the recruiter UI
- [ ] 2.42 Review of not_matched in the UI
- [ ] 2.43 Phase 2 closeout and capacity check

## Phase 3: Candidate AI features and remaining workflows

- [ ] 3.1 Skill catalog and alias mapping
- [ ] 3.2 Candidate skills API and UI
- [ ] 3.3 Certification management
- [ ] 3.4 Structured education and career records
- [ ] 3.5 Career timeline (data + UI)
- [ ] 3.6 Skill evolution chart
- [ ] 3.7 Job-specific narrative
- [ ] 3.8 Assessment models
- [ ] 3.9 Assessment authoring (API + UI)
- [ ] 3.10 Attach a required assessment to a job
- [ ] 3.11 Gate computation and shortlist block (backend)
- [ ] 3.12 Gate status UI
- [ ] 3.13 Assessment attempts (backend)
- [ ] 3.14 Assessment taking and results UI
- [ ] 3.15 Coaching models
- [ ] 3.16 Text coaching feedback
- [ ] 3.17 Coaching UI
- [ ] 3.18 Curated resources and retake loop
- [ ] 3.19 Messaging models
- [ ] 3.20 Messaging permissions, read state and notifications
- [ ] 3.21 Message thread UI
- [ ] 3.22 Employer dashboard (API + UI)
- [ ] 3.23 Analytics and override rate (API + UI)
- [ ] 3.24 Job share links and embed (API + UI)
- [ ] 3.25 Interview pack generation (API + UI)
- [ ] 3.26 Interview scheduling (API + UI)
- [ ] 3.27 Interview feedback (API + UI)
- [ ] 3.28 Offer letter drafts (API + UI)
- [ ] 3.29 Employer team and roles (API + UI)
- [ ] 3.30 Admin user management and dashboard (API + UI)
- [ ] 3.31 Audit log search and CSV export (API + UI)
- [ ] 3.32 Broadcast announcements (optional)
- [ ] 3.33 Phase 3 closeout

## Phase 4: Security and production readiness

- [ ] 4.1 Permission and ownership audit
- [ ] 4.2 TOTP MFA for employer admins (API + UI)
- [ ] 4.3 Field-level encryption
- [ ] 4.4 Verify encryption in a database dump
- [ ] 4.5 Authenticated file serving
- [ ] 4.6 Rate limits
- [ ] 4.7 Security headers and CSP verification
- [ ] 4.8 GDPR data export (API + UI)
- [ ] 4.9 GDPR account deletion (API + UI)
- [ ] 4.10 Error reporting and PII-free logs
- [ ] 4.11 /metrics/ endpoint
- [ ] 4.12 CI hardening
- [ ] 4.13 Payment provider abstraction (bKash/SSLCommerz)
- [ ] 4.14 Backup and restore drill
- [ ] 4.15 Staging deploy and rollback
- [ ] 4.16 Load test
- [ ] 4.17 Release checklist

## Phase 5: Optional advanced features

- [ ] 5.1 Reconcile payment architecture
- [ ] 5.2 Subscription state, webhooks and billing UI
- [ ] 5.3 Bengali localisation
- [ ] 5.4 Remaining languages
- [ ] 5.5 Installable PWA
- [ ] 5.6 WebSocket notifications
