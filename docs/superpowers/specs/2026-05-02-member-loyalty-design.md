# Member Loyalty Scoring — Design Spec

**Date:** 2026-05-02
**Feature:** FM-based loyalty tier assignment for members

---

## Overview

Add a `score_member_loyalty()` function to `gamefydb/segmenter.py` that scores each member
on two RFM dimensions (Frequency and Monetary) and assigns a Bronze/Silver/Gold/Platinum
loyalty tier. The output is a new CSV `output/forecasts/member_loyalty.csv`.

This complements the existing K-means segmentation: K-means captures behavioral clusters
(spending pattern shape), loyalty scoring captures absolute value rank (how much a member
contributes to the business).

---

## Input

`dim_member` DataFrame — same input used by `segment_members()`.

Required columns: `member_id`, `username`, `firstname`, `lastname`, `total_tnd`, `duration_min`

---

## Algorithm

### 1. Filter
Remove members where both `total_tnd` and `duration_min` are zero (same guard as K-means).

### 2. Quartile scoring
Assign integer scores 1–4 using `pd.qcut` with `duplicates='drop'` and `labels=False`:

| Score | Meaning |
|---|---|
| 1 | Bottom 25% |
| 2 | 25–50th percentile |
| 3 | 50–75th percentile |
| 4 | Top 25% |

- **M score** — quartile rank of `total_tnd`
- **F score** — quartile rank of `duration_min` (proxy for visit frequency: more time spent = more visits)

### 3. FM composite score
`fm_score = m_score + f_score` — range 2–8

### 4. Tier mapping

| FM score | Tier |
|---|---|
| 2–3 | Bronze |
| 4–5 | Silver |
| 6–7 | Gold |
| 8 | Platinum |

---

## Output

Columns: `member_id`, `username`, `firstname`, `lastname`, `total_tnd`, `duration_min`,
`m_score`, `f_score`, `fm_score`, `loyalty_tier`

Sorted by `fm_score` descending.

Saved to: `output/forecasts/member_loyalty.csv`

---

## Integration in `run.py`

Call `score_member_loyalty(schema['dim_member'])` after `segment_members()`.
Print tier distribution (count per tier) to stdout.
Save output CSV alongside the other forecast CSVs.

---

## Edge Cases

- `pd.qcut` with `duplicates='drop'` handles the case where many members share the same
  value (e.g. all zeros in one column). Members that fall in a dropped bin get NaN score →
  fill with 1 (bottom tier).
- Members filtered out (all-zero) are excluded from the output entirely.

---

## Thesis Justification

> "In addition to K-means behavioral clustering, we apply an FM scoring model (a simplified
> RFM adapted to available data) to rank members by loyalty. Since individual visit timestamps
> are not available, Recency is omitted and Frequency is approximated by total time spent at
> the center. Each member receives a quartile score on Monetary value (total_tnd) and
> Frequency proxy (duration_min), combined into a composite FM score mapped to four loyalty
> tiers: Bronze, Silver, Gold, and Platinum."
