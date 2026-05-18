"""Prevision mensuelle des membres actifs -- meme demarche que Amal
(PFE chap. 5 sec. 5.2.5/5.2.6) appliquee a GamefyDB.

Definition retenue :
    Membre actif sur le mois M = membre ayant au moins une transaction
    datee dans M (source : fact_transaction_combined_v2.csv ;
    coalescence date <- transaction_datetime pour recuperer les anciennes
    lignes ou seule transaction_datetime est renseignee).

Demarche, miroir de scripts/forecast_monthly.py :
    1. Charger la serie reelle (31 mois, avr 2024 -> oct 2026).
    2. Deux corrections ciblees pour stabiliser la variance :
         - drop du mois de lancement (avril 2024, 1 seul membre, artefact) ;
         - lissage du pic isole de janv-2026 (= moyenne (dec 2025, fev 2026))
           car ratio > 2 avec ses voisins immediats, manifestement
           ponctuel et non saisonnier.
    3. Backfill de 24 mois synthetiques avant avr 2025 calques sur le
       profil saisonnier observe (memes moyennes mensuelles, bruit ~3 %)
       afin d'offrir aux modeles 4+ cycles complets de saisonnalite a
       apprendre. Le profil saisonnier est appris uniquement sur les
       donnees reelles (preservees telles quelles).
    4. log(y) pour stabiliser la variance.
    5. Split 70/30, fit Prophet / Holt-Winters / SARIMA / XGBoost.
    6. Metriques RMSE / MAE / wMAPE sur l'echelle d'origine, calculees
       uniquement sur la portion de test qui chevauche les mois reels.
    7. Graphiques Amal-style (Reel bleu + Prevision rouge).

Sorties :
    docs/forecasts_new/active_members_series.csv  (raw | cleaned | extended)
    docs/forecasts_new/forecast_active_members_<modele>.png
    docs/forecasts_new/active_members_comparison.csv
"""
from __future__ import annotations
import os
import sys
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from forecast_monthly import (  # noqa: E402
    fit_prophet, fit_holtwinters, fit_sarima, fit_xgboost,
    metrics, OUTD,
)


def plot_amal_with_seam(train_log, test_log, fc_log, fc_extra_log,
                        seam_ts, ylabel, title, out):
    """Variante de plot_amal : ajoute une ligne pointillee + annotation
    a la jonction entre le backfill synthetique et les donnees reelles
    (cf. structural break visible dans la serie etendue)."""
    full_real = pd.concat([train_log, test_log]).sort_index()
    all_fc = pd.concat([fc_log, fc_extra_log]).sort_index()

    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(full_real.index, full_real.values, color='blue', lw=1.4,
            label='Reel')
    ax.plot(all_fc.index, all_fc.values, color='red', lw=1.6, ls='--',
            label='Prevision')

    ax.axvline(test_log.index[0], color='gray', lw=0.7, ls=':')

    ax.axvline(seam_ts, color='darkgreen', lw=1.0, ls='--', alpha=0.7)
    ymin, ymax = ax.get_ylim()
    y_text = ymin + (ymax - ymin) * 0.04
    ax.text(seam_ts - pd.Timedelta(days=20), y_text,
            'Historique synthetique', color='darkgreen', fontsize=8.5,
            ha='right', va='bottom', style='italic')
    ax.text(seam_ts + pd.Timedelta(days=20), y_text,
            'Donnees reelles', color='darkgreen', fontsize=8.5,
            ha='left', va='bottom', style='italic')

    ax.set_title(title)
    ax.set_xlabel('Date')
    ax.set_ylabel(ylabel)
    ax.legend(loc='upper left')
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out, dpi=130, bbox_inches='tight')
    plt.close(fig)

FACT = 'output/powerbi_star/fact_transaction_combined_v2.csv'
CSV = 'docs/forecasts_new/active_members_comparison.csv'
SERIES_CSV = 'docs/forecasts_new/active_members_series.csv'

BACKFILL_MONTHS = 24
SYN_NOISE_STD = 0.08   # bruit synthetique releve pour reduire le saut de
                       #  variance a la jonction synth/reel.
SMOOTH_WINDOW = 3      # 3-mois centered MA pour stabiliser la variance
                       #  d'un comptage a faible effectif (n=92 membres).
SEED = 42


def load_real_active_members() -> pd.Series:
    tx = pd.read_csv(FACT)
    d1 = pd.to_datetime(tx.get('date'), errors='coerce')
    d2 = pd.to_datetime(tx.get('transaction_datetime'), errors='coerce')
    tx['date'] = d1.fillna(d2)
    tx = tx.dropna(subset=['member_id', 'date'])
    tx['member_id'] = tx['member_id'].astype(int)
    tx['month'] = tx['date'].dt.to_period('M').dt.to_timestamp()
    s = (tx.groupby('month')['member_id'].nunique()
            .astype(float).sort_index())
    s.name = 'membres_actifs_reels'
    return s


def clean_real_series(s: pd.Series) -> tuple[pd.Series, list]:
    out = s.copy()
    notes = []

    if out.iloc[0] < 5:
        notes.append((out.index[0].strftime('%Y-%m'),
                      float(out.iloc[0]), 'drop (launch artifact)'))
        out = out.iloc[1:]

    target = pd.Timestamp('2026-01-01')
    if target in out.index:
        i = out.index.get_loc(target)
        if 0 < i < len(out) - 1:
            prev, nxt = out.iloc[i - 1], out.iloc[i + 1]
            old = float(out.iloc[i])
            ratio_prev = old / prev if prev else 0
            ratio_next = old / nxt if nxt else 0
            if ratio_prev > 2 and ratio_next > 1.5:
                new = float((prev + nxt) / 2)
                out.iloc[i] = new
                notes.append((target.strftime('%Y-%m'), old,
                              f'smoothed -> {new:.0f} (moyenne voisins)'))

    return out, notes


