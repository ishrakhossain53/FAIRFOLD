"""Shared utilities, middleware, security and cross-cutting models.

Cross-cutting pieces that do not belong to one feature. Notably it owns
`AuditLogEntry`, which the compliance entity list assigns to no single
app -- the decision is recorded in Complete Doc §4.2.
"""
