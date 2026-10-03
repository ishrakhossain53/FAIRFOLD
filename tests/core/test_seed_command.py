"""Tests for the `seed` management command and the health-check views.

`seed.py` was the site of a real bug: `_verify_reference` was decorated
`@staticmethod` but wrote to `self.stdout`, so **every** `manage.py seed` raised
`NameError` at exactly the point the score bands are known to be provisional.
Nothing in the documentation could have caught it; flake8's F821 did.

These tests need a database (`pytest.mark.django_db`) because the command
asserts the groups it loaded. CI provides PostgreSQL; there is no SQLite path.
"""

from __future__ import annotations

import json

import pytest
from django.contrib.auth.models import Group
from django.core.management import CommandError, call_command

from core.management.commands.seed import FIXTURES, ROLES, load_json_fixture
from core.models import Skill
from core.reference import SCORE_BANDS, is_calibrated


@pytest.mark.django_db
class TestSeedCommand:
    def test_loads_every_declared_fixture(self):
        call_command("seed", verbosity=0)
        # The fixtures list is what CI and the compose entrypoint both rely on.
        # A fixture added to the directory but not to FIXTURES is silently never
        # loaded, which looks like a working seed and an empty taxonomy.
        assert FIXTURES == ["groups", "skills"]

    def test_creates_all_four_roles(self):
        call_command("seed", verbosity=0)
        existing = set(Group.objects.values_list("name", flat=True))
        assert set(ROLES) <= existing, f"missing roles: {set(ROLES) - existing}"

    def test_creates_the_skill_taxonomy(self):
        call_command("seed", verbosity=0)
        assert Skill.objects.count() > 0

    def test_is_idempotent(self):
        # CI runs migrate -> seed on every push and the compose entrypoint runs
        # it on every container start. A second run must not duplicate rows, or
        # the skill count drifts upward until matching slows to a crawl.
        call_command("seed", verbosity=0)
        first_skills = Skill.objects.count()
        first_groups = Group.objects.count()
        call_command("seed", verbosity=0)
        assert Skill.objects.count() == first_skills
        assert Group.objects.count() == first_groups

    def test_skills_have_canonical_names_and_aliases(self):
        call_command("seed", verbosity=0)
        # An empty alias list is not an error -- many skills have none -- but a
        # skill with no canonical_name would break Stage-1 matching silently.
        for skill in Skill.objects.all():
            assert skill.canonical_name
            assert skill.canonical_name == skill.canonical_name.strip()

    def test_aliases_resolve_to_one_skill(self):
        # The point of the taxonomy: "JS" and "JavaScript" must not be two
        # different skills, or a resume is scored against neither.
        call_command("seed", verbosity=0)
        js = Skill.objects.get(canonical_name="JavaScript")
        assert js.matches("js")
        assert js.matches("JS")
        assert js.matches("Node.js")
        assert not js.matches("Python")

    def test_alias_matching_ignores_case_and_surrounding_space(self):
        call_command("seed", verbosity=0)
        py = Skill.objects.get(canonical_name="Python")
        assert py.matches("  PYTHON  ")
        assert py.matches("Python3")

    def test_refuses_demo_data_when_debug_is_false(self, settings):
        # A refusal, not a warning. Demo rows in a production-shaped database are
        # how a "test employer" ends up holding a real employer's data.
        settings.DEBUG = False
        with pytest.raises(CommandError, match="DEBUG is False"):
            call_command("seed", demo=True, verbosity=0)


class TestFixtureFiles:
    def test_groups_fixture_matches_the_declared_roles(self):
        rows = load_json_fixture("groups")
        names = {row["fields"]["name"] for row in rows}
        assert names == set(ROLES), (
            "core/fixtures/groups.json and seed.ROLES have drifted apart. The "
            "command verifies the database, not the constant, so this is the "
            "only place the two are compared."
        )

    def test_skills_fixture_is_unique_on_canonical_name(self):
        rows = load_json_fixture("skills")
        names = [row["fields"]["canonical_name"] for row in rows]
        duplicates = {n for n in names if names.count(n) > 1}
        # loaddata would not complain -- it upserts by pk -- so a duplicate
        # canonical name lands as two rows that match the same resume text.
        assert not duplicates, f"duplicate canonical names: {duplicates}"

    def test_skills_fixture_primary_keys_are_stable_uuids(self):
        # Generated with uuid5 from a fixed namespace. A random pk per regeneration
        # makes every fixture edit show 68 changed lines instead of one.
        rows = load_json_fixture("skills")
        for row in rows[:3]:
            assert row["pk"].count("-") == 4

    def test_score_bands_are_not_calibrated(self):
        # design.md 3.4 calls them provisional. `seed` warns on every run, and
        # this asserts the data behind that warning so it cannot be flipped
        # without a deliberate edit.
        assert is_calibrated() is False
        assert all(band["calibrated"] is False for band in SCORE_BANDS)

    def test_no_fixture_carries_real_pii(self):
        # Every fixture row is reference data. A name, email or resume fragment
        # in here would be committed and shipped.
        for fixture in FIXTURES:
            blob = json.dumps(load_json_fixture(fixture)).lower()
            for marker in ("@example.com", "@gmail.com", "password", "resume.pdf"):
                assert marker not in blob, f"{fixture}.json contains {marker!r}"
