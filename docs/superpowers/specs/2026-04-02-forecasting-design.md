# GamefyDB Forecasting Module — Design Spec
**Date:** 2026-04-02

## Overview

A Prophet-based time series forecasting module that reads the GamefyDB pipeline's star-schema output and produces two forecasts:

1. **Per-item consumption** — predicted daily/weekly quantity sold (`Out` movements) per stock item, with confidence intervals.
2. **Revenue** — predicted total daily/weekly income in TND, from two complementary views: a direct Prophet model on `fact_cash_transactions` and a derived estimate computed as `Σ(predicted_qty × avg_unit_price)` per item.

Output is written as CSV files, a single Excel workbook, and a printed terminal summary.

---

## Why Prophet

The dataset spans ~7 months of daily transactional data (~210 days). Key characteristics:

- **Per-item daily data is sparse** — `fact_stock_movements` has ~2,370 rows across an estimated 15–30 unique items, meaning many items average fewer than 10 sales per day. Zero-sale days are common.
- **Weekly seasonality is the dominant signal** — a gaming center has a strong weekday/weekend pattern. Prophet detects this automatically from daily data with no manual configuration.
- **Short history** — ~210 days is not enough for a global LightGBM model to generalise reliably across items (LightGBM needs more data to avoid overfitting lag features on a small multi-series dataset). Prophet fits one model per series and is well-calibrated at this scale.
- **Confidence intervals matter** — inventory planning requires a range ("expect 5–9 units of Soda next week"), not just a point estimate. Prophet's uncertainty intervals are native and interpretable.
- **Maintainability** — Prophet requires no feature engineering. A non-data-scientist can read and understand the forecasting code. LightGBM would require lag columns, rolling windows, and careful cross-validation to avoid leakage.

LightGBM would be the better choice if the dataset grew to 2+ years with 50+ items. ARIMA was ruled out because it requires manual stationarity testing per item and does not scale cleanly to 15–30 series.

---

## Project Integration

Follows the existing `gamefydb/` module pattern:

```
gamefydb/
    ingestor.py       (existing)
    cleaner.py        (existing)
    transformer.py    (existing)
    writer.py         (existing)
    forecaster.py     ← NEW

run.py                (existing — ETL pipeline)
forecast.py           ← NEW CLI entry point
tests/
    test_forecaster.py ← NEW
```

The forecasting module is independent of the ETL pipeline at runtime — it reads the pipeline's CSV output directly and can be run any time after `run.py` has produced the output files.

---

## Data Sources

Reads three files from the pipeline's `output/` directory:

| File | Used for |
|---|---|
| `output/facts/fact_stock_movements.csv` | Item consumption series (`in_out = 'Out'`) |
| `output/facts/fact_cash_transactions.csv` | Revenue series (`income_expense = 'Income'`) |
| `output/dims/dim_item.csv` | Item name lookup for labelling output |

---

## Architecture & Data Flow

```
output/dims/dim_item.csv
output/facts/fact_stock_movements.csv     ──► prepare_consumption_series()
output/facts/fact_cash_transactions.csv   ──► prepare_revenue_series()
                                               │
                                    Prophet (one model per item
                                     + one model for total revenue)
                                               │
                          ┌────────────────────┼─────────────────────┐
              forecast_consumption.csv    forecast_revenue.csv    terminal summary
              (+ Excel sheet)             (+ Excel sheet)         (stdout)
```

---

## Module: `gamefydb/forecaster.py`

### Functions

| Function | Signature | Returns |
|---|---|---|
| `load_data` | `(output_dir: str) → dict` | `{'stock': df, 'cash': df, 'items': df}` |
| `prepare_consumption_series` | `(stock: df, items: df) → tuple` | `({item_name: daily_qty_Series}, [skipped_item_names])` — DatetimeIndex, zeros filled |
| `prepare_revenue_series` | `(cash: df) → Series` | Daily total income Series — DatetimeIndex |
| `fit_prophet` | `(series: Series, horizon: int, freq: str) → df` | Forecast DataFrame: `ds`, `yhat`, `yhat_lower`, `yhat_upper` |
| `forecast_all` | `(output_dir, horizon, freq, forecast_dir) → dict` | All result DataFrames; side-effects: writes files, prints summary |

### `load_data`

Reads the three CSV files from `output_dir`. Raises `FileNotFoundError` with the message `"Run the pipeline first: python run.py"` if any file is missing.

### `prepare_consumption_series`

1. Filter `stock` to `in_out == 'Out'`.
2. Join `item_id` → `item_name` via `dim_item`.
3. Group by `(movement_datetime.date, item_name)`, sum `quantity`.
4. Reindex to a full daily DatetimeIndex (pipeline date range), fill missing days with 0.
5. Return one Series per item. Items with fewer than **14 non-zero periods** (after resampling to `freq`) are excluded; they are collected into a `skipped_items` list returned alongside the dict.

### `prepare_revenue_series`

1. Filter `cash` to `income_expense == 'Income'`.
2. Group by `transaction_datetime.date`, sum `amount_tnd`.
3. Reindex to full daily DatetimeIndex, fill missing days with 0.
4. If the resulting Series is all zeros, raise `ValueError("No income data found in fact_cash_transactions")`.

### `fit_prophet`

