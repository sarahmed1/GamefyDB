import numpy as np
import pandas as pd

from gamefydb.forecaster import _to_daily


_COLS = ['date', 'series', 'weekday', 'actual',
         'weekday_mean', 'weekday_std', 'z_score', 'direction', 'severity']


def _flag_series(daily_df: pd.DataFrame, label: str, threshold: float = 2.0) -> pd.DataFrame:
    df = daily_df.copy()
    df['weekday'] = df['ds'].dt.day_name()

    stats = (
        df.groupby('weekday')['y']
        .agg(['mean', 'std', 'count'])
        .reset_index()
        .rename(columns={'mean': 'weekday_mean', 'std': 'weekday_std', 'count': '_n'})
    )

    df = df.merge(stats, on='weekday')
    df = df[(df['_n'] >= 4) & (df['weekday_std'] > 0)].copy()

    if df.empty:
        return pd.DataFrame(columns=_COLS)

    df['z_score'] = ((df['y'] - df['weekday_mean']) / df['weekday_std']).round(2)
    df = df[df['z_score'].abs() >= threshold].copy()

    if df.empty:
        return pd.DataFrame(columns=_COLS)

    df['series'] = label
    df['direction'] = df['z_score'].apply(lambda z: 'high' if z > 0 else 'low')
    df['severity'] = df['z_score'].abs().apply(lambda z: 'severe' if z > 3.0 else 'mild')
    df['date'] = df['ds'].dt.date
    df['actual'] = df['y'].round(2)
    df['weekday_mean'] = df['weekday_mean'].round(2)
    df['weekday_std'] = df['weekday_std'].round(2)

    return df[_COLS]


def detect_anomalies(transactions_df: pd.DataFrame, threshold: float = 2.0) -> pd.DataFrame:
    income = transactions_df[transactions_df['income_expense'] == 'Income'].copy()
    income['_v'] = income['amount_tnd']
    revenue_daily = _to_daily(income, 'transaction_datetime', '_v')

    sessions = transactions_df.copy()
    sessions['_v'] = 1
    sessions_daily = _to_daily(sessions, 'transaction_datetime', '_v')

    members = transactions_df[
        transactions_df['transaction_type'] == 'Member Transactions'
    ].copy()
    members['_v'] = 1
    members_daily = _to_daily(members, 'transaction_datetime', '_v')

    frames = [
        _flag_series(revenue_daily, 'revenue', threshold),
        _flag_series(sessions_daily, 'session_volume', threshold),
        _flag_series(members_daily, 'member_activity', threshold),
    ]
    frames = [f for f in frames if not f.empty]

    if not frames:
        return pd.DataFrame(columns=_COLS)

    result = pd.concat(frames, ignore_index=True)
    return result.iloc[result['z_score'].abs().argsort()[::-1]].reset_index(drop=True)
