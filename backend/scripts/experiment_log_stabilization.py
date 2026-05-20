"""A/B experiment: does log-stabilization of the target improve forecast
accuracy on the GamefyDB series?

For each forecast series (revenue, sessions, members), we run Prophet and
XGBoost twice:
    - baseline: fit on raw y
    - log:      fit on log(1+y), exp(yhat)-1 back to raw scale for scoring

Both variants are scored on the SAME test split, in the SAME raw units
(TND or transaction count), so wMAPE is directly comparable.

The point of stabilisation is to flatten the variance, which can help
Prophet's residual model (and XGBoost's MSE loss) when the series is
heteroscedastic. This script measures the effect empirically -- if log
wins, we wire it into forecaster.py for production.
"""
from __future__ import annotations
import os
import sys
import warnings
import numpy as np
import pandas as pd

warnings.filterwarnings('ignore')

# Allow `python scripts/experiment_log_stabilization.py` from repo root
sys.path.insert(0, os.getcwd())

from backend.packages.analytics.forecaster import (
    _to_daily, _to_weekly, _evaluate_prophet, _evaluate_xgboost,
)

FACT_PATH = 'output/powerbi_star/fact_transaction_combined_v2.csv'


def run_with_log(df: pd.DataFrame, fn, **kwargs) -> dict:
    """Run an evaluator on log(1+y), then convert MAE/RMSE back to raw scale.

    Important: we must compute wMAPE on the raw-scale residuals so it is
    comparable to the baseline. The evaluator returns MAE/MAPE on whatever
    scale it was trained on; here we re-evaluate manually on raw scale.
    """
    df_log = df.copy()
    df_log['y'] = np.log1p(df['y'])

    # Patch: evaluators compute mape internally; we need raw-scale numbers.
    # Easiest path is to monkey-fit by replicating the predict step. Instead,
    # we re-run the evaluator on log series but then convert via mean trick:
    #   for log fit, m['mape'] is on log scale. To get raw-scale wMAPE we
    #   need to redo prediction. Simpler: re-implement minimally below.
    raise NotImplementedError('Use the dedicated _eval_*_log helpers below.')


def _eval_prophet_log(df: pd.DataFrame, split: float, freq: str = 'D') -> dict:
    """Prophet fit on log1p(y), scored on raw scale."""
    from prophet import Prophet
    from backend.packages.analytics.forecaster import _build_holiday_df

    n = len(df)
    cutoff = int(n * split)
    if cutoff < 2 or n - cutoff < 2:
        return {}
    train = df.iloc[:cutoff].copy()
    test  = df.iloc[cutoff:].copy()
    train['y'] = np.log1p(train['y'].astype(float))

    holiday_df = _build_holiday_df(df['ds'].min(), df['ds'].max())
    m = Prophet(interval_width=0.8,
                holidays=holiday_df if holiday_df is not None else None,
                holidays_prior_scale=20.0)
    m.fit(train)
    future = m.make_future_dataframe(periods=len(test), freq=freq)
    fc = m.predict(future)[['ds', 'yhat']]
    fc['yhat'] = np.expm1(fc['yhat']).clip(lower=0.0)

    merged = test.merge(fc, on='ds', how='inner')
    if merged.empty:
        return {}
    err = merged['y'].astype(float) - merged['yhat']
    mae  = float(err.abs().mean())
    rmse = float((err ** 2).mean() ** 0.5)
    mean_actual = float(merged['y'].astype(float).mean())
    mape = (mae / mean_actual * 100) if mean_actual > 0 else float('nan')
    return {'mae': mae, 'mape': mape, 'rmse': rmse}


