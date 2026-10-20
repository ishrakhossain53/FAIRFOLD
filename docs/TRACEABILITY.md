# Requirements traceability

One row per functional requirement — the 63 FRs, first to sixty-third — with the phase, the owning
Django app, the API route from Complete Doc §C.12, the table from Arch Doc §5.1, the current status
and the evidence path. Non-functional requirements are summarised as groups below.

## Sources and method

| Column | Source |
|---|---|
| Requirement name, Priority | Arch Doc §4.1 (the 63-row FR table). Priority vocabulary is High/Medium/Low, enforced by `verify_docs.py` |
| Phase | The requirement's own acceptance text where it names a phase; otherwise Arch Doc §10 acceptance criteria and `prd.md` §5.1 |
| Owning app | The Django app named in `prd.md` §12.3 that owns the model or service. The HTTP layer itself is the `api` app |
| API endpoint(s) | Complete Doc §C.12. Where §C.12 has no route for the requirement, the cell says so instead of inventing one |
| DB table(s) | Arch Doc §5.1 DDL (33 `CREATE TABLE` statements) |
| Status | `not started` / `partial` / `done`. `done` only when every acceptance criterion is shown by a passing test |
| Evidence path | A real file in the repository today. Blank for `not started` |
| Planned batch | Left blank on purpose; filled when a batch is scheduled. The schedule itself lives in `docs/ROADMAP.md` |

**Count invariant.** This table has exactly 63 rows and 63 distinct FR ids, one row per line, and no
other line in this file holds a full FR id, so a count of lines carrying the FR-id prefix equals 63.
Nothing here edits requirement text. `scripts/verify_docs.py` is **not** wired to this file, so this
table must not be used to satisfy the §4.1 row-count check — that check reads the Arch Doc itself.

## Functional requirements

