# Validation instrument — `FAIRFOLD_Feasibility_and_Design.md` §1.3.4

This directory holds the **instrument** for the requirement-validation plan: the
consent form, the recording sheets, the survey, and an empty results table.

## ⚠️ Nothing here has been collected

**No interview, survey or concept test has been run.** `results.md` is empty by design
and every cell is marked. Do not fill any of it from memory, from assumption, or from
"what we would expect" — an invented finding is worse than no finding, because §1.2.2
and the academic report both cite evidence, and a fabricated count would propagate into
a claim nobody can trace back to a person.

The plan fixes the sample size, the channel and the questions **before** anyone collects
data, so that nobody can later describe a result that was never collected. Keeping that
promise is the entire reason this directory exists.

## What is in here

| File | What it is | Who uses it |
|---|---|---|
| `consent_form.md` | Printed and signed before any session | The participant |
| `instruments.md` | Interview guides, the concept-test script, the survey | The interviewer |
| `results.md` | The recording sheet, **empty** | The person who ran the sessions |

## Rules for whoever runs this

1. **Read the consent form aloud**, not just hand it over. Several participants will not
   read it, and the ones who cannot read it well are disproportionately the ones the
   product is for.
2. **Record answers, not conclusions.** The sheet asks for a quote or a count. "They
   seemed to distrust it" is a conclusion and it is unusable.
3. **Do not correct participants.** If someone says screening is fine, that is the data.
4. **Do not lead.** The guides are ordered so the leading questions come last. Do not
   add a fifth "but wouldn't you agree…" — that is the single easiest way to turn this
   exercise into confirmation of the PRD.
5. **Do not run past the stated sample sizes.** 8–10 candidates, 5–6 recruiters. Beyond
   that the material stops being themes and starts being a dataset nobody has time to
   analyse, and a half-analysed set of 20 interviews is worth less than a complete set
   of 9.
6. **Withdraw anything.** A participant can ask for their notes to be deleted at any
   point, including after the session. Delete them and note the withdrawal in
   `results.md` without recording why.

## Sample sizes are small, and that is deliberate

The target is a small honest evidence base, not a study. At n=9 candidates, **no
percentage from this exercise may be published as a market fact.** Report as "of N
participants". Anything else turns eight conversations into a statistic, which is the
mistake this project has already had to correct once — the withdrawn "bias-free" claim
(`HISTORY.md` §2.22) began as an unmeasured assertion.

## After it runs

1. Fill `results.md` — counts and quotes only.
2. In `FAIRFOLD_Feasibility_and_Design.md` §1.3.4, retag each activity **[Done]** and
   cite the real counts.
3. In §1.2.2, replace any **[Illustrative]** local-evidence claim with the measured one —
   or leave it tagged if the new data does not cover it.
4. Update `HISTORY.md` §4.2, which currently says this plan is **[Planned], not a
   blocker**.

If the data contradicts a requirement, **the requirement changes**, not the reading of
the data. That is the whole reason this is recorded before collection rather than after.