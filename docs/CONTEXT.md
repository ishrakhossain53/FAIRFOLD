# Context (read this first)

Generated 2026-11-11. A condensed index over the canonical docs. **Read `CLAUDE.md` in full**
for the operating rules, the privacy/fairness invariants, the repo conventions and the commands —
those are not repeated here. Open a canonical doc only for the section a batch cites (use the
`grep` / `sed` commands below); never read `HISTORY.md`, `design.md`, `prd.md` or the Feasibility
doc whole.

## Product (5 lines)

1. FairFold is an AI-powered, **explainable** recruitment platform.
2. Stack: Django 5.2 monolith, DRF + JWT (simplejwt), Django templates + HTMX (AD-002), Celery + Redis, PostgreSQL 17 + pgvector, Docker Compose.
3. AI screening is **advisory** — a human always decides, every action is audited.
4. Candidate identity stays hidden from employers until shortlist (per-employer alias, REQ-FR-029/054).
5. Canonical sources: Arch Doc (requirements §4.1, DDL §5.1, ADRs, acceptance §10) and Complete Doc (API §C.12, migration/seed §C.8).

## Functional requirements (63 REQ-FR)

Status from `docs/TRACEABILITY.md` (done / partial / not started). Batches that name the FR in
their "Requirement and source refs" line (a blank means no batch spec cites it yet).

