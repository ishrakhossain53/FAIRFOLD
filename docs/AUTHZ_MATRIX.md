# Authorization matrix

**Enforced by:** `tests/core/test_authz_matrix.py` (batches 1.13, 1.15, 1.16).
**Requirement:** REQ-SEC-010 (security headers) and the fail-closed rule in the
batch: `REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"]` is `IsAuthenticated`, and a
view that needs to be public must say so explicitly.

This file is the human-readable half of the matrix. The test is the authority; if
the two disagree, the test output wins and this table is the bug.

## Actors

| Actor | How the test builds it |
|---|---|
| anonymous | a fresh `django.test.Client`, no session |
| candidate | `User` in the `candidate` group |
| employer | `User` in the `employer_hr` group |
| admin | `is_staff=True`, `is_superuser=True`, **no role group** |

`admin` deliberately holds no role group: `/django-admin/` must be gated by
`is_staff`, and the API must treat the account as authenticated rather than as a
member of a role. Groups come from `core/fixtures/groups.json`, the D-2 source of
truth.

## Matrix

All requests are `GET` except the rows marked `POST`; a `POST` row is sent an
empty body on purpose. The question is whether the request reaches the permission
layer's answer or is refused before the serializer runs.

| Route | Method | Anonymous | Candidate | Employer | Admin | Why |
|---|---|:--:|:--:|:--:|:--:|---|
| `/` | GET | 200 | 200 | 200 | 200 | public landing page |
| `/api/demo/` | GET | 200 | 200 | 200 | 200 | public connectivity probe |
| `/health/` | GET | 200 | 200 | 200 | 200 | liveness probe (Arch Doc §6.5) |
| `/health/ready/` | GET | 200 | 200 | 200 | 200 | readiness probe reports, does not gate |
| `/register/` | GET | 200 | 200 | 200 | 200 | public page #6 |
| `/register/check-email/` | GET | 302 | 302 | 302 | 302 | no pending address in the session → back to registration |
| `/verify-email/` | GET | 400 | 400 | 400 | 400 | no token = documented invalid state |
| `/verify-email/resend/` | POST | 302 | 302 | 302 | 302 | no pending address in the session → back to registration |
| `/login/` | GET | 200 | 302 | 302 | 302 | signed-in users are sent to their landing page |
| `/logout/` | POST | 302 | 302 | 302 | 302 | POST-only by design; GET logout would be CSRF-able |
| `/forgot-password/` | GET | 200 | 200 | 200 | 200 | public page #9 |
| `/reset-password/` | GET | 400 | 400 | 400 | 400 | no uid/token = documented expired state |
| `/candidate/onboarding/` | GET | 302 | 200 | 403 | 403 | candidate-only onboarding form; anonymous → login (batch 1.16) |
| `/candidate/profile/` | GET | 302 | 302 | 403 | 403 | candidate-only profile; no profile → onboarding (batch 1.16) |
| `/candidate/profile/edit/` | POST | 302 | 302 | 403 | 403 | candidate-only inline edit; no profile → onboarding (batch 1.16) |
| `/django-admin/` | GET | 302 | 302 | 302 | 200 | staff-only; non-staff go to the admin login |
| `/api/v1/` | GET | 200 | 200 | 200 | 200 | public API index (URL prefixes only) |
| `/api/v1/auth/register/` | POST | 400 | 400 | 400 | 400 | public by necessity; empty body fails validation |
| `/api/v1/auth/verify-email/` | POST | 400 | 400 | 400 | 400 | public; the token is the credential |
| `/api/v1/auth/verify-email/resend/` | POST | 400 | 400 | 400 | 400 | public; identical answer for every address |
| `/api/v1/auth/login/` | POST | 400 | 400 | 400 | 400 | public; it is how a caller becomes authenticated |
| `/api/v1/auth/refresh/` | POST | 400 | 400 | 400 | 400 | public; the refresh token is the credential |
| `/api/v1/auth/logout/` | POST | 400 | 400 | 400 | 400 | public; the refresh token in the body is the credential |
| `/api/v1/auth/password/reset/` | POST | 400 | 400 | 400 | 400 | public; anti-enumeration answer |
| `/api/v1/auth/password/reset/confirm/` | POST | 400 | 400 | 400 | 400 | public; uid + token are the credential |
| `/api/v1/auth/password/change/` | POST | **401** | 400 | 400 | 400 | authenticated for every role; the 400 is the empty body |
| `/api/v1/auth/me/` | GET | **401** | 200 | 200 | 200 | authenticated for every role (batch 1.12) |
| `/api/v1/candidates/me/` | GET | **401** | 404 | 403 | 403 | candidate-only; 404 until onboarding; PATCH is covered by `tests/candidates/test_profile_api.py` (batch 1.15) |
| `/api/v1/accounts/` | GET | **401** | 200 | 200 | 200 | DRF router root inherits the global default |
| `/api/v1/candidates/` | GET | **401** | 200 | 200 | 200 | same |
| `/api/v1/employers/` | GET | **401** | 200 | 200 | 200 | same |
| `/api/v1/assessments/` | GET | **401** | 200 | 200 | 200 | same |
| `/api/v1/interviews/` | GET | **401** | 200 | 200 | 200 | same |
| `/api/v1/notifications/` | GET | **401** | 200 | 200 | 200 | same |

