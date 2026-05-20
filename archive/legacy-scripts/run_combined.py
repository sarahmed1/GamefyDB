"""Run the forecasting + figures pipeline on the combined (real + synthetic) data.

Outputs:
  - output/forecasts_combined/   intermediate CSVs
  - output/figures_combined/     all PNG figures
"""
import os
os.environ.setdefault('MPLBACKEND', 'Agg')

import pandas as pd

from backend.packages.analytics.forecaster import (
    forecast_revenue,
    forecast_members,
    forecast_peak_hours,
    forecast_session_volume,
    study_stationarity,
)
from backend.packages.analytics.segmenter import segment_members, score_member_loyalty
from backend.packages.analytics.anomaly_detector import detect_anomalies
from backend.packages.analytics.figures import generate_all_figures


def _load_combined_transactions():
    """Load real + synthetic transactions with unified column names."""
    # Real star-schema data
    real = pd.read_csv('output/powerbi_star/fact_transaction.csv')
    real = real.rename(columns={
        'type': 'income_expense',
        'amount': 'amount_tnd',
        'date': 'transaction_datetime',
        'category': 'transaction_type',
        'payment': 'payment_method',
        'tx_id': 'transaction_id',
    })

    # Synthetic data (comma-decimal amounts)
    syn = pd.read_csv('fact_transaction_synthetic.csv')
    syn['amount_tnd'] = (
        syn['amount_tnd']
        .astype(str)
        .str.replace(',', '.', regex=False)
        .astype(float)
    )

    # Keep only common forecaster columns
    cols = [
        'transaction_id', 'cashier_id', 'terminal_id', 'item_id', 'member_id',
        'transaction_datetime', 'income_expense', 'payment_method',
        'transaction_type', 'amount_tnd',
    ]
    real_cols = [c for c in cols if c in real.columns]
    syn_cols = [c for c in cols if c in syn.columns]

    combined = pd.concat([real[real_cols], syn[syn_cols]], ignore_index=True)
    print(f'  Combined transactions: {len(combined)} rows '
          f'(real {len(real)} + synthetic {len(syn)})')
    return combined


def main():
    forecasts_dir = os.path.join('output', 'figures2')
    figures_dir = os.path.join('output', 'figures2')
    os.makedirs(forecasts_dir, exist_ok=True)
    os.makedirs(figures_dir, exist_ok=True)

    print('Loading combined transactions...')
    tx = _load_combined_transactions()

    print('Loading dim_member...')
    dim_member = pd.read_csv('output/powerbi_star/dim_member.csv', encoding='utf-8-sig')
    print(f'  dim_member: {len(dim_member)} rows')

    # ── Forecasting ──────────────────────────────────────────────────────────
    print()
    print('Forecasting (combined data)...')
    print('  Verdict thresholds — GOOD: MAPE < 10%  ACCEPTABLE: < 20%  POOR: > 20%')
    print()

    print('  Stationarity analysis...')
    study_stationarity(tx).to_csv(
        os.path.join(forecasts_dir, 'stationarity_tests.csv'), index=False
    )

    print('  Revenue...')
    forecast_revenue(tx).to_csv(
        os.path.join(forecasts_dir, 'forecast_revenue.csv'), index=False
    )

    print('  Member activity...')
    forecast_members(tx).to_csv(
        os.path.join(forecasts_dir, 'forecast_members.csv'), index=False
    )

    print('  Peak hours...')
    ph_hour, ph_day = forecast_peak_hours(tx)
    ph_hour.to_csv(os.path.join(forecasts_dir, 'peak_hours_by_hour.csv'), index=False)
    ph_day.to_csv(os.path.join(forecasts_dir, 'peak_hours_by_day.csv'), index=False)

    print('  Session volume...')
    forecast_session_volume(tx).to_csv(
        os.path.join(forecasts_dir, 'session_volume.csv'), index=False
    )

    print('  Member segmentation...')
    segments = segment_members(dim_member)
    segments.to_csv(
        os.path.join(forecasts_dir, 'member_segments.csv'), index=False, encoding='utf-8-sig'
    )
    for label, count in segments['segment_label'].value_counts().items():
        print(f'    {label}: {count} members')

    print('  Member loyalty scoring...')
    loyalty = score_member_loyalty(dim_member)
    loyalty.to_csv(
        os.path.join(forecasts_dir, 'member_loyalty.csv'), index=False, encoding='utf-8-sig'
    )
    for tier, count in loyalty['loyalty_tier'].value_counts().items():
        print(f'    {tier}: {count} members')

    print('  Anomaly detection...')
    anomalies = detect_anomalies(tx)
    anomalies.to_csv(os.path.join(forecasts_dir, 'anomalies.csv'), index=False)
    for label in ['revenue', 'session_volume', 'member_activity']:
        subset = anomalies[anomalies['series'] == label]
        n = len(subset)
        if n == 0:
            print(f'    [{label}]  no anomalies detected')
        else:
            severe = int((subset['severity'] == 'severe').sum())
            print(f'    [{label}]  {n} anomalies — {severe} severe, {n - severe} mild')

    print(f'  Forecasts written to {forecasts_dir}/')

    # ── Figures ──────────────────────────────────────────────────────────────
    print()
    print('Generating figures (combined data)...')
    generate_all_figures(tx, dim_member, forecasts_dir, figures_dir)
    print(f'  Figures written to {figures_dir}/')

    print()
    print('Done.')


if __name__ == '__main__':
    main()

