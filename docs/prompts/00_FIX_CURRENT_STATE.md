# Fix the current state (run before Phase 2)

Two prompts, two sessions, in this order. Each is documentation/tooling only: no product code changes.
Branch for FIX-1: `chore/fix-state`. Branch for FIX-2: `chore/token-diet`. Review the diff, run the checks yourself, merge, then start the next one.

Before FIX-1, copy into the repo and commit on its own branch: `docs/prompts/` (this folder), `scripts/slim_prompts.py`, `scripts/build_phase_prompts.py`.

What the audit found (2026-11-11, `main` at `abd3eea`, read from git and files; Docker and pytest were not run):

| # | Finding | Fixed in |
|---|---|---|
| 1 | `CLAUDE.md` and `AGENTS.md` are byte-identical, so the agent loads the same 8 KB twice | FIX-1 |
| 2 | `CLAUDE.md` line 4 and `docs/ROADMAP.md` line 61 point to `prompts/`; the real folder is `docs/prompts/paste-ready/` | FIX-2 |
| 3 | `docs/PROGRESS.md`: 0.3 to 0.5 unchecked although `TRACEABILITY.md` and `DECISIONS.md` exist; 2.26 to 2.29 are `[ ]` but the code landed (should be `[~]`) | FIX-1 |
| 4 | Table count drift: the DDL has 33 `CREATE TABLE`, `verify_docs.py` asserts 33 in 22 places, `CLAUDE.md`, ROADMAP and batch 2.30 say 32; `CLAUDE.md` says 51 FKs, the script asserts 53 | FIX-1 |
| 5 | "bias-free" appears in 6 files (Arch Doc, Feasibility, Complete Doc, prd, HISTORY, README, per `verify_docs.py`); W26 to W29 defined but unreferenced; README says 64 wireframes, script says 65 | FIX-1 |
| 6 | 99 specs for Phases 2 to 5 (363 KB) repeat a rules block that says "you cannot see my repo, I run the tests", which contradicts `CLAUDE.md`. Measured: slimming them leaves 73 KB | FIX-2 |
| 7 | The agent is told to read canonical docs that total about 1.4 MB, so each session burns tokens on text it does not need | FIX-2 |
| 8 | Branches: `v1`, `ishrak53V2`, `ishrakhossain53-patch-1` are fully merged (0 unique commits); the Dependabot branch has 1 commit that only changes `package-lock.json` | FIX-1 (report only) |

Not fixed on purpose: `stripe` is still pinned in `requirements.txt` (decision D-11, handled in 4.13 and 5.1); the empty apps `journey`, `interviews`, `assessments`, `api` stay in `INSTALLED_APPS` until their features exist.

---

## FIX-1: Repo state and doc consistency

```text
Read CLAUDE.md. This is a cleanup batch, not a feature batch. Change no product code or behaviour. Do not commit, push, merge or delete any branch. Work on a new branch `chore/fix-state`.

First confirm these exist, else STOP: docs/prompts/PHASE_2.md to PHASE_5.md, scripts/slim_prompts.py, scripts/build_phase_prompts.py.

1. Git. Run `git fetch --all --prune`. The working tree must be clean and on the latest origin/main. For every remote branch run `git rev-list --left-right --count origin/main...origin/<branch>` and report a table: branch, commits unique to it, last commit date. If any branch except the Dependabot one has unique commits, STOP and list them. For `dependabot/npm_and_yarn/npm_and_yarn-a8587adb2e`, show the diff, test it on a throwaway checkout with `npm ci && npm run build`, and say whether it passes. Do not merge it. List the fully merged branches so I can delete them on GitHub.
2. Hygiene. `git ls-files | grep -E '(^|/)\.env$|\.pem$|id_rsa'` must print nothing, and `.env` must be in .gitignore. Report the result.
3. AGENTS.md is identical to CLAUDE.md. Replace it with exactly: "Read CLAUDE.md in full before doing anything. It is the only agent instruction file."
4. docs/PROGRESS.md. Check evidence before touching a line.
   - 0.3: if docs/TRACEABILITY.md lists all 63 REQ-FR with a status and a source, mark [x] with the date and the count you verified.
   - 0.4: if docs/DECISIONS.md holds proposals D-1 to D-13, mark [x].
   - 0.5: for each of D-1 to D-13 state whether DECISIONS.md records an acceptance and what the code actually does (file evidence). Mark 0.5 [x] only if every decision is accepted and applied. Otherwise leave it [ ] and put each undecided one in your report under "Needs my decision", with your recommendation. Do not pick silently.
   - 2.26 to 2.29: change [ ] to [~] (pre-filled code, verified later in group P2.5/P2.6). Do not mark them done.
   - Touch no other line.
5. Count drift. The truth for table, FK and index counts is the DDL in the Arch Doc section 5.1. Count the CREATE TABLE statements, FOREIGN KEY/REFERENCES clauses and indexes there. (At audit: 33 tables; CLAUDE.md, docs/ROADMAP.md and batch 2.30 say 32; CLAUDE.md says 51 FKs, verify_docs.py asserts 53.) Cross-check against the Django models and migrations. If the DDL and the models disagree, STOP and report. Otherwise make every file agree with what scripts/verify_docs.py asserts. Grep the whole repo for the old numbers, including docs/prompts/paste-ready/2.* to 5.* . Do NOT edit docs/prompts/paste-ready/0.* or 1.* (Phase 0 and 1 prompts stay byte-identical); report any stale number you find there. Do not change an assertion in verify_docs.py to make it pass without telling me.
6. verify_docs.py notes.
   - "bias-free": in each flagged file reword to "explainable", unless the mention is a quote, a historical record, or a sentence that forbids the term. Leave those and list them with file and line.
   - Wireframes: report which of W26 to W29 are unreferenced by a page row, and where batch 2.20 (which cites W26 to W29) expects them. README says 64, the script says 65 defined and 61 referenced: explain the gap. Do not delete or edit wireframes. Propose the smallest design.md fix and wait for me.
7. Observations only, do not fix: stripe pinned in requirements.txt (D-11), empty app packages, anything else you notice.
8. Run every command from the CLAUDE.md "Commands" section that can run in your environment (verify_docs, verify_bias_set, manage.py check, makemigrations --check, flake8, black, isort, mypy, bandit, full pytest if Docker works). Report exactly what ran and what did not.

Append a dated entry to HISTORY.md under "## 7. Batch log" with `cat >>`, do not read the file. Use the CLAUDE.md final report format, then stop.
```

