"""Settings package.

Four modules, composed rather than imported wholesale:

- ``base``    — everything shared. Never imported directly by ``manage.py``.
- ``local``   — development. ``DEBUG=True``, console email, local Postgres.
- ``ci``      — CI. Production-like security settings, test database, fast hashing.
- ``production`` — everything asserted and no defaults.

``test`` is **not** defined: ``.env.example`` states that SQLite lacks pgvector,
so a ``config.settings.test`` module would invite exactly the tests that fail for
the wrong reason. Tests use ``config.settings.ci`` against real PostgreSQL.
"""