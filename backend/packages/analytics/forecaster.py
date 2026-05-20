import logging
import math

import numpy as np
import pandas as pd
from pmdarima import auto_arima
from prophet import Prophet
from statsmodels.tsa.stattools import adfuller
from xgboost import XGBRegressor

from backend.packages.analytics.weather import fetch_weather

logging.getLogger('cmdstanpy').setLevel(logging.WARNING)
logging.getLogger('prophet').setLevel(logging.WARNING)


# ── Holiday calendar ──────────────────────────────────────────────────────────

# Fixed Tunisian civil holidays: (month, day, name, lower_window, upper_window)
_FIXED_HOLIDAYS = [
    (1,  1, 'New Year',         -1,  3),  # window: Dec 31 → Jan 4 (post-holiday spike)
    (1, 14, 'Revolution Day',    0,  0),
    (3, 20, 'Independence Day',  0,  0),
    (4,  9, 'Martyrs Day',       0,  0),
    (5,  1, 'Labour Day',        0,  0),
    (7, 25, 'Republic Day',      0,  0),
    (8, 13, 'Womens Day',        0,  0),
    (10,15, 'Evacuation Day',    0,  0),
    (12,25, 'Christmas',         0,  1),
    (12,31, 'New Year Eve',      0,  0),
]

# Approximate Islamic holidays (dates shift each year).
# upper_window=3 on Eid days covers the Eid+1..Eid+3 cluster present in the
# training data (see data_generator._eid_week_pattern).
_ISLAMIC_HOLIDAYS = [
    (2022,  5,  2, 'Eid al-Fitr',     0, 3),
    (2022,  7,  9, 'Eid al-Adha',     0, 3),
    (2022,  7, 30, 'Islamic New Year', 0, 0),
    (2022, 10,  8, 'Mawlid',          0, 0),
    (2023,  4, 21, 'Eid al-Fitr',     0, 3),
    (2023,  6, 28, 'Eid al-Adha',     0, 3),
    (2023,  7, 19, 'Islamic New Year', 0, 0),
    (2023,  9, 27, 'Mawlid',          0, 0),
    (2024,  4, 10, 'Eid al-Fitr',     0, 3),
    (2024,  6, 17, 'Eid al-Adha',     0, 3),
    (2024,  7,  8, 'Islamic New Year', 0, 0),
    (2024,  9, 16, 'Mawlid',          0, 0),
    (2025,  3, 31, 'Eid al-Fitr',     0, 3),
    (2025,  6,  7, 'Eid al-Adha',     0, 3),
    (2025,  6, 27, 'Islamic New Year', 0, 0),
    (2025,  9,  5, 'Mawlid',          0, 0),
    (2026,  3, 21, 'Eid al-Fitr',     0, 3),
    (2026,  5, 27, 'Eid al-Adha',     0, 3),
    (2026,  6, 17, 'Islamic New Year', 0, 0),
]


def _build_holiday_df(min_date: pd.Timestamp, max_date: pd.Timestamp):
    """Return a Prophet-compatible holidays DataFrame covering [min_date, max_date]."""
    rows = []
    for year in range(min_date.year, max_date.year + 2):
        for month, day, name, lower, upper in _FIXED_HOLIDAYS:
            try:
                ds = pd.Timestamp(year, month, day)
                if min_date <= ds <= max_date + pd.Timedelta(days=30):
                    rows.append({'holiday': name, 'ds': ds,
                                 'lower_window': lower, 'upper_window': upper})
            except ValueError:
                pass
    for year, month, day, name, lower, upper in _ISLAMIC_HOLIDAYS:
        ds = pd.Timestamp(year, month, day)
        if min_date <= ds <= max_date + pd.Timedelta(days=30):
            rows.append({'holiday': name, 'ds': ds,
                         'lower_window': lower, 'upper_window': upper})
    return pd.DataFrame(rows) if rows else None


