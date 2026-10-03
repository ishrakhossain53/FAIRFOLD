"""Pytest configuration for the whole suite.

Two things here that are easy to get wrong:

1. **`django.setup()` runs before any test is collected.** Without it, importing a
   model at module scope raises `AppRegistryNotReady`, and the error appears in
   whichever test file happened to import first — which reads as a bug in that app
   rather than as a missing setup step.
2. **No SQLite fallback.** `pyproject.toml` points `DJANGO_SETTINGS_MODULE` at
   `config.settings.ci`, which uses the PostgreSQL service container. A test that
   touches a `VectorField` cannot run on SQLite, and allowing one would mean
   passing locally and failing in CI.

`ai.bias_pass` and `ai.bias_audit` need **none** of this — they are dependency-free
so they can run in CI, a management command and a Celery worker without a database.
The bias tests under `tests/bias/` therefore execute with or without Django
installed, which is deliberate: the pass is the highest-risk logic in the product
and should not be gated on infrastructure being up.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Set before django.setup(). pyproject.toml sets it too, but a bare `pytest
# tests/bias/` or an IDE runner may not read pyproject.toml first.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.ci")

try:
    import django
except ImportError:
    # Django is absent. Not an error: the bias-pass tests do not need it, and
    # failing here would make `pytest tests/bias/` impossible to run standalone.
    django = None  # type: ignore[assignment]

if django is not None:
    django.setup()


# ---------------------------------------------------------------------------
# Markers
# ---------------------------------------------------------------------------
# Declared here as well as in pyproject.toml because `--strict-markers` (set there)
# makes an undeclared marker an ERROR. A marker that only pytest knows about is
# usually a typo, and a typo'd marker means the tests it was meant to select ran
# for the wrong reason.

def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "bias: bias-pass behaviour. Runs without Django or a database.",
    )
    config.addinivalue_line(
        "markers",
        "slow: takes more than a few seconds. Excluded from the pre-commit run.",
    )
    config.addinivalue_line(
        "markers",
        "requires_pgvector: touches a VectorField. Needs the PostgreSQL service.",
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def bias_set_dir() -> Path:
    """Path to the current bias fixture version.

    Pinned to the highest version directory rather than read from a constant, so a
    new `v1.0.2/` is picked up automatically instead of leaving the tests running
    against a version nobody meant to assert.
    """
    versions = sorted((ROOT / "tests" / "bias").glob("v*"))
    if not versions:
        pytest.skip("no bias fixture versions found")
    return versions[-1]