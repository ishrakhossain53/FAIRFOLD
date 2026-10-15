# Willingness-to-Pay Module

**Document:** `validation/willingness_to_pay.md`  
**Date:** 2026-10-13  
**Purpose:** Estimate price sensitivity for FairFold employer plans. Uses Joanne Pedersen's price sensitivity meter and tier comparison.

**⚠️ Do not anchor on the USD tables in prd.md §15.2.** Prices are [Planned: set after validation results]. BDT conversion is not yet known.

---

## Method 1: Price Sensitivity Meter

Present these four questions to recruiters. Use Joanne Pedersen's scale: **Too cheap / Bargain / Getting expensive / Too expensive**.

> **Instructions to interviewer:** "Imagine you're shopping for a screening tool. I'll give you four price points. Tell me where each feels -- not what you'd definitely buy, but what you're thinking just looking at the number."

### Questions

1. **"If FairFold cost 50 BDT per month, how would you feel?"**
   - Too cheap
   - Bargain
   - Getting expensive
   - Too expensive
   - Not sure / Depends on features

2. **"If FairFold cost 500 BDT per month (≈ $5), how would you feel?"**
   - Too cheap
   - Bargain
   - Getting expensive
   - Too expensive
   - Not sure / Depends on features

3. **"If FairFold cost 2,500 BDT per month (≈ $25), how would you feel?"**
   - Too cheap
   - Bargain
   - Getting expensive
   - Too expensive
   - Not sure / Depends on features

4. **"If FairFold cost 5,000 BDT per month (≈ $50), how would you feel?"**
   - Too cheap
   - Bargain
   - Getting expensive
   - Too expensive
   - Not sure / Depends on features

---

## Method 2: Per-Job vs Per-Month vs Per-Hire Comparison

Present this tier comparison and ask:

> "Imagine you have three options. Rank them by what feels most valuable for your budget."

### Tier comparison

| Tier | Price | What you get |
|---|---|---|
| **Free** | 0 BDT/month | 3 jobs, 50 AI screens, candidate list |
| **Starter** | 1,000 BDT/month | 50 jobs, 500 AI screens, basic analytics |
| **Pay-per-job** | 200 BDT/sealed screening | Full features for one role's applications |

> "Which pricing model appeals to you most, and why?"

**Probes:**
- "Do you prefer predictable monthly cost or pay-as-you-go?"
- "What's your budget cycle like (monthly, per-hire, quarterly)?"
- "How many roles do you typically fill in a month?"

---

## What to record

| Field | Example |
|---|---|
| Code | R01 |
| PSM-Q1 | Bargain |
| PSM-Q2 | Bargain |
| PSM-Q3 | Getting expensive |
| PSM-Q4 | Too expensive |
| Preference | Monthly (predictability) |
| Jobs/month | 3–5 |
| Current tool cost | "Free + 20 hours HR time" |
| Notes | "500 BDT feels right for a startup" |

---

## Analysis guide

**Price sensitivity interpretation:**

- **>60% say "Too cheap" at any price** → Price is above market, consider lowering
- **>50% say "Bargain" + >30% say "Getting expensive" at 500–1000 BDT** → Sweet spot likely there
- **>40% say "Too expensive" at 2500 BDT** → Consider smaller companies not willing to pay
- **"Per-job" preferred by >50%** → Consider pay-as-you-go option

**Tier boundaries (to be set from results):**

- **Free:** 3 jobs, 50 screens (unchanged)
- **Starter:** [Planned: BDT 800–1,200/month]
- **Growth:** [Planned: BDT 3,000–5,000/month]
- **Scale:** [Planned: BDT 8,000–15,000/month]

---

## Anchor questions (use sparingly)

If a participant mentions price unprompted:

> "What would you expect to pay for a tool that saves 2 hours of screening per role?"

> "How does this compare to what you currently spend on hiring tools?"

**Do not lead with "Would you pay $X/month for this?"** that's a direct anchor.

---

## Exit question

> "If we launched tomorrow with these prices, would you purchase a Starter plan for your company within the next month?"

- Yes
- Maybe (need to check budget)
- No (not in my budget)
- No (don't think I'd use it)