| FR | Requirement | Priority | Phase | Owning app | API endpoint(s) (Complete Doc §C.12) | DB table(s) (Arch Doc §5.1) | Status | Evidence path | Planned batch |
|---|---|---|---|---|---|---|---|---|---|
| REQ-FR-001 | User Registration | High | 1 | accounts | POST /api/v1/auth/register/; POST /api/v1/auth/verify-email/; POST /api/v1/auth/verify-email/resend/ | users | done | accounts/services.py — `register_user` (1.3), `make_verification_token`/`verify_email`/`resend_verification_email` (1.4); accounts/tasks.py — `send_verification_email`; accounts/serializers.py + accounts/api_views.py + accounts/auth_urls.py — the three endpoints (1.5); accounts/forms.py + accounts/views.py + accounts/public_urls.py + templates/accounts/ — pages #6 (register) and #11 (pending, verified, expired, invalid, resend) (1.6); tests/accounts/test_registration.py, tests/accounts/test_email_verification.py, tests/accounts/test_auth_api.py, tests/accounts/test_registration_ui.py — 363 passed at acceptance |  |
| REQ-FR-002 | User Login | High | 1 | accounts | POST /api/v1/auth/login/ | users | done | accounts/services.py — `authenticate_with_lockout` is the single credential check (1.7); accounts/api_views.py — `LoginView` returns the 15-min access + 7-day refresh pair (1.8); accounts/views.py — `login_view` uses session auth for the pages (D-1, 1.9); config/settings/base.py — `SIMPLE_JWT` (D-7); tests/accounts/test_login_service.py, tests/accounts/test_auth_tokens_api.py, tests/accounts/test_login_ui.py |  |
| REQ-FR-003 | Account Lockout | High | 1 | accounts | POST /api/v1/auth/login/ | users | done | accounts/services.py — `MAX_FAILED_LOGIN_ATTEMPTS=5`, `LOCKOUT_DURATION=15m`, `AccountLocked`, counter reset on success and after expiry, `account_locked` audit row (1.7); accounts/views.py + templates/accounts/login.html — lockout state with the mm:ss countdown (1.9); tests/accounts/test_login_service.py (frozen clock: lock, expiry, reset, audit), tests/accounts/test_auth_tokens_api.py (423 + `retry_after`), tests/accounts/test_login_ui.py (alert state) |  |
| REQ-FR-004 | Password Recovery | High | 1 | accounts | POST /api/v1/auth/password/reset/; POST /api/v1/auth/password/reset/confirm/; POST /api/v1/auth/password/change/ | users | done | accounts/services.py — `make_password_reset_token`, `reset_password`, `change_password`, lockout clear + refresh-token revocation (1.10); accounts/tasks.py — `send_password_reset_email`; config/settings/base.py — `PASSWORD_RESET_TIMEOUT=3600`; accounts/api_views.py + accounts/auth_urls.py; accounts/views.py + templates/accounts/forgot_password.html, reset_password.html (1.11); tests/accounts/test_password_reset.py, tests/accounts/test_password_reset_ui.py |  |
| REQ-FR-005 | MFA Enable | Medium | 4 | accounts | POST /api/v1/auth/mfa/enable/ | users | not started |  |  |
| REQ-FR-006 | MFA Verification | Medium | 4 | accounts | POST /api/v1/auth/mfa/verify/ | users | not started |  |  |
| REQ-FR-007 | JWT Token Refresh | High | 1 | accounts | POST /api/v1/auth/refresh/ | users | done | config/settings/base.py — 15-min access, 7-day refresh, `ROTATE_REFRESH_TOKENS` + `BLACKLIST_AFTER_ROTATION`, token_blacklist installed (D-7); accounts/api_views.py — `RefreshView`; tests/accounts/test_auth_tokens_api.py — rotates the pair, old refresh returns 401, access lifetime asserted at 900 s |  |
| REQ-FR-008 | JWT Token Revocation | Medium | 1 | accounts | POST /api/v1/auth/logout/ | users | done | accounts/api_views.py — `LogoutView` blacklists the refresh token (1.8); accounts/services.py — `_revoke_refresh_tokens` on password reset (1.10); tests/accounts/test_auth_tokens_api.py — logout 204 then refresh 401; tests/accounts/test_password_reset.py — reset blacklists outstanding tokens |  |
| REQ-FR-009 | Candidate Profile Creation | High | 1 | candidates | GET /api/v1/candidates/me/; PATCH /api/v1/candidates/me/ | candidate_profiles | not started |  |  |
| REQ-FR-010 | Resume Upload via Presigned URL | High | 1 | candidates | POST /api/v1/candidates/resumes/; GET /api/v1/candidates/resumes/{id}/ | candidate_resumes | not started |  |  |
| REQ-FR-011 | Resume PII Stripping | High | 2 | ai | POST /api/v1/candidates/resumes/{id}/process/ | candidate_resumes | not started |  |  |
| REQ-FR-012 | Resume Text Extraction | High | 2 | ai | POST /api/v1/candidates/resumes/{id}/process/ | candidate_resumes | not started |  |  |
| REQ-FR-013 | Resume Embedding Generation | High | 2 | ai | POST /api/v1/candidates/resumes/{id}/process/ | candidate_profiles (`resume_embedding VECTOR(384)`) | not started |  |  |
| REQ-FR-014 | Skill Management | High | 3 | candidates | GET/POST /api/v1/candidates/skills/; PATCH/DELETE /api/v1/candidates/skills/{id}/ | candidate_skills; skills | not started |  |  |
| REQ-FR-015 | Skill Deduplication | Medium | 3 | core | (none in §C.12) | skills | partial | core.Skill model, migration and core/fixtures/skills.json exist; no alias mapping |  |
| REQ-FR-016 | Journey Mapping — Timeline | High | 3 | journey | GET /api/v1/candidates/journey/ | candidate_profiles (`journey_timeline JSONB`) | not started |  |  |
| REQ-FR-017 | Journey Mapping — Skill Evolution | Medium | 3 | journey | GET /api/v1/candidates/journey/ | candidate_profiles; candidate_skills | not started |  |  |
| REQ-FR-018 | Journey Mapping — Dynamic Storytelling | Medium | 3 | journey | POST /api/v1/candidates/journey/regenerate/ | candidate_profiles; applications | not started |  |  |
| REQ-FR-019 | Assessment Taking | Medium | 3 | assessments | GET /api/v1/candidates/assessments/; POST /api/v1/candidates/assessments/{id}/start/; POST /api/v1/candidates/assessments/{id}/answer/ | assessments; assessment_questions; assessment_attempts | not started |  |  |
| REQ-FR-020 | Assessment Auto-Scoring | Medium | 3 | assessments | POST /api/v1/candidates/assessments/{id}/answer/ | assessment_attempts | not started |  |  |
| REQ-FR-021 | Interview Coaching | Medium | 3 | interviews | POST /api/v1/coaching/sessions/ | interview_coaching_sessions | not started |  |  |
| REQ-FR-022 | Job Application | High | 1 | candidates | (none in §C.12 — no apply route; see gap note 1) | applications | not started |  |  |
| REQ-FR-023 | Application Status Tracking | High | 1 | employers | GET /api/v1/candidates/applications/; GET /api/v1/candidates/applications/{id}/; GET /api/v1/jobs/{id}/applications/ | applications | not started |  |  |
| REQ-FR-024 | Match Score Visibility | High | 2 | matching | GET /api/v1/candidates/applications/{id}/ | applications; candidate_profiles | not started |  |  |
| REQ-FR-025 | Job Creation | High | 1 | employers | POST /api/v1/jobs/ | jobs | not started |  |  |
| REQ-FR-026 | Job Editing | High | 1 | employers | PATCH /api/v1/jobs/{id}/ | jobs | not started |  |  |
| REQ-FR-027 | Job Activation | High | 1 | employers | POST /api/v1/jobs/{id}/activate/ | jobs | not started |  |  |
| REQ-FR-028 | AI Screening Trigger | High | 2 | matching | POST /api/v1/jobs/{id}/screen/ | applications | not started |  |  |
| REQ-FR-029 | Screening Result Display | High | 2 | matching | GET /api/v1/jobs/{id}/applications/; POST /api/v1/applications/{id}/review/ | applications | not started |  |  |
| REQ-FR-030 | Evidence-Cited Rationale | High | 2 | ai | GET /api/v1/jobs/{id}/applications/; GET /api/v1/candidates/applications/{id}/ | applications; audit_log_entries | partial | ai/bias_pass.py, ai/bias_audit.py, tests/bias/test_bias_pass.py, tests/bias/test_bias_audit.py — bias audit only; no rationale generation or evidence-citation test |  |
| REQ-FR-031 | Interview Pack Generation | Medium | 3 | interviews | POST /api/v1/jobs/{id}/interview-pack/; GET /api/v1/interviews/{id}/pack/ | interview_packs | not started |  |  |
| REQ-FR-032 | Interview Scheduling | Medium | 3 | interviews | POST /api/v1/interviews/ | interviews | not started |  |  |
| REQ-FR-033 | Interview Feedback | Medium | 3 | interviews | POST /api/v1/interviews/{id}/feedback/ | interview_feedback | not started |  |  |
| REQ-FR-034 | Offer Generation | Low | 3 | employers | (none in §C.12) | (no offer table in §5.1; see gap note 2) | not started |  |  |
| REQ-FR-035 | Analytics Dashboard | Medium | 3 | employers | GET /api/v1/jobs/{id}/analytics/; GET /api/v1/jobs/{id}/analytics/override-rate/ | applications; audit_log_entries | not started |  |  |
| REQ-FR-036 | Job Sharing | Medium | 3 | employers | POST /api/v1/jobs/{id}/share/ | jobs | not started |  |  |
| REQ-FR-037 | Admin Dashboard | Medium | 3 | core | GET /api/v1/admin/dashboard/ | users; jobs; applications | not started |  |  |
| REQ-FR-038 | User Management | High | 3 | core | GET /api/v1/admin/users/ | users | partial | `accounts.permissions.IsPlatformAdmin` and `IsEmployerAdmin` exist and are tested against all four seeded roles in tests/accounts/test_permissions.py (batch 1.2); missing: admin user list, filtering, role editing, lockout/reset actions |  |
| REQ-FR-039 | Audit Log Search | High | 3 | core | GET /api/v1/admin/audit-log/ | audit_log_entries | partial | core.AuditLogEntry model and migration exist; no search logic, filtering or CSV export |  |
| REQ-FR-040 | Data Export (GDPR) | High | 4 | core | POST /api/v1/gdpr/export/; GET /api/v1/gdpr/export/{id}/; GET /api/v1/gdpr/export/{id}/download/ | data_export_requests | not started |  |  |
| REQ-FR-041 | Account Deletion (GDPR) | High | 4 | core | POST /api/v1/gdpr/deletion/; GET /api/v1/gdpr/deletion/{id}/; POST /api/v1/gdpr/deletion/{id}/cancel/ | data_deletion_requests | not started |  |  |
| REQ-FR-042 | Job Browse and Search | High | 1 | employers | GET /api/v1/jobs/public/; GET /api/v1/jobs/public/{id}/ | jobs; job_skills (D-6c); employer_profiles (`show_company_name`) | not started |  |  |
| REQ-FR-043 | Candidate–Employer Messaging | Medium | 3 | notifications | GET /api/v1/messages/; POST /api/v1/messages/; GET /api/v1/notifications/ | messages; notifications | not started |  |  |
| REQ-FR-044 | Certification Management | Medium | 3 | candidates | GET /api/v1/candidates/certifications/; POST /api/v1/candidates/certifications/ | certifications | not started |  |  |
| REQ-FR-045 | Employer Company Profile | High | 1 | employers | GET /api/v1/employers/me/; PATCH /api/v1/employers/me/ | employer_profiles | partial | `accounts.services.assign_role` enforces candidate/employer mutual exclusivity, tested in both directions for every conflicting pair in tests/accounts/test_role_assignment.py (batch 1.2); missing: `EmployerProfile` model, onboarding endpoints, and the activation guard |  |
| REQ-FR-046 | Employer Dashboard | Medium | 3 | employers | (none in §C.12) | jobs; applications; subscriptions | not started |  |  |
| REQ-FR-047 | Employer Team and Roles | Medium | 3 | employers | GET /api/v1/employers/team/; POST /api/v1/employers/team/invite/; POST /api/v1/employers/team/{id}/role/; DELETE /api/v1/employers/team/{id}/; POST /api/v1/employers/team/invitations/{token}/accept/; DELETE /api/v1/employers/team/invitations/{id}/ | employer_team_members | not started |  |  |
| REQ-FR-048 | Billing and Plan Management | Medium | 5 | employers | (none in §C.12) | subscriptions; payments | not started |  |  |
| REQ-FR-049 | Assessment Management | Medium | 3 | assessments | GET/POST /api/v1/assessments/; GET/PATCH /api/v1/assessments/{id}/; POST /api/v1/assessments/{id}/questions/; PATCH/DELETE /api/v1/assessments/{id}/questions/{qid}/; POST /api/v1/assessments/{id}/reorder/; POST /api/v1/assessments/{id}/activate/; POST /api/v1/assessments/{id}/deactivate/ | assessments; assessment_questions | not started |  |  |
| REQ-FR-050 | Broadcast Announcement | Low | 4 | notifications | GET/POST /api/v1/admin/announcements/; POST /api/v1/admin/announcements/resolve-audience/; POST /api/v1/admin/announcements/{id}/send/; POST /api/v1/admin/announcements/{id}/cancel/ | announcements | not started |  |  |
| REQ-FR-051 | Employer-Required Skill Assessment | High | 3 | assessments | GET/POST /api/v1/jobs/{id}/required-assessments/; DELETE /api/v1/jobs/{id}/required-assessments/{req_id}/; POST /api/v1/applications/{id}/shortlist/ | job_assessment_requirements; assessment_attempts; applications | not started |  |  |
| REQ-FR-052 | Override Visibility and Record | High | 2 | matching | POST /api/v1/applications/{id}/shortlist/; POST /api/v1/applications/{id}/reject/ | applications; audit_log_entries | not started |  |  |
| REQ-FR-053 | Paid discovery only — no ranking influence | High | 2 | matching | GET /api/v1/jobs/{id}/applications/; GET /api/v1/jobs/public/ | candidate_profiles (`visibility_tier`, `is_promoted`); audit_log_entries | not started |  |  |
| REQ-FR-054 | Per-employer candidate alias | High | 2 | candidates | GET /api/v1/jobs/{id}/applications/ | candidate_aliases; applications | not started |  |  |
| REQ-FR-055 | Assessment integrity events | Medium | 3 | assessments | POST /api/v1/candidates/assessments/{id}/answer/ (no dedicated integrity route in §C.12) | assessment_integrity_events; assessment_attempts | not started |  |  |
| REQ-FR-056 | Local payment providers (bKash, SSLCommerz) | High | 4 | employers | (none in §C.12) | payments; subscriptions | not started |  |  |
| REQ-FR-057 | Expanded PII and proxy stripping | High | 2 | ai | POST /api/v1/candidates/resumes/{id}/process/ | candidate_resumes | not started |  |  |
| REQ-FR-058 | Text-only interview practice | Medium | 3 | interviews | GET/POST /api/v1/practice-questions/; POST /api/v1/coaching/sessions/ | practice_questions; interview_coaching_sessions | not started |  |  |
| REQ-FR-059 | STAR rubric grading with cited feedback | Medium | 3 | interviews | POST /api/v1/coaching/sessions/; GET/POST /api/v1/jobs/{id}/scorecard-criteria/ | interview_coaching_sessions; scorecard_criteria | not started |  |  |
| REQ-FR-060 | Coaching practice isolation | Medium | 3 | interviews | POST/GET /api/v1/coaching/sessions/ | interview_coaching_sessions | not started |  |  |
| REQ-FR-061 | Training gap resources | Medium | 3 | assessments | GET /api/v1/resources/; POST /api/v1/assessments/{id}/recommend-resources/ | resources; attempt_resource_recommendations | not started |  |  |
| REQ-FR-062 | Coaching evaluation set | Low | 3 | interviews | POST /api/v1/coaching/rate/ | interview_coaching_sessions | not started |  |  |
| REQ-FR-063 | Assessment → Resource → Retake loop | Low | 3 | assessments | GET /api/v1/assessments/{id}/retake-eligible/; POST /api/v1/assessments/{id}/recommend-resources/ | attempt_resource_recommendations; assessment_attempts; candidate_skills | not started |  |  |