## How the test stays fail-closed

1. **Route discovery is independent of the table.** The test walks
   `django.urls.get_resolver()` recursively and compares the discovered paths
   with the matrix in both directions:
   - a route with no row fails (`test_every_registered_route_has_a_matrix_row`);
   - a row for a route that no longer exists also fails, so the table cannot
     drift into fiction.
2. **A synthetic new route is proved to be caught**
   (`test_a_route_added_without_a_rule_is_detected`), so the discovery half is
   itself tested rather than assumed.
3. **Parameterised routes must be handled explicitly.** Any path containing
   `<...>` outside `django-admin/` fails
   (`test_no_parameterised_route_is_silently_uncovered`); a real object id would
   otherwise make the expected answer depend on which row exists. DRF's
   `<drf_format_suffix:format>` duplicate of a router root is the one exception:
   it resolves to the same view.
4. **The global default is asserted**
   (`test_the_global_default_is_fail_closed`): the API-wide permission class is
   `IsAuthenticated`, so a new `APIView` that forgets `permission_classes` is
   closed, not open.

### Deliberate exclusions

| Excluded | Reason |
|---|---|
| `django-admin/` internals (~80 generated CRUD paths) | all pass through the same `is_staff` check; one matrix row covers the decision |
| `static/`, `media/` | development-only mounts in `config/urls.py`, not application routes |
| `api/schema/`, `api/docs/` | registered only with `DEBUG=True`; not part of the production surface |

A new prefix or a new route under an existing app is **not** excluded and will
fail the discovery test until it is added here.

## Security headers

Asserted on real responses under production-like settings in
`tests/core/test_security_headers.py`:

| Header | Value | Set by |
|---|---|---|
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains; preload` | `SecurityMiddleware`, only on secure requests |
| `X-Content-Type-Options` | `nosniff` | `SecurityMiddleware` |
| `X-Frame-Options` | `DENY` | `XFrameOptionsMiddleware` |
| `Referrer-Policy` | `same-origin` | `SecurityMiddleware` |
| `Content-Security-Policy` | `default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self'; font-src 'self'` | `core.middleware.ContentSecurityPolicyMiddleware` from `settings.CONTENT_SECURITY_POLICY` |

The settings half of the same contract is asserted in
`tests/core/test_production_settings.py::test_transport_security_is_on`.

### Content-Security-Policy (REQ-SEC-010)

Set by `core.middleware.ContentSecurityPolicyMiddleware` from
`settings.CONTENT_SECURITY_POLICY` on every response. Django 5.2 has no CSP
support, and the policy was previously documented only at the Nginx edge
(Arch Doc §6.3). A deployment without that proxy therefore shipped no CSP, and
there was nothing for a Django test to assert. The policy is now part of the
application's tested surface; the edge must not add a second, different header,
because browsers intersect multiple CSP headers and the effective policy then
depends on two files that can drift.

The policy is deliberately self-hosted:

```text
default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self'
'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self'; font-src 'self'
```

- `base.html` loads the compiled Tailwind file and the vendored htmx from
  `/static/`, and design.md §11.2 says the CDN is not a production fallback.
  No `cdn.tailwindcss.com` or `cdn.jsdelivr.net` source remains.
- `'unsafe-inline'` for scripts and styles is still required by the two inline
  `<script>` blocks (`base.html`, `home.html`) and by inline style attributes.
  Replacing it with a per-response nonce is a separate change with its own
  template edits; it is not silently claimed here.
- `connect-src 'self'` is sufficient because AI calls are server-side. The
  browser never talks to OpenRouter.

A response that already carries a `Content-Security-Policy` keeps it: a view
with a stricter per-page policy must not be weakened by the global one.