def _holiday_proximity(ds_arr, holiday_df) -> np.ndarray:
    """Return array of days-to-nearest-holiday for each date in ds_arr (capped at 30)."""
    if holiday_df is None or holiday_df.empty:
        return np.full(len(ds_arr), 30)
    holiday_dates = pd.to_datetime(holiday_df['ds']).dt.date.values
    result = np.empty(len(ds_arr), dtype=float)
    for i, ts in enumerate(ds_arr):
        d = pd.Timestamp(ts).date()
        result[i] = min((abs((d - h).days) for h in holiday_dates), default=30)
    return np.minimum(result, 30)


# ── Weather regressor helpers ─────────────────────────────────────────────────

def _attach_weather(df: pd.DataFrame, horizon_days: int = 0) -> pd.DataFrame:
    """Left-merge daily temp_max_c / precip_mm onto df['ds']."""
    start = pd.Timestamp(df['ds'].min())
    end   = pd.Timestamp(df['ds'].max()) + pd.Timedelta(days=horizon_days)
    w = fetch_weather(start, end)
    out = df.merge(w, on='ds', how='left')
    out['temp_max_c'] = out['temp_max_c'].fillna(out['temp_max_c'].mean() if out['temp_max_c'].notna().any() else 20.0)
    out['precip_mm']  = out['precip_mm'].fillna(0.0)
    return out


def _attach_weather_weekly(df: pd.DataFrame, horizon_days: int = 0) -> pd.DataFrame:
    """Aggregate weather to weekly (mean temp, sum precip) keyed by week-start ds."""
    start = pd.Timestamp(df['ds'].min())
    end   = pd.Timestamp(df['ds'].max()) + pd.Timedelta(days=horizon_days + 7)
    w = fetch_weather(start, end)
    w['_w'] = w['ds'].dt.to_period('W').apply(lambda p: p.start_time)
    w_weekly = (
        w.groupby('_w').agg(temp_max_c=('temp_max_c', 'mean'),
                            precip_mm=('precip_mm', 'sum'))
        .reset_index()
        .rename(columns={'_w': 'ds'})
    )
    out = df.merge(w_weekly, on='ds', how='left')
    out['temp_max_c'] = out['temp_max_c'].fillna(out['temp_max_c'].mean() if out['temp_max_c'].notna().any() else 20.0)
    out['precip_mm']  = out['precip_mm'].fillna(0.0)
    return out


def _to_daily(df: pd.DataFrame, date_col: str, value_col: str) -> pd.DataFrame:
    daily = df.copy()
    daily['ds'] = pd.to_datetime(daily[date_col]).dt.normalize()
    return (
        daily.groupby('ds')[value_col]
        .sum()
        .reset_index()
        .rename(columns={value_col: 'y'})
    )


def _to_weekly(daily: pd.DataFrame) -> pd.DataFrame:
    """Aggregate a daily (ds, y) series to weekly sums, ds = week-start (Mon)."""
    d = daily.copy()
    d['_w'] = d['ds'].dt.to_period('W').apply(lambda p: p.start_time)
    weekly = d.groupby('_w')['y'].sum().reset_index().rename(columns={'_w': 'ds'})
    weekly['ds'] = pd.to_datetime(weekly['ds'])
    return weekly


def holiday_week_starts(min_date: pd.Timestamp, max_date: pd.Timestamp) -> set:
    """Week-start (Monday) timestamps covered by Ramadan, Eid, or the Eid+1..Eid+3
    cluster. Used by the error-decomposition analysis to separate "ordinary"
    weeks from "holiday-cluster" weeks in the test set.
    """
    from backend.packages.etl.data_generator import _RAMADAN_PERIODS
    days = set()
    for start, end in _RAMADAN_PERIODS:
        if end < min_date or start > max_date:
            continue
        for d in pd.date_range(max(start, min_date), min(end, max_date)):
            days.add(d)
    for year, month, day, name, lower, upper in _ISLAMIC_HOLIDAYS:
        if 'Eid' not in name:
            continue
        try:
            eid = pd.Timestamp(year, month, day)
        except ValueError:
            continue
        for offset in range(lower, upper + 1):
            d = eid + pd.Timedelta(days=offset)
            if min_date <= d <= max_date:
                days.add(d)
    return {pd.Timestamp(d).to_period('W').start_time for d in days}


