"""Monthly forecasting comparison -- Prophet vs Holt-Winters vs SARIMA --
reproducing the experimental setup of A. Siala's PFE (chapter 5, sec.
5.2.5 / 5.2.6) on the GamefyDB data.

Inputs:
    output/powerbi_star/fact_transaction_stationary.csv

For each series (Chiffre d'affaires, Nombre de clients):
    1. Aggregate to monthly, drop incomplete edge months.
    2. log(y) to stabilise variance (Amal sec. 5.2.3.2).
    3. 70 / 30 train / test split.
    4. Fit Prophet (yearly seasonality), Holt-Winters (add+add, m=12),
       SARIMA via auto_arima.
    5. Forecast the test horizon, exp() back to TND / count for scoring.
    6. RMSE, MAE, wMAPE on the original scale.

Outputs:
    docs/forecast_monthly_revenue_prophet.png
    docs/forecast_monthly_revenue_holtwinters.png
    docs/forecast_monthly_revenue_sarima.png
    docs/forecast_monthly_sessions_prophet.png
    docs/forecast_monthly_sessions_holtwinters.png
    docs/forecast_monthly_sessions_sarima.png
    docs/monthly_forecast_comparison.csv
"""
from __future__ import annotations
import os
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from prophet import Prophet
from pmdarima import auto_arima
from xgboost import XGBRegressor

warnings.filterwarnings('ignore')
import logging
logging.getLogger('prophet').setLevel(logging.WARNING)
logging.getLogger('cmdstanpy').setLevel(logging.WARNING)

FACT  = 'output/powerbi_star/fact_transaction_stationary.csv'
OUTD  = 'docs/forecasts_new'
CSV   = 'docs/forecasts_new/monthly_forecast_comparison.csv'
SPLIT = 0.70


def load_monthly() -> tuple[pd.Series, pd.Series]:
    tx = pd.read_csv(FACT, parse_dates=['transaction_datetime'])
    tx['month'] = tx['transaction_datetime'].dt.to_period('M').dt.to_timestamp()
    inc = tx[tx['income_expense'] == 'Income']
    rev = inc.groupby('month')['amount_tnd'].sum().sort_index()
    ses = tx.groupby('month').size().astype(float).sort_index()
    rev = rev[rev > 1000.0]
    ses = ses[ses > 100.0]
    rev.name = "Chiffre d'affaires"
    ses.name = 'Nombre de clients'
    return rev, ses


def split_70_30(s: pd.Series) -> tuple[pd.Series, pd.Series]:
    n = len(s)
    cut = max(int(n * SPLIT), 24)
    cut = min(cut, n - 3)
    return s.iloc[:cut], s.iloc[cut:]


def metrics(actual: np.ndarray, pred: np.ndarray) -> dict:
    err = actual - pred
    mae  = float(np.abs(err).mean())
    rmse = float(np.sqrt((err ** 2).mean()))
    wmape = float(np.abs(err).sum() / np.abs(actual).sum() * 100)
    return {'mae': mae, 'rmse': rmse, 'wmape': wmape}


def fit_prophet(train_log: pd.Series, horizon: int) -> pd.Series:
    df = pd.DataFrame({'ds': train_log.index, 'y': train_log.values})
    m = Prophet(yearly_seasonality=True, weekly_seasonality=False,
                daily_seasonality=False, interval_width=0.8)
    m.fit(df)
    future = m.make_future_dataframe(periods=horizon, freq='MS')
    fc = m.predict(future).tail(horizon)
    return pd.Series(fc['yhat'].values,
                     index=pd.DatetimeIndex(fc['ds'].values))


def fit_holtwinters(train_log: pd.Series, horizon: int) -> pd.Series:
    m = ExponentialSmoothing(train_log, trend='add', seasonal='add',
                              seasonal_periods=12).fit(optimized=True)
    fc = m.forecast(horizon)
    idx = pd.date_range(start=train_log.index[-1] + pd.offsets.MonthBegin(1),
                        periods=horizon, freq='MS')
    return pd.Series(fc.values, index=idx)


def _xgb_features(values: np.ndarray, dates: pd.DatetimeIndex,
                  i: int) -> dict:
    """Monthly features for XGBoost: lag_1..lag_3 + lag_12 + month + year-trend."""
    return {
        'lag_1':   float(values[i - 1]),
        'lag_2':   float(values[i - 2]),
        'lag_3':   float(values[i - 3]),
        'lag_12':  float(values[i - 12]) if i >= 12 else float(values[0]),
        'month':   int(dates[i].month),
        'trend':   int(i),
    }


def fit_xgboost(train_log: pd.Series, horizon: int) -> pd.Series:
    """Recursive monthly XGBoost on log-transformed series."""
    y = train_log.values.astype(float)
    dates_train = train_log.index
    min_lag = 12 if len(y) > 18 else 3

    X, Y = [], []
    for i in range(min_lag, len(y)):
        X.append(_xgb_features(y, dates_train, i))
        Y.append(y[i])
    if len(X) < 5:
        return pd.Series([np.nan] * horizon)

    model = XGBRegressor(n_estimators=200, learning_rate=0.05,
                         max_depth=3, subsample=0.9, colsample_bytree=0.9,
                         random_state=42, verbosity=0)
    model.fit(pd.DataFrame(X), Y)

    extended_values = y.tolist()
    fc_idx = pd.date_range(start=train_log.index[-1] + pd.offsets.MonthBegin(1),
                            periods=horizon, freq='MS')
    extended_dates = list(dates_train) + list(fc_idx)
    preds = []
    for k in range(horizon):
        i = len(extended_values)
        feat = _xgb_features(np.array(extended_values),
                             pd.DatetimeIndex(extended_dates), i)
        p = float(model.predict(pd.DataFrame([feat]))[0])
        preds.append(p)
        extended_values.append(p)
    return pd.Series(preds, index=fc_idx)


