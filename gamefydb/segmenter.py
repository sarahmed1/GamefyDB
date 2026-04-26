import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
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

    centers = scaler.inverse_transform(km.cluster_centers_)
    label_map = _assign_labels(centers)
    df['segment_label'] = df['cluster_id'].map(label_map)

    keep = ['member_id', 'username', 'firstname', 'lastname'] + FEATURES + ['cluster_id', 'segment_label']
    return df[[c for c in keep if c in df.columns]]