def _check_stationarity(series: pd.Series, label: str, stage: str = 'raw') -> dict:
    """Run the Augmented Dickey-Fuller test on a time series and report the result."""
    clean = series.dropna()
    if clean.nunique() <= 1:
        print(f'    [{label} / {stage}]  skipped (constant series)')
        return {
            'series': label,
            'stage': stage,
            'adf_statistic': float('nan'),
            'p_value': float('nan'),
            'critical_value_5pct': float('nan'),
            'is_stationary': None,
            'verdict': 'skipped (constant)',
        }
    if len(clean) < 50:
        print(f'    [{label} / {stage}]  note: short series (N={len(clean)}), interpret ADF with caution')
    adf_stat, p_value, _, _, critical_values, _ = adfuller(clean, autolag='AIC')
    is_stationary = p_value < 0.05
    verdict = 'stationary' if is_stationary else 'non-stationary'
    print(
        f'    [{label} / {stage}]  ADF={adf_stat:+.4f}  p={p_value:.4f}'
        f'  critical(5%)={critical_values["5%"]:.4f}  => {verdict}'
    )
    return {
        'series': label,
        'stage': stage,
        'adf_statistic': round(adf_stat, 4),
        'p_value': round(p_value, 4),
        'critical_value_5pct': round(critical_values['5%'], 4),
        'is_stationary': is_stationary,
        'verdict': verdict,
    }


def _stabilize(series: pd.Series) -> pd.Series:
    """Apply variance- and trend-stabilising transformation: log(1+y) then
    first-difference. The result hovers around zero with constant variance
    when the original series has a multiplicative trend with bursty spikes,
    which is the visual pattern present in the GamefyDB forecast series."""
    return np.log1p(series.astype(float)).diff()


def study_stationarity(transactions_df: pd.DataFrame) -> pd.DataFrame:
    """Run ADF stationarity tests on the three forecast series, both on the
    raw observations and after a log(1+y)+first-difference stabilization step.

    Tests:
        1. Daily revenue (TND income)
        2. Daily session volume (transaction count)
        3. Weekly member activity

    Returns a long-format DataFrame with two rows per series ("raw" and
    "log_diff" stages) and columns:
        series, stage, adf_statistic, p_value, critical_value_5pct,
        is_stationary, verdict
    """
    print('  Stationarity tests (ADF, significance=0.05):')

    income = transactions_df[transactions_df['income_expense'] == 'Income'].copy()
    income['_v'] = income['amount_tnd']
    rev_daily = _to_daily(income, 'transaction_datetime', '_v')

    vol_df = transactions_df.copy()
    vol_df['_v'] = 1
    vol_daily = _to_daily(vol_df, 'transaction_datetime', '_v')

    mem = transactions_df[transactions_df['transaction_type'] == 'Member Transactions'].copy()
    mem['_v'] = 1
    mem_daily = _to_daily(mem, 'transaction_datetime', '_v')
    mem_daily['_w'] = mem_daily['ds'].dt.to_period('W').apply(lambda p: p.start_time)
    mem_weekly = (
        mem_daily.groupby('_w')['y'].sum()
        .reset_index()
        .rename(columns={'_w': 'ds', 'y': 'y'})
    )

    series_specs = [
        (rev_daily['y'],  'Revenue (TND, daily)'),
        (vol_daily['y'],  'Session volume (daily)'),
        (mem_weekly['y'], 'Member activity (weekly)'),
    ]

    results = []
    for s, label in series_specs:
        results.append(_check_stationarity(s, label, stage='raw'))
        results.append(_check_stationarity(_stabilize(s), label, stage='log_diff'))
    return pd.DataFrame(results)


