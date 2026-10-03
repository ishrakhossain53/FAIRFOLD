# Bias test set — changelog

One line per version: what changed and why. Versions are **immutable**; a fix is a new
directory, never an edit to an old one, so a CI run reproduces the set it thought it ran.

Format follows the spec in `FAIRFOLD_Project_Architecture_and_Requirements.md` §7.4.

---

## v1.0.1 — 2026-10-03 — the numeric rule layer

**Closes `LIM-001` (no numeric age) and `LIM-002` (no graduation-year proximity) by fix.**
Authored and measured the same day as v1.0.0.

| | v1.0.0 | v1.0.1 |
|---|---|---|
| Cases | 76 | **103** (+27) |
| Categories | 10 | **13** |
| Phrase terms | 62 | 62 — **unchanged, byte-identical** |
| Numeric rules | none | **5**, in 2 families |
| Must-flag / must-not-flag | 58 / 18 | 75 / 28 |
| Measured | rate 0.7632 | recall **1.0** · **0 FP** · rate **0.7282** |
| CI assertions | 18 | **25** |

**Versioning is why the terms did not move.** The phrase list and the rules are separate
layers precisely so a reader can tell whether a regression came from the phrases or from the
rules without diffing two large files. A single mixed list would make that unanswerable.

### New categories

| # | Category | Cases | Purpose |
|---|---|---|---|
| 11 | `numeric_age` | 9 must-flag | Closes `LIM-001`. `24 years old`, `Age: 31`, `Aged 22`, `28 yrs old`, and three date-of-birth formats |
| 12 | `graduation_year_proximity` | 8 must-flag | Closes `LIM-002`. `Graduated in 2026`, `Class of 2025`, `Cohort of 2024`, `Passed HSC in 2026`, `Currently pursuing B.Sc` |
| 13 | `numeric_near_miss` | 10 must-not-flag | Ordinary professional text, including `team of 12 junior engineers` and `1,000-concurrent load test` |

**Category 13 is the point of this version.** Ten lines that look nothing like an age are
what stop a rule learning to read any two-digit number as one.

### Two guards make the graduation rule usable at all

Without either of these the rule is worthless, and both are asserted:

1. **The year must sit within 24 characters of an education keyword.** A bare four-digit
   year is a phone number or a budget. `Budget approved: 2026` must not flag.
2. **The year must fall inside `graduation_window_years` of `reference_year`.**
   `NUMF-009` — *"Graduated in 1994"* — must not flag. **Every resume has a graduation
   year**, so an unbounded rule flags everything and reports clean by doing so.

`ScanContext` carries both parameters instead of the rule reading the clock, so a run is
reproducible and a test can assert an exact year.

### Three findings from authoring it

