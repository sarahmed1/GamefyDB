import os
os.environ.setdefault('MPLBACKEND', 'Agg')

import argparse

import pandas as pd

from gamefydb.pipeline import run_pipeline
from gamefydb.forecaster import (
    forecast_revenue,
    forecast_members,
    forecast_peak_hours,
    forecast_session_volume,
    forecast_stock_replenishment,
    study_stationarity,
)
from gamefydb.segmenter import segment_members, score_member_loyalty
from gamefydb.anomaly_detector import detect_anomalies
from gamefydb.figures import generate_all_figures


def _print_anomaly_summary(anomalies: pd.DataFrame) -> None:
    for label in ['revenue', 'session_volume', 'member_activity']:
        subset = anomalies[anomalies['series'] == label]
        n = len(subset)
        if n == 0:
            print(f'    [{label}]  no anomalies detected')
            continue
        severe = int((subset['severity'] == 'severe').sum())
        mild = n - severe
        noun = 'anomaly' if n == 1 else 'anomalies'
        print(f'    [{label}]  {n} {noun} — {severe} severe, {mild} mild')
        w = subset.iloc[0]
        print(f'      Worst: {w["date"]} {str(w["weekday"])[:3]}'
              f'  actual={w["actual"]}'
              f'  expected={w["weekday_mean"]}'
              f'  z={w["z_score"]:+.2f} ({w["severity"]}, {w["direction"]})')


def main():
    parser = argparse.ArgumentParser(description='GamefyDB PFE — clean + star schema + forecast')
    parser.add_argument('--input',  default='excel',  help='Directory with .xls source files')
    parser.add_argument('--output', default='output', help='Output directory')
    args = parser.parse_args()

    print('Loading and cleaning...')
    schema, cash, stock = run_pipeline(args.input)

    print('Writing star schema...')
    star_dir = os.path.join(args.output, 'powerbi_star')
    os.makedirs(star_dir, exist_ok=True)
    for name, df in schema.items():
        df.to_csv(os.path.join(star_dir, f'{name}.csv'), index=False, encoding='utf-8-sig')
        print(f'  {name}: {len(df)} rows')

    print('Forecasting...')
    print('  Note: each model is evaluated on an 80/20 chronological train/test split')
    print('  (first 80% of historical data trains the model, last 20% is held out')
    print('   and compared against real recorded values to measure accuracy)')
    print('  Metric: wMAPE (weighted MAPE = MAE / mean_actual) — stable for volatile data')
    print('  Verdict thresholds — GOOD: wMAPE < 20%  ACCEPTABLE: < 50%  POOR: > 50%')
    print()
    forecasts_dir = os.path.join(args.output, 'forecasts')
    os.makedirs(forecasts_dir, exist_ok=True)

    # Rename star schema columns to match forecaster expectations
    tx = schema['fact_transaction'].rename(columns={
        'type': 'income_expense',
        'amount': 'amount_tnd',
        'date': 'transaction_datetime',
        'category': 'transaction_type',
    })

    # Cleaned stock rows (individual movements) for replenishment
    stock_mv = stock.rename(columns={'date': 'movement_datetime'})

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

    print('  Stock replenishment...')
    forecast_stock_replenishment(stock_mv).to_csv(
        os.path.join(forecasts_dir, 'stock_replenishment.csv'), index=False
    )

    print('  Member segmentation...')
    segments = segment_members(schema['dim_member'])
    segments.to_csv(
        os.path.join(forecasts_dir, 'member_segments.csv'), index=False, encoding='utf-8-sig'
    )
    for label, count in segments['segment_label'].value_counts().items():
        print(f'    {label}: {count} members')

    print('  Member loyalty scoring...')
    loyalty = score_member_loyalty(schema['dim_member'])
    loyalty.to_csv(
        os.path.join(forecasts_dir, 'member_loyalty.csv'), index=False, encoding='utf-8-sig'
    )
    for tier, count in loyalty['loyalty_tier'].value_counts().items():
        print(f'    {tier}: {count} members')

    print('  Anomaly detection...')
    anomalies = detect_anomalies(tx)
    _print_anomaly_summary(anomalies)
    anomalies.to_csv(os.path.join(forecasts_dir, 'anomalies.csv'), index=False)

    print(f'  Forecasts written to {forecasts_dir}/')

    print('Generating figures...')
    figures_dir = os.path.join('docs')
    generate_all_figures(tx, schema['dim_member'], forecasts_dir, figures_dir)
    print(f'  Figures written to {figures_dir}/')

    print('Done.')


if __name__ == '__main__':
    main()