def _evaluate_prophet(df: pd.DataFrame, split: float, freq: str = 'D',
                       use_weather: bool = False,
                       weekly_weather: bool = False) -> dict:
    n = len(df)
    cutoff = int(n * split)
    if cutoff < 2 or n - cutoff < 2:
        return {}

    if use_weather:
        df = (_attach_weather_weekly(df) if weekly_weather else _attach_weather(df))

    train, test = df.iloc[:cutoff].copy(), df.iloc[cutoff:].copy()

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

    merged = test.merge(fc[['ds', 'yhat']], on='ds', how='inner')
    if merged.empty:
        return {}

    mae  = float((merged['y'] - merged['yhat']).abs().mean())
    rmse = float(((merged['y'] - merged['yhat']) ** 2).mean() ** 0.5)
    # wMAPE (weighted MAPE) = MAE / mean(actual) — stable for near-zero actual days
    mean_actual = float(merged['y'].mean())
    mape = (mae / mean_actual * 100) if mean_actual > 0 else float('nan')
    return {'mae': mae, 'mape': mape, 'rmse': rmse}


def _evaluate_sarima(df: pd.DataFrame, split: float, m: int = 7):
    n = len(df)
    cutoff = int(n * split)
    if cutoff < 2 or n - cutoff < 2:
        return None

    train, test = df.iloc[:cutoff], df.iloc[cutoff:]

    try:
        model = auto_arima(
            train['y'],
            seasonal=True,
            m=m,
            stepwise=True,
            suppress_warnings=True,
            error_action='ignore',
            information_criterion='aic',
        )
        predictions = model.predict(n_periods=len(test))
    except Exception:
        return None

    actual = test['y'].values
    mae  = float(np.abs(actual - predictions).mean())
    rmse = float(np.sqrt(((actual - predictions) ** 2).mean()))
    mean_actual = float(actual.mean())
    mape = (mae / mean_actual * 100) if mean_actual > 0 else float('nan')
    return {'mae': mae, 'mape': mape, 'rmse': rmse}


def _xgb_features(i: int, y_arr: np.ndarray, ds_arr,
                   proximity: np.ndarray = None,
                   temp_arr: np.ndarray = None,
                   precip_arr: np.ndarray = None) -> dict:
    """Build feature dict for position i using y_arr for lag values."""
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


def _evaluate_xgboost(df: pd.DataFrame, split: float,
                      use_weather: bool = False, weekly_weather: bool = False):
    """Train XGBoost on the training split and recursively predict the test split.

    Uses lag_1, lag_7, lag_14, 7/14-day rolling means, day-of-week, weekend
    flag, month, and days-to-nearest-holiday as features. Optionally adds
    temp_max_c + precip_mm.
    """
    n = len(df)
    cutoff = int(n * split)
    # Need at least 14 lags + 20 usable training samples; cutoff - 14 >= 20 → cutoff >= 34
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

    # Build training feature matrix (need at least 14 lags)
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

    # Recursive multi-step prediction over the test period
    y_extended = y_arr[:cutoff].tolist()
    preds = []
    for i in range(cutoff, n):
        feat = _xgb_features(i, np.array(y_extended), ds_arr, proximity, temp_arr, precip_arr)
        pred = max(0.0, float(model.predict(pd.DataFrame([feat]))[0]))
        preds.append(pred)
        y_extended.append(pred)          # feed prediction back as next lag

    actual = y_arr[cutoff:]
    preds  = np.array(preds)
    mae    = float(np.abs(actual - preds).mean())
    rmse   = float(np.sqrt(((actual - preds) ** 2).mean()))
    mean_actual = float(actual.mean())
    mape   = (mae / mean_actual * 100) if mean_actual > 0 else float('nan')
    return {'mae': mae, 'mape': mape, 'rmse': rmse,
            'preds': preds, 'test_ds': ds_arr[cutoff:]}


