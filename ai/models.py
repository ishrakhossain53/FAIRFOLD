"""AI provider abstraction, bias auditing and the rationale path.

Models are declared here as empty on purpose. `ai/` is the exception: it has no
models of its own, and `AuditLogEntry` lives in `core/` (Complete Doc §4.2).

This scaffold deliberately does **not** pre-declare the 24 tables from
Arch Doc §5.1. Writing them from the DDL in one pass would produce models
whose field types, indexes and constraints were never checked against a running
database, and `makemigrations --check` in CI would then pass on migrations that
encode a guess. The DDL remains the specification; models are added app by app
against it, one migration at a time.
"""
