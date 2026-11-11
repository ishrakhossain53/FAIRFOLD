# Prompts: how to use

22 prompts replace the old one-prompt-per-batch flow (150 batches). Phase 0 and Phase 1 specs are unchanged.

| Phase | Prompts | Batches | File |
|---|---|---|---|
| Fix | FIX-1, FIX-2 | repo and doc state | `00_FIX_CURRENT_STATE.md` |
| 0, 1 | done | 0.1 to 1.50 | `paste-ready/0.*`, `paste-ready/1.*` (unchanged) |
| 2 | P2.1 to P2.7 | 2.1 to 2.43 | `PHASE_2.md` |
| 3 | P3.1 to P3.5 | 3.1 to 3.33 | `PHASE_3.md` |
| 4 | P4.1 to P4.4 | 4.1 to 4.17 | `PHASE_4.md` |
| 5 | P5.1 to P5.4 | 5.1 to 5.6 | `PHASE_5.md` |

## Run loop (every prompt)

1. Fresh agent session on a new branch (`mvp/p2-1` or similar), from an up-to-date `main`.
2. Paste the prompt from its fenced block.
3. Read the final report and `git diff`. Run the checks yourself.
4. Merge, then start the next prompt.

Rules that make this cheap:

- A prompt resumes at the first batch not `[x]` in `docs/PROGRESS.md`. If a session runs out of room or stops at a blocker, paste the same prompt again in a new session.
- Planned stops: P2.6 at 2.30 and P5.1 at 5.1 (decision batches). Record your answer in `docs/DECISIONS.md`, then re-run the prompt.
- Do not start P2.1 until FIX-1 and FIX-2 are merged. The group prompts depend on `docs/CONTEXT.md` and the Group run rules that FIX-2 adds to `CLAUDE.md`.
- Each prompt is self-contained: its batch specs (scope, out of scope, done-when, warnings) are at the end of the fenced block. Paste the whole block.
- The embedded specs are generated. If you edit a spec in `paste-ready/`, run `python scripts/build_phase_prompts.py` to refresh the phase files (run `python scripts/slim_prompts.py` first if the spec still has the old boilerplate).
