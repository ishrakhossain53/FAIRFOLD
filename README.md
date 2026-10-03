# FAIRFOLD — AI-Powered, Explainable Recruitment Platform

> **NOTE:** This is the development version. See [FAIRFOLD_Project_Architecture_and_Requirements.md](FAIRFOLD_Project_Architecture_and_Requirements.md) for detailed documentation.

> ### ✅ Named: FairFold (decided 2026-10-03)
> The working name "Match Minds" was abandoned — it was in commercial use by at least two
> other AI recruitment products and two unrelated software products, and it is descriptive
> enough of what every ATS does to be hard to trademark. **FairFold** was chosen from four
> screened candidates; no living commercial use of the string was found. The
> `MATCH_MINDS_*.md` files were renamed to `FAIRFOLD_*.md`. Reasoning:
> [`prd.md` §4.3](prd.md) and [Feasibility Doc §1.4.2](FAIRFOLD_Feasibility_and_Design.md).
>
> **✅ Domain owned** — a temporary domain first, moving to the primary at launch.
> **🟡 Still to do before any public launch:** commission a **formal trademark search** in
> Bangladesh and each target export market, and file the word mark in classes 42 and 35
> per market. A web search, a DNS lookup and a domain registration are **not** a
> trademark clearance. Tracked as **RSK-011** (Medium/Low).
>
> Because the host will change, keep `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, the Stripe
> webhook URL and the Sentry DSN in environment variables — the switch should be a config
> edit, not a debugging session — and do not build SEO or email reputation against the
> temporary host.

> ### ⚠️ The product does not claim to be bias-free — yet
> There is **no disparity measurement**, so "bias-free" was removed from every document on
> 2026-10-03. The subtitle is now *"AI-Powered, **Explainable** Recruitment Platform"*,
> which describes what the product does rather than what it achieves. FairFold makes every
> score carry cited evidence and every action write an audit entry — that is a guarantee
> about **process**. Whether it reduces biased **outcomes** is what `prd.md` §8.7 has to
> measure, and it may not be advertised before it has. Approved wording:
> [`prd.md` §4.2](prd.md).

## Documentation

| Document | Role | Covers |
|---|---|---|
| [FAIRFOLD_Complete_Project_Document.md](FAIRFOLD_Complete_Project_Document.md) | **Canonical** | Product vision, market & competitor analysis, AI strategy, security architecture, implementation roadmap |
| [FAIRFOLD_Project_Architecture_and_Requirements.md](FAIRFOLD_Project_Architecture_and_Requirements.md) | **Canonical** | System architecture, 52 functional & 50 non-functional requirements, database schema, CI/CD, operations, risk register |
| [prd.md](prd.md) | **Canonical** | Product requirements — objectives, success metrics, FRs with phases, AI requirements, data model, API surface, pricing, release criteria, open questions |
| [FAIRFOLD_Feasibility_and_Design.md](FAIRFOLD_Feasibility_and_Design.md) | Supplement | Feasibility study (technical, economic, operational, schedule, legal), user stories, UML diagrams, Gantt, data dictionary, accessibility |
| [design.md](design.md) | Supplement | UI design specification — colour tokens & 16 verified contrast ratios, typography, 19 generic + 12 product components, 62 page specs, **52 wireframes covering all 62 pages**, frontend build tooling, implementation notes |
| [HISTORY.md](HISTORY.md) | Log | What has been done on this repo and what is still outstanding |
| [`validation/`](validation/) | Instrument | Consent form, interview guide, survey and results log for the §1.3.4 user validation — **built, never run** |

**Start here:** `prd.md` if you want the product, `FAIRFOLD_Project_Architecture_and_Requirements.md` if you want to build it, `HISTORY.md` if you want to know where things stand.

## What is FairFold?

FairFold is an AI-powered recruitment platform that makes screening **explainable and
auditable** — by employers *and* candidates:

- **Strips identity before any AI call** — names, photos, emails, locations and phone
  numbers never reach a model provider
- **Gives candidates control** over their professional narrative via AI-Powered Journey Mapping
- **Enables explainable AI** - candidates and recruiters see why matches were scored
- **Runs on free-tier AI** (OpenRouter's free models)

## Quick Start

### Prerequisites

- Docker + Docker Compose
- Python 3.12+
- PostgreSQL 17+ with pgvector extension
- Redis 7+ (server) / Redis 5+ (Python client)

### Setup

1. **Clone and configure environment:**
   ```bash
   cp .env.example .env
   python scripts/generate_secret_key.py --write-env   # fills in the secret keys
   # Then edit .env with your own settings
   ```

   `.env.example` documents every variable (see Complete Project Document §C.7).
   The generator writes cryptographically strong `DJANGO_SECRET_KEY` and
   `ENCRYPTION_KEY` values so you never invent weak secrets by hand.

2. **Start the stack:**
   ```bash
   docker-compose up -d
   ```

3. **Initialize database:**
   ```bash
   docker exec -it fairfold-django python manage.py migrate
   docker exec -it fairfold-django python manage.py seed
   ```

   `seed` loads the reference data a fresh database needs before serving a request: the
   four Django role groups and the 68-skill taxonomy. It also validates the score bands,
   countries and industries in `core/reference.py` and **warns that the bands are
   uncalibrated** — `design.md` §3.4 calls them provisional pending a calibrated model, so
   do not present them as measured.

4. **Create superuser:**
   ```bash
   docker exec -it fairfold-django python manage.py createsuperuser
   ```

5. **Access the application:**
   - Django admin: http://localhost:8000/django-admin/
   - API: http://localhost:8000/api/v1/
   - Health check: http://localhost:8000/health/

## Project Structure

```
fairfold/
├── manage.py                # Django entrypoint; defaults to config.settings.local
├── config/                  # Django PROJECT package (not an app)
│   ├── settings/
│   │   ├── base.py          # Shared settings (security, apps, middleware, env helpers)
│   │   ├── local.py         # Development (DEBUG=True, PostgreSQL 17 + pgvector via Docker)
│   │   ├── ci.py            # CI — every test uses this. There is NO test.py; see below.
│   │   └── production.py    # Production (DEBUG=False, Sentry, HTTPS, asserts everything)
│   ├── urls.py              # mounts /api/v1/ and the app prefixes
│   ├── celery.py
│   └── wsgi.py
├── core/                    # middleware, logging, exceptions, pagination, reference data
│   ├── middleware.py        # RequestIDMiddleware — the correlation ID in every log line
│   ├── logging.py           # RequestIDFilter — without it every log record fails to format
│   ├── exceptions.py        # a 500 body never carries the exception text
│   ├── pagination.py        # page_size ceiling of 100
│   ├── reference.py         # score bands, countries, industries (constants, NOT tables)
│   ├── fixtures/            # groups.json (4 roles), skills.json (68 skills)
│   └── management/commands/seed.py
├── accounts/                # User model, auth, RBAC, profiles
├── candidates/              # Candidate dashboard, journey mapping, assessments
├── employers/               # Employer dashboard, job postings, screening
├── matching/                # AI matching engine, pgvector, ranking
├── assessments/             # Skill assessment creation, taking, scoring
├── interviews/              # Interview scheduling, AI-generated Q packs
├── notifications/           # Email, in-app notifications
├── api/                     # DRF API root, versioning
├── journey/                 # AI-Powered Professional Journey Mapping
└── ai/                      # provider abstraction + bias_pass.py / bias_audit.py

