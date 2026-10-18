# FairFold — baseline run

Batch 0.2. Read-only audit: no source file was edited. This file records the exact commands run and
their real output, so a reader can reproduce every result.

- **Date:** 2026-10-19
- **Branch:** `0.1-Reconcile-repo-state`
- **HEAD:** `c80db9b docs: reconcile repo state against HISTORY.md (batch 0.1)`
- **Working tree:** clean at the start and at the end (`git status --short` → empty).
- **Compose stack:** already up from a previous session; `docker compose up -d --wait` re-run and
  returned `EXIT=0`.

Every result below was produced by the command shown above it. Where output is long, an elided
summary is marked with `…`; nothing else is edited. **Every failure below is pre-existing** — this
batch changed no code.

---

## 1. Environment

| Item | Value |
|---|---|
| Host Python venv | `.venv/bin/python` → `/usr/bin/python`, **Python 3.14.8** |
| Django | 5.2.18 |
| pytest / flake8 / black / isort / mypy / bandit / pip-audit | 8.3.3 / 7.1.1 / 24.10.0 / 5.x / 1.13.0 / **1.7.10** / 2.9.0 |
| Docker Engine / Compose | 29.9.0 / v5.6.0 |
| Containers | `postgres` (pgvector/pgvector:pg17), `redis:7-alpine`, `clamav/clamav:1.4`, `django`, `celery`, `celery-beat` all `Up`, health-checked ones `healthy` |
| CI target Python | **3.12** (`.github/workflows/ci-cd.yml:95`) — differs from this host's 3.14; see §Pre-existing failures |

Two environment facts that matter for reproduction:

1. **The shell exports `DEBUG=True` and `DJANGO_SETTINGS_MODULE=config.settings.local`.** This is the
   footgun documented in `README.md` ("Do not `source .env` …") and `CLAUDE.md`. All test/Django
   commands below were run after `unset DEBUG` and with `DJANGO_SETTINGS_MODULE=config.settings.ci`.
2. **The published host port `8000` is not bound in this environment.** `docker compose ps` and
   `docker compose port django 8000` both report `0.0.0.0:8000`, but `ss -ltn` shows listeners for
   `3310`, `5432`, `6379` and **not `8000`**; `curl 127.0.0.1:8000` is refused. The app is reached
   instead through the container (see §6). This is an artifact of this sandbox's Docker setup, not a
   property of the repository.

### Commands run (copy-pasteable)

```bash
# 1. Stack (README Quick Start step 3)
docker compose up -d --wait

# 2. Host-side test env (README "Running tests"), DEBUG deliberately unset
unset DEBUG
export DJANGO_SETTINGS_MODULE=config.settings.ci
export DJANGO_SECRET_KEY=test-only-not-a-real-key
export ENCRYPTION_KEY=test-only-fernet-placeholder-0000000000=
export DB_PASSWORD=<from .env>
export DB_HOST=127.0.0.1
export REDIS_URL=redis://127.0.0.1:6379/0
export CELERY_BROKER_URL=redis://127.0.0.1:6379/0
export CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/1
export CLAMD_HOST=127.0.0.1

# 3. Django / migrations / seed
.venv/bin/python manage.py check
.venv/bin/python manage.py makemigrations --check --dry-run
.venv/bin/python manage.py migrate --noinput     # against an empty DB (see §4)
.venv/bin/python manage.py seed

# 4. Tests
.venv/bin/pytest tests/ -v

# 5. Lint / types / security / deps
.venv/bin/flake8 config/ core/ accounts/ candidates/ employers/ matching/ assessments/ \
  interviews/ notifications/ api/ journey/ ai/ --max-line-length=120 --extend-exclude='*/migrations/*'
.venv/bin/black --check .
.venv/bin/isort --check-only .
.venv/bin/mypy config/ core/ accounts/ candidates/ employers/ matching/ ai/ --ignore-missing-imports
.venv/bin/bandit -r . -c bandit.yaml -s B104,B105,B106,B107,B108,B311,B403
.venv/bin/pip-audit -r requirements.txt

# 6. Documentation / fixtures
.venv/bin/python scripts/verify_docs.py
.venv/bin/python scripts/verify_bias_set.py
```

---

## 2. Results summary

