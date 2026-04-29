# Anomaly Detection — Design Spec
_2026-04-29_

## Overview

Add a Z-score anomaly detection module that flags statistically unusual days across three time series: revenue, session volume, and member activity. Each series is evaluated independently. Within each series, each day is compared against other days of the same weekday (Monday vs Mondays, Sunday vs Sundays) to account for the natural weekly seasonality of a gaming center.

Output: a printed summary during pipeline run + `output/forecasts/anomalies.csv` for Power BI.

---

## Method — Day-of-Week Z-Score

For each series and each weekday group:
1. Compute `mean` and `std` of all historical values for that weekday (e.g. all Mondays in the dataset)
2. For each day, compute `z_score = (actual - mean) / std`
3. Flag the day if `|z_score| >= 2.0`

**Threshold:** 2.0σ — flags roughly the most unusual 5% of days per weekday group. Days beyond 3.0σ are marked severe.

**Minimum group size:** a weekday group needs at least 4 data points to compute a meaningful std. Groups with fewer points are skipped (not flagged).

---

## New File — `gamefydb/anomaly_detector.py`

Single public function:

```
detect_anomalies(transactions_df: pd.DataFrame) -> pd.DataFrame
```

### Input
`transactions_df` — the cleaned cash transactions DataFrame (same input used by `forecast_revenue` and `forecast_session_volume`). Contains `transaction_datetime`, `amount_tnd`, `income_expense`, `transaction_type` columns.

### Internal series built from transactions_df
- **Revenue** — daily sum of `amount_tnd` where `income_expense == 'Income'`
- **Session volume** — daily count of all rows
- **Member activity** — daily count of rows where `transaction_type == 'Member Transactions'`

All three series are built using the same `_to_daily()` helper already in `forecaster.py` (imported, not duplicated).

### Output DataFrame columns

| Column | Type | Description |
|--------|------|-------------|
| `date` | date | The flagged date |
| `series` | str | `revenue` / `session_volume` / `member_activity` |
| `weekday` | str | e.g. `Monday` |
| `actual` | float | Observed value that day |
| `weekday_mean` | float | Mean of all same-weekday values (historical) |
| `weekday_std` | float | Std of all same-weekday values (historical) |
| `z_score` | float | (actual − mean) / std, rounded to 2 dp |
| `direction` | str | `high` or `low` |
| `severity` | str | `mild` (2–3σ) or `severe` (>3σ) |

Sorted by `z_score` absolute value descending (most extreme first).

---

## Console Output (printed by `run.py`)

```
Anomaly detection...
  [Revenue]         3 anomalies — 1 severe, 2 mild
    Worst: 2025-02-10 Mon  actual=85 TND  expected=430 TND  z=-4.1 (severe, low)
  [Session volume]  2 anomalies — 0 severe, 2 mild
    Worst: 2025-03-22 Sat  actual=178     expected=92       z=+2.4 (mild, high)
  [Member activity] 1 anomaly  — 1 severe, 0 mild
    Worst: 2025-01-05 Sun  actual=0       expected=38       z=-3.8 (severe, low)
```

---

## CSV Output

Path: `output/forecasts/anomalies.csv`

All flagged rows from all three series combined. Same columns as the output DataFrame above. Power BI can filter by `series`, `severity`, or `direction`.

---

## Integration — `run.py`

After the existing forecasting section, add:

```python
from gamefydb.anomaly_detector import detect_anomalies

print('\nAnomaly detection...')
anomalies = detect_anomalies(transactions_df)
# print summary per series
writer.write_anomalies(anomalies, output_dir)
```

`writer.py` gets a new `write_anomalies()` function following the same pattern as existing write functions.

---

## `ml_choices_explained.md` Addition

New section (section 11): **Anomaly Detection — Z-Score (Day-of-Week)**

Covers:
- What Z-score is and the formula
- Why day-of-week grouping (weekly seasonality at a gaming center)
- Threshold choice (2σ) and severity split (mild / severe)
- Alternatives considered: rolling Z-score (needs more data), Isolation Forest (overkill, harder to explain), Prophet residuals (ties detection to forecast model)

---

## Tests — `tests/test_anomaly_detector.py`

| Test | What it checks |
|------|----------------|
| Normal data returns empty DataFrame | No false positives on flat series |
| One spike detected correctly | A day at 3σ above mean is flagged as severe/high |
| One dip detected correctly | A day at 2.5σ below mean is flagged as mild/low |
| Series isolation | Anomaly in revenue does not appear in session_volume rows |
| Small group skipped | Weekday with < 4 points produces no flags |
| Output columns present | All 9 required columns exist in output |
| Sorted by abs z_score desc | Most extreme row is first |

---

## Out of Scope

- No anomaly detection on stock movements or member segments (different data shape, no time series)
- No alerting or notifications — output is CSV + console only
- No rolling/adaptive baseline — global weekday mean is sufficient for 7 months of data