### Column notes

- **Owning app** is the app expected to hold the model or service. Where the spec does not name an
  owner, the closest existing app from `prd.md` §12.3 is used and the ambiguity is listed under
  Observations — it is a build-planning hint, not a requirement.
- **Phase** for the coaching and screening-integrity requirements (FR-051 to FR-063) is taken from
  the phase named inside their own acceptance text; for the rest it is Arch Doc §10 and `prd.md`
  §5.1. Two requirements carry a range (FR-052 is written "Phase 2–3"); the earlier end is used, and
  the range is recorded here.

## Non-functional requirement groups

Counts are the four families in Arch Doc §4.2: 14 + 9 + 23 + 4 = the documented 50 NFRs. The batch
brief named three groups; the canonical set is four, and `verify_docs.py` checks all four.

| Group | Family | Count | Phase | Verification method |
|---|---|---|---|---|
| REQ-SEC | Security | 14 | 1 (CSRF, XSS, SQLi, session, JWT) → 4 (encryption, rate limits, MFA, headers audit) | tests/security/ (RBAC, rate limiting, data encryption); `bandit`; `pip-audit`; ZAP scan; `manage.py check --deploy`; the PII-leak test (REQ-SEC-002) |
| REQ-NFR | Performance, scalability, availability, maintainability | 23 | 2 (processing/screening timings) → 4 (load, DR, monitoring) | tests/load/test_concurrent_apply.py and test_ai_screening.py; measured benchmarks (embedding < 10 s, screening < 5 min per 100); `pytest --cov-fail-under=80`; black/isort/flake8/mypy |
| REQ-COM | Compliance | 9 | 2 (audit trail) → 4 (GDPR, accessibility, EU AI Act evidence) | tests/integration/test_compliance.py (export/delete end-to-end); tests/accessibility/test_wcag.py (axe-core); the versioned bias test set for the EU AI Act evidence |
| REQ-NFOR | Operability | 4 | 4 → 5 | tests/core/test_production_settings.py; Sentry configuration (REQ-NFOR-024); the deploy/rollback drill (batch 4.15); backup/restore drill (batch 4.14) |

