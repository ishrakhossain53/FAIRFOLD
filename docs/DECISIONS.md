# Decisions D-1 to D-12 — proposals for the founder to answer

Batch 0.4. **Proposals only — nothing here has been applied.** No code and no spec has been edited.
Each decision states the question, the evidence (`file:line`), the options, what each option breaks,
a single recommendation, and the exact files that change if it is accepted.

Source of the original eight decisions: `docs/ROADMAP.md` lines 46–55 ("Decisions needed"). D-9 to
D-12 are additional conflicts found while confirming D-1 to D-8 against the code. A few smaller
conflicts that need no decision are listed at the end under Observations.

How to answer: tick one option per decision, or write your own. Batch 0.5 applies the accepted
answers; it does not start until every `[ ]` below is answered.

> **Partial answers recorded 2026-10-19.** Only D-2, D-3, D-6(a)–(c) and D-7 were accepted, and
> batch 0.5 applied exactly those. The remaining decisions (D-1, D-4, D-5, D-6(d)–(e), D-8–D-12)
> are still open and are not applied.

| ID | Question | Recommendation | Files that change | Your answer |
|---|---|---|---|---|
| D-1 | Sessions or JWT for the HTMX template pages? | Sessions for pages, JWT for `/api/v1/`, one shared service | `accounts/services.py` (new), `accounts/views.py`, `accounts/urls.py` | [ ] |
| D-2 | Which role vocabulary, and which role is protected as "last one"? | Adopt the requirement names: `employer_manager`, and protect the last `employer_hr` | `core/fixtures/groups.json`, `accounts/models.py`, `seed.py`, `employers/__init__.py`, specs | [x] **B** — `employer_manager`, protect the last `employer_hr`. Applied to `groups.json`, `seed.py` ROLES and the specs; `accounts/models.py` / `employers/__init__.py` deferred to the code batch. |
| D-3 | Add email-verification endpoints to §C.12? | Yes: `verify-email/` + `verify-email/resend/`, stateless signed token (no new table) | Complete Doc §C.12, `prd.md` §13, `docs/TRACEABILITY.md` | [x] **A** — two endpoints, stateless signed token, no new table. |
| D-4 | Build the per-employer alias in Phase 1? | Yes, pull it forward (batch 1.35) | `candidates/` alias service + tests, `docs/TRACEABILITY.md` | [ ] |
| D-5 | Encrypt the PII columns now or in Phase 4? | Encrypt from creation, with the §C.8.2 `key_version` rotation plan | `accounts/models.py` + migration, new models, Complete Doc §C.8 | [ ] |
| D-6 | Close the five §5.1 schema holes now? | Yes, amend §5.1 first, then build; five sub-choices below | Arch Doc §5.1/§5.2, several models + migrations | [x] **(a)** resume `status` column, **(b)** screening state as `applications` columns (no new table), **(c)** new `job_skills` join table. **(d)/(e)** deferred. |
| D-7 | JWT lifetimes and refresh semantics | 15-min access; enable `token_blacklist`; rotation invalidates the old token | `config/settings/base.py`, Arch Doc REQ-FR-007 | [x] **A** — 15-min access; `token_blacklist` installed; REQ-FR-007 amended to "rotation invalidates the old token". |
| D-8 | Which branch is truth, `main` or `v3`? | `origin/main` (the default branch; it contains `v3`) | none (process); `HISTORY.md` §4.9 note | [ ] |
| D-9 | Password hasher: Argon2id required, code uses the default | Add `PASSWORD_HASHERS` with Argon2id first | `config/settings/base.py`, `accounts/models.py` comment | [ ] |
| D-10 | Production still emails via the console backend | Set `EMAIL_BACKEND` to an Anymail backend | `config/settings/production.py`, `.env.example` | [ ] |
| D-11 | `stripe` pinned while Phase 4 is bKash/SSLCommerz | Keep the pin but mark it Phase 5; no Phase-4 import | `requirements.txt` | [ ] |
| D-12 | `admin` app listed in the docs, absent from the repo | Drop `admin` from the app list; admin is `core` + `django.contrib.admin` | `prd.md` §12.3, Arch Doc §6.2 | [ ] |

---

## D-1 — Auth for the HTMX template pages: session or JWT?

**Question.** AD-002 promises "no auth-token complexity", but REQ-FR-002/007/008 specify JWT and the
settings enable both JWT and session auth. Which mechanism do the server-rendered pages use?

**Evidence.**

