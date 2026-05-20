# Member Segmentation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add K-means clustering on members (total_tnd, duration_min, orders_tnd) and export segments to CSV alongside forecast outputs.

**Architecture:** New pure module `gamefydb/segmenter.py` exposes a single function `segment_members(dim_member)`. `run.py` calls it after the star schema is written and saves the result to `output/forecasts/member_segments.csv`.

**Tech Stack:** scikit-learn (KMeans, StandardScaler), pandas

---

## File Map

| Action | Path |
|--------|------|
| Create | `gamefydb/segmenter.py` |
| Create | `tests/test_segmenter.py` |
| Modify | `requirements.txt` |
| Modify | `run.py` |

---

## Task 1: Add scikit-learn to requirements and install

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Add scikit-learn to requirements.txt**

Open `requirements.txt` and make it read:

```
pandas
xlrd
openpyxl
pytest
prophet
scikit-learn
```

- [ ] **Step 2: Install it**

```bash
C:/Users/sarah/AppData/Local/Python/bin/python -m pip install scikit-learn
```

Expected: `Successfully installed scikit-learn-...` (or `already satisfied`)

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "Add scikit-learn dependency for member segmentation"
```

---

## Task 2: Write failing tests for segmenter

**Files:**
- Create: `tests/test_segmenter.py`

- [ ] **Step 1: Create the test file**

```python
import pandas as pd
import numpy as np
import pytest
from gamefydb.segmenter import segment_members


VALID_LABELS = {'Heavy Users', 'Casual Spenders', 'Regulars', 'Light Users'}


def make_members():
    return pd.DataFrame({
        'member_id':   [1,    2,    3,    4,    5,    6,    7,    8],
        'username':    ['a',  'b',  'c',  'd',  'e',  'f',  'g',  'h'],
        'firstname':   ['A',  'B',  'C',  'D',  'E',  'F',  'G',  'H'],
        'lastname':    ['',   '',   '',   '',   '',   '',   '',   ''],
        'total_tnd':   [1000, 800,  500,  300,  200,  100,  50,   20],
        'duration_min':[500,  400,  300,  200,  100,  80,   30,   10],
        'orders_tnd':  [200,  150,  100,  80,   50,   30,   10,   2],
        'usage_tnd':   [800,  650,  400,  220,  150,  70,   40,   18],
        'usb_tnd':     [0,    0,    0,    0,    0,    0,    0,    0],
    })


def test_returns_dataframe():
    result = segment_members(make_members())
    assert isinstance(result, pd.DataFrame)


def test_adds_cluster_id_column():
    result = segment_members(make_members())
    assert 'cluster_id' in result.columns


def test_adds_segment_label_column():
    result = segment_members(make_members())
    assert 'segment_label' in result.columns


def test_cluster_id_is_integer():
    result = segment_members(make_members())
    assert np.issubdtype(result['cluster_id'].dtype, np.integer)


def test_four_unique_labels():
    result = segment_members(make_members())
    assert result['segment_label'].nunique() == 4


def test_labels_are_valid():
    result = segment_members(make_members())
    assert set(result['segment_label'].unique()).issubset(VALID_LABELS)


def test_preserves_member_columns():
    result = segment_members(make_members())
    for col in ['member_id', 'username', 'firstname', 'lastname']:
        assert col in result.columns


def test_preserves_feature_columns():
    result = segment_members(make_members())
    for col in ['total_tnd', 'duration_min', 'orders_tnd']:
        assert col in result.columns


def test_output_row_count_matches_non_zero_input():
    df = make_members()
    result = segment_members(df)
    assert len(result) == len(df)


def test_drops_all_zero_members():
    df = make_members()
    # Make member_id=1 all zeros
    df.loc[0, ['total_tnd', 'duration_min', 'orders_tnd']] = 0
    result = segment_members(df)
    assert 1 not in result['member_id'].values


def test_heavy_user_has_highest_spend():
    result = segment_members(make_members())
    heavy = result[result['segment_label'] == 'Heavy Users']['total_tnd'].mean()
    light = result[result['segment_label'] == 'Light Users']['total_tnd'].mean()
    assert heavy > light


def test_no_extra_columns():
    result = segment_members(make_members())
    expected = {'member_id', 'username', 'firstname', 'lastname',
                'total_tnd', 'duration_min', 'orders_tnd',
                'cluster_id', 'segment_label'}
    assert set(result.columns) == expected
```

- [ ] **Step 2: Run tests to confirm they all fail**

```bash
C:/Users/sarah/AppData/Local/Python/bin/python -m pytest tests/test_segmenter.py -v
```

Expected: All tests FAIL with `ImportError: cannot import name 'segment_members'`

- [ ] **Step 3: Commit the failing tests**

```bash
git add tests/test_segmenter.py
git commit -m "Add failing tests for member segmentation"
```

---

## Task 3: Implement segmenter.py

**Files:**
- Create: `gamefydb/segmenter.py`

- [ ] **Step 1: Create the module**

```python
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
```

- [ ] **Step 2: Run the tests**

```bash
C:/Users/sarah/AppData/Local/Python/bin/python -m pytest tests/test_segmenter.py -v
```

Expected: All 12 tests PASS

- [ ] **Step 3: Commit**

```bash
git add gamefydb/segmenter.py
git commit -m "Implement member segmentation (K-means k=4)"
```

---

## Task 4: Integrate into run.py

**Files:**
- Modify: `run.py`

- [ ] **Step 1: Add the import at the top of run.py**

After the existing imports, add:

```python
from gamefydb.segmenter import segment_members
```

So the imports block becomes:

```python
import argparse
import os

import pandas as pd

from gamefydb.pipeline import run_pipeline
from gamefydb.forecaster import (
    forecast_revenue,
    forecast_members,
    forecast_peak_hours,
    forecast_session_volume,
    forecast_stock_replenishment,
)
from gamefydb.segmenter import segment_members
```

- [ ] **Step 2: Add the segmentation call after the stock replenishment block**

Find this line in `run.py`:

```python
    print(f'  Forecasts written to {forecasts_dir}/')
```

Add the segmentation block before it:

```python
    print('  Member segmentation...')
    segments = segment_members(schema['dim_member'])
    segments.to_csv(
        os.path.join(forecasts_dir, 'member_segments.csv'), index=False, encoding='utf-8-sig'
    )
    for label, count in segments['segment_label'].value_counts().items():
        print(f'    {label}: {count} members')

    print(f'  Forecasts written to {forecasts_dir}/')
```

- [ ] **Step 3: Run the full pipeline to verify end-to-end**

```bash
C:/Users/sarah/AppData/Local/Python/bin/python run.py --input excel --output output
```

Expected output includes:

```
  Member segmentation...
    Heavy Users: X members
    Casual Spenders: X members
    Regulars: X members
    Light Users: X members
```

Also verify the file exists:

```bash
C:/Users/sarah/AppData/Local/Python/bin/python -c "import pandas as pd; df = pd.read_csv('output/forecasts/member_segments.csv'); print(df.columns.tolist()); print(df['segment_label'].value_counts())"
```

Expected: prints column names and segment counts with no errors.

- [ ] **Step 4: Run full test suite to confirm no regressions**

```bash
C:/Users/sarah/AppData/Local/Python/bin/python -m pytest -v
```

Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add run.py
git commit -m "Integrate member segmentation into pipeline output"
```
