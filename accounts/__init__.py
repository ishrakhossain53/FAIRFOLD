"""User model, authentication, MFA, RBAC and profiles.

`AUTH_USER_MODEL = "accounts.User"`. Roles are the four Django groups seeded by `manage.py seed` (Complete Doc §C.8.3); permissions are checked with `has_perm`, never by comparing a role string in a view.
"""
