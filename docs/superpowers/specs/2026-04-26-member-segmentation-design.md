# Member Segmentation Design

**Date:** 2026-04-26
**Feature:** K-means clustering on gaming center members

## Goal

Segment members into behaviorally distinct groups using unsupervised clustering, so the business can identify high-value customers, casual visitors, and inactive members. Output is a CSV ready for Power BI import.

## Data

Source: `dim_member` table produced by the existing pipeline.

Features used for clustering:
- `total_tnd` — total money spent at the center
- `duration_min` — total time spent (usage proxy)
- `orders_tnd` — food/drink order spend

Excluded: `usb_tnd` (always empty), `usage_tnd` (overlaps with total_tnd), name/id fields (non-numeric).

Members with all three features missing or zero are dropped before clustering.

## Algorithm

**K-means clustering, k=4.**

Rationale:
- K-means is interpretable, well-known, and appropriate for this feature set
- k=4 produces four meaningful business segments without over-fragmenting the data
- Fixed k keeps the output stable and explainable in the thesis

Preprocessing: `StandardScaler` normalization applied before clustering — required because K-means is distance-based and the three features have very different scales (TND amounts vs minutes).

## Segments

Cluster labels are assigned post-fit based on which feature dominates the cluster centroid:

| Label | Profile |
|-------|---------|
| Heavy Users | High time + high spend |
| Casual Spenders | Lower time, higher orders relative to usage |
| Regulars | Balanced across all three features |
| Light Users | Low across all features |

Labels are heuristic — assigned by comparing each cluster's centroid against the others. If two clusters are ambiguous, the one with higher total_tnd gets the higher-value label.

## Module

**File:** `gamefydb/segmenter.py`

**Function:** `segment_members(dim_member: pd.DataFrame) -> pd.DataFrame`

- Input: `dim_member` DataFrame from `pipeline.run_pipeline()`
- Output: same columns + `cluster_id` (int) + `segment_label` (str)
- No side effects — pure function, no file I/O

## Integration

**In `run.py`:**
1. Call `segment_members(schema['dim_member'])`
2. Write result to `output/forecasts/member_segments.csv`
3. Print segment summary (label + count per group)

Output location is `output/forecasts/` alongside the forecast CSVs (not `output/powerbi_star/`) since this is an analytical output, not a dimension table.

## Output CSV Columns

`member_id, username, firstname, lastname, total_tnd, duration_min, orders_tnd, cluster_id, segment_label`

## Dependencies

- `scikit-learn` — `KMeans`, `StandardScaler` (add to `requirements.txt`)