- `FAIRFOLD_Project_Architecture_and_Requirements.md:116-120` (AD-002): "Django Templates + HTMX for
  MVP … no CORS/auth-token complexity".
- `FAIRFOLD_Project_Architecture_and_Requirements.md:326` (REQ-FR-002) and `:331`/`:332`
  (REQ-FR-007/008): JWT access 15 min + refresh 7 days; refresh; logout revocation.
- `config/settings/base.py:375-380`: `DEFAULT_AUTHENTICATION_CLASSES` = JWT **and** Session;
  `DEFAULT_PERMISSION_CLASSES` = `IsAuthenticated`.
- `config/settings/base.py:164-173`: `SessionMiddleware` + `AuthenticationMiddleware` are active;
  `:302-307` session lifetime 30 min, `SESSION_ENGINE = db` (server-side).
- `config/urls.py:3-11`: two mounts — `/api/v1/` (DRF) and "everything else" (HTMX pages).
- `templates/base.html:23-25` and `:93-99`: HTMX reads the CSRF **cookie**; this is the
  session/CSRF model, not bearer-token.
- `prd.md:743`: "Sessions / tokens … JWT 15-min access / 7-day refresh with rotation and blacklist".

**Options.**

- **A — Sessions for pages, JWT for `/api/v1/`, one shared login/verification/lockout service.**
- **B — JWT everywhere** (the page layer also carries tokens).
- **C — Sessions only**, drop JWT.

**What each option breaks.**

- A: needs the auth service to expose two entry points (session login for pages, token issue for the
  API) and to keep the lockout counter and verification in **one** place. Breaks nothing in the docs.
- B: contradicts AD-002; forces token refresh in JavaScript on HTMX pages; a refresh token in a
  cookie re-introduces the CSRF/rotation problem sessions already solve.
- C: contradicts REQ-FR-002/007/008 and the DRF JWT configuration.

**Recommendation. A.** It is the only option that satisfies both AD-002 and REQ-FR-002/007/008, and
it matches what the repo already sets up (`base.py:375-380`, `urls.py:3-11`).

**Files that change if accepted.** `accounts/services.py` (new), `accounts/views.py`,
`accounts/urls.py`, `tests/accounts/test_auth_service.py`; no settings change required.

---

## D-2 — Role vocabulary, and which role is protected as "last one"

**Question.** The code and the requirements disagree on the employer-admin role name, "admin" appears
as a group in some docs and nowhere in the code, and the docs disagree about *which* role must never
be removed.

**Evidence.**

- Code: `accounts/models.py:51` `ROLES = ("candidate","employer_hr","employer_admin","interviewer")`;
  `:171`,`:175`; `core/fixtures/groups.json:22-24` (`employer_admin`);
  `core/management/commands/seed.py:45`; `employers/__init__.py:3` ("last-`employer_admin` rule").
- Requirements: `FAIRFOLD_Project_Architecture_and_Requirements.md:414` (REQ-FR-047) names
  `employer_manager`, `employer_hr`, `interviewer` and protects "the last `employer_hr`"; `:632`
  DDL `CONSTRAINT ck_team_role CHECK (role IN ('employer_manager','employer_hr','interviewer'))`.
- Docs disagree with each other: `prd.md:199`,`:577`,`:745` and
  `FAIRFOLD_Feasibility_and_Design.md:1294`,`:2390`,`:2398` say `employer_manager`; but
  `FAIRFOLD_Complete_Project_Document.md:1449` says `employer_admin`, and `design.md:1802`,`:1808`
  show `employer_admin` with the last-`employer_admin` protection.
- `prd.md:745` lists groups `admin`, `employer_hr`, `employer_manager`, `interviewer`, `candidate`,
  `guest`; REQ-FR-037/038/039/049/050 say "admin user" (`…:376-380`, `:416`). The code has **no**
  `admin` or `guest` group. Recorded as conflict 3 in `docs/AUDIT.md:95-103`.

**Options.**

- **A — Keep the code's names** (`employer_admin`), treat `admin` as `is_staff`/`is_superuser`, drop
  `employer_manager` and `guest`.
- **B — Adopt the requirement names** (`employer_manager`), protect the last `employer_hr`, treat
  `admin` as `is_staff`/`is_superuser`, treat `guest` as "unauthenticated" (not a group).
- **C — Adopt `prd.md:745` literally**: six real groups including `admin` and `guest`.

**What each option breaks.**