| # | Check | Exit | Result |
|---|---|---|---|
| 1 | `docker compose up -d --wait` | 0 | all 6 services running, health-checked ones healthy |
| 2 | `manage.py check` | 0 | `System check identified no issues (0 silenced).` |
| 3 | `manage.py makemigrations --check --dry-run` | 0 | `No changes detected` |
| 4 | `manage.py migrate` (empty DB) | 0 | all migrations `OK` |
| 5 | `manage.py seed` | 0 | `Seed complete: 2 fixtures, 12 countries, 15 industries, 4 score bands.` |
| 6 | `pytest tests/ -v` | 0 | **115 passed in 2.86s** |
| 7 | `flake8 …` | 0 | no output (clean) |
| 8 | `black --check .` | **1** | **1 file would be reformatted** — `scripts/verify_docs.py` |
| 9 | `isort --check-only .` | 0 | `Skipped 9 files` |
| 10 | `mypy …` | 0 | `Success: no issues found in 69 source files` |
| 11 | `bandit …` | **2** | **cannot run on this host — Python 3.14 incompatible** (`Unknown test found in profile: B107`) |
| 12 | `pip-audit -r requirements.txt` | 0 | `No known vulnerabilities found` (2 deps skipped, see below) |
| 13 | `scripts/verify_docs.py` | 0 | `All checks passed.` (14 notes for a human) |
| 14 | `scripts/verify_bias_set.py` | 0 | `All 2 version(s) internally consistent.` |

Two failures (rows 8 and 11). Both are **pre-existing** and explained in §5.

---

## 3. Django checks

```
$ .venv/bin/python manage.py check
System check identified no issues (0 silenced).
EXIT=0
```

```
$ .venv/bin/python manage.py makemigrations --check --dry-run
/home/…/django/core/management/commands/makemigrations.py:161: RuntimeWarning: Got an error checking
a consistent migration history performed for database connection 'default': connection to server at
"127.0.0.1", port 5432 failed: FATAL:  database "fairfold_test" does not exist

  warnings.warn(
No changes detected
EXIT=0
```

The `RuntimeWarning` is benign: `POSTGRES_DB=fairfold_test` is the *test* database pytest creates;
`makemigrations --check` only needs the models, and it reports **no drift**. (`manage.py check` above
ran with the same warning suppressed from view because it does not open a DB connection.)

---

## 4. Migrate and seed on an empty database

A throwaway database `fairfold_baseline` was created to satisfy "migrate on an empty DB" without
touching the development database, then dropped afterwards.

```
$ docker compose exec -T postgres psql -U fairfold -d postgres -c "CREATE DATABASE fairfold_baseline;"
CREATE DATABASE

$ POSTGRES_DB=fairfold_baseline .venv/bin/python manage.py migrate --noinput
Operations to perform:
  Apply all migrations: accounts, admin, auth, contenttypes, core, django_celery_beat, sessions, sites
Running migrations:
  Applying contenttypes.0001_initial... OK
  …
  Applying sites.0002_alter_domain_unique... OK
EXIT=0
```

Every listed migration applied `OK`; there were no errors or skipped migrations.

```
$ POSTGRES_DB=fairfold_baseline .venv/bin/python manage.py seed
  loaded groups.json
  loaded skills.json
  score bands are PROVISIONAL and uncalibrated (weak_match, partial_match, good_match, strong_match). design.md §3.4 marks them as needing a calibrated model; do not present them as measured.
Seed complete: 2 fixtures, 12 countries, 15 industries, 4 score bands.
EXIT=0
```