| ID | Requirement | Status | Batches |
|---|---|---|---|
| REQ-FR-001 | User Registration | done | 0.03, 1.01, 1.03, 1.04, 1.05, 1.06 |
| REQ-FR-002 | User Login | done | 1.04, 1.07, 1.08, 1.09 |
| REQ-FR-003 | Account Lockout | done | 1.01, 1.07 |
| REQ-FR-004 | Password Recovery | done | 1.10, 1.11 |
| REQ-FR-005 | MFA Enable | not started | 4.02 |
| REQ-FR-006 | MFA Verification | not started | 4.02 |
| REQ-FR-007 | JWT Token Refresh | done | 1.08 |
| REQ-FR-008 | JWT Token Revocation | done | 1.08 |
| REQ-FR-009 | Candidate Profile Creation | done | 1.14, 1.15, 1.16 |
| REQ-FR-010 | Resume Upload via Presigned URL | partial | 1.17, 1.18, 1.19, 1.21, 1.22 |
| REQ-FR-011 | Resume PII Stripping | not started | 2.01, 2.06, 2.07, 2.09 |
| REQ-FR-012 | Resume Text Extraction | partial | 1.18, 2.01, 2.02, 2.03, 2.04, 2.05 |
| REQ-FR-013 | Resume Embedding Generation | not started | 2.11, 2.12, 2.13, 2.14 |
| REQ-FR-014 | Skill Management | not started | 3.02 |
| REQ-FR-015 | Skill Deduplication | partial | 3.01 |
| REQ-FR-016 | Journey Mapping — Timeline | not started | 3.04, 3.05 |
| REQ-FR-017 | Journey Mapping — Skill Evolution | not started | 3.06 |
| REQ-FR-018 | Journey Mapping — Dynamic Storytelling | not started | 3.07 |
| REQ-FR-019 | Assessment Taking | not started | 3.08, 3.13, 3.14 |
| REQ-FR-020 | Assessment Auto-Scoring | not started | |
| REQ-FR-021 | Interview Coaching | not started | 3.16 |
| REQ-FR-022 | Job Application | done | 1.34, 1.36, 1.37, 1.43 |
| REQ-FR-023 | Application Status Tracking | partial | 1.38, 1.39, 1.41, 1.43, 1.44 |
| REQ-FR-024 | Match Score Visibility | not started | 2.40 |
| REQ-FR-025 | Job Creation | partial | 1.26, 1.27, 1.30, 2.14 |
| REQ-FR-026 | Job Editing | done | 1.28 |
| REQ-FR-027 | Job Activation | done | 1.29 |
| REQ-FR-028 | AI Screening Trigger | not started | 2.30, 2.31, 2.32, 2.33, 2.34, 2.35 |
| REQ-FR-029 | Screening Result Display | partial | 1.40, 1.42, 2.18, 2.19, 2.20, 2.29, 2.39, 2.42 |
| REQ-FR-030 | Evidence-Cited Rationale | partial | 2.21, 2.24, 2.25, 2.27, 2.28, 2.29 |
| REQ-FR-031 | Interview Pack Generation | not started | 3.25 |
| REQ-FR-032 | Interview Scheduling | not started | 3.26 |
| REQ-FR-033 | Interview Feedback | not started | 3.27 |
| REQ-FR-034 | Offer Generation | not started | 3.28 |
| REQ-FR-035 | Analytics Dashboard | not started | 3.23 |
| REQ-FR-036 | Job Sharing | not started | 3.24 |
| REQ-FR-037 | Admin Dashboard | not started | 3.30 |
| REQ-FR-038 | User Management | partial | 1.02, 3.30 |
| REQ-FR-039 | Audit Log Search | partial | 3.31 |
| REQ-FR-040 | Data Export (GDPR) | not started | 4.08 |
| REQ-FR-041 | Account Deletion (GDPR) | not started | 4.09 |
| REQ-FR-042 | Job Browse and Search | done | 1.31, 1.32, 1.33 |
| REQ-FR-043 | Candidate–Employer Messaging | not started | 3.19, 3.20, 3.21 |
| REQ-FR-044 | Certification Management | not started | 3.03 |
| REQ-FR-045 | Employer Company Profile | partial | 1.02, 1.23, 1.24, 1.25, 1.29 |
| REQ-FR-046 | Employer Dashboard | not started | 3.22 |
| REQ-FR-047 | Employer Team and Roles | not started | 3.29 |
| REQ-FR-048 | Billing and Plan Management | not started | 5.01, 5.02 |
| REQ-FR-049 | Assessment Management | not started | 3.09 |
| REQ-FR-050 | Broadcast Announcement | not started | 3.32 |
| REQ-FR-051 | Employer-Required Skill Assessment | partial | 3.10, 3.11, 3.12 |
| REQ-FR-052 | Override Visibility and Record | partial | 1.41, 2.37, 2.38, 3.23 |
| REQ-FR-053 | Paid discovery only — no ranking influence | not started | 2.17 |
| REQ-FR-054 | Per-employer candidate alias | partial | 1.35, 1.40, 2.19, 2.39 |
| REQ-FR-055 | Assessment integrity events | not started | |
| REQ-FR-056 | Local payment providers (bKash, SSLCommerz) | not started | 4.13, 5.01 |
| REQ-FR-057 | Expanded PII and proxy stripping | not started | 2.06, 2.07, 2.08 |
| REQ-FR-058 | Text-only interview practice | not started | 3.15, 3.17 |
| REQ-FR-059 | STAR rubric grading with cited feedback | not started | |
| REQ-FR-060 | Coaching practice isolation | not started | |
| REQ-FR-061 | Training gap resources | not started | 3.18 |
| REQ-FR-062 | Coaching evaluation set | not started | |
| REQ-FR-063 | Assessment → Resource → Retake loop | not started | |

## Table index (Arch Doc §5.1 — 33 tables)

Each grep prints exactly that table's definition. DDL lives in
`FAIRFOLD_Project_Architecture_and_Requirements.md`.

