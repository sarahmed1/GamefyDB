# Weather Regressor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add daily Tunis weather (temp_max_c, precip_mm) as Prophet + XGBoost regressors for revenue/sessions forecasting, with weather effect injected into synthetic data.

**Architecture:** New `gamefydb/weather.py` fetches and caches Open-Meteo data. `data_generator.py` applies a weather multiplier to the synthetic bootstrap. `forecaster.py` adds the regressors to Prophet and XGBoost.

**Tech Stack:** Open-Meteo Archive API, requests, pyarrow (parquet cache), Prophet `add_regressor`, XGBoost features.

---

## Task 1: Build `gamefydb/weather.py`

**Files:**
- Create: `gamefydb/weather.py`
- Modify: `requirements.txt` (add `pyarrow` if missing)

- [ ] **Step 1: Create the module**

```python
"""Daily weather for Tunis from Open-Meteo. Cached locally so repeated runs hit the API zero times."""

import os
from pathlib import Path
import pandas as pd
import requests

TUNIS_LAT = 36.8065
TUNIS_LON = 10.1815
ARCHIVE_URL = 'https://archive-api.open-meteo.com/v1/archive'
FORECAST_URL = 'https://api.open-meteo.com/v1/forecast'
CACHE_PATH = Path('excel') / 'weather_tunis.parquet'


def _load_cache() -> pd.DataFrame:
    if CACHE_PATH.exists():
        df = pd.read_parquet(CACHE_PATH)
        df['ds'] = pd.to_datetime(df['ds'])
        return df.sort_values('ds').reset_index(drop=True)
    return pd.DataFrame(columns=['ds', 'temp_max_c', 'precip_mm'])


def _save_cache(df: pd.DataFrame) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.sort_values('ds').reset_index(drop=True).to_parquet(CACHE_PATH, index=False)


def _fetch_range(url: str, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    params = {
        'latitude': TUNIS_LAT, 'longitude': TUNIS_LON,
        'start_date': start.strftime('%Y-%m-%d'),
        'end_date':   end.strftime('%Y-%m-%d'),
        'daily': 'temperature_2m_max,precipitation_sum',
        'timezone': 'Africa/Tunis',
    }
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()['daily']
    return pd.DataFrame({
        'ds':         pd.to_datetime(data['time']),
        'temp_max_c': data['temperature_2m_max'],
        'precip_mm':  data['precipitation_sum'],
    })


def _climatology(cache: pd.DataFrame, dates: pd.DatetimeIndex) -> pd.DataFrame:
    """Return mean temp/precip by (month, day) for fallback on dates beyond available data."""
    src = cache.copy()
    src['_mo'] = src['ds'].dt.month
    src['_dy'] = src['ds'].dt.day
    clim = src.groupby(['_mo', '_dy'])[['temp_max_c', 'precip_mm']].mean().reset_index()
    out = pd.DataFrame({'ds': dates})
    out['_mo'] = out['ds'].dt.month
    out['_dy'] = out['ds'].dt.day
    out = out.merge(clim, on=['_mo', '_dy'], how='left')
    # If even climatology has gaps (cache empty), fill neutrally
    out['temp_max_c'] = out['temp_max_c'].fillna(20.0)
    out['precip_mm']  = out['precip_mm'].fillna(0.0)
    return out[['ds', 'temp_max_c', 'precip_mm']]


def fetch_weather(start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """Return daily Tunis weather for [start, end] inclusive.

    Strategy:
      1. Load cache.
      2. For dates ≤ today not in cache → fetch from Archive API.
      3. For dates > today → use climatological fallback from cache history.
    """
    start = pd.Timestamp(start).normalize()
    end   = pd.Timestamp(end).normalize()
    today = pd.Timestamp.today().normalize()

    cache = _load_cache()
    cached_dates = set(cache['ds'].dt.normalize()) if not cache.empty else set()

    # Determine historical range to fetch (anything ≤ today not in cache)
    hist_end = min(end, today)
    if start <= hist_end:
        all_hist = pd.date_range(start, hist_end, freq='D')
        missing  = [d for d in all_hist if d not in cached_dates]
        if missing:
            fetch_start = pd.Timestamp(min(missing))
            fetch_end   = pd.Timestamp(max(missing))
            new_rows = _fetch_range(ARCHIVE_URL, fetch_start, fetch_end)
            cache = pd.concat([cache, new_rows], ignore_index=True).drop_duplicates('ds')
            _save_cache(cache)

    # Slice cache to requested range
    requested = pd.date_range(start, end, freq='D')
    result = cache[cache['ds'].isin(requested)].copy()

    # Fill future dates (> today) with climatology
    future_dates = requested[requested > today]
    if len(future_dates) > 0:
        clim = _climatology(cache, future_dates)
        result = pd.concat([result, clim], ignore_index=True)

    return result.sort_values('ds').reset_index(drop=True)


def weather_multiplier(temp_max_c: float, precip_mm: float) -> float:
    """Revenue multiplier for synthetic data injection."""
    mult = 1.0
    if precip_mm > 2.0:    mult *= 0.90
    if temp_max_c > 33.0:  mult *= 1.08
    return mult
```

