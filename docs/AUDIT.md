# Repository audit (pre-filled by the assistant)

Prepared on 2026-10-18 from the uploaded `FAIRFOLD-main.zip` (203 files). I read code and docs and ran three
database-free checks. I did **not** run Docker or any database test, and the zip had no `.git` folder.
Treat this as a starting point for batch 0.1: have your agent confirm it against your real repo and branch.

## App by app

| App / area | State | Evidence |
|---|---|---|
| `accounts` | `User` model + migration `0001`. No registration or login endpoints found. No tests. | `accounts/models.py` (UUID pk, email login, lockout fields, roles via groups) |
| `core` | `AuditLogEntry`, `Skill`, migration, `seed` command, groups and skills fixtures, middleware, health views, pagination, exception handler. 4 test files. | `core/models.py`, `core/fixtures/`, `tests/core/` |
| `ai` | `bias_pass.py`, `bias_audit.py` (`audit_rationale` at line 136), versioned bias sets. **No `AIProvider`.** | `ai/`, `tests/bias/`; no `AIProvider` match in any `.py` |
| `candidates`, `employers`, `matching`, `assessments`, `interviews`, `notifications`, `journey` | Placeholder `models.py` only. The one I opened (`ai/models.py`) states models are added app by app against the DDL. | `*/models.py` |
| `api` | URL wiring only; not audited line by line. | `api/urls.py` |
| Templates | `base.html`, `home.html`, error pages. No feature pages. | `templates/` |
| Tests | `tests/bias/` and `tests/core/` only. Nothing for `accounts`. | `tests/` |

## What I ran

| Check | Result |
|---|---|
| `pytest tests/bias` (outside Django config) | 40 passed |
| `scripts/verify_bias_set.py` | v1.0.0 and v1.0.1 internally consistent (v1.0.1: 103 cases) |
| `scripts/verify_docs.py` | exit 0, with warnings (see item 6 below) |
| Docker stack, `manage.py check`, migrations, DB tests, linters | **Not run** |

## Disagreements and gaps found

1. `HISTORY.md` says no Django model exists. `accounts.User`, `core.AuditLogEntry` and `core.Skill` do.
2. `HISTORY.md` says the working branch is `v3`; the zip is named `main`. Confirm which is current.
3. `HISTORY.md` has duplicated section numbers (`2.28`, `2.31`, `2.36`) and repeated content near the end. Appending the batch log at the very end of the file is safe; do not rewrite older sections.
4. Roles: `groups.json` has `employer_admin`; REQ-FR-047 says `employer_manager`; several FRs say "admin" with no admin group (decision D-2).
5. JWT: settings use a 30-minute access token with rotation and blacklist-after-rotation; REQ-FR-002 says 15 minutes and REQ-FR-007 says the old refresh token stays valid. `rest_framework_simplejwt.token_blacklist` is not in INSTALLED_APPS (decision D-7).
6. `verify_docs.py` warnings: the phrase "bias-free" appears in 6 documents and must be attributed or historical; 65 wireframes are defined but only 61 are referenced by a page row (W26 to W29 unreferenced). Confirm which counts the docs should state.
7. No email-verification endpoint in the API list (§C.12) although REQ-FR-001/002 need one (decision D-3).
8. Schema holes: resume upload/scan/processing status; no screening-run table; no job-to-skills link though REQ-FR-042 searches skills; `users` uses `date_joined` where the DDL says `created_at`/`updated_at` (decision D-6).
9. `docker-compose.yml` has no object store, but REQ-FR-010 needs S3-compatible storage (batch 1.17).
10. `requirements.txt` includes `stripe`; REQ-FR-056 makes bKash/SSLCommerz the Phase 4 path.
11. `HISTORY.md` §2.38 says 115 tests passed on 2026-10-16. Not reproduced here; batch 0.2 reproduces it.
