# Phase 1 closeout report

**Batch:** 1.46 (audit). **Date:** 2026-10-30. **Source:** Arch Doc §10, Phase 1
acceptance bullets; HISTORY.md through batch 1.45.

**Verdict: Phase 1 is not closed.** Seven of the ten acceptance bullets pass with
command evidence. Three fail: the Compose stack does not start Flower, no real
transactional email is sent in production, and CI is red. The three failures are
tracked as new batches 1.47-1.49 at the end of this report.

Nothing in this batch changed product code, schema, endpoints or requirements.

## Method

Each claim below is backed by a command run in this environment on 2026-10-30,
with `DJANGO_SETTINGS_MODULE=config.settings.ci`, `DEBUG` unset and PostgreSQL 17
from Docker Compose. No bullet is marked pass on documentation alone.

## Acceptance walkthrough

| # | Phase 1 acceptance bullet (Arch Doc §10) | Result |
|---|---|---|
| 1 | `docker-compose up -d` starts PostgreSQL, Redis, Django, Celery, Flower | **FAIL** — no Flower service |
| 2 | User can register; verification email sent (Resend API) | **FAIL** — production sends through the console backend |
| 3 | User can login; JWT access + refresh tokens returned | PASS |
| 4 | Candidate can upload a resume via presigned S3 URL (type validation) | PASS (browser gesture not automated) |
| 5 | Employer can create/edit/delete job postings (all fields validated) | PASS |
| 6 | Candidate can apply; unique constraint prevents duplicates | PASS |
| 7 | Employer sees the list of applications for their job | PASS |
| 8 | All security headers present (HSTS, CSP, X-Frame-Options, nosniff) | PASS |
| 9 | Tests: 80%+ coverage on models, auth, job CRUD | PASS |
| 10 | CI: lint passes (black, isort, flake8), security scan passes (bandit, pip-audit) | **FAIL** — black, pip-audit and the deploy check fail |

### 1. Compose stack — FAIL

`docker compose config --services` returns:

```
clamav
minio
postgres
redis
django
celery
celery-beat
```

There is no `flower` service. `docker compose ps` shows every listed service
`Up`, with `postgres`, `redis`, `minio`, `clamav`, `django` healthy;
`curl localhost:8000/health/ready/` returns
`{"status": "ok", "checks": {"database": "ok", "cache": "ok"}}`, and `/jobs/`
returns 200. PostgreSQL, Redis, Django and Celery are therefore met; Flower is
not. The Arch Doc §6.1 note records that the built file has no Flower service,
but the §10 bullet still names it, so the acceptance line is unmet. Proposed
batch 1.49.

### 2. Registration and verification email — FAIL

The registration and verification behaviour is implemented and tested:
`tests/accounts/test_registration.py`, `test_email_verification.py`,
`test_registration_ui.py` and `test_auth_tokens_api.py` pass, including
`test_sends_one_email_to_the_account` and the cooldown/outbox cases. The 1.45
end-to-end test also registers, verifies and logs in both users.

What fails is the provider. In `config.settings.production`:

```
EMAIL_BACKEND = django.core.mail.backends.console.EmailBackend
ANYMAIL = {'BASE_URL': 'https://placeholder@api.resend.com'}
```

`production.py` sets `ANYMAIL` and `EMAIL_BACKEND_URL` but never sets
`EMAIL_BACKEND` to the anymail backend, so the base console backend wins and
every message is discarded. No Resend API call can occur in production. This is
a functional Phase 1 failure and proposed batch 1.48.

### 3. Login and JWT — PASS

`tests/accounts/test_auth_tokens_api.py` passes: the token pair is returned,
access lives 15 minutes, refresh rotates and blacklists, logout revokes, lockout
returns 423 with a countdown, and an unverified address is refused after the
correct password. The template login shares `authenticate_with_lockout`
(`tests/accounts/test_login_ui.py`). Included in the 311-test targeted run below
and the full suite.

### 4. Resume upload via presigned URL — PASS (backend and storage; browser gesture manual)

Evidence:

- `tests/candidates/test_resume_upload_api.py` (29 tests) — candidate-only,
  MIME allow-list, size limit, server-generated key, `pending` row, presigned
  PUT, expiry from settings.
- `tests/candidates/test_resume_completion_api.py` + `test_resume_scan.py` (33
  tests, including the real-clamd cases while the Compose ClamAV is up) —
  real size and libmagic type checked, failure deletes the bytes.
- `tests/candidates/test_resume_list_detail_api.py` (37) and
  `tests/candidates/test_resume_ui.py` (32).
- `docker compose exec django python manage.py check_storage` ->
  `storage round-trip verified: backend=storages.backends.s3.S3Storage
  bucket=fairfold-media ... bytes=35`.