- A: contradicts REQ-FR-047 and the DDL check — a spec amendment is required.
- B: renames `employer_admin`→`employer_manager` in four code files; also requires fixing
  `Complete Doc:1449` and `design.md:1802/1808`.
- C: adds a group for unauthenticated users, which is not expressible as a Django group
  (anonymous users have no groups); "guest" would be a state, not a role.

**Recommendation. B**, with one clarification you must make: REQ-FR-047 (the requirement) protects the
last **`employer_hr`**, while `design.md:1808` and `employers/__init__.py:3` protect the last
**`employer_admin`**. Pick the one that is correct and we will make the other two files match it.

**Files that change if accepted.** `core/fixtures/groups.json`; `accounts/models.py:51`,`:171`,`:175`;
`core/management/commands/seed.py:45`; `employers/__init__.py:3`; spec fixes in
`FAIRFOLD_Complete_Project_Document.md:1449`, `design.md:1802`,`:1808`, `prd.md:745`.

---

## D-3 — Email-verification endpoints are missing from §C.12

**Question.** REQ-FR-001 sends a verification email and REQ-FR-002 requires a verified user, but the
API list has no verification route.

**Evidence.**

- Complete Doc §C.12 auth block: `FAIRFOLD_Complete_Project_Document.md:1799-1811` — register,
  login, refresh, logout, mfa, me, password. **No** verify-email or resend route.
- `FAIRFOLD_Project_Architecture_and_Requirements.md:325` (REQ-FR-001) and `:326` (REQ-FR-002).
- `accounts/models.py:109` `email_verified`; `design.md:714` page #11 "Email verification" with a
  resend button; `docs/ROADMAP.md:48` (D-3).
- §5.1 has **no** verification-token table (the 32 tables are listed in `ARCH §5.1`); adding one
  would change the asserted table count.

**Options.**

- **A — Add two endpoints**, `POST /api/v1/auth/verify-email/` and `POST /api/v1/auth/verify-email/resend/`,
  using a **stateless signed token** (Django `signing`/`PasswordResetTokenGenerator`), so no table is
  added.
- **B — Add the endpoints with a dedicated `email_verification_tokens` table.** Breaks the 32-table
  count everywhere (`verify_docs.py`, README, HISTORY) and needs a spec amendment.
- **C — Verify via a template page only** (token in the link). No API route.

**What each option breaks.**

- A: smallest change; needs a spec edit to §C.12 and `prd.md` §13, and a new TRACEABILITY endpoint
  cell for FR-001.
- B: a table count change ripples through several files and the doc checker.
- C: leaves the DRF API unable to verify, though §C.12 is API-first.

**Recommendation. A** — stateless signed token, no new table.

**Files that change if accepted.** `FAIRFOLD_Complete_Project_Document.md` §C.12; `prd.md` §13;
`docs/TRACEABILITY.md` (FR-001/002 endpoint cells); later `accounts/urls.py`, `accounts/api_urls.py`.

---

## D-4 — Build the per-employer alias in Phase 1?

**Question.** REQ-FR-054 is marked Phase 2, but the first employer-facing list is Phase 1.

**Evidence.**

- `FAIRFOLD_Project_Architecture_and_Requirements.md:363` (REQ-FR-029): candidates listed "by
  anonymised ID with no name, photo or contact detail".
- `FAIRFOLD_Project_Architecture_and_Requirements.md:437` (REQ-FR-054), `**Phase 2**`.
- `candidate_aliases` is in §5.1 (`ARCH §5.1`).
- `docs/ROADMAP.md:37` (finding 5) recommends pulling it forward.
- Invariant in `CLAUDE.md`/`AGENTS.md`: identity is never shown to employers before shortlist.

**Options.** **A — Pull the alias service into Phase 1** (batch 1.35, before the employer inbox).
**B — Defer to Phase 2** as the FR text says.

**What each option breaks.**

- A: FR-054's phase moves earlier; no doc contradiction, because the FR does not forbid an earlier
  build.
- B: the Phase 1 employer inbox (batches 1.40/1.42) shows identity and must be retrofitted, risking
  a real identity leak in the interim.

**Recommendation. A.**

**Files that change if accepted.** `candidates/` alias service + `tests/candidates/`;
`docs/TRACEABILITY.md` (FR-054 phase); `docs/ROADMAP.md` note.

---

## D-5 — Encrypt the PII columns now or in Phase 4?

**Question.** The DDL marks several columns `ENCRYPTED`, but the model stores them in plain text.

**Evidence.**

