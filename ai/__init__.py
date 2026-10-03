"""AI provider abstraction, bias auditing and the rationale path.

This module must stay free of Django imports. `bias_pass.py` is deliberately
dependency-free -- pure text matching, no ORM, no settings -- so it can run in CI,
in a management command and in a Celery worker without a configured database.
Importing anything from `django` here would make that property false for the
whole package, and `bias_audit` handles it by importing `core.models` lazily
inside the function that needs it.

Two modules:

- ``bias_pass``   — the term/rule matcher over ``tests/bias/<version>/``. Pure.
- ``bias_audit``  — writes the pass result to ``core.models.AuditLogEntry``.

``AuditLogEntry`` lives in ``core/``, not here: it is a cross-cutting compliance
entity that no single feature owns, and the entity list assigned it to no app at
all. See Complete Doc \u00a74.2.
"""