## Phase 3 release criteria and the validation gate

`prd.md` §20 lists ten release conditions. Nine are engineering gates covered by Phases 1–4. Item 10
is a **product validation gate** that sits in front of the Phase 3 build:

- Employer hypotheses H-EM-001 to H-EM-005 must each reach their "Go" threshold in
  `validation/decision_rules.md`; ≥5 recruiter interviews; willingness-to-pay viable (Starter
  ≤1000 BDT).
- The thresholds were to be locked by 2026-10-20 and cannot reference interview results once set.
- If 1–2 hypotheses land in "Adjust", the Phase 3 scope is reduced (candidate files suggest making
  the assessment gate optional rather than required); if ≥3 land in "Stop", the project pauses.

**Effect on build order.** The validation gate precedes the Phase 3 features that depend on it most
directly — the assessment gate (FR-051), integrity signals (FR-055) and the coaching/resource set
(FR-058 to FR-063). Those should not be committed until the gate returns "Go", or the adjusted scope
is agreed in writing. Phases 1–2 and the non-AI parts of Phase 3 (skills, journey, messaging,
employer dashboard) are not gated by it.

## Gap notes

1. **Apply route absent from §C.12.** FR-022 (Job Application) needs a candidate-facing create route.
   §C.12 lists only `GET /api/v1/candidates/applications/` and `.../{id}/`; there is no `POST`. Batch
   1.36 ("Apply to a job API") is scheduled to build it. The endpoint must be added to the API list
   first (spec-first), as the Arch Doc §4.1 note already requires. Unlike D-3 (email-verification
   endpoints), which batch 0.5 resolved by adding `verify-email/` and `verify-email/resend/` to
   §C.12, this one is still open.
2. **Offer Generation has no backing object.** FR-034 names an AI-drafted offer letter, but §5.1 has
   no offer table and §C.12 has no route. Needs a spec decision before it can be built.
3. **Employer dashboard, billing and payments have no §C.12 route** (FR-046, FR-048, FR-056). The
   models exist in the DDL; the routes do not.
4. **No owning app is defined for the coaching tables.** `practice_questions`,
   `interview_coaching_sessions`, `scorecard_criteria`, `resources` and
   `attempt_resource_recommendations` appear in §5.1, but `prd.md` §12.3 lists no coaching or
   resources app. This table tentatively assigns them to `interviews` and `assessments`; the owner
   should be fixed in batch 0.5 with the other D-series schema decisions.