- `pytest tests/core/test_storage.py` against the live MinIO with `AWS_*` set ->
  **20 passed, 1 skipped** (the skip is the "no bucket configured" case).
- `pytest tests/core/test_presign_endpoint.py` -> **8 passed**.

`file_key` is the only storage value on the row; no object bytes or signed URL
are persisted. Caveat: the browser PUT (CORS preflight, XHR progress) is not
automated; it is the remaining `partial` item on REQ-FR-010.

### 5. Employer job CRUD — PASS

`tests/employers/test_job_create_api.py`, `test_job_edit_delete_api.py` and
`test_job_lifecycle_api.py` hold 58 tests covering field validation, the
`status`/`employer` write refusal, draft-only editing, delete, and the
draft/paused/active/closed matrix with an audit entry per change. Page #36 posts
the same whitelist (`JobForm`), and the 1.45 test creates and activates a job
through it. The full suite passes.

### 6. Apply and duplicate prevention — PASS

`tests/matching/test_apply_api.py` and `test_application_decision_api.py` hold
48 tests; `tests/matching/test_job_application_models.py` pins
`UNIQUE(job, candidate)` and the duplicate refusal. The 1.45 test applies over
HTTP and asserts exactly one row; a repeat apply is information, not a second
row.

### 7. Employer sees applications — PASS

`tests/employers/test_job_applications_api.py` (47 reported at acceptance),
`test_employer_applications_ui.py` (41) and `test_application_rationale_ui.py`
(12) pass. The 1.45 test proves the inbox renders the per-employer alias and
none of the candidate name, email or internal user id, and that a candidate is
403 on the employer review and shortlist routes.

### 8. Security headers — PASS

`tests/core/test_security_headers.py` asserts, on four paths including an
unauthenticated 401, under production-like settings: HSTS
`max-age=31536000; includeSubDomains; preload`, `X-Frame-Options: DENY`,
`X-Content-Type-Options: nosniff`, `Referrer-Policy: same-origin`, and a
self-hosted CSP with no CDN or OpenRouter host. On the running development
container (plain HTTP, `config.settings.local`) the live response carries CSP,
X-Frame-Options, nosniff and Referrer-Policy; HSTS is correctly absent over
HTTP and is covered by the secure-request test.

### 9. Coverage — PASS

Two measurements, because the CI command and the configured scope differ:

| Command | Total | Result |
|---|---|---|
| `pytest tests/ -q --cov --cov-report=term` (configured scope) | **95.49%** | gate reached |
| `pytest tests/ -q --cov=. --cov-fail-under=80` (CI's command) | **98.37%** | gate reached |

Configured-scope module detail (from the report):

| Module | Coverage |
|---|---|
| `accounts/models.py` | 99% |
| `accounts/services.py` | 96% |
| `accounts/views.py` | 97% |
| `employers/models.py` | 100% |
| `employers/api_views.py` | 100% |
| `matching/models.py` | 99% |
| `matching/services.py` | 100% |
| `core/models.py` | 87% |
| `candidates/models.py` (measured separately) | 99% |
| `notifications/models.py` (measured separately) | 100% |

Measuring `candidates`, `notifications`, `api`, `assessments`, `interviews` and
`journey` together with `--cov-fail-under=0` gives **97%**. The Phase 1 models,
auth and job-CRUD bullet is therefore met with margin.

**Weakness found (not a failure):** `--cov=.` measures the test suite itself
(the report lists `tests/**/test_*.py` at 100%), so CI's number is inflated and
the explicit `[tool.coverage.run] source` scope is not what the gate enforces.
The configured scope still passes at 95.49%. Alignment is part of batch 1.47.

### 10. CI lint and security — FAIL

GitHub Actions run **#101** for commit `7517a10` (the current HEAD), branch
`1.40-1.43`, created 2026-10-30T08:57:05Z, concluded **failure**
(`https://github.com/ishrakhossain53/FAIRFOLD/actions/runs/41029893681`).
The job-level detail is not readable without an authenticated GitHub session
(see Limitations), so the CI steps were reproduced locally with the same pins:

| CI step | Local result |
|---|---|
| `flake8` (CI scope) | clean (exit 0) |
| `isort --check-only .` | clean (exit 0) |
| `black --check .` | **FAIL** — `scripts/verify_docs.py` would be reformatted |
| `mypy` (CI scope) | Success, 113 files |
| `bandit -r . -c bandit.yaml -s B104,...,B403` | **cannot run** on Python 3.14: `ERROR Unknown test found in profile: B105` |
| `pip-audit -r requirements.txt` | **FAIL** — 3 advisories, all in `djangorestframework 3.17.2`, fixed in 3.18.2: GHSA-33wh-fxxf-88vv, GHSA-3547-9m27-7rxg, GHSA-xw6w-gcfp-cf8m |
| `manage.py check --deploy --fail-level WARNING` (production settings) | **FAIL** — `drf_spectacular.W001` enum collision for fields named `status` |
| `scripts/verify_docs.py` / `verify_bias_set.py` | exit 0 |
| `pytest tests/` | 1598 passed, 4 skipped |

The black failure and the W001 warning are pre-existing (HISTORY.md records
both); the pip-audit advisories apply to the current `djangorestframework`
3.17.2 pin. The audit does not fix them. Proposed batch 1.47.

## Targeted regression run

```
pytest tests/accounts/test_registration.py tests/accounts/test_email_verification.py \
  tests/accounts/test_registration_ui.py tests/accounts/test_auth_tokens_api.py \
  tests/employers/test_job_create_api.py tests/employers/test_job_edit_delete_api.py \
  tests/employers/test_job_lifecycle_api.py tests/matching/test_apply_api.py \
  tests/matching/test_application_decision_api.py tests/core/test_security_headers.py \
  tests/core/test_phase1_end_to_end.py -q
-> 311 passed in 13.89s
```

Full suite: **1598 passed, 4 skipped** (67.30s; the four skips are
`tests/core/test_storage.py`'s S3 integration cases without `AWS_*`).
`manage.py check` -> no issues.

## Traceability changes made by this audit

- **REQ-FR-027 (Job Activation): `partial` -> `done`.** The row's missing item
  was candidate-side visibility, which batches 1.31/1.33 built and the 1.45
  end-to-end test demonstrates (activate, then find and apply as the candidate).
- **REQ-FR-045:** the "guard cannot exist until the Job model lands" sentence was
  stale; the guard exists and is tested. The only remaining acceptance gap is
  `company_name` encryption (decision D-5, scheduled as batch 4.3).
- **REQ-FR-054:** the missing list said detail, notifications and audit views.
  Detail (page #41) and notifications (batches 1.43/1.44) are alias-only and
  tested; exports, audit views and reveal-on-shortlist (batch 2.39) remain.
- **REQ-FR-010:** corrected the storage/presign test counts to today's run
  (20 passed / 1 skipped against MinIO; 8 presign tests) and kept `partial` for
  the browser gesture, production bucket decision and rate limiting.
- **REQ-FR-001:** added a deployment note that production still uses the console
  email backend; the requirement's behaviour is tested, the provider wiring is
  tracked as batch 1.48.

## Deferred work, as new batches

These are inserted after 1.46 and before Phase 2. They are Phase 1 acceptance
fixes, not new features.

| ID | Batch | Why it exists | Type |
|---|---|---|---|
| 1.47 | CI green: black, deploy check, dependency audit | The three reproducible red CI steps above; also align `--cov=.` with the configured coverage scope and record how bandit is run on Python 3.12 | backend+tests |
| 1.48 | Transactional email provider wiring | `EMAIL_BACKEND` must be an anymail backend in production; add a settings test and a manual send check. Phase 1 bullet 2. | backend+tests |
| 1.49 | Flower service in Compose | Phase 1 bullet 1 names Flower; the service does not exist. | ops |
| 1.50 | Candidate dashboard page #15 (X03) | REQ-FR-023's acceptance says "candidate sees updated status in dashboard"; only the tracker (#28) exists. | ui |
| 1.51 | REQ-FR-010 browser upload verification and production bucket decision | CORS preflight, XHR progress and drag-and-drop are manual today; the production bucket/credentials choice is open. Automating the browser gesture needs a tooling decision first. | audit |

Already scheduled, not new: `company_name` encryption (REQ-FR-045, D-5) is batch
4.3; upload rate limiting (REQ-FR-010) is batch 4.6; controlled identity reveal
(REQ-FR-054) is batch 2.39. The remaining job-creation items (AI-suggested
questions, `job_skills`, `screening_questions`, assessment requirements) are
Phase 2/3 work and stay on their existing batches.

## Limitations of this audit

- GitHub's jobs/logs endpoints return no data without an authenticated session,
  and the unauthenticated rate limit was nearly exhausted, so only the run-level
  conclusion (failure) and the locally reproduced steps are evidenced. The exact
  first failing CI step is not claimed.
- `bandit 1.7.10` cannot load its test profile on this machine's Python 3.14, so
  its CI result on Python 3.12 is unknown. It is not marked pass or fail.
- No Resend API key is available, so real provider delivery could not be tested;
  the backend misconfiguration is proven from settings instead.
- No browser automation is configured, so the resume upload gesture and the
  360px UI are verified by their server-rendered tests, not by a real browser.
- Counts are from this environment and include the uncommitted batch 1.45
  `tests/core/test_phase1_end_to_end.py`; the GitHub run #101 is for HEAD
  `7517a10`, which does not contain that file. CI on Python 3.12 may differ in
  warnings, not in outcomes.