def _print_comparison(label: str, n: int, split: float,
                      prophet_m: dict, sarima_m, xgb_m=None,
                      prophet_w: dict = None, xgb_w=None) -> None:
    if not prophet_m:
        print(f'    [{label}] Prophet evaluation failed — skipped')
        return

    n_train = int(n * split)
    n_test  = n - n_train
    pct     = int(split * 100)

    def verdict(mape): return 'GOOD' if mape < 20 else ('ACCEPTABLE' if mape < 50 else 'POOR')

    print(f'    [{label}] {pct}/{100 - pct} split — {n_train} train / {n_test} test points')
    print(f'      [Prophet]          MAPE {prophet_m["mape"]:5.1f}%  MAE {prophet_m["mae"]:8.2f}  RMSE {prophet_m["rmse"]:8.2f}  -> {verdict(prophet_m["mape"])}')

    scores = {'Prophet': prophet_m['mape']}

    if prophet_w:
        print(f'      [Prophet+weather]  MAPE {prophet_w["mape"]:5.1f}%  MAE {prophet_w["mae"]:8.2f}  RMSE {prophet_w["rmse"]:8.2f}  -> {verdict(prophet_w["mape"])}')
        scores['Prophet+weather'] = prophet_w['mape']

    if sarima_m:
        print(f'      [SARIMA]           MAPE {sarima_m["mape"]:5.1f}%  MAE {sarima_m["mae"]:8.2f}  RMSE {sarima_m["rmse"]:8.2f}  -> {verdict(sarima_m["mape"])}')
        scores['SARIMA'] = sarima_m['mape']
    else:
        print(f'      [SARIMA]           failed to converge — skipped')

    if xgb_m:
        print(f'      [XGBoost]          MAPE {xgb_m["mape"]:5.1f}%  MAE {xgb_m["mae"]:8.2f}  RMSE {xgb_m["rmse"]:8.2f}  -> {verdict(xgb_m["mape"])}')
        scores['XGBoost'] = xgb_m['mape']

    if xgb_w:
        print(f'      [XGBoost+weather]  MAPE {xgb_w["mape"]:5.1f}%  MAE {xgb_w["mae"]:8.2f}  RMSE {xgb_w["rmse"]:8.2f}  -> {verdict(xgb_w["mape"])}')
        scores['XGBoost+weather'] = xgb_w['mape']

    if len(scores) > 1:
        winner = min(scores, key=scores.get)
        print(f'      Winner: {winner}')


def _prophet_forecast(daily: pd.DataFrame, use_weather: bool = False) -> tuple:
    """Fit Prophet and return (weekly_4rows, monthly_3rows) DataFrames."""
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

    def _add_weather(future):
        w = fetch_weather(future['ds'].min(), future['ds'].max())
        out = future.merge(w, on='ds', how='left')
        out['temp_max_c'] = out['temp_max_c'].fillna(daily['temp_max_c'].mean())
        out['precip_mm']  = out['precip_mm'].fillna(0.0)
        return out

    future_w = m.make_future_dataframe(periods=28)
    if use_weather:
        future_w = _add_weather(future_w)
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
        future_m = _add_weather(future_m)
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


# ── Revenue ───────────────────────────────────────────────────────────────────

def forecast_revenue(transactions_df: pd.DataFrame) -> pd.DataFrame:
    """Forecast total revenue (TND) for the next 4 weeks and 3 months."""
    income = transactions_df[transactions_df['income_expense'] == 'Income'].copy()
    income['_v'] = income['amount_tnd']
    daily = _to_daily(income, 'transaction_datetime', '_v')
    weekly_eval = _to_weekly(daily)
    p   = _evaluate_prophet(weekly_eval, split=0.8, freq='7D')
    p_w = _evaluate_prophet(weekly_eval, split=0.8, freq='7D',
                            use_weather=True, weekly_weather=True)
    s   = _evaluate_sarima(weekly_eval, split=0.8, m=4)
    x   = _evaluate_xgboost(weekly_eval, split=0.8)
    x_w = _evaluate_xgboost(weekly_eval, split=0.8,
                            use_weather=True, weekly_weather=True)
    _print_comparison('Revenue (TND, weekly)', len(weekly_eval), 0.8,
                      p, s, x, prophet_w=p_w, xgb_w=x_w)
    weekly, monthly = _prophet_forecast(daily, use_weather=True)
    result = pd.concat([weekly, monthly], ignore_index=True)
    return result[['date', 'granularity', 'yhat', 'yhat_lower', 'yhat_upper']]


