# Requirements traceability

Generated from Arch Doc §4.1 (63 functional requirements) and the batch plan. Statuses reflect the uploaded zip as read on 2026-10-18; code was read, not run. Update the Status column after each batch (`done` only when its acceptance criteria are shown by passing tests).

Non-functional groups (REQ-SEC, REQ-NFR, REQ-COM) are covered by Phase 4 batches 4.1 to 4.17 and by the 'Watch out' notes in earlier batches; they are not listed row by row here.

| FR | Requirement | Priority | Planned batch(es) | Status | Evidence / note |
|---|---|---|---|---|---|
| REQ-FR-001 | User Registration | High | 0.3, 1.1, 1.3, 1.4, 1.5, 1.6 | not started |  |
| REQ-FR-002 | User Login | High | 0.5, 1.4, 1.7, 1.8, 1.9 | not started |  |
| REQ-FR-003 | Account Lockout | High | 1.1, 1.7 | partial | User.failed_login_attempts / locked_until / is_locked() exist in accounts/models.py; no login logic or tests |
| REQ-FR-004 | Password Recovery | High | 1.10, 1.11 | not started |  |
| REQ-FR-005 | MFA Enable | Medium | 4.2 | not started |  |
| REQ-FR-006 | MFA Verification | Medium | 4.2 | not started |  |
| REQ-FR-007 | JWT Token Refresh | High | 0.5, 1.8 | not started |  |
| REQ-FR-008 | JWT Token Revocation | Medium | 1.8 | not started |  |
| REQ-FR-009 | Candidate Profile Creation | High | 1.14, 1.15, 1.16 | not started |  |
| REQ-FR-010 | Resume Upload via Presigned URL | High | 1.17, 1.18, 1.19, 1.21, 1.22 | not started |  |
| REQ-FR-011 | Resume PII Stripping | High | 2.1, 2.6, 2.7, 2.9 | not started |  |
| REQ-FR-012 | Resume Text Extraction | High | 1.18, 2.1, 2.2, 2.3, 2.4, 2.5 | not started |  |
| REQ-FR-013 | Resume Embedding Generation | High | 2.11, 2.12, 2.13, 2.14 | not started |  |
| REQ-FR-014 | Skill Management | High | 3.2 | not started |  |
| REQ-FR-015 | Skill Deduplication | Medium | 3.1 | partial | core.Skill model, migration and core/fixtures/skills.json exist; no alias mapping |
| REQ-FR-016 | Journey Mapping — Timeline | High | 3.4, 3.5 | not started |  |
| REQ-FR-017 | Journey Mapping — Skill Evolution | Medium | 3.6 | not started |  |
| REQ-FR-018 | Journey Mapping — Dynamic Storytelling | Medium | 3.7 | not started |  |
| REQ-FR-019 | Assessment Taking | Medium | 3.8, 3.13, 3.14 | not started |  |
| REQ-FR-020 | Assessment Auto-Scoring | Medium | 3.8, 3.13, 3.14 | not started |  |
| REQ-FR-021 | Interview Coaching | Medium | 3.16 | not started |  |
| REQ-FR-022 | Job Application | High | 1.34, 1.36, 1.37, 1.43 | not started |  |
| REQ-FR-023 | Application Status Tracking | High | 1.38, 1.39, 1.41, 1.43, 1.44 | not started |  |
| REQ-FR-024 | Match Score Visibility | High | 2.40 | not started |  |
| REQ-FR-025 | Job Creation | High | 1.26, 1.27, 1.30, 2.14 | not started |  |
| REQ-FR-026 | Job Editing | High | 1.28, 1.30 | not started |  |
| REQ-FR-027 | Job Activation | High | 1.29, 1.30 | not started |  |
| REQ-FR-028 | AI Screening Trigger | High | 2.30, 2.31, 2.32, 2.33, 2.34, 2.35 | not started |  |
| REQ-FR-029 | Screening Result Display | High | 1.40, 1.42, 2.18, 2.19, 2.20, 2.29, 2.39, 2.42 | not started |  |
| REQ-FR-030 | Evidence-Cited Rationale | High | 2.21, 2.24, 2.25, 2.27, 2.28, 2.29 | partial | ai/bias_audit.py and ai/bias_pass.py exist with tests/bias/ (40 tests pass); no rationale generation |
| REQ-FR-031 | Interview Pack Generation | Medium | 3.25 | not started |  |
| REQ-FR-032 | Interview Scheduling | Medium | 3.26 | not started |  |
| REQ-FR-033 | Interview Feedback | Medium | 3.27 | not started |  |
| REQ-FR-034 | Offer Generation | Low | 3.28 | not started |  |
| REQ-FR-035 | Analytics Dashboard | Medium | 3.23 | not started |  |
| REQ-FR-036 | Job Sharing | Medium | 3.24 | not started |  |
| REQ-FR-037 | Admin Dashboard | Medium | 3.30 | not started |  |
| REQ-FR-038 | User Management | High | 1.2, 3.30 | not started |  |
| REQ-FR-039 | Audit Log Search | High | 3.31 | partial | core.AuditLogEntry model and migration exist; no search or CSV export |
| REQ-FR-040 | Data Export (GDPR) | High | 4.8 | not started |  |
| REQ-FR-041 | Account Deletion (GDPR) | High | 4.9 | not started |  |
| REQ-FR-042 | Job Browse and Search | High | 1.23, 1.26, 1.31, 1.32, 1.33 | not started |  |
| REQ-FR-043 | Candidate–Employer Messaging | Medium | 3.19, 3.20, 3.21 | not started |  |
| REQ-FR-044 | Certification Management | Medium | 3.3 | not started |  |
| REQ-FR-045 | Employer Company Profile | High | 1.2, 1.23, 1.24, 1.25, 1.29 | not started |  |
| REQ-FR-046 | Employer Dashboard | Medium | 3.22 | not started |  |
| REQ-FR-047 | Employer Team and Roles | Medium | 3.29 | not started |  |
| REQ-FR-048 | Billing and Plan Management | Medium | 5.1, 5.2 | not started |  |
| REQ-FR-049 | Assessment Management | Medium | 3.8, 3.9 | not started |  |
| REQ-FR-050 | Broadcast Announcement | Low | 3.32 | not started |  |
| REQ-FR-051 | Employer-Required Skill Assessment | High | 3.8, 3.10, 3.11, 3.12 | not started |  |
| REQ-FR-052 | Override Visibility and Record | High | 1.41, 2.37, 2.38, 3.23 | not started |  |
| REQ-FR-053 | Paid discovery only — no ranking influence | High | 1.14, 2.17 | not started |  |
| REQ-FR-054 | Per-employer candidate alias | High | 1.35, 1.40, 2.19, 2.39 | not started |  |
| REQ-FR-055 | Assessment integrity events | Medium | 3.8, 3.13, 3.14 | not started |  |
| REQ-FR-056 | Local payment providers (bKash, SSLCommerz) | High | 4.13, 5.1 | not started |  |
| REQ-FR-057 | Expanded PII and proxy stripping | High | 2.6, 2.7, 2.8 | not started |  |
| REQ-FR-058 | Text-only interview practice | Medium | 3.15, 3.16, 3.17 | not started |  |
| REQ-FR-059 | STAR rubric grading with cited feedback | Medium | 3.15, 3.16, 3.17 | not started |  |
| REQ-FR-060 | Coaching practice isolation | Medium | 3.15, 3.16 | not started |  |
| REQ-FR-061 | Training gap resources | Medium | 3.15, 3.18 | not started |  |
| REQ-FR-062 | Coaching evaluation set | Low | 3.15, 3.16 | not started |  |
| REQ-FR-063 | Assessment → Resource → Retake loop | Low | 3.18 | not started |  |
