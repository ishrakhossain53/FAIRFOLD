# FAIRFOLD — Detailed Architecture & Requirements Specification

**Version:** 4.1 (52 FRs · override visibility · employer-required assessments · versioned hard filters)  
**Date:** September 2026  
**Status:** Ready for Implementation  
**Authors:** Sardar Shihab, Arnob Biswas Antu, Ishrak Hossain, Mohammad Abdul Ahad, Fahad Haque  

> **Companion document to:** `FAIRFOLD_Complete_Project_Document.md`  
> This document provides the detailed, implementation-ready architecture and requirements that supplement the high-level project document. Where the project document describes *what* to build and *why*, this document specifies *how* — with concrete APIs, data models, acceptance criteria, and measurable quality attributes.

---

## Table of Contents

1. [Purpose & Scope](#1-purpose--scope)
2. [Identified Gaps in Original Document](#2-identified-gaps-in-original-document)
3. [System Architecture](#3-system-architecture)
4. [Detailed Requirements Specification](#4-detailed-requirements-specification)
5. [Data Architecture](#5-data-architecture)
6. [CI/CD & Deployment](#6-cicd--deployment)
7. [Testing Strategy](#7-testing-strategy)
8. [Operations & Monitoring](#8-operations--monitoring)
   8.1 [Monitoring Stack](#81-monitoring-stack)
   8.2 [Key Dashboards](#82-key-dashboards)
   8.3 [Log Format (Structured JSON)](#83-log-format-structured-json)
   8.4 [Environment Configuration](#84-environment-configuration)
   8.5 [Maintenance & Patch Management Schedule](#85-maintenance--patch-management-schedule)
   8.6 [Incident Response Plan](#86-incident-response-plan)
   8.7 [Post-Deployment Evaluation & Retrospective Process](#87-post-deployment-evaluation--retrospective-process)
   8.8 [Environment Promotion & Configuration Drift Prevention](#88-environment-promotion--configuration-drift-prevention)
   8.9 [Versioning & Release Strategy](#89-versioning--release-strategy)
9. [Risk Register](#9-risk-register)
10. [Acceptance Criteria](#10-acceptance-criteria)
11. [Glossary](#11-glossary)

---

## 1. Purpose & Scope

This document defines the complete technical architecture, functional requirements (FRs), and non-functional requirements (NFRs) for the **FairFold** platform. It serves as the implementation contract between the design team and engineering.

### 1.1 Out of Scope
- Mobile app native development (Phase 5; PWA is the Phase 4 fallback)
- Real-time video interview recording (Phase 5; Phase 3 provides async coaching only)
- Third-party profile scraping (LinkedIn API integration, etc.) — explicitly excluded per §3.2
- On-premises deployment for customers (Phase 5 "Enterprise" tier feature)

### 1.2 Document Conventions
- **REQ-FR-xxx**: Functional requirement
- **REQ-NFR-xxx**: Non-functional requirement
- **REQ-SEC-xxx**: Security requirement
- **REQ-COM-xxx**: Compliance requirement
- **AD-00x**: Architecture decision record
- Acceptance criteria use Gherkin-style Given/When/Then format

---

## 2. Identified Gaps in Original Document

### 2.1 Architectural Gaps

| Gap ID | Missing Component | Severity | Original Section Affected |
|---|---|---|---|
| GAP-001 | Explicit API endpoint specification | Medium | §4, §7 |
| GAP-002 | Error handling & retry strategy | High | §5, §6 |
| GAP-003 | Rate limiting implementation details | Medium | §5.5 |
| GAP-004 | CI/CD pipeline YAML/Specification | Medium | §5.6, §10 |
| GAP-005 | Testing strategy (unit, integration, E2E) | High | §5.6, §10 |
| GAP-006 | Deployment configuration (Docker Compose) | Medium | §4.1, §10 |
| GAP-007 | Internationalization (i18n) structure | Low | §7, §9 Phase 5 |
| GAP-008 | Monitoring alert thresholds | Medium | §5.6 |
| GAP-009 | Database migration strategy | Medium | §8, §10 |
| GAP-010 | Offline-first capabilities | Medium | §6, §7 |
| GAP-011 | Caching strategy (keys, TTL, invalidation) | High | §4.1 |
| GAP-012 | Complete database schema (all models) | High | §8 |
| GAP-013 | Disaster recovery (RTO/RPO) | Medium | §5.2 |
| GAP-014 | Penetration testing plan | Medium | §5.5 |
| GAP-015 | Feature backlog with acceptance criteria | High | §9 |
| GAP-016 | Complete pricing tier breakdown | Low | §1, §10 |
| GAP-017 | Frontend technology contradiction | Medium | §4.1 vs §7.3 |
| GAP-018 | EU AI Act reference date ambiguity | Low | §5.4, §11 |

### 2.2 Requirements Gaps

| Gap ID | Missing Requirement | Priority | Original Section Affected |
|---|---|---|---|
| GAP-A01 | Non-functional requirements (performance, availability) | High | §5, §10 |
| GAP-A02 | Security requirements (specific controls, not just categories) | High | §5 |
| GAP-A03 | Data retention policies with specific durations | High | §5.7 |
| GAP-A04 | Audit requirements (who, when, what, format) | Medium | §5.5 |
| GAP-A05 | Backup and restore procedures | High | §5.2 |
| GAP-A06 | Disaster recovery plan (RTO/RPO per component) | Medium | §5.2 |
| GAP-A07 | Accessibility compliance testing | Low | §5.7 |
| GAP-A08 | Internationalization requirements | Low | §7, §9 |
| GAP-A09 | Scalability requirements (concurrent users, throughput) | High | §4 |
| GAP-A10 | Maintainability requirements (code coverage, linting) | Medium | §10 |

---

## 3. System Architecture

### 3.1 Architecture Decision Records (ADRs)

#### AD-001: Full Python Stack (Django, not Rust/Go/Node)
**Status:** Accepted  
**Context:** The original proposal considered Rust/Actix for "high-performance components." Analysis showed the team has Python expertise and AI API calls dominate latency, not web serving.  
**Decision:** Full Python stack: Django 5.2+ LTS + DRF + Celery + pgvector. Single language reduces cognitive load, onboarding time, and deployment complexity.  
**Consequences:** Simpler hiring (Python devs are abundant), fewer build pipelines, but cannot leverage Rust's zero-cost abstractions for future performance needs.

#### AD-002: Django Templates + HTMX for MVP Frontend
**Status:** Accepted  
**Context:** Original §4.1 architecture diagram showed React 18 SPA, but §7.3 recommended Django Templates + HTMX. This was a contradiction in the source document.  
**Decision:** Django Templates + HTMX for MVP. React 18 + Vite reserved for Phase 5 (mobile PWA, real-time WebSocket features). DRF API is built from day one so the React SPA can be added without backend changes.  
**Consequences:** Faster MVP delivery, single deployment artifact, no CORS/auth-token complexity. React becomes an optional frontend layer, not a replacement.

#### AD-003: OpenRouter as Primary AI Provider
**Status:** Accepted  
**Context:** Need free-tier AI for cost-sensitive MVP in emerging markets.  
**Decision:** OpenRouter `openrouter/free` router as default. Abstraction layer (`AIProvider` ABC) allows seamless switching to self-hosted models (vLLM/Llama) or other providers. Offline fallbacks (spaCy NER, sentence-transformers embeddings, template-based interview Qs) ensure zero-cost operation in degradation mode.  
**Consequences:** $0 AI cost for first ~50 req/day per IP. Risk of free tier removal mitigated by abstraction layer.

#### AD-004: pgvector for Semantic Matching
**Status:** Accepted  
**Context:** Need sub-second similarity matching for 1000s of candidates without AI API calls.  
**Decision:** PostgreSQL 17 + pgvector extension. `sentence-transformers/all-MiniLM-L6-v2` (384-dim) generates embeddings offline. Cosine similarity computed in-database via `<=>` operator.  
**Consequences:** Zero per-query AI cost. Index maintenance (HNSW IVF) required for datasets > 10K. Fallback to Python-level cosine similarity if pgvector unavailable.

#### AD-005: PII Stripping Before Any External Processing
**Status:** Accepted  
**Context:** GDPR Article 25, EU AI Act compliance. Competitors (Eightfold, SeekOut) send full PII to third-party AI.  
**Decision:** Multi-phase PII stripping pipeline: Phase 1 = regex + spaCy NER (offline, 100% free); Phase 2 = LLM-based detection (future). PII never reaches OpenRouter API. Audit log records every stripping event.  
**Consequences:** Extra latency (~2s per resume) but full compliance. Trust advantage over competitors.

#### AD-006: Monolith-First Architecture
**Status:** Accepted  
**Context:** Team of 5 developers, single deployment target.  

> *Corrected 2026-10-03.* This line still said 4 after the rename pass, so conflict 9
> (§5.3 of the feasibility document) was recorded as settled when one of its two
> occurrences had never been touched. The correction note is kept on its own line on
> purpose: a note sharing the line would also share the exemption that lets a line
> describe a stale figure, and the claim would then never be checked again.
**Decision:** Single Django monolith with app-level separation (candidates, employers, matching, assessments, interviews, journey, ai, core). Docker Compose for local; single-container or Kubernetes for prod. Microservices split only when scaling demands it.  
**Consequences:** Faster development, simpler debugging, atomic deployments. Future risk of tight coupling mitigated by app-level boundaries.

#### AD-007: Celery for Async AI Tasks
**Status:** Accepted  
**Context:** AI API calls take 2-10 seconds; cannot block web request.  
**Decision:** Celery + Redis as task queue. AI processing (resume parsing, matching, rationale generation) runs as background tasks. Celery Beat handles scheduled tasks (quota resets, backup notifications, data retention purges).  
**Consequences:** Requires Redis persistence strategy. Task results stored in Redis or database (django-celery-results).

### 3.2 High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          INTERNET (Users)                                   │
└────────────────────────────────────┬────────────────────────────────────────┘
                                     │ HTTPS (TLS 1.3)
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                  LOAD BALANCER / REVERSE PROXY                              │
│                        (Nginx + Let's Encrypt)                              │
│  - SSL/TLS Termination                                                     │
│  - Rate Limiting (1000 req/min per IP at edge)                            │
│  - Security Headers (CSP, HSTS, X-Frame-Options, etc.)                    │
│  - Static file serving (via Whitenoise or CDN)                            │
└────────────────────────────────────┬────────────────────────────────────────┘
                                     │ HTTP
            ┌────────────────────────┼──────────┐
            ▼                        ▼          ▼
┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐
│   Django App      │  │   Celery Worker   │  │   Celery Beat     │
│   (Gunicorn)      │  │   (AI Tasks)      │  │   (Scheduler)     │
│   4-8 workers     │  │   2-4 workers     │  │   Periodic tasks  │
│                   │  │                   │  │                   │
│  • Django Templates │ │  • OpenRouter API  │ │  • Quota reset     │
│  • HTMX + Tailwind │ │  • sentence-       │ │    job (daily)     │
│  • Chart.js          │ │    transformers    │ │  • Backup notify   │
│  • DRF API           │ │  • spaCy NER        │ │    (hourly)        │
└─────────┬─────────┘  └─────────┬─────────┘  └─────────┬─────────┘
          │                        │                      │
          ▼                        ▼                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          SHARED SERVICES                                    │
├───────────────────┬───────────────────┬───────────────────┬───────────────────┐
│   PostgreSQL      │      Redis        │      S3/MinIO     │     Email         │
│   (Primary DB)    │   (Broker+Cache)  │   (File Storage)  │   (Transactional) │
│   pgvector ext    │   Rate Limiting   │   SSE-KMS         │   SendGrid/Resend │
│   pgcrypto        │   Task Results    │   Protected URLs  │                   │
│   Row-level sec   │   Session Store   │                   │                   │
└───────────────────┴───────────────────┴───────────────────┴───────────────────┘
```

### 3.3 Component Interactions (Data Flow)

**Flow 1: Candidate Applies to Job (No AI)**

```
1. Candidate           2. Django           3. PostgreSQL       4. Candidate
   uploads resume ────→ POST /resume/ ────→ INSERT applications ────→ sees "Applied" status
   (presigned S3 URL)
   ↓
   S3 stores file with UUID name
   Django saves S3 key in DB (never the file itself)
```

**Flow 2: Employer Triggers AI Screening (With AI)**

```
1. Employer clicks  2. Django creates  3. Redis Queue    4. Celery Worker   5. OpenRouter API
   "Screen All"       screening task    ───→ dequeues task ───→ PII strips   ───→ free models
                                             ↑                    ↑ (anonymized)
   shows cost estimate  ←  6. Redis cache    │  7. pgvector       │
   ($0.00 free tier)        stores results   └── cosine sim ──────┘
                                                  ↓ ranking
                                                8. Django returns
                                                   ranked list + rationale
```

**Flow 3: PII Stripping Pipeline (Privacy Layer)**

```
Resume PDF ──→ Text Extraction (pdfplumber) ──→ PII Detection (spaCy NER + regex)
                       │
                       ▼
                Replace with placeholders:
                "John Smith" → [CANDIDATE_NAME]
                "john@email.com" → [CANDIDATE_EMAIL]
                "Dhaka, Bangladesh" → [CANDIDATE_LOCATION]
                       │
                       ▼
                Store anonymized text in DB
                Original PII stays in EncryptedCharField
                Audit log entry: PII stripped + model used
```

### 3.4 Technology Stack Matrix

| Layer | Technology | Version | Rationale |
|---|---|---|---|
| **Frontend** | Django Templates | ships with Django 5.2 | Single framework, faster MVP |
| | HTMX | 1.18+ | SPA-like interactivity without separate frontend |
| | TailwindCSS | 3.4 | Rapid UI development |
| | Django-HTMX | 1.0+ | HTMX ↔ Django integration |
| | Chart.js | 4.4 | Journey mapping visualization |
| **Build Tooling** | Node.js | 20 LTS | **Build-time only.** Runs the Tailwind CLI and nothing else — there is no SPA, no bundler and no `node_modules` in the production image. Added 2026-10-03 (gap O): the frontend stack was named but no toolchain was specified, so "build Tailwind to a static CSS file" (`design.md` §11.2) was an instruction with no way to execute it |
| | Tailwind CSS CLI | 3.4 | `npm run build` → `static/css/tailwind.css`, compiled from `tailwind.config.js` and the tokens in `design.md` §3–§5 |
| | HTMX (npm) | 1.18 | Vendored to `static/js/htmx.min.js` so the CSP does not need a third-party script host |
| | Chart.js (npm) | 4.4 | Vendored the same way; loaded only on Journey Map and Analytics pages (`design.md` §11.4) |
| **Backend** | Django | 5.2+ | LTS — production-proven (Instagram, Pinterest) |
| | Django REST Framework | 3.15.1 | API layer for the DRF endpoints; pinned in `requirements.txt` |
| | DRF Spectacular | 0.28 | OpenAPI 3.0 auto-generation |
| **Database** | PostgreSQL | 17 | JSON support, row-level security |
| | psycopg2-binary | 2.9.9+ | PostgreSQL driver |
| | pgvector (Python) | 0.2.0+ | Semantic similarity search; the PostgreSQL extension is a separate version — see below |
| | pgcrypto | built-in | Additional field encryption |
| **AI/ML** | sentence-transformers | 3.0+ | Offline embeddings ($0 cost) |
| | spaCy | 3.8+ | PII detection NER (offline) |
| | OpenRouter SDK (openai) | 1.40+ | Free tier AI access |
| | torch | 2.3+, **CPU wheel** | Required by sentence-transformers. Installed from `download.pytorch.org/whl/cpu`; the default PyPI wheel bundles CUDA and pulls several GB onto a CPU-only VPS |
| | transformers | 4.44+ | Required by sentence-transformers |
| **Background** | Celery | 5.4+ | Async task processing |
| | Celery Beat | built-in | Scheduled tasks |
| | Celery Results (django-celery-results) | 2.5+ | Task result backend |
| | Celery Beat UI (django-celery-beat) | 2.7+ | Periodic task scheduler |
| | Redis | 5.0+ | Celery broker + result backend |
| | django-redis | 5.4 | **Redis cache backend.** Added 2026-10-03: §5.4 specifies Redis-backed caching and Redis rate-limit counters, but no Django Redis cache backend was in the dependency list, so the cache strategy was unimplementable and rate limits would have been per-process |
| | Flower | 2.0+ | Celery monitoring UI |
| **Infrastructure** | Docker | 24.x | Containerization |
| | Docker Compose | v2 | Local dev orchestration |
| | Nginx | 1.25+ | Reverse proxy, TLS termination |
| | Gunicorn | 22.0 | WSGI server |
| | Whitenoise | 6.8+ | Static file serving (fallback) |
| | python-dotenv | 1.0.1+ | Loads `.env` in development |
| **Storage** | django-storages | 1.14+ | S3-compatible storage backend |
| | boto3 | 1.34+ | AWS S3 / MinIO SDK |
| | python-magic | 0.4+ | MIME type validation |
| | clamav-client | 0.10+ | Antivirus scanning |
| | pdfplumber | 0.11+ | PDF text extraction |
| **Security** | Argon2id | via argon2-cffi | Password hashing |
| | cryptography | 43.0+ | AES-256-GCM field encryption |
| | django-encrypted-model-fields | 1.3.0 | EncryptedCharField |
| | django-ratelimit | 4.1.0 | Rate limiting. **Must be configured against the Redis cache**, not the default local-memory cache, or limits are enforced per gunicorn worker and are therefore not limits |
| | django-otp | 0.16.0 | TOTP MFA |
| | djangorestframework-simplejwt | 5.3.3 | JWT authentication |
| **Email** | django-anymail | 10.0+ | Unified email backend |
| **Billing** | stripe | 10.0+ | Payment processing |
| **Monitoring** | sentry-sdk | 2.14+ | Error tracking |
| | prometheus-client | 0.20+ | Metrics endpoint |
| **Dev Tools** | pytest | 8.3+ | Testing framework |
| | pytest-django | 4.8+ | Django test integration |
| | pytest-cov | 5.0+ | Coverage reporting |
| | factory-boy | 3.3+ | Test fixtures |
| | black | 24.10+ | Code formatting |
| | flake8 | 7.1+ | Linting |
| | isort | 5.13+ | Import sorting |
| | mypy | 1.13+ | Type checking |
| | bandit | 1.7+ | Security static analysis |
| | pip-audit | 2.8+ | Dependency vulnerability scan |
| | safety | 2.5+ | Supplementary dependency vulnerability scan |
| | sphinx | 8.2+ | API documentation generator |

---

## 4. Detailed Requirements Specification

### 4.1 Functional Requirements

#### Authentication & User Management

| ID | Requirement | Priority | Acceptance Criteria |
|---|---|---|---|
| REQ-FR-001 | User Registration | High | **Given** unverified email; **When** user submits registration form with valid email/password/role; **Then** account created, verification email sent, `email_verified=False` |
| REQ-FR-002 | User Login | High | **Given** verified user with correct credentials; **When** user submits login; **Then** JWT access (15 min) + refresh (7 day) tokens returned; **And** `failed_login_attempts` reset to 0 |
| REQ-FR-003 | Account Lockout | High | **Given** user has 5 consecutive failed login attempts; **When** 6th attempt occurs; **Then** account locked for 15 min; **And** `locked_until` set to current time + 15 min |
| REQ-FR-004 | Password Recovery | High | **Given** user requests password reset; **When** valid email provided; **Then** password reset email sent with 1-hour expiry token link |
| REQ-FR-005 | MFA Enable | Medium | **Given** authenticated user; **When** user submits MFA enable request; **Then** TOTP secret generated, QR code displayed, `mfa_secret` stored encrypted |
| REQ-FR-006 | MFA Verification | Medium | **Given** MFA enabled and user has authenticator app; **When** user submits 6-digit TOTP code; **Then** code verified against stored secret, `mfa_enabled=True` set |
| REQ-FR-007 | JWT Token Refresh | High | **Given** valid refresh token not expired; **When** user calls refresh endpoint; **Then** new access token issued, old refresh token remains valid until 7 days |
| REQ-FR-008 | JWT Token Revocation | Medium | **Given** expired or revoked refresh token; **When** user calls logout; **Then** refresh token added to blacklist, subsequent use returns 401 |

#### Candidate Portal

| ID | Requirement | Priority | Acceptance Criteria |
|---|---|---|---|
| REQ-FR-009 | Candidate Profile Creation | High | **Given** registered candidate user; **When** user completes onboarding; **Then** CandidateProfile created with title, bio, location, remote_ok |
| REQ-FR-010 | Resume Upload via Presigned URL | High | **Given** authenticated candidate; **When** candidate uploads file; **Then** frontend requests presigned URL from `/api/candidates/resumes/`; **And** file uploaded directly from browser to S3; **And** Django stores only the S3 key |
| REQ-FR-011 | Resume PII Stripping | High | **Given** uploaded resume; **When** PII stripping pipeline runs; **Then** name/email/phone/location removed or replaced with placeholders; **And** anonymized text stored; **And** audit log entry created |
| REQ-FR-012 | Resume Text Extraction | High | **Given** PDF resume uploaded; **When** processing completes; **Then** full text extracted (pdfplumber); **And** stored in `extracted_text` field (anonymized) |
| REQ-FR-013 | Resume Embedding Generation | High | **Given** extracted text; **When** embedding task runs; **Then** 384-dim vector generated via sentence-transformers; **And** stored in pgvector column `resume_embedding` |
| REQ-FR-014 | Skill Management | High | **Given** candidate with skills; **When** candidate adds/edits/deletes skill; **Then** CandidateSkill record created/updated/deleted with level and source |
| REQ-FR-015 | Skill Deduplication | Medium | **Given** skill aliases ("JS", "JavaScript"); **When** skill added; **Then** mapped to canonical Skill record; **And** no duplicate canonical skills created |
| REQ-FR-016 | Journey Mapping — Timeline | High | **Given** parsed resume with career history; **When** journey mapping runs; **Then** interactive timeline rendered with Chart.js showing experience periods |
| REQ-FR-017 | Journey Mapping — Skill Evolution | Medium | **Given** skills with timestamps; **When** candidate views journey; **Then** skill acquisition timeline chart shows when each skill was gained |
| REQ-FR-018 | Journey Mapping — Dynamic Storytelling | Medium | **Given** a specific job application; **When** candidate views their story; **Then** AI generates narrative optimized for that job's requirements |
| REQ-FR-019 | Assessment Taking | Medium | **Given** available assessment; **When** candidate starts; **Then** timer begins; **And** answers saved incrementally; **And** auto-submitted on timeout |
| REQ-FR-020 | Assessment Auto-Scoring | Medium | **Given** completed assessment; **When** scoring runs; **Then** each answer scored; **And** total score calculated; **And** score stored in AssessmentAttempt |
| REQ-FR-021 | Interview Coaching | Medium | **Given** candidate preparing for interview; **When** candidate pastes practice answer; **Then** AI provides feedback on structure, content, missing points |
| REQ-FR-022 | Job Application | High | **Given** authenticated candidate and active job; **When** candidate applies; **Then** Application record created with status="applied"; **And** candidate notified; **And** employer notified |
| REQ-FR-023 | Application Status Tracking | High | **Given** existing application; **When** status changes; **Then** candidate sees updated status in dashboard; **And** notification sent |
| REQ-FR-024 | Match Score Visibility | High | **Given** screened application; **When** candidate views application; **Then** match score (0-100) displayed with evidence-cited rationale |

#### Employer Portal

| ID | Requirement | Priority | Acceptance Criteria |
|---|---|---|---|
| REQ-FR-025 | Job Creation | High | **Given** authenticated employer; **When** employer fills job form; **Then** Job record created with all fields; **And** screening questions auto-suggested by AI |
| REQ-FR-026 | Job Editing | High | **Given** existing job (draft status); **When** employer edits; **Then** all fields updated; **And** audit log entry created |
| REQ-FR-027 | Job Activation | High | **Given** draft job; **When** employer publishes; **Then** status changes to "active"; **And** job visible to candidates |
| REQ-FR-028 | AI Screening Trigger | High | **Given** active job with applications; **When** employer clicks "Screen All"; **Then** cost estimate shown ($0.00 for free tier); **And** user confirms; **And** Celery batch task queued |
| REQ-FR-029 | Screening Result Display | High | **Given** completed screening; **When** employer views applications; **Then** ranked list shows match scores; **And** clicking candidate shows full rationale; **And** candidates are listed by anonymised ID with no name, photo or contact detail — **the name is revealed only when the employer shortlists** (REQ-FR-030); **And** candidates the hard filter marked `not_matched` **remain listed and visible to the employer with the reason shown** — a rule-based rejection is never hidden and never final on its own; **And** the employer can pull any `not_matched` candidate into review, which sets `status` back to `screened` and writes an audit entry; **And** the version of the hard-filter rule set that produced each result is recorded on the application (`filter_rules_version`) and shown in the UI. *Amended 2026-10-03 from Gap G3 — see `FAIRFOLD_Feasibility_and_Design.md` §2.4.1. Motivated by EEOC v. iTutorGroup, where a hard-coded age filter was the entire discriminating mechanism (§1.2.1).* |
| REQ-FR-030 | Evidence-Cited Rationale | High | **Given** AI-generated rationale; **When** employer views candidate; **Then** rationale shows specific resume text for each claim; **And** missing skills listed; **And** bias audit status shown; **And** the candidate's name, photo and contact details stay hidden until the employer shortlists them, at which point they are revealed to that employer only and the reveal writes an audit entry; **And** unrevealed PII is never sent to any external AI provider |
| REQ-FR-031 | Interview Pack Generation | Medium | **Given** job with requirements; **When** employer generates interview pack; **Then** AI produces structured Qs + scoring rubric; **And** pack stored and linked to job |
| REQ-FR-032 | Interview Scheduling | Medium | **Given** shortlisted candidate; **When** employer schedules; **Then** calendar invite sent; **And** video call URL generated; **And** candidate notified |
| REQ-FR-033 | Interview Feedback | Medium | **Given** completed interview; **When** interviewer submits feedback; **Then** scores + comments stored; **And** recommendation recorded |
| REQ-FR-034 | Offer Generation | Low | **Given** selected candidate; **When** employer generates offer; **Then** AI drafts offer letter from job details; **And** employer can edit |
| REQ-FR-035 | Analytics Dashboard | Medium | **Given** jobs with applications; **When** employer views analytics; **Then** time-to-hire, source of hire, drop-off points, AI accuracy shown in charts; **And** an **override rate** is shown — the number and share of shortlist/reject decisions that went against the AI ranking, broken down by who made them and by job — so a reviewer can see whether the ranking is actually being respected, and each override links to its recorded reason (REQ-FR-052); **And** the count of `not_matched` candidates pulled into review is shown alongside the count that were not, so the hard filter's effect is measurable |
| REQ-FR-036 | Job Sharing | Medium | **Given** published job; **When** employer generates share link; **Then** unique URL created; **And** embed code provided for career page |

#### Administrative

| ID | Requirement | Priority | Acceptance Criteria |
|---|---|---|---|
| REQ-FR-037 | Admin Dashboard | Medium | **Given** admin user; **When** viewing dashboard; **Then** system metrics, user counts, AI usage shown |
| REQ-FR-038 | User Management | High | **Given** admin; **When** viewing users; **Then** list/filter/sort all users; **And** roles editable; **And** lockout/reset actions available |
| REQ-FR-039 | Audit Log Search | High | **Given** audit logs exist; **When** admin searches; **Then** filter by action, resource, user, date range; **And** export to CSV |
| REQ-FR-040 | Data Export (GDPR) | High | **Given** any user; **When** requests data export; **Then** all personal data compiled as JSON; **And** download link provided; **And** expires in 7 days |
| REQ-FR-041 | Account Deletion (GDPR) | High | **Given** user requests deletion; **When** admin approves; **Then** hard delete all user data; **And** audit log entry created; **And** notification sent |

#### Job Discovery & Messaging

> Added to close two traceability gaps found during the feasibility review. Both
> capabilities already existed as use cases (`UC16`, `UC31`), user stories
> (`US-023`, `US-050`), a `Message` model (Complete Doc §C.11) and page
> specifications (`design.md` pages #4, #5, #31, #48) — but had no requirement
> anywhere. See `FAIRFOLD_Feasibility_and_Design.md` §2.4.1 for the analysis
> and `prd.md` §7.2–7.3 for the original proposal.

| ID | Requirement | Priority | Acceptance Criteria |
|---|---|---|---|
| REQ-FR-042 | Job Browse and Search | High | **Given** a job with status `active`; **When** any user (including an unauthenticated guest) visits the job board; **Then** active jobs listed, newest first; **And** keyword search over title, description and skills; **And** filters for location, remote flag and experience level combine with search; **And** results paginated; **And** an employer name is not shown until the employer has opted into candidate-facing disclosure |
| REQ-FR-043 | Candidate–Employer Messaging | Medium | **Given** an application exists; **When** either party opens the message thread for that application; **Then** thread is scoped to that application only; **And** the other party can send and read messages; **And** read state is stored and shown as an unread marker; **And** the recipient is notified in-app; **And** messages are excluded from AI processing and never sent to any external AI provider; **And** deleting one party soft-deletes rather than removes the counterparty's copy: the `messages` row is retained with `content` blanked, `sender_id`/`recipient_id` nulled and `deleted_at` set, since all three FKs are `ON DELETE SET NULL` (§5.1) |

**Related API gap:** `Complete Doc §C.12` does not list public job browse/search
endpoints for REQ-FR-042, nor GDPR export/delete endpoints for REQ-FR-040/041, nor any
endpoint for team management (REQ-FR-047), assessment authoring (REQ-FR-049) or broadcast
(REQ-FR-050). Those must be added to the API list before the build starts.

#### Employer Organisation, Billing & Content

> Added to close a second round of traceability gaps. A page-level audit of
> `design.md` §10 found seven pages building real features with no requirement
> behind them — the same failure mode as GAP-1/GAP-2, missed by the use-case
> pass because those pages are supporting features rather than core journeys.
> See `FAIRFOLD_Feasibility_and_Design.md` §2.4.1 for the analysis.

| ID | Requirement | Priority | Acceptance Criteria |
|---|---|---|---|
| REQ-FR-044 | Certification Management | Medium | **Given** authenticated candidate; **When** candidate adds a certification; **Then** `Certification` record created with name, issuer, issue/expiry dates and credential ID; **And** `credential_id` stored encrypted; **And** candidate can list, edit and delete their own certifications; **And** `verified` remains false until manually confirmed |
| REQ-FR-045 | Employer Company Profile | High | **Given** registered user with the employer role; **When** completing onboarding; **Then** `EmployerProfile` created with company name (encrypted), industry and company size; **And** an employer cannot hold both the candidate and employer roles; **And** a job cannot be activated until a company profile exists |
| REQ-FR-046 | Employer Dashboard | Medium | **Given** authenticated employer; **When** opening the dashboard; **Then** open job count, new applications, applications awaiting screening and interviews this week are shown; **And** quota usage is displayed against the current subscription; **And** applications flagged by the bias check are surfaced for human review; **And** every KPI links to the underlying list |
| REQ-FR-047 | Employer Team and Roles | Medium | **Given** an employer with `employer_hr` role; **When** inviting, re-roling or removing a team member; **Then** `employer_manager`, `employer_hr` or `interviewer` role assigned from the defined set; **And** the last `employer_hr` cannot be removed or demoted, which would orphan the account; **And** an `employer_team_members` row is created or updated (§5.1); **And** an audit entry is written for every role change; **And** MFA is required before an invited member can act |
| REQ-FR-048 | Billing and Plan Management | Medium | **Given** authenticated employer; **When** viewing billing; **Then** current plan, usage meters and invoice history shown; **And** plan changes are initiated through the Stripe-hosted flow so no card data touches FAIRFOLD; **And** `Subscription` quota and job limits update on the Stripe webhook, not on the browser redirect; **And** a webhook failure leaves the subscription unchanged rather than half-updated |
| REQ-FR-049 | Assessment Management | Medium | **Given** admin user; **When** creating or editing an assessment; **Then** title, linked skill, difficulty, question count and time limit stored; **And** questions created, edited and reordered within the assessment; **And** deactivating an assessment hides it from new attempts without deleting existing `AssessmentAttempt` records; **And** an audit entry is written |
| REQ-FR-050 | Broadcast Announcement | Low | **Given** admin user; **When** creating an announcement; **Then** title, body, audience, channel and schedule are captured in an `Announcement` row with a preview; **And** the announcement is delivered to the selected audience on schedule via Celery Beat; **And** an empty audience match sends nothing and is reported rather than silently succeeding; **And** the resolved audience size is shown **before** sending, because "empty" is only one of the two bad outcomes — see the five constraints below. **HARDENED 2026-10-03.** This is the highest blast-radius feature per story point in the specification, and the original criteria covered only the *empty*-audience case. Five conditions are now written into the requirement itself rather than left to implementation: **(1) Suppression list** — the audience is resolved at send time, not create time, and deleted, bounced and unsubscribed users are skipped and counted in `skipped_count`. Otherwise a scheduled announcement emails a hard-deleted account, contradicting `REQ-FR-041`. **(2) Audience-type confinement** — an `employers`-only announcement must never be readable by a candidate, and vice versa. A wrong audience is a confidentiality incident, not a UI bug, so the send task re-checks the recipient's role rather than trusting the stored filter. **(3) Transactional-email protection** — bulk sends are capped per hour and go through a **separate** sending domain/subaddress from verification and password-reset mail. A burst from the transactional path can get the sending domain rate-limited or blocked, which would break account access for every user; a marketing feature must not be able to do that. **(4) Idempotency** — `idempotency_key` is unique and set before the task runs, so a Celery retry cannot send the same announcement twice. **(5) Audit entry** on create, send and cancel. **KEPT — decided 2026-10-03.** The team confirmed: keep `REQ-FR-050`, **Phase 4 only, never a launch dependency.** The total stays **217 points** and Phase 4 stays **44**. Two conditions ride on that decision, and both are binding: **(a)** it must never become a launch blocker — if Phase 4 hardening is short, this is the thing that slips, not GDPR export or the load test; **(b)** the four artefacts stay coupled, so if it is ever cut later, `REQ-FR-050`, `US-062`, `design.md` page #62 **and** the `announcements` table go together in one change. The original estimate was 3 points, which was wrong: it was re-estimated at **8** on 2026-10-03 once the missing table and these five constraints were priced |

#### Screening Integrity — Employer-Required Assessments, Override Visibility, Reviewable Filters

> Added 2026-10-03 to close **G1**, **G2** and **G3**, the three gaps exposed by writing
> the experience-to-requirement traceability table
> (`FAIRFOLD_Feasibility_and_Design.md` §1.3.2, analysis in §2.4.1). All three
> trace back to the same root cause — the Product Owner's own hiring process — and
> all three were approved by the team on 2026-10-03.
>
> **G2 is the important one.** Anonymised ranking only matters if the ranking is
> respected. Nothing in the previous specification recorded a shortlist or rejection
> that went *against* the ranking, which meant the platform could have offered a
> fair-looking process while the real decision was still made informally.

| ID | Requirement | Priority | Acceptance Criteria |
|---|---|---|---|
| REQ-FR-051 | Employer-Required Skill Assessment | High | **Given** an active job; **When** the employer attaches one or more assessments to that job as a required step; **Then** a `job_assessment_requirements` row is created per assessment with an optional `min_score` pass mark (§5.1); **And** an applicant who has not completed a required assessment has `assessment_gate_status = 'pending'` and **cannot be shortlisted on their match score alone** — the Shortlist action is disabled and explains why; **And** `assessment_gate_status` becomes `passed` or `failed` once a completed `AssessmentAttempt` is matched on candidate + assessment, and it is shown on the application row; **And** a job with no required assessment sets the gate to `not_required` for all its applicants, so existing behaviour is unchanged; **And** removing a required assessment never deletes existing attempts or scores; **And** every change to a job's required assessments writes an audit entry. **Phase 3** — this is the requirement that answers pain point P2 ("no skills check before the interview"), which the candidate-initiated assessments of REQ-FR-019/020 did not |
| REQ-FR-052 | Override Visibility and Record | High | **Given** a ranked application; **When** a user shortlists a candidate ranked **below** the employer's cut-off, or rejects one ranked **above** it; **Then** a written reason is **required** before the action completes — the dialog cannot be dismissed with an empty reason; **And** the application records `decision_override = TRUE`, `decision_override_reason` and `decided_by`; **And** an `AuditLogEntry` is written with `resource_type = 'ai_decision'`, so it is retained with the application record (2 years, 5 years if hired) rather than rotating at 90 days; **And** the employer can override with the reason empty only where the job has no cut-off configured, and that exception is recorded in the audit entry; **And** the override is surfaced on the application row, in the audit log, and as the override-rate chart in REQ-FR-035; **And** overrides are **not** blocked — the employer remains the decision-maker (`prd.md` §8.1). Requiring a reason makes an informal decision *visible and countable*, it does not prevent it. **Phase 2–3** |

#### Reviewable Hard Filters — implementation notes for G3

`not_matched` was previously a terminal state created by a rule, with no reason
recorded and no route back. Three changes make it defensible:

1. **Reason.** `applications.not_matched_reason` stores which rule fired (e.g.
   `experience_level`, `min_years`, `location`). Without it the employer cannot
   review the decision and the candidate cannot be told.
2. **Version.** `jobs.screening_config` holds the rule set as JSONB and
   `jobs.screening_config_version` increments on every edit. Each application stores
   `filter_rules_version`, so "which rule rejected this?" is answerable months later
   even after the job has been edited. An unversioned rule set is an unauditable one.
3. **Route back.** `not_matched` candidates stay in the ranked list behind a filter
   toggle, with the reason shown, and the employer can pull any of them into review.

**Constraint:** a filter may only ever produce `not_matched`, never `rejected`. Only
a person can reject a candidate.

### 4.2 Non-Functional Requirements

#### Performance

| ID | Requirement | Target | Measurement |
|---|---|---|---|
| REQ-NFR-001 | Resume processing (text extraction + PII strip) | < 30 sec | End-to-end time logged in task metadata |
| REQ-NFR-002 | Embedding generation (sentence-transformers) | < 10 sec | Per resume; batch of 10 = < 60 sec |
| REQ-NFR-003 | AI screening for 100 applications | < 5 min | Batch start to completion; within free tier limits |
| REQ-NFR-004 | pgvector similarity query (100 candidates) | < 2 sec | Database query time logged |
| REQ-NFR-005 | Page load time (server-side rendered) | < 2 sec | Lighthouse performance score ≥ 90 |
| REQ-NFR-006 | API response time (95th percentile) | < 500 ms | Prometheus histogram |
| REQ-NFR-007 | Static asset load time | < 500 ms | From CDN/edge cache |

#### Scalability

| ID | Requirement | Target | Measurement |
|---|---|---|---|
| REQ-NFR-008 | Concurrent authenticated users | 1,000 | Locust load test |
| REQ-NFR-009 | Concurrent AI screening tasks | 50 | Celery worker pool with autoscaling |
| REQ-NFR-010 | Database connections (pool) | 100 max | Django connection pooling |
| REQ-NFR-011 | File storage scalability | Petabyte-scale | S3/MinIO auto-scales |
| REQ-NFR-012 | Horizontal scaling | Stateless app layer | Add Django replicas behind load balancer |
| REQ-NFR-013 | Database read scaling | Read replicas | pgBouncer + read replicas |

#### Availability & Reliability

| ID | Requirement | Target | Measurement |
|---|---|---|---|
| REQ-NFR-014 | Platform uptime | 99.9% | Prometheus uptime monitoring; < 43 min/year downtime |
| REQ-NFR-015 | AI provider fallback | 99.99% | Offline fallback (spaCy + pgvector) activates within 30 sec of API failure |
| REQ-NFR-016 | Database failure recovery | RTO < 2 hr, RPO < 15 min | Monthly DR test |
| REQ-NFR-017 | Graceful degradation | No user-facing crash on AI failure | Users see "AI delayed" badge, not error page |
| REQ-NFR-018 | Self-healing | Auto-restart on crash | Docker restart policies |

#### Security

| ID | Requirement | Target | Verification |
|---|---|---|---|
| REQ-SEC-001 | Password hashing | Argon2id, 512-bit salt | Django default; verified via `password_hashers` setting |
| REQ-SEC-002 | PII never sent to AI | 100% | Audit log verification; OpenRouter request body inspection |
| REQ-SEC-003 | Field-level encryption | AES-256-GCM | Encrypted fields unreadable in DB backup |
| REQ-SEC-004 | TLS everywhere | TLS 1.3 minimum | SSL Labs A+ rating |
| REQ-SEC-005 | CSRF protection | All state-changing requests | Django middleware + JWT csrf token |
| REQ-SEC-006 | XSS protection | Auto-escaping + CSP | OWASP ZAP scan; CSP violation reporting |
| REQ-SEC-007 | SQL injection protection | Parameterized queries | Django ORM only; no raw SQL in views |
| REQ-SEC-008 | Rate limiting | Per-IP + per-user | Abusive IPs blocked automatically |
| REQ-SEC-009 | MFA requirement | Employer admin accounts | Verified in CI test; optional for candidates |
| REQ-SEC-010 | Security headers | HSTS, CSP, X-Frame-Options, nosniff | securityheaders.com grade A+ |
| REQ-SEC-011 | Dependency vulnerabilities | Zero critical/high | `pip-audit` in CI; blocking merge on failure |
| REQ-SEC-012 | File upload security | MIME validation + virus scan | ClamAV + python-magic; max 10MB |
| REQ-SEC-013 | Session security | HttpOnly, Secure, SameSite=Lax | Cookie attributes verified in browser |
| REQ-SEC-014 | JWT security | 15-min access, 7-day refresh, blacklist on logout | Token expiry enforced; refresh rotation |

#### Compliance

| ID | Requirement | Standard | Verification |
|---|---|---|---|
| REQ-COM-001 | Data minimization | GDPR Article 25 | PII stripping before AI; no unnecessary data collection |
| REQ-COM-002 | Right to erasure | GDPR Article 17 | Account deletion + hard delete + audit log |
| REQ-COM-003 | Right to data portability | GDPR Article 20 | JSON/PDF export endpoint |
| REQ-COM-004 | Consent capture | GDPR Article 7 | Checkbox on registration for privacy policy |
| REQ-COM-005 | Data retention | GDPR Article 5(1)(e) | Configurable retention; automated purge via Celery Beat |
| REQ-COM-006 | EU AI Act compliance | EU AI Act 2024 (adopted May 2024, effective Feb 2025) | Human-in-the-loop; transparency; bias monitoring |
| REQ-COM-007 | Accessibility | WCAG 2.1 AA | axe-core / pa11y testing in CI |
| REQ-COM-008 | Audit trail | GDPR Article 30 | Append-only audit log; 90-day retention |
| REQ-COM-009 | Privacy by design | GDPR Article 25 | PII stripping; encryption; default-deny permissions |

#### Maintainability & Operability

| ID | Requirement | Target | Measurement |
|---|---|---|---|
| REQ-NFR-019 | Test coverage | ≥ 80% | `pytest --cov=. --cov-fail-under=80` in CI |
| REQ-NFR-020 | Code formatting | 100% compliant | `black --check` and `flake8` in CI |
| REQ-NFR-021 | Type safety | 100% of new code | `mypy --strict` passes |
| REQ-NFR-022 | Import ordering | 100% compliant | `isort --check` in CI |
| REQ-NFR-023 | API documentation | Auto-generated, always current | drf-spectacular OpenAPI schema |
| REQ-NFOR-024 | Error tracking | 100% of exceptions captured | Sentry `send_default_pii=False` |
| REQ-NFOR-025 | Log format | Structured JSON | All logs parseable by ELK stack |
| REQ-NFOR-001 | Deployment rollback | < 5 min | `docker-compose up -d <previous_tag>` |
| REQ-NFOR-002 | Environment parity | Identical across dev/staging/prod | Docker Compose for dev; same containers for prod |

---

## 5. Data Architecture

### 5.1 Complete Database Schema (SQL)

```sql
-- === USERS ===
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,          -- Argon2id
    first_name      VARCHAR(150) NOT NULL ENCRYPTED,
    last_name       VARCHAR(150) NOT NULL ENCRYPTED,
    auth_provider   VARCHAR(20) DEFAULT 'email',    -- email, google, github
    email_verified  BOOLEAN DEFAULT FALSE,
    mfa_enabled     BOOLEAN DEFAULT FALSE,
    mfa_secret      BYTEA,                          -- encrypted TOTP secret
    locked_until    TIMESTAMPTZ,
    failed_login_attempts INTEGER DEFAULT 0,
    last_login      TIMESTAMPTZ,
    is_active       BOOLEAN DEFAULT TRUE,
    is_staff        BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- === CANDIDATE PROFILES ===
CREATE TABLE candidate_profiles (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    title           VARCHAR(200),                   -- "Senior Software Engineer"
    bio             TEXT,
    location        TEXT ENCRYPTED,                 -- AES-256-GCM
    remote_ok       BOOLEAN DEFAULT TRUE,
    skills          JSONB DEFAULT '[]',             -- [{"name":"Python","level":"expert","source":"self_reported"}]
    journey_timeline JSONB DEFAULT '[]',            -- structured career timeline
    match_scores    JSONB DEFAULT '{}',             -- {job_id: score} for quick lookups
    resume_embedding VECTOR(384),                   -- pgvector embedding
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE candidate_resumes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id    UUID REFERENCES candidate_profiles(id) ON DELETE CASCADE,
    file_key        VARCHAR(500) NOT NULL,          -- S3 key (UUID-based name)
    original_filename TEXT ENCRYPTED,               -- encrypted
    file_size       INTEGER,
    mime_type       VARCHAR(100),
    extracted_text  TEXT,                          -- PII-stripped text
    raw_text_hash   VARCHAR(64),                    -- for deduplication
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- === EMPLOYER PROFILES ===
CREATE TABLE employer_profiles (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    company_name    TEXT ENCRYPTED,                 -- AES-256-GCM
    industry        VARCHAR(100),
    company_size    INTEGER,
    show_company_name BOOLEAN DEFAULT FALSE,      -- REQ-FR-042: public board shows the company
                                                      -- name only after the employer opts in. Off by default,
                                                      -- because "who is hiring" is itself information.
    billing_plan    VARCHAR(20) DEFAULT 'free',
    billing_cycle   VARCHAR(10) DEFAULT 'monthly',
    stripe_customer_id TEXT ENCRYPTED,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE employer_team_members (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employer_id     UUID REFERENCES employer_profiles(id) ON DELETE CASCADE,
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    role            VARCHAR(20) NOT NULL DEFAULT 'interviewer',
    invited_by      UUID REFERENCES users(id) ON DELETE SET NULL,
    invite_status   VARCHAR(20) NOT NULL DEFAULT 'pending',
    mfa_enforced    BOOLEAN DEFAULT TRUE,
    joined_at       TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_employer_team_member UNIQUE (employer_id, user_id),
    CONSTRAINT ck_team_role CHECK (role IN ('employer_manager','employer_hr','interviewer')),
    CONSTRAINT ck_invite_status CHECK (invite_status IN ('pending','accepted','revoked'))
);
CREATE INDEX idx_team_employer ON employer_team_members(employer_id);
CREATE INDEX idx_team_user ON employer_team_members(user_id);

CREATE TABLE subscriptions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employer_id     UUID REFERENCES employer_profiles(id) ON DELETE CASCADE,
    plan            VARCHAR(20) DEFAULT 'free',
    stripe_customer_id TEXT ENCRYPTED,
    stripe_subscription_id TEXT ENCRYPTED,
    current_period_end TIMESTAMPTZ,
    ai_quota_remaining INTEGER DEFAULT 50,
    ai_quota_reset_date TIMESTAMPTZ,
    max_jobs        INTEGER DEFAULT 3,
    jobs_used       INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- === JOBS & APPLICATIONS ===
CREATE TABLE jobs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employer_id     UUID REFERENCES employer_profiles(id) ON DELETE CASCADE,
    title           VARCHAR(300) NOT NULL,
    description     TEXT,
    responsibilities TEXT,
    requirements    TEXT,
    nice_to_have    TEXT,
    location        VARCHAR(200),
    remote_allowed  BOOLEAN DEFAULT FALSE,
    experience_level VARCHAR(20),                  -- entry, intermediate, senior, lead
    status          VARCHAR(20) DEFAULT 'draft',   -- draft, active, paused, closed
    description_embedding VECTOR(384),              -- pgvector
    screening_questions JSONB DEFAULT '[]',
    screening_config JSONB DEFAULT '{}',            -- G3: stage-1 hard-filter rule set {"filters": {...}}
    screening_config_version INTEGER DEFAULT 1,     -- G3: increments on every rule edit; stamped onto each application
    ai_model_used   VARCHAR(100),
    cost_estimate   DECIMAL(10,4),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE applications (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id          UUID REFERENCES jobs(id) ON DELETE CASCADE,
    candidate_id    UUID REFERENCES candidate_profiles(id) ON DELETE CASCADE,
    status          VARCHAR(20) DEFAULT 'applied',  -- applied, screened, not_matched, shortlisted, interview, offered, hired, rejected
    match_score     INTEGER,                       -- 0-100 from AI
    match_rationale TEXT,                          -- AI-generated explanation
    ai_model_used   VARCHAR(100),
    screened_at     TIMESTAMPTZ,
    shortlisted_at  TIMESTAMPTZ,
    -- Gap G3: the stage-1 hard filter records what it excluded and under which
    -- rule-set version, and the employer can always pull the candidate back.
    not_matched_reason   TEXT,                     -- which rule fired, e.g. experience_level
    filter_rules_version INTEGER,                  -- = jobs.screening_config_version at screening time
    -- Gap G1: employer-required assessments gate the shortlist.
    assessment_gate_status VARCHAR(20) DEFAULT 'not_required', -- not_required, pending, passed, failed
    -- Gap G2: a decision that goes against the ranking is recorded, not prevented.
    decision_override        BOOLEAN DEFAULT FALSE,
    decision_override_reason TEXT,                 -- required whenever decision_override is TRUE
    decided_by               UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(job_id, candidate_id),
    -- A recorded override must always carry a reason. Enforced in the database, not only in the form.
    CONSTRAINT chk_override_has_reason CHECK (
        decision_override = FALSE OR (decision_override_reason IS NOT NULL AND length(btrim(decision_override_reason)) > 0)
    )
);

CREATE INDEX idx_applications_gate ON applications(assessment_gate_status);

-- === SKILLS & CERTIFICATIONS ===
CREATE TABLE skills (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    canonical_name  VARCHAR(100) UNIQUE NOT NULL,   -- "JavaScript"
    aliases         JSONB DEFAULT '[]',             -- ["JS", "ECMAScript", "Node.js"]
    category        VARCHAR(50),                   -- programming, soft_skill, domain
    description     TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE candidate_skills (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id    UUID REFERENCES candidate_profiles(id) ON DELETE CASCADE,
    skill_id        UUID REFERENCES skills(id) ON DELETE CASCADE,
    level           VARCHAR(20),                   -- beginner, intermediate, expert
    years_experience DECIMAL(3,1),
    source          VARCHAR(30),                   -- resume_parse, self_reported, assessment, journey_map
    verified        BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(candidate_id, skill_id)
);

CREATE TABLE certifications (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id    UUID REFERENCES candidate_profiles(id) ON DELETE CASCADE,
    name            VARCHAR(200) NOT NULL,
    issuing_organization VARCHAR(200),
    issue_date      DATE,
    expiry_date     DATE,
    credential_id   TEXT ENCRYPTED,
    credential_url  VARCHAR(500),
    verified        BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- === ASSESSMENTS ===
CREATE TABLE assessments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title           VARCHAR(300) NOT NULL,
    description     TEXT,
    skill_id        UUID REFERENCES skills(id),
    difficulty      VARCHAR(20),                  -- beginner, intermediate, advanced
    question_count  INTEGER DEFAULT 10,
    time_limit_minutes INTEGER DEFAULT 30,
    is_active       BOOLEAN DEFAULT TRUE,
    created_by      UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE assessment_questions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_id   UUID REFERENCES assessments(id) ON DELETE CASCADE,
    question_type   VARCHAR(20),                 -- multiple_choice, coding, text
    question_text   TEXT NOT NULL,
    options         JSONB DEFAULT '[]',           -- for multiple choice
    correct_answer  TEXT,
    code_language   VARCHAR(20),                 -- for coding challenges
    max_score       INTEGER DEFAULT 10
);

CREATE TABLE assessment_attempts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id    UUID REFERENCES candidate_profiles(id) ON DELETE CASCADE,
    assessment_id   UUID REFERENCES assessments(id) ON DELETE CASCADE,
    started_at      TIMESTAMPTZ DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,
    score           DECIMAL(5,2),
    status          VARCHAR(20) DEFAULT 'in_progress',
    answers         JSONB DEFAULT '[]'
);

-- === EMPLOYER-REQUIRED ASSESSMENTS (Gap G1, REQ-FR-051) ===
-- An employer attaches an assessment to a job as a step that must be completed
-- before shortlist. Reuses the existing assessments/assessment_attempts pair: the
-- gate is satisfied by matching candidate + assessment on a completed attempt.
CREATE TABLE job_assessment_requirements (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id          UUID REFERENCES jobs(id) ON DELETE CASCADE,
    assessment_id   UUID REFERENCES assessments(id) ON DELETE CASCADE,
    min_score       DECIMAL(5,2),                  -- pass mark; NULL = any completed attempt satisfies it
    sort_order      INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(job_id, assessment_id)
);

CREATE INDEX idx_job_assessment_req_job ON job_assessment_requirements(job_id);

-- === INTERVIEWS ===
CREATE TABLE interview_packs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id          UUID REFERENCES jobs(id) ON DELETE CASCADE,
    title           VARCHAR(300),
    questions       JSONB DEFAULT '[]',
    scoring_rubric  JSONB DEFAULT '[]',
    ai_model_used   VARCHAR(100),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    is_active       BOOLEAN DEFAULT TRUE
);

CREATE TABLE interviews (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id  UUID REFERENCES applications(id) ON DELETE CASCADE,
    interview_pack_id UUID REFERENCES interview_packs(id) ON DELETE SET NULL,
    scheduled_at    TIMESTAMPTZ NOT NULL,
    duration_minutes INTEGER DEFAULT 45,
    status          VARCHAR(20) DEFAULT 'scheduled',
    video_call_url  VARCHAR(500),
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE interview_feedback (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    interview_id    UUID REFERENCES interviews(id) ON DELETE CASCADE,
    interviewer_id  UUID REFERENCES users(id),
    scores          JSONB DEFAULT '{}',
    comments        TEXT,
    overall_recommendation VARCHAR(20),
    submitted_at    TIMESTAMPTZ DEFAULT NOW()
);

-- === COMMUNICATION ===
CREATE TABLE messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id  UUID REFERENCES applications(id) ON DELETE SET NULL,
    sender_id       UUID REFERENCES users(id) ON DELETE SET NULL,
    recipient_id    UUID REFERENCES users(id) ON DELETE SET NULL,
    content         TEXT NOT NULL,
    read            BOOLEAN DEFAULT FALSE,
    -- Soft delete (REQ-FR-043): a user's GDPR erasure must not delete the
    -- counterparty's copy of a conversation. Rows are retained with the
    -- content blanked and the party references nulled.
    deleted_at      TIMESTAMPTZ,
    deleted_by_user BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_messages_thread ON messages(application_id, created_at);
CREATE INDEX idx_messages_recipient ON messages(recipient_id, read);

CREATE TABLE notifications (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recipient_id    UUID REFERENCES users(id) ON DELETE CASCADE,
    title           VARCHAR(200),
    message         TEXT,
    notification_type VARCHAR(30),
    read            BOOLEAN DEFAULT FALSE,
    url             VARCHAR(500),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- === BROADCAST ANNOUNCEMENTS (REQ-FR-050) ===
-- Added 2026-10-03. REQ-FR-050 was approved in scope, given a page (#62) and an endpoint,
-- but had **no table**: nothing could store the announcement, its audience, its schedule,
-- or which users it reached. `notifications` cannot substitute — it is per-recipient with
-- a single `recipient_id`, so it can record a delivery but never the broadcast itself.
-- The requirement was unimplementable as written.
CREATE TABLE announcements (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title           VARCHAR(200) NOT NULL,
    body            TEXT NOT NULL,
    audience        VARCHAR(30) NOT NULL DEFAULT 'all',  -- all, candidates, employers, employers_by_plan, custom
    audience_filter JSONB DEFAULT '{}',                -- the resolved predicate, e.g. {"plan": ["growth"]}
    channel         VARCHAR(20) NOT NULL DEFAULT 'in_app',  -- in_app, email, both
    status          VARCHAR(20) NOT NULL DEFAULT 'draft',   -- draft, scheduled, sending, sent, failed, cancelled
    scheduled_at    TIMESTAMPTZ,
    sent_at         TIMESTAMPTZ,
    recipient_count INTEGER DEFAULT 0,                -- resolved at send time, not at create time
    skipped_count   INTEGER DEFAULT 0,                -- suppressed: deleted, bounced or unsubscribed
    failure_detail  TEXT,
    created_by      UUID REFERENCES users(id) ON DELETE SET NULL,  -- SET NULL: the record survives the admin account
    idempotency_key UUID UNIQUE,                      -- Celery Beat retry must not double-send
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_announcements_status ON announcements(status, scheduled_at);
CREATE INDEX idx_announcements_sent ON announcements(sent_at);

-- === COMPLIANCE ===
CREATE TABLE data_export_requests (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    status          VARCHAR(20) DEFAULT 'pending',
    file_key        VARCHAR(500),
    requested_at    TIMESTAMPTZ DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ
);

CREATE TABLE data_deletion_requests (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE SET NULL,
    reason          TEXT,
    requested_at    TIMESTAMPTZ DEFAULT NOW(),
    processed_at    TIMESTAMPTZ,
    approved_by     UUID REFERENCES users(id) ON DELETE SET NULL,  -- REQ-FR-041: erasure is
                                        -- admin-approved, not self-service. A candidate-facing
                                        -- DELETE would also destroy the employer's own
                                        -- application history, which is their record too.
    status          VARCHAR(20) DEFAULT 'pending',  -- pending, approved, rejected, completed
    UNIQUE (user_id, status)
);

-- === AUDIT LOG (append-only) ===
CREATE TABLE audit_log_entries (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_id        UUID REFERENCES users(id) ON DELETE SET NULL,
    action          VARCHAR(100) NOT NULL,
    resource_type   VARCHAR(50),
    resource_id     UUID,
    details         JSONB DEFAULT '{}',
    ip_address      INET,
    user_agent      VARCHAR(500),
    result          VARCHAR(20),
    created_at      TIMESTAMPTZ DEFAULT NOW()
) WITH (fillfactor=100);

CREATE INDEX idx_audit_created ON audit_log_entries(created_at);
CREATE INDEX idx_audit_resource ON audit_log_entries(resource_type, resource_id);
CREATE INDEX idx_audit_action ON audit_log_entries(action, created_at);

-- pgvector indexes for similarity search
CREATE INDEX idx_jobs_embedding ON jobs USING hnsw (description_embedding vector_cosine_ops);
CREATE INDEX idx_candidates_embedding ON candidate_profiles USING hnsw (resume_embedding vector_cosine_ops);
```

### 5.2 Entity Relationship Summary

```
users (1) ──(1)──> candidate_profiles │ employer_profiles
                   │                    │
                   ├──(N)──> candidate_skills ──(N)──> skills
                   ├──(N)──> candidate_resumes
                   ├──(N)──> certifications
                   ├──(N)──> assessment_attempts ──(N)──> assessments ──(N)──> assessment_questions
                   └──(N)──> applications ──(N)──> jobs
                                          ├──(N)──> interview_feedback
                                          ├──(N)──> messages
                                          └──(N)──> interviews ──(N)──> interview_packs

employer_profiles ──(1)──> subscriptions
                    ├──(N)──> jobs
                    └──(N)──> interview_feedback (as interviewer)

users ──(N)──> notifications
users ──(N)──> messages (sent + received)
users ──(1)──> data_export_requests
users ──(0..1)──> data_deletion_requests
users ──(N)──> audit_log_entries
```

### 5.3 Sequence Diagram: AI Screening Flow

```
Employer   Django     Redis     Celery     OpenRouter    pgvector     spaCy NER
   │         │          │          │            │            │           │
   │ POST /jobs/{id}/screen/     │          │            │            │           │
   │─────────▶│          │          │            │            │           │
   │         │ Queue task          │            │            │            │           │
   │         │─────────▶│          │            │            │            │           │
   │         │          │          │            │            │            │           │
   │         │ Return cost estimate│            │            │            │           │
   │         │ ◀────────          │            │            │            │           │
   │         │ Display $0.00       │            │            │            │           │
   │     Show confirmation        │            │            │            │           │
   │         │          │          │            │            │            │           │
   │    [User confirms]           │            │            │            │           │
   │         │          │          │            │            │            │           │
   │         │ Queue batch tasks  │            │            │            │            │           │
   │         │─────────▶│          │            │            │            │            │           │
   │         │          │          │ Dequeue    │            │            │            │           │
   │         │          │          │─────────▶│            │            │            │           │
   │         │          │          │            │ Strip PII│            │            │           │
   │         │          │          │            │─────────▶│           │            │           │
   │         │          │          │            │          │            │           │ NER identifies
   │         │          │          │            │          │ ◀─────── │            │ names, emails,
   │         │          │          │            │          │                    │ phones, locations
   │         │          │          │            │          │                    │
   │         │          │          │            │ Generate │                    │
   │         │          │          │            │ embeddings│                    │
   │         │          │          │            │─────────▶│                    │
   │         │          │          │            │          │ Store vec        │
   │         │          │          │            │          │─────────▶│
   │         │          │          │            │ ←─────── │                    │
   │         │          │          │            │          │                    │
   │         │          │          │ Compute    │            │                    │
   │         │          │          │ cosine sim │            │                    │
   │         │          │          │─────────▶│            │                    │
   │         │          │          │          │←───────────│                    │
   │         │          │          │ Rank       │            │                    │
   │         │          │          │ results    │            │                    │
   │         │          │          │          │            │                    │
   │         │          │          │ Call LLM   │            │                    │
   │         │          │          │─────────▶│            │                    │
   │         │          │          │            │ Analyze  │                    │
   │         │          │          │            │ anonymized│                    │
   │         │          │          │            │ data      │                    │
   │         │          │          │            │←───────── │                    │
   │         │          │          │            │            │                    │
   │         │          │ Store    │            │            │                    │
   │         │          │─────────▶│            │            │                    │
   │         │ Return   │          │            │            │                    │
   │         │ ranked   │          │            │            │                    │
   │         │ results  │          │            │            │                    │
   │         │◀──────── │          │            │            │                    │
   │         │ Notify   │          │            │            │                    │
   │         │ employer │          │            │            │                    │
   │         │◀──────── │          │            │            │                    │
```

### 5.4 Caching Strategy

Redis is used for three distinct purposes with different TTLs and eviction policies:

| Cache Key Pattern | TTL | Content | Eviction |
|---|---|---|---|
| `user_profile:{user_id}` | 1 hour | Serialized user + profile + candidate/employer data | LRU |
| `job_embeddings:{job_id}` | 24 hours | Pre-computed pgvector embedding for job description | LRU |
| `similarity_matrix:{job_id}` | 2 hours | Cached candidate-job similarity scores | LRU |
| `rate_limit:{user_id}:{endpoint}` | 15 minutes | Rate limit counters | TTL expiry |
| `openrouter_quota:{day}` | 24 hours (resets at midnight UTC) | Daily free tier usage tracker | TTL expiry |
| `skill_taxonomy:v1` | 7 days (versioned) | Canonical skill name mappings | Versioned override |
| `ai_response:{hash}` | 6 hours | Cached LLM responses (deduplication by prompt hash) | LRU |

**Cache Invalidation Rules:**
- Job update → invalidate `job_embeddings:{job_id}` + `similarity_matrix:{job_id}`
- Resume re-upload → invalidate `user_profile:{user_id}`
- Skill update → invalidate `user_profile:{user_id}` (candidate side only)
- Daily midnight → reset `openrouter_quota:{day}`

---

## 6. CI/CD & Deployment

### 6.1 Docker Compose (Development)

```yaml
# docker-compose.yml
version: "3.9"

services:
  postgres:
    image: pgvector/pgvector:pg17
    container_name: fairfold-postgres
    environment:
      POSTGRES_DB: fairfold_dev
      POSTGRES_USER: fairfold
      POSTGRES_PASSWORD: ${DB_PASSWORD:-devpassword}
    volumes:
      - pg_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U fairfold"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: fairfold-redis
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  clamav:
    # ADDED 2026-10-03 (gap P). The resume-upload path REJECTS a file when ClamAV is
    # unreachable rather than passing it through unscanned (.env.example), so without this
    # service every upload fails in development. clamav/clamav ships its own definitions and
    # daemon; the "freshclam" entrypoint updates them on start.
    image: clamav/clamav:1.4
    container_name: fairfold-clamav
    ports:
      - "3310:3310"
    healthcheck:
      test: ["CMD-SHELL", "clamdcheck.sh || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 10
      start_period: 60s

  django:
    build: .
    container_name: fairfold-django
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      clamav:
        condition: service_healthy
    env_file: .env
    environment:
      DATABASE_URL: postgresql://fairfold:${DB_PASSWORD:-devpassword}@postgres:5432/fairfold_dev
      REDIS_URL: redis://redis:6379/0
      CELERY_BROKER_URL: redis://redis:6379/0
      CELERY_RESULT_BACKEND: redis://redis:6379/1
      CLAMD_HOST: clamav
      CLAMD_PORT: 3310
    volumes:
      - .:/app
      - media_data:/app/media
    ports:
      - "8000:8000"
    command: >
      sh -c "
        python manage.py migrate &&
        python manage.py runserver 0.0.0.0:8000
      "

  celery:
    build: .
    container_name: fairfold-celery
    depends_on:
      - redis
      - postgres
    env_file: .env
    environment:
      DATABASE_URL: postgresql://fairfold:${DB_PASSWORD:-devpassword}@postgres:5432/fairfold_dev
      REDIS_URL: redis://redis:6379/0
      CELERY_BROKER_URL: redis://redis:6379/0
      CELERY_RESULT_BACKEND: redis://redis:6379/1
    volumes:
      - .:/app
    command: celery -A config worker -l info

  celery-beat:
    build: .
    container_name: fairfold-celery-beat
    depends_on:
      - celery
    env_file: .env
    environment:
      DATABASE_URL: postgresql://fairfold:${DB_PASSWORD:-devpassword}@postgres:5432/fairfold_dev
      REDIS_URL: redis://redis:6379/0
      CELERY_BROKER_URL: redis://redis:6379/0
      CELERY_RESULT_BACKEND: redis://redis:6379/1
    volumes:
      - .:/app
    command: celery -A config beat -l info

  nginx:
    image: nginx:1.25-alpine
    container_name: fairfold-nginx
    depends_on:
      - django
    ports:
      - "8080:80"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/conf.d/default.conf:ro
      - media_data:/app/media
    command: "/bin/sh -c 'while true; do sleep 30; done'"
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:80/health/ || exit 1"]
      interval: 30s
      timeout: 5s
      retries: 3

volumes:
  pg_data:
  media_data:
```

> **Container names:** every service sets an explicit `container_name`, so the containers can be addressed by a stable name regardless of the Compose project directory. This is what the README's `docker exec -it fairfold-django ...` commands rely on.

| Service | Container name | Port |
|---|---|---|
| `postgres` | `fairfold-postgres` | 5432 |
| `redis` | `fairfold-redis` | 6379 |
| `django` | `fairfold-django` | 8000 |
| `celery` | `fairfold-celery` | — |
| `celery-beat` | `fairfold-celery-beat` | — |
| `nginx` | `fairfold-nginx` | 8080 |
| `clamav` | `fairfold-clamav` | 3310 |

### 6.2 Production Dockerfile

```dockerfile
# ---- Stage 1: frontend build (ADDED 2026-10-03, gap O) ----
# design.md §11.2 requires Tailwind to be compiled to a static CSS file so the CSP can
# drop the CDN and `unsafe-inline`. That compile needs a Node toolchain, but Node must
# NOT be in the final image. So it lives in a throwaway stage whose only output is
# static/css/tailwind.css and static/js/*.min.js.
FROM node:20-alpine AS assets

WORKDIR /build
COPY package.json package-lock.json* ./
RUN npm ci --no-audit --no-fund
COPY tailwind.config.js postcss.config.js* ./
COPY templates/ ./templates/
COPY static/ ./static/
RUN npm run build

# ---- Stage 2: runtime ----
FROM python:3.12-slim

# System dependencies.
#   libmagic1    — python-magic is a pip package wrapping this system library; without it
#                  the module fails at import.
#   clamav-daemon — the upload path REJECTS a file when ClamAV is unreachable rather than
#                  passing it through unscanned, so this must be present in the image even
#                  where the daemon itself runs as a separate service.
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    libmagic1 \
    clamav-daemon \
    && rm -rf /var/lib/apt/lists/*

# torch is installed CPU-only. requirements.txt carries
# --extra-index-url https://download.pytorch.org/whl/cpu for local installs; here it is
# explicit, because the default CUDA wheel adds several GB to the image for hardware this
# project does not target (prd.md §18.2 — a 2-4 vCPU VPS).

# Create non-root user
RUN groupadd -r fairfold && useradd -r -g fairfold fairfold

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY --chown=fairfold:fairfold . /app
# Built frontend assets from stage 1. Copied *after* the application code on purpose:
# COPY . /app would otherwise overwrite the compiled files with whatever is in the working
# tree, and the compiled CSS is the artefact the CSP depends on.
COPY --from=assets --chown=fairfold:fairfold /build/static/ /app/static/
WORKDIR /app

# Collect static files
RUN python manage.py collectstatic --noinput

# Switch to non-root user
USER fairfold

# Gunicorn
EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120", "config.wsgi:application"]
```

### 6.3 Nginx Configuration (Production)

```nginx
# nginx/nginx.conf
upstream django {
    server django:8000;
}

server {
    listen 80;
    server_name fairfold.com www.fairfold.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name fairfold.com www.fairfold.com;

    # SSL (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/fairfold.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/fairfold.com/privkey.pem;
    ssl_protocols TLSv1.3 TLSv1.2;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self' https://openrouter.ai; font-src 'self';" always;
    add_header Permissions-Policy "camera=(), microphone=()" always;

    # Static and media files
    location /static/ {
        alias /app/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias /app/media/;
        expires 1h;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=1000r/m;

    # API rate limiting
    location /api/ {
        limit_req zone=api_limit burst=100 nodelay;
        proxy_pass http://django;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }

    # Health check
    location /health/ {
        proxy_pass http://django;
        access_log off;
    }

    # Main app
    location / {
        proxy_pass http://django;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 6.4 Kubernetes Helm Values (Production)

```yaml
# helm/values.yaml
replicaCount: 3

image:
  repository: fairfold/app
  tag: latest
  pullPolicy: Always

django:
  workers: 4
  gunicornTimeout: 120
  secretKey: # Set via Kubernetes Secret

celery:
  workerReplicas: 2
  aiWorkerReplicas: 2
  beatEnabled: true

redis:
  architecture: standalone
  auth:
    enabled: true
    existingSecret: redis-secret
  metrics:
    enabled: true

postgresql:
  image:
    repository: pgvector/pgvector
    tag: pg17
  auth:
    existingSecret: postgres-secret
  primary:
    persistence:
      enabled: true
      size: 20Gi
      storageClass: gp2
  metrics:
    enabled: true

s3:
  endpointUrl: https://s3.amazonaws.com  # or MinIO
  bucketName: fairfold-production
  region: us-east-1

resources:
  limits:
    cpu: "2"
    memory: 4Gi
  requests:
    cpu: "500m"
    memory: 1Gi

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80
```

### 6.5 CI/CD Pipeline (GitHub Actions)

```yaml
# .github/workflows/ci-cd.yml
name: CI/CD Pipeline
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

concurrency:
  group: build-and-deploy
  cancel-in-progress: true

jobs:
  lint-and-test:
    runs-on: ubuntu-24.04
    services:
      postgres:
        image: pgvector/pgvector:pg17
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_USER: postgres
          POSTGRES_DB: fairfold_test
        options: >-
          --health-cmd "pg_isready -U postgres"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 5
        ports: ["5432:5432"]
      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 5s
          --health-timeout 3s
          --health-retries 5
        ports: ["6379:6379"]
      clamav:
        # ADDED 2026-10-03 (gap P). The upload path rejects a file when ClamAV is
        # unreachable rather than passing it unscanned, so without this service every
        # upload test fails for the wrong reason. `start_period` is generous because
        # freshclam downloads definitions on first boot.
        image: clamav/clamav:1.4
        ports: ["3310:3310"]
        options: >-
          --health-cmd "clamdcheck.sh"
          --health-interval 30s
          --health-timeout 10s
          --health-retries 10
          --health-start-period 60s

    steps:
      - uses: actions/checkout@v4

      - name: Install OS dependencies
        # python-magic binds to libmagic; it is a pip package wrapping a system library,
        # so pip alone is not enough and the job fails at import otherwise.
        run: sudo apt-get update && sudo apt-get install -y libmagic1

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt -r requirements-dev.txt

      - name: Install spaCy model
        run: python -m spacy download en_core_web_sm

      # ADDED 2026-10-03 (gap O). There is no SPA, but there is a compiled CSS file:
      # design.md §11.2 requires Tailwind to be built to a static file rather than loaded
      # from the CDN, so the CSP can drop `unsafe-inline`. Without this step CI would test
      # a stylesheet that does not exist in production, and a broken tailwind.config.js
      # would only be discovered at deploy time. This runs before the Django steps because
      # `collectstatic` and the template tests both read static/css/tailwind.css.
      - name: Set up Node
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - name: Install frontend dependencies
        run: npm ci --no-audit --no-fund

      - name: Build frontend assets
        run: npm run build

      - name: Fail if built CSS exceeds the size budget
        # design.md §11.4 budgets built CSS at < 30 KB gzipped. A missing content glob in
        # tailwind.config.js silently produces a near-empty stylesheet, which passes every
        # other check in this job, so the budget is asserted rather than trusted.
        run: |
          gzip -c static/css/tailwind.css | wc -c | awk '{ if ($1 >= 30720) { print "::error::tailwind.css is " $1 " bytes gzipped, budget is 30720"; exit 1 } }'

      # NOTE 2026-10-03: these commands previously targeted `fairfold/`, which is the
      # repository name, not a directory. The Django project package is `config/` and the
      # apps are top-level packages (Complete Doc §4.2). `bandit.yaml` and `pyproject.toml`
      # (black/isort/mypy config) must exist at the repository root for these to run.

      - name: Lint — flake8
        run: flake8 config/ core/ accounts/ candidates/ employers/ matching/ assessments/ interviews/ notifications/ api/ admin/ journey/ ai/ --max-line-length=120

      - name: Lint — black (check)
        run: black --check .

      - name: Lint — isort (check)
        run: isort --check-only .

      - name: Type check — mypy
        run: mypy config/ core/ accounts/ candidates/ employers/ matching/ ai/ --ignore-missing-imports

      - name: Security scan — bandit
        run: bandit -r . -c bandit.yaml

      - name: Dependency audit — pip-audit
        run: pip-audit -r requirements.txt

      - name: Licence scan — REQ-COM / RSK-012
        # Added 2026-10-03. AI-assisted development can reproduce a known or non-OSI
        # implementation, and the product claims it does not assert anything it cannot
        # evidence. A licence check is the cheapest way to keep that claim honest.
        run: |
          pip install licensedb
          licensedb cache
          licensedb report --format csv --packages . > licence-report.csv
          licensedb whitelist --from-file=licensedb.yml || true

      - name: Run tests
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/fairfold_test
          REDIS_URL: redis://localhost:6379/0
          CLAMD_HOST: localhost
          CLAMD_PORT: 3310
          DJANGO_SETTINGS_MODULE: config.settings.ci
        run: |
          # `--check` fails if any model change has no committed migration, which is the
          # only thing that actually enforces the Complete Doc §C.8.1 rule that migration
          # files are generated and committed rather than hand-crafted per-PR.
          python manage.py makemigrations --check --dry-run
          python manage.py migrate
          python manage.py seed
          python manage.py collectstatic --noinput --clear
          pytest tests/ -v --cov=. --cov-fail-under=80

      - name: Generate OpenAPI schema
        run: python manage.py spectacular --file schema.yml

      - name: Documentation consistency check
        # Added 2026-10-03. The six documents state the same figures in many places,
        # and those figures had already drifted twice (34 -> 35 FKs, 212 -> 217 points)
        # plus a live team-size figure in an ADR that an earlier pass had missed. Reading
        # the docs does not catch that; running the checker does.
        run: python3 scripts/verify_docs.py

      - name: Bias test set consistency check
        # Validates the fixture set, NOT the bias pass -- there is no implementation to
        # validate yet, so this asserts nothing about accuracy. It proves the cases are
        # internally coherent: every declared term exists, no must-not-flag case contains
        # a term, category counts match §7.4.3, and the manifest's keyword_list_sha matches
        # the term list it hashes.
        run: python3 scripts/verify_bias_set.py

      - name: Upload schema artifact
        uses: actions/upload-artifact@v4
        with:
          name: openapi-schema
          path: schema.yml

  build-and-push:
    needs: lint-and-test
    runs-on: ubuntu-24.04
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - name: Log in to Docker Hub
        run: echo "${{ secrets.DOCKERHUB_TOKEN }}" | docker login -u ${{ secrets.DOCKERHUB_USER }} --password-stdin
      - name: Build and push
        uses: docker/build-push-action@v6
        with:
          context: .
          push: true
          tags: fairfold/app:${{ github.sha }},fairfold/app:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max

  deploy-staging:
    needs: build-and-push
    runs-on: ubuntu-24.04
    if: github.ref == 'refs/heads/main'
    environment: staging
    steps:
      - name: Deploy to staging
        run: |
          ssh "${{ secrets.STAGING_USER }}@${{ secrets.STAGING_HOST }}" \
            "docker-compose pull && docker-compose up -d --wait"
      - name: Smoke test
        run: |
          curl -f https://staging.fairfold.com/health/
          curl -f https://staging.fairfold.com/api/v1/jobs/

  deploy-production:
    needs: deploy-staging
    runs-on: ubuntu-24.04
    if: github.ref == 'refs/heads/main'
    environment: production
    steps:
      - name: Deploy to production
        run: |
          ssh "${{ secrets.PROD_USER }}@${{ secrets.PROD_HOST }}" \
            "docker-compose pull && docker-compose up -d --wait"
      - name: Health check
        run: |
          curl -f https://app.fairfold.com/health/

  rollback-staging:
    runs-on: ubuntu-24.04
    needs: build-and-push
    if: github.event_name == 'workflow_dispatch'
    environment: staging
    steps:
      - name: Rollback to previous image
        run: |
          ssh "${{ secrets.STAGING_USER }}@${{ secrets.STAGING_HOST }}" \
            "docker image tag fairfold/app:$(git rev-parse --short HEAD~1) fairfold/app:latest && docker-compose up -d --wait"
      - name: Post-rollback health check
        run: curl -f https://staging.fairfold.com/health/

  rollback-production:
    runs-on: ubuntu-24.04
    needs: build-and-push
    if: github.event_name == 'workflow_dispatch'
    environment: production
    steps:
      - name: Rollback to previous image
        run: |
          ssh "${{ secrets.PROD_USER }}@${{ secrets.PROD_HOST }}" \
            "docker image tag fairfold/app:$(git rev-parse --short HEAD~1) fairfold/app:latest && docker-compose up -d --wait"
      - name: Post-rollback health check
        run: curl -f https://app.fairfold.com/health/
```

> **Rollback strategy:** Each successful production deploy tags the current image with `github.sha`. The rollback job retags the *previous* commit's image as `:latest` and redeploys via `docker-compose`. Manual trigger via GitHub Actions "Run workflow" button. Target rollback time: < 5 minutes.

---

## 7. Testing Strategy

### 7.1 Test Pyramid

| Layer | Tools | Target | Coverage |
|---|---|---|---|
| Unit tests | pytest, pytest-django | Individual functions/methods | 80%+ |
| Integration tests | pytest, factory-boy, TestClient | API endpoints, DB interactions | 100% of critical paths |
| Contract tests | pytest | AI provider abstractions | 100% interfaces |
| Security tests | bandit, pip-audit, OWASP ZAP | All code, all dependencies | Zero critical/high |
| Load tests | Locust | 1,000 concurrent users | 95th percentile < 500ms |
| Accessibility tests | axe-core, pa11y | All HTML pages | WCAG 2.1 AA pass |

### 7.2 Test File Structure

```
tests/
├── __init__.py
├── conftest.py                    # Pytest fixtures (DB, Redis, test users)
├── bias/                          # versioned bias test set — spec in §7.4, authored v1.0.0
│   ├── CHANGELOG.md               # what changed per version and why
│   ├── v1.0.0/
│   │   ├── manifest.json          # version + keyword_list_sha + case count + "measured": false
│   │   ├── keyword_terms.json     # 62 terms, 6 deliberate exclusions, 5 known limitations
│   │   ├── proxy_cases.jsonl      # 48 must_flag, categories 1-7
│   │   ├── negative_cases.jsonl   # 18 must_not_flag, categories 9-10
│   │   └── rationale_cases.jsonl  # 10 must_flag, category 8 (LLM pass only, not CI-gated)
│   └── test_bias_pass.py          # WRITTEN IN PHASE 2 — 100% recall, 0 FP, 60-95% flag rate
├── unit/
│   ├── test_pii_stripping.py     # PII detection regex + NER accuracy tests
│   ├── test_matching.py           # pgvector cosine similarity correctness
│   ├── test_ai_provider.py        # Mock-based AI provider tests
│   └── test_utils.py              # Utility function tests
├── integration/
│   ├── test_auth_flows.py        # Registration, login, MFA, password reset
│   ├── test_candidate_flows.py   # Resume upload, journey mapping, assessments
│   ├── test_employer_flows.py    # Job creation, screening, interview packs
│   └── test_compliance.py        # GDPR export/deletion, audit logging
├── security/
│   ├── test_rbac.py              # Role-based access control
│   ├── test_rate_limiting.py     # Rate limit enforcement
│   └── test_data_encryption.py   # PII encryption/decryption
├── load/
│   ├── test_concurrent_apply.py  # 1000 concurrent job applications
│   └── test_ai_screening.py      # 100 concurrent screening tasks
└── accessibility/
    └── test_wcag.py              # axe-core scans on all pages
```

### 7.3 Key Test Scenarios

| Test | Type | Description |
|---|---|---|
| PII stripping accuracy | Unit | 95%+ of PII types (name, email, phone, location) correctly stripped from test resumes |
| Offline fallback | Contract | When OpenRouter returns 5xx, system uses pgvector + spaCy without user-facing error |
| Evidence-cited rationale | Integration | LLM rationale always contains specific resume text citations; no hallucinated claims |
| Bias audit pass rate | Integration | 100% of LLM rationales pass bias keyword check; flagged rationales are re-processed. **Measured against the versioned set in §7.4, not against examples the keyword list was written from** |
| Cost estimate accuracy | Unit | Estimated cost matches actual API cost within ±10% |
| Audit log completeness | Integration | Every screening action creates audit entry with timestamp, model, rationale hash |
| GDPR export | Integration | User can export all personal data as JSON/PDF; includes resume text, skills, applications |
| GDPR deletion | Integration | User deletion hard-deletes all PII; audit log retained (with user_id=null); data_export/deletion requests recorded |
| MFA enforcement | Integration | Employer admin accounts require TOTP; incorrect codes rejected; recovery codes work |
| Rate limiting | Security | 1000 req/hr user limit enforced; AI endpoints 20 req/min limit enforced; excess returns 429 |
| Concurrent applications | Load | 1000 candidates applying to same job simultaneously; no data loss; < 5 sec response |

### 7.4 Versioned Bias Test Set — Phase 2, owner Ishrak Hossain

**Specified 2026-10-03.** Until this file existed, the bias audit had no measurable
target: §7.3 says *"100% of LLM rationales pass bias keyword check"*, and the Phase 2
acceptance criterion says *"flags every seeded phrase in the versioned bias test set"* —
and there was no test set to seed. **A keyword list with no fixture set is a list that
can only be shown to work on the examples it was written from.**

#### 7.4.0 Status — **v1.0.0 authored 2026-10-03**

The cases are **written**. `tests/bias/v1.0.0/` holds **76 cases** — 58 must-flag, 18
must-not-flag — across all ten categories, with a 62-term proposal in
`keyword_terms.json`. `scripts/verify_bias_set.py` proves the set is internally
consistent and runs in CI.

> **The pass rate is still unmeasured, and the manifest says so.** There is no bias pass
> implementation in this repository. `pass_criteria` in the manifest are **targets**, not
> results, and `manifest.json` carries `"measured": false` for exactly that reason. The
> set being coherent says nothing about the pass being good.

| | |
|---|---|
| Cases | 76 (48 proxy · 18 negative · 10 rationale) |
| Terms | 62 across 8 groups, plus **6 deliberately excluded**, each naming the negative case that enforces it |
| Known limitations | **5** — `LIM-001`–`004` and `GAP-001`, each with a planned version |
| Most serious gap | **`LIM-003`: the term list is English-only.** The target market is Bangladesh, so a pass reading only English reports clean on exactly the population the product is for. v1.1.0, with native review rather than machine translation |
| Pass rate | **Not measured.** No implementation exists |

**Three findings from writing the cases.** Each is in `tests/bias/CHANGELOG.md` in full:

1. **The validator caught three authoring errors in the first draft** — cases whose
   `expected_terms` their own text did not contain (`PROXY-040` declared *not planning to
   marry* over text reading "no plans to marry"; `RAT-007` and `RAT-010` likewise). All
   three looked caught and were not. This is precisely the failure mode `expected_terms`
   exists to prevent: a keyword pass whose fixtures agree with it by construction reports
   a clean result forever.
2. **§7.4.3 itself contained a collision.** It listed *"recent graduate programme 2026"*
   as a must-NOT-flag example while *recent graduate* belongs in `age_reference`. The same
   phrase cannot both flag and not flag. Resolved by removing *recent graduate* from the
   term list and rewording `NEG-015` — and the underlying gap is **not** closed:
   graduation-year proximity is the mechanism behind the 2018 case, tracked as `LIM-002`.
3. **`GAP-001` is a deliberate non-fix.** Single-word vague and age-coded adjectives —
   *energetic, articulate, mature, ambitious, young, dynamic, passive* — are **not** terms.
   A rationale reading "Energetic and culturally aligned" is age-coded and **will not be
   flagged** by v1.0.0. Adding those words bare would flag ordinary professional text, and
   the zero-false-positive criterion is not negotiable. The gap is recorded rather than
   papered over, because an unwritten term is a known gap and a quietly widened list is an
   unnoticed one.

#### 7.4.1 What the set is for, and what it is not for

| The set measures | The set does **not** measure |
|---|---|
| Whether the deterministic keyword pass flags text it should flag | Whether FairFold is "bias-free", or unbiased, or fair in any statistical sense |
| Whether a proxy phrase survives PII stripping | Whether the *model* is biased, or whether outcomes differ across groups |
| Whether a regression in the keyword list is caught by CI | Anything publishable as a disparity statistic |

That second column is the reason the set is sized at tens of cases and not thousands.
**A 40-case fixture cannot support a disparity claim**, and §1.4.1 already records that
the product makes no such claim. A test set that quietly became a diversity statistic is
how a "bias-free" assertion creeps back in through the side door — the exact withdrawal
recorded in §2.22 of `HISTORY.md`.

#### 7.4.2 File layout and case format

```
tests/bias/
├── __init__.py
├── CHANGELOG.md              # one line per version: what was added and why
├── v1.0.0/
│   ├── manifest.json         # version, created, author, keyword_list_sha, case count
│   ├── proxy_cases.jsonl     # MUST-FLAG cases (the Amazon-style category)
│   ├── negative_cases.jsonl  # MUST-NOT-FLAG cases
│   └── rationale_cases.jsonl # uncited / vague-rationale cases (LLM pass only)
```

Versions are **immutable**. Fixing a case means adding `v1.0.1`, not editing `v1.0.0`,
so a CI run months later reproduces the set it thought it ran.

One JSON object per line:

```json
{
  "id": "PROXY-014",
  "category": "gendered_club_role",
  "text": "President, University Women's Society; organised the annual intra-faculty debate",
  "must_flag": true,
  "expected_terms": ["women's society"],
  "note": "A gendered organisation name in an otherwise strong CV. PII stripping removes the candidate's name and does not touch this.",
  "source_pattern": "Amazon 2018 - gendered club/society roles correlated with male-dominated technical roles"
}
```

**`expected_terms` is what makes this a test rather than a demo.** The keyword pass has to
flag the case *and* the case asserts which terms should have triggered it, so a keyword
list that flags everything still fails. Without it, "accuracy" on a flag-only test is
meaningless.

#### 7.4.3 Case categories

| # | Category | What it catches | `must_flag` | v1.0.0 target |
|---|---|---|---|---:|
| 1 | `gendered_club_role` | "President, University Women's Society", "women's sports captain" | ✅ true | 12 |
| 2 | `institution_gender_signal` | College names that correlate with gender in the labour market | ✅ true | 8 |
| 3 | `age_reference` | "young and energetic", "recent graduate", "must be under 30", "digital native" | ✅ true | 8 |
| 4 | `nationality_origin_proxy` | "Bangladeshi male", "native speaker", "must be from Dhaka" | ✅ true | 6 |
| 5 | `family_status` | "married", "no children", "young male preferred", "family responsibilities" | ✅ true | 6 |
| 6 | `disability_health` | "must be physically fit", "no glasses", "healthy and fit" | ✅ true | 4 |
| 7 | `photo_appearance` | "attach a photo", "formal appearance", "well-presented" | ✅ true | 4 |
| 8 | `uncited_vague_rationale` | "cultural fit", "not a team player", "seems junior", no resume text cited | ✅ true | 10 |
| 9 | `legitimate_skill_match` | A real skills match with no proxy language — must **not** flag | ❌ false | 12 |
| 10 | `necessary_context` | "Eligible for a women-only safety officer role", "must hold a valid visa", "co-founded a women's rights reading group" | ❌ false | 6 |

Categories 9 and 10 matter more than their size suggests. **A keyword pass that flags
everything reports a clean result by flagging the whole file**, and category 10 exists
specifically to stop someone "fixing" a false positive by deleting the case. In v1.0.0
these 18 cases also justify the **six deliberately-excluded terms**: each exclusion names
the case that enforces it, and the validator checks that link still holds.

#### 7.4.4 The Amazon-style proxy cases, and why PII stripping is not enough

The Amazon 2018 case (`Feasibility §1.2.1`) is in the specification for one reason. The
screening model did not use gender, age or college as features. It learned a proxy from
**the resume text itself** — activities, clubs, societies — which correlate with gender in
the applicant pool.

**Every one of those phrases survives PII stripping untouched.** The stripping pipeline
removes names, emails, phone numbers and locations. "President, University Women's
Society" contains none of those, so it passes through clean, is embedded, and is ranked.
This is the single most important thing the bias test set has to prove, and it is why
categories 1 and 2 are mandatory rather than aspirational.

The cases are **synthetic, in the same shape, with the source pattern recorded** in the
`source_pattern` field. That is a deliberate choice over quoting the published material
verbatim: the test needs the *shape* of the failure, not another company's wording
committed into this repository. The reasoning stays traceable through the field, so a
reviewer can check the derivation without the repo carrying the text.

**A synthetic set has one honest weakness**, stated here so nobody is surprised: invented
phrases are drawn from the patterns we already know about, so the set can only find
proxies we thought of. It cannot bound the ones we did not. This is why category 8 is
hand-extended after every production use that produced a flagged rationale — the set
grows from real cases, and the version bump records which production incident added
which line.

#### 7.4.5 Pass criteria

The Phase 2 criterion *"flags every seeded phrase"* means precisely this, and it is
checked in CI:

| Metric | Threshold | Why that number |
|---|---|---|
| `must_flag` cases flagged | **100%** | A proxy phrase that gets through is a silent ranking error. There is no acceptable miss rate for a known-bad phrase |
| `must_flag` cases flagged by an `expected_terms` hit (not incidentally) | **100%** | Stops the flag-everything strategy passing |
| `must_flag` **false** positives (categories 9, 10) | **0** | Every false positive is an employer shown a rationale the product calls biased when it is not. It trains recruiters to ignore the badge |
| Overall flag rate on categories 1–8 | **between 60% and 95%** | The band is the check. Under 60% means the list is too thin; over 95% means it is flagging noise |

```python
# tests/bias/test_bias_pass.py -- runs in CI, no network, no AI provider.
def test_bias_keyword_pass(bias_pass, manifest):
    cases = load(f"tests/bias/{manifest['version']}")
    result = bias_pass.run_all(cases)
    assert result.recall == 1.0, f"missed: {result.missed_ids}"       # must_flag
    assert result.false_positives == [], result.false_positives         # must_not_flag
    assert 0.60 <= result.flag_rate <= 0.95, result.flag_rate
```

`bias_pass` is the deterministic keyword implementation only. **The LLM bias pass is
advisory and is not gated on this set** — an advisory signal is allowed to be wrong, and
§10 Phase 2 already records that it may not block auto-shortlist. Gating CI on an
advisory signal makes the suite flaky and tempts someone to disable it.

#### 7.4.6 Versioning

`manifest.json` records the **SHA of the keyword list the cases were written against**.
If the keyword list changes and the manifest SHA does not, the set is stale and CI says
so. Without that field, adding a term silently makes old cases pass for a new reason,
and the set stops being a regression test — it becomes a snapshot of whatever the list
happened to be.

---

## 8. Operations & Monitoring

### 8.1 Monitoring Stack

| Component | Purpose | Metrics Collected |
|---|---|---|
| Sentry | Error tracking | Exception rate, error fingerprint, user impact |
| Prometheus | Metrics collection | Request rate, latency, error rate, Celery queue depth, AI cost |
| Grafana | Dashboards | All Prometheus metrics visualized; SLO dashboards |
| Flower | Celery monitoring | Task queue depth, worker status, task duration, failure rate |
| pgBouncer | Connection pooling | Active connections, pool utilization, query latency |
| Health check endpoint | Liveness/readiness | `/health/` returns DB + Redis + AI provider status |

### 8.2 Key Dashboards

1. **Application Performance** — request latency, error rates, throughput (per endpoint)
2. **AI Operations** — OpenRouter API call count, cost, success rate; pgvector query latency; offline fallback usage
3. **Celery** — task queue depth, failure rate, worker utilization, retry count
4. **Security** — failed login attempts, rate-limited IPs, PII leak detections, security header violations
5. **Business** — jobs posted, applications received, hires completed, conversion funnel, AI accuracy review

### 8.3 Log Format (Structured JSON)

All application logs use structured JSON format:

```json
{
  "timestamp": "2026-09-24T14:30:00.123Z",
  "level": "INFO",
  "service": "fairfold-django",
  "trace_id": "a1b2c3d4-e5f6-7890-g123-h456i789j012",
  "user_id": "uuid-or-null",
  "action": "ai.screening_completed",
  "resource_type": "application",
  "resource_id": "uuid",
  "duration_ms": 2450,
  "details": {
    "job_id": "uuid",
    "candidates_screened": 87,
    "candidates_passed_hard_filter": 34,
    "llm_analyzed": 10,
    "cost_estimate_cents": 0,
    "model_used": "openrouter/free"
  }
}
```

### 8.4 Environment Configuration

The document references settings separation into:
- `config/settings/base.py` — shared settings (security, installed apps, middleware)
- `config/settings/local.py` — development (`DEBUG=True`, **PostgreSQL 17 + pgvector** via Docker; no SQLite fallback)
- `config/settings/test.py` — **pure unit tests only** (in-memory SQLite; referenced via `pytest --ds=config.settings.test`). Any test touching a `VectorField` must use `ci.py`, because pgvector does not exist in SQLite
- `config/settings/ci.py` — CI/testing (**PostgreSQL + pgvector** for unit and integration tests alike)

> ⚠️ **SQLite is not a substitute for PostgreSQL — resolved 2026-10-03.**
> `pgvector` does not exist in SQLite, so any model with a `VectorField` cannot be
> created or queried there. Screening, ranking, rationale and bias audit all depend on
> vector search (REQ-FR-028/029/030), so a SQLite-backed `local` or `test` settings
> module **cannot run the application** — it would fail at the first migration.
>
> The corrected rule, applied to every reference below:
> - **Local dev** → PostgreSQL 17 + pgvector via `docker compose up -d db`.
> - **`test.py`** → in-memory SQLite is acceptable **only** for pure unit tests that
>   touch no `VectorField`. Anything touching `matching/`, `candidates/` embeddings or
>   `employers/` screening needs the Postgres test database.
> - **`ci.py`** → Postgres service container, for both unit and integration jobs.
>
> This was a genuine contradiction: the dependency list, the schema and the settings
> hierarchy all assumed PostgreSQL, while the settings comments invited a SQLite
> fallback that could never work.
- `config/settings/production.py` — production (`DEBUG=False`, Sentry, HTTPS)

The full variable reference (including `DB_PASSWORD`, `CELERY_BROKER_URL`, and `CELERY_RESULT_BACKEND`, which are consumed directly by the Compose file above) lives in the Complete Project Document, §C.7.

A `.env.example` file at the repo root mirrors that table and is copied to `.env` during setup.

### 8.5 Maintenance & Patch Management Schedule

**Daily (automated):**
- [ ] Log rotation check (Django logs, Celery logs, Nginx logs)
- [ ] Disk space check on all service volumes (alert if > 80%)
- [ ] Sentry error rate check (alert if > 5% 5xx errors over 5 min)
- [ ] Celery queue depth check (alert if > 1000 pending tasks)
- [ ] Backup job status check (alert on failure)

**Weekly (automated via cron/Celery Beat):**
- [ ] Dependency audit — `pip-audit -r requirements.txt` and auto-create GitHub issue on new CVEs
- [ ] `safety check` scan for known vulnerable packages
- [ ] SSL/TLS certificate expiry check (alert if < 30 days)
- [ ] Database index bloat analysis and reindex if needed
- [ ] pgvector HNSW index health check (reindex if recall degrades)

**Monthly (manual review):**
- [ ] Security patch review — apply OS-level (Ubuntu) and Python dependency updates
- [ ] Full vulnerability scan via OWASP ZAP on staging
- [ ] Review and rotate encryption keys (field-level encryption keys rotate every 90 days)
- [ ] Review and expire stale API tokens (older than 30 days)
- [ ] Review retention policy compliance (data older than retention period auto-purged)

**Quarterly (manual review):**
- [ ] Full disaster recovery drill — restore PostgreSQL from latest WAL backup to staging
- [ ] Third-party penetration test (manual pentest vendor)
- [ ] GDPR compliance audit — data export/deletion workflow verification
- [ ] EU AI Act compliance audit — bias monitoring review, human-in-the-loop verification
- [ ] Performance review — compare actual metrics against SLA targets

**Yearly (manual review):**
- [ ] Full security audit (SOC 2 Type II or equivalent)
- [ ] Architecture review — evaluate monolith-to-microservices migration necessity
- [ ] Technology stack review — check for deprecated libraries, new LTS versions
- [ ] Team skills audit — identify training needs for upcoming phases

### 8.6 Incident Response Plan

**Tier 1 — Critical (P1): Security breach, data exfiltration, downtime > 15 min**
- **Trigger:** Sentry alert with 10+ critical errors in 5 min, or security team notification
- **Response time:** < 15 minutes
- **Actions:**
  1. On-call engineer acknowledges PagerDuty alert
  2. Isolate affected service (scale down, block traffic via Nginx)
  3. Capture forensic data (DB snapshot, recent logs, Sentry event IDs)
  4. Notify security team and incident commander
  5. If PII exposed: trigger data breach notification workflow (GDPR 72-hour notification)
  6. After resolution: mandatory post-mortem within 48 hours
- **Communication:** #incidents Slack channel; updates every 30 min until resolved

**Tier 2 — High (P2): Degraded performance, AI API failures, partial feature outage**
- **Trigger:** Prometheus alert (error rate > 10%, latency > 2x SLA)
- **Response time:** < 1 hour
- **Actions:**
  1. Engineer acknowledges alert in PagerDuty
  2. Switch to fallback systems (offline spaCy + pgvector for AI failures)
  3. Check OpenRouter status page; if downtime, enable offline mode globally
  4. Scale Celery workers if queue backlog detected
  5. Post-resolution: document in incident log
- **Communication:** #oncall Slack channel

**Tier 3 — Medium (P3): Minor bugs, low-impact degradations, non-critical alerts**
- **Trigger:** Bug report from users, or low-severity monitoring alert
- **Response time:** Next business day
- **Actions:**
  1. Triage and assign to sprint backlog
  2. Fix and deploy in next release cycle
- **Communication:** GitHub Issues tracker

**Post-Mortem Template:**
```
## Incident Post-Mortem
- **ID:** INC-YYYY-MM-DD-HHMM
- **Start time:** 
- **End time:** 
- **Duration:** 
- **Impact:** (users affected, data exposed, features unavailable)
- **Root cause:**
- **Detection method:**
- **What went well:**
- **What went wrong:**
- **Timeline:**
  - HH:MM — Detection
n  - HH:MM — Acknowledgment
  - HH:MM — Mitigation started
  - HH:MM — Service restored
- **Action items:**
  1. [ ] (Owner, Due Date) —  
  2. [ ] (Owner, Due Date) —  
  3. [ ] (Owner, Due Date) — 
```

### 8.7 Post-Deployment Evaluation & Retrospective Process

**Phase 1: Release Verification (within 1 hour of deploy)**
- [ ] Health endpoint returns 200 (`curl -f https://app.fairfold.com/health/`)
- [ ] Key API endpoints respond (jobs list, auth login, health check)
- [ ] Sentry shows no new error spikes
- [ ] Prometheus shows no metric anomalies (request rate, error rate, latency)
- [ ] Database connection pool healthy (< 70% utilization)
- [ ] Celery workers processing tasks normally

**Phase 2: 24-Hour Monitoring (within 24 hours of deploy)**
- [ ] Compare error rate to baseline (alert if > 2x increase)
- [ ] Compare latency to baseline (alert if > 2x increase)
- [ ] Verify feature functionality (smoke test key user flows)
- [ ] Check database query performance (alert on slow queries > 1s)
- [ ] Check AI API success rate (alert if < 95%)

**Phase 3: Post-Release Review (within 72 hours of deploy)**

A **Release Retrospective** is held after every production release:

| Metric | Target | Actual | Status | Action |
|---|---|---|---|---|
| Deployment frequency | Weekly |  |  |  |  i
| Deployment success rate | > 95% |  |  |  |
| MTTR (Mean Time to Recovery) | < 5 min |  |  |  |
| Change fail rate | < 15% |  |  |  |
| Rollback frequency | < 5% |  |  |  |

**Retrospective agenda:**
1. What went well in this release?
2. What went wrong (incidents, rollbacks, issues)?
3. What did we learn?
4. What will we improve in the next release?
5. Action items assigned with owners and deadlines

**Success Metrics Tracking (quarterly review):**
- [ ] Time-to-screen for 100 applications (target: < 5 min) — tracked in Business dashboard
- [ ] Cost per AI screening (target: $0.00 free tier) — tracked in Prometheus `ai_cost_total`
- [ ] Candidate satisfaction score (target: > 80%) — tracked via NPS survey (Phase 3)
- [ ] Bias audit pass rate (target: 100%) — tracked in `audit_log_entries` table
- [ ] Data breach incidents (target: 0) — tracked in Sentry security events

### 8.8 Environment Promotion & Configuration Drift Prevention

**Environment hierarchy:**
```
local (dev laptop) → CI (test) → staging → production
```

**Configuration parity:**
- Same Docker images promoted across environments (no rebuild)
- Environment-specific settings via env vars only (never baked into images)
- `docker tag fairfold/app:%SHA% fairfold/app:latest` then promote same image

**Configuration drift detection:**
- [ ] `env0` or `terraform` state diff before deployment (compares env configs)
- [ ] `configcheck` tool compares production and staging env var files
- [ ] Django `diffsettings` command run in CI to catch settings drift
- [ ] `django-check-secure` plugin runs in CI to enforce production settings

### 8.9 Versioning & Release Strategy

**Versioning scheme:** Semantic Versioning 2.0.0 (`MAJOR.MINOR.PATCH`)
- **MAJOR:** Breaking changes to API or data model (rare; requires migration script)
- **MINOR:** New features, backward-compatible
- **PATCH:** Bug fixes, backward-compatible
- Pre-release identifiers: `-alpha`, `-beta`, `-rc.1` (e.g., `v2.1.0-rc.1`)

**Release cadence:**
- **Regular releases:** Weekly, every Tuesday at 10:00 UTC
- **Hotfix releases:** As needed for P1 incidents (deployed out-of-band)
- **Beta releases:** Before each major feature phase (Phase 2, Phase 3, etc.)

**Git branching strategy:** GitHub Flow (trunk-based)
- `main` — always deployable; protected branch with required CI checks
- `feature/{name}` — short-lived feature branches; merged via PR after review + CI pass
- `release/v{MAJOR}.{MINOR}.{PATCH}` — release branch for RC validation (optional, for major releases)

**Tagging convention:**
- `git tag -a v{MAJOR}.{MINOR}.{PATCH} -m "Release v{MAJOR}.{MINOR}.{PATCH}"`
- Tags pushed to GitHub trigger Docker image tagging: `fairfold/app:v{MAJOR}.{MINOR}.{PATCH}`
- The `latest` tag always points to the most recent stable release on `main`

**Pre-release process:**
1. Release branch cut 2 days before scheduled release
2. QA signs off on staging environment
3. Canary deployment to production (1% traffic for 30 minutes)
4. If health checks pass, full rollout (100% traffic)
5. If health checks fail, automatic rollback to previous version
6. Post-release: monitor for 2 hours, then mark release as stable

**Release checklist (pre-deployment):**
- [ ] All CI checks pass (lint, test, security scan, coverage ≥ 80%)
- [ ] OpenAPI schema regenerated and reviewed
- [ ] Migration scripts written and tested (if applicable)
- [ ] Release notes drafted (user-facing changes, breaking changes)
- [ ] Rollback plan confirmed (previous image available, rollback job tested)
- [ ] Canary monitor configured (Prometheus alert for error rate spike)
- [ ] On-call engineer assigned for post-deploy monitoring

**Rollback procedure:**
1. Trigger `rollback-production` GitHub Actions workflow manually
2. The job retags the previous release image (`v{MAJOR}.{MINOR}.{PATCH-1}`) as `:latest`
3. `docker-compose` on the production server pulls the previous image and restarts
4. Health check runs (`curl -f https://app.fairfold.com/health/`)
5. Incident commander notified via Slack #incidents channel
6. Post-rollback: capture forensic data and schedule post-mortem

> **Note:** Rollback target time: < 5 minutes. Previous Docker images are retained for 30 days.

---

## 9. Risk Register

| ID | Risk | Category | Probability | Impact | Mitigation | Owner |
|---|---|---|---|---|---|---|
| RSK-001 | OpenRouter free tier removed/changed | Technical | Medium | High | AIProvider abstraction; offline spaCy + pgvector fallback; start offline-first | Backend Engineer |
| RSK-002 | LLM hallucinations in match rationale | Technical | Medium | Medium | Evidence-cited format (must cite resume text); human recruiter review before hiring decisions; bias audit pre-filter | AI Engineer |
| RSK-003 | Resume parsing accuracy < 80% | Technical | Medium | Medium | Manual edit fallback for candidates; IBM Granite Docling as future upgrade (85-95% accuracy) | AI Engineer |
| RSK-004 | Data breach (PII exposure) | Security | Low | Critical | Defense-in-depth: PII stripping before AI, AES-256-GCM encryption at rest, TLS 1.3 in transit, quarterly pentests | Security Lead |
| RSK-005 | Competitor copies Journey Mapping | Business | Low | Medium | Deep system integration (parsing + timeline + storytelling + narrative) creates switching costs; network effects from candidate data | Product Lead |
| RSK-006 | EU AI Act compliance failure | Legal | Low | High | Documentation of human-in-the-loop; candidates see AI rationale; regular bias disparity analysis | Legal/Compliance |
| RSK-007 | Scalability beyond free tier limits | Business | High (eventual) | Medium | Tiered model: free → cheap OpenRouter models → self-hosted vLLM; usage-based billing | Backend Engineer |
| RSK-008 | Bangladesh market doesn't convert | Business | Medium | High | MVP targets both BD market + global SMBs; self-hostable option for price-sensitive markets | Product Lead |
| RSK-009 | Team lacks DevOps experience | Technical | Medium | Medium | Use Docker Compose for dev; managed services (Neon, Upstash) for early production; hire/freelance DevOps for Phase 4 | Project Manager |
| RSK-010 | Talent acquisition (Python + Django) | Technical | Medium | Medium | Focus on Python-experienced hires; Django skills training for team; leverage open-source community | Project Manager |
| RSK-011 | **Trademark clearance for the chosen name.** The previous working name was abandoned because it was contested by three unrelated commercial users (see `FAIRFOLD_Feasibility_and_Design.md` §1.4.2). **FairFold was selected on 2026-10-03** after a search found no living commercial use, but a web search and a DNS lookup are **not** a clearance. If the name turns out to be unregistable in a target market, a rename would again force a rebrand, a domain change and a support burden. | Legal / Brand | Medium | Low | **Domain: ✅ owned** (temporary first, primary at launch). **Still to do:** commission a **formal trademark search** in Bangladesh and every target export market, and file the word mark in classes 42 (software/SaaS) and 35 (recruitment services) per market. A domain registration is **not** a trademark filing — it does not confer the right to use the name in commerce. None of this has been done yet | Product Owner |
| RSK-012 | **AI-assisted development degrades review quality.** The team is using AI to produce code to fit 217 points into 12 weeks. AI raises throughput, not correctness: it produces confident, plausible, wrong code, and — worse for this product — tests derived from the implementation rather than the acceptance criteria, which agree by construction. The product's whole claim is that it does not assert anything it cannot evidence, so a confidently-wrong codebase is the worst outcome available to it. | Technical / Process | **High** | High | Acceptance criteria in §4.1 are written before the test. No generated code merges unread. `bandit` + `pip-audit` + `safety` already in CI; add a licence scan. **No-AI-review-list** — eight named paths (`accounts/`, PII stripping + resume encryption, the rationale **citation check**, the bias-audit keyword pass, `matching/` filters and ranking, the shortlist/reject gate, all migrations, any Celery task that sends or mutates) require a named human reader before merge; see `FAIRFOLD_Feasibility_and_Design.md` §2.6.4.2. The rationale citation check is the single highest-risk file in the product: if it passes a hallucinated quote, the evidence-cited differentiator is false. Capacity claim measured as `ASM-003` at the end of Phase 1 | Backend Engineer |
**Domain — ✅ owned, recorded 2026-10-03.** The team already holds a domain and intends
to **run on a temporary domain first and move to the primary domain at launch**. That
closes the registration half of this risk. Two consequences worth writing down:

- **Every environment variable and CI secret must be able to change host without a code
  change.** `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `SITE_ID`'s absolute URLs, the
  Stripe webhook URL and the Sentry DSN are all host-bound. The temporary → primary
  switch is a deployment-config change, not a code change. If any of those values is
  hard-coded, the migration will be a debugging session rather than an edit.
- **Do not build SEO, email reputation or social handles against the temporary domain.**
  Verification emails sent from it establish SPF/DKIM for *that* host, and candidate
  links containing it will not survive the move. This is a real cost of starting on a
  temporary domain, and it is why the move should happen before any public launch
  rather than after traction exists.


---

## 10. Acceptance Criteria

### Phase 1: Foundation (Weeks 1-3)
- ✅ `docker-compose up -d` starts PostgreSQL, Redis, Django, Celery, Flower
- ✅ User can register with email + password; verification email sent (Resend API)
- ✅ User can login; JWT access + refresh tokens returned
- ✅ Candidate can upload resume via presigned S3 URL (file type validation)
- ✅ Employer can create/edit/delete job postings (all fields validated)
- ✅ Candidate can apply to a job (unique constraint prevents duplicate applications)
- ✅ Employer sees list of applications for their job
- ✅ All security headers present (HSTS, CSP, X-Frame-Options, nosniff)
- ✅ Tests: 80%+ coverage on models, auth, job CRUD
- ✅ CI: lint passes (black, isort, flake8), security scan passes (bandit, pip-audit)

### Phase 2: AI Integration (Weeks 4-6)
- ✅ PII stripping removes name/email/phone/location with 95%+ accuracy on test dataset
- ✅ Resume embeddings generated via sentence-transformers (384-dim vectors)
- ✅ pgvector cosine similarity returns ranked results in < 2s for 100 candidates
- ✅ LLM rationale generated for top 10 candidates per job (evidence-cited format)
- ✅ The versioned bias test set **exists**: `tests/bias/v1.0.0/`, **76 cases** across all ten categories, with a 62-term proposal, 6 deliberate exclusions and 5 recorded limitations. `scripts/verify_bias_set.py` validates it in CI
- ⬜ Deterministic keyword pass flags **100%** of the `must_flag` cases, with **0** false positives on categories 9–10, and a flag rate on categories 1–8 between 60% and 95% (**set authored 2026-10-03**; the pass itself is still to be implemented and the rate is **unmeasured** — §7.4.0)
- ✅ The bias test set **includes Amazon-style proxy cases** as mandatory categories 1 and 2 — synthetic, in the same shape, source pattern recorded in each case's `source_pattern` field (§7.4.4). These survive PII stripping untouched, which is why stripping names is not sufficient. Pattern source: `FAIRFOLD_Feasibility_and_Design.md` §1.2.1
- ✅ 100% of sampled AI request bodies are PII-free (REQ-SEC-002)
- ⚠️ LLM bias pass is advisory only and may not block auto-shortlist
- ✅ Employer sees ranked candidates with scores + evidence-cited rationales
- ✅ Cost estimate shown before processing; $0.00 for free tier
- ✅ Audit entries logged for every AI scoring action (timestamp, model, rationale hash)
- ⬜ Hard-filter `not_matched` results show the rule that fired and stay listed behind a filter toggle, and can be pulled into review (REQ-FR-029, Gap G3)
- ⬜ `filter_rules_version` is stamped onto every screened application and survives later edits to the job's rules (Gap G3)
- ⬜ A shortlist/reject that goes against the ranking requires a written reason and writes an `ai_decision`-class audit entry (REQ-FR-052, Gap G2)

### Phase 3: Candidate AI Features (Weeks 7-9)
- ✅ Candidate sees interactive career timeline from parsed resume (Chart.js)
- ✅ Skill evolution chart shows skills acquired over time
- ✅ Candidate can take a skill assessment and get auto-scored results
- ✅ AI interview coaching provides structured feedback on practice answers
- ✅ Dynamic storytelling generates a narrative optimized for a specific target job
- ✅ Candidate sees match scores for all applied jobs with AI rationale
- ⬜ An employer can attach an assessment to a job as a required step, and an applicant without a passing attempt cannot be shortlisted on their score alone (REQ-FR-051, Gap G1)
- ⬜ `assessment_gate_status` (not_required / pending / passed / failed) is shown on the application row and disables the Shortlist action with an explanation (REQ-FR-051)
- ⬜ Removing a required assessment leaves existing attempts and scores intact (REQ-FR-051)
- ⬜ Analytics shows override rate, broken down by user and by job, each override linking to its recorded reason (REQ-FR-035, REQ-FR-052)

### Phase 4: Production Hardening (Weeks 10-12)
- ✅ MFA (TOTP) works for employer admin accounts
- ✅ Field-level encryption verified: encrypted PII not readable in DB backups
- ✅ File serving requires authentication (no direct S3 URL access)
- ✅ Rate limiting enforced: 1000 req/hr candidates, 5000 req/hr employers, 20 req/min AI
- ✅ Sentry catches and reports errors (no PII in payloads — `send_default_pii=False`)
- ✅ Prometheus metrics exposed at `/metrics/`
- ✅ GDPR: candidate can export all data as JSON
- ✅ GDPR: candidate can request account deletion (hard delete + audit log)
- ✅ CI/CD: automated deploy to staging on merge to main
- ✅ Load test: 100 concurrent applicants, < 5s response, < 1% error rate

### Phase 5: Advanced Features (Weeks 13+)
- ✅ Stripe billing: upgrade/downgrade plans, payment method management
- ✅ Bengali (and 3 more languages) UI fully translated
- ✅ PWA installable on mobile devices (manifest.json + service worker)
- ✅ WebSocket connection for live interview coaching session
- ✅ WebSocket connection for real-time employer notifications

---

## 11. Glossary

| Term | Definition |
|---|---|
| **AI Provider** | Abstract interface (`ai.base.AIProvider`) that wraps OpenRouter, OpenAI, or offline fallbacks. Allows swapping providers without changing business logic. |
| **Bias Audit** | Automated check that scans AI-generated match rationales for biased language (e.g., "cultural fit" without evidence, gendered pronouns, age-related terms). |
| **Candidate** | End-user seeking employment via the platform. |
| **Employer** | Organization or individual posting job openings and reviewing candidates. |
| **Hard Filter** | Deterministic, non-AI criteria applied before semantic matching (location, visa status, required certifications, min years experience). |
| **PII Stripping** | The process of identifying and redacting personally identifiable information from candidate data before it reaches any external AI service. |
| **pgvector** | PostgreSQL extension for storing and querying vector embeddings. Used for semantic similarity search. |
| **Rationale** | AI-generated explanation of why a candidate was matched (or not matched) to a job. Must be evidence-cited (references specific resume text). |
| **Screening** | The AI process of ranking candidates for a job posting: hard filter → pgvector similarity → LLM qualitative analysis → bias audit. |
| **Journey Mapping** | AI-Powered Professional Journey Mapping — transforms a candidate's resume into an interactive timeline showing skill evolution, impact visualization, and dynamic storytelling per job application. |

---

*End of document. This document supersedes all previous versions of `FAIRFOLD_Project_Architecture_and_Requirements.md`.*
