"""Reproduit la demarche complete de A. Siala (PFE chap. 5, sec. 5.2.3 ->
5.2.5.1) directement sur les donnees GamefyDB stabilisees.

Demarche :
    1. Charger la serie mensuelle (Chiffre d'affaires + Nombre de clients)
       depuis fact_transaction_combined_v2.csv -- desormais stationnaire
       et tres faiblement bruitee (CV daily ~ 4 %).
    2. Test ADF sur la serie brute.
    3. Transformation logarithmique pour stabiliser la variance.
    4. Re-test ADF sur la serie log.
    5. Decoupage 70 % entrainement / 30 % test.
    6. Holt-Winters additif (saisonnalite 12 mois) sur la portion train.
    7. Prevision sur le test + 24 mois.
    8. Graphique "Reel" (bleu) / "Prevision" (rouge pointille), meme
       presentation que les figures 5.6 et 5.7 d'Amal.

Sorties :
    docs/forecast_holtwinters_revenue.png
    docs/forecast_holtwinters_sessions.png
    docs/stationarity_tests_amal.csv
"""
from __future__ import annotations
import os
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from statsmodels.tsa.stattools import adfuller
from statsmodels.tsa.holtwinters import ExponentialSmoothing

warnings.filterwarnings('ignore')

FACT = 'output/powerbi_star/fact_transaction_stationary.csv'
OUT_REV = 'docs/forecasts_new/forecast_holtwinters_revenue.png'
OUT_SES = 'docs/forecasts_new/forecast_holtwinters_sessions.png'
OUT_CSV = 'docs/forecasts_new/stationarity_tests_amal.csv'

tx = pd.read_csv(FACT, parse_dates=['transaction_datetime'])
tx['month'] = tx['transaction_datetime'].dt.to_period('M').dt.to_timestamp()

income = tx[tx['income_expense'] == 'Income']
rev_m = (income.groupby('month')['amount_tnd'].sum()
         .asfreq('MS').dropna())
ses_m = (tx.groupby('month').size().astype(float)
         .asfreq('MS').dropna())

# Exclude any incomplete edge months (first / last partial)
rev_m = rev_m[rev_m > 1000.0]
ses_m = ses_m[ses_m > 100.0]
rev_m.name = "Chiffre d'affaires"
ses_m.name = 'Nombre de clients'


def adf_p(s: pd.Series, regression: str = 'c') -> float:
    try:
        return adfuller(s.dropna().values, autolag='AIC',
                        regression=regression)[1]
    except Exception:
        return float('nan')


log_rev = np.log(rev_m)
log_ses = np.log(ses_m)

p_rev_raw, p_rev_log = adf_p(rev_m, 'c'), adf_p(log_rev, 'c')
p_ses_raw, p_ses_log = adf_p(ses_m, 'c'), adf_p(log_ses, 'c')

pd.DataFrame([
    {'serie': "Chiffre d'affaires", 'transformation': 'brute',
     'adf_pvalue': p_rev_raw, 'stationnaire': p_rev_raw < 0.05},
    {'serie': "Chiffre d'affaires", 'transformation': 'log',
     'adf_pvalue': p_rev_log, 'stationnaire': p_rev_log < 0.05},
    {'serie': 'Nombre de clients',  'transformation': 'brute',
     'adf_pvalue': p_ses_raw, 'stationnaire': p_ses_raw < 0.05},
    {'serie': 'Nombre de clients',  'transformation': 'log',
     'adf_pvalue': p_ses_log, 'stationnaire': p_ses_log < 0.05},
]).to_csv(OUT_CSV, index=False)


def holt_winters_forecast(log_series: pd.Series,
                          horizon_extra_months: int = 24
                          ) -> tuple[pd.Series, pd.Series]:
    """Decoupage 70/30 + Holt-Winters additif (saisonnalite 12 mois).
    Si la serie est courte (< 2 cycles + 70%) on entraine sur tout."""
    n = len(log_series)
    cut = max(int(n * 0.70), 24)
    if cut >= n - 2:
        cut = n  # entire series as training
    train = log_series.iloc[:cut]
    test_len = max(0, n - cut)
    fc_len = test_len + horizon_extra_months
    model = ExponentialSmoothing(train, trend='add', seasonal='add',
                                 seasonal_periods=12).fit(optimized=True)
    fc_values = model.forecast(fc_len)
    fc_idx = pd.date_range(start=train.index[-1] + pd.offsets.MonthBegin(1),
                            periods=fc_len, freq='MS')
    fc = pd.Series(fc_values.values, index=fc_idx)
    return train, fc


def plot_amal_style(log_series: pd.Series, fc: pd.Series, ylabel: str,
                    title: str, out_path: str) -> None:
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(log_series.index, log_series.values, color='blue', lw=1.4,
            label='Reel')
    ax.plot(fc.index, fc.values, color='red', lw=1.6, ls='--',
            label='Prevision')
    ax.set_title(title)
    ax.set_xlabel('Date')
    ax.set_ylabel(ylabel)
    ax.legend(loc='upper left')
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=130, bbox_inches='tight')
    plt.close(fig)


train_r, fc_r = holt_winters_forecast(log_rev, horizon_extra_months=24)
plot_amal_style(log_rev, fc_r, ylabel="Chiffre d'affaires",
                title='Prevision Holt-Winters', out_path=OUT_REV)

train_s, fc_s = holt_winters_forecast(log_ses, horizon_extra_months=24)
plot_amal_style(log_ses, fc_s, ylabel='Nombre de clients',
                title='Prevision Holt-Winters - Nombre de clients',
                out_path=OUT_SES)

os.makedirs(os.path.dirname(OUT_REV), exist_ok=True)
print(f'Saved: {OUT_REV}')
print(f'Saved: {OUT_SES}')
print(f'Saved: {OUT_CSV}')
print()
print(f"Serie mensuelle    : {rev_m.index.min():%Y-%m} -> {rev_m.index.max():%Y-%m} "
      f'({len(rev_m)} mois reels)')
print(f"Train Holt-Winters : {train_r.index.min():%Y-%m} -> {train_r.index.max():%Y-%m} "
      f'({len(train_r)} mois)')
print(f"Prevision          : {fc_r.index.min():%Y-%m} -> {fc_r.index.max():%Y-%m} "
      f'({len(fc_r)} mois)')
print()
print('Test ADF (H0 = non stationnaire) :')
print(f"  Chiffre d'affaires brute  : p = {p_rev_raw:.4g}  -> "
      f"{'STATIONNAIRE' if p_rev_raw < 0.05 else 'NON STATIONNAIRE'}")
print(f"  Chiffre d'affaires log    : p = {p_rev_log:.4g}  -> "
      f"{'STATIONNAIRE' if p_rev_log < 0.05 else 'NON STATIONNAIRE'}")
print(f"  Nombre de clients  brute  : p = {p_ses_raw:.4g}  -> "
      f"{'STATIONNAIRE' if p_ses_raw < 0.05 else 'NON STATIONNAIRE'}")
print(f"  Nombre de clients  log    : p = {p_ses_log:.4g}  -> "
      f"{'STATIONNAIRE' if p_ses_log < 0.05 else 'NON STATIONNAIRE'}")
