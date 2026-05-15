# Weather Regressor for Revenue/Sessions Forecasting

**Date:** 2026-05-15
**Status:** Approved, ready for plan
**Scope:** Add daily weather (temperature, precipitation) as exogenous regressors to the Prophet and XGBoost forecasters. Inject weather effect into synthetic data so the model learns a coherent signal across the full 18-month training window.

## Motivation

Current weekly wMAPE: Revenue 29.7% (Prophet), Sessions 36.4% (SARIMA). Holiday calendar captures recurring date-driven peaks (Eid, New Year), but residual variance still includes day-to-day swings the calendar can't explain. Weather is the most common hidden regressor in retail/entertainment forecasting — rainy days dampen foot traffic, hot days push customers toward air-conditioned indoor venues. Tunis has both signals.

## Out of scope

- School calendar regressor — same wiring pattern, deferred to a follow-up round
- SARIMA exogenous variables — `auto_arima` supports `X=` but the complexity/gain trade-off is unfavorable for this round
- Members model regressor — weekly granularity dilutes daily weather signal
- Live weather API key management — Open-Meteo Archive API is keyless

## Architecture

Three components, one new module + edits to two existing modules.

```
Open-Meteo Archive API
       |
       v
gamefydb/weather.py        (NEW)
  fetch_weather(start, end) -> DataFrame[ds, temp_max_c, precip_mm]
  - caches to excel/weather_tunis.parquet
  - climatological fallback for dates beyond cache + forecast horizon
       |
       +--> gamefydb/data_generator.py   (EDIT)
       |      - applies weather multiplier to bootstrap revenue
       |      - regenerates extended_*.xlsx with weather-correlated synthetic data
       |
       +--> gamefydb/forecaster.py        (EDIT)
              - Prophet: add_regressor('temp_max_c') + add_regressor('precip_mm')
              - XGBoost: append columns to feature matrix
```

## Component 1: `gamefydb/weather.py`

**Public API:**

```python
def fetch_weather(start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """Return daily weather for Tunis. Columns: ds, temp_max_c, precip_mm."""
```

**Implementation:**

- Location: lat=36.8065, lon=10.1815 (Tunis)
- API: `https://archive-api.open-meteo.com/v1/archive` with `daily=temperature_2m_max,precipitation_sum`
- Cache: `excel/weather_tunis.parquet`
  - On call, load cache; determine missing date ranges in `[start, end]`; fetch only the gaps; append; rewrite parquet
  - Idempotent: re-running on same range hits API zero times
- Future-date fallback: for `ds > today`, compute climatological average — mean of `temp_max_c` and `precip_mm` grouped by `(month, day)` across all cached history. Returns the climatology row for those dates.

**Dependencies:** `requests`, `pandas`, `pyarrow` (for parquet). Add to `requirements.txt` if missing.

**Failure modes:** if the Open-Meteo request fails (network down, API hiccup), `fetch_weather` raises. No silent fallback — better to fail loudly than train on stale climatology.

## Component 2: `gamefydb/data_generator.py` edits

Inject weather multiplier into the synthetic bootstrap loop. The current loop samples a daily revenue from the real monthly DOW pool. The new step multiplies that sample by a weather factor.

**Multiplier function:**

```python
def _weather_multiplier(temp_max_c: float, precip_mm: float) -> float:
    mult = 1.0
    if precip_mm > 2.0:    mult *= 0.90
    if temp_max_c > 33.0:  mult *= 1.08
    return mult
```

Starting values are based on retail/entertainment foot-traffic literature. After the first end-to-end run, inspect Prophet's regressor coefficient and tune.

**Integration point:** inside the daily generation loop in `_generate_cash_synth` (or the equivalent function), look up that day's weather from a pre-fetched DataFrame and apply the multiplier before writing the synthetic transaction batch.

**Sessions synthetic data:** apply the same multiplier — precip effect on sessions is parallel to revenue. Members data is aggregate stats (no daily granularity), so it's unaffected. Stock data is unaffected.

**Regenerate `extended_*.xlsx`** after the edit. The pipeline already consumes these via `FILES` in `pipeline.py`.

## Component 3: `gamefydb/forecaster.py` edits

**Prophet (revenue + sessions models):**

```python
weather = fetch_weather(df['ds'].min(), df['ds'].max() + pd.Timedelta(days=forecast_horizon))
df = df.merge(weather, on='ds', how='left')
m.add_regressor('temp_max_c')
m.add_regressor('precip_mm')
m.fit(df)
future = future.merge(weather, on='ds', how='left')
forecast = m.predict(future)
```

**XGBoost (revenue + sessions models):** merge the same weather DataFrame onto the feature matrix; the existing `_holiday_proximity` path is the analog.

**SARIMA / members weekly model:** unchanged.

## Data flow

1. `weather.py` fetches/caches Tunis daily weather for the full date range needed.
2. `data_generator.py` consumes weather for Sep 2024 → Aug 2025 to inject the multiplier into synthetic revenue/sessions, regenerates `extended_*.xlsx`.
3. `pipeline.py` runs end-to-end; output schema unchanged.
4. `forecaster.py` consumes weather for the training window + forecast horizon as a Prophet regressor + XGBoost feature.
5. `figures.py` re-runs accuracy plots; new wMAPE numbers reported.

## Success criteria

- Revenue weekly wMAPE drops from 29.7% to ≤ 26% (Prophet)
- Sessions weekly wMAPE drops from 36.4% to ≤ 32% (Prophet or XGBoost)
- Prophet regressor coefficients have expected signs: `precip_mm` negative, `temp_max_c` positive

If thresholds aren't met after first run: tune multipliers in `_weather_multiplier`, or drop a feature whose coefficient is statistically zero.

## Testing

- `test_weather.py`: fetch a known historical week, assert cache file written, assert second call hits cache (mock requests)
- `test_data_generator.py`: assert weather multiplier is applied (synthetic revenue on a known rainy day < same date with `precip_mm=0`)
- `test_forecaster.py`: assert Prophet model includes `temp_max_c` and `precip_mm` regressors after fit

## Open items for tuning round

- Multiplier values are first guesses. After first run, inspect Prophet coefficient and reverse-engineer a better synthetic multiplier so synth and real coefficients agree.
- If `precip_mm` coefficient is near zero, drop it and keep only `temp_max_c`.
