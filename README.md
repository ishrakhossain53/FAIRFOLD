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
> Because the host will change, keep `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, the bKash/SSLCommerz
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
| [FAIRFOLD_Project_Architecture_and_Requirements.md](FAIRFOLD_Project_Architecture_and_Requirements.md) | **Canonical** | System architecture, 63 functional & 50 non-functional requirements, 32-table database schema, CI/CD, operations, risk register |
| [prd.md](prd.md) | **Canonical** | Product requirements — objectives, success metrics, FRs with phases, AI requirements, data model, API surface, pricing, release criteria, open questions |
| [FAIRFOLD_Feasibility_and_Design.md](FAIRFOLD_Feasibility_and_Design.md) | Supplement | Feasibility study (technical, economic, operational, schedule, legal), user stories, UML diagrams, Gantt, data dictionary, accessibility |
| [design.md](design.md) | Supplement | UI design specification — colour tokens & 16 verified contrast ratios, typography, 7.13–7.21 product components, 78 page specs, **64 wireframes covering all 78 pages**, frontend build tooling, implementation notes |
| [HISTORY.md](HISTORY.md) | Log | What has been done on this repo and what is still outstanding |
| [`validation/`](validation/) | Instrument | Consent form, interview guide, survey and results log for the §1.3.4 user validation — **kit prepared 2026-10-13, study not yet run** |

**Start here:** `prd.md` if you want the product, `FAIRFOLD_Project_Architecture_and_Requirements.md` if you want to build it, `HISTORY.md` if you want to know where things stand.

## What is FairFold?

FairFold is an AI-powered recruitment platform that makes screening **explainable and
auditable** — by employers *and* candidates:

- **Strips identity before any AI call** — names, photos, emails, locations and phone
  numbers never reach a model provider
- **Gives candidates control** over their professional narrative via AI-Powered Journey Mapping
- **Enables explainable AI** - candidates and recruiters see why matches were scored
- **Runs on free-tier AI** (OpenRouter's free models)

## Quick Start — local setup from a fresh clone

Everything the application needs runs in containers: PostgreSQL 17 + pgvector, Redis,
ClamAV, Django, the Celery worker and Celery beat. The six steps below are the whole of
it.

### Prerequisites

- **Docker Engine 24+ with the Compose v2 plugin** — check with `docker compose version`
- **Git**
- **Python 3.12+** — needed only to generate the secret keys (step 2) and to run the test
  suite on the host. Node 20+ is needed only if you rebuild the frontend assets by hand
  (see [Frontend assets](#frontend-assets)).

You do **not** need PostgreSQL, Redis or ClamAV installed on the host. Not installing
them locally is what `docker-compose.yml` exists to avoid.

### 1. Clone the repository

```bash
git clone https://github.com/ishrakhossain53/FAIRFOLD.git
cd FAIRFOLD
```

### 2. Create `.env` and generate the two secrets

```bash
cp .env.example .env
python3 scripts/generate_secret_key.py --write-env
```

`--write-env` replaces the `change-me…` placeholders in `.env` with a fresh 512-bit
`DJANGO_SECRET_KEY` and a Fernet-format `ENCRYPTION_KEY`. Both are read on every boot and
the application refuses to start with either one missing, so this step is not optional.

- `.env` is gitignored; `.env.example` is the committed template. Never put a real secret
  in `.env.example`.
- No Python on the host? Run the same script in a throwaway container. `--user` keeps the
  written `.env` owned by you rather than by root:
  ```bash
  docker run --rm --user "$(id -u):$(id -g)" -v "$PWD:/w" -w /w python:3.12-slim \
    python scripts/generate_secret_key.py --write-env
  ```
- **Optional — AI features.** Set `OPENROUTER_API_KEY` in `.env` to use real models. Left
  empty, the app falls back to `OfflineFallbackProvider`, which returns deterministic
  non-AI responses, so every page still renders.
- **Optional — error tracking.** `SENTRY_DSN` may stay empty locally. Only
  `config.settings.production` requires it.

### 3. Start the stack

```bash
docker compose up -d --wait
```

This builds the image and starts `postgres`, `redis`, `minio`, `clamav`, `django`, `celery`
and `celery-beat`. On **every** start the `django` container:

1. applies migrations (`manage.py migrate`),
2. loads reference data (`manage.py seed` — role groups, skills, countries, industries,
   score bands; it warns that the bands are **uncalibrated**, per `design.md` §3.4),
3. creates the MinIO bucket and its CORS policy (`manage.py ensure_storage`), then
4. collects static files (`manage.py collectstatic`), and only then
5. starts gunicorn on `0.0.0.0:8000`.

`--wait` returns once every health check passes, so a completed command means the stack is
ready to use. The first run takes a few minutes: pip installs PyTorch (CPU wheels), spaCy
and the rest, and ClamAV downloads its signature database on first boot.

You never run `migrate`, `seed` or `ensure_storage` by hand to get started — the container
entrypoint does all three. They are re-run safely on every restart (all are idempotent).

### 4. Verify it is up

```bash
docker compose ps                     # every service Up, the health-checked ones healthy
curl -s localhost:8000/health/ready/  # {"status": "ok", "checks": {"database": "ok", "cache": "ok"}}
docker compose exec django python manage.py check_storage   # write, read, delete a probe object
```

The last command is the one that proves object storage works: a healthy MinIO container
does not prove Django is pointed at the right bucket with the right credentials.

Then open **http://localhost:8000/**.

| URL | What it is |
|---|---|
| http://localhost:8000/ | Landing page |
| http://localhost:8000/django-admin/ | Django admin (needs step 5) |
| http://localhost:8000/api/v1/ | API index |
| http://localhost:8000/api/docs/ | OpenAPI UI (`DEBUG` only) |
| http://localhost:8000/api/schema/ | OpenAPI schema |
| http://localhost:8000/health/ | Liveness probe |
| http://localhost:8000/health/ready/ | Readiness — reports database and cache |

### 5. Create an admin user (optional)

There is no login UI yet, so `createsuperuser` is how you reach the admin.

```bash
docker compose exec django python manage.py createsuperuser
```

### 6. Day-to-day commands

```bash
docker compose logs -f django      # follow the application log
docker compose logs -f celery      # follow the worker
docker compose ps                  # what is running
docker compose restart django      # restart one service
docker compose down                # stop the stack, KEEP the database volume
docker compose down -v             # stop and DELETE the database (a clean slate)
docker compose up -d --build       # rebuild the image after a code change
```

> **Source changes need a rebuild.** The application code is copied into the image, not
> bind-mounted, so editing a `.py` or `.html` file changes nothing until
> `docker compose up -d --build`. Note that `down -v` deletes resume files and the
> collected static files too, not just the database.

### Troubleshooting

- **`error while interpolating … required variable … is missing a value`** — `.env` is
  absent or incomplete. Run `cp .env.example .env` first; `DB_PASSWORD`,
  `DJANGO_SECRET_KEY`, `ENCRYPTION_KEY`, `EMAIL_BACKEND_URL`, `DEFAULT_FROM_EMAIL`,
  `MINIO_ROOT_USER` and `MINIO_ROOT_PASSWORD` must each have a value. An `.env` written
  before batch 1.17 has no `MINIO_*` lines; copy them from `.env.example`.
- **`minio` fails to pull with `401 Unauthorized`** — MinIO no longer publishes anonymous
  images (`minio/minio` was removed from Docker Hub, `quay.io/minio/minio` requires a
  login). Run `docker login quay.io` once, or set `MINIO_IMAGE` to a registry this machine
  is already authenticated to. `django` will not start until MinIO is healthy, because it
  creates the bucket on boot.
- **`check_storage` fails with `S3 error InvalidAccessKeyId` / `SignatureDoesNotMatch`** —
  `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` in `.env` do not match the credentials the
  existing `minio_data` volume was initialised with. Either restore the old values or
  `docker compose down -v` to start the object store empty (that also deletes the database
  and uploaded files).
- **A port is already in use (8000, 5432, 6379, 9000, 9001, 3310)** — another stack, or a
  host PostgreSQL/Redis/MinIO, owns it. Change `DJANGO_PORT` / `POSTGRES_PORT` /
  `REDIS_PORT` / `MINIO_PORT` / `MINIO_CONSOLE_PORT` / `CLAMD_PORT` in `.env`, or stop the
  other process.
- **`django` is healthy but the browser cannot connect** — confirm the bind address:
  `docker compose logs django | grep "Listening at"` must report `0.0.0.0:8000`. If it
  reports `127.0.0.1:8000`, gunicorn lost its arguments and the published port is dead.
- **The page is unstyled, or HTMX does nothing** — static files were not collected or the
  vendored JS is missing:
  ```bash
  docker compose exec django python manage.py collectstatic --noinput
  curl -I localhost:8000/static/js/htmx.min.js
  ```
- **An upload is rejected because ClamAV is unreachable** — this is deliberate; the scan
  fails closed. Wait for `docker compose ps` to show `clamav` as healthy.
- **The pending page shows the verification link** — that is deliberate in this build: the link
  is always rendered (also for an address that is already verified) so onboarding can be finished
  without a mailbox; console email lands in the Celery worker's log. It is a pre-deployment
  convenience, **not** production behaviour: the page can be requested by anyone who types an
  address, so it must be re-gated before the app is reachable by other people.

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
static/js/              # htmx.min.js + chart.min.js (vendored by `npm run build`, not committed)
tests/
├── conftest.py           # Django setup; degrades gracefully when Django is absent
└── bias/                 # versioned bias test set — v1.0.0 (76) + v1.0.1 (103 cases); spec in Arch Doc §7.4

docker-compose.yml
Dockerfile
package.json            # Tailwind 3.4 · HTMX 1.9 · Chart.js 4.4 (build-time only)
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
- `GET /api/v1/auth/me/` - Get current user (email, names, role names)
- `PUT /api/v1/auth/me/` - Update the current user's first and last name

### Jobs
- `GET /api/v1/jobs/` - List jobs
- `POST /api/v1/jobs/` - Create job
- `POST /api/v1/jobs/{id}/screen/` - Screen applications

### Candidates
- `GET /api/v1/candidates/me/` - Get the candidate's profile (404 before onboarding)
- `PATCH /api/v1/candidates/me/` - Create or update title, bio, location, remote_ok

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

### Running tests

Tests do **not** run inside the runtime image — `pytest` is a development dependency and
is deliberately not installed there. Create a virtualenv on the host and point it at the
containers from step 3, which publish their ports.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt -r requirements-dev.txt

# PostgreSQL, Redis and ClamAV come from `docker compose up -d`.
export DJANGO_SETTINGS_MODULE=config.settings.ci
export DJANGO_SECRET_KEY=test-only-not-a-real-key
export ENCRYPTION_KEY=test-only-fernet-placeholder-0000000000=
export DB_PASSWORD=devpassword
export DB_HOST=127.0.0.1
export REDIS_URL=redis://127.0.0.1:6379/0
export CELERY_BROKER_URL=redis://127.0.0.1:6379/0
export CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/1
export CLAMD_HOST=127.0.0.1

.venv/bin/pytest tests/ -v
```