---

## FIX-2: Token diet and one run rule

```text
Read CLAUDE.md. Documentation and tooling batch. No product code changes. FIX-1 must already be merged into main: check `git log` for it, else STOP. Work on a new branch `chore/token-diet`.

Problem: each session loads far too much. HISTORY.md is 354 KB, design.md 201 KB, the Arch Doc 190 KB, the Feasibility doc 168 KB, the Complete Doc 155 KB, prd.md 95 KB. One batch needs about 5% of that. The 99 specs for Phases 2 to 5 repeat boilerplate that contradicts CLAUDE.md.

1. Slim the specs. Run `python scripts/slim_prompts.py --dry-run`, then `python scripts/slim_prompts.py`. Confirm all of: 99 files rewritten; `git diff --stat -- 'docs/prompts/paste-ready/0.*' 'docs/prompts/paste-ready/1.*'` is empty (Phase 0 and 1 prompts must stay byte-identical); every rewritten file still has In scope, Out of scope and Done when; 2.30 and 5.1 still contain their "Gate: STOP" line. Report bytes before and after.
   Then run `python scripts/build_phase_prompts.py`. It copies the slimmed specs into the end of each group prompt in docs/prompts/PHASE_2.md to PHASE_5.md, so each prompt is self-contained (this also picks up the count fixes FIX-1 made in the specs, for example the table count in 2.30). Confirm a second run changes nothing, and that every fenced prompt now ends with its batch specs.
2. Create docs/CONTEXT.md. Target 25 KB, hard cap 30 KB. Condense from the canonical docs with section references; invent nothing.
   a. Five-line product summary. Point to CLAUDE.md for the invariants; do not copy them.
   b. All 63 REQ-FR as a table: ID | one-line text | status from TRACEABILITY.md | batch IDs that cover it.
   c. Table index: every CREATE TABLE in Arch Doc section 5.1 as name | one-line purpose | the exact grep that prints only that definition, e.g. `grep -n -A40 "CREATE TABLE candidate_resumes" FAIRFOLD_Project_Architecture_and_Requirements.md`. Do not paste the DDL.
   d. API index from Complete Doc section C.12: METHOD path | app | batch. One line each.
   e. Repo map: app directory to what lives there, read from the code (say which apps are empty).
   f. Current asserted counts (tables, FRs, FKs, indexes, wireframes) as verify_docs.py reports them.
3. Edit CLAUDE.md. Keep every line of "Privacy and fairness invariants", "Repo conventions that have already caused bugs" and "Commands" byte-for-byte. Change only these:
   a. Lines 3 and 4: batch prompts are now group prompts in docs/prompts/PHASE_<n>.md (the folder docs/prompts/ also has 00_FIX_CURRENT_STATE.md and README.md). Each group prompt already contains its batch specs, so the agent does not open docs/prompts/paste-ready/. Those files stay as the source that scripts/build_phase_prompts.py copies from.
   b. "Where truth lives": add as item 0 "docs/CONTEXT.md: read it first." Add: open a canonical doc only for the section a batch cites, using grep or `sed -n 'A,Bp'`; never read HISTORY.md, design.md, prd.md or the Feasibility doc whole.
   c. In "Working method", replace "One batch per session. Never start the next batch." with the section below, added as "## Group run rules":
      - A prompt names a group of batches, e.g. P2.1 = 2.1 to 2.5. The specs are inside the prompt; do not open docs/prompts/paste-ready/.
      - Do the batches in order, starting at the first one not `[x]` in docs/PROGRESS.md. Re-running a prompt resumes it.
      - After each batch: targeted tests, `manage.py check` (plus `makemigrations --check` if models changed), then the three progress updates. Then continue.
      - Stop at the first blocker, failing check, missing prerequisite or decision gate. Never start another group.
      - Run the full suite and all linters once at the end of the group.
      - One final report per group, with one section per batch.
   d. "Progress tracking": append to HISTORY.md with `cat >>` under "## 7. Batch log"; never read the whole file.
   Keep CLAUDE.md under 10 KB. Show `git diff CLAUDE.md` and confirm no line inside the three protected sections changed.
4. docs/ROADMAP.md, "how to run each batch" (around line 61): replace with: new session, paste one group prompt from docs/prompts/PHASE_<n>.md, review the diff, run the checks, merge. State that Phase 2 has 7 group prompts, Phase 3 has 5, Phase 4 has 4, Phase 5 has 4. Remove the instruction to paste files for the agent: it works inside the repo.
5. scripts/verify_docs.py: add a warning when CLAUDE.md exceeds 10 KB or docs/CONTEXT.md exceeds 30 KB. Run the script; it must pass.
6. Do not move or delete any document. If you think a move would help, say so under Observations.

Append a HISTORY.md entry (no PROGRESS line, this is not a numbered batch). Use the CLAUDE.md final report format, include byte sizes before and after for every file touched, then stop.
```
