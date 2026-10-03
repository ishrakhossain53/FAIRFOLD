"""Load the reference data a fresh database needs before serving a request.

Complete Doc §C.8.3. Run automatically after `migrate` in CI and in the Compose
entrypoint, so a CI database and a developer's database hold **identical**
reference data. A divergence there produces a test that passes locally and fails
in CI for no visible reason.

**Two mechanisms, not one**, because only two of the four seeds are tables:

- **Fixtures** (`loaddata`) for `groups` and `skills`. Both are real tables in
  Arch Doc §5.1 -- `auth_group` (Django's own) and `skills`.
- **Constants** in `core.reference` for score bands, countries and industries.
  §5.1 has no table for any of them, and none was added: nothing joins to these
  values, no user edits them at runtime, and schema designed to match a fixture
  list rather than a requirement is how a 24-table schema becomes a 27-table one
  nobody chose. `core.reference.validate()` runs here, so an empty or overlapping
  list fails at seed time instead of rendering an empty `<select>`.

What is **not** seeded: employers, candidates, jobs, applications, resumes. Those
come from `factory-boy` in tests and from real use in production. Seeding demo
rows into a production-shaped database is how a "test employer" ends up holding a
real employer's data — and `--demo=true` refuses to run when `DEBUG=False` for
exactly that reason.
"""

from __future__ import annotations

import json
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core import reference

# Only tables. Score bands, countries and industries are constants in
# `core.reference`, validated below rather than loaded here.
FIXTURES = ["groups", "skills"]

# The four roles from the Arch Doc. Kept as module constants so a test can assert
# the set matches, rather than spelling them out in a dozen test files.
ROLES = ["candidate", "employer_hr", "employer_admin", "interviewer"]


class Command(BaseCommand):
    help = "Load committed reference-data fixtures. Idempotent."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--demo",
            action="store_true",
            default=False,
            help=(
                "Add clearly-fake sample rows for local UI work. Refuses to run "
                "when DEBUG is False."
            ),
        )
        parser.add_argument(
            "--noinput",
            "--no-input",
            action="store_true",
            dest="noinput",
            default=False,
            help="Do not prompt.",
        )

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        if options["demo"] and not settings.DEBUG:
            # Not a warning. Demo rows in a production-shaped database are a data
            # leak waiting for the first real employer to be assigned one.
            raise CommandError(
                "--demo refused: DEBUG is False. Demo data must never be loaded "
                "into a non-development environment."
            )

        for name in FIXTURES:
            path = self._fixture_path(name)
            if not path.exists():
                # A missing fixture is a hard error. Skipping it would leave an
                # empty `skills` table and every matching test would fail with a
                # message pointing at the wrong thing.
                raise CommandError(
                    f"Missing fixture: {path}. It is committed to the repository; "
                    f"a missing one means a bad checkout, not an empty database."
                )
            call_command("loaddata", name, verbosity=0)
            self.stdout.write(self.style.SUCCESS(f"  loaded {name}.json"))

        self._verify_groups()
        self._verify_reference()

        if options["demo"]:
            call_command("seed_demo", verbosity=options["verbosity"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Seed complete: {len(FIXTURES)} fixtures, "
                f"{len(reference.COUNTRIES)} countries, "
                f"{len(reference.INDUSTRIES)} industries, "
                f"{len(reference.SCORE_BANDS)} score bands."
            )
        )

    @staticmethod
    def _fixture_path(name: str) -> Path:
        return Path(settings.BASE_DIR) / "core" / "fixtures" / f"{name}.json"

    @staticmethod
    def _verify_reference() -> None:
        """Validate the constants, and warn loudly about uncalibrated bands.

        The warning is on every seed run because the bands will still be
        provisional when Phase 2 starts, and a developer seeing a "Consider for
        interview" band in the UI should know the threshold has never been tested
        against real scores. Silence here would let an uncalibrated threshold
        harden into an assumed one.
        """
        try:
            reference.validate()
        except ValueError as exc:
            raise CommandError(f"core.reference is invalid: {exc}") from exc

        if not reference.is_calibrated():
            labels = ", ".join(reference.band_labels())
            self.stdout.write(
                self.style.WARNING(
                    f"  score bands are PROVISIONAL and uncalibrated ({labels}). "
                    f"design.md §3.4 marks them as needing a calibrated model; do "
                    f"not present them as measured."
                )
            )

    def _verify_groups(self) -> None:
        """Assert every role exists after loading.

        Role checks run on nearly every permission test, and a missing group fails
        as "permission denied" — which points at the test rather than at the seed.
        Checking here turns a confusing test failure into a clear boot error.
        """
        existing = set(Group.objects.values_list("name", flat=True))
        missing = [role for role in ROLES if role not in existing]
        if missing:
            raise CommandError(
                f"groups.json did not create: {missing}. Expected exactly {ROLES}."
            )
        # Warn rather than fail on extras: an admin may have added a role
        # deliberately, and refusing to seed would block a legitimate deploy.
        extra = existing - set(ROLES)
        if extra:
            self.stdout.write(
                self.style.WARNING(
                    f"  note: extra groups present beyond the four documented "
                    f"roles: {sorted(extra)}"
                )
            )


def load_json_fixture(name: str) -> list[dict]:
    """Read a fixture file as a list of dicts. Used by tests and the demo seeder."""
    path = Command._fixture_path(name)
    if not path.exists():
        raise CommandError(f"Missing fixture: {path}")
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)