def _eval_xgboost_log(df: pd.DataFrame, split: float) -> dict:
    """XGBoost fit on log1p(y), scored on raw scale.

    Implementation note: the XGBoost evaluator's recursive prediction loop
    references lag features built from the same target. When fitting on
    log scale, lags must also be in log scale (consistent feature space),
    then expm1 the final prediction.
    """
    from xgboost import XGBRegressor
    from backend.packages.analytics.forecaster import (
        _xgb_features, _build_holiday_df, _holiday_proximity,
    )
    n = len(df)
    cutoff = int(n * split)
    if cutoff < 34 or n - cutoff < 2:
        return None

    ds_arr = df['ds'].values
    y_raw  = df['y'].values.astype(float)
    y_log  = np.log1p(y_raw)

    holiday_df = _build_holiday_df(df['ds'].min(), df['ds'].max())
    proximity  = _holiday_proximity(ds_arr, holiday_df)

    X_train, y_train = [], []
    for i in range(14, cutoff):
        X_train.append(_xgb_features(i, y_log, ds_arr, proximity))
        y_train.append(y_log[i])
    if len(X_train) < 10:
        return None

    model = XGBRegressor(n_estimators=300, learning_rate=0.05,
                         max_depth=5, subsample=0.8, colsample_bytree=0.8,
                         random_state=42, verbosity=0)
    model.fit(pd.DataFrame(X_train), y_train)

    y_extended = y_log[:cutoff].tolist()
    preds_log = []
    for i in range(cutoff, n):
        feat = _xgb_features(i, np.array(y_extended), ds_arr, proximity)
        p = float(model.predict(pd.DataFrame([feat]))[0])
        preds_log.append(p)
        y_extended.append(p)

    preds_raw = np.expm1(np.array(preds_log)).clip(min=0.0)
    actual = y_raw[cutoff:]
    err = actual - preds_raw
    mae  = float(np.abs(err).mean())
    rmse = float(np.sqrt((err ** 2).mean()))
    mean_actual = float(actual.mean())
    mape = (mae / mean_actual * 100) if mean_actual > 0 else float('nan')
    return {'mae': mae, 'mape': mape, 'rmse': rmse}


def verdict(p):
    if p is None or p != p:
        return '----'
    return 'GOOD' if p < 20 else ('ACCEPTABLE' if p < 50 else 'POOR')


def report(label, baseline, logfit):
    print(f'\n  [{label}]')
    if baseline:
        print(f'    raw target  : wMAPE {baseline["mape"]:5.1f}%  '
              f'MAE {baseline["mae"]:8.2f}  RMSE {baseline["rmse"]:8.2f}  '
              f'-> {verdict(baseline["mape"])}')
    else:
        print('    raw target  : (failed)')
    if logfit:
        delta = (logfit['mape'] - baseline['mape']) if baseline else 0
        arrow = 'better' if delta < 0 else 'worse '
        print(f'    log target  : wMAPE {logfit["mape"]:5.1f}%  '
              f'MAE {logfit["mae"]:8.2f}  RMSE {logfit["rmse"]:8.2f}  '
              f'-> {verdict(logfit["mape"])}  ({arrow} by {abs(delta):4.1f} pts)')
    else:
        print('    log target  : (failed)')


def main():
    print(f'Loading {FACT_PATH}...')
    tx_df = pd.read_csv(FACT_PATH, parse_dates=['transaction_datetime'])
    print(f'  Transactions: {len(tx_df):,} rows ('
          f'{tx_df["transaction_datetime"].min():%Y-%m-%d} -> '
          f'{tx_df["transaction_datetime"].max():%Y-%m-%d})')

    income = tx_df[tx_df['income_expense'] == 'Income'].copy()
    income['_v'] = income['amount_tnd']
    rev_daily  = _to_daily(income, 'transaction_datetime', '_v')
    rev_weekly = _to_weekly(rev_daily)

    vol = tx_df.copy()
    vol['_v'] = 1
    vol_daily  = _to_daily(vol, 'transaction_datetime', '_v')
    vol_weekly = _to_weekly(vol_daily)

    members = tx_df[tx_df['transaction_type'] == 'Member Transactions'].copy()
    members['_v'] = 1
    mem_daily  = _to_daily(members, 'transaction_datetime', '_v')
    mem_weekly = _to_weekly(mem_daily)

    print('\n=== Prophet baseline vs log-stabilized (weekly target) ===')
    for label, df in [('Revenue (TND, weekly)', rev_weekly),
                      ('Session volume (weekly)', vol_weekly),
                      ('Member activity (weekly)', mem_weekly)]:
        base = _evaluate_prophet(df, split=0.8, freq='7D')
        logf = _eval_prophet_log(df,  split=0.8, freq='7D')
        report(f'Prophet -- {label}', base, logf)

    print('\n=== XGBoost baseline vs log-stabilized (daily target) ===')
    for label, df in [('Revenue (TND, daily)', rev_daily),
                      ('Session volume (daily)', vol_daily)]:
        base = _evaluate_xgboost(df, split=0.8)
        logf = _eval_xgboost_log(df,  split=0.8)
        report(f'XGBoost -- {label}', base, logf)

    print('\nDone. If log wins on the production series, wire `use_log=True`')
    print('into _evaluate_prophet / _prophet_forecast in forecaster.py.')


if __name__ == '__main__':
    main()