| Table | Purpose | Print just that table |
|---|---|---|
| users | Custom auth user (UUID pk, email login, lockout) | `grep -n -A17 "CREATE TABLE users" FAIRFOLD_Project_Architecture_and_Requirements.md` |
| candidate_profiles | Candidate profile + embeddings + visibility | `grep -n -A15 "CREATE TABLE candidate_profiles" FAIRFOLD_Project_Architecture_and_Requirements.md` |
| candidate_resumes | Resume upload / processing state | `grep -n -A15 "CREATE TABLE candidate_resumes" FAIRFOLD_Project_Architecture_and_Requirements.md` |
| employer_profiles | Employer company profile | `grep -n -A13 "CREATE TABLE employer_profiles" FAIRFOLD_Project_Architecture_and_Requirements.md` |
| employer_team_members | Employer team membership + roles | `grep -n -A13 "CREATE TABLE employer_team_members" FAIRFOLD_Project_Architecture_and_Requirements.md` |
| subscriptions | Employer subscription / plan state | `grep -n -A13 "CREATE TABLE subscriptions" FAIRFOLD_Project_Architecture_and_Requirements.md` |
| jobs | Job postings + screening-run state | `grep -n -A28 "CREATE TABLE jobs" FAIRFOLD_Project_Architecture_and_Requirements.md` |
| job_skills | Job ↔ skill join (REQ-FR-042) | `grep -n -A7 "CREATE TABLE job_skills" FAIRFOLD_Project_Architecture_and_Requirements.md` |
| applications | Applications + match score + gate status | `grep -n -A35 "CREATE TABLE applications" FAIRFOLD_Project_Architecture_and_Requirements.md` |
| skills | Skill catalog | `grep -n -A7 "CREATE TABLE skills" FAIRFOLD_Project_Architecture_and_Requirements.md` |
| candidate_skills | Candidate ↔ skill | `grep -n -A11 "CREATE TABLE candidate_skills" FAIRFOLD_Project_Architecture_and_Requirements.md` |
| certifications | Candidate certifications | `grep -n -A11 "CREATE TABLE certifications" FAIRFOLD_Project_Architecture_and_Requirements.md` |
| assessments | Assessment definitions | `grep -n -A11 "CREATE TABLE assessments" FAIRFOLD_Project_Architecture_and_Requirements.md` |
| assessment_questions | Assessment questions | `grep -n -A9 "CREATE TABLE assessment_questions" FAIRFOLD_Project_Architecture_and_Requirements.md` |
| assessment_attempts | Candidate assessment attempts | `grep -n -A11 "CREATE TABLE assessment_attempts" FAIRFOLD_Project_Architecture_and_Requirements.md` |
| job_assessment_requirements | Required assessments per job (REQ-FR-051) | `grep -n -A8 "CREATE TABLE job_assessment_requirements" FAIRFOLD_Project_Architecture_and_Requirements.md` |
| interview_packs | Generated interview question packs | `grep -n -A9 "CREATE TABLE interview_packs" FAIRFOLD_Project_Architecture_and_Requirements.md` |
| interviews | Scheduled interviews | `grep -n -A10 "CREATE TABLE interviews" FAIRFOLD_Project_Architecture_and_Requirements.md` |
| interview_feedback | Interviewer feedback | `grep -n -A8 "CREATE TABLE interview_feedback" FAIRFOLD_Project_Architecture_and_Requirements.md` |
| messages | Candidate–employer messages | `grep -n -A13 "CREATE TABLE messages" FAIRFOLD_Project_Architecture_and_Requirements.md` |
| notifications | In-app notifications | `grep -n -A9 "CREATE TABLE notifications" FAIRFOLD_Project_Architecture_and_Requirements.md` |
| announcements | Broadcast announcements (REQ-FR-050) | `grep -n -A17 "CREATE TABLE announcements" FAIRFOLD_Project_Architecture_and_Requirements.md` |
| data_export_requests | GDPR export requests | `grep -n -A8 "CREATE TABLE data_export_requests" FAIRFOLD_Project_Architecture_and_Requirements.md` |
| data_deletion_requests | GDPR deletion requests | `grep -n -A12 "CREATE TABLE data_deletion_requests" FAIRFOLD_Project_Architecture_and_Requirements.md` |
| audit_log_entries | Append-only audit log | `grep -n -A11 "CREATE TABLE audit_log_entries" FAIRFOLD_Project_Architecture_and_Requirements.md` |
| candidate_aliases | Per-employer candidate alias | `grep -n -A8 "CREATE TABLE candidate_aliases" FAIRFOLD_Project_Architecture_and_Requirements.md` |
| assessment_integrity_events | Light-proctoring events | `grep -n -A6 "CREATE TABLE assessment_integrity_events" FAIRFOLD_Project_Architecture_and_Requirements.md` |
| payments | Payment records (bKash/SSLCommerz) | `grep -n -A11 "CREATE TABLE payments" FAIRFOLD_Project_Architecture_and_Requirements.md` |
| practice_questions | Interview practice questions | `grep -n -A10 "CREATE TABLE practice_questions" FAIRFOLD_Project_Architecture_and_Requirements.md` |
| interview_coaching_sessions | Coaching sessions | `grep -n -A12 "CREATE TABLE interview_coaching_sessions" FAIRFOLD_Project_Architecture_and_Requirements.md` |
| scorecard_criteria | Published scorecard criteria | `grep -n -A9 "CREATE TABLE scorecard_criteria" FAIRFOLD_Project_Architecture_and_Requirements.md` |
| resources | Curated training resources | `grep -n -A12 "CREATE TABLE resources" FAIRFOLD_Project_Architecture_and_Requirements.md` |
| attempt_resource_recommendations | Resource recommendations per attempt | `grep -n -A6 "CREATE TABLE attempt_resource_recommendations" FAIRFOLD_Project_Architecture_and_Requirements.md` |