- `accounts/models.py:20-26`: encryption "is not applied here", plain `CharField` for now.
- `ARCH §5.1` `ENCRYPTED` columns: `users.first_name`/`last_name` (`:560-561`),
  `candidate_profiles.location` (`:581`), `candidate_resumes.original_filename` (`:597`),
  `employer_profiles.company_name` (`:609`), `certifications.credential_id` (`:736`),
  `mfa_secret` (`users`, bytea); `stripe_customer_id` (`:617`,`:642`).
- `config/settings/base.py:262` requires `ENCRYPTION_KEY`; `config/settings/production.py:42-47`
  asserts it; `requirements.txt:59` pins `django-encrypted-model-fields`.
- Complete Doc §C.8.2 `FAIRFOLD_Complete_Project_Document.md:1437`: key rotation adds a
  `key_version` column and re-encrypts in batches.
- `prd.md:752`,`:756`: AES-256-GCM at rest; the trade-off is that encrypted columns are not
  searchable, so non-sensitive copies (for example `skills`) carry search.

**Options.** **A — Encrypt from creation** (new fields as `Encrypted*` fields) together with the
§C.8.2 `key_version` rotation plan. **B — Defer to Phase 4** (batch 4.3) and keep plain text now.

**What each option breaks.**

- A: requires the rotation/`key_version` design up front; encrypted columns cannot be filtered on.
- B: retrofitting over existing rows needs a data migration and a rotation plan anyway; PII sits in
  plaintext until Phase 4; and `accounts/models.py:20-26` warns a naive switch makes old rows
  unreadable.

**Recommendation. A**, applying the `key_version` column and the rotation task as part of the same
change, and adding the two already-shipped plain columns (`users.first_name`/`last_name`) via a new
migration (never editing `0001_initial`, per Complete Doc §C.8.1 `:1420`).

**Files that change if accepted.** `accounts/models.py` + a new migration; every Phase 1 model with
an `ENCRYPTED` column; `FAIRFOLD_Complete_Project_Document.md` §C.8.

---

## D-6 — The five §5.1 schema holes

**Question.** Five gaps between the DDL and what the features need. Each is a sub-decision.

**Evidence.**

- (a) **Resume processing status.** `ARCH §5.1` `candidate_resumes` (`:593`) has no status column;
  REQ-FR-010/012 (`…:339`,`:341`) require upload → extract → embed states.
- (b) **Screening-run state.** §5.1 has no screening-run table (the 32 tables are fixed); REQ-FR-028
  (`…:362`) needs a queued batch job with progress and retry.
- (c) **Jobs ↔ skills.** REQ-FR-042 (`…:393`) searches "title, description and skills", but `jobs`
  (`:654`) has no skills link and no `job_skills` table exists.
- (d) **`users` timestamps.** DDL has `created_at`/`updated_at` (`:571-572`); the model has
  `date_joined` (`accounts/models.py:121`). Conflict 6, `docs/AUDIT.md:119-126`.
- (e) **Skills twice.** `candidate_profiles.skills` JSONB (DDL `:584`) *and* a `candidate_skills`
  table both exist; `prd.md:756` calls the JSONB a denormalised search copy.

**Options per sub-decision.**

- (a) Add a `status` enum + timestamps to `candidate_resumes`, **or** a separate processing table.
  **Recommend** the status column (smallest change that fits the 32-table schema).
- (b) Add a `screening_runs` table (32→33, a counted change), **or** store per-application screening
  state on `applications`. **Recommend** deciding explicitly; a job-level run has its own progress
  and cost fields, which suggests a table.
- (c) Add a `job_skills` join table (32→33) **or** a JSONB skills column on `jobs`. **Recommend** the
  join table, because REQ-FR-042 must *query* skills, and the join is indexable while JSONB-filtered
  search is not.
- (d) Align the model to the DDL (`created_at`/`updated_at`) **or** amend the DDL to `date_joined`.
  **Recommend** aligning the model to the DDL, since §5.1 is the artefact of record.
- (e) Declare `candidate_skills` the source of truth and the JSONB `skills` a search copy (as
  `prd.md:756` already says), **or** drop one. **Recommend** documenting the copy, not dropping.

**What each option breaks.** Any new table changes the asserted counts (**32 tables, 51 FKs, 25
indexes**) that `verify_docs.py` and several documents assert; those must be updated together
(`grep -rn '32 tables\|51 foreign\|25 indexes'`). Renaming `date_joined` is a column rename with a
migration.

