# Repository audit — reconciled against the real repo

Batch 0.1. Read-only audit. Prepared **2026-10-19** by running the checks below against the working
tree, not from a zip. This replaces the earlier pre-filled version, which was written from
`FAIRFOLD-main.zip` without `.git`, without Docker and without running any database test.

- **Branch I am on:** `0.0-ready-to-began` (`git status` → `On branch 0.0-ready-to-began … nothing to commit`).
- **HEAD:** `0335ecb chore: add agent operating rules and project tracking docs`.
- **Working tree:** clean.

Every claim below carries a `file:line` or a command result. Where HISTORY.md disagrees with the code,
the code wins (`CLAUDE.md` §"Where truth lives").

## How this was verified

| Check | Command | Result |
|---|---|---|
| Django check | `manage.py check` (settings `config.settings.ci`) | `System check identified no issues (0 silenced).` |
| Migration drift | `manage.py makemigrations --check --dry-run` | `No changes detected` |
| Migrations present | `find . -path "*/migrations/*" -name "*.py"` | only `accounts/migrations/0001_initial.py`, `core/migrations/0001_initial.py` |
| Tables actually created | `docker exec fairfold-postgres-1 psql -U fairfold -d fairfold_dev -c "\dt"` | 19 relations, incl. `users`, `skills`, `audit_log_entries` |
| Test suite | `pytest tests/ -q` with `DEBUG` unset | **115 passed** |
| Bias suite (no DB) | `pytest tests/bias/ -q` | **40 passed** |
| Doc checker | `scripts/verify_docs.py` | exit 0, with 14 non-asserted notes (see §Disagreements 12) |
| Bias-set checker | `scripts/verify_bias_set.py` | v1.0.0 and v1.0.1 internally consistent |
| Endpoints | `docker exec fairfold-django-1 curl -o /dev/null -w "%{http_code}" http://127.0.0.1:8000<url>` | see §Disagreements 7 |

> **Environment note (reproducible).** This shell exports `DEBUG=True` (a devcontainer/VS Code
> variable). With it set, `pytest tests/` reports **14 failed, 101 passed** — all 14 are in
> `tests/core/test_production_settings.py`, because the fixture's `VALID_ENV` does not override
> `DEBUG` and `config/settings/production.py:33` asserts `DEBUG is False`. This is the footgun
> documented in `CLAUDE.md`/README ("do not `source .env` before running pytest"). With `env -u DEBUG`
> the suite is **115 passed**. HISTOR §2.38's "115 tests pass" is confirmed.

## Branch reconciliation (the batch asks for this explicitly)

Git history **is** available.

