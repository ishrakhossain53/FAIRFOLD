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

- [x] 1.1 User model characterization tests (2026-10-20, 29 passed in tests/accounts/test_user_model.py)
- [x] 1.2 Role helpers, permission classes, role-exclusivity (2026-10-20, 19 role-assignment + 36 permission tests passed; 16/16 role-matrix pairs covered)
- [x] 1.3 Registration service (2026-10-20, 34 registration + 3 password-hasher tests passed)
- [x] 1.4 Email verification tokens and email task (2026-10-20, 26 tests passed; 147 passed across batches 1.1-1.4)
- [x] 1.5 Registration and verification API (2026-10-20, 101 targeted + 363 full suite passed)
- [x] 1.6 Registration and verification UI (2026-10-20, 101 targeted + 363 full suite passed)
- [x] 1.7 Login service with lockout (2026-10-20, 18 passed in tests/accounts/test_login_service.py)
- [x] 1.8 JWT login, refresh, logout and revocation API (2026-10-20, 22 passed in tests/accounts/test_auth_tokens_api.py)
- [x] 1.9 Login, logout and access-denied UI (2026-10-20, 21 passed in tests/accounts/test_login_ui.py)
- [x] 1.10 Password reset and change (service + API) (2026-10-20, 29 passed in tests/accounts/test_password_reset.py)
- [x] 1.11 Password reset UI (2026-10-20, 12 passed in tests/accounts/test_password_reset_ui.py; 102 passed across 1.7-1.11, full suite 465 passed)
- [x] 1.12 Current-user endpoint (2026-10-20, 16 passed in tests/accounts/test_me_api.py; full suite 481 at the time, 538 after 1.14)
- [x] 1.13 Authorization matrix and security headers (2026-10-20, 34 passed in tests/core/test_authz_matrix.py + 10 in tests/core/test_security_headers.py; full suite 526 at the time, 538 after 1.14)
- [x] 1.14 Candidate profile model (2026-10-20, 12 passed in tests/candidates/test_candidate_profile_model.py; full suite 538 passed)
- [x] 1.15 Candidate profile API (2026-10-20, 23 passed in tests/candidates/test_profile_api.py; 120 targeted, full suite 591)
- [x] 1.16 Candidate onboarding and profile UI (2026-10-20, 26 passed in tests/candidates/test_profile_ui.py; 120 targeted, full suite 591)
- [x] Post-1.16 UI polish and development verification link (2026-10-20, landing page, shared account nav, password reveal on login, friendlier check-email/onboarding/profile/error pages; DEBUG-only link on the pending page and in the server log; 6 new tests, full suite 597 passed)
- [x] 1.17 S3-compatible dev storage (2026-10-22, `docker compose up -d --build --wait` -> 7 services healthy incl. `minio`, bucket `fairfold-media` created by the entrypoint, `check_storage` verified a 35-byte round-trip; 20 passed + 1 skipped in tests/core/test_storage.py against the running MinIO, full suite 614 passed / 4 skipped. Local `.env` uses the `MINIO_IMAGE` mirror override because `quay.io/minio/minio` needs `docker login quay.io`; the committed default is still quay)
- [x] 1.18 Resume model (spec first) (2026-10-22, 10 passed in tests/candidates/test_resume_model.py; full suite 632 passed / 4 skipped)
- [x] 1.19 Presigned upload API (2026-10-22, 29 passed in tests/candidates/test_resume_upload_api.py; full suite 662 passed / 4 skipped)
- [x] 1.20 Upload completion, MIME validation and ClamAV scan (2026-10-22, 33 passed in tests/candidates/test_resume_completion_api.py + test_resume_scan.py incl. 2 real-clamd tests; full suite 696 passed / 4 skipped)
- [x] 1.21 Resume list and detail API (2026-10-22, 37 passed in tests/candidates/test_resume_list_detail_api.py, 80 with the authz matrix; full suite 736 passed / 4 skipped at the time; DELETE is a hard delete audited as `resume.deleted`)
- [x] 1.22 Resume upload UI (2026-10-22, 32 passed in tests/candidates/test_resume_ui.py + 9 in tests/core/test_presign_endpoint.py; full suite 780 passed / 4 skipped; presigned URL signed for the browser host, real MinIO PUT returned 200. Browser CORS/progress remains a manual check)
- [x] 1.23 Employer profile model (2026-10-22, 13 passed in tests/employers/test_employer_profile_model.py; full suite 855 passed / 4 skipped)
- [x] 1.24 Employer onboarding API (2026-10-22, 28 passed in tests/employers/test_employer_profile_api.py, 121 with the authz matrix; full suite 855 passed / 4 skipped)
- [x] 1.25 Employer onboarding UI (2026-10-22, 29 passed in tests/employers/test_employer_onboarding_ui.py, 70 in tests/employers/; full suite 855 passed / 4 skipped)
- [x] 1.26 Job model (2026-10-24; `matching/models.py` `Job` + `matching/migrations/0001_initial.py`; 20 passed in tests/matching/test_job_application_models.py, matching/models.py 100% line coverage)
- [x] 1.27 Create draft job API (2026-10-23, 20 passed in tests/employers/test_job_create_api.py, 175 in tests/employers/ + tests/matching/ + authz matrix; full suite 971 passed / 4 skipped with the README CI env)
- [x] 1.28 Edit and delete draft jobs (2026-10-24; GET/PATCH/DELETE /api/v1/jobs/{id}/; 32 passed in tests/employers/test_job_edit_delete_api.py, 217 in tests/employers/ + authz matrix; full suite 1033 passed / 4 skipped, coverage 94% with `employers` now in the gate)
- [x] 1.29 Activate, pause and close jobs (2026-10-24; Arch Doc §4.3 transition matrix; 24 passed in tests/employers/test_job_lifecycle_api.py; full suite 1033 passed / 4 skipped)
- [x] 1.30 Employer job management UI (2026-10-24; pages #35/#36/#37 at `/employer/jobs/`, `/employer/jobs/new/`, `/employer/jobs/{id}/edit/`, `/employer/jobs/{id}/`; 54 passed in tests/employers/test_job_management_ui.py, 11 new authz matrix cases, full suite 1098 passed / 4 skipped, coverage 95%)
- [x] 1.31 Public job list and detail API (2026-10-25; `GET /api/v1/jobs/public/` + `{id}/`, `AllowAny`, active only, employer name via `show_company_name`; 28 passed in tests/employers/test_public_job_api.py)
- [x] 1.32 Search, filters, ordering and pagination (2026-10-25; `job_skills` model + migration, keyword search over title/description/skill name, location/remote/level filters, stable newest-first, `page_size` capped at 50; 33 passed in tests/employers/test_public_job_search_api.py + 5 `JobSkill` model tests)
- [x] 1.33 Public job board UI (2026-10-25; pages #4/#5 at `/jobs/` and `/jobs/{id}/`, guest/signed-in, filters, pagination, empty/error states, concealment in HTML; 29 passed in tests/employers/test_job_board_ui.py; full suite 1240 passed / 4 skipped)
- [x] 1.34 Application model (2026-10-26, model + migration already landed 2026-10-22 as a prerequisite of 2.27; 25 passed in tests/matching/test_job_application_models.py incl. duplicate, both check constraints and both cascades; full suite 1293 passed / 4 skipped)
- [x] 1.35 Per-employer candidate alias service (2026-10-26, 16 passed in tests/candidates/test_candidate_alias.py; full suite 1293 passed / 4 skipped)
- [x] 1.36 Apply to a job API (2026-10-26, 18 passed in tests/matching/test_apply_api.py; full suite 1293 passed / 4 skipped)
- [x] 1.37 Apply UI (2026-10-26, 17 passed in tests/employers/test_apply_ui.py, 29 in test_job_board_ui.py, 2 new authz rows; full suite 1293 passed / 4 skipped)
- [x] 1.38 Candidate application history API (2026-10-26, 39 passed in tests/matching/test_application_list_detail_api.py; full suite 1368 passed / 4 skipped)
- [x] 1.39 Candidate application list and detail UI (2026-10-26, 32 passed in tests/candidates/test_application_ui.py, 81 in tests/core/test_authz_matrix.py; full suite 1368 passed / 4 skipped)
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
- [ ] 2.26 Integrate the bias audit (code + tests landed 2026-10-22; my run: 950 passed, 4 skipped; awaiting your test output)
- [ ] 2.27 Store rationale with audit entry (code + tests landed 2026-10-22; my run: 950 passed, 4 skipped; awaiting your test output)
- [ ] 2.28 Evidence traceability tests (code + tests landed 2026-10-22; citation validator at 100% line coverage; awaiting your test output)
- [ ] 2.29 Rationale detail UI (page #41 rationale column built 2026-10-22; evidence, missing skills, bias status, AI mark, error/empty states; awaiting your test output)
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