**Recommendation.** Amend Arch Doc §5.1 (and §5.2 ER) **first** for (a)–(c), then build. This is
spec-first: no model is written until the DDL agrees.

**Files that change if accepted.** `FAIRFOLD_Project_Architecture_and_Requirements.md` §5.1/§5.2/§5.3;
`accounts/models.py` + migration; the new `candidates`/`employers`/`matching` models;
`docs/TRACEABILITY.md`; and every file asserting the table/FK/index counts.

---

## D-7 — JWT lifetimes and refresh semantics

**Question.** The settings and the requirements disagree on the access lifetime and on what a refresh
does, and the blacklist app is not installed.

**Evidence.**

- `config/settings/base.py:398` `ACCESS_TOKEN_LIFETIME = 30 min` vs
  `ARCH:326` (REQ-FR-002) and `prd.md:504`,`:743` = **15 min**.
- `config/settings/base.py:400-401` `ROTATE_REFRESH_TOKENS=True`, `BLACKLIST_AFTER_ROTATION=True`
  vs `ARCH:331` (REQ-FR-007): the old refresh token "remains valid until 7 days".
  But `prd.md:743` says "rotation and blacklist on logout" — the two docs already disagree.
- `ARCH:332` (REQ-FR-008) requires blacklisting on logout, but
  `rest_framework_simplejwt.token_blacklist` is **not** in `INSTALLED_APPS`
  (`config/settings/base.py:137-162`), so blacklist-after-rotation is inert. Conflict 5,
  `docs/AUDIT.md:110-117`.

**Options.**

- **A — 15-min access; install `token_blacklist`; keep rotation+blacklist; amend REQ-FR-007** to say
  rotation invalidates the old token (matching `prd.md:743`).
- **B — 15-min access; `ROTATE_REFRESH_TOKENS=False`** to honour REQ-FR-007 literally; blacklist only
  on logout.
- **C — Change the docs to match the code** (30 min, rotation).

**What each option breaks.**

- A: edits REQ-FR-007 wording (spec-first), and adds `token_blacklist` and its two migration tables.
- B: contradicts `prd.md:743` ("with rotation and blacklist").
- C: contradicts two of the three places that state 15 minutes.

**Recommendation. A.** Decide explicitly whether REQ-FR-007 or `prd.md:743` wins, then make the other
match.

**Files that change if accepted.** `config/settings/base.py:137-162` and `:397-403`;
`FAIRFOLD_Project_Architecture_and_Requirements.md:331`; `tests/accounts/`.

---

## D-8 — Which branch is truth, `main` or `v3`?

**Question.** HISTORY.md says the working branch is `v3`; the repository says otherwise.

**Evidence (live, 2026-10-19).**

- `git branch -a`: local `main` = `6aaf7aa`; `v3` = `origin/v3` = `7a7a6d9`;
  `origin/main` = `a1c4a0b`; `origin/HEAD -> origin/main`.
- `git merge-base --is-ancestor v3 origin/main` → **yes**: `v3` is contained in `origin/main`.
- `origin/main` tip `a1c4a0b` is "Merge pull request #29 from …/0.2-Baseline-run-passed"; its parents
  include `8ac6d40` (batch 0.2) and the merges of 0.0/0.1/`v3`.
- Local `main` (`6aaf7aa`) is **stale**: `git rev-list --count main..v3` = 4, `main` is an ancestor of
  `v3`.
- `HISTORY.md` §4.9 and `docs/AUDIT.md:35-56` record the same reconciliation.

**Options.** **A — `origin/main` is truth** (default branch; contains `v3`). **B — `v3` remains
truth.**

**What each option breaks.**

- A: the local `main` ref must be reset/fast-forwarded; every batch branch is cut from `origin/main`.
- B: keeps working on an ancestor of the default branch and will diverge from merged work.

**Recommendation. A — `origin/main`.** Cut every batch branch from it.

**Files that change if accepted.** None (process). A one-line note in `HISTORY.md` §4.9 and
`docs/ROADMAP.md` "How to run each batch" step 1.

---

## D-9 (extra conflict) — Password hasher: Argon2id required, code uses the Django default

**Evidence.** `ARCH:505` (REQ-SEC-001) "Password hashing | Argon2id, 512-bit salt" and `prd.md:742`;
`accounts/models.py:102` comment claims "Argon2id (`settings.AUTH_PASSWORD_HASHERS`)". But **no**
`PASSWORD_HASHERS`/`AUTH_PASSWORD_HASHERS` is set in `config/settings/base.py` or `production.py`
(only `ci.py:88` and `local.py:45` set `MD5PasswordHasher`), so production uses Django's default
PBKDF2, not Argon2id. `requirements.txt:60` already installs `argon2-cffi`. The comment also names
the wrong setting (`AUTH_PASSWORD_HASHERS` does not exist; the setting is `PASSWORD_HASHERS`).