templates/              # base.html + errors/{403,404,500}.html
static/css/             # tokens.css (from design.md §3–§5), tailwind.src.css, tailwind.css (built)
tests/
├── conftest.py           # Django setup; degrades gracefully when Django is absent
└── bias/                 # versioned bias test set — v1.0.0 (76) + v1.0.1 (103 cases); spec in Arch Doc §7.4

docker-compose.yml
Dockerfile
package.json            # Tailwind 3.4 · HTMX 1.18 · Chart.js 4.4 (build-time only)
tailwind.config.js      # maps design tokens onto utility names
pyproject.toml          # black · isort · mypy · pytest config
bandit.yaml             # bandit skips, each with its reason
requirements.txt / requirements-dev.txt
.env.example        # template for every env var (never put secrets here)
.gitignore          # keeps .env out of git; .env.example stays tracked
scripts/
├── generate_secret_key.py   # generates DJANGO_SECRET_KEY + ENCRYPTION_KEY
├── verify_docs.py           # cross-document consistency check (also runs in CI)
└── verify_bias_set.py       # validates the bias test set's internal consistency (CI)
```

> **There is no `config/settings/test.py`, and that is deliberate.** SQLite has no pgvector, so
> a SQLite test module would let the embedding, ranking and screening tests pass on a database
> that cannot represent a vector — and fail in production. **Every test uses
> `config.settings.ci`** against real PostgreSQL. Set `DJANGO_SETTINGS_MODULE` in `.env`.

> **`ai/bias_pass.py` and `ai/bias_audit.py` need none of this.** The pass is dependency-free
> pure text matching, so `pytest tests/bias/` runs with or without Django, a database or a
> settings module — which is deliberate, because it is the highest-risk logic in the product
> and should not be gated on infrastructure being up.

## Build Order

**Start with these components (in order) — see [§9 Implementation Roadmap](FAIRFOLD_Complete_Project_Document.md#9-implementation-roadmap) in the Complete Project Document for phase details:**

1. **Development Environment** *(Complete Project Doc: §10.1, §10.2 | Architecture Doc: §6.1)*
   - `docker-compose.yml` — starts PostgreSQL, Redis, ClamAV, Django, Celery
   - `.env` configuration
   - `npm ci && npm run build` — compiles Tailwind to `static/css/tailwind.css` and
     vendors HTMX and Chart.js into `static/js/`. **Build-time only**: Node is not in the
     runtime image, so a container rebuild without this step ships the unstyled CDN
     fallback. See `design.md` §11.2.

2. **Authentication System** *(Complete Project Doc: §9 Phase 1 | Architecture Doc: §4.1 Functional Requirements)*
   - User model with role-based access
   - Registration and login endpoints
   - JWT token authentication

3. **Core Models** *(Complete Project Doc: §9 Phase 1, §8 | Architecture Doc: §5 Data Architecture)*
   - CandidateProfile, Resume, Job, Application models
   - Database migrations

4. **Resume Processing** *(Complete Project Doc: §9 Phase 2 | Architecture Doc: §3.4, §5.4)*
   - File upload via presigned URLs
   - PII stripping pipeline
   - Text extraction

5. **Job Posting Flow** *(Complete Project Doc: §9 Phase 1 | Architecture Doc: §4.1 Functional Requirements)*
   - Job creation forms
   - Application management

6. **AI Matching Engine** *(Complete Project Doc: §9 Phase 2, §6 AI Strategy, §6.5 pgvector | Architecture Doc: §3.4 Technology Stack, §5.1 schema + HNSW indexes)*
   - pgvector-based similarity matching
   - OpenRouter integration

7. **Security Hardening** *(Complete Project Doc: §9 Phase 4, §5 Security Architecture | Architecture Doc: §4.2 Non-Functional Requirements → Security, §8 Operations)*
   - Field-level encryption
   - Rate limiting
   - Audit logging

## API Endpoints

### Authentication
- `POST /api/v1/auth/register/` - Register new user
- `POST /api/v1/auth/login/` - Login, get JWT tokens
- `GET /api/v1/auth/me/` - Get current user

### Jobs
- `GET /api/v1/jobs/` - List jobs
- `POST /api/v1/jobs/` - Create job
- `POST /api/v1/jobs/{id}/screen/` - Screen applications

## Technology Choices

| Component | Choice | Why |
|-----------|--------|-----|
| Backend | Django 5.2+ LTS + DRF | Production-proven, batteries-included, current LTS |
| Frontend | Django Templates + HTMX | Faster MVP, single framework |
| Database | PostgreSQL 17 + pgvector | Semantic matching, JSON support |
| AI | OpenRouter free tier | $0 cost for developers |
| Background | Celery + Redis | Async processing |
| Deployment | Docker Compose | Simple, reproducible |

## Development

### Running Tests
```bash
# Local — needs PostgreSQL + pgvector (no SQLite fallback; see above)
pip install -r requirements.txt -r requirements-dev.txt
pytest tests/ -v

# The bias pass alone needs NO database and NO Django
pytest tests/bias/ -v

# Docker
docker exec fairfold-django pytest tests/ -v
```

### Verifying the documentation
```bash
python3 scripts/verify_docs.py       # counts, ids, links, line counts, wireframe coverage
python3 scripts/verify_bias_set.py   # every bias fixture version's internal consistency
```

### Running Migrations
```bash
docker exec fairfold-django python manage.py makemigrations
docker exec fairfold-django python manage.py migrate
```

### Opening Django Shell
```bash
docker exec -it fairfold-django python manage.py shell
```

## Production Deployment

1. Set `DJANGO_SETTINGS_MODULE=config.settings.production`
2. Configure SSL certificate
3. Set up a proper PostgreSQL instance with backups
4. Use S3-compatible storage for files
5. Enable Sentry for error tracking
6. Configure monitoring (Prometheus + Grafana)

## Key Architecture Decisions

1. **Free-tier AI:** Uses OpenRouter's free models to minimize costs
2. **PII Privacy:** Text is anonymized before any AI processing
3. **pgvector Matching:** Semantic similarity computed offline, no API costs
4. **Monolith First:** Single Django app; can split into services later
5. **HTMX Frontend:** Achieves SPA interactivity without complex React setup

## License

