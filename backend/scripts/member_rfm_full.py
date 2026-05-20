"""Scoring RFM complet (Recency + Frequency + Monetary) sur les membres GamefyDB.

Le scoring `score_member_loyalty` existant dans gamefydb/segmenter.py ne
calcule que F + M (Frequency = duration_min, Monetary = total_tnd). On
ajoute ici la dimension R en derivant la date de derniere transaction
depuis fact_transaction_combined_v2.csv (date OU transaction_datetime).

Demarche :
    1. Reference de date = dernier jour observe dans les transactions.
    2. Recency = (reference - max(date)) en jours pour chaque membre.
    3. Quartiles inverses sur R (recent = 4, ancien = 1).
    4. Quartiles directs sur F et M (gros = 4).
    5. Segments RFM standards (Champions, Loyal, At Risk, Lost, etc.).

Sorties :
    docs/members_new/member_rfm.csv
    docs/members_new/rfm_segment_distribution.png
    docs/members_new/rfm_revenue_contribution.png
    docs/members_new/rfm_segment_summary.csv
"""
from __future__ import annotations
import os
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

warnings.filterwarnings('ignore')

FACT = 'output/powerbi_star/fact_transaction_combined_v2.csv'
DIM = 'output/powerbi_star/dim_member.csv'
OUT_DIR = 'docs/members_new'
os.makedirs(OUT_DIR, exist_ok=True)


def load_member_tx() -> pd.DataFrame:
    tx = pd.read_csv(FACT)
    d1 = pd.to_datetime(tx.get('date'), errors='coerce')
    d2 = pd.to_datetime(tx.get('transaction_datetime'), errors='coerce')
    tx['date'] = d1.fillna(d2)
    tx = tx.dropna(subset=['member_id', 'date']).copy()
    tx['member_id'] = tx['member_id'].astype(int)
    tx['amount'] = pd.to_numeric(tx['amount'], errors='coerce').fillna(0)
    return tx[['member_id', 'date', 'amount']]


def compute_rfm(tx: pd.DataFrame, dim: pd.DataFrame) -> pd.DataFrame:
    reference = tx['date'].max() + pd.Timedelta(days=1)

    agg = tx.groupby('member_id').agg(
        recency_days=('date', lambda s: (reference - s.max()).days),
        frequency_tx=('date', 'count'),
        monetary_tx=('amount', 'sum'),
    ).reset_index()

    dim = dim.copy()
    dim['member_id'] = pd.to_numeric(dim['member_id'], errors='coerce')
    dim = dim.dropna(subset=['member_id'])
    dim['member_id'] = dim['member_id'].astype(int)

    df = agg.merge(
        dim[['member_id', 'username', 'firstname', 'lastname', 'total_tnd', 'duration_min']],
        on='member_id', how='left',
    )
    df['monetary'] = df['total_tnd'].fillna(df['monetary_tx']).fillna(0)

    df['R_score'] = pd.qcut(df['recency_days'].rank(method='first'),
                            q=4, labels=[4, 3, 2, 1]).astype(int)
    df['F_score'] = pd.qcut(df['frequency_tx'].rank(method='first'),
                            q=4, labels=[1, 2, 3, 4]).astype(int)
    df['M_score'] = pd.qcut(df['monetary'].rank(method='first'),
                            q=4, labels=[1, 2, 3, 4]).astype(int)

    df['RFM_score'] = df['R_score'] * 100 + df['F_score'] * 10 + df['M_score']
    df['segment'] = df.apply(_segment, axis=1)
    return df.sort_values(['R_score', 'F_score', 'M_score'], ascending=False)


def _segment(row: pd.Series) -> str:
    r, f, m = row['R_score'], row['F_score'], row['M_score']
    fm = (f + m) / 2
    if r >= 4 and fm >= 3.5:
        return 'Champions'
    if r >= 3 and fm >= 3:
        return 'Loyal'
    if r >= 4 and fm <= 2:
        return 'New'
    if r >= 3 and f <= 2:
        return 'Potential'
    if r == 2 and fm >= 3:
        return 'At Risk'
    if r <= 1 and fm >= 3:
        return 'Cant Lose'
    if r <= 2 and fm <= 2:
        return 'Hibernating'
    return 'Lost'


