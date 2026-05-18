# Member Loyalty Scoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `score_member_loyalty()` to `gamefydb/segmenter.py` that scores each member on Frequency (duration_min) and Monetary (total_tnd) and assigns a Bronze/Silver/Gold/Platinum loyalty tier, wired into `run.py` and saved to `output/forecasts/member_loyalty.csv`.

**Architecture:** Quartile-rank each member 1–4 on `total_tnd` (M score) and `duration_min` (F score), sum for an FM composite score (2–8), map to four tiers. Function lives in `segmenter.py` alongside `segment_members()` since it operates on the same `dim_member` input.

**Tech Stack:** pandas (`pd.qcut`), Python 3. No new dependencies.

---

## File Map

| File | Change |
|---|---|
| `gamefydb/segmenter.py` | Add `score_member_loyalty()` function |
| `run.py` | Import + call `score_member_loyalty`, save CSV, print tier counts |
| `tests/test_loyalty.py` | New test file — 9 tests |

---

### Task 1: Write failing tests

**Files:**
- Create: `tests/test_loyalty.py`

- [ ] **Step 1: Create the test file**

```python
import pandas as pd
import pytest
from gamefydb.segmenter import score_member_loyalty


def _members(total_tnd, duration_min):
    n = len(total_tnd)
    return pd.DataFrame({
        'member_id': range(1, n + 1),
        'username':  [f'u{i}' for i in range(1, n + 1)],
        'firstname': ['A'] * n,
        'lastname':  ['B'] * n,
        'total_tnd':    total_tnd,
        'duration_min': duration_min,
    })


# 8 members with evenly spread values so quartile splits are clean:
# Q1=[10,20] Q2=[30,40] Q3=[50,60] Q4=[70,80]
_SPREAD = [10, 20, 30, 40, 50, 60, 70, 80]


def test_output_columns():
    result = score_member_loyalty(_members(_SPREAD, _SPREAD))
    assert list(result.columns) == [
        'member_id', 'username', 'firstname', 'lastname',
        'total_tnd', 'duration_min', 'm_score', 'f_score', 'fm_score', 'loyalty_tier',
    ]


def test_sorted_descending_by_fm_score():
    result = score_member_loyalty(_members(_SPREAD, _SPREAD))
    assert result['fm_score'].is_monotonic_decreasing


def test_fm_score_equals_sum_of_m_and_f():
    result = score_member_loyalty(_members(_SPREAD, _SPREAD))
    assert (result['fm_score'] == result['m_score'] + result['f_score']).all()


def test_platinum_member():
    # member_id=8 has max total_tnd=80 AND max duration_min=80 → m=4, f=4, fm=8
    result = score_member_loyalty(_members(_SPREAD, _SPREAD))
    top = result[result['member_id'] == 8].iloc[0]
    assert top['loyalty_tier'] == 'Platinum'
    assert top['fm_score'] == 8


def test_bronze_member():
    # member_id=1 has min total_tnd=10 AND min duration_min=10 → m=1, f=1, fm=2
    result = score_member_loyalty(_members(_SPREAD, _SPREAD))
    bottom = result[result['member_id'] == 1].iloc[0]
    assert bottom['loyalty_tier'] == 'Bronze'
    assert bottom['fm_score'] == 2


def test_tier_mapping():
    tiers = score_member_loyalty(_members(_SPREAD, _SPREAD)).set_index('fm_score')['loyalty_tier']
    assert tiers[8] == 'Platinum'
    for score in [6, 7]:
        if score in tiers.index:
            assert tiers[score] == 'Gold'
    for score in [4, 5]:
        if score in tiers.index:
            assert tiers[score] == 'Silver'
    for score in [2, 3]:
        if score in tiers.index:
            assert tiers[score] == 'Bronze'


def test_all_zero_members_excluded():
    df = _members([0, 0, 50, 80], [0, 0, 300, 600])
    result = score_member_loyalty(df)
    assert set(result['member_id']) == {3, 4}


def test_empty_input_returns_correct_columns():
    empty = _members([], [])
    result = score_member_loyalty(empty)
    assert result.empty
    assert 'loyalty_tier' in result.columns
    assert 'fm_score' in result.columns


def test_all_same_values_no_error():
    # All identical values — pd.qcut would normally raise; must not crash
    df = _members([100, 100, 100, 100, 100], [200, 200, 200, 200, 200])
    result = score_member_loyalty(df)
    assert len(result) == 5
    assert result['loyalty_tier'].notna().all()
```