## API index (Complete Doc §C.12)

App = owning Django app; batch = the batch that builds it (Phase 1 is implemented, later phases planned).

| Method + path | App | Batch |
|---|---|---|
| POST /api/v1/auth/register/ | accounts | 1.03, 1.05 |
| POST /api/v1/auth/verify-email/ | accounts | 1.05 |
| POST /api/v1/auth/verify-email/resend/ | accounts | 1.05 |
| POST /api/v1/auth/login/ | accounts | 1.07, 1.08 |
| POST /api/v1/auth/refresh/ | accounts | 1.08 |
| POST /api/v1/auth/logout/ | accounts | 1.08 |
| POST /api/v1/auth/mfa/enable/ | accounts | 4.02 |
| POST /api/v1/auth/mfa/verify/ | accounts | 4.02 |
| GET /api/v1/auth/me/ | accounts | 1.12 |
| PUT /api/v1/auth/me/ | accounts | 1.12 |
| POST /api/v1/auth/password/change/ | accounts | 1.10 |
| POST /api/v1/auth/password/reset/ | accounts | 1.10 |
| POST /api/v1/auth/password/reset/confirm/ | accounts | 1.10 |
| GET /api/v1/candidates/me/ | candidates | 1.15 |
| PATCH /api/v1/candidates/me/ | candidates | 1.15 |
| GET /api/v1/candidates/skills/ | candidates | 3.02 |
| POST /api/v1/candidates/skills/ | candidates | 3.02 |
| PATCH /api/v1/candidates/skills/{id}/ | candidates | 3.02 |
| DELETE /api/v1/candidates/skills/{id}/ | candidates | 3.02 |
| GET /api/v1/candidates/resumes/ | candidates | 1.19, 1.21 |
| POST /api/v1/candidates/resumes/ | candidates | 1.19 |
| POST /api/v1/candidates/resumes/{id}/complete/ | candidates | 1.20 |
| POST /api/v1/candidates/resumes/{id}/process/ | candidates | 2.04 |
| GET /api/v1/candidates/resumes/{id}/ | candidates | 1.21 |
| DELETE /api/v1/candidates/resumes/{id}/ | candidates | 1.21 |
| GET /api/v1/candidates/certifications/ | candidates | 3.03 |
| POST /api/v1/candidates/certifications/ | candidates | 3.03 |
| GET /api/v1/candidates/journey/ | candidates | 3.04 |
| POST /api/v1/candidates/journey/regenerate/ | candidates | 3.07 |
| GET /api/v1/candidates/assessments/ | candidates | 3.08 |
| POST /api/v1/candidates/assessments/{id}/start/ | candidates | 3.13 |
| POST /api/v1/candidates/assessments/{id}/answer/ | candidates | 3.13 |
| GET /api/v1/candidates/applications/ | candidates | 1.38 |
| GET /api/v1/candidates/applications/{id}/ | candidates | 1.38, 2.40 |
| POST /api/v1/jobs/{id}/apply/ | matching | 1.36 |
| GET /api/v1/employers/me/ | employers | 1.24 |
| PATCH /api/v1/employers/me/ | employers | 1.24 |
| GET /api/v1/jobs/ | matching | 1.27 |
| POST /api/v1/jobs/ | matching | 1.27 |
| GET /api/v1/jobs/{id}/ | matching | 1.28 |
| PATCH /api/v1/jobs/{id}/ | matching | 1.28 |
| DELETE /api/v1/jobs/{id}/ | matching | 1.28 |
| POST /api/v1/jobs/{id}/activate/ | matching | 1.29 |
| POST /api/v1/jobs/{id}/pause/ | matching | 1.29 |
| POST /api/v1/jobs/{id}/close/ | matching | 1.29 |
| POST /api/v1/jobs/{id}/screen/ | matching | 2.32, 2.33 |
| GET /api/v1/jobs/{id}/applications/ | matching | 1.40, 2.19 |
| POST /api/v1/jobs/{id}/interview-pack/ | matching | 3.25 |
| GET /api/v1/jobs/{id}/analytics/ | matching | 3.23 |
| GET /api/v1/jobs/{id}/analytics/override-rate/ | matching | 3.23 |
| POST /api/v1/jobs/{id}/share/ | matching | 3.24 |
| GET /api/v1/jobs/{id}/required-assessments/ | matching | 3.10 |
| POST /api/v1/jobs/{id}/required-assessments/ | matching | 3.10 |
| DELETE /api/v1/jobs/{id}/required-assessments/{req_id}/ | matching | 3.10 |
| POST /api/v1/applications/{id}/shortlist/ | matching | 1.41 |
| POST /api/v1/applications/{id}/reject/ | matching | 1.41 |
| POST /api/v1/applications/{id}/review/ | matching | 2.18 |
| GET /api/v1/assessments/ | assessments | 3.09 |
| POST /api/v1/assessments/ | assessments | 3.09 |
| GET /api/v1/assessments/{id}/ | assessments | 3.09 |
| PATCH /api/v1/assessments/{id}/ | assessments | 3.09 |
| POST /api/v1/assessments/{id}/questions/ | assessments | 3.09 |
| PATCH /api/v1/assessments/{id}/questions/{qid}/ | assessments | 3.09 |
| DELETE /api/v1/assessments/{id}/questions/{qid}/ | assessments | 3.09 |
| POST /api/v1/assessments/{id}/reorder/ | assessments | 3.09 |
| POST /api/v1/assessments/{id}/activate/ | assessments | 3.09 |
| POST /api/v1/assessments/{id}/deactivate/ | assessments | 3.09 |
| GET /api/v1/interviews/ | interviews | 3.26 |
| POST /api/v1/interviews/ | interviews | 3.26 |
| GET /api/v1/interviews/{id}/ | interviews | 3.26 |
| POST /api/v1/interviews/{id}/feedback/ | interviews | 3.27 |
| GET /api/v1/interviews/{id}/pack/ | interviews | 3.25 |
| GET /api/v1/notifications/ | notifications | 1.44 |
| POST /api/v1/notifications/{id}/read/ | notifications | 1.44 |
| GET /api/v1/messages/?application={id} | notifications | 3.20 |
| POST /api/v1/messages/ | notifications | 3.20 |
| GET /api/v1/jobs/public/ | matching | 1.31, 1.32 |
| GET /api/v1/jobs/public/{id}/ | matching | 1.31 |
| POST /api/v1/gdpr/export/ | core | 4.08 |
| GET /api/v1/gdpr/export/{id}/ | core | 4.08 |
| GET /api/v1/gdpr/export/{id}/download/ | core | 4.08 |
| POST /api/v1/gdpr/deletion/ | core | 4.09 |
| GET /api/v1/gdpr/deletion/{id}/ | core | 4.09 |
| POST /api/v1/gdpr/deletion/{id}/cancel/ | core | 4.09 |
| GET /api/v1/employers/team/ | employers | 3.29 |
| POST /api/v1/employers/team/invite/ | employers | 3.29 |
| POST /api/v1/employers/team/{id}/role/ | employers | 3.29 |
| DELETE /api/v1/employers/team/{id}/ | employers | 3.29 |
| POST /api/v1/employers/team/invitations/{token}/accept/ | employers | 3.29 |
| DELETE /api/v1/employers/team/invitations/{id}/ | employers | 3.29 |
| GET /api/v1/admin/announcements/ | core | 3.32 |
| POST /api/v1/admin/announcements/ | core | 3.32 |
| POST /api/v1/admin/announcements/resolve-audience/ | core | 3.32 |
| POST /api/v1/admin/announcements/{id}/send/ | core | 3.32 |
| POST /api/v1/admin/announcements/{id}/cancel/ | core | 3.32 |
| POST /api/v1/practice-questions/ | ai | 3.15 |
| GET /api/v1/practice-questions/ | ai | 3.15 |
| POST /api/v1/coaching/sessions/ | ai | 3.16 |
| GET /api/v1/coaching/sessions/ | ai | 3.16 |
| GET /api/v1/jobs/{id}/scorecard-criteria/ | matching | 3.08 |
| POST /api/v1/jobs/{id}/scorecard-criteria/ | matching | 3.08 |
| GET /api/v1/resources/?skill={id} | ai | 3.18 |
| POST /api/v1/assessments/{id}/recommend-resources/ | assessments | 3.18 |
| GET /api/v1/assessments/{id}/retake-eligible/ | assessments | 3.18 |
| POST /api/v1/coaching/rate/ | ai | 3.18 |
| GET /api/v1/admin/dashboard/ | core | 3.30 |
| GET /api/v1/admin/users/ | core | 3.30 |
| GET /api/v1/admin/audit-log/ | core | 3.31 |
| GET /api/v1/admin/ai-quota/ | core | 2.31 |