# ── Member activity ───────────────────────────────────────────────────────────

def forecast_members(transactions_df: pd.DataFrame) -> pd.DataFrame:
    """Forecast member transaction count for the next 4 weeks and 3 months.

    Fits Prophet on weekly aggregated data to avoid sparse daily counts
    producing negative confidence bounds.
    """
    members = transactions_df[
        transactions_df['transaction_type'] == 'Member Transactions'
    ].copy()
    members['_v'] = 1
    daily = _to_daily(members, 'transaction_datetime', '_v')

    daily['_w'] = daily['ds'].dt.to_period('W').apply(lambda p: p.start_time)
    weekly_hist = (
        daily.groupby('_w')['y'].sum()
        .reset_index()
        .rename(columns={'_w': 'ds'})
    )
    weekly_hist['ds'] = pd.to_datetime(weekly_hist['ds'])
    p = _evaluate_prophet(weekly_hist, split=0.8, freq='7D')
    s = _evaluate_sarima(weekly_hist, split=0.8, m=4)
    x = _evaluate_xgboost(weekly_hist, split=0.8)
    _print_comparison('Member activity', len(weekly_hist), 0.8, p, s, x)

    m = Prophet(interval_width=0.8)
    m.fit(weekly_hist)

    cols = ['ds', 'yhat', 'yhat_lower', 'yhat_upper']

    future_w = m.make_future_dataframe(periods=4, freq='W')
    weekly = m.predict(future_w)[cols].tail(4).reset_index(drop=True)
    weekly = weekly.rename(columns={'ds': 'date'})
    weekly['granularity'] = 'weekly'

    future_m = m.make_future_dataframe(periods=13, freq='W')
    fc_m = m.predict(future_m)[cols].tail(13).reset_index(drop=True)
    fc_m['_b'] = fc_m.index // 4
    monthly = (
        fc_m.groupby('_b')
        .agg(date=('ds', 'last'), yhat=('yhat', 'sum'),
             yhat_lower=('yhat_lower', 'sum'), yhat_upper=('yhat_upper', 'sum'))
        .reset_index(drop=True)
        .head(3)
    )
    monthly['granularity'] = 'monthly'

    result = pd.concat([weekly, monthly], ignore_index=True)
    for col in ['yhat', 'yhat_lower', 'yhat_upper']:
        result[col] = result[col].clip(lower=0).round().astype(int)
    return result[['date', 'granularity', 'yhat', 'yhat_lower', 'yhat_upper']]


# ── Peak hours ────────────────────────────────────────────────────────────────

def forecast_peak_hours(transactions_df: pd.DataFrame) -> tuple:
    """Identify busiest hours and days of the week from transaction history.

    Returns:
        (by_hour, by_day) — two DataFrames, each with columns:
            hour / day_of_week, avg_transactions, pct_of_total.
    """
    df = transactions_df.copy()
    df['dt'] = pd.to_datetime(df['transaction_datetime'])
    df['date'] = df['dt'].dt.date
    df['hour'] = df['dt'].dt.hour
    df['day_of_week'] = df['dt'].dt.day_name()

    by_hour = (
        df.groupby(['date', 'hour']).size()
        .reset_index(name='count')
        .groupby('hour')['count'].mean()
        .round(1)
        .reset_index()
        .rename(columns={'hour': 'hour', 'count': 'avg_transactions'})
    )
    total_h = by_hour['avg_transactions'].sum()
    by_hour['pct_of_total'] = (by_hour['avg_transactions'] / total_h * 100).round(1)

    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    by_day = (
        df.groupby(['date', 'day_of_week']).size()
        .reset_index(name='count')
        .groupby('day_of_week')['count'].mean()
        .round(1)
        .reset_index()
        .rename(columns={'day_of_week': 'day_of_week', 'count': 'avg_transactions'})
    )
    by_day['_ord'] = by_day['day_of_week'].map({d: i for i, d in enumerate(day_order)})
    by_day = by_day.sort_values('_ord').drop(columns=['_ord']).reset_index(drop=True)
    total_d = by_day['avg_transactions'].sum()
    by_day['pct_of_total'] = (by_day['avg_transactions'] / total_d * 100).round(1)

    return by_hour[['hour', 'avg_transactions', 'pct_of_total']], \
           by_day[['day_of_week', 'avg_transactions', 'pct_of_total']]


