"""The FairFold user model.

Transcribed from Arch Doc §5.1 `CREATE TABLE users`. `AUTH_USER_MODEL` in
`config/settings/base.py` points here, so this class must exist before
`manage.py check` can pass — which is why it is the first model written rather
than one of the last.

Three decisions worth stating, because each looks unusual in a Django codebase:

1. **No `username`.** Django's default user model requires one; this project
   authenticates by email. `USERNAME_FIELD = "email"` and `REQUIRED_FIELDS =
   ["first_name", "last_name"]` make that explicit, so a `createsuperuser`
   prompt does not ask for a field that does not exist.
2. **A UUID primary key**, matching the DDL. Not Django's autoincrement. The
   ids appear in URLs and in audit rows, and a sequential integer is an
   enumeration oracle for anyone who guesses one.
3. **`AbstractBaseUser`, not `AbstractUser`.** The default brings a `username`
   column and a `last_login` we do not want to inherit without deciding on it.

**Encrypted fields.** `first_name` and `last_name` are ENCRYPTED in the DDL.
That is field-level encryption via `django-encrypted-model-fields`, which needs
`ENCRYPTION_KEY` set or the model raises at query time. **The encryption is not
applied here** — adding an `EncryptedCharField` before the key-rotation and
data-migration strategy in Complete Doc §C.8 exists would create rows that the
rotation procedure cannot read. Plain `CharField` for now, with the DDL's intent
recorded in the migration that will switch it.

**Roles are not a field.** `employer_admin`, `employer_hr`, `interviewer` and
`candidate` are Django **groups**, seeded from `core/fixtures/groups.json`, and
checked with `has_perm`. A `role` column would be a second source of truth that
drifts from the permission tables, and `REQ-FR-047`'s last-admin rule would then
have to be enforced twice.
"""

from __future__ import annotations

import uuid
from typing import Any

from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models
from django.utils import timezone

# The four documented roles. Declared here so a test can assert the fixture set
# matches, rather than the names being spelled out in a dozen test files. The
# authoritative definitions live in core/fixtures/groups.json.
ROLES = ("candidate", "employer_hr", "employer_admin", "interviewer")


class UserManager(BaseUserManager["User"]):
    """Creates users without a username.

    `create_user` sets a unusable password when none is given, so a user created
    for an OAuth flow cannot log in with a blank password. That default is the
    point: an OAuth-only account that also accepts an empty password is an
    account anyone can take over.
    """

    use_in_migrations = True

    def _create(self, email: str, password: str | None, **extra: Any) -> "User":
        if not email:
            raise ValueError("An email address is required.")
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_user(
        self, email: str, password: str | None = None, **extra: Any
    ) -> "User":
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create(email, password, **extra)

    def create_superuser(
        self, email: str, password: str | None = None, **extra: Any
    ) -> "User":
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("is_active", True)
        if not extra["is_staff"] or not extra["is_superuser"]:
            raise ValueError("A superuser must have is_staff and is_superuser set.")
        return self._create(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    """A person using FairFold — either a candidate or an employer."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    email = models.EmailField(unique=True, max_length=255)

    # Argon2id (settings.AUTH_PASSWORD_HASHERS). `AbstractBaseUser` stores this as
    # `password`; the DDL calls the column `password_hash` and the two are the
    # same value.
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)

    auth_provider = models.CharField(max_length=20, default="email")
    email_verified = models.BooleanField(default=False)
    mfa_enabled = models.BooleanField(default=False)

    # Lockout state, used by the failed-login counter in §4.1 REQ-FR-022.
    # `locked_until` is an absolute time rather than a boolean so a lockout can
    # expire on its own with no scheduled job to clear it.
    locked_until = models.DateTimeField(null=True, blank=True)
    failed_login_attempts = models.PositiveIntegerField(default=0)
    last_login = models.DateTimeField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        db_table = "users"
        verbose_name = "user"
        verbose_name_plural = "users"
        ordering = ["-date_joined"]

    def __str__(self) -> str:
        # The email, not the name. This string appears in admin listings, in log
        # lines and in error messages, and the first and last name are the fields
        # the DDL marks ENCRYPTED — putting them here would decrypt them for
        # every log line that renders a user.
        return self.email

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def is_locked(self) -> bool:
        """True while a lockout is in force.

        `locked_until` in the past means the lockout has served its time. Reading
        the field directly instead of calling this method is the easy mistake,
        and it produces a user who stays locked forever.
        """
        return bool(self.locked_until and self.locked_until > timezone.now())

    def has_role(self, role: str) -> bool:
        """Membership of a seeded group.

        Read-only and advisory — it does **not** grant a permission. Use
        `has_perm` for an access decision; this is for "which UI does this user
        see" and for tests. Two ways to answer the same question is how they
        drift apart.
        """
        return self.groups.filter(name=role).exists()

    @property
    def is_candidate(self) -> bool:
        return self.has_role("candidate")

    @property
    def is_employer(self) -> bool:
        return self.has_role("employer_admin") or self.has_role("employer_hr")

    @property
    def is_employer_admin(self) -> bool:
        return self.has_role("employer_admin")
