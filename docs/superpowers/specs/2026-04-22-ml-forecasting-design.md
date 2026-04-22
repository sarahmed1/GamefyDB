# ML Forecasting & Bundle Suggestions — Design Spec
**Date:** 2026-04-22  
**Project:** GamefyDB (Pancafe ETL Pipeline)  
**Status:** Approved

---

## Overview

Add a machine learning module to the GamefyDB pipeline that:
1. **Forecasts future revenue** (next 4 weeks + next 3 months)
2. **Forecasts future member activity** (next 4 weeks + next 3 months)
3. **Suggests item bundles** — pairs slow-selling items with popular ones

All outputs are CSV files consumed by Power BI.

---

## Architecture

The ML module is a standalone 5th stage added after `writer.py`. It reads existing pipeline output CSVs and writes forecast CSVs to `output/forecasts/`.

```
output/facts/fact_transaction.csv  ─┐
output/facts/fact_session.csv      ─┤→ gamefydb/forecaster.py → output/forecasts/
output/dims/dim_item.csv           ─┘
```

**New file:** `gamefydb/forecaster.py`  
**New output directory:** `output/forecasts/`

The forecaster is triggered via `run.py` flags and is fully independent of the ingestion/cleaning/transformation stages.

---

## CLI Usage

```bash
# Full pipeline + forecast
python run.py --input excel --output output --forecast

# Forecast only (skips ingestion, reads existing CSVs)
python run.py --forecast-only
```

---

## Module 1: Revenue Forecasting (Prophet)

**Input:** `output/facts/fact_transaction.csv`  
**Aggregation:** Sum of `amount` grouped by calendar date (daily totals)  
**Model:** Facebook Prophet — learns daily trend + weekly seasonality  
**Horizon:** 28 days (weekly view) + 90 days (monthly view)  
**Training:** Full 7-month history, retrained on every run

**Output:** `output/forecasts/forecast_revenue.csv`

| Column | Description |
|--------|-------------|
| `date` | Forecast date |
| `granularity` | `weekly` or `monthly` |
| `yhat` | Predicted revenue (TND) |
| `yhat_lower` | Lower confidence bound (80%) |
| `yhat_upper` | Upper confidence bound (80%) |

---

## Module 2: Member Activity Forecasting (Prophet)

**Input:** `output/facts/fact_session.csv`  
**Aggregation:** Count of distinct `member_id` per day (non-null only — active members)  
**Model:** Facebook Prophet — same approach as revenue  
**Horizon:** 28 days (weekly) + 90 days (monthly)

**Output:** `output/forecasts/forecast_members.csv`

| Column | Description |
|--------|-------------|
| `date` | Forecast date |
| `granularity` | `weekly` or `monthly` |
| `yhat` | Predicted active member count |
| `yhat_lower` | Lower confidence bound (80%) |
| `yhat_upper` | Upper confidence bound (80%) |

---

## Module 3: Bundle Suggestions (FP-Growth / Association Rules)

**Goal:** Identify slow-selling items and pair each with the popular item most frequently bought in the same time window.

**Input:** `output/facts/fact_transaction.csv` + `output/dims/dim_item.csv`

**Algorithm:** FP-Growth (association rule mining via `mlxtend`)

**Process:**
1. Identify **top 5 most sold items** by quantity from `dim_item`
2. Identify **slow items** — items with quantity significantly below the median
3. Group transactions by date + hour to form "baskets" (items bought around the same time)
4. Mine association rules between slow items and popular items
5. For each slow item, output the best pairing (highest confidence)

**Output:** `output/forecasts/bundle_suggestions.csv`

| Column | Description |
|--------|-------------|
| `slow_item` | The underperforming item |
| `pair_with` | Recommended popular item to bundle with |
| `co_occurrence_pct` | % of slow item transactions where pair_with also appears |

---

## Dependencies

Add to `requirements.txt`:
```
prophet
mlxtend
```

Prophet requires `pystan` or `cmdstanpy` as a backend. `cmdstanpy` is recommended (lighter install).

---

## Power BI Integration

Power BI connects directly to the three forecast CSV files:
- `output/forecasts/forecast_revenue.csv` — line chart with confidence band using `yhat_lower`/`yhat_upper`
- `output/forecasts/forecast_members.csv` — same chart type
- `output/forecasts/bundle_suggestions.csv` — table or card visual

Workflow: re-run pipeline → refresh Power BI data source → charts update automatically.

---

## Extensibility

Everything in `forecaster.py` is parameterized. Future additions with minimal changes:
- Forecast by category (Computer vs. PlayStation vs. Orders)
- Forecast peak hours (busiest hour of day)
- Add more bundle targets (top 10 instead of top 5)
- Adjust confidence interval (default 80%, configurable)
- Adjust forecast horizon (weeks/months ahead)