SEGMENT_ORDER = ['Champions', 'Loyal', 'Potential', 'New',
                 'At Risk', 'Cant Lose', 'Hibernating', 'Lost']
SEGMENT_COLORS = {
    'Champions':   '#1f77b4',
    'Loyal':       '#2ca02c',
    'Potential':   '#17becf',
    'New':         '#9467bd',
    'At Risk':     '#ff7f0e',
    'Cant Lose':   '#d62728',
    'Hibernating': '#7f7f7f',
    'Lost':        '#8c564b',
}


def plot_distribution(rfm: pd.DataFrame) -> str:
    counts = rfm['segment'].value_counts().reindex(SEGMENT_ORDER, fill_value=0)
    colors = [SEGMENT_COLORS[s] for s in counts.index]

    fig, ax = plt.subplots(figsize=(10, 5.5))
    bars = ax.bar(counts.index, counts.values, color=colors)
    for bar, val in zip(bars, counts.values):
        if val > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, val + 0.3,
                    str(int(val)), ha='center', va='bottom', fontsize=9)
    ax.set_ylabel('Nombre de membres')
    ax.set_title('Distribution des membres par segment RFM')
    ax.grid(True, axis='y', alpha=0.3)
    plt.xticks(rotation=20)

    out = os.path.join(OUT_DIR, 'rfm_segment_distribution.png')
    plt.tight_layout()
    plt.savefig(out, dpi=140)
    plt.close()
    return out


def plot_revenue_contribution(rfm: pd.DataFrame) -> str:
    rev = (rfm.groupby('segment')['monetary'].sum()
              .reindex(SEGMENT_ORDER, fill_value=0))
    total = rev.sum()
    pct = (rev / total * 100) if total > 0 else rev * 0
    colors = [SEGMENT_COLORS[s] for s in rev.index]

    fig, ax = plt.subplots(figsize=(10, 5.5))
    bars = ax.bar(rev.index, rev.values, color=colors)
    for bar, val, p in zip(bars, rev.values, pct.values):
        if val > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, val + total * 0.005,
                    f'{p:.1f}%', ha='center', va='bottom', fontsize=9)
    ax.set_ylabel("Chiffre d'affaires cumule (TND)")
    ax.set_title("Contribution au chiffre d'affaires par segment RFM")
    ax.grid(True, axis='y', alpha=0.3)
    plt.xticks(rotation=20)

    out = os.path.join(OUT_DIR, 'rfm_revenue_contribution.png')
    plt.tight_layout()
    plt.savefig(out, dpi=140)
    plt.close()
    return out


def write_segment_summary(rfm: pd.DataFrame) -> str:
    summary = (rfm.groupby('segment')
                  .agg(members=('member_id', 'count'),
                       avg_recency_days=('recency_days', 'mean'),
                       avg_frequency_tx=('frequency_tx', 'mean'),
                       avg_monetary_tnd=('monetary', 'mean'),
                       total_revenue_tnd=('monetary', 'sum'))
                  .reindex(SEGMENT_ORDER)
                  .dropna(subset=['members']))
    summary['revenue_share_pct'] = (summary['total_revenue_tnd'] /
                                    summary['total_revenue_tnd'].sum() * 100)
    out = os.path.join(OUT_DIR, 'rfm_segment_summary.csv')
    summary.round(2).to_csv(out)
    return out


def main() -> None:
    print('Loading data...')
    tx = load_member_tx()
    dim = pd.read_csv(DIM)
    print(f'    {len(tx):,} dated member transactions  |  {dim.shape[0]} dim rows')

    rfm = compute_rfm(tx, dim)
    csv_path = os.path.join(OUT_DIR, 'member_rfm.csv')
    rfm.round(2).to_csv(csv_path, index=False)

    dist_path = plot_distribution(rfm)
    rev_path = plot_revenue_contribution(rfm)
    sum_path = write_segment_summary(rfm)

    print('\nSegment distribution:')
    print(rfm['segment'].value_counts().reindex(SEGMENT_ORDER, fill_value=0).to_string())
    top_seg = rfm.groupby('segment')['monetary'].sum().sort_values(ascending=False).head(3)
    print('\nTop revenue segments:')
    print(top_seg.round(0).to_string())

    print(f'\nOutputs:\n  {csv_path}\n  {dist_path}\n  {rev_path}\n  {sum_path}')


if __name__ == '__main__':
    main()
