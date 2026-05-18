# April Data Validation — Notes

## What we want to do

When April Excel files arrive from the gaming center, use them to check how accurate the
already-generated forecasts were. This is a real out-of-sample test — the model never saw
April data.

## The key distinction

**Accuracy validation** (what we're doing):
- Model stays as-is, trained on Sep 2025 – Feb 2026
- Load actual April revenue/sessions/members
- Compare against `output/forecasts/forecast_revenue.csv` April rows (already generated)
- Calculate MAE/MAPE for April specifically
- Plot actual vs predicted → strong figure for the thesis

**Model retraining** (separate, optional, later):
- Add April data → retrain → now Ramadan 2026 is in training
- Add `is_ramadan` flag → Prophet learns the cultural seasonality
- Get better forecasts for future years
- This is a future improvement, not needed for the current thesis

## Why the current 50% MAPE is not "pointless"

- Naive baseline (predict same as last week) also hits 52.9% MAPE on same test period
- Test period was Ramadan 2026 (Feb 17 – Mar 18), which was never in training data
- Data only starts Sep 1, 2025 — Ramadan 2025 ended Mar 29, 2025, so zero Ramadan
  in training
- Models are at the ceiling for this data; methodology is sound

## What April validation would show

- If April MAPE is lower than 50% → confirms Ramadan was the outlier, not the model
- If April MAPE is similar → data is just noisy (gaming center daily revenue has CV=67%)
- Either way it's a valid thesis conclusion

## Files to get from the gaming center

Same 4 Excel files, extended with April rows:
- `Cash DATA 01-09-2025.xls`
- `DATA session reports 01-09-2025.xls`
- `Stock DATA 01-09-2025.xls`
- `memeber DATA 01-09-2025.xls`

Drop them in `excel/` folder. The pipeline handles the rest.

## Steps once April data arrives

1. Drop April Excel files in `excel/`
2. Run `python run.py --input excel --output output` — pipeline regenerates all CSVs
3. Load actual April revenue from output CSVs
4. Compare against existing `forecast_revenue.csv` April predictions
5. Generate a "forecast vs actual" validation figure
6. Add MAPE/MAE numbers to the thesis report

## Current model performance (for reference)

| Series | Winner | MAPE |
|--------|--------|------|
| Revenue | Prophet | 50.1% |
| Session volume | Prophet | 41.7% |
| Member activity | SARIMA | 45.8% |

ADF stationarity: all three series are stationary (p < 0.05).