## Repo map (from the code)

| App | Contents |
|---|---|
| `core` | `AuditLogEntry`, `Skill` models; storage, middleware, pagination, markdown, geo/reference data, seed + storage commands |
| `accounts` | Custom `User` (AUTH_USER_MODEL, `db_table="users"`), auth/permission/role services, JWT + session views, registration/verification/reset |
| `candidates` | `CandidateProfile`, `CandidateAlias`, `CandidateResume` models; resume upload/scan/processing, alias service, profile UI/API |
| `employers` | `EmployerProfile` model; job CRUD, public board, application inbox/review UI/API |
| `matching` | `Job`, `JobSkill`, `Application` models; apply/decision/rank services and APIs |
| `notifications` | `Notification` model; delivery tasks, list/unread UI/API, context processor |
| `ai` | No models. Bias pass/audit, citation validator, screening helpers (Phase-2 infrastructure, used by tests) |
| `assessments` | **Empty** (12-line `models.py` placeholder, no models/migrations) — Phase 3 |
| `interviews` | **Empty** — Phase 3 |
| `journey` | **Empty** — Phase 3 |
| `api` | **Empty models** — mounts the other apps' routers (`api/urls.py`) |

## Asserted counts (what `scripts/verify_docs.py` reports)

- **33 tables**, 53 foreign keys, 27 indexes (Arch Doc §5.1 DDL is the artefact of record).
- **63 FRs** (§4.1), **50 NFRs** (SEC 14 + COM 9 + NFR 23 + NFOR 4).
- **63 user stories / 260 points** (37 Must / 21 Should / 5 Could).
- **78 page rows**, **65 wireframes defined / 61 referenced by a page row** (W26–W29 are component/state drawings, not pages).
- `docs/DECISIONS.md` holds D-1 to D-13 (some open); see it for decision state.
