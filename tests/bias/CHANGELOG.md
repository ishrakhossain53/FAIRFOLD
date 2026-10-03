# Bias test set — changelog

One line per version: what changed and why. Versions are **immutable**; a fix is a new
directory, never an edit to an old one, so a CI run reproduces the set it thought it ran.

Format follows the spec in `FAIRFOLD_Project_Architecture_and_Requirements.md` §7.4.

---

## v1.0.0 — 2026-10-03 — first version

**Authored:** Ishrak Hossain. **Spec:** Arch Doc §7.4, written earlier the same day.
**Status:** fixture set complete and internally consistent. **Pass rate: not measured** —
there is no bias pass implementation in the repository yet.

| | |
|---|---|
| Cases | **76** — 58 must-flag, 18 must-not-flag |
| Categories | 10, matching the §7.4.3 targets exactly |
| Terms | **62** proposed terms in 8 groups, plus **6 deliberately excluded** |
| Known limitations | **5** (`LIM-001`–`004`, `GAP-001`), each with a planned version |

**Contents by category.** `gendered_club_role` 12 · `institution_gender_signal` 8 ·
`age_reference` 8 · `nationality_origin_proxy` 6 · `family_status` 6 ·
`disability_health` 4 · `photo_appearance` 4 · `uncited_vague_rationale` 10 ·
`legitimate_skill_match` 12 · `necessary_context` 6.

### Three things worth remembering about how this set was written

**1. The negatives are the half that matters.** 18 of 76 cases exist to stop the pass
being trivially good. `NEG-013` (a women's-rights reading group) is why bare *women's* is
excluded; `NEG-017` (a candidate describing a male-dominated field) is why bare *male* is
excluded. Each of the 6 excluded terms names the case that enforces its exclusion, and the
validator checks that link holds — so an exclusion cannot be quietly deleted along with the
case that justified it.

**2. The validator found three authoring errors in the first draft.** Declared
`expected_terms` that the case text did not actually contain:

| Case | Declared | The text said | Cause |
|---|---|---|---|
| `PROXY-040` | `not planning to marry` | "no plans to marry" | paraphrase drift while authoring |
| `RAT-007` | `does not fit our culture` | "does not yet fit our culture" | same |
| `RAT-010` | `cultural fit` | "culturally aligned" | see GAP-001 |

All three were cases where the text looked like it would be caught, and would not have
been. This is the case for `expected_terms` existing at all: a keyword pass with no
per-case declaration is exactly the thing that reports a clean result because its
fixtures agree with it by construction.

**3. The spec had a collision in it, found while writing the cases.** §7.4.3 listed
*"recent graduate programme 2026"* as a must-NOT-flag `necessary_context` example, while
*recent graduate* belongs in `age_reference` as a proxy — the same phrase cannot both flag
and not flag. Resolution: **`recent graduate` was removed from the term list** (recorded
in `deliberately_excluded`) and `NEG-015` reworded to *"six-month graduate trainee
programme in 2026"*. The underlying gap is real and is **not** closed: graduation-year
proximity is the mechanism behind the 2018 case and is tracked as `LIM-002` for v1.0.1.

### What this version deliberately does not do

- **Measure nothing.** `pass_criteria` in the manifest are targets, not results.
- **Make no disparity claim.** At 76 cases the set cannot support one, and §1.4.1 of the
  feasibility document already withdraws the claim. `does_not_support` in the manifest
  states this so a later report cannot cite the set as evidence of fairness.
- **Cover no Bengali-language text** (`LIM-003`, severity high). The target market is
  Bangladesh and the term list is English-only. **This is the most serious gap in
  v1.0.0** — a pass that reads only English will report clean on exactly the population
  the product is for.
- **Detect no numeric age** (`LIM-001`) and **no graduation-year proximity** (`LIM-002`).

### Next version — v1.0.1 (planned, not written)

Close `LIM-001` (numeric age) and `LIM-002` (graduation-year proximity) with new
categories and their own negative cases, and address `GAP-001`. Author the Bengali term
list for **v1.1.0** with native review, not machine translation.