| Ref | Commit | Relationship |
|---|---|---|
| `0.0-ready-to-began` (HEAD) | `0335ecb` | = `v3` + 1 commit (the agent-rules/docs commit) |
| `v3` / `origin/v3` | `7a7a6d9` | 4 commits ahead of local `main`; 0 commits behind it |
| `main` (local) | `6aaf7aa` | **ancestor** of `v3`; `git rev-list --count v3..main` = 0 |
| `origin/main` / `origin/HEAD` | `e40f0fc` | 3 commits ahead of `v3` (contains the `0.0-ready-to-began` merge PRs #24, #27) |

- **Does `main` differ from `v3`?** Yes. `v3` has 4 commits `main` lacks (`0909c23`, `d4b4ef3`,
  `c6ebb5c`, `7a7a6d9`); `main` has none that `v3` lacks. `git diff --stat main v3` shows the
  local-run fixes, README rewrite, `validation/` kit and the extra `verify_docs.py` checks.
- The local `main` ref is **stale**: `origin/main` (`e40f0fc`) already contains the
  `0.0-ready-to-began` work and is the tip of the default branch.
- `git diff --stat HEAD origin/main` is **empty** — this working tree is byte-identical to
  `origin/main`. So the "zip named `main`" is (or matches) the current tree; HISTORY's
  "current branch is `v3`" describes an ancestor, not the checkout.
- HISTORY.md §4.9 (line 1865) says `origin/v3` is in sync with local `v3` — **confirmed**
  (`git rev-parse v3 origin/v3` both `7a7a6d9`). Live `git fetch`/`ls-remote` was not attempted
  (no credentials), so this is a local-ref comparison, not a network check.

## App-by-app: implemented vs scaffold only

"Implemented" = a model/service/view with a migration or logic and (where stated) tests.
"Scaffold" = a package with docstring-only modules, empty URL lists, or unchanged placeholder files.

| App | State | Evidence |
|---|---|---|
| `accounts` | **Implemented (model only).** `User` model + migration; no views, no API, no tests. | `accounts/models.py:95` (`User`), `:51` (`ROLES`); `accounts/migrations/0001_initial.py:18`; `accounts/urls.py` → `urlpatterns: list = []`; `accounts/api_urls.py:25` empty router; `accounts/tests.py` docstring only; no `tests/accounts/` |
| `core` | **Implemented.** `AuditLogEntry` + `Skill` models + migration; `reference.py`, `seed` command, `groups.json`/`skills.json` fixtures, middleware, logging, pagination, exception handler, error/health views; **75 passing tests**. | `core/models.py:33`,`:110`; `core/migrations/0001_initial.py:19`,`:37`; `core/{reference,middleware,logging,pagination,exceptions,views,urls}.py`; `tests/core/` (36+19+13+7 = 75) |
| `candidates` | **Scaffold only.** | `candidates/models.py` docstring-only (12 lines); `candidates/urls.py` empty; `candidates/api_urls.py:25` empty router; no migration; no tests |
| `employers` | **Scaffold only.** | `employers/models.py` docstring-only; `employers/urls.py` empty; `employers/api_urls.py:25` empty router; no migration; no tests |
| `matching` | **Scaffold only.** No API module at all. | `matching/models.py` docstring-only; `matching/urls.py` empty; **no `matching/api_urls.py`**; no migration; no tests |
| `assessments` | **Scaffold only.** | `assessments/models.py` docstring-only; `assessments/urls.py` empty; `assessments/api_urls.py:25` empty router; no migration; no tests |
| `interviews` | **Scaffold only.** | `interviews/models.py` docstring-only; `interviews/urls.py` empty; `interviews/api_urls.py:25` empty router; no migration; no tests |
| `notifications` | **Scaffold only.** | `notifications/models.py` docstring-only; `notifications/urls.py` empty; `notifications/api_urls.py:25` empty router; no migration; no tests |
| `journey` | **Scaffold only.** No API module at all. | `journey/models.py` docstring-only; `journey/urls.py` empty; **no `journey/api_urls.py`**; no migration; no tests |
| `api` | **Scaffold + a working API root.** `ApiRootView` and router wiring exist; **zero registered viewsets**. | `api/urls.py:56` `ApiRootView`, `:108` `urlpatterns`; `grep -rn "router.register"` → matches only comments, no live registrations |
| `ai` | **Mixed:** `bias_pass.py` (333 lines) and `bias_audit.py` (290 lines) implemented, with `tests/bias/` (40 passing tests) and versioned sets v1.0.0/v1.0.1; **but** no `AIProvider`, `models.py` is a docstring only, `urls.py` empty. | `ai/bias_pass.py`, `ai/bias_audit.py:136`; `tests/bias/`; `ai/models.py` (12 lines); `grep -rn "class .*Provider" ai core matching` → none |
| `config` | **Implemented.** Four settings modules, `urls.py`, `wsgi.py`, `celery.py`. | `config/settings/{base,local,ci,production}.py`; `config/urls.py` |
| `templates` | **Partial scaffold.** Base shell, landing page, three error pages; no feature pages. | `templates/{base,home}.html`, `templates/errors/{403,404,500}.html` |

**Models implemented: 3 of the 32 tables** asserted in Arch Doc §5.1 (`users`, `skills`,
`audit_log_entries`). HISTOR §1/§2.30 said "no Django model exists"; that is now false.

## Disagreements between the docs and the code

Numbered; each has file:line evidence.

1. **HISTORY.md says no model exists.** `HISTORY.md:10` ("no Django model exists, so `migrate`
   creates zero tables"), `:27` and `:1654` say the same. **False:** `accounts.User`
   (`accounts/models.py:95`), `core.AuditLogEntry` (`core/models.py:33`), `core.Skill`
   (`core/models.py:110`) exist with migrations, `makemigrations --check` reports no drift, and the
   database contains `users`, `skills`, `audit_log_entries`.

2. **HISTORY.md says the current branch is `v3`.** `HISTORY.md:8`. The checkout is
   `0.0-ready-to-began` (`0335ecb`), one commit ahead of `v3` (`7a7a6d9`). See §Branch reconciliation.

3. **Role name: `employer_admin` (code) vs `employer_manager` (requirements).**
   Code: `accounts/models.py:51` (`ROLES`), `:171`–`:175`; `core/fixtures/groups.json:22`;
   `core/management/commands/seed.py:45`; `employers/__init__.py:3`.
   Docs: `FAIRFOLD_Project_Architecture_and_Requirements.md:414` (REQ-FR-047) and `:632`
   (`CONSTRAINT ck_team_role CHECK (role IN ('employer_manager','employer_hr','interviewer'))`);
   `prd.md:199`, `:577`, `:745`; `FAIRFOLD_Feasibility_and_Design.md:1294`, `:2390`, `:2398`, `:2603`.
   The docs also contradict **each other**: `FAIRFOLD_Complete_Project_Document.md:1449` lists
   `employer_hr, employer_admin, interviewer` and `design.md:1802` shows `employer_admin`, while
   `FAIRFOLD_Complete_Project_Document.md:303` lists `employer_manager`.

4. **JWT access-token lifetime: 30 min (code) vs 15 min (requirement).**
   Code: `config/settings/base.py:398` `"ACCESS_TOKEN_LIFETIME": timedelta(minutes=30)`.
   Requirement: `FAIRFOLD_Project_Architecture_and_Requirements.md:326` (REQ-FR-002, "JWT access
   (15 min)"); `prd.md:504`.

5. **JWT refresh semantics: rotation+blacklist (code) vs "old refresh stays valid" (requirement).**
   Code: `config/settings/base.py:400`–`:401` (`ROTATE_REFRESH_TOKENS=True`,
   `BLACKLIST_AFTER_ROTATION=True`). Requirement: REQ-FR-007
   (`FAIRFOLD_Project_Architecture_and_Requirements.md:331`) says the old refresh token "remains
   valid until 7 days". Related: REQ-FR-008 (`:332`) requires blacklisting on logout, but
   `rest_framework_simplejwt.token_blacklist` is **not** in `INSTALLED_APPS`
   (`config/settings/base.py:137`–`:162`; `grep -rn token_blacklist config/` → no match), so
   blacklist-after-rotation is not effective.

6. **`users` field names differ from the DDL.**
   DDL `CREATE TABLE users` (`FAIRFOLD_Project_Architecture_and_Requirements.md:556`–`:572`) declares
   `password_hash` (`:559`), `mfa_secret` (`:565`), `created_at` (`:571`), `updated_at` (`:572`).
   Model (`accounts/models.py`) has Django's `password` (`accounts/migrations/0001_initial.py:21`),
   `date_joined` (`accounts/models.py:121`) and **no** `created_at`, `updated_at` or `mfa_secret`
   (`grep -rn "mfa_secret\|updated_at" accounts core` → no match). The model adds `is_superuser`
   (via `PermissionsMixin`, `accounts/models.py:95`) which the DDL does not declare. The
   `password_hash`↔`password` equivalence is documented at `accounts/models.py:102`–`:104`.

7. **Endpoints: ~70 listed in Complete Doc §C.12; none implemented.** Requests to
   `/api/v1/auth/login/`, `/api/v1/auth/refresh/`, `/api/v1/jobs/`, `/api/v1/employers/team/`,
   `/api/v1/admin/announcements/`, `/api/v1/messages/` all return **404**. The only endpoints that
   respond are core ones: `/` (200), `/api/demo/` (200), `/health/` (200), `/health/ready/` (200),
   `/api/v1/` (200), `/django-admin/` (302). Two specific mismatches:
   - `api/urls.py:98`–`:105` (`ApiRootView.get`) advertises `"jobs"` and `"gdpr"` domains, but
     `api/urls.py:108`–`:116` mounts only `accounts`, `candidates`, `employers`, `assessments`,
     `interviews`, `notifications`. `/api/v1/jobs/` and `/api/v1/gdpr/` → **404**.
   - The six mounted prefixes are empty `DefaultRouter`s (`accounts/api_urls.py:25` and siblings),
     so `/api/v1/accounts/` etc. return **401** (the router's own authenticated API-root), not a
     product endpoint.

8. **Resume-upload path: `/api/candidates/resumes/` vs `/api/v1/candidates/resumes/`.**
   REQ-FR-010 (`FAIRFOLD_Project_Architecture_and_Requirements.md:339`) writes
   `/api/candidates/resumes/` (no version segment); `FAIRFOLD_Complete_Project_Document.md` §C.12
   writes `/api/v1/candidates/resumes/`.

9. **`core/tests.py` holds a test pytest does not run.** `core/tests.py:7`–`:12` defines
   `HomePageTests.test_homepage_renders`. `pyproject.toml:96` (`python_files = ["test_*.py"]`) and
   `:100` (`testpaths = ["tests"]`) mean this file is never collected. `CLAUDE.md` calls `<app>/tests.py`
   "empty placeholders"; this one is neither empty nor run.

10. **Table count.** The docs assert **32 tables** (`HISTORY.md:73`; `verify_docs.py` note "32 tables
    asserted 12 time(s)"). The code implements **3** (§App-by-app). Expected scaffold state, recorded
    as the numeric delta rather than an error.

11. **No AI provider abstraction.** The Progress plan's batch 2.21 and REQ-FR-030's rationale path
    expect an `AIProvider`/offline-fallback seam; `grep -rn "class .*Provider" ai core matching` →
    no matches. Only the deterministic bias pass exists (`ai/bias_pass.py`, `ai/bias_audit.py`).

12. **`verify_docs.py` notes that are real doc inconsistencies (the checker passes them as notes).**
    `README.md:38`/`design.md` state **64 wireframes covering all 78 pages**, but the checker reports
    "65 wireframes defined, 61 referenced by a page row; unreferenced: `W26`, `W27`, `W28`, `W29`".
    The phrase "bias-free" also still appears in six documents (checker note), against the
    `CLAUDE.md` invariant that the product must not be described as bias-free.

## Observations (out of scope for this batch — noticed, not fixed)

- **`manage.py seed --demo` would fail.** `core/management/commands/seed.py:97` calls
  `call_command("seed_demo", …)`, but only `seed.py` exists in `core/management/commands/`
  (`ls core/management/commands/` → `__init__.py`, `seed.py`). Any `--demo` run raises
  "Unknown command". Not exercised in the normal path (CI/Compose run `seed` without `--demo`).
- **`requirements.txt` pins `stripe`** while the Phase-4 payment path in the docs is
  bKash/SSLCommerz (`prd.md` §8.8) — carried over from the pre-filled audit, not re-verified here.
- **HISTORY.md has duplicated section numbers** (`2.28`, `2.36` appear more than once near the end,
  lines ~1508–1974). Left untouched; the new entry is appended at the very end.

## Not done in this batch

- No code was edited. No requirement status was changed to `done` — this batch demonstrates no
  acceptance criterion (it is an audit), so `docs/TRACEABILITY.md` is left as-is per the batch prompt.