- [ ] **Step 2: Run tests to confirm they all fail**

```
C:/Users/sarah/AppData/Local/Python/bin/python -m pytest tests/test_loyalty.py -v
```

Expected: 9 failures — `ImportError: cannot import name 'score_member_loyalty'`

---

### Task 2: Implement `score_member_loyalty()`

**Files:**
- Modify: `gamefydb/segmenter.py` (append after `segment_members`)

- [ ] **Step 1: Append the function to `gamefydb/segmenter.py`**

Add this after the closing line of `segment_members()`:

```python


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

    return (
        df[[c for c in _LOYALTY_KEEP if c in df.columns]]
        .sort_values('fm_score', ascending=False)
        .reset_index(drop=True)
    )
```

- [ ] **Step 2: Run the tests**

```
C:/Users/sarah/AppData/Local/Python/bin/python -m pytest tests/test_loyalty.py -v
```

Expected: all 9 PASS

- [ ] **Step 3: Run the full test suite to check for regressions**

```
C:/Users/sarah/AppData/Local/Python/bin/python -m pytest --ignore=tests/test_forecaster_eval.py -v
```

Expected: all tests PASS (skip `test_forecaster_eval.py` — it takes 20–30 s and is unrelated)

- [ ] **Step 4: Commit**

```
git add gamefydb/segmenter.py tests/test_loyalty.py
git commit -m "feat: add FM-based member loyalty scoring"
```

---

### Task 3: Wire into `run.py`

**Files:**
- Modify: `run.py`

- [ ] **Step 1: Update the import on line 16**

Old:
```python
from gamefydb.segmenter import segment_members
```

New:
```python
from gamefydb.segmenter import segment_members, score_member_loyalty
```

- [ ] **Step 2: Add the loyalty scoring block after the member segmentation block**

The existing segmentation block ends at line 105:
```python
    for label, count in segments['segment_label'].value_counts().items():
        print(f'    {label}: {count} members')
```

Add immediately after it:
```python
    print('  Member loyalty scoring...')
    loyalty = score_member_loyalty(schema['dim_member'])
    loyalty.to_csv(
        os.path.join(forecasts_dir, 'member_loyalty.csv'), index=False, encoding='utf-8-sig'
    )
    for tier, count in loyalty['loyalty_tier'].value_counts().items():
        print(f'    {tier}: {count} members')
```

- [ ] **Step 3: Commit**

```
git add run.py
git commit -m "feat: wire member loyalty scoring into pipeline, output member_loyalty.csv"
```

---

### Task 4: Smoke test the full pipeline

- [ ] **Step 1: Run the pipeline end-to-end**

```
C:/Users/sarah/AppData/Local/Python/bin/python run.py --input excel --output output
```

Expected output includes:
```
  Member loyalty scoring...
    Platinum: X members
    Gold: X members
    Silver: X members
    Bronze: X members
```

- [ ] **Step 2: Verify the output file exists and looks right**

```
C:/Users/sarah/AppData/Local/Python/bin/python -c "
import pandas as pd
df = pd.read_csv('output/forecasts/member_loyalty.csv')
print(df.shape)
print(df['loyalty_tier'].value_counts())
print(df.head(3).to_string())
"
```

Expected: non-empty DataFrame, all 4 tiers present, sorted by fm_score descending.

- [ ] **Step 3: Final commit if any minor fixes were needed**

```
git add -p
git commit -m "fix: adjust loyalty scoring after smoke test"
```

Only needed if Step 1 or 2 surfaced a problem.