# ── Session volume ────────────────────────────────────────────────────────────

def forecast_session_volume(transactions_df: pd.DataFrame) -> pd.DataFrame:
    """Forecast total daily activity volume for the next 4 weeks and 3 months.

    Uses daily transaction count as a proxy for session volume (sessions table
    has no timestamps). Results are whole numbers.
    """
    df = transactions_df.copy()
    df['_v'] = 1
    daily = _to_daily(df, 'transaction_datetime', '_v')
    weekly_eval = _to_weekly(daily)
    p   = _evaluate_prophet(weekly_eval, split=0.8, freq='7D')
    p_w = _evaluate_prophet(weekly_eval, split=0.8, freq='7D',
                            use_weather=True, weekly_weather=True)
    s   = _evaluate_sarima(weekly_eval, split=0.8, m=4)
    x   = _evaluate_xgboost(weekly_eval, split=0.8)
    x_w = _evaluate_xgboost(weekly_eval, split=0.8,
                            use_weather=True, weekly_weather=True)
    _print_comparison('Session volume (weekly)', len(weekly_eval), 0.8,
                      p, s, x, prophet_w=p_w, xgb_w=x_w)
    weekly, monthly = _prophet_forecast(daily, use_weather=True)
    result = pd.concat([weekly, monthly], ignore_index=True)
    for col in ['yhat', 'yhat_lower', 'yhat_upper']:
        result[col] = result[col].clip(lower=0).round().astype(int)
    return result[['date', 'granularity', 'yhat', 'yhat_lower', 'yhat_upper']]


# ── Stock replenishment ───────────────────────────────────────────────────────

def forecast_stock_replenishment(
    movements_df: pd.DataFrame,
    safety_weeks: float = 1.5,
) -> pd.DataFrame:
    """Compute reorder recommendations for each item based on consumption rate.

    All stock movements are "Out" (sales) — there are no restock records —
    so this function calculates how fast each item sells and suggests how
    much to order and how often.

    Args:
        movements_df: stock movements with columns: movement_datetime, item, quantity.
        safety_weeks: safety buffer multiplier on top of average weekly consumption.
                      Default 1.5 means order 1.5× the weekly average each time.
                      Raise for fast-moving or hard-to-source items.

    Returns:
        DataFrame sorted by avg_per_week descending, with columns:
            item               — item name
            total_sold         — total units sold across the full period
            avg_per_week       — average units sold per week (rounded)
            suggested_order_qty — how many units to order per restock (avg × safety_weeks)
            reorder_frequency  — 'weekly' / 'bi-weekly' / 'monthly' based on velocity
    """
    df = movements_df.copy()
    df['dt'] = pd.to_datetime(df['movement_datetime'])

    period_weeks = max((df['dt'].max() - df['dt'].min()).days / 7, 1)

    agg = (
        df.groupby('item')['quantity']
        .sum()
        .reset_index()
        .rename(columns={'quantity': 'total_sold'})
    )
    agg['total_sold'] = agg['total_sold'].astype(int)
    agg['avg_per_week'] = (agg['total_sold'] / period_weeks).round(1)
    agg['suggested_order_qty'] = (agg['avg_per_week'] * safety_weeks).apply(
        lambda x: max(1, math.ceil(x))
    )

    def _frequency(avg):
        if avg >= 20:
            return 'weekly'
        elif avg >= 8:
            return 'bi-weekly'
        else:
            return 'monthly'

    agg['reorder_frequency'] = agg['avg_per_week'].apply(_frequency)

    return (
        agg.sort_values('avg_per_week', ascending=False)
        .reset_index(drop=True)
        [['item', 'total_sold', 'avg_per_week', 'suggested_order_qty', 'reorder_frequency']]
    )