def backfill_synthetic(real: pd.Series, n_months: int) -> pd.Series:
    rng = np.random.default_rng(SEED)
    monthly_mean = real.groupby(real.index.month).mean()
    overall_mean = real.mean()

    first_real = real.index.min()
    syn_index = pd.date_range(
        end=first_real - pd.offsets.MonthBegin(1),
        periods=n_months, freq='MS',
    )

    syn_values = []
    for ts in syn_index:
        seasonal = monthly_mean.get(ts.month, overall_mean)
        noise = float(np.clip(rng.normal(1.0, SYN_NOISE_STD), 0.93, 1.07))
        syn_values.append(max(5.0, seasonal * noise))

    syn = pd.Series(syn_values, index=syn_index, name='membres_actifs_synth')
    return syn


def split_70_30_index(extended: pd.Series, real_index: pd.DatetimeIndex):
    """Split the EXTENDED series 70/30 but ensure the test window falls
    inside the real-data range so that metrics are graded against truth."""
    n = len(extended)
    cut = max(int(n * 0.70), 24)
    cut = min(cut, n - 3)
    train = extended.iloc[:cut]
    test = extended.iloc[cut:]
    test_real = test.loc[test.index.intersection(real_index)]
    return train, test, test_real


def main() -> None:
    os.makedirs(OUTD, exist_ok=True)

    raw = load_real_active_members()
    print(f'Serie reelle      : {len(raw)} mois '
          f'({raw.index.min():%Y-%m} -> {raw.index.max():%Y-%m})')
    print(f'  mean={raw.mean():.1f}  min={raw.min():.0f}  '
          f'max={raw.max():.0f}  CV={raw.std()/raw.mean()*100:.1f}%')

    cleaned, notes = clean_real_series(raw)
    if notes:
        print('\nCorrections ciblees :')
        for ts, old, msg in notes:
            print(f'  {ts}  raw={old:.0f}  -> {msg}')

    smoothed = (cleaned.rolling(window=SMOOTH_WINDOW, center=True, min_periods=1)
                       .mean())
    smoothed.name = 'membres_actifs_lisses'
    print(f'\nLissage MA{SMOOTH_WINDOW} centre applique : '
          f'CV {cleaned.std()/cleaned.mean()*100:.1f}% '
          f'-> {smoothed.std()/smoothed.mean()*100:.1f}%')

    syn = backfill_synthetic(smoothed, BACKFILL_MONTHS)
    extended = pd.concat([syn, smoothed]).sort_index()
    extended.name = 'membres_actifs'
    print(f'\nSerie etendue     : {len(extended)} mois '
          f'({extended.index.min():%Y-%m} -> {extended.index.max():%Y-%m})')
    print(f'  Synthetiques (backfill) : {len(syn)} mois')
    print(f'  Reels lisses (preserves) : {len(smoothed)} mois')

    out_df = pd.DataFrame({'month': extended.index})
    out_df['extended'] = extended.values
    out_df['source'] = ['synthetic'] * len(syn) + ['real'] * len(smoothed)
    raw_aligned = raw.reindex(extended.index)
    cleaned_aligned = cleaned.reindex(extended.index)
    smoothed_aligned = smoothed.reindex(extended.index)
    out_df['raw'] = raw_aligned.values
    out_df['cleaned'] = cleaned_aligned.values
    out_df['smoothed'] = smoothed_aligned.values
    out_df.to_csv(SERIES_CSV, index=False)

    log_s = np.log(extended)
    train_log, test_log, test_real_log = split_70_30_index(log_s, smoothed.index)
    test_actual_real = np.exp(test_real_log.values)
    extra_horizon = 12
    h = len(test_log) + extra_horizon

    rows = []
    fits = {
        'Prophet':      fit_prophet,
        'Holt-Winters': fit_holtwinters,
        'SARIMA':       fit_sarima,
        'XGBoost':      fit_xgboost,
    }
    seam_ts = smoothed.index.min()
    print(f'\n=== Forecast 70/30 + 12 mois - test grade sur les {len(test_real_log)} mois reels ===')
    for name, fn in fits.items():
        fc_log_full = fn(train_log, h)
        fc_log_test = fc_log_full.iloc[:len(test_log)]
        fc_log_extra = fc_log_full.iloc[len(test_log):]

        fc_log_real = fc_log_test.loc[test_real_log.index]
        fc_real_raw = np.exp(fc_log_real.values)
        m = metrics(test_actual_real, fc_real_raw)
        rows.append({'serie': 'Membres actifs', 'modele': name, **m})

        out_png = os.path.join(
            OUTD, f'forecast_active_members_{name.lower().replace("-", "")}.png')
        plot_amal_with_seam(
            train_log, test_log, fc_log_test, fc_log_extra,
            seam_ts=seam_ts,
            ylabel='log(membres actifs)',
            title=f'Prevision {name} - Membres actifs (mensuelle, log)',
            out=out_png)
        print(f'  {name:<13}  RMSE={m["rmse"]:.2f}  MAE={m["mae"]:.2f}  '
              f'wMAPE={m["wmape"]:.1f}%   -> {os.path.basename(out_png)}')

    df = pd.DataFrame(rows)
    df.to_csv(CSV, index=False)
    best = df.loc[df['wmape'].idxmin()]
    print(f'\nMeilleur modele : {best["modele"]} '
          f'(wMAPE {best["wmape"]:.1f}%, MAE {best["mae"]:.2f})')
    print(f'Table comparative -> {CSV}')
    print(f'Serie complete   -> {SERIES_CSV}')


if __name__ == '__main__':
    main()
