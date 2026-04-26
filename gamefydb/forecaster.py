import logging
import math

import numpy as np
import pandas as pd
from pmdarima import auto_arima
from prophet import Prophet

logging.getLogger('cmdstanpy').setLevel(logging.WARNING)
logging.getLogger('prophet').setLevel(logging.WARNING)


def _to_daily(df: pd.DataFrame, date_col: str, value_col: str) -> pd.DataFrame:
    daily = df.copy()
    daily['ds'] = pd.to_datetime(daily[date_col]).dt.normalize()
    return (
        daily.groupby('ds')[value_col]
        .sum()
        .reset_index()
        .rename(columns={value_col: 'y'})
    )


def _evaluate_prophet(df: pd.DataFrame, split: float, freq: str = 'D') -> dict:
    n = len(df)
    cutoff = int(n * split)
    if cutoff < 2 or n - cutoff < 2:
        return {}

    train, test = df.iloc[:cutoff].copy(), df.iloc[cutoff:].copy()

    m = Prophet(interval_width=0.8)
    m.fit(train)
    future = m.make_future_dataframe(periods=len(test), freq=freq)
    fc = m.predict(future)

    merged = test.merge(fc[['ds', 'yhat']], on='ds', how='inner')
    if merged.empty:
        return {}

    mae = float((merged['y'] - merged['yhat']).abs().mean())
    rmse = float(((merged['y'] - merged['yhat']) ** 2).mean() ** 0.5)
    nonzero = merged['y'] != 0
    mape = float(
        ((merged.loc[nonzero, 'y'] - merged.loc[nonzero, 'yhat']).abs()
         / merged.loc[nonzero, 'y']).mean() * 100
        if nonzero.any() else float('nan')
    )
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
    mae = float(np.abs(actual - predictions).mean())
    rmse = float(np.sqrt(((actual - predictions) ** 2).mean()))
    nonzero = actual != 0
    mape = float(
        np.abs((actual[nonzero] - predictions[nonzero]) / actual[nonzero]).mean() * 100
        if nonzero.any() else float('nan')
    )
    return {'mae': mae, 'mape': mape, 'rmse': rmse}


def _print_comparison(label: str, n: int, split: float, prophet_m: dict, sarima_m) -> None:
    if not prophet_m:
        print(f'    [{label}] Prophet evaluation failed — skipped')
        return

    n_train = int(n * split)
    n_test = n - n_train
    pct = int(split * 100)

    p_verdict = 'GOOD' if prophet_m['mape'] < 10 else ('ACCEPTABLE' if prophet_m['mape'] < 20 else 'POOR')

    print(f'    [{label}] {pct}/{100 - pct} split — {n_train} train / {n_test} test points')
    print(f'      [Prophet] MAPE {prophet_m["mape"]:5.1f}%  MAE {prophet_m["mae"]:8.2f}  RMSE {prophet_m["rmse"]:8.2f}  → {p_verdict}')

    if sarima_m:
        s_verdict = 'GOOD' if sarima_m['mape'] < 10 else ('ACCEPTABLE' if sarima_m['mape'] < 20 else 'POOR')
        winner = 'Prophet' if prophet_m['mape'] <= sarima_m['mape'] else 'SARIMA'
        print(f'      [SARIMA]  MAPE {sarima_m["mape"]:5.1f}%  MAE {sarima_m["mae"]:8.2f}  RMSE {sarima_m["rmse"]:8.2f}  → {s_verdict}')
        print(f'      Winner: {winner}')
    else:
        print(f'      [SARIMA]  failed to converge — skipped')


def _prophet_forecast(daily: pd.DataFrame) -> tuple:
    """Fit Prophet and return (weekly_4rows, monthly_3rows) DataFrames."""
    m = Prophet(interval_width=0.8)
    m.fit(daily)

    cols = ['ds', 'yhat', 'yhat_lower', 'yhat_upper']

    future_w = m.make_future_dataframe(periods=28)
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
    _evaluate_prophet(daily, split=0.8)
    weekly, monthly = _prophet_forecast(daily)
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
    _evaluate_prophet(weekly_hist, split=0.8, freq='W')

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
    _evaluate_prophet(daily, split=0.8)
    weekly, monthly = _prophet_forecast(daily)
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