> **Do not `source .env` for this.** `.env` sets `DEBUG=True`, and
> `tests/core/test_production_settings.py` asserts that `config.settings.production`
> refuses to load with `DEBUG` on — so a sourced `.env` fails those tests for a reason
> that has nothing to do with the code.

The bias pass needs no database, no Django and no settings module:

```bash
.venv/bin/pytest tests/bias/ -v
```

### Lint, types, security and docs checks (what CI runs)

```bash
.venv/bin/flake8 config/ core/ accounts/ candidates/ employers/ matching/ \
  assessments/ interviews/ notifications/ api/ journey/ ai/ \
  --max-line-length=120 --extend-exclude='*/migrations/*'
.venv/bin/black --check .
.venv/bin/isort --check-only .
.venv/bin/mypy config/ core/ accounts/ candidates/ employers/ matching/ ai/ \
  --ignore-missing-imports
.venv/bin/bandit -r . -c bandit.yaml -s B104,B105,B106,B107,B108,B311,B403

.venv/bin/python scripts/verify_docs.py       # counts, ids, links, line counts, wireframes
.venv/bin/python scripts/verify_bias_set.py   # bias fixture consistency
```

### Frontend assets

`static/css/tailwind.css` and `static/js/{htmx,chart}.min.js` are **generated, not
committed** (`.gitignore` keeps them out). The Docker image builds them in its `node`
stage, so a container build needs nothing extra. Build them on the host only if you want
the stylesheet without rebuilding the image:

```bash
npm ci                 # or `npm install` if package-lock.json is missing
npm run build          # vendors htmx + Chart.js into static/js/, then compiles Tailwind
npm run watch          # Tailwind only, in watch mode
npm run check-budget   # fails if tailwind.css exceeds the 30 KB gzipped budget
```

`npm run build` is two steps: `npm run vendor` copies HTMX and Chart.js out of
`node_modules` into `static/js/` (they are served from our own origin — the CSP allows no
third-party script host), then `npm run build:css` compiles Tailwind. Running only
`build:css` leaves the pages unstyled-by-JS: htmx.min.js 404s and every `hx-*` element is
inert.

### Migrations and Django shell

```bash
docker compose exec django python manage.py makemigrations
docker compose exec django python manage.py migrate
docker compose exec django python manage.py shell
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