- [ ] **Step 2: Ensure `pyarrow` is in requirements**

Check `requirements.txt` for `pyarrow`. If not present, append it.

- [ ] **Step 3: Smoke-test the module**

Run:
```
C:/Users/sarah/AppData/Local/Python/bin/python -c "import pandas as pd; from gamefydb.weather import fetch_weather; print(fetch_weather(pd.Timestamp('2024-09-01'), pd.Timestamp('2024-09-07')))"
```
Expected: 7-row DataFrame with non-null `temp_max_c` and `precip_mm`. Re-run should be instant (cache hit).

- [ ] **Step 4: Commit**
```
git add gamefydb/weather.py requirements.txt
git commit -m "feat: add weather.py module with Open-Meteo fetch + parquet cache"
```

---

## Task 2: Inject weather multiplier into `data_generator.py`

**Files:**
- Modify: `gamefydb/data_generator.py` (top imports, `generate_cash`, `generate_sessions`, `generate_all`)

- [ ] **Step 1: Add import + lookup helper**

After existing imports near the top, add:
```python
from gamefydb.weather import fetch_weather, weather_multiplier
```

Right above `def generate_cash`, add:
```python
def _weather_lookup(start: pd.Timestamp, end: pd.Timestamp) -> dict:
    """Return {date -> (temp_max_c, precip_mm)} dict for the range."""
    w = fetch_weather(start, end)
    return {pd.Timestamp(r.ds).normalize(): (float(r.temp_max_c), float(r.precip_mm))
            for r in w.itertuples()}
```

- [ ] **Step 2: Inject in `generate_cash`**

Change `generate_cash` signature to accept a `weather` dict:
```python
def generate_cash(start: pd.Timestamp, end: pd.Timestamp,
                  daily_pool=None, weather: dict | None = None) -> pd.DataFrame:
```

Right after the `event_mul = holiday_mul * ramadan_mul * eid_week_mul` line (around line 356), add:
```python
        if weather is not None and day.normalize() in weather:
            t, p = weather[day.normalize()]
            event_mul *= weather_multiplier(t, p)
```

- [ ] **Step 3: Inject in `generate_sessions`**

Same pattern. Change signature:
```python
def generate_sessions(start: pd.Timestamp, end: pd.Timestamp,
                      weather: dict | None = None) -> pd.DataFrame:
```

After `event_mul = holiday_mul * ramadan_mul * eid_week_mul` (around line 410), insert the same 3-line lookup-and-multiply block.

- [ ] **Step 4: Wire into `generate_all`**

In `generate_all` near line 721 (after `synth_start` / `synth_end` are defined), add:
```python
    weather = _weather_lookup(synth_start, synth_end)
```

Then update the two synthetic generation calls:
```python
    synth_cash = generate_cash(synth_start, synth_end, daily_pool=daily_pool, weather=weather)
    synth_sess = generate_sessions(synth_start, synth_end, weather=weather)
```

(Stock unchanged.)

- [ ] **Step 5: Commit**
```
git add gamefydb/data_generator.py
git commit -m "feat: inject Tunis weather multiplier into synthetic data"
```

---

## Task 3: Regenerate `extended_*.xlsx`

- [ ] **Step 1: Run the generator**

```
C:/Users/sarah/AppData/Local/Python/bin/python -m gamefydb.data_generator
```

Expected: writes `excel/extended_cash.xlsx`, `extended_session.xlsx`, `extended_stock.xlsx`, `extended_members.xlsx`. Also creates `excel/weather_tunis.parquet` on the first run. Console prints synthetic date range.

- [ ] **Step 2: Commit data files**

```
git add excel/extended_*.xlsx excel/weather_tunis.parquet
git commit -m "data: regenerate extended files with weather-correlated synthetic revenue"
```

---

## Task 4: Wire weather regressors into `forecaster.py`

**Files:**
- Modify: `gamefydb/forecaster.py`