**1. My own cases caught two rule bugs, not the reverse.** `NUM-005` (*"Date of birth 4 July
1995"*) and `NUM-007` (*"Born on 1999-06-14"*) both failed on the first run. The cause was
not the cases but the rule: a single `date_of_birth` pattern could not put the year in
capture group 1 for both day-first and ISO order, so it was **split into three rules** —
`dob_day_first`, `dob_iso`, `dob_named_month` — each capturing the year.

**2. `(?:0?\d)` matched only a one-digit day.** So `12/03/1998` never matched at all while
`4 July 1995` did, which is why only two of the three failed. Corrected to `(?:\d{1,2})` in
all three rules. **A pattern that looks right and is wrong on two-digit inputs is not caught
by a reviewer reading it** — it is caught by a case with a two-digit day in it.

**3. `NEG-015` and `NUMF-010` had to be reworded, and the rule was right both times.**
v1.0.0's `NEG-015` ended *"…trainee programme in 2026"*. The new `graduation_year` rule
flags it — **a 2026 completion year genuinely is the proxy**. That is the rule working, not
a failure, so the case was reworded rather than the rule weakened. Both cases now say why
they changed.

### Still open after this version

| ID | Status |
|---|---|
| `LIM-003` | **Accepted out of scope** — no Bengali term list |
| `GAP-001` | **Closed by decision** — bare adjectives stay out |
| `LIM-004` | Open, **low** — substring matching has no word boundaries |

No limitation in this version is "scheduled and unwritten". The three that remain are one
accepted risk, one decision, and one low-severity note.

---

## v1.0.0 — 2026-10-03 — first version, and the pass

**Authored:** Ishrak Hossain. **Spec:** Arch Doc §7.4.
**Status:** fixture set complete; **bias pass implemented and measured**
(`ai/bias_pass.py`, `tests/bias/test_bias_pass.py`, 18 assertions passing).

| | |
|---|---|
| Cases | **76** — 58 must-flag, 18 must-not-flag |
| Categories | 10, matching the §7.4.3 targets exactly |
| Terms | **62** in 8 groups, plus **6 deliberately excluded** and 5 allowed single-word tokens |
| Known limitations | **5** — `LIM-001`, `LIM-002` scheduled for v1.0.1; `LIM-004` low; **`LIM-003` and `GAP-001` closed by decision** |
| Measured | recall **1.0** · false positives **0** · overall flag rate **0.7632** |

> **What the measured numbers do and do not mean.** Recall of 1.0 on a set whose term list
> was authored alongside the cases is close to tautological and proves very little. The
> two figures that carry information are the **zero false positives**, which show the six
> deliberate exclusions hold, and the **flag rate landing inside [0.60, 0.95]**, which
> shows the pass is not flagging everything. This is a fixture result. It is not evidence
> about real candidates, and it says nothing about the embedding model or the ranking
> function.

**Contents by category.** `gendered_club_role` 12 · `institution_gender_signal` 8 ·
`age_reference` 8 · `nationality_origin_proxy` 6 · `family_status` 6 ·
`disability_health` 4 · `photo_appearance` 4 · `uncited_vague_rationale` 10 ·
`legitimate_skill_match` 12 · `necessary_context` 6.

### Three things worth remembering about how the set was written

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

### Measured run

| Metric | Value |
|---|---|
| Flagged | 58 / 76 |
| Recall on must-flag | 1.0 (58/58) |
| False positives on must-not-flag | **0** (0/18) |
| Overall flag rate | **0.7632** — inside the [0.60, 0.95] band |
| Assertions | **18** passing |

### Five findings from implementing the pass

**1. The spec's flag-rate band was unsatisfiable.** §7.4.5 originally set the band *"on
categories 1–8"* at 60–95%. But 100% recall is required on exactly those categories, so
their flag rate is necessarily **1.0** — permanently above the 0.95 ceiling. Two
requirements in one section, mutually exclusive. The band now applies to the **overall**
rate across all 76 cases, the only denominator under which it carries information. Found by
running the pass, not by reading the section: the two requirements look fine on the page
and cannot both be met.

**2. A test I wrote asserted a rule the spec never stated.** The first version of
`test_no_single_word_terms` banned *all* single-word terms, and failed on `married`,
`presentable` and `all-girls`. The spec only forbids single-word **vague adjectives**
(`GAP-001`). The test was wrong, not the term list. It now tests the rule that exists —
the named adjectives are absent — plus a cap of 8 single-word tokens, so the set cannot
drift toward one-word adjectives without a deliberate change.

**3. `'married'` is a substring of `'unmarried'`.** Both are `family_status` terms and
both must flag, so the overlap is harmless here. Recorded in
`single_word_terms.known_interaction` because the same overlap in another pair would be a
silent double-count, and because seeing it is the kind of thing that should be written down
rather than discovered.

**4. Negative-testing the implementation found an untested branch.** The pass was broken
three ways on purpose and the suite was required to fail each time:

| Injected regression | Caught? |
|---|---|
| Drop apostrophe folding | ✅ 2 assertions failed |
| Match every term unconditionally (flag everything) | ✅ 3 assertions failed |
| **Swallow the missing-term-list exception and return `[]`** | ❌ **suite passed** |

The third is the worst failure mode the pass has: **with no terms it flags nothing, every
case looks clean, and the output is indistinguishable from a pass finding no bias.** No test
caught it because every test supplies an explicit set directory, so the missing-file branch
was never executed. Two tests were added in response
(`test_missing_term_list_fails_loudly`, `test_no_versioned_set_fails_loudly`) and the
regression now fails as it should.

This is the strongest argument for negative-testing a checker rather than a checker: a suite
that has only ever been run green is evidence that the cases pass, not evidence that they
can fail.

**5. `keyword_terms.json` gained a `single_word_terms` block and two decisions.** The
manifest `keyword_list_sha` was bumped to match. **No term was added or removed** — the
cases are unaffected.

### Decisions taken 2026-10-03

| ID | Decision | Effect |
|---|---|---|
| **`LIM-003`** | **No Bengali term list.** Accepted as out of scope | A Bengali or transliterated resume gets a flag rate of zero from this pass and **no indication the check did not apply**. Residual risk stated in the file; not repeated across the documentation |
| **`GAP-001`** | **Bare adjectives stay out.** `energetic`, `articulate`, `mature`, `dynamic`, `passive` etc. are not terms | Closed by decision, not by fix — the gap still exists. The mitigation is the existing design: the LLM pass is advisory, the rationale is shown with evidence, and a human decides. `test_no_bare_vague_adjectives_in_the_list` enforces it in CI |

### Verification note

The suite was executed in this environment through a **minimal pytest shim**, because
pytest is not installed here and installing it was not authorised. The assertions ran and
all 15 passed; CI runs real pytest. Recorded in `manifest.measured.verified_in_this_environment`
so nobody later mistakes a shimmed run for a proper one.

### What this version deliberately does not do

- **Make no disparity claim.** At 76 cases the set cannot support one, and §1.4.1 of the
  feasibility document already withdraws the claim. `does_not_support` in the manifest
  states this so a later report cannot cite the set as evidence of fairness.
- **Detect no numeric age** (`LIM-001`) and **no graduation-year proximity** (`LIM-002`).
  Both scheduled for v1.0.1.
- **Cover no Bengali-language text** (`LIM-003`) — **accepted out of scope by the team**,
  not missed. See the decisions table.

### Next version — v1.0.1 (planned, not written)

Close `LIM-001` (numeric age) and `LIM-002` (graduation-year proximity) with new
categories and their own negative cases.