Resulting schema: **19 tables** (the 3 product tables `users`, `skills`, `audit_log_entries` plus
Django's own `auth_*`, `django_*` tables). Seeded rows: `skills` = 68, `auth_group` = 4.

Cleanup:

```
$ docker compose exec -T postgres psql -U fairfold -d postgres -c "DROP DATABASE IF EXISTS fairfold_baseline;"
DROP DATABASE
```

Left behind: only `fairfold_dev` (plus `postgres`, `template0`, `template1`).

> **Note.** `manage.py seed` prints `12 countries` and `15 industries`. Those are
> `core/reference.py` constants, not tables, consistent with `README.md`'s description of `core`.

---

## 5. Test suite

```
$ .venv/bin/pytest tests/ -v
…
tests/core/test_settings_isolation.py::TestLiveSettingsAreNotPolluted::test_the_connection_agrees_with_the_settings PASSED [100%]

============================= 115 passed in 2.86s ==============================
EXIT=0
```

- **115 passed, 0 failed, 0 errors, 0 skipped.** This matches batch 0.1's `docs/AUDIT.md`
  ("115 passed") and confirms HISTORY §2.38 for this tree.
- The run includes `tests/bias/` (the DB-free bias pass) and `tests/core/` (which needs PostgreSQL,
  Redis and ClamAV from Compose).
- Run with `DEBUG` unset and `DJANGO_SETTINGS_MODULE=config.settings.ci`. With `DEBUG=True` the 14
  tests in `tests/core/test_production_settings.py` fail for an unrelated reason — the documented
  footgun.

---

## 6. Documented endpoints

Requested from **inside** the `django` container (`docker compose exec django curl …`), the method
used in `docs/AUDIT.md`. Bodies are shown for the health endpoints.

| URL | Status | Body |
|---|---|---|
| `/` | 200 | (landing page HTML) |
| `/health/` | 200 | `{"status": "ok"}` |
| `/health/ready/` | 200 | `{"status": "ok", "checks": {"database": "ok", "cache": "ok"}}` |
| `/api/v1/` | 200 | `{"version":"v1","documentation":"/api/docs/","domains":{"accounts":"/api/v1/accounts/","candidates":"/api/v1/candidates/","employers":"/api/v1/employers/","jobs":"/api/v1/jobs/","assessments":"/api/v1/assessments/","interviews":"/api/v1/interviews/","gdpr":"/api/v1/gdpr/","notifications":"/api/v1/notifications/"}}` |
| `/api/docs/` | 200 | OpenAPI UI |
| `/api/schema/` | 200 | OpenAPI schema |
| `/django-admin/` | 302 | redirect to admin login |
| `/api/demo/` | 200 | (demo page HTML) |

Host-side curl to the published port failed in this environment (see §1). Reaching the container's
bridge IP directly with `Host: localhost`, the same statuses are returned:

```
$ ip=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}' fairfold-django-1)
$ curl -s -H 'Host: localhost' -o /dev/null -w '%{http_code}\n' "http://$ip:8000/health/"
200
```

(The bare-IP request without the `Host` header returns **400**, which is `ALLOWED_HOSTS` working as
intended.)

---

## 7. Lint, types, security, dependencies

### flake8 — PASS

```
$ .venv/bin/flake8 config/ core/ accounts/ candidates/ employers/ matching/ assessments/ \
    interviews/ notifications/ api/ journey/ ai/ --max-line-length=120 --extend-exclude='*/migrations/*'
EXIT=0
```
No output.

### black — FAIL (pre-existing)

```
$ .venv/bin/black --check .
would reformat /home/shehab/FILES/CODE/PROJECTS/FAIRFOLD/scripts/verify_docs.py

Oh no! 💥 💔 💥
1 file would be reformatted, 112 files would be left unchanged.
EXIT=1
```

Black's suggested change (from `--diff`) is purely wrapping one `if any(…)` call in
`scripts/verify_docs.py` (around line 523) across multiple lines. No source file was edited. This
file is **not** covered by either the `black` or `isort` exclusions in `pyproject.toml` and the
failure is independent of this batch.

### isort — PASS

```
$ .venv/bin/isort --check-only .
Skipped 9 files
EXIT=0
```

### mypy — PASS

```
$ .venv/bin/mypy config/ core/ accounts/ candidates/ employers/ matching/ ai/ --ignore-missing-imports
Success: no issues found in 69 source files
EXIT=0
```

### bandit — CANNOT RUN ON THIS HOST (pre-existing)

The exact CI command fails before scanning, on Python 3.14.8:

```
$ .venv/bin/bandit -r . -c bandit.yaml -s B104,B105,B106,B107,B108,B311,B403
[main]  INFO  profile include tests: None
[main]  INFO  profile exclude tests: None
[main]  INFO  cli include tests: None
[main]  INFO  cli exclude tests: B104,B105,B106,B107,B108,B311,B403
[main]  ERROR Unknown test found in profile: B107
EXIT=2
```

Root cause — **bandit 1.7.10 is incompatible with Python 3.14**:

```
$ .venv/bin/bandit core/models.py -c bandit.yaml -d
[manager]  DEBUG  Exception string: 'Constant' object has no attribute 's'
```

`bandit/core/node_visitor.py` reads the pre-3.8 `ast.Constant.s`, so **every** file is skipped
("exception while scanning file"), and the plugin registry does not register `B107`
(`has B107: False`). CI pins **Python 3.12** (`.github/workflows/ci-cd.yml:95`), where bandit 1.7.10
is expected to run normally. The CI bandit result therefore **could not be reproduced here**
(`CLAUDE.md`: do not substitute a different check and call it equivalent). I attempted to run the
CI command in a throwaway `python:3.12-slim` container; the `pip install bandit==1.7.10` step did not
complete within the timeout (no reliable package access), so this is reported as **not run**.

### pip-audit — PASS

```
$ .venv/bin/pip-audit -r requirements.txt
No known vulnerabilities found
Name           Skip Reason
-------------- -----------------------------------------------------------------------------
en-core-web-sm Dependency not found on PyPI and could not be audited: en-core-web-sm (3.8.0)
torch          Dependency not found on PyPI and could not be audited: torch (2.14.1+cpu)
EXIT=0
```

Two dependencies are **skipped, not passed**: `en-core-web-sm` and `torch` come from non-PyPI
wheels, so pip-audit cannot see advisories for them. Their CVE status is **unknown**, not clean.

---

## 8. Documentation and fixture checks

### scripts/verify_docs.py — PASS (14 human notes)

```
$ .venv/bin/python scripts/verify_docs.py
…
All checks passed.

14 note(s) for a human to confirm -- these are recorded, not asserted:
  * ER entities not matched to a CREATE TABLE (expected for non-table boxes): 0
  * FAIRFOLD_Project_Architecture_and_Requirements.md mentions 'bias-free' -- must be attributed or historical, check it
  * FAIRFOLD_Feasibility_and_Design.md mentions 'bias-free' -- must be attributed or historical, check it
  * FAIRFOLD_Complete_Project_Document.md mentions 'bias-free' -- must be attributed or historical, check it
  * prd.md mentions 'bias-free' -- must be attributed or historical, check it
  * HISTORY.md mentions 'bias-free' -- must be attributed or historical, check it
  * README.md mentions 'bias-free' -- must be attributed or historical, check it
  * 63 FRs asserted 20 time(s) across the set
  * 260 points asserted 16 time(s) across the set
  * 32 tables asserted 12 time(s) across the set
  * 51 FKs asserted 5 time(s) across the set
  * 25 indexes asserted 5 time(s) across the set
  * mermaid parse harness not present in this environment; run it manually
  * 65 wireframes defined, 61 referenced by a page row; unreferenced: ['W26', 'W27', 'W28', 'W29']
EXIT=0
```

All asserted checks pass; the notes are the same set recorded in `docs/AUDIT.md`. Two are worth a
human's attention (unchanged by this batch, recorded not fixed):
`'bias-free'` still appears in six documents, and `W26`–`W29` are defined but not referenced by a
page row.

### scripts/verify_bias_set.py — PASS

```
$ .venv/bin/python scripts/verify_bias_set.py
Bias test set consistency check
…
v1.0.0
  PASS  v1.0.0 is internally consistent — 76 cases
v1.0.1
  PASS  v1.0.1 is internally consistent — 103 cases
============================================================
All 2 version(s) internally consistent.
EXIT=0
```

---

## 9. Pre-existing failures (not caused by this batch)

| Failure | Evidence | Cause | Introduced when |
|---|---|---|---|
| `black --check .` exits 1 | `1 file would be reformatted` — `scripts/verify_docs.py` | formatting-only wrapping; file predates this batch | before 0.2 |
| `bandit` exits 2, cannot scan | `Unknown test found in profile: B107`; `'Constant' object has no attribute 's'` | host Python 3.14.8 vs host-installed bandit 1.7.10; CI uses Python 3.12 | environmental |

No other command failed. No source file was changed, so nothing here can be a regression from this
batch.

---

## 10. What could not be run, and why

- **`bandit` under the CI Python.** The CI command cannot run on this host (Python 3.14). A
  `python:3.12` container attempt did not finish installing bandit. **Not verified here.**
- **README step 2 (`generate_secret_key.py --write-env`).** Not re-run: `.env` already exists with a
  populated `DJANGO_SECRET_KEY` and `ENCRYPTION_KEY` (no `change-me…` placeholders remain), and
  rewriting keys would invalidate the running stack's sessions. Verified only that the file is
  complete.
- **A true "fresh clone".** Not possible: this is the working tree, not a clone, and there are no
  network credentials. The stack was brought up with the same `docker compose up -d --wait` the
  README calls.
- **Host `curl localhost:8000/…`.** The published port is not bound in this sandbox (see §1), so the
  documented host command returns `000` here. Endpoints were verified from the container and via the
  bridge IP instead.

---

## 11. How to reproduce

1. `cp .env.example .env && python3 scripts/generate_secret_key.py --write-env` (fresh clone only).
2. `docker compose up -d --wait`.
3. Create a venv, `pip install -r requirements.txt -r requirements-dev.txt`.
4. Export the variables in §1 "Commands run", **without** `DEBUG`.
5. Run the command block in §1 and compare against §2.
6. For the endpoints, either `curl localhost:8000/health/ready/` (on a normal Docker host) or
   `docker compose exec django curl -s http://127.0.0.1:8000/health/ready/`.
7. `bandit` needs Python 3.12 (CI's version).

> **Known environment caveat:** run with Python 3.12 for bandit; the venv on this host is 3.14.