- [ ] **Step 1: Add import + helper**

After existing imports add:
```python
from gamefydb.weather import fetch_weather
```

Right below `_holiday_proximity` (around line 86), add:
```python
def _attach_weather(df: pd.DataFrame, horizon_days: int = 0) -> pd.DataFrame:
    """Left-merge temp_max_c / precip_mm onto df. Caller may extend range via horizon_days."""
    start = pd.Timestamp(df['ds'].min())
    end   = pd.Timestamp(df['ds'].max()) + pd.Timedelta(days=horizon_days)
    w = fetch_weather(start, end)
    out = df.merge(w, on='ds', how='left')
    out['temp_max_c'] = out['temp_max_c'].fillna(out['temp_max_c'].mean())
    out['precip_mm']  = out['precip_mm'].fillna(0.0)
    return out
```

- [ ] **Step 2: Add a flag for weekly-aggregated frames**

Weather is daily; weekly data needs weekly aggregation. Add helper:

```python
def _attach_weather_weekly(df: pd.DataFrame, horizon_days: int = 0) -> pd.DataFrame:
    """Same as _attach_weather but aggregates weather to weekly (mean temp, sum precip) on the week-start ds."""
    start = pd.Timestamp(df['ds'].min())
    end   = pd.Timestamp(df['ds'].max()) + pd.Timedelta(days=horizon_days + 7)
    w = fetch_weather(start, end)
    w['_w'] = w['ds'].dt.to_period('W').apply(lambda p: p.start_time)
    w_weekly = w.groupby('_w').agg(temp_max_c=('temp_max_c', 'mean'),
                                    precip_mm=('precip_mm', 'sum')).reset_index()
    w_weekly = w_weekly.rename(columns={'_w': 'ds'})
    out = df.merge(w_weekly, on='ds', how='left')
    out['temp_max_c'] = out['temp_max_c'].fillna(out['temp_max_c'].mean())
    out['precip_mm']  = out['precip_mm'].fillna(0.0)
    return out
```

- [ ] **Step 3: Wire into `_evaluate_prophet`**

Update the function to accept a `use_weather` flag and a `weekly` flag for weather alignment, and attach + add regressors:

```python
def _evaluate_prophet(df: pd.DataFrame, split: float, freq: str = 'D',
                       log_y: bool = False, use_weather: bool = False,
                       weekly_weather: bool = False) -> dict:
    n = len(df)
    cutoff = int(n * split)
    if cutoff < 2 or n - cutoff < 2:
        return {}

    if use_weather:
        df = (_attach_weather_weekly(df) if weekly_weather else _attach_weather(df))

    train, test = df.iloc[:cutoff].copy(), df.iloc[cutoff:].copy()

    if log_y:
        train['y'] = np.log1p(train['y'])

    holiday_df = _build_holiday_df(df['ds'].min(), df['ds'].max())
    m = Prophet(interval_width=0.8,
                holidays=holiday_df if holiday_df is not None else None,
                holidays_prior_scale=20.0)
    if use_weather:
        m.add_regressor('temp_max_c')
        m.add_regressor('precip_mm')
    m.fit(train)

    future = m.make_future_dataframe(periods=len(test), freq=freq)
    if use_weather:
        future = future.merge(df[['ds', 'temp_max_c', 'precip_mm']], on='ds', how='left')
        future['temp_max_c'] = future['temp_max_c'].fillna(df['temp_max_c'].mean())
        future['precip_mm']  = future['precip_mm'].fillna(0.0)
    fc = m.predict(future)

    if log_y:
        fc['yhat'] = np.expm1(fc['yhat'])

    merged = test.merge(fc[['ds', 'yhat']], on='ds', how='inner')
    if merged.empty:
        return {}
    mae  = float((merged['y'] - merged['yhat']).abs().mean())
    rmse = float(((merged['y'] - merged['yhat']) ** 2).mean() ** 0.5)
    mean_actual = float(merged['y'].mean())
    mape = (mae / mean_actual * 100) if mean_actual > 0 else float('nan')
    return {'mae': mae, 'mape': mape, 'rmse': rmse}
```

- [ ] **Step 4: Wire into `_evaluate_xgboost`**

Update signature and feature builder. First, extend `_xgb_features` to accept optional weather arrays:

```python
def _xgb_features(i: int, y_arr: np.ndarray, ds_arr,
                   proximity: np.ndarray = None,
                   temp_arr: np.ndarray = None,
                   precip_arr: np.ndarray = None) -> dict:
    ts = pd.Timestamp(ds_arr[i])
    feat = {
        'lag_1':    float(y_arr[i - 1]),
        'lag_7':    float(y_arr[i - 7]),
        'lag_14':   float(y_arr[i - 14]),
        'roll_7':   float(y_arr[i - 7:i].mean()),
        'roll_14':  float(y_arr[i - 14:i].mean()),
        'dow':      ts.dayofweek,
        'is_weekend': int(ts.dayofweek >= 5),
        'month':    ts.month,
        'days_to_holiday': float(proximity[i]) if proximity is not None else 30.0,
    }
    if temp_arr is not None:
        feat['temp_max_c'] = float(temp_arr[i])
        feat['precip_mm']  = float(precip_arr[i])
    return feat
```

Then update `_evaluate_xgboost`:

```python
def _evaluate_xgboost(df: pd.DataFrame, split: float,
                      use_weather: bool = False, weekly_weather: bool = False):
    n = len(df)
    cutoff = int(n * split)
    if cutoff < 34 or n - cutoff < 2:
        return None

    if use_weather:
        df = (_attach_weather_weekly(df) if weekly_weather else _attach_weather(df))

    ds_arr = df['ds'].values
    y_arr  = df['y'].values
    temp_arr   = df['temp_max_c'].values if use_weather else None
    precip_arr = df['precip_mm'].values  if use_weather else None

    holiday_df = _build_holiday_df(df['ds'].min(), df['ds'].max())
    proximity  = _holiday_proximity(ds_arr, holiday_df)

    X_train, y_train = [], []
    for i in range(14, cutoff):
        X_train.append(_xgb_features(i, y_arr, ds_arr, proximity, temp_arr, precip_arr))
        y_train.append(y_arr[i])

    if len(X_train) < 10:
        return None

    model = XGBRegressor(n_estimators=300, learning_rate=0.05,
                         max_depth=5, subsample=0.8, colsample_bytree=0.8,
                         random_state=42, verbosity=0)
    model.fit(pd.DataFrame(X_train), y_train)

    y_extended = y_arr[:cutoff].tolist()
    preds = []
    for i in range(cutoff, n):
        feat = _xgb_features(i, np.array(y_extended), ds_arr, proximity, temp_arr, precip_arr)
        pred = max(0.0, float(model.predict(pd.DataFrame([feat]))[0]))
        preds.append(pred)
        y_extended.append(pred)

    actual = y_arr[cutoff:]
    preds  = np.array(preds)
    mae    = float(np.abs(actual - preds).mean())
    rmse   = float(np.sqrt(((actual - preds) ** 2).mean()))
    mean_actual = float(actual.mean())
    mape   = (mae / mean_actual * 100) if mean_actual > 0 else float('nan')
    return {'mae': mae, 'mape': mape, 'rmse': rmse,
            'preds': preds, 'test_ds': ds_arr[cutoff:]}
```

- [ ] **Step 5: Pass `use_weather=True` from revenue + sessions forecasts**

In `forecast_revenue` (around line 416) update Prophet + XGBoost eval calls:
```python
    p = _evaluate_prophet(weekly_eval, split=0.8, freq='7D', log_y=True,
                          use_weather=True, weekly_weather=True)
    s = _evaluate_sarima(weekly_eval, split=0.8, m=4)
    x = _evaluate_xgboost(weekly_eval, split=0.8,
                          use_weather=True, weekly_weather=True)
```

Find the sessions forecast equivalent and apply the same change. Leave `forecast_members` alone (weekly aggregate, weather signal too noisy).

- [ ] **Step 6: Wire into `_prophet_forecast` (the production forecast, not just eval)**

Update `_prophet_forecast` to accept and use weather:

```python
def _prophet_forecast(daily: pd.DataFrame, use_weather: bool = False) -> tuple:
    if use_weather:
        daily = _attach_weather(daily, horizon_days=90)

    holiday_df = _build_holiday_df(daily['ds'].min(),
                                   daily['ds'].max() + pd.Timedelta(days=90))
    m = Prophet(interval_width=0.8,
                holidays=holiday_df if holiday_df is not None else None,
                holidays_prior_scale=20.0)
    if use_weather:
        m.add_regressor('temp_max_c')
        m.add_regressor('precip_mm')
    m.fit(daily)

    cols = ['ds', 'yhat', 'yhat_lower', 'yhat_upper']

    future_w = m.make_future_dataframe(periods=28)
    if use_weather:
        future_w = future_w.merge(fetch_weather(future_w['ds'].min(), future_w['ds'].max()),
                                   on='ds', how='left')
        future_w['temp_max_c'] = future_w['temp_max_c'].fillna(daily['temp_max_c'].mean())
        future_w['precip_mm']  = future_w['precip_mm'].fillna(0.0)
    fc_w = m.predict(future_w)[cols].tail(28).reset_index(drop=True)
    fc_w['_b'] = fc_w.index // 7
    weekly = (
        fc_w.groupby('_b')
        .agg(date=('ds', 'last'), yhat=('yhat', 'sum'),
             yhat_lower=('yhat_lower', 'sum'), yhat_upper=('yhat_upper', 'sum'))
        .reset_index(drop=True)
    )
    weekly['granularity'] = 'weekly'

    future_m = m.make_future_dataframe(periods=90)
    if use_weather:
        future_m = future_m.merge(fetch_weather(future_m['ds'].min(), future_m['ds'].max()),
                                   on='ds', how='left')
        future_m['temp_max_c'] = future_m['temp_max_c'].fillna(daily['temp_max_c'].mean())
        future_m['precip_mm']  = future_m['precip_mm'].fillna(0.0)
    fc_m = m.predict(future_m)[cols].tail(90).reset_index(drop=True)
    fc_m['_b'] = fc_m.index // 30
    monthly = (
        fc_m.groupby('_b')
        .agg(date=('ds', 'last'), yhat=('yhat', 'sum'),
             yhat_lower=('yhat_lower', 'sum'), yhat_upper=('yhat_upper', 'sum'))
        .reset_index(drop=True)
    )
    monthly['granularity'] = 'monthly'
    return weekly, monthly
```

In `forecast_revenue` update the production forecast call:
```python
    weekly, monthly = _prophet_forecast(daily, use_weather=True)
```

- [ ] **Step 7: Commit**
```
git add gamefydb/forecaster.py
git commit -m "feat: add weather regressors to Prophet + XGBoost revenue/sessions forecasts"
```

---

## Task 5: Tests

**Files:**
- Create: `tests/test_weather.py`

- [ ] **Step 1: Write tests**

```python
import pandas as pd
import pytest
from gamefydb.weather import fetch_weather, weather_multiplier


def test_weather_multiplier_clear_day():
    assert weather_multiplier(25.0, 0.0) == 1.0


def test_weather_multiplier_rain():
    assert weather_multiplier(25.0, 5.0) == pytest.approx(0.90)


def test_weather_multiplier_hot():
    assert weather_multiplier(35.0, 0.0) == pytest.approx(1.08)


def test_weather_multiplier_hot_and_rain():
    assert weather_multiplier(35.0, 5.0) == pytest.approx(0.90 * 1.08)


def test_fetch_weather_returns_expected_columns():
    df = fetch_weather(pd.Timestamp('2024-09-01'), pd.Timestamp('2024-09-03'))
    assert set(df.columns) >= {'ds', 'temp_max_c', 'precip_mm'}
    assert len(df) == 3
    assert df['temp_max_c'].notna().all()
```

- [ ] **Step 2: Run tests**

```
C:/Users/sarah/AppData/Local/Python/bin/python -m pytest tests/test_weather.py -v
```
Expected: 5 passed.

- [ ] **Step 3: Commit**
```
git add tests/test_weather.py
git commit -m "test: cover weather multiplier and fetch_weather"
```

---

## Task 6: End-to-end pipeline run

- [ ] **Step 1: Run full pipeline**

```
C:/Users/sarah/AppData/Local/Python/bin/python run.py --input excel --output output
```

Expected console output should include the wMAPE comparison lines:
```
[Revenue (TND, weekly)] ... [Prophet] MAPE ...
[Session volume (weekly)] ... [Prophet] MAPE ...
```

- [ ] **Step 2: Compare wMAPE against baselines**

Baselines (from memory):
- Revenue weekly Prophet: 29.7%
- Sessions weekly: 36.4% (SARIMA) / 36.8% (Prophet)

Target: Revenue ≤ 26%, Sessions ≤ 32%. If not met, this is a tuning round, not a failure — report numbers + Prophet coefficient signs.

- [ ] **Step 3: Report results back to user**

Do not commit anything else until user has reviewed wMAPE numbers.

---

## Self-review notes

- All file paths absolute or workspace-relative — ✓
- No TBD/TODO/"add error handling" — ✓
- Function signatures consistent across tasks (`use_weather`, `weekly_weather`) — ✓
- Open-Meteo Archive API is keyless and unrestricted for personal/research use — ✓
- Parquet cache survives across runs; future-date climatology handles 3-month horizon — ✓
