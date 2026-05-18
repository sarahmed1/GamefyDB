"""Cohort retention analysis on GamefyDB members.

Demarche (inspire des analyses RFM/cohortes classiques en retail) :
    1. Charger fact_transaction_combined_v2.csv (seule table avec dates).
    2. Pour chaque membre, identifier le mois de premiere transaction = mois de cohorte.
    3. Construire la matrice de retention : pour chaque (cohorte, offset_mois),
       compter la part de membres actifs (au moins 1 tx dans le mois).
    4. Tracer la heatmap triangulaire + courbes de retention par cohorte.
    5. Exporter la matrice et un resume CSV.

Sorties :
    docs/members_new/cohort_retention_heatmap.png
    docs/members_new/cohort_retention_curves.png
    docs/members_new/cohort_retention_matrix.csv
    docs/members_new/cohort_summary.csv
"""
from __future__ import annotations
import os
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

warnings.filterwarnings('ignore')

FACT = 'output/powerbi_star/fact_transaction_combined_v2.csv'
OUT_DIR = 'docs/members_new'
os.makedirs(OUT_DIR, exist_ok=True)


def load_member_transactions() -> pd.DataFrame:
    tx = pd.read_csv(FACT)
    d1 = pd.to_datetime(tx.get('date'), errors='coerce')
    d2 = pd.to_datetime(tx.get('transaction_datetime'), errors='coerce')
    tx['date'] = d1.fillna(d2)
    tx = tx.dropna(subset=['member_id', 'date']).copy()
    tx['member_id'] = tx['member_id'].astype(int)
    tx['month'] = tx['date'].dt.to_period('M')
    return tx[['member_id', 'date', 'month', 'amount']]


def build_cohort_matrix(tx: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    first_month = tx.groupby('member_id')['month'].min().rename('cohort')
    tx = tx.join(first_month, on='member_id')
    tx['offset'] = (tx['month'] - tx['cohort']).apply(lambda p: p.n)

    active = (tx.groupby(['cohort', 'offset'])['member_id']
                .nunique()
                .unstack(fill_value=0))

    cohort_size = first_month.value_counts().sort_index()
    retention = active.div(cohort_size, axis=0).fillna(0) * 100

    return retention, cohort_size


def plot_heatmap(retention: pd.DataFrame, cohort_size: pd.Series) -> str:
    fig, ax = plt.subplots(figsize=(11, 6))
    data = retention.values
    im = ax.imshow(data, cmap='Blues', aspect='auto', vmin=0, vmax=100)

    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            if not np.isnan(data[i, j]) and data[i, j] > 0:
                txt = f'{data[i, j]:.0f}'
                color = 'white' if data[i, j] > 55 else 'black'
                ax.text(j, i, txt, ha='center', va='center', color=color, fontsize=8)

    cohort_labels = [f'{str(c)} (n={cohort_size.get(c, 0)})' for c in retention.index]
    ax.set_yticks(range(len(retention.index)))
    ax.set_yticklabels(cohort_labels, fontsize=9)
    ax.set_xticks(range(retention.shape[1]))
    ax.set_xticklabels([f'M+{c}' for c in retention.columns], fontsize=9)
    ax.set_xlabel('Mois depuis acquisition')
    ax.set_ylabel('Cohorte (mois de premiere transaction)')
    ax.set_title("Matrice de retention des membres (% actifs par cohorte)")
    cbar = plt.colorbar(im, ax=ax, fraction=0.03)
    cbar.set_label('% actifs')

    out = os.path.join(OUT_DIR, 'cohort_retention_heatmap.png')
    plt.tight_layout()
    plt.savefig(out, dpi=140)
    plt.close()
    return out


def plot_curves(retention: pd.DataFrame, cohort_size: pd.Series,
                min_cohort: int = 10, horizon: int = 12) -> str:
    big = [c for c in retention.index if cohort_size.get(c, 0) >= min_cohort]
    cols = [c for c in retention.columns if c <= horizon]
    sub = retention.loc[big, cols]

    fig, ax = plt.subplots(figsize=(10, 6))
    palette = ['#1f77b4', '#2ca02c', '#ff7f0e', '#9467bd', '#17becf']
    for i, cohort in enumerate(sub.index):
        ax.plot(sub.columns, sub.loc[cohort].values, marker='o', linewidth=1.8,
                color=palette[i % len(palette)], alpha=0.85,
                label=f'{cohort} (n={cohort_size[cohort]})')

    weights = cohort_size.loc[big].values.reshape(-1, 1)
    weighted_avg = (sub.values * weights).sum(axis=0) / weights.sum()
    ax.plot(sub.columns, weighted_avg, color='black', linewidth=3,
            linestyle='--', marker='s', markersize=7,
            label='Moyenne ponderee', zorder=5)

    ax.set_xlabel('Mois depuis acquisition')
    ax.set_ylabel('% membres actifs')
    ax.set_title(f'Retention des cohortes principales (n >= {min_cohort}, horizon M+{horizon})')
    ax.set_ylim(0, 105)
    ax.set_xticks(list(sub.columns))
    ax.grid(True, alpha=0.3)
    ax.legend(loc='upper right', fontsize=9, framealpha=0.95)

    out = os.path.join(OUT_DIR, 'cohort_retention_curves.png')
    plt.tight_layout()
    plt.savefig(out, dpi=140)
    plt.close()
    return out


def write_summary(retention: pd.DataFrame, cohort_size: pd.Series) -> str:
    summary = pd.DataFrame({
        'cohort': cohort_size.index.astype(str),
        'cohort_size': cohort_size.values,
        'M+1_retention_pct': [retention.loc[c, 1] if 1 in retention.columns else np.nan
                              for c in cohort_size.index],
        'M+3_retention_pct': [retention.loc[c, 3] if 3 in retention.columns else np.nan
                              for c in cohort_size.index],
        'M+6_retention_pct': [retention.loc[c, 6] if 6 in retention.columns else np.nan
                              for c in cohort_size.index],
    })
    out = os.path.join(OUT_DIR, 'cohort_summary.csv')
    summary.to_csv(out, index=False)
    return out


def main() -> None:
    print('Loading member transactions...')
    tx = load_member_transactions()
    print(f'    {len(tx):,} member transactions, {tx["member_id"].nunique()} unique members')

    retention, cohort_size = build_cohort_matrix(tx)
    matrix_path = os.path.join(OUT_DIR, 'cohort_retention_matrix.csv')
    retention.round(2).to_csv(matrix_path)

    heatmap_path = plot_heatmap(retention, cohort_size)
    curves_path = plot_curves(retention, cohort_size)
    summary_path = write_summary(retention, cohort_size)

    print('\nCohort sizes:')
    print(cohort_size.to_string())
    print(f'\nOutputs:\n  {matrix_path}\n  {heatmap_path}\n  {curves_path}\n  {summary_path}')

    avg_m1 = retention[1].dropna().mean() if 1 in retention.columns else float('nan')
    avg_m3 = retention[3].dropna().mean() if 3 in retention.columns else float('nan')
    print(f'\nAvg retention M+1: {avg_m1:.1f}%  |  M+3: {avg_m3:.1f}%')


if __name__ == '__main__':
    main()
