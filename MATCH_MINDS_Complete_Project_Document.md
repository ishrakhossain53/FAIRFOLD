# MATCH MINDS — Complete Project Document
## AI-Powered Bias-Free Recruitment Platform

**Version:** 2.2 (JobAssessmentRequirement model · override recording · versioned hard filters · real-world evidence)
**Date:** September 2026
**Team:** Sardar Shihab, Arnob Biswas Antu, Ishrak Hossain, Mohammad Abdul Ahad, Fahad Haque

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Market Analysis — Competitors & Gaps](#2-market-analysis--competitors--gaps)
3. [Why We Can Surpass Existing Solutions](#3-why-we-can-surpass-existing-solutions)
4. [Technical Architecture (Full Python Stack)](#4-technical-architecture-full-python-stack)
5. [Security Architecture — Highest Standards](#5-security-architecture--highest-standards)
6. [AI Strategy — Free & Best-in-Class](#6-ai-strategy--free--best-in-class)
7. [System Workflow & UI/UX](#7-system-workflow--uiux)
8. [Database Schema (Core Entities)](#8-database-schema-core-entities)
9. [Implementation Roadmap](#9-implementation-roadmap)
10. [What You Need to Build This](#10-what-you-need-to-build-this)
11. [Open Source References & Inspirations](#11-open-source-references--inspirations)
12. [Appendix A: Success Criteria](#appendix-a-success-criteria--how-we-measure-if-were-winning)
13. [Appendix B: Key Risks](#appendix-b-key-risks-and-mitigations)
14. [Appendix C: Gap-Fill Addendum](#appendix-c-gap-fill-addendum-updates--additions)

---

## 1. Executive Summary

**Match Minds** is an all-in-one, AI-powered recruitment platform that eliminates the two fundamental problems in hiring today: (1) unconscious bias in candidate screening, and (2) the inability of job seekers to showcase their true potential beyond rigid resume templates.

The platform has two distinct portals:
- **Candidate Portal** — Dynamic skill dashboards, AI-powered skill assessments, interview coaching, and AI-Powered Professional Journey Mapping
- **Employer Portal** — AI-automated resume screening, bias-free ranking, structured interview generation, and real-time candidate communication

**Key Differentiators vs. Market Leaders:**
- Built-in **bias audit trail** — every screening decision is logged with rationale, making audits possible (HireVue dropped facial analysis after bias backlash; we build transparency in from day one)
- **Privacy-first architecture** — PII stripped before any AI model sees candidate data (unlike Eightfold/SeekOut which send full profiles to third-party clouds)
- **Freemium + transparent pricing** — $5-50/mo for candidates, $100-5000/mo for employers (vs. Eightfold's $200K+/year enterprise-only model)
- **Full Python stack** — Django + DRF + Celery + pgvector, simpler hiring/development than PHP-based OpenCATS or multi-service Laravel setups
- **AI-Powered Professional Journey Mapping** — no existing competitor offers dynamic career storytelling; this is our unique feature

---

## 2. Market Analysis — Competitors & Gaps

### 2.1 Enterprise incumbents (what they do well, where they fail)

| Competitor | Core Strength | Pricing | Key Weaknesses |
|---|---|---|---|
| **HireVue** | Video interview AI, structured assessments, enterprise scale (processed ~20M assessments Q1 2024) | $35K+/year, enterprise custom | Dropped facial analysis in 2021 after bias backlash — trust damaged; slow LLM-native roadmap; overkill under ~200 roles/year; candidates refuse to record |
| **Eightfold AI** | Deepest talent graph (billions of profiles), skill adjacency mapping, internal mobility | $200K+/year (5,000+ employees); $7-10/emp/month | Black-box scoring — hard to explain to candidates/auditors; 6-12 month implementation; inaccessible below 5,000 employees; high burn rate |
| **SeekOut** | Best diversity + technical sourcing (GitHub, patents, clearance data, 750M+ profiles) | $15K-40K+/year; seat-based, opaque | AI matching is keyword-driven under the hood — "AI" framing oversells; sourcing-only (no downstream ATS); pricing surprises |
| **Paradox (Olivia)** | Conversational AI for high-volume hourly hiring (50K+ applicants/year) | Mid-five to six-figure annual | Overkill for tech/professional hiring; locked into Paradox's conversation design; heavy sales/procurement cycle |
| **LinkedIn Recruiter** | Largest network (1.3B+ profiles), "Open to Work" signals, Hiring Assistant AI agent (2025) | $170/mo Lite; $10,800+/seat/yr Corporate | Doesn't verify contact details beyond InMail; AI features often underused; LinkedIn's algorithm changes affect sourcing |
| **Manatal** | SMB-friendly ATS + AI, web-sourced candidates | $15-19/user/month | Small talent pool vs. Eightfold/SeekOut; limited integrations at lower tiers |
| **Workable** | All-in-one mid-market, smart candidate scoring, broad integrations | From $169/month | Less AI depth than dedicated tools; not competitive at enterprise |
| **Phenom** | Career-site personalization, CRM+CMS+chatbot bundled | $150K+/year | Suite breadth = modules not best-in-class; heavy services attach; less compelling when applicants come from job boards |
| **HackerEarth** | Technical assessments (17K questions, 900+ skills, SonarQube grading) | Contact for pricing | Purpose-built for technical roles — non-tech teams find it overkill |

### 2.2 Open Source Projects (what exists, what we learn)

| Project | Stack | AI | Strengths | Gaps / Lessons for Us |
|---|---|---|---|---|
| **CandiSift** (confused-ai) | FastAPI, Python, hexagonal arch, Agno agents, Claude | LLM resume screening, bias-audit endpoint, PII stripping, cost-estimate-before-process | Best-in-class open-source architecture; cost-aware; evidence-cited breakdowns; ATS-readability scoring; near-duplicate detection | No candidate portal/journey mapping; no Django ecosystem; Claude-dependent (not free) |
| **OpenCATS** (opencats) | PHP, MySQL, 710 stars | None — purely manual | Mature (since 2009), staffing-agency focused, 30 contributors | No AI whatsoever; PHP stack; dated UX; no candidate self-service |
| **candidacy** (steelburn) | Laravel 10, Vue.js 3, MySQL, Redis, Ollama/OpenRouter | IBM Granite Docling PDF parsing (85-95% accuracy), AI matching, interview Q gen | Full 12-service microservices; OpenRouter integration is directly relevant to us; DBML schema-as-code | PHP/Laravel, not Python; 12 services = high operational complexity; no journey mapping |
| **SkillAI** (olafkfreund) | Next.js 15, PostgreSQL+pgvector, Claude/Gemini | 4-dimension scoring (tech, experience, culture, communication), interview Q packs, MCP server | Multi-tenant with row-level security; MCP server for workflow composition; semantic search | No candidate journey feature; Next.js not Django; Claude/Gemini costs |
| **Vekt** (Behnoudmst) | Next.js 15, SQLite/Prisma, Inngest, OpenAI/Ollama | AI resume scoring, screening questions, GDPR-compliant, data retention policy | Privacy-aware by default; MIT licensed; self-hostable; protected file serving | SQLite limits scale; no candidate portal; no journey mapping |
| **Talent Platform** (kvadou) | Next.js 14, PostgreSQL+pgvector, Prisma, Clerk, OpenAI | AI candidate scoring, interview scheduling (Zoom), e-signatures (Dropbox Sign), background checks (Checkr) | Full ATS pipeline; Kanban; real integrations (Zoom, Checkr, Dropbox Sign) | Next.js; OpenAI costs; Clerk auth lock-in |
| **The Talent App** (freshy969) | React/Vite, Supabase, Deno edge functions, Gemini | AI HR Manager "Chitragupta" — autonomous monitoring, escalation, daily reports | Agentic AI HR manager concept is fascinating; Supabase simplifies infra | Supabase lock-in; Deno edge functions; Gemini-only |
| **OpenATS** (chamals3n4) | Next.js, Express 5, Drizzle+PostgreSQL, BullMQ/Redis, Gemini | AI resume parsing background jobs, scoring, summaries | Clean separation: CV analysis as background worker; WSO2 Asgardeo auth | No journey mapping; Express not Django; Gemini-only |

### 2.3 What No One Is Doing (Our Gap)

1. **AI-Powered Professional Journey Mapping** — dynamic career timelines showing skill evolution over time, impact visualization, learning trajectory, dynamic storytelling per application. Zero competitor has this.
2. **Bias-free + explainable AI** — CandiSift has a bias-audit endpoint; we combine this with full audit trails AND make it candidate-visible (candidates see why they were ranked the way they were)
3. **Free-tier AI for screening** — every open-source project above uses paid Claude/Gemini/OpenAI. We use OpenRouter free tier + fallback patterns.
4. **Freemium candidate access** — enterprise tools are all recruiter-side. We put powerful tools (skill assessments, interview coaching, journey mapping) in the candidate's hands for free/cheap.

---

## 3. Why We Can Surpass Existing Solutions

### 3.1 The core insight

Every incumbent solves one slice of the problem:
- HireVue → video interviewing
- Eightfold → talent intelligence (enterprise-only)
- SeekOut → sourcing (keyword-driven AI)
- Paradox → high-volume conversational screening
- OpenCATS → manual tracking (no AI)

**Match Minds is the first to connect BOTH sides with AI while keeping power in the candidate's hands.**

### 3.2 How we overcome each competitor's moat

| Competitor Moat | Our Counter |
|---|---|
| Eightfold's proprietary talent graph (billions of profiles) | We don't need a pre-built graph — our AI-Powered Professional Journey Mapping builds a dynamic skills profile per candidate at ingest time using OpenRouter LLMs. We start with semantic matching on what candidates actually submit, not external profile scraping. |
| HireVue's structured interview science | We generate structured interview packs per role using AI (like candidacy and SkillAI do), but add real-time coaching feedback for candidates before the interview — something HireVue doesn't offer candidates. |
| SeekOut's 750M-profile index | We don't compete on profile volume. We compete on depth per candidate: journey mapping, skill evolution, impact visualization. A candidate with a rich Match Minds profile is more valuable than 10 LinkedIn profiles. |
| Enterprise pricing lock-in ($200K+/year) | Our freemium model ($5-50/mo candidates, $100-5000/mo employers) makes us accessible to SMBs and startups — a segment Eightfold/HireVue/Phenom explicitly don't serve. |
| Black-box AI (unexplainable scoring) | Every Match Minds ranking comes with an evidence-cited breakdown (CandiSift pattern): which skills matched, which were missing, what the AI reasoned. Candidates can see their own breakdown. |
| Privacy concerns (sending PII to third-party AI) | PII stripping before AI processing (CandiSift pattern). OpenRouter free models don't log prompts for the free tier routers. Field-level encryption in DB for sensitive fields even at rest. |

### 3.3 Our unfair advantage: Bangladesh + emerging markets

Bangladesh and similar emerging markets represent our initial beachhead — where no established competitor has a solution. In these markets:
- Companies still use manual hiring (spreadsheets, email)
- LinkedIn penetration is lower
- Eightfold/HireVue are completely inaccessible (price + implementation)
- A lightweight, self-hostable, free-tier-AI platform is a perfect wedge

We enter through Bangladesh/emerging markets where no one has a solution, then expand to SMBs in developed markets who can't afford Eightfold.

---

## 4. Technical Architecture (Full Python Stack)

### 4.1 Stack Decision: Why Full Python (No Rust)

The original proposal included Rust/Actix for "high-performance components." After analysis:

**Why we drop Rust:**
- Django + DRF + Celery is production-proven at scale (Instagram, Pinterest, Spotify use Django)
- Rust adds a second language, second build chain, second deployment pipeline — for a project team of 5 with mostly Python experience
- The performance gains Rust gives are irrelevant at our scale: AI API calls dominate latency, not Python web serving. pgvector does the heavy lifting for matching
- Every open-source ATS project above uses a single primary language (PHP, TypeScript, Python). Multi-language = higher onboarding and maintenance cost

**Full Python stack:**

```
┌─────────────────────────────────────────────────────┐
│                    FRONTEND                          │
│  Django Templates + HTMX (SPA-like interactivity)  │
│  TailwindCSS + Chart.js                              │
│  (React 18 + Vite reserved for Phase 5 mobile/offline)│
└──────────────────────┬──────────────────────────────┘
                       │ REST API (DRF) — available for future SPA
┌──────────────────────▼──────────────────────────────┐
│                    BACKEND                           │
│  Django 5 + Django REST Framework                   │
│  Django Ninja (optional, for OpenAPI auto-gen)      │
│  PostgreSQL 17 + pgvector (semantic matching)       │
│  Redis (Celery broker + caching + rate limiting)    │
│  Celery + Celery Beat (async AI tasks, scheduled)   │
└──────┬─────────────┬──────────────┬────────────────┘
       │             │              │
┌──────▼──────┐ ┌────▼───────┐ ┌──▼──────────────┐
│  AI Service  │ │  Matching  │ │  Assessment     │
│  (Celery     │ │  Engine    │ │  Service        │
│   workers)   │ │  (pgvector │ │  (skill tests,  │
│  OpenRouter  │ │   cosine   │ │  coding chal-   │
│  + free      │ │   similarity)│ │  lenges via    │
│  models)     │ │            │ │  sandbox)       │
└──────────────┘ └────────────┘ └─────────────────┘
       │
┌──────▼─────────────────────────────────────────────┐
│  INFRASTRUCTURE                                     │
│  Docker + Docker Compose (local)                    │
│  Docker Compose / Kubernetes (prod)                 │
│  Nginx reverse proxy + SSL (Let's Encrypt)          │
│  S3-compatible storage (MinIO or Cloudflare R2)     │
│  PostgreSQL 17 (pgvector extension)                 │
│  Redis 7                                            │
│  Sentry (error tracking)                            │
│  Prometheus + Grafana (observability)               │
└─────────────────────────────────────────────────────┘
```

### 4.2 Django Application Structure

```
matchminds/
├── core/                    # Shared utilities, middleware, security
├── accounts/               # User model, auth, RBAC, profiles
├── candidates/             # Candidate dashboard, journey mapping, assessments
├── employers/              # Employer dashboard, job postings, screening
├── matching/               # AI matching engine, pgvector, ranking
├── assessments/            # Skill assessment creation, taking, scoring
├── interviews/             # Interview scheduling, AI-generated Q packs
├── notifications/          # Email, in-app notifications
├── api/                    # DRF API root, versioning
├── admin/                  # Custom admin for super-admin operations
├── journey/                # AI-Powered Professional Journey Mapping (MVP feature)
└── ai/                     # AI provider abstraction (OpenRouter + fallback)
```

### 4.3 Core Django Settings for Security (see Section 5 for full detail)

```python
# settings.py — security-critical settings
SECRET_KEY = env("DJANGO_SECRET_KEY")  # 512-bit random, rotated per deploy
DEBUG = False
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS")
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
```

---

## 5. Security Architecture — Highest Standards

This section is the most critical addition to the original document. Recruitment platforms handle highly sensitive personal data (resumes, identity documents, assessment results, interview recordings). We implement defense-in-depth.

### 5.1 Authentication & Authorization

| Layer | Implementation |
|---|---|
| **Password hashing** | Argon2id (Django default since 4.0) — not bcrypt, not PBKDF2. Argon2id is memory-hard and resists GPU/ASIC attacks. |
| **Session auth** | Django session framework with secure cookies (HttpOnly, Secure, SameSite=Lax) |
| **API token auth** | DRF `TokenAuthentication` with 256-bit random tokens, rotated on password change. Short-lived JWT (15-min access, 7-day refresh) for mobile/SPA. |
| **MFA** | TOTP (time-based one-time password) via `django-otp` — required for employer admin accounts, optional for candidates |
| **RBAC** | Django Groups + custom permission system: `admin`, `employer_hr`, `employer_manager`, `interviewer`, `candidate`, `guest` |
| **Account lockdown** | After 5 failed login attempts → 15-min cooldown; after 10 → email verification required to unlock |
| **Password policy** | Minimum 12 characters, breached-password check against HaveIBeenPwned API (k-anonymity, no password sent) |

### 5.2 Data Protection at Rest

| Data Category | Protection |
|---|---|
| **PII (name, email, phone, address)** | Encrypted at rest using Django's `EncryptedField` (cryptography library, AES-256-GCM) via `django_encrypted_model_fields` (from `django_encrypted_model_fields.fields` import `EncryptedCharField`) — separate encryption key per deployment, stored in environment/secret manager, NOT in DB |
| **Resume/CV files** | Stored in S3-compatible storage with server-side encryption (SSE-S3 or SSE-KMS). Filenames are UUIDs with no semantic meaning. Files served only through authenticated, rate-limited Django views — never directly from S3. |
| **Assessment answers** | Encrypted at rest. AI scoring uses anonymized content only (see 5.4). |
| **Database** | PostgreSQL with `pgcrypto` for additional field-level encryption where Django encrypted fields aren't sufficient. Full database encryption at rest via filesystem/disk encryption (LUKS on Linux, or cloud provider disk encryption). |
| **Backups** | Encrypted backups, stored in separate location from primary. Retention: 30 days rolling. Backup access logged. |
| **API keys / AI keys** | Stored in environment variables or HashiCorp Vault / AWS Secrets Manager — never in code, never in DB, never in .env committed to git |

### 5.3 Data Protection in Transit

| Channel | Protection |
|---|---|
| **All HTTP** | HTTPS only (TLS 1.3 minimum). HSTS with 1-year max-age, includeSubDomains, preload. |
| **Internal service communication** | All inter-service calls (Celery → Redis, Django → PostgreSQL) over local socket or TLS-encrypted connections. Redis with TLS. PostgreSQL with `sslmode=require`. |
| **AI API calls (OpenRouter)** | HTTPS to OpenRouter API. Request payloads contain NO raw PII — PII stripped before reaching AI layer. |
| **File uploads** | Direct upload to S3 via presigned URLs (browser → S3, not browser → Django → S3). Django receives only the S3 key. This avoids buffering large files through Django. |

### 5.4 AI Privacy Layer (Critical — Unique to Match Minds)

This is our key architectural differentiator vs. every competitor above.

```
Candidate submits resume PDF
        │
        ▼
┌─────────────────────┐
│  PII Stripping      │   ← Removes: name, email, phone, address,
│  (pre-AI gate)      │      LinkedIn URL, photo references, ID numbers
│  (deterministic     │      Keeps: skills, experience, education, projects
│   regex + NER)      │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Anonymized Content │   ← Replaced with candidate_id hash + generic labels
│  (candidate_12345)  │      "Candidate worked at [COMPANY_A] as [ROLE_B]"
│                     │      Skills, years of experience, project descriptions kept intact
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  AI Processing      │   ← OpenRouter free models score/anonymized content
│  (OpenRouter API)   │      No PII reaches the AI provider
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Result Re-assembly │   ← AI score + rationale mapped back to candidate_id
│  + Audit Log        │      Audit log: timestamp, model used, prompt hash,
│  (append-only)      │      rationale, candidate_id — never raw PII in logs
└─────────────────────┘
```

**PII stripping implementation:**
- Phase 1 (MVP): Deterministic regex + spaCy NER (free, offline) to identify and redact name, email, phone, location
- Phase 2: LLM-based PII detection as a pre-processing step (still using free OpenRouter models, but a different, cheaper model for this specific task)

**Why this matters legally and competitively:**
- GDPR Article 25 (data protection by design and default) — we implement it from day one
- EU AI Act (adopted May 2024, effective February 2025) — high-risk AI systems (including recruitment AI) require transparency, human oversight, and data governance. Our PII-stripping + audit trail directly addresses these requirements
- Candidates trust platforms that don't send their raw personal data to third-party AI providers. This is a marketing point, not just a compliance checkbox

### 5.5 Application Security

| Control | Implementation |
|---|---|
| **OWASP Top 10** | Django protects against: SQL injection (ORM parameterized queries), XSS (auto-escaping in templates), CSRF (middleware), clickjacking (X-Frame-Options=DENY). Remaining: we manually protect against insecure deserialization, security misconfiguration, and vulnerable components. |
| **Input validation** | Django form/serializer validation on all inputs. DRF serializers with strict type checking. File upload: validate MIME type (python-magic, not extension), max 10MB for resumes, scan with ClamAV or similar before storage |
| **Rate limiting** | Django Ratelimit or DRF Throttle: 100 req/hour for unauthenticated, 1000 req/hour for authenticated candidates, 5000 req/hour for employer HR. Stricter on AI endpoints (20 req/min per user — aligns with OpenRouter free tier limits) |
| **CSP** | Content-Security-Policy header: `default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self' https://openrouter.ai;` — tight, no external script sources except Tailwind CDN |
| **Security headers** | `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy: camera=(), microphone=()` — camera/mic blocked by default; enabled only on specific interview pages with user consent |
| **Dependency scanning** | `pip-audit` or `safety` in CI pipeline. Dependabot or Renovate for automated PRs on vulnerabilities. |
| **Audit logging** | Every significant action logged: login/logout, password change, job post created/edited, candidate viewed/screened/ranked, AI score generated, file uploaded/downloaded, permission change. Logs are append-only, stored separately, rotated 90 days. Log format: timestamp, user_id, action, resource_type, resource_id, IP, user-agent, result (success/failure). |

### 5.6 Infrastructure Security

| Control | Implementation |
|---|---|
| **Network** | Django/Gunicorn behind Nginx. Nginx handles TLS termination. Internal services (PostgreSQL, Redis) not exposed to internet — only accessible from Django container on private Docker network. |
| **Database** | PostgreSQL with `pg_hba.conf` restricting to Django host only. Strong DB user password (32-char random). No superuser DB access from application — dedicated Django DB user with minimal required permissions. |
| **Celery workers** | Run on separate container(s). No direct internet access except to OpenRouter API (whitelisted egress). Result backend: Redis with authentication. |
| **Secrets management** | Production: environment variables injected via Docker secrets or cloud secret manager. No `.env` files on production servers. Development: `.env` in `.gitignore`, `.env.example` committed with placeholder values. |
| **CI/CD** | GitHub Actions (or GitLab CI). Pipeline: lint → test → security scan (pip-audit, bandit for Python static analysis) → build Docker image → push to registry → deploy. No deployment without passing security scans. |
| **Monitoring** | Sentry for error tracking (no PII in Sentry payloads — configure `send_default_pii=False`). Prometheus metrics: request rate, error rate, latency, Celery task duration, AI API call count/cost. Grafana dashboards. |

### 5.7 Compliance Checklist

- [x] GDPR: data minimization (PII stripping), right to erasure (candidate data deletion endpoint), consent capture (privacy policy acceptance on signup), data portability (export candidate profile as JSON/PDF)
- [x] EU AI Act: human-in-the-loop (recruiter makes final decision, AI is advisory), transparency (candidates can see AI rationale), bias monitoring (regular disparity analysis by gender/ethnicity if data collected)
- [x] Data retention: configurable per-employer (default 2 years for candidates, 5 years for hired employees' records). Automated purging via Celery Beat. Deletion is hard delete with audit log entry.
- [x] Accessibility: WCAG 2.1 AA target — Django admin is accessible; custom frontend must be tested with screen readers

---

## 6. AI Strategy — Free & Best-in-Class

### 6.1 OpenRouter as Primary AI Provider

**Why OpenRouter:**
- Single API for 300+ models across 60+ providers — swap models without code changes
- Free tier: 20 req/min, 50 req/day free without any credit card or phone verification
- OpenAI-compatible API — works with the `openai` Python SDK out of the box
- `openrouter/free` router automatically selects a free model — zero cost for development and early production
- Paid models available when you need more power: Llama 3.3 70B at $0.10/1M input, GPT-4.1 Nano at $0.10/1M, Gemma 4 26B at $0.06/1M — dramatically cheaper than Claude or GPT-4 directly

**Free models available on OpenRouter (as of September 2026):**

| Model | Input $/1M | Output $/1M | Context | Best For |
|---|---|---|---|---|
| `openrouter/free` | Free | Free | 200K | General routing — use as default, falls back automatically |
| `cohere/north-mini-code:free` | Free | Free | 131K | Code + structured tasks |
| `google/gemma-4-26b-a4b-it:free` | Free | Free | 256K | General purpose, multilingual |
| `nvidia/nemotron-3-nano-30b-a3b:free` | Free | Free | 262K | Large context, general |
| `openai/gpt-oss-20b:free` | Free | Free | — | OpenAI's open model |
| `google/gemma-3n-4b-it:free` | $0.06 | $0.12 | 8K | Lightweight, edge cases |
| Llama 3.3 70B Instruct | $0.10 | $0.32 | 66K | High-quality general (paid, but cheap) |

### 6.2 AI Task → Model Mapping

| AI Task | Recommended Model (Free Tier) | Fallback | Notes |
|---|---|---|---|
| **Resume/JD parsing** (extract skills, experience, education from text) | `openai/gpt-oss-20b:free` or `cohere/north-mini-code:free` | spaCy NER (offline, no API cost) | Structured extraction — needs good instruction-following |
| **Candidate-job matching** (semantic similarity score 0-100) | `google/gemma-4-26b-a4b-it:free` | pgvector cosine similarity (no AI cost — pure vector math) | First try pgvector; use LLM for nuanced qualitative match explanation |
| **Interview question generation** (structured Q pack per role) | `openrouter/free` router | Predefined question templates by role category | Template fallback ensures zero-cost when free tier is exhausted |
| **Interview coaching feedback** (analyze candidate's practice answers) | `cohere/north-mini-code:free` | Rule-based feedback on keyword coverage | Coaching is a candidate-facing feature — keep it free |
| **Journey Mapping — skill extraction** (find hidden skills in project descriptions) | `google/gemma-4-26b-a4b-it:free` | Pattern-based skill dictionary lookup | LLM catches non-obvious skills; dictionary catches obvious ones for free |
| **Journey Mapping — career story generation** (dynamic narrative per job application) | `openrouter/free` router | Template-based narrative using extracted skills | Template fallback for high-volume scenarios |
| **Bias audit** (check ranking rationale for biased language) | `cohere/north-mini-code:free` | Deterministic keyword check (flag terms like "culture fit" without evidence) | Bias audit is a compliance feature — runs offline/deterministic where possible |

### 6.3 Cost Management Strategy

```python
# ai/providers.py — tiered AI provider with cost awareness

class TieredAIProvider:
    """
    Uses cheapest available option first, escalates only when needed.
    Never uses a paid model without explicit override.
    """
    
    def __init__(self):
        self.free_client = OpenRouterClient(model="openrouter/free")
        self.paid_client = OpenRouterClient()  # configured but not used by default
    
    def parse_resume(self, text: str, use_paid: bool = False):
        if use_paid:
            return self.paid_client.chat(model="google/gemma-4-26b-a4b-it", ...)
        return self.free_client.chat(model="openai/gpt-oss-20b:free", ...)
    
    def estimate_cost(self, task: str, token_estimate: int) -> float:
        """Return estimated cost in cents — show this to employer BEFORE processing."""
        # Free tier: $0. Paid models: look up from OpenRouter pricing API.
        ...
```

**Key principle: show employers the cost before they confirm processing.** CandiSift does this — we adopt it. An employer uploads 100 resumes, sees "this batch will cost $0.00 (free tier) or $0.15 (if we need Gemma 4 for nuanced scoring)" and confirms.

### 6.4 AI Architecture — Abstraction Layer

```python
# ai/base.py
from abc import ABC, abstractmethod

class AIProvider(ABC):
    """Swap OpenRouter for any other provider without touching business logic."""
    
    @abstractmethod
    def chat_completion(self, messages: list[dict], model: str, 
                       max_tokens: int = 1024) -> dict: ...
    
    @abstractmethod
    def embed(self, text: str) -> list[float]: ...

class OpenRouterProvider(AIProvider):
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
    
    def chat_completion(self, messages, model="openrouter/free", max_tokens=1024):
        return self.client.chat.completions.create(model=model, messages=messages, 
                                                   max_tokens=max_tokens)
    
    def embed(self, text):
        # Use a free embedding model or fallback to offline sentence-transformers
        ...

class OfflineSpaCyProvider(AIProvider):
    """Zero-cost fallback when API is unavailable or free tier exhausted."""
    def __init__(self):
        import spacy
        self.nlp = spacy.load("en_core_web_sm")
    
    def chat_completion(self, messages, model=None, max_tokens=1024):
        # Rule-based response or raise ManagedException for retry
        ...
    
    def embed(self, text: str) -> list[float]:
        """Offline embedding using sentence-transformers (no API cost)."""
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer('all-MiniLM-L6-v2')
        return model.encode(text).tolist()
```

**Why this abstraction matters:** If OpenRouter changes pricing or a better free provider emerges (e.g., a new aggregator), we swap one class. Business logic, views, Celery tasks — none of them change.

### 6.5 pgvector for Semantic Matching (Zero-AI-Cost Matching)

For the core candidate-job matching, we use pgvector's cosine similarity — pure vector math, no AI API cost:

```python
# matching/vectorize.py
from sentence_transformers import SentenceTransformer

# Load once at worker startup — runs offline, no API cost
model = SentenceTransformer('all-MiniLM-L6-v2')  # 384-dim, runs on CPU

def embed_resume_text(text: str) -> list[float]:
    return model.encode(text).tolist()

def embed_job_description(text: str) -> list[float]:
    return model.encode(text).tolist()

# In PostgreSQL:
# CREATE EXTENSION vector;
# Candidates.resume_embedding VECTOR(384)
# Jobs.description_embedding VECTOR(384)
# Query: SELECT *, 1 - (resume_embedding <=> job_description_embedding) AS similarity
#        FROM candidates WHERE job_id = %s ORDER BY similarity DESC;
```

**Matching pipeline (cost-optimized):**
1. **Deterministic hard filters** (free) — location, visa status, minimum years, required certifications — reject immediately
2. **pgvector cosine similarity** (free — offline model) — rank remaining candidates by semantic similarity
3. **LLM qualitative analysis** (free OpenRouter tier) — for top N candidates only (e.g., top 20), generate the evidence-cited breakdown: which skills matched, which were missing, why this candidate is a strong fit
4. **Bias audit** (free) — check the LLM's rationale for problematic language before showing to recruiter

This funnel means: 100 resumes → maybe 20 pass hard filters → pgvector ranks all 20 → LLM analyzes top 5-10. That's 5-10 AI calls per job post, not 100. Well within free tier limits.

---

## 7. System Workflow & UI/UX

### 7.1 Candidate Journey (User Flow)

```
Sign Up / Login (email + password, MFA optional)
    │
    ▼
Onboarding: Upload resume OR build profile manually
    │  (PII stripped before storage/AI)
    ▼
Dashboard:
  ├─ Skill Overview (parsed from resume + manual additions)
  ├─ AI-Powered Professional Journey Mapping (interactive timeline)
  │   ├─ Skill Evolution Over Time (chart)
  │   ├─ Impact Visualization (achievements with numbers)
  │   ├─ Learning Trajectory (formal + informal skills applied)
  │   └─ Dynamic Storytelling (rewrites narrative per target job)
  ├─ Skill Assessments (take assessments, earn badges/certifications)
  ├─ AI Interview Coaching (practice questions, get feedback)
  └─ Applied Jobs (status tracker with AI rationale visible)
    │
    ▼
Apply to Job → AI shows "Your match score: 87/100" + rationale
    │
    ▼
Interview coaching for that specific role (AI-generated Q pack)
    │
    ▼
Real-time status updates (applied → screened → interview → offer/declined)
```

### 7.2 Employer Journey (User Flow)

```
Sign Up / Login (email + password, MFA required for HR admin)
    │
    ▼
Create Job Posting:
  ├─ Title, department, location, remote/hybrid/onsite
  ├─ Required skills (auto-suggested by AI from similar existing jobs)
  ├─ Nice-to-have skills
  ├─ Experience level
  ├─ Screening questions (AI-suggested, editor-customizable)
  └─ AI model preference: "Auto (free tier)" / "Best available (paid)"
    │
    ▼
Post Job → Share link / embed on career page
    │
    ▼
Candidates Apply → PII stripped → Celery task queues:
  ├─ Hard filter (location, visa, certs) — free, instant
  ├─ pgvector embedding + similarity ranking — free, ~seconds
  └─ LLM deep analysis on top N — free OpenRouter tier
    │
    ▼
Screening Dashboard:
  ├─ Ranked candidate list with match scores
  ├─ Click any candidate → full evidence-cited breakdown
  │   ├─ Matched skills (with evidence from resume)
  │   ├─ Missing skills
  │   ├─ AI rationale (explainable, not black-box)
  │   ├─ Bias audit pass/fail
  │   ├─ Screening question answers
  │   └─ Full anonymized resume text
  ├─ Accept / Reject / Shortlist per candidate
  ├─ Bulk actions (shortlist top 10, reject bottom 20)
  └─ Schedule interviews (AI picks available slots, sends invites)
    │
    ▼
Interview Stage:
  ├─ AI-generated structured interview pack (questions + scoring rubric)
  ├─ Interviewers score via structured form (reduces inconsistency)
  └─ Candidate gets real-time coaching before interview
    │
    ▼
Offer Stage:
  ├─ Generate offer letter (AI drafts from job details)
  ├─ Track acceptance / counter-offer
  └─ Onboarding checklist (automated)
    │
    ▼
Analytics:
  ├─ Time-to-hire per role
  ├─ Source of hire (which job boards / referrals)
  ├─ Drop-off points in pipeline
  ├─ Diversity metrics (if candidates opt in to provide demographic data)
  └─ AI accuracy review (how often did AI's top pick actually get hired?)
```

### 7.3 Frontend Technology Decision

For the MVP, we recommend **Django Templates + HTMX + TailwindCSS** over a separate React SPA:

- Faster development — one framework, not two
- Django's template system + HTMX gives SPA-like interactivity without the complexity of a separate frontend build pipeline, API versioning, CORS setup, and auth token management
- The team has Django experience; React adds a third technology (after Python and AI)
- For the candidate journey mapping interactive timeline, HTMX + a lightweight charting library (Chart.js or Recharts via CDN) works well

**When to switch to React SPA:** When the dashboard needs complex real-time updates (WebSockets for live interview coaching), offline capability, or mobile app reuse. Add React as a separate frontend app consuming the DRF API when those needs arise — the API is already designed for it.

---

## 8. Database Schema (Core Entities)

### 8.1 Entity Relationship Overview

```
Users (1) ──────< (N) Profiles (candidate OR employer)
                    │
        ┌───────────┴───────────┐
        ▼                       ▼
  CandidateProfile        EmployerProfile
  (skills, journey,       (company, industry,
   assessments,           settings, billing)
   certifications)
        │                       │
        │                       │
        ▼                       ▼
  Applications (N) <──────────> Jobs (N)
  (candidate + job +       (title, description,
   status + AI score +     requirements, screening_qs,
   match rationale)         embedding, status)
        │
        ├──────────────┐
        ▼              ▼
  AssessmentScores   InterviewPacks
  (skill test        (AI-generated Qs,
   results)          scoring rubric)
```

### 8.2 Core Django Models (abridged)

```python
# accounts/models.py
class User(AbstractUser):
    # Extends Django's AbstractUser
    auth_provider = models.CharField(max_length=20, default="email")  # email, oauth
    email_verified = models.BooleanField(default=False)
    mfa_enabled = models.BooleanField(default=False)
    mfa_secret = EncryptedCharField(max_length=32, blank=True)  # TOTP secret
    locked_until = models.DateTimeField(null=True, blank=True)
    failed_login_attempts = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

# candidates/models.py
class CandidateProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="candidate_profile")
    title = models.CharField(max_length=200)  # "Senior Software Engineer"
    bio = models.TextField(blank=True)
    location = EncryptedCharField(max_length=200, blank=True)
    remote_ok = models.BooleanField(default=True)
    skills = models.JSONField(default=list)  # list of {"name": "Python", "level": "expert", "source": "self_reported|ai_parsed"}
    journey_timeline = models.JSONField(default=list)  # structured career timeline
    match_scores = models.JSONField(default=dict)  # {job_id: score} for quick lookups
    created_at = models.DateTimeField(auto_now_add=True)

class CandidateResume(models.Model):
    candidate = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE)
    file = models.FileField(upload_to="resumes/")  # S3 key, not path
    original_filename = EncryptedCharField(max_length=500)
    file_size = models.IntegerField()
    mime_type = models.CharField(max_length=100)
    extracted_text = models.TextField(blank=True)  # PII-stripped text
    raw_text_hash = models.CharField(max_length=64)  # for dedup
    created_at = models.DateTimeField(auto_now_add=True)

# employers/models.py
class EmployerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="employer_profile")
    company_name = EncryptedCharField(max_length=300)
    industry = models.CharField(max_length=100, blank=True)
    company_size = models.IntegerField(choices=COMPANY_SIZE_CHOICES, blank=True)
    billing_plan = models.CharField(max_length=20, default="free")  # free, starter, growth, enterprise
    billing_cycle = models.CharField(max_length=10, default="monthly")
    stripe_customer_id = models.CharField(max_length=100, blank=True)  # if paid
    created_at = models.DateTimeField(auto_now_add=True)

class EmployerTeamMember(models.Model):
    """An employer organisation has several people, so EmployerProfile is 1-to-1 with
    User but the organisation is many-to-many with it. REQ-FR-047."""
    employer = models.ForeignKey(EmployerProfile, on_delete=models.CASCADE, related_name="team")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="employer_teams")
    role = models.CharField(max_length=20, choices=TEAM_ROLE_CHOICES, default="interviewer")
    invited_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    invite_status = models.CharField(max_length=20, default="pending")  # pending/accepted/revoked
    mfa_enforced = models.BooleanField(default=True)
    joined_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["employer", "user"], name="uq_employer_team_member"),
        ]

# matching/models.py
class Job(models.Model):
    employer = models.ForeignKey(EmployerProfile, on_delete=models.CASCADE, related_name="jobs")
    title = models.CharField(max_length=300)
    description = models.TextField()  # full JD
    responsibilities = models.TextField(blank=True)
    requirements = models.TextField(blank=True)
    nice_to_have = models.TextField(blank=True)
    location = models.CharField(max_length=200)
    remote_allowed = models.BooleanField(default=False)
    experience_level = models.CharField(max_length=20, choices=EXP_LEVEL_CHOICES)
    status = models.CharField(max_length=20, default="draft")  # draft, active, paused, closed
    description_embedding = VectorField(384)  # pgvector — from pgvector.django import VectorField; null until embed_job() called
    screening_questions = models.JSONField(default=list)  # AI-suggested + editor-edited
    screening_config = models.JSONField(default=dict)  # Gap G3: stage-1 hard-filter rules {"filters": {...}}
    screening_config_version = models.PositiveIntegerField(default=1)  # Gap G3: bumped on every rule edit
    ai_model_used = models.CharField(max_length=100, blank=True)  # which model scored candidates
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Application(models.Model):
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="applications")
    candidate = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE, related_name="applications")
    status = models.CharField(max_length=20, default="applied")  # applied, screened, not_matched, shortlisted, interview, offered, hired, rejected
    match_score = models.IntegerField(null=True, blank=True)  # 0-100 from AI
    match_rationale = models.TextField(blank=True)  # AI-generated explanation
    ai_model_used = models.CharField(max_length=100, blank=True)
    screened_at = models.DateTimeField(null=True, blank=True)
    shortlisted_at = models.DateTimeField(null=True, blank=True)

    # --- Gap G3: the stage-1 hard filter records what it excluded, and never decides ---
    not_matched_reason = models.TextField(blank=True)  # which rule fired, e.g. "experience_level"
    filter_rules_version = models.PositiveIntegerField(null=True, blank=True)  # = job.screening_config_version

    # --- Gap G1 / REQ-FR-051: employer-required assessments gate the shortlist ---
    assessment_gate_status = models.CharField(max_length=20, default="not_required")  # not_required, pending, passed, failed

    # --- Gap G2 / REQ-FR-052: a decision against the ranking is recorded, never blocked ---
    decision_override = models.BooleanField(default=False)
    decision_override_reason = models.TextField(blank=True)
    decided_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("job", "candidate")]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(decision_override=False)
                | models.Q(decision_override_reason__isnull=False),
                name="chk_override_has_reason",
            ),
        ]

    # not_matched is a filter outcome, not a rejection. Only a person may reject.
    def can_shortlist(self) -> bool:
        """REQ-FR-051. Shortlist is refused while the assessment gate is open or failed."""
        return self.assessment_gate_status in ("not_required", "passed")


class JobAssessmentRequirement(models.Model):
    """An assessment an employer attaches to a job as a required pre-shortlist step.

    Added 2026-10-03 to close Gap G1. REQ-FR-019/020 made assessments a *candidate*
    action; nothing made them an *employer* action, so a hiring manager could reach
    shortlist having seen no skill evidence at all. This join is what lets a job
    require one. It reuses assessments/assessment_attempts — the gate is satisfied by
    matching candidate + assessment on a completed attempt — so no attempt data is
    duplicated.
    """
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="required_assessments")
    assessment = models.ForeignKey("candidates.Assessment", on_delete=models.CASCADE, related_name="required_by_jobs")
    min_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)  # None = any completed attempt passes
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("job", "assessment")]

class AuditLogEntry(models.Model):
    """Append-only audit log — never updated or deleted."""
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=100)  # "application.screened", "job.created", "user.login"
    resource_type = models.CharField(max_length=50)  # "application", "job", "candidate", "user"
    resource_id = models.UUIDField()  # every core entity uses a UUID PK — IntegerField here was a bug (prd §19.2 item 6)
    details = models.JSONField(default=dict)  # action-specific context, NO raw PII
    ip_address = GenericIPAddressField()
    user_agent = models.CharField(max_length=500, blank=True)
    result = models.CharField(max_length=20)  # success, failure
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
```

---

## 9. Implementation Roadmap

### Phase 1: Foundation (Weeks 1-3) — Get Something Running

**Goal:** A working Django project where employers can post jobs and candidates can apply. No AI yet.

- [ ] Set up Django 5 project with PostgreSQL + Redis via Docker Compose
- [ ] Configure all security settings from Section 5.1
- [ ] Implement User model, email/password auth, email verification
- [ ] Implement CandidateProfile + EmployerProfile
- [ ] Implement Job model (CRUD for employers)
- [ ] Implement Application model (candidates apply to jobs)
- [ ] Basic Django Templates + TailwindCSS UI for both portals
- [ ] File upload: S3 presigned URLs for resume upload
- [ ] Basic email notifications (application received, job posted)

**Deliverable:** `docker-compose up` starts the full stack. Employer creates a job, candidate applies with a resume, employer sees the application in a list.

### Phase 2: AI Integration (Weeks 4-6) — The Core Value

**Goal:** AI-powered screening with free-tier OpenRouter. PII stripping. Explainable rankings.

- [ ] Implement `ai/providers.py` — OpenRouterProvider + OfflineFallbackProvider
- [ ] Implement PII stripping pipeline (regex + spaCy NER) on resume upload
- [ ] Implement `matching/vectorize.py` — sentence-transformers embedding, store in pgvector
- [ ] Implement Celery task: `screen_applications(job_id)` — hard filter → pgvector rank → LLM analyze top N
- [ ] Implement match rationale generation (evidence-cited, what matched, what missed)
- [ ] Implement bias audit check on AI rationale
- [ ] Employer dashboard: ranked application list with scores + rationale
- [ ] Show employer cost estimate before confirming AI screening batch
- [ ] Audit log entries for every AI scoring action

**Deliverable:** Employer posts a job, receives 50 applications, clicks "AI Screen All" — sees cost estimate ($0.00), confirms, and 2 minutes later sees ranked candidates with explanations.

### Phase 3: Candidate AI Features (Weeks 7-9) — The Differentiator

**Goal:** Skill assessments + AI interview coaching + Journey Mapping MVP.

- [ ] Skill assessment system: employer-created or platform-created skill tests
- [ ] Assessment taking UI + auto-scoring (for technical: code sandbox via Piston API or similar)
- [ ] AI interview coaching: candidate pastes practice answer → AI gives feedback on structure, content, missing points
- [ ] Journey Mapping MVP: parse resume → extract timeline events → render interactive timeline
- [ ] Journey Mapping: skill evolution chart (which skills acquired when)
- [ ] Journey Mapping: dynamic storytelling — generate a narrative summary optimized for a specific target job
- [ ] Candidate dashboard: match scores for all applied jobs, visible AI rationale

**Deliverable:** Candidate uploads resume, sees their career timeline, takes a Python skill assessment, gets AI coaching on "Tell me about yourself" for a specific job they applied to.

### Phase 4: Production Hardening (Weeks 10-12) — Security + Scale

**Goal:** Everything from Section 5 fully implemented. Monitoring. Backup. Compliance.

- [ ] Argon2 password hashing verified, MFA (TOTP) implemented
- [ ] Field-level encryption (PII fields) deployed and tested
- [ ] S3 file serving through authenticated views (not direct S3 URLs)
- [ ] Rate limiting on all endpoints, stricter on AI endpoints
- [ ] CSP, HSTS, all security headers verified with securityheaders.com
- [ ] Sentry integrated, Prometheus + Grafana dashboards live
- [ ] GDPR: data export endpoint, data deletion endpoint, consent capture
- [ ] Automated backup verification (restore test)
- [ ] CI/CD pipeline: lint, test, pip-audit, bandit, Docker build
- [ ] Load testing: 100 concurrent applicants applying simultaneously
- [ ] Documentation: setup guide, API docs (DRF Spectacular or Django Ninja OpenAPI)

**Deliverable:** Production-ready deployment on a single VPS (or Docker Swarm / Kubernetes if scaling). Security audit passed.

### Phase 5: Advanced Features (Weeks 13+) — Competitive Differentiation

- [ ] Full Journey Mapping: skill ontology mapping (map "JS", "JavaScript", "ECMAScript" to same skill node), hidden skill detection from project descriptions
- [ ] Impact visualization: extract numbers from resume text ("increased revenue by 40%", "managed team of 8")
- [ ] Learning trajectory: suggest next skills based on career goals + market demand
- [ ] Multi-language support (i18n) — critical for Bangladesh/emerging markets
- [ ] Stripe integration: freemium billing, premium candidate subscriptions, employer plans
- [ ] Mobile-responsive PWA or React Native app
- [ ] WebSockets for real-time interview coaching (candidate typing → AI responding live)

---

## 10. What You Need to Build This

### 10.1 Infrastructure

| Item | Specification | Cost |
|---|---|---|
| **Development machine** | Any modern laptop/desktop, 8GB+ RAM | $0 (existing) |
| **Production VPS** | 2-4 CPU, 4-8GB RAM, 40-80GB SSD (DigitalOcean, Linode, Hetzner, or similar) | $10-40/month |
| **Database** | PostgreSQL 17 with pgvector extension (self-hosted on VPS, or managed like Supabase/Neon if preferred) | $0 (self-hosted) or $0-25/mo (managed) |
| **Object storage** | MinIO (self-hosted, S3-compatible) or Cloudflare R2 (10GB free, then $0.015/GB) | $0 |
| **Redis** | Redis 7 (self-hosted via Docker) | $0 |
| **Domain name** | matchminds.io or similar | ~$10/year |
| **SSL certificates** | Let's Encrypt (free, auto-renewed via certbot) | $0 |

### 10.2 Software Dependencies

```text
# Core
Python >= 3.12
Django >= 5.2  # LTS (5.0 is EOL — no security patches)  # LTS — 5.0 is EOL, no security patches
Django REST Framework >= 3.14
djangorestframework-simplejwt  # JWT auth for API
django-otp  # TOTP MFA
django-ratelimit  # rate limiting
django-celery-results  # Celery result backend in Django DB
celery >= 5.3
redis >= 5.0

# AI / ML
openai >= 1.0  # OpenRouter SDK (OpenAI-compatible)
sentence-transformers >= 2.0  # pgvector embeddings (offline, free)
spacy >= 3.7  # PII detection NER (offline, free)
cryptography >= 42.0  # AES-256-GCM field encryption
argon2-cffi  # Argon2id password hashing (Django built-in)

# Database
psycopg2-binary >= 2.9
pgvector >= 0.2.0  # PostgreSQL extension + Python wrapper (import from pgvector.django)
django-encrypted-model-fields >= 1.3  # EncryptedField/EncryptedCharField (AES-256-GCM via cryptography)
django-storages >= 1.14  # S3-compatible storage backend
boto3 >= 1.34  # AWS S3 / MinIO SDK (for presigned URLs)

# Security
python-magic >= 0.4  # MIME type validation (uses libmagic)
clamav-client >= 0.10  # Virus scanning for uploaded files (clamd protocol)
pdfplumber >= 0.11  # PDF text extraction for resume parsing

# Monitoring
sentry-sdk >= 2.14  # Error tracking (no PII in events)
prometheus-client >= 0.20  # Prometheus metrics endpoint

# Frontend (Django templates + HTMX path)
django-htmx >= 1.0  # HTMX integration with Django

# Production
gunicorn >= 22.0  # WSGI server

# Email
django-anymail >= 10.0  # Unified email backend (SendGrid, Resend, AWS SES)

# Billing
stripe >= 10.0  # Payment processing for freemium plans

# Dev / CI
pytest >= 8.0
pytest-django >= 4.8
pytest-cov >= 5.0
factory-boy >= 3.3  # test fixtures
pip-audit >= 0.20  # dependency vulnerability scanning
bandit >= 1.7  # Python security static analysis
black >= 24.0  # code formatting
flake8 >= 7.0  # linting
isort >= 5.13  # import sorting
mypy >= 1.13  # type checking
drf-spectacular >= 0.28  # OpenAPI schema generation for DRF
sphinx >= 8.2  # documentation generation
```

### 10.3 API Keys Needed

| Key | Purpose | Cost |
|---|---|---|
| **OpenRouter API key** | All AI calls (free tier covers development + early production) | Free |
| **Stripe API keys** (test mode first, live later) | Billing for premium plans | Free (test mode) |
| **SendGrid / Resend / AWS SES API key** | Transactional emails (application confirmations, interview invites) | Free tier available (Resend: 3,000 emails/month free) |
| **Sentry DSN** | Error tracking | Free (10K errors/month free) |

### 10.4 Team and Roles (from the original document)

| Person | Role | Primary Responsibilities |
|---|---|---|
| Sardar Shihab | Full-Stack Engineer | Django templates/HTMX UI, TailwindCSS, interactive journey mapping charts, responsive design; backend endpoints as needed |
| Arnob Biswas Antu | Frontend Engineer | Employer dashboard UI, application review interface, interview scheduling UI, real-time status updates |
| Ishrak Hossain | Backend & AI Engineer | Django backend, DRF API, Celery tasks, OpenRouter AI integration, PII stripping, pgvector matching, security implementation |
| Mohammad Abdul Ahad | UI/UX Designer | Design system ownership — colour, type and spacing tokens, component library, accessibility (WCAG 2.1 AA) |
| Fahad Haque | UI/UX Designer | Candidate journey wireframes, employer dashboard UX, Journey Mapping interactive timeline design |

**Missing role:** DevOps/Infrastructure — initially handled by Ishrak Hossain (backend engineer). When scaling, add or outsource.

### 10.5 Estimated Timeline to MVP

- **Week 1-3:** Phase 1 — working Django app with job posting + application (no AI)
- **Week 4-6:** Phase 2 — AI screening with OpenRouter free tier
- **Week 7-9:** Phase 3 — candidate AI features (assessments, coaching, journey mapping MVP)
- **Week 10-12:** Phase 4 — security hardening, production deployment
- **Week 13+:** Phase 5 — advanced features, billing, mobile

**MVP definition:** Employer can post a job, candidates can apply with a resume, AI screens and ranks applicants with explainable scores using free-tier AI, candidates see their match scores and get interview coaching. That's Phase 1-3, ~9 weeks with a focused team of 4.

---

## 11. Open Source References & Inspirations

The following projects informed this architecture. We studied their strengths and explicitly avoided their gaps:

### Architecture References
- **CandiSift** (confused-ai/candisift) — Hexagonal architecture, PII stripping before AI, cost-estimate-before-process, evidence-cited breakdowns, bias-audit endpoint. We adopted all of these patterns. We diverge by using Django instead of FastAPI (ecosystem, team skills) and adding the candidate journey mapping feature.
- **candidacy** (steelburn/candidacy) — OpenRouter integration as AI provider (directly relevant), DBML schema-as-code approach, 12-service microservices (we chose monolith-to-start for simplicity, can split later if needed).
- **Vekt** (Behnoudmst/vekt) — GDPR-compliant by default, protected file serving, configurable data retention, privacy policy included. We adopted the privacy-first mindset.
- **SkillAI** (olafkfreund/SkillAI) — Row-level security in PostgreSQL, MCP server concept (interesting for future — expose Match Minds data to Claude Desktop for workflow automation).

### Things We Explicitly Don't Copy
- **OpenCATS** (opencats/OpenCATS): No AI, PHP stack, dated UX — confirmed why we need to build new, not fork
- **LinkedIn Recruiter model**: Profile scraping + keyword search — we don't build a profile database; we build deep per-candidate profiles from what candidates submit
- **HireVue's facial analysis**: Banned under EU AI Act, bias backlash — we do text-based AI only, fully compliant

### Relevant Market Data Sources
- AI Recruitment Market Report (ReportPrime, 2025): Market size, company revenues, YoY growth — used in Section 2
- JobsPipe AI Recruiting Companies Comparison (2026): Stage-by-stage tool mapping — used in Section 2
- EU AI Act (adopted May 2024, effective February 2025): Emotion recognition ban in hiring — used in Section 5.4 compliance argument

---

## Appendix A: Success Criteria — How We Measure If We're Winning

| Metric | Target | How We Beat Competitors |
|---|---|---|
| **Time-to-screen** | < 5 minutes for 100 applications | Eightfold/HireVue require 6-12 month implementation; we're instant |
| **Cost per hire** | < $50 for AI screening (vs. $35K+/year for HireVue) | Our free tier means $0 for first 50 req/day; paid only when volume exceeds free tier |
| **Candidate satisfaction** | > 80% would recommend | No competitor gives candidates AI coaching + journey mapping — we do |
| **Bias audit pass rate** | 100% of AI rationales pass bias audit | Every competitor has some bias risk; we audit every rationale before showing it |
| **Data breach incidents** | Zero | PII never reaches AI providers; field-level encryption; audit logging — most competitors send full profiles to third-party AI |
| **Implementation time** | < 1 week for a new employer | Eightfold takes 6-12 months; we're self-serve signup + post job |
| **SMB accessibility** | <$100/month entry point | Eightfold starts at $50K/year; we start at $0 (free tier) |

---

## Appendix B: Key Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| **OpenRouter free tier changes or is removed** | Medium | High | Abstraction layer (AIProvider interface) makes switching providers a one-class change. Offline spaCy + pgvector matching works without ANY AI API. Start with offline-first for matching. |
| **LLM hallucinations in match rationale** | Medium | Medium | Evidence-cited format: LLM must cite specific resume text for each claim. If no evidence, rationale says "no evidence found" rather than fabricating. Human recruiter reviews before acting on AI score. |
| **Resume parsing accuracy** | Medium | Medium | Fallback: candidates can manually edit their parsed profile. Manual + AI hybrid. IBM Granite Docling (used by candidacy) achieves 85-95% — we can integrate it later if needed. |
| **Scaling beyond free tier** | High (eventual) | Medium | Tiered model: free tier → cheap OpenRouter models ($0.06-0.10/1M tokens) → self-hosted open model (OLMo, Llama 3.1 8B via vLLM) when volume justifies hardware cost |
| **Data breach** | Low | Critical | Defense-in-depth from Section 5. Encryption at rest + in transit. PII stripped before any external service. Regular security audits. Bug bounty program once production live. |
| **Competitors copy Journey Mapping feature** | Low (short term) | Medium | Journey Mapping requires deep integration of parsing + timeline + storytelling + per-application narrative — it's a system, not a feature. By the time a competitor builds it, we have data and network effects from candidates who've built their journeys on our platform. |

---

## Appendix C: Gap-Fill Addendum (Updates & Additions)

> This appendix fills every gap identified during documentation review. Each section is cross-referenced to the original document section it supplements.

### C.1 Error Handling & Retry Strategy (supplements §5.5, §6)

**Philosophy:** Fail gracefully, never expose stack traces to users, always log for debugging, and degrade gracefully when AI providers are unavailable.

| Scenario | Behavior | User-Facing Outcome |
|---|---|---|
| OpenRouter API returns 429 (rate limit) | Celery task retries with exponential backoff (3 retries: 5s, 15s, 45s); if still failing, falls back to pgvector-only scoring without LLM rationale | Employer sees "AI analysis delayed, using semantic similarity only" badge |
| OpenRouter API returns 503/500 | `ManagedException` raised in `ai/providers.py`; Celery retries with circuit breaker; after 3 failures, switches to offline fallback (spaCy NER + keyword matching) | Same as rate limit: semantic-only matching, no LLM rationale |
| Resume file fails MIME validation | Rejected immediately with user-facing error: "Invalid file type. Please upload PDF, DOC, or DOCX." | File not stored; user can retry |
| Virus scan detects malware | File quarantined, Celery task fails, Security team alerted via Sentry, AuditLogEntry records the block | User notified via email: "Your file was flagged for security review" |
| AI rationale contains potential PII (leaked through PII stripping) | Post-processing filter catches it; rationale is re-stripped; AuditLogEntry records the leak attempt | Rationale shown is fully anonymized |
| pgvector extension unavailable | Falls back to Python-level cosine similarity using `sentence-transformers` directly (slower but functional) | No user-visible impact except slightly slower ranking |
| Database connection lost | Django's `CONN_MAX_AGE` + retry middleware handles transient failures; Celery task retries with backoff | User sees standard 500 error page; retry later |
| Celery worker dies mid-task | Redis stores task state; `CELERY_TASK_ACKS_LATE=True` + `task_reject_on_worker_lost=True` ensures re-queueing | Task retries automatically on next available worker |

```python
# ai/errors.py — exception hierarchy
class AIServiceError(Exception):
    """Base error for AI service failures."""
    pass

class AIRateLimitError(AIServiceError):
    """OpenRouter free tier rate limit exceeded."""
    pass

class AIUnavailableError(AIServiceError):
    """AI provider returned 5xx or is unreachable."""
    pass

# tasks/screening.py — retry pattern in Celery
@celery_app.task(bind=True, max_retries=3, default_retry_delay=5)
def screen_application(self, job_id, candidate_id):
    try:
        # ... AI processing ...
    except AIRateLimitError as e:
        raise self.retry(exc=e, countdown=60, max_retries=3)
    except AIUnavailableError as e:
        # Fallback to pgvector-only scoring
        return fallback_similarity_score(job_id, candidate_id)
```

### C.2 Caching Strategy (supplements §4.1, §5.3)

Redis serves three distinct purposes per tier with different TTLs:

| Cache Key Pattern | TTL | Content | Eviction Policy |
|---|---|---|---|
| `user_profile:{user_id}` | 1 hour | Serialized user + profile data | LRU |
| `job_embeddings:{job_id}` | 24 hours | pgvector embedding for job description | LRU |
| `similarity_matrix:{job_id}` | 2 hours | Pre-computed candidate-job similarity scores | LRU |
| `rate_limit:{user_id}:{endpoint}` | 15 minutes | Rate limit counters | TTL expiry |
| `openrouter_quota:{day}` | 24 hours (midnight reset) | Free tier remaining quota tracker | TTL expiry |
| `skill_taxonomy:v1` | 7 days (versioned) | Canonical skill name mappings (JS→JavaScript, etc.) | Versioned override |
| `ai_response:{hash}` | 6 hours | Cached LLM responses keyed by prompt hash (deduplication) | LRU |

**Cache Invalidation Rules:**
- Job update → invalidate `job_embeddings:{job_id}` and all `similarity_matrix:{job_id}`
- Resume re-upload → invalidate `user_profile:{user_id}`
- Skill update → invalidate `user_profile:{user_id}` (candidate side only)
- Daily midnight → invalidate `openrouter_quota:{day}` (quota reset)

### C.3 Monitoring & Alerting Thresholds (supplements §5.6)

| Metric | Alert Threshold | Severity | Action |
|---|---|---|---|
| Django 5xx error rate | > 5% over 5 min | Critical | PagerDuty to on-call engineer |
| Celery task failure rate | > 15% over 10 min | Critical | PagerDuty; queue paused |
| OpenRouter API error rate | > 20% over 5 min | High | Auto-switch to offline fallback |
| pgvector query latency | > 500ms avg over 10 requests | Warning | Investigate index performance |
| Database connection pool | > 90% utilization for 2 min | Warning | Scale worker pool |
| Redis memory usage | > 80% | Warning | Increase memory or purge old keys |
| AI API cost (daily) | > $5 (paid tier breach) | Warning | Alert; auto-switch to free models |
| Suspicious login attempts | > 10 failed logins / IP / 15 min | Warning | Auto-block IP for 1 hour; notify user |
| Audit log write failures | > 5 failures / 5 min | Critical | Halt processing; alert security team |
| SSL/TLS certificate expiry | < 30 days | Warning | Auto-renew; alert if renewal fails |

**SLA Targets:**
- 99.9% uptime (max 43 min downtime/year)
- < 2 sec median page load
- < 5 min median AI screening time for 100 applications
- 4-hour response time for P1 (critical security) incidents

### C.4 Disaster Recovery Plan (supplements §5.2)

| Component | RTO (Recovery Time Objective) | RPO (Recovery Point Objective) | Strategy |
|---|---|---|---|
| Primary PostgreSQL | 2 hours | 15 minutes | WAL archiving to S3 every 15 min; pg_basebackup hourly; point-in-time recovery (PITR) tested monthly |
| Redis | 1 hour | 0 (no persistence needed) | No RDB/AOF; state is ephemeral; restart from empty cache is fine |
| File storage (S3/MinIO) | 4 hours | 0 | Cross-region replication; Glacier deep archive for older resumes (90+ days) |
| Application containers | 15 minutes | 0 | Automated redeployment via CI/CD; Docker image registry versioned |
| AI API keys / secrets | 5 minutes | 0 | Environment variables via Docker secrets or AWS Secrets Manager; backup key rotation every 90 days |

**DR Testing Schedule:**
- Monthly: `pg_restore` from latest WAL backup to staging environment
- Quarterly: Full DR drill — simulate primary data center failure
- Annually: Third-party penetration test + compliance audit (SOC 2 Type II)

### C.5 Penetration Testing Plan (supplements §5.5, §5.6)

| Test | Frequency | Scope | Tool |
|---|---|---|---|
| OWASP ZAP scan | Weekly (CI) | All public endpoints | OWASP ZAP Docker image |
| Bandit (Python SAST) | Every commit (CI) | Python source code | bandit |
| pip-audit (dependency scan) | Every commit (CI) | Python dependencies | pip-audit |
| SQL injection test | Quarterly | All DB queries | sqlmap (authorized) |
| CSRF/XSS test | Quarterly | All forms + API | Manual + OWASP ZAP |
| Auth bypass test | Quarterly | Login, MFA, RBAC | Manual pentest |
| Network port scan | Quarterly | All exposed ports | nmap |
| Full manual pentest | Annually | End-to-end | Third-party vendor |

### C.6 CI/CD Pipeline Specification (supplements §5.6, §10.2)

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
          POSTGRES_DB: matchminds_test
        options: >-
          --health-cmd "pg_isready"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 5
        ports: ["5432:5432"]
      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 5
        ports: ["6379:6379"]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install -r requirements-dev.txt
          pip install -r requirements.txt
          pip install drf-spectacular

      - name: Lint — flake8
        run: flake8 matchminds/ --max-line-length=120

      - name: Lint — black (check)
        run: black --check matchminds/

      - name: Lint — isort (check)
        run: isort --check matchminds/

      - name: Type check — mypy
        run: mypy matchminds/ --ignore-missing-imports

      - name: Security scan — bandit
        run: bandit -r matchminds/ -c bandit.yaml

      - name: Dependency audit — pip-audit
        run: pip-audit -r requirements.txt

      - name: Run tests
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/matchminds_test
          REDIS_URL: redis://localhost:6379/0
          DJANGO_SETTINGS_MODULE: config.settings.ci
        run: |
          python manage.py migrate
          pytest tests/ -v --cov=matchminds --cov-fail-under=80

      - name: Generate OpenAPI schema
        run: python manage.py spectacular --file schema.yml

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
        run: echo ${{ secrets.DOCKERHUB_TOKEN }} | docker login -u ${{ secrets.DOCKERHUB_USER }} --password-stdin
      - name: Build and push
        uses: docker/build-push-action@v6
        with:
          context: .
          push: true
          tags: matchminds/app:${{ github.sha }},matchminds/app:latest
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
          ssh ${{ secrets.STAGING_USER }}@${{ secrets.STAGING_HOST }} \
            "docker-compose pull && docker-compose up -d --wait"
      - name: Smoke test
        run: |
          curl -f https://staging.matchminds.com/health/
          curl -f https://staging.matchminds.com/api/v1/jobs/

  deploy-production:
    needs: deploy-staging
    runs-on: ubuntu-24.04
    if: github.ref == 'refs/heads/main'
    environment: production
    steps:
      - name: Deploy to production
        run: |
          ssh ${{ secrets.PROD_USER }}@${{ secrets.PROD_HOST }} \
            "docker-compose pull && docker-compose up -d --wait"
      - name: Health check
        run: |
          curl -f https://app.matchminds.com/health/

  rollback-staging:
    runs-on: ubuntu-24.04
    needs: deploy-staging
    if: github.event_name == 'workflow_dispatch'
    environment: staging
    steps:
      - uses: actions/checkout@v4
      - name: Rollback to previous release image
        run: |
          ssh ${{ secrets.STAGING_USER }}@${{ secrets.STAGING_HOST }} \
            "docker image tag matchminds/app:v$(cat .version-tag-staging | rev | cut -d. -f2- | rev) matchminds/app:latest && docker-compose up -d --wait"
      - name: Post-rollback health check
        run: |
          curl -f https://staging.matchminds.com/health/
          curl -f https://staging.matchminds.com/api/v1/jobs/
      - name: Comment on PR / Notify Slack
        run: |
          echo "Rollback to previous release completed for staging." | curl -X POST -H 'Content-type: application/json' --data '{"text": "Staging rollback completed — matchminds/staging"} ' $SLACK_WEBHOOK_URL

  rollback-production:
    runs-on: ubuntu-24.04
    needs: deploy-production
    if: github.event_name == 'workflow_dispatch'
    environment: production
    steps:
      - uses: actions/checkout@v4
      - name: Rollback to previous release image
        run: |
          ssh ${{ secrets.PROD_USER }}@${{ secrets.PROD_HOST }} \
            "docker image tag matchminds/app:v$(cat .version-tag-prod | rev | cut -d. -f2- | rev) matchminds/app:latest && docker-compose up -d --wait"
      - name: Post-rollback health check
        run: |
          curl -f https://app.matchminds.com/health/
      - name: Comment on PR / Notify Slack
        run: |
          echo "Rollback to previous release completed for production." | curl -X POST -H 'Content-type: application/json' --data '{"text": "Production rollback completed — matchminds/production"} ' $SLACK_WEBHOOK_URL

> **Rollback strategy:** Each successful production deploy records the current version tag to `.version-tag-prod` (and `.version-tag-staging` for staging). The rollback job reads this file, extracts the previous version tag, retags the previous image as `:latest`, and redeploys via `docker-compose`. Manual trigger via GitHub Actions "Run workflow" button with `workflow_dispatch`. Target rollback time: < 5 minutes.

```

### C.7 Environment Variables (.env) Reference (supplements §10.3)

| Variable | Required | Default | Description |
|---|---|---|---|
| `DJANGO_SECRET_KEY` | Yes | — | 512-bit random key; rotate every deploy |
| `DJANGO_SETTINGS_MODULE` | Yes | `config.settings.local` | Settings module path |
| `DB_PASSWORD` | Yes | `devpassword` | Postgres password; interpolated into `DATABASE_URL` by docker-compose |
| `DATABASE_URL` | Yes | — | PostgreSQL connection string (`postgresql://user:pass@host:port/db`) |
| `REDIS_URL` | Yes | — | Redis connection string (`redis://:password@host:port/db`) |
| `CELERY_BROKER_URL` | Yes | `redis://redis:6379/0` | Celery broker (message queue) |
| `CELERY_RESULT_BACKEND` | Yes | `redis://redis:6379/1` | Celery result storage |
| `OPENROUTER_API_KEY` | Yes (AI features) | — | OpenRouter API key for free tier models |
| `STRIPE_SECRET_KEY` | No (Phase 5) | — | Stripe secret key for billing |
| `STRIPE_WEBHOOK_SECRET` | No (Phase 5) | — | Webhook signing secret |
| `EMAIL_BACKEND_URL` | Yes | — | SMTP or API endpoint for transactional emails |
| `SENTRY_DSN` | Yes | — | Sentry error tracking DSN |
| `ALLOWED_HOSTS` | Yes | `localhost` | Comma-separated list of hosts |
| `CSRF_TRUSTED_ORIGINS` | Yes | — | Comma-separated list of trusted origins |
| `AWS_ACCESS_KEY_ID` | No (S3) | — | S3-compatible storage access key |
| `AWS_SECRET_ACCESS_KEY` | No (S3) | — | S3-compatible storage secret key |
| `AWS_STORAGE_BUCKET_NAME` | No (S3) | — | S3 bucket name |
| `AWS_S3_REGION_NAME` | No (S3) | — | S3 region |
| `AWS_S3_ENDPOINT_URL` | No (MinIO) | — | Custom endpoint URL for MinIO |
| `ENCRYPTION_KEY` | Yes | — | AES-256-GCM key for field-level encryption (Fernet) |
| `CLAMD_HOST` | No (antivirus) | `localhost` | ClamAV daemon host |
| `CLAMD_PORT` | No (antivirus) | `3310` | ClamAV daemon port |
| `DEFAULT_FROM_EMAIL` | Yes | — | Email sender address |
| `DEBUG` | No | `False` | Django debug mode (must be False in production) |
| `SITE_ID` | Yes | `1` | Django site framework ID |

### C.8 Data Migration Strategy (supplements §8, §9)

**Schema migrations:** Standard Django `makemigrations` / `migrate` workflow. Each migration reviewed in code review. No external migration tools needed — Django's built-in migration system handles all schema and data migrations.

**Data migrations:** Custom Django data migration scripts for:
- PII re-encryption key rotation (every 90 days): Re-encrypt all `EncryptedCharField` values with new key via Celery background task; old keys retained for 30 days for recovery
- Resume embedding upgrades: When `sentence-transformers` model is updated, re-embed all resumes via batched Celery task
- Skill taxonomy sync: Map old skill names to new canonical names during migration (e.g., "JS" → "JavaScript")

**Zero-downtime deployment:**
- Database: Add new columns as nullable first; migrate data in background; then set NOT NULL in a follow-up migration
- Containers: Rolling updates with health check wait; 3 replica minimum for Django + Celery
- Embeddings: New and old models run side-by-side during transition; traffic switched via feature flag

### C.9 OpenRouter Rate Limit Handling (supplements §6)

The OpenRouter free tier allows 20 req/min and 50 req/day. The system handles this through:

1. **Quota tracking** — Redis key `openrouter_quota:{YYYY-MM-DD}` tracks daily usage. Checked before every AI task. If exceeded, task falls back to offline strategy immediately without calling the API.

2. **Request queuing** — Celery tasks that need OpenRouter are queued with `queue="ai_high_priority"` (for top-N rationale) and `queue="ai_low_priority"` (for batch parsing). High-priority queue gets 80% of worker capacity when quota is low.

3. **Batch optimization** — Instead of 20 individual LLM calls for 20 resumes, batch them into fewer calls by combining multiple candidates' anonymized data into a single LLM prompt (reduces from 20 calls to 4 calls, each analyzing 5 candidates).

4. **Intelligent degradation** — Rate limit hierarchy:
   - Level 0 (quota > 50% remaining): Full LLM analysis + rationale + bias audit
   - Level 1 (quota 20-50% remaining): LLM rationale for top 5 candidates only
   - Level 2 (quota < 20% remaining): pgvector-only scoring, no LLM
   - Level 3 (quota exhausted): Offline spaCy NER + keyword matching only

5. **Auto-refill prediction** — System monitors quota consumption rate and predicts when free tier will replenish; schedules heavy batch jobs during low-traffic hours.

### C.10 Internationalization (i18n) Strategy (supplements §7, §9 Phase 5)

**Phase 1 (MVP):** English only. Django i18n strings wrapped in `gettext_lazy()` from day one for easy future translation.

**Phase 5 (advanced):** Full i18n support:
- Django `i18n_patterns` for URL routing
- `django-rosetta` for translation management interface
- `.po`/`.mo` files per language (priority: Bengali, Indonesian, Portuguese, Spanish)
- RTL language support (Arabic) via CSS `dir="rtl"` attribute
- Date/time/number formatting via `babel` library
- Search index per-language (Elasticsearch or pgvector with language-specific tokenizers)
- Journey Mapping narratives generated in candidate's preferred language (detected from browser or profile setting)

### C.11 Complete Database Models (supplements §8.2)

The original §8.2 was labeled "abridged." Below are the **complete** Django model definitions for all entities, including those referenced in the ER diagram (§8.1) but never defined in the original.

**Imports needed:**
```python
# from pgvector.django import VectorField
# from django_encrypted_model_fields.fields import EncryptedCharField
```

```python
# candidates/models.py — Additional models
class Skill(models.Model):
    """Canonical skill taxonomy. Maps synonyms to canonical names."""
    canonical_name = models.CharField(max_length=100, unique=True)  # "JavaScript"
    aliases = models.JSONField(default=list)  # ["JS", "ECMAScript", "Node.js"]
    category = models.CharField(max_length=50)  # "programming", "soft_skill", "domain"
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class CandidateSkill(models.Model):
    """Skills explicitly associated with a candidate, with proficiency and source."""
    candidate = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE, related_name="candidate_skills")
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)
    level = models.CharField(max_length=20, choices=SKILL_LEVEL_CHOICES)  # beginner, intermediate, expert
    years_experience = models.DecimalField(max_digits=3, decimal_places=1, null=True)
    source = models.CharField(max_length=30, choices=[
        ("resume_parse", "AI Parsed from Resume"),
        ("self_reported", "Self-Reported"),
        ("assessment", "From Assessment"),
        ("journey_map", "From Journey Mapping"),
    ])
    verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Certification(models.Model):
    candidate = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE, related_name="certifications")
    name = models.CharField(max_length=200)
    issuing_organization = models.CharField(max_length=200)
    issue_date = models.DateField()
    expiry_date = models.DateField(null=True, blank=True)
    credential_id = EncryptedCharField(max_length=200, blank=True)
    credential_url = models.URLField(max_length=500, blank=True)
    verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class Assessment(models.Model):
    """A skill assessment that candidates can take."""
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="assessments")
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES)  # beginner, intermediate, advanced
    question_count = models.IntegerField(default=10)
    time_limit_minutes = models.IntegerField(default=30)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

class AssessmentQuestion(models.Model):
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name="questions")
    question_type = models.CharField(max_length=20, choices=[
        ("multiple_choice", "Multiple Choice"),
        ("coding", "Coding Challenge"),
        ("text", "Free Text"),
    ])
    question_text = models.TextField()
    options = models.JSONField(default=list)  # For multiple choice
    correct_answer = models.TextField(blank=True)  # Expected answer
    code_language = models.CharField(max_length=20, blank=True)  # For coding challenges
    max_score = models.IntegerField(default=10)

class AssessmentAttempt(models.Model):
    candidate = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE, related_name="assessment_attempts")
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name="attempts")
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    status = models.CharField(max_length=20, default="in_progress")  # in_progress, completed, timed_out
    answers = models.JSONField(default=list)  # [{"question_id": 1, "answer": "...", "score": 8}]

class InterviewPack(models.Model):
    """AI-generated structured interview question pack for a job."""
    job = models.ForeignKey("matching.Job", on_delete=models.CASCADE, related_name="interview_packs")
    title = models.CharField(max_length=300)
    questions = models.JSONField(default=list)  # [{"question": "...", "category": "...", "follow_ups": [...]}]
    scoring_rubric = models.JSONField(default=list)  # [{"criterion": "technical", "weight": 0.4, "scale": 5}]
    ai_model_used = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

class Interview(models.Model):
    application = models.ForeignKey("matching.Application", on_delete=models.CASCADE, related_name="interviews")
    interview_pack = models.ForeignKey(InterviewPack, on_delete=models.SET_NULL, null=True)
    scheduled_at = models.DateTimeField()
    duration_minutes = models.IntegerField(default=45)
    status = models.CharField(max_length=20, default="scheduled")  # scheduled, completed, cancelled
    video_call_url = models.URLField(max_length=500, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class InterviewFeedback(models.Model):
    interview = models.ForeignKey(Interview, on_delete=models.CASCADE, related_name="feedback")
    interviewer = models.ForeignKey("accounts.User", on_delete=models.CASCADE)
    scores = models.JSONField(default=dict)  # {"technical": 4, "communication": 3, "culture": 5}
    comments = models.TextField(blank=True)
    overall_recommendation = models.CharField(max_length=20, choices=[
        ("strong_yes", "Strong Yes"),
        ("yes", "Yes"),
        ("no", "No"),
        ("strong_no", "Strong No"),
    ])
    submitted_at = models.DateTimeField(auto_now_add=True)

class Notification(models.Model):
    recipient = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=30, choices=[
        ("application_update", "Application Update"),
        ("interview_scheduled", "Interview Scheduled"),
        ("ai_score_ready", "AI Score Ready"),
        ("offer", "Offer"),
        ("system", "System"),
    ])
    read = models.BooleanField(default=False)
    url = models.CharField(max_length=500, blank=True)  # Link to relevant page
    created_at = models.DateTimeField(auto_now_add=True)

class Message(models.Model):
    """Real-time communication between candidate and employer."""
    application = models.ForeignKey("matching.Application", on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="sent_messages")
    recipient = models.ForeignKey("accounts.User", on_delete=CASCADE, related_name="received_messages")
    content = models.TextField()
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

# employers/models.py — Additional models
class Subscription(models.Model):
    employer = models.OneToOneField(EmployerProfile, on_delete=models.CASCADE, related_name="subscription")
    plan = models.CharField(max_length=20, choices=[
        ("free", "Free (3 jobs, 50 AI screens/mo)"),
        ("starter", "Starter ($100/mo, 50 jobs, 500 AI screens/mo)"),
        ("growth", "Growth ($500/mo, 500 jobs, 5000 AI screens/mo)"),
        ("enterprise", "Enterprise ($5000/mo, unlimited)"),
    ])
    stripe_customer_id = EncryptedCharField(max_length=100, blank=True)
    stripe_subscription_id = EncryptedCharField(max_length=100, blank=True)
    current_period_end = models.DateTimeField()
    ai_quota_remaining = models.IntegerField(default=50)
    ai_quota_reset_date = models.DateTimeField()
    max_jobs = models.IntegerField(default=3)
    jobs_used = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

# core/models.py — Additional models
class DataExportRequest(models.Model):
    """GDPR Article 20 — Right to data portability."""
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="export_requests")
    status = models.CharField(max_length=20, default="pending")  # pending, processing, ready, expired
    file_url = models.CharField(max_length=500, blank=True)  # S3 key
    requested_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

class DataDeletionRequest(models.Model):
    """GDPR Article 17 — Right to erasure."""
    user = models.OneToOneField("accounts.User", on_delete=models.CASCADE, related_name="deletion_request")
    reason = models.TextField(blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, default="pending")  # pending, processing, completed
```
```

**Updated Entity Relationship Diagram:**

```
Users (1) ───(1)───< (N) CandidateProfile/EmployerProfile
   │                  │
   │                  ├──(1)───< (N) CandidateSkill ───(N)──> Skills
   │                  ├──(1)───< (N) CandidateResume
   │                  ├──(1)───< (N) Certification
   │                  ├──(1)───< (N) CandidateSkill ───(N)──> Skills
   │                  ├──(1)───< (N) AssessmentAttempt ───(N)──> Assessments
   │                  └──(1)───< (N) Applications ───(N)──> Jobs
   │                            │                       │
   │                            ├──(1)───< (N) InterviewFeedback
   │                            ├──(1)───< (N) Messages
   │                            └──(1)───< (N) Interviews ───(N)──> InterviewPacks ───(N)──> InterviewQuestions
   │
EmployerProfile ───(1)───< (1) Subscription
                  ├──(1)───< (N) Jobs
                  ├──(1)───< (N) InterviewFeedback (as interviewer)
                  └──(1)───< (N) Messages (as recipient)

AuditLogEntry: actor_id → Users.id, resource_id → any entity
Notification: recipient_id → Users.id
DataExportRequest / DataDeletionRequest: user_id → Users.id
```

### C.12 API Endpoint Specification (supplements §7.3)

#### Authentication & User Management
```http
POST   /api/v1/auth/register/                    # Register new user (email, password, role)
POST   /api/v1/auth/login/                       # Login, return JWT access + refresh tokens
POST   /api/v1/auth/refresh/                     # Refresh JWT access token
POST   /api/v1/auth/logout/                      # Revoke refresh token
POST   /api/v1/auth/mfa/enable/                  # Enable TOTP MFA
POST   /api/v1/auth/mfa/verify/                  # Verify TOTP code
GET    /api/v1/auth/me/                          # Get current user profile
PUT    /api/v1/auth/me/                          # Update user profile
POST   /api/v1/auth/password/change/             # Change password
POST   /api/v1/auth/password/reset/              # Request password reset email
POST   /api/v1/auth/password/reset/confirm/      # Confirm password reset
```

#### Candidate Endpoints
```http
GET    /api/v1/candidates/me/                    # Get candidate profile
PATCH  /api/v1/candidates/me/                    # Update candidate profile (title, bio, location, remote_ok)
GET    /api/v1/candidates/skills/                # List candidate skills
POST   /api/v1/candidates/skills/                # Add skill
PATCH  /api/v1/candidates/skills/{id}/           # Update skill
DELETE /api/v1/candidates/skills/{id}/           # Delete skill
GET    /api/v1/candidates/resumes/               # List resumes
POST   /api/v1/candidates/resumes/               # Upload new resume (returns presigned URL)
POST   /api/v1/candidates/resumes/{id}/process/  # Trigger PII stripping + embedding
GET    /api/v1/candidates/resumes/{id}/          # Get resume details
GET    /api/v1/candidates/certifications/        # List certifications
POST   /api/v1/candidates/certifications/        # Add certification
GET    /api/v1/candidates/journey/               # Get journey mapping data
POST   /api/v1/candidates/journey/regenerate/    # Trigger journey re-generation
GET    /api/v1/candidates/assessments/           # List available assessments
POST /api/v1/candidates/assessments/{id}/start/  # Start assessment attempt
POST /api/v1/candidates/assessments/{id}/answer/ # Submit answer
GET    /api/v1/candidates/applications/          # List applications (with match scores)
GET    /api/v1/candidates/applications/{id}/     # Get application details + AI rationale
```

#### Employer Endpoints
```http
GET    /api/v1/employers/me/                     # Get employer profile
PATCH  /api/v1/employers/me/                     # Update employer profile
GET    /api/v1/jobs/                             # List jobs
POST   /api/v1/jobs/                             # Create job
GET    /api/v1/jobs/{id}/                        # Get job details
PATCH  /api/v1/jobs/{id}/                        # Update job
POST   /api/v1/jobs/{id}/activate/               # Activate job posting
POST   /api/v1/jobs/{id}/screen/                 # Trigger AI screening (with cost estimate)
GET    /api/v1/jobs/{id}/applications/           # List applications for job (ranked); ?status=not_matched shows filter-excluded candidates (REQ-FR-029)
POST   /api/v1/jobs/{id}/interview-pack/         # Generate AI interview pack
GET    /api/v1/jobs/{id}/analytics/              # Get job analytics
GET    /api/v1/jobs/{id}/analytics/override-rate/ # Override rate by user + job, each linking to its reason (REQ-FR-035, REQ-FR-052)
POST   /api/v1/jobs/{id}/share/                  # Generate shareable link
```

#### Screening Integrity Endpoints (added 2026-10-03 — REQ-FR-051, REQ-FR-052, REQ-FR-029)

```http
GET    /api/v1/jobs/{id}/required-assessments/       # List assessments required before shortlist (REQ-FR-051)
POST   /api/v1/jobs/{id}/required-assessments/       # Attach one: {assessment_id, min_score?} (REQ-FR-051)
DELETE /api/v1/jobs/{id}/required-assessments/{req_id}/ # Detach; existing attempts and scores are untouched (REQ-FR-051)
POST   /api/v1/applications/{id}/shortlist/          # {reason?} — REQ-FR-052
POST   /api/v1/applications/{id}/reject/             # {reason?} — REQ-FR-052
POST   /api/v1/applications/{id}/review/             # Pull a not_matched candidate back into review (REQ-FR-029)
```

> **These must be action endpoints, not a bare `PATCH applications/{id}/`.** Two
> reasons, both load-bearing:
>
> 1. **The reason is required by the serializer.** REQ-FR-052 asks for a written reason
>    when a decision goes against the ranking. If the endpoint is a generic PATCH, the
>    reason is optional in the API and the rule is only enforced by a front-end form
>    that any API client can bypass.
> 2. **The assessment gate returns `409`.** REQ-FR-051 is only a constraint if the
>    server refuses a shortlist while `assessment_gate_status` is `pending` or `failed`.
>    A generic PATCH cannot refuse an action it does not know about.
>
> `POST .../reject/` writes an `AuditLogEntry` with `resource_type = 'ai_decision'`
> whenever the rejection is against the ranking, so it is retained with the
> application record rather than rotating at 90 days.

#### Assessment Endpoints
```http
GET    /api/v1/assessments/                      # List platform assessments (admin)
POST   /api/v1/assessments/                      # Create assessment (admin)
GET    /api/v1/assessments/{id}/                 # Get assessment details
PATCH  /api/v1/assessments/{id}/                 # Update assessment (admin)
```

#### Interview Endpoints
```http
GET    /api/v1/interviews/                       # List interviews (candidate + employer)
POST   /api/v1/interviews/                       # Schedule interview
GET    /api/v1/interviews/{id}/                  # Get interview details
POST   /api/v1/interviews/{id}/feedback/         # Submit feedback
GET    /api/v1/interviews/{id}/pack/             # Get interview pack
```

#### Notification & Communication Endpoints
```http
GET    /api/v1/notifications/                    # List notifications
POST   /api/v1/notifications/{id}/read/          # Mark notification as read
GET    /api/v1/messages/?application={id}/         # Get messages for application
POST   /api/v1/messages/                         # Send message
```

#### Administrative Endpoints
```http
GET    /api/v1/admin/dashboard/                  # Admin dashboard stats
GET    /api/v1/admin/users/                      # List all users
GET    /api/v1/admin/audit-log/                  # Query audit logs
GET    /api/v1/admin/ai-quota/                   # Check OpenRouter quota usage
POST   /api/v1/admin/broadcast/                  # Send system-wide announcement
```

### C.13 Testing Strategy (supplements §5.6, §10.2)

| Test Category | Tools | Target Coverage | What's Tested |
|---|---|---|---|
| **Unit tests** | pytest, pytest-django | 80%+ | Individual model methods, utility functions, PII stripping logic, AI provider abstraction |
| **Integration tests** | pytest, factory-boy | N/A (all integration paths) | API endpoints, Celery task execution, pgvector queries, email sending |
| **Security tests** | bandit, pip-audit, OWASP ZAP | Zero critical/high vulnerabilities | SQL injection, XSS, CSRF, auth bypass, dependency vulnerabilities |
| **Load tests** | Locust | 1000 concurrent users, < 2s response | API endpoints, job posting, application flow, AI screening |
| **Contract tests** | pytest | All AI provider implementations | OpenRouterProvider and OfflineFallbackProvider return consistent response format |
| **Accessibility tests** | axe-core, pa11y | WCAG 2.1 AA compliance | All HTML pages, form fields, keyboard navigation |
| **i18n tests** | pytest-django i18n | All strings wrapped in gettext | String extraction, translation coverage |

**Settings module hierarchy** (`config/settings/`):

| Module | Purpose |
|---|---|
| `base.py` | Shared settings — installed apps, middleware, security, DRF/Celery config |
| `local.py` | Development (`DEBUG=True`, SQLite fallback if Postgres unavailable) |
| `test.py` | Testing (in-memory SQLite, fast unit tests) |
| `ci.py` | CI (in-memory SQLite for unit tests, Postgres for integration tests) |
| `production.py` | Production (`DEBUG=False`, Sentry, HTTPS enforcement) |

**Test environment:**
- `.github/workflows/ci-cd.yml` — runs `pytest tests/ --cov=matchminds --cov-fail-under=80` with `DJANGO_SETTINGS_MODULE=config.settings.ci`
- Local: `pytest tests/ -v --ds=config.settings.test`

### C.14 Complete Freemium Pricing Tiers (supplements §1, §9 Phase 5)

**Candidate Tiers:**

| Tier | Price | Features | Limits |
|---|---|---|---|
| **Free** | $0/mo | Basic profile, resume upload, apply to jobs, basic match scores, interview coaching (5 sessions/mo), journey mapping (basic) | 5 applications/day, 5 AI interactions/day |
| **Essential** | $5/mo | All Free features + unlimited applications, 20 AI coaching sessions/mo, advanced journey mapping (skill evolution charts), priority in employer search | 50 AI interactions/day |
| **Professional** | $20/mo | All Essential + unlimited AI coaching, career story generation per application, skill assessments (10/mo), interview pack builder, export journey as PDF | 200 AI interactions/day |
| **Premium** | $50/mo | All Professional + personalized AI mentor, market salary insights, 50 skill assessments/mo, featured in employer search, custom resume templates | Unlimited |

**Employer Tiers:**

| Tier | Price | Features | Limits |
|---|---|---|---|
| **Starter** | $100/mo | 50 job postings, 500 AI screens/mo, basic analytics, email support | Up to 25 employees |
| **Growth** | $500/mo | 500 job postings, 5,000 AI screens/mo, advanced analytics, interview packs, priority support | Up to 250 employees |
| **Scale** | $1,500/mo | Unlimited jobs, 15,000 AI screens/mo, custom AI model selection, API access, dedicated support | Up to 1,000 employees |
| **Enterprise** | $5,000/mo | Unlimited everything, custom embedding domain, white-label career site, SSO (SAML/OIDC), on-premises option, 24/7 support | Unlimited |
| **Self-Hosted** | $0 (open source) / Custom support | Everything in Enterprise, deployed on your infrastructure | Requires ops team |

**Overage pricing:** $0.0001 per additional AI call beyond quota (negligible — OpenRouter free tier covers most usage).

### C.15 Feature Backlog Per Phase (supplements §9)

**Phase 1 Acceptance Criteria:**
- [ ] `docker-compose up -d` starts Postgres, Redis, Django, Celery
- [ ] User can register with email + password; verification email sent
- [ ] User can login; JWT tokens returned
- [ ] Candidate can upload resume via presigned URL
- [ ] Employer can create/edit/delete job postings
- [ ] Candidate can apply to a job
- [ ] Employer sees list of applications for their job
- [ ] All security headers present (HSTS, CSP, X-Frame-Options)
- [ ] Tests: 80%+ coverage on models, auth, job CRUD
- [ ] CI: lint, test, security scan all pass

**Phase 2 Acceptance Criteria:**
- [ ] PII stripping removes name/email/phone/location with 95%+ accuracy
- [ ] Resume embeddings generated via sentence-transformers
- [ ] pgvector cosine similarity returns ranked results in < 2 seconds for 100 candidates
- [ ] LLM rationale generated for top 10 candidates per job
- [ ] Deterministic keyword bias pass flags every seeded phrase in the versioned bias test set (set is a Phase 2 deliverable — do not claim a pass rate until it exists)
- [ ] Employer sees ranked candidates with scores + evidence-cited rationales
- [ ] Cost estimate shown before processing; $0.00 for free tier
- [ ] Audit entries logged for every AI scoring action

**Phase 3 Acceptance Criteria:**
- [ ] Candidate sees interactive career timeline from parsed resume
- [ ] Skill evolution chart renders with Chart.js
- [ ] Candidate can take a skill assessment and get auto-scored results
- [ ] AI interview coaching provides structured feedback on practice answers
- [ ] Dynamic storytelling generates a narrative optimized for a specific target job
- [ ] Candidate sees match scores for all applied jobs

**Phase 4 Acceptance Criteria:**
- [ ] MFA (TOTP) works for employer admin accounts
- [ ] Field-level encryption verified: encrypted PII not readable in DB
- [ ] File serving requires authentication (no direct S3 URL access)
- [ ] Rate limiting enforced: 1000 req/hr for candidates, 5000 req/hr for employers
- [ ] Sentry catches and reports errors (no PII in payloads)
- [ ] Prometheus metrics exposed at `/metrics/`
- [ ] GDPR: candidate can export all data as JSON
- [ ] GDPR: candidate can request account deletion (hard delete + audit log)
- [ ] CI/CD: automated deploy to staging on merge to main
- [ ] Load test: 100 concurrent applicants, < 5 sec response, < 1% error rate

**Phase 5 Acceptance Criteria:**
- [ ] Stripe billing: upgrade/downgrade plans, payment method management
- [ ] Bengali (and 3 more languages) UI fully translated
- [ ] PWA installable on mobile devices
- [ ] WebSocket connection for live interview coaching session
- [ ] WebSocket connection for real-time employer notifications

### C.16 Operational Procedures Addendum (supplements §8.5–§8.9 of `MATCH_MINDS_Project_Architecture_and_Requirements.md`)

This addendum consolidates the five operational-procedure sections that were added to the Architecture document as part of the SDLC gap-fill initiative (Phases 6–8: Deployment, Maintenance, Evaluation). The content below is the canonical reference; the Architecture document contains the same material for in-document navigation.

---

#### C.16.1 Rollback Procedure

**When to use:** A production or staging deployment causes errors, performance degradation, or data integrity issues, and the issue cannot be resolved by a targeted hot-patch within 5 minutes.

**Rollback types:**

| Type | Trigger | Scope | Target time |
|---|---|---|---|
| **Staging rollback** | Manual (`workflow_dispatch`) or failed staging deploy | Staging environment only | < 5 min |
| **Production rollback** | Manual (`workflow_dispatch`) only; never auto-triggered | Production environment | < 5 min |
| **Database rollback** | Data migration failed or corrupted data detected | DB schema state | < 10 min (uses `django-pg-zero` / WAL-G) |

**Rollback steps (production):**
1. **Decide** — Incident Commander declares a rollback; on-call engineer acknowledges in #incidents Slack.
2. **Trigger** — Navigate to GitHub Actions → CI/CD Pipeline → "Run workflow" → select `rollback-production` job.
3. **Wait** — The job reads `.version-tag-prod` to identify the previous version tag, retags the previous `matchminds/app:vX.Y.Z` image as `:latest`, and redeploys via `docker-compose up -d --wait`.
4. **Verify** — `curl -f https://app.matchminds.com/health/` must return 200. Check Sentry for new error spikes.
5. **Communicate** — Post update in #incidents with rollback time and version. Notify product and support leads.
6. **Investigate** — Schedule post-mortem within 48 hours (see post-mortem template below).

> **Image retention:** Docker images are retained for 30 days on the registry. Version tags are never deleted.

**Database rollback (PostgreSQL):**
- If a migration caused data corruption, use `django-pg-zero backup` to restore from the latest pre-migration snapshot.
- Command: `pg_restore --verbose --clean --no-acl --no-owner -h $DB_HOST -U $DB_USER -d $DB_NAME /backup/pre_migration_$(date -d "1 hour ago" +%Y%m%d_%H%M%S).sql`
- After restore, verify data integrity by spot-checking key tables (users, jobs, applications).
- Update `django_migrations` table to record the rolled-back migration state.

---

#### C.16.2 Maintenance & Patch Management Schedule

**Daily (automated, via cron on bastion host):**
- [ ] Log rotation check (Django logs, Celery logs, Nginx logs)
- [ ] Disk space check on all service volumes (alert if > 80%)
- [ ] Sentry error rate check (alert if > 5% 5xx errors over 5 min)
- [ ] Celery queue depth check (alert if > 1000 pending tasks)
- [ ] Backup job status check (alert on failure)

**Weekly (automated, via cron/Celery Beat):**
- [ ] `pip-audit -r requirements.txt` — auto-create GitHub issue on new CVEs
- [ ] `safety check` scan for known vulnerable packages
- [ ] SSL/TLS certificate expiry check (alert if < 30 days)
- [ ] Database index bloat analysis and `REINDEX` if needed
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

---

#### C.16.3 Incident Response Plan

**Tier 1 — Critical (P1):** Security breach, data exfiltration, downtime > 15 min
- **Trigger:** Sentry alert with 10+ critical errors in 5 min, or security team notification
- **Response time:** < 15 minutes
- **Actions:**
  1. On-call engineer acknowledges PagerDuty alert
  2. Isolate affected service (scale down, block traffic via Nginx)
  3. Capture forensic data (DB snapshot, recent logs, Sentry event IDs)
  4. Notify security team and incident commander
  5. If PII exposed: trigger data breach notification workflow (GDPR 72-hour notification)
  6. After resolution: mandatory post-mortem within 48 hours
- **Communication:** `#incidents` Slack channel; updates every 30 min until resolved

**Tier 2 — High (P2):** Degraded performance, AI API failures, partial feature outage
- **Trigger:** Prometheus alert (error rate > 10%, latency > 2x SLA)
- **Response time:** < 1 hour
- **Actions:**
  1. Engineer acknowledges alert in PagerDuty
  2. Switch to fallback systems (offline spaCy + pgvector for AI failures)
  3. Check OpenRouter status page; if downtime, enable offline mode globally
  4. Scale Celery workers if queue backlog detected
  5. Post-resolution: document in incident log
- **Communication:** `#oncall` Slack channel

**Tier 3 — Medium (P3):** Minor bugs, low-impact degradations, non-critical alerts
- **Trigger:** Bug report from users, or low-severity monitoring alert
- **Response time:** Next business day
- **Actions:**
  1. Triage and assign to sprint backlog
  2. Fix and deploy in next release cycle
- **Communication:** GitHub Issues tracker

**Post-Mortem Template:**
```markdown
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
  - HH:MM - Detection
  - HH:MM - Acknowledgment
  - HH:MM - Mitigation started
  - HH:MM - Service restored
- **Action items:**
  1. [ ] (Owner, Due Date) -
  2. [ ] (Owner, Due Date) -
  3. [ ] (Owner, Due Date) -
```

---

#### C.16.4 Post-Deployment Evaluation & Retrospective Process

**Phase 1: Release Verification (within 1 hour of deploy)**
- [ ] Health endpoint returns 200 (`curl -f https://app.matchminds.com/health/`)
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
| Deployment frequency | Weekly |  |  |  |
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

---

#### C.16.5 Versioning & Release Strategy

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
- Tags pushed to GitHub trigger Docker image tagging: `matchminds/app:v{MAJOR}.{MINOR}.{PATCH}`
- The `latest` tag always points to the most recent stable release on `main`

**Pre-release process:**
1. Release branch cut 2 days before scheduled release
2. QA signs off on staging environment
3. Canary deployment to production (1% traffic for 30 minutes)
4. If health checks pass, full rollout (100% traffic)
5. If health checks fail, automatic rollback to previous version
6. Post-release: monitor for 2 hours, then mark release as stable

**Release checklist (pre-deployment):**
- [ ] All CI checks pass (lint, test, security scan, coverage >= 80%)
- [ ] OpenAPI schema regenerated and reviewed
- [ ] Migration scripts written and tested (if applicable)
- [ ] Release notes drafted (user-facing changes, breaking changes)
- [ ] Rollback plan confirmed (previous image available, rollback job tested)
- [ ] Canary monitor configured (Prometheus alert for error rate spike)
- [ ] On-call engineer assigned for post-deploy monitoring

> **Note:** Rollback target time: < 5 minutes. Previous Docker images are retained for 30 days.

---

*End of document. This supersedes the original MATCH MINDS PDF proposal.*