def fit_sarima(train_log: pd.Series, horizon: int) -> pd.Series:
    # D=0 forced: the series is already stationary after log transformation,
    # and the OCSB seasonal-differencing test needs >= 24 + m samples which
    # we do not have at monthly resolution.
    m = auto_arima(train_log, seasonal=True, m=12,
                   D=0, d=None, max_D=0,
                   stepwise=True, suppress_warnings=True,
                   error_action='ignore', information_criterion='aic',
                   max_p=2, max_q=2, max_P=1, max_Q=1)
    fc = m.predict(n_periods=horizon)
    idx = pd.date_range(start=train_log.index[-1] + pd.offsets.MonthBegin(1),
                        periods=horizon, freq='MS')
    return pd.Series(np.asarray(fc), index=idx)


def plot_amal(train_log, test_log, fc_log, fc_extra_log, ylabel, title, out):
    """Amal-style: log scale, Reel (blue solid) + Prevision (red dashed),
    forecast covers test horizon + extra months."""
    full_real = pd.concat([train_log, test_log]).sort_index()
    all_fc = pd.concat([fc_log, fc_extra_log]).sort_index()
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(full_real.index, full_real.values, color='blue', lw=1.4,
            label='Reel')
    ax.plot(all_fc.index, all_fc.values, color='red', lw=1.6, ls='--',
            label='Prevision')
    ax.axvline(test_log.index[0], color='gray', lw=0.7, ls=':')
    ax.set_title(title); ax.set_xlabel('Date'); ax.set_ylabel(ylabel)
    ax.legend(loc='upper left'); ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out, dpi=130, bbox_inches='tight'); plt.close(fig)


def evaluate_series(series: pd.Series, slug: str, label_fr: str,
                    extra_horizon: int = 24) -> list[dict]:
    log_s = np.log(series)
    train_log, test_log = split_70_30(log_s)
    test = series.loc[test_log.index]
    h = len(test_log) + extra_horizon

    rows = []
    fits = {
        'Prophet':       fit_prophet,
        'Holt-Winters':  fit_holtwinters,
        'SARIMA':        fit_sarima,
        'XGBoost':       fit_xgboost,
    }
    for name, fn in fits.items():
        fc_log_full = fn(train_log, h)
        fc_log_test  = fc_log_full.iloc[:len(test_log)]
        fc_log_extra = fc_log_full.iloc[len(test_log):]
        fc_test_raw  = np.exp(fc_log_test.values)
        m = metrics(test.values, fc_test_raw)
        rows.append({'serie': label_fr, 'modele': name, **m})
        out = os.path.join(OUTD,
            f'forecast_monthly_{slug}_{name.lower().replace("-","")}.png')
        plot_amal(train_log, test_log, fc_log_test, fc_log_extra,
                  ylabel=label_fr,
                  title=f'Prevision {name} - {label_fr} (mensuelle, log)',
                  out=out)
        print(f'  {name:<13}  RMSE={m["rmse"]:.2f}  MAE={m["mae"]:.2f}  '
              f'wMAPE={m["wmape"]:.1f}%   -> {os.path.basename(out)}')
    return rows


def main():
    os.makedirs(OUTD, exist_ok=True)
    rev, ses = load_monthly()
    print(f"Revenue  : {len(rev)} mois ({rev.index.min():%Y-%m} -> "
          f"{rev.index.max():%Y-%m}), mean={rev.mean():.0f} TND")
    print(f"Sessions : {len(ses)} mois ({ses.index.min():%Y-%m} -> "
          f"{ses.index.max():%Y-%m}), mean={ses.mean():.0f}")
    print()

    print(f"=== Chiffre d'affaires (mensuel, log) -- split {int(SPLIT*100)}/30 ===")
    rows_rev = evaluate_series(rev, 'revenue', "Chiffre d'affaires")
    print()
    print(f"=== Nombre de clients (mensuel, log) -- split {int(SPLIT*100)}/30 ===")
    rows_ses = evaluate_series(ses, 'sessions', 'Nombre de clients')

    df = pd.DataFrame(rows_rev + rows_ses)
    df.to_csv(CSV, index=False)
    print()
    print(f'Saved comparison table -> {CSV}')
    print()
    print('Best model per series (lowest wMAPE):')
    for serie, grp in df.groupby('serie'):
        best = grp.loc[grp['wmape'].idxmin()]
        print(f'  {serie:<22}  ->  {best["modele"]:<13} '
              f'(wMAPE {best["wmape"]:.1f}%, MAE {best["mae"]:.2f})')


if __name__ == '__main__':
    main()
