# Pre-Commitment Ask — Validation Kit

**Document:** `validation/pre_commitment_ask.md`  
**Date:** 2026-10-13  
**Purpose:** Ladder of real commitments beyond stated interest. Used to predict actual adoption.

---

## The Commitment Ladder

Each rung is a stronger commitment than the last. Count commitments above stated interest.

| Ladder rung | Commitment type | What we ask |
|---|---|---|
| 1 | Second meeting | "Can we schedule a 15-minute follow-up next week?" |
| 2 | Share job description | "Can you share a real job description we can demo this on?" |
| 3 | Run a pilot | "Would you let us run this on one live role, with your real applicants?" |
| 4 | Letter of intent | "Would you sign a one-page letter saying you'll purchase if the pilot works?" |

---

## Scoring Rule

**Commitments count, not interest.**

For each participant, track:

- **Stated interest:** "This sounds interesting" or "I'd consider it"
- **Strong commitment:** "Yes, let's do it" or signing something
- **Conditional commitment:** "If X, then yes" (count only if X is achievable)

**Scoring:**

| Score | Meaning |
|---|---|
| 0 | Only stated interest |
| 1 | Second meeting agreed |
| 2 | Shared job description or pilot candidate |
| 3 | Pilot willing / LOI conditional |
| 4 | Letter of intent signed |

---

## How to ask

Use the ladder progressively. Don't jump to LOI on first interview.

### First interview close:

> "Based on what we've discussed, would you be open to a second, shorter session where we walk through the actual UI designs?"

### After showing wireframes:

> "Could you share a real job description we could run through this flow? It doesn't have to be live production."

### If they like the demo:

> "Would you be willing to run this on one role at your company? We'd use your real applicants and you'd see the full screening flow."

### If the pilot goes well:

> "We'd like to offer you early access. Would you sign a letter of intent to purchase when we launch? It just confirms your commitment to try it."

---

## Track in results.md

| Code | Q1: 2nd meet | Q2: Job desc | Q3: Pilot | Q4: LOI | Score | Notes |
|---|---|---|---|---|---|---|
| R01 | Yes | Shared | Yes | No (need budget) | 2 | Started strong |
| R02 | Maybe | No | No | — | 0 | Hesitant on pilot |

---

## What counts as NOT a commitment

- "I'll think about it"
- "Let me check with my team" (without follow-up scheduled)
- Vague interest: "This could be useful someday"
- Conditional with impossible criteria: "If you add feature X, Y, Z"

---

## Exit script

At the end of the interview, say:

> "To recap, this is what I heard:
> - You can see the problem [briefly restate their pain point]
> - The solution addresses it through [anonymised screening / assessment gating]
> - You're interested in [specific aspect they liked]
> 
> The next step for us is to validate whether this translates to adoption. Would you be open to a second, shorter session next week?"

Then wait for the answer. Note whether they say yes, maybe, or no.

---

## Open question for founder

**What threshold of commitments do you need to feel confident about moving to Phase 3?**

Options to consider:
- 2/6 participants at score ≥2
- 1/6 at score ≥3
- Every recruiters at score ≥1
- No one at score ≥4 (pilot phase)
- [Planned: founder must confirm]

This is a **go/adjust/stop** decision point. Document the answer in this file or in the decision rules.