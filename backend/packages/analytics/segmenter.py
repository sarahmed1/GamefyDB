import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler


FEATURES = ['total_tnd', 'duration_min', 'orders_tnd']
N_CLUSTERS = 4


def _assign_labels(centers: np.ndarray) -> dict:
    df = pd.DataFrame(centers, columns=FEATURES)
    remaining = list(df.index)
    label_map = {}

    heavy = df['total_tnd'].idxmax()
    label_map[heavy] = 'Heavy Users'
    remaining.remove(heavy)

    light = df.loc[remaining, 'total_tnd'].idxmin()
    label_map[light] = 'Light Users'
    remaining.remove(light)

    ratio = df.loc[remaining, 'orders_tnd'] / (df.loc[remaining, 'duration_min'] + 1)
    casual = ratio.idxmax()
    label_map[casual] = 'Casual Spenders'
    remaining.remove(casual)

    label_map[remaining[0]] = 'Regulars'
    return label_map


def segment_members(dim_member: pd.DataFrame) -> pd.DataFrame:
    df = dim_member.copy()

    for col in FEATURES:
        if col not in df.columns:
            df[col] = 0.0
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    all_zero = (df[FEATURES] == 0).all(axis=1)
    df = df[~all_zero].reset_index(drop=True)

    X = df[FEATURES].values.astype(float)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    km = KMeans(n_clusters=N_CLUSTERS, random_state=42, n_init=10)
    df['cluster_id'] = km.fit_predict(X_scaled)

    score = silhouette_score(X_scaled, df['cluster_id'])
    verdict = 'GOOD' if score > 0.5 else ('ACCEPTABLE' if score > 0.25 else 'POOR')
    print(f'    Silhouette score: {score:.2f}  -> {verdict}')

    centers = scaler.inverse_transform(km.cluster_centers_)
    label_map = _assign_labels(centers)
    df['segment_label'] = df['cluster_id'].map(label_map)

    keep = ['member_id', 'username', 'firstname', 'lastname'] + FEATURES + ['cluster_id', 'segment_label']
    return df[[c for c in keep if c in df.columns]]


_TIER_MAP = {2: 'Bronze', 3: 'Bronze', 4: 'Silver', 5: 'Silver',
             6: 'Gold',   7: 'Gold',   8: 'Platinum'}

_LOYALTY_KEEP = [
    'member_id', 'username', 'firstname', 'lastname',
    'total_tnd', 'duration_min', 'm_score', 'f_score', 'fm_score', 'loyalty_tier',
]


def score_member_loyalty(dim_member: pd.DataFrame) -> pd.DataFrame:
    _FM_FEATURES = ['total_tnd', 'duration_min']

    df = dim_member.copy()
    for col in _FM_FEATURES:
        if col not in df.columns:
            df[col] = 0.0
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    all_zero = (df[_FM_FEATURES] == 0).all(axis=1)
    df = df[~all_zero].reset_index(drop=True)

    if df.empty:
        return pd.DataFrame(columns=_LOYALTY_KEEP)

    for col, score_col in [('total_tnd', 'm_score'), ('duration_min', 'f_score')]:
        try:
            df[score_col] = (
                pd.qcut(df[col], q=4, labels=[1, 2, 3, 4], duplicates='drop')
                .astype(float)
                .fillna(1)
                .astype(int)
            )
        except ValueError:
            df[score_col] = 1

    df['fm_score'] = df['m_score'] + df['f_score']
    df['loyalty_tier'] = df['fm_score'].map(_TIER_MAP)

    n_nan = df['loyalty_tier'].isna().sum()
    if n_nan:
        print(f'    Warning: {n_nan} members have unmapped fm_score — check data distribution')

    return (
        df[[c for c in _LOYALTY_KEEP if c in df.columns]]
        .sort_values('fm_score', ascending=False)
        .reset_index(drop=True)
    )