**Recommendation.** Add `PASSWORD_HASHERS = ["django.contrib.auth.hashers.Argon2PasswordHasher", …]`
to `base.py`, keep the MD5 override in `ci.py`/`local.py`, and fix the comment.

**Files that change if accepted.** `config/settings/base.py`, `accounts/models.py:102`, a hasher test.

---

## D-10 (extra conflict) — Production still emails via the console backend

**Evidence.** `config/settings/production.py:110-118` requires a real `EMAIL_BACKEND_URL` and sets
`ANYMAIL = {"BASE_URL": …}`, but never sets `EMAIL_BACKEND`; `config/settings/base.py:335` leaves
`EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"`. So in production a password-reset
or interview email is printed to the log, not sent — with the log being the one place PII must not go.

**Options.** **A — Set `EMAIL_BACKEND` to the matching Anymail backend** (for example
`anymail.backends.resend.EmailBackend`) and configure `ANYMAIL` with the provider key.
**B — Keep the console backend** and drop the "real provider required" assertion.

**Recommendation. A.** `requirements.txt:83` already pins `django-anymail`.

**Files that change if accepted.** `config/settings/production.py`, `.env.example`, `README.md`.

---

## D-11 (extra conflict) — `stripe` pinned while the Phase-4 path is bKash/SSLCommerz

**Evidence.** `requirements.txt:86` pins `stripe>=10.0.0`; `ARCH:439` (REQ-FR-056) makes
bKash/SSLCommerz the Phase-4 payment path and Stripe a **Phase 5** option; `docs/ROADMAP.md:55`
flags this. There is no bKash/SSLCommerz client in `requirements.txt`.

**Recommendation.** Keep the `stripe` pin but mark it Phase 5 and ensure no Phase-4 module imports it
(the `PaymentProvider` abstraction in batch 4.13 is where this is enforced).

**Files that change if accepted.** `requirements.txt` (comment), and the Phase-4 design note.

---

## D-12 (extra conflict) — `admin` app is listed but does not exist

**Evidence.** `prd.md:892` lists `admin` among the Django apps, and
`FAIRFOLD_Project_Architecture_and_Requirements.md:1720` runs flake8 over `admin/`, but the repo has
no `admin/` package and `INSTALLED_APPS` (`config/settings/base.py:137-162`) does not include one.
Admin functionality is `django.contrib.admin` plus `core`. Related to D-2's "admin" role question.

**Options.** **A — Drop `admin` from the app lists** and note that admin lives in `core` +
`django.contrib.admin`. **B — Create an `admin` app** for the Phase-3 admin dashboard (batch 3.30).

**Recommendation. A**, unless an admin Django app is actually wanted; batch 3.30 can build the admin
views inside `core` without a new package.

**Files that change if accepted.** `prd.md:892`, `FAIRFOLD_Project_Architecture_and_Requirements.md:1720`.

---

## Observations — smaller conflicts, no decision needed yet

- `accounts/models.py:112` cites the lockout counter as "§4.1 REQ-FR-022", but REQ-FR-022 is Job
  Application; the lockout requirement is REQ-FR-003. A comment fix.
- `ARCH:339` (REQ-FR-010) writes `/api/candidates/resumes/` while Complete Doc §C.12
  (`:1821-1824`) writes `/api/v1/candidates/resumes/`. Conflict 8, `docs/AUDIT.md:140-143`. A doc
  typo fix, spec-first.
- `api/urls.py:98-105` advertises `jobs` and `gdpr` domains in the API root but `:108-116` mounts
  only accounts/candidates/employers/assessments/interviews/notifications. Conflict 7,
  `docs/AUDIT.md:128-138`. Expected scaffold state; fixed when those viewsets land.
- `core/tests.py:7-12` defines a test pytest never collects (pyproject `test_*.py` only).
  Conflict 9, `docs/AUDIT.md:145-148`.
- `core/management/commands/seed.py:97` calls `seed_demo`, which does not exist. `docs/AUDIT.md:166-169`.

---

**STOP.** These are proposals only. No code or spec has been changed. Answer D-1 to D-12 (tick one
option each, or write your own) and batch 0.5 will apply the accepted answers.
