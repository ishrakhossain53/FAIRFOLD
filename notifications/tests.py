"""Email and in-app notifications.

Tests live in `tests/<app>/` rather than here, so that `pytest tests/` collects
them and the `--cov=.` target in the CI workflow matches the directory pytest
actually reads. An empty `tests.py` inside an app is a file pytest collects and
reports zero tests from, which looks like coverage.
"""