1. **Resample** the input Series to `freq` before fitting — Prophet must be trained at the same granularity as the forecast (`'D'` = daily sum, `'W'` = weekly sum). Passing daily data with `freq='W'` to `make_future_dataframe` produces a model/forecast mismatch.
2. Build a Prophet-compatible DataFrame: `ds` = date, `y` = value.
3. Instantiate `Prophet(weekly_seasonality=True, daily_seasonality=False, yearly_seasonality=False)`.
   - Yearly seasonality disabled — 7 months is not enough data to fit a reliable yearly cycle.
   - Weekly seasonality is the dominant signal for a gaming center (weekday/weekend pattern).
4. Suppress Prophet's verbose INFO logs: `logging.getLogger('prophet').setLevel(logging.WARNING)` and `logging.getLogger('cmdstanpy').setLevel(logging.WARNING)` before fitting.
5. Fit on the full resampled series.
6. Call `make_future_dataframe(periods=horizon, freq=freq)`.
7. Predict and return the forecast slice (future periods only, i.e. rows where `ds > max training date`).
8. Clamp `yhat`, `yhat_lower`, `yhat_upper` to ≥ 0 (quantities and revenue cannot be negative).

### `forecast_all`

Orchestrates the full run:

1. `load_data` → `prepare_consumption_series` → `prepare_revenue_series`
2. Call `fit_prophet` for each item series + for the revenue series.
3. Compute `avg_unit_price` per item from historical `unit_price_tnd` (mean of non-zero values).
4. Compute `derived_revenue_tnd = Σ(predicted_qty × avg_unit_price)` per date across all forecast items.
5. Assemble `forecast_consumption` and `forecast_revenue` DataFrames (schemas below).
6. Write CSV + Excel + print terminal summary.
7. Return `{'consumption': df, 'revenue': df}`.

---

## Output Schema

### `forecast_consumption.csv` / `Consumption` sheet

| Column | Type | Notes |
|---|---|---|
| `date` | date | Forecast date |
| `item_name` | str | e.g. `Soda` |
| `predicted_qty` | float | `yhat`, clamped ≥ 0 |
| `lower_qty` | float | `yhat_lower`, clamped ≥ 0 |
| `upper_qty` | float | `yhat_upper`, clamped ≥ 0 |

### `forecast_revenue.csv` / `Revenue` sheet

| Column | Type | Notes |
|---|---|---|
| `date` | date | Forecast date |
| `direct_revenue_tnd` | float | Prophet on `fact_cash_transactions` income |
| `direct_lower_tnd` | float | Lower confidence bound |
| `direct_upper_tnd` | float | Upper confidence bound |
| `derived_revenue_tnd` | float | `Σ(predicted_qty × avg_unit_price)` — item sales only |

`direct_*` covers all revenue (sessions + item sales). `derived_*` covers item sales only. Both are included so the user can see the full picture.

### Excel

Single workbook: `output/forecasts/forecast.xlsx`
- Sheet `Consumption` — `forecast_consumption` table
- Sheet `Revenue` — `forecast_revenue` table

### Terminal Summary

Printed after writing files. Contains:
- Top 10 items by total predicted consumption over the horizon (tabulated)
- Total predicted direct revenue and range over the horizon
- List of skipped items (< 14 non-zero days) with day counts

---

## CLI: `forecast.py`

```
python forecast.py                            # 30-day daily forecast, default paths
python forecast.py --horizon 14               # 14-day forecast
python forecast.py --freq W                   # weekly granularity
python forecast.py --input output/            # custom pipeline output directory
python forecast.py --output output/forecasts/ # custom forecast output directory
```

| Argument | Default | Type | Notes |
|---|---|---|---|
| `--input` | `output/` | str | Pipeline CSV output directory |
| `--output` | `output/forecasts/` | str | Forecast output directory |
| `--horizon` | `30` | int | Periods ahead to forecast |
| `--freq` | `D` | str | `D` = daily, `W` = weekly |

Mirrors the structure and argument naming of `run.py`.

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| Pipeline CSVs missing | `FileNotFoundError`: `"Run the pipeline first: python run.py"` |
| `prophet` not installed | `ImportError` with message: `"Install prophet: pip install prophet"` |
| Revenue series is all zeros | `ValueError`: `"No income data found in fact_cash_transactions"` |
| Item has < 14 non-zero days | Skip silently, add to `skipped_items` list, print in terminal summary |
| `yhat` / bounds < 0 | Clamp to 0 |

---

## Testing: `tests/test_forecaster.py`

All tests use synthetic DataFrames — no dependency on the actual Excel files.

| Test | Verifies |
|---|---|
| `test_prepare_consumption_series_aggregates_correctly` | Daily `Out` quantities are summed correctly; `In` rows excluded |
| `test_prepare_consumption_series_fills_zeros` | Missing dates in the range are filled with 0 |
| `test_prepare_revenue_series_income_only` | Only `Income` rows included; `Expense` rows excluded |
| `test_fit_prophet_output_shape` | Forecast has exactly `horizon` rows; required columns present |
| `test_fit_prophet_clamps_negatives` | `yhat`, `yhat_lower`, `yhat_upper` are all ≥ 0 |
| `test_sparse_item_excluded` | Item with < 14 non-zero days appears in `skipped_items`, not in results |

---

## Dependencies

Added to `requirements.txt`:

```
prophet
```

Prophet pulls in `pystan` or `cmdstanpy` as a backend. No other new dependencies required — pandas and openpyxl are already in the project.
