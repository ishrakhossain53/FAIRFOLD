# PII and proxy test set — changelog

One entry per version: what was added and why. Versions are **immutable**; a fix or
expansion is a new directory (`v1.0.1`, ...), never an edit to `resumes.jsonl` in an
existing version, so a CI run reproduces the exact dataset it claims to have evaluated.

Format mirrors `tests/bias/CHANGELOG.md` and follows `FAIRFOLD_Project_Architecture_and_Requirements.md`
§4.1 (`REQ-FR-011`, `REQ-FR-057`), `AD-005`, and §10 Phase 2.

---

## v1.0.0 — 2026-11-11 — initial synthetic evaluation set and harness

**Spec:** `REQ-FR-011` (amended 2026-10-12 to cross-reference `REQ-FR-057`), `REQ-FR-057`
(expanded PII and proxy stripping), `AD-005`, Arch Doc §10 Phase 2 (`95%+` accuracy).

| Metric | Value |
|---|---|
| Resumes | **20** synthetic CVs (`PII-001` .. `PII-020`), fictional people only |
| Categories | **10** (`name`, `email`, `phone`, `address`, `national_id`, `age_date`, `url`, `photo`, `employer`, `institution`) |
| Labelled PII spans | **229** (`name` 22, `email` 20, `phone` 20, `address` 40, `national_id` 18, `age_date` 33, `url` 21, `photo` 11, `employer` 21, `institution` 23) |
| Keep-set spans | **134** (role titles, degree levels and fields, technical skills, experience durations) |
| Trivial baseline (2.6) | recall **0.0000** (0/229) · precision **0.0000** · keep-set survival **1.0000** (134/134) |
| Deterministic layer (`redact_deterministic`, 2.7) | deterministic recall **1.0000** (119/119) · overall recall **0.6681** (153/229) · precision **1.0000** · keep-set survival **1.0000** (134/134) |
| Full pipeline (`strip_pii`, 2.8) | overall recall **1.0000** (229/229, `>= 0.95` gate) · precision **1.0000** · keep-set survival **1.0000** (134/134) |

### Why both `pii_spans` and `keep_spans` exist

A stripper that replaces the entire resume with `[REDACTED]` achieves 100% recall on
every PII category while destroying the resume for downstream embedding and citation.
The 134 `keep_spans` guard the opposite failure mode: every role title, degree level and
field, technical skill, and years-of-experience duration must survive stripping intact.
