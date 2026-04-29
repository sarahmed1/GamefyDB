# Anomaly Detection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a day-of-week Z-score anomaly detector that flags unusual days in revenue, session volume, and member activity, writes results to `output/forecasts/anomalies.csv`, and prints a summary during the pipeline run.

**Architecture:** A new `gamefydb/anomaly_detector.py` module exposes a single public function `detect_anomalies(transactions_df)`. It reuses `_to_daily` from `forecaster.py` to build three daily series, applies per-weekday Z-score flagging to each independently, and returns a combined DataFrame. `run.py` calls it after the existing forecasting block and writes the CSV inline (no separate writer function — matches the existing pattern).

**Tech Stack:** pandas, numpy (already installed); no new dependencies.

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `gamefydb/anomaly_detector.py` | `_flag_series()` + `detect_anomalies()` |
| Create | `tests/test_anomaly_detector.py` | 7 unit tests |
| Modify | `run.py` | Call detect_anomalies, print summary, write CSV |
| Modify | `docs/ml_choices_explained.md` | Section 11 — anomaly detection choices |

---

## Task 1: Write all failing tests

**Files:**
- Create: `tests/test_anomaly_detector.py`

- [ ] **Step 1: Create the test file**

```python
import pandas as pd
import pytest

from gamefydb.anomaly_detector import detect_anomalies


PYTHON = 'C:/Users/sarah/AppData/Local/Python/bin/python'

# ── helpers ──────────────────────────────────────────────────────────────────

def _make_income_tx(dates, amounts):
    """One Income transaction per date at the given amount."""
    return pd.DataFrame({
        'transaction_datetime': pd.to_datetime(dates),
        'amount_tnd': [float(a) for a in amounts],
        'income_expense': 'Income',
        'transaction_type': 'Cash',
    })


def _mondays(n):
    """Return n consecutive Monday dates starting 2025-01-06."""
    return pd.date_range('2025-01-06', periods=n, freq='7D')


# ── tests ────────────────────────────────────────────────────────────────────

def test_normal_data_returns_empty():
    # 5 Mondays all identical — std == 0, no anomaly possible
    dates = _mondays(5)
    tx = _make_income_tx(dates, [100] * 5)
    result = detect_anomalies(tx)
    assert result.empty


def test_spike_detected_as_severe():
    # 12 Mondays: 11 at 100, 1 at 1200 → z ≈ 3.17 → severe, high
    dates = _mondays(12)
    amounts = [100] * 11 + [1200]
    tx = _make_income_tx(dates, amounts)
    result = detect_anomalies(tx)
    assert len(result) == 1
    row = result.iloc[0]
    assert row['series'] == 'revenue'
    assert row['severity'] == 'severe'
    assert row['direction'] == 'high'
    assert row['z_score'] > 3.0


def test_dip_detected_as_mild():
    # 6 Mondays: 5 at 100, 1 at 10 → z ≈ -2.04 → mild, low
    dates = _mondays(6)
    amounts = [100] * 5 + [10]
    tx = _make_income_tx(dates, amounts)
    result = detect_anomalies(tx)
    assert len(result) == 1
    row = result.iloc[0]
    assert row['severity'] == 'mild'
    assert row['direction'] == 'low'
    assert -3.0 < row['z_score'] < -2.0


def test_revenue_anomaly_not_in_session_volume():
    # 12 Mondays, revenue spike on last day
    # Session volume = 1 transaction/day (constant) → std == 0 → no session anomaly
    dates = _mondays(12)
    amounts = [100] * 11 + [1200]
    tx = _make_income_tx(dates, amounts)
    result = detect_anomalies(tx)
    assert result[result['series'] == 'session_volume'].empty


def test_small_group_skipped():
    # Only 3 Mondays (< 4 required) — no flags even with extreme values
    dates = _mondays(3)
    tx = _make_income_tx(dates, [1, 100, 1000])
    result = detect_anomalies(tx)
    assert result.empty


def test_output_columns_present():
    dates = _mondays(12)
    amounts = [100] * 11 + [1200]
    tx = _make_income_tx(dates, amounts)
    result = detect_anomalies(tx)
    expected_cols = {
        'date', 'series', 'weekday', 'actual',
        'weekday_mean', 'weekday_std', 'z_score',
        'direction', 'severity',
    }
    assert expected_cols.issubset(set(result.columns))


def test_sorted_by_abs_z_score_descending():
    # 12 Mondays (spike z≈3.17) + 6 Tuesdays (spike z≈2.04) — Monday row must be first
    mon_dates = _mondays(12)
    mon_amounts = [100] * 11 + [1200]

    tue_dates = pd.date_range('2025-01-07', periods=6, freq='7D')  # Tuesdays
    tue_amounts = [100] * 5 + [300]

    tx = pd.concat([
        _make_income_tx(mon_dates, mon_amounts),
        _make_income_tx(tue_dates, tue_amounts),
    ], ignore_index=True)

    result = detect_anomalies(tx)
    assert len(result) >= 2
    abs_z = result['z_score'].abs().tolist()
    assert abs_z == sorted(abs_z, reverse=True)
```

- [ ] **Step 2: Run tests to confirm they all fail with ImportError**

```
C:/Users/sarah/AppData/Local/Python/bin/python -m pytest tests/test_anomaly_detector.py -v
```

Expected: 7 errors — `ModuleNotFoundError: No module named 'gamefydb.anomaly_detector'`

- [ ] **Step 3: Commit the failing tests**

```bash
git add tests/test_anomaly_detector.py
git commit -m "test: add failing tests for anomaly detector"
```

---

## Task 2: Implement `gamefydb/anomaly_detector.py`

**Files:**
- Create: `gamefydb/anomaly_detector.py`

- [ ] **Step 1: Create the module**

```python
import numpy as np
import pandas as pd

from gamefydb.forecaster import _to_daily


_COLS = ['date', 'series', 'weekday', 'actual',
         'weekday_mean', 'weekday_std', 'z_score', 'direction', 'severity']


def _flag_series(daily_df: pd.DataFrame, label: str, threshold: float = 2.0) -> pd.DataFrame:
    df = daily_df.copy()
    df['weekday'] = df['ds'].dt.day_name()

    stats = (
        df.groupby('weekday')['y']
        .agg(['mean', 'std', 'count'])
        .reset_index()
        .rename(columns={'mean': 'weekday_mean', 'std': 'weekday_std', 'count': '_n'})
    )

    df = df.merge(stats, on='weekday')
    df = df[(df['_n'] >= 4) & (df['weekday_std'] > 0)].copy()

    if df.empty:
        return pd.DataFrame(columns=_COLS)

    df['z_score'] = ((df['y'] - df['weekday_mean']) / df['weekday_std']).round(2)
    df = df[df['z_score'].abs() >= threshold].copy()

    if df.empty:
        return pd.DataFrame(columns=_COLS)

    df['series'] = label
    df['direction'] = df['z_score'].apply(lambda z: 'high' if z > 0 else 'low')
    df['severity'] = df['z_score'].abs().apply(lambda z: 'severe' if z > 3.0 else 'mild')
    df['date'] = df['ds'].dt.date
    df['actual'] = df['y'].round(2)
    df['weekday_mean'] = df['weekday_mean'].round(2)
    df['weekday_std'] = df['weekday_std'].round(2)

    return df[_COLS]


def detect_anomalies(transactions_df: pd.DataFrame, threshold: float = 2.0) -> pd.DataFrame:
    income = transactions_df[transactions_df['income_expense'] == 'Income'].copy()
    income['_v'] = income['amount_tnd']
    revenue_daily = _to_daily(income, 'transaction_datetime', '_v')

    sessions = transactions_df.copy()
    sessions['_v'] = 1
    sessions_daily = _to_daily(sessions, 'transaction_datetime', '_v')

    members = transactions_df[
        transactions_df['transaction_type'] == 'Member Transactions'
    ].copy()
    members['_v'] = 1
    members_daily = _to_daily(members, 'transaction_datetime', '_v')

    frames = [
        _flag_series(revenue_daily, 'revenue', threshold),
        _flag_series(sessions_daily, 'session_volume', threshold),
        _flag_series(members_daily, 'member_activity', threshold),
    ]
    frames = [f for f in frames if not f.empty]

    if not frames:
        return pd.DataFrame(columns=_COLS)

    result = pd.concat(frames, ignore_index=True)
    return result.iloc[result['z_score'].abs().argsort()[::-1]].reset_index(drop=True)
```

- [ ] **Step 2: Run the tests**

```
C:/Users/sarah/AppData/Local/Python/bin/python -m pytest tests/test_anomaly_detector.py -v
```

Expected: all 7 tests PASS.

- [ ] **Step 3: Run the full test suite to check no regressions**

```
C:/Users/sarah/AppData/Local/Python/bin/python -m pytest -v
```

Expected: all tests PASS (forecaster and segmenter tests still green).

- [ ] **Step 4: Commit**

```bash
git add gamefydb/anomaly_detector.py
git commit -m "feat: add day-of-week Z-score anomaly detector"
```

---

## Task 3: Wire anomaly detection into `run.py`

**Files:**
- Modify: `run.py`

- [ ] **Step 1: Add the import at the top of run.py (after the segmenter import)**

In `run.py`, find this line:
```python
from gamefydb.segmenter import segment_members
```

Add below it:
```python
from gamefydb.anomaly_detector import detect_anomalies
```

- [ ] **Step 2: Add the anomaly detection block after the segmentation block**

In `run.py`, find this block (near the end of `main()`):
```python
    print(f'  Forecasts written to {forecasts_dir}/')
    print('Done.')
```

Replace it with:
```python
    print('  Anomaly detection...')
    anomalies = detect_anomalies(tx)
    _print_anomaly_summary(anomalies)
    anomalies.to_csv(os.path.join(forecasts_dir, 'anomalies.csv'), index=False)

    print(f'  Forecasts written to {forecasts_dir}/')
    print('Done.')
```

- [ ] **Step 3: Add the summary helper function to `run.py`, before `main()`**

Find the line:
```python
def main():
```

Add above it:
```python
def _print_anomaly_summary(anomalies: pd.DataFrame) -> None:
    labels = ['revenue', 'session_volume', 'member_activity']
    for label in labels:
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


```

- [ ] **Step 4: Run the pipeline end-to-end to verify output**

```
C:/Users/sarah/AppData/Local/Python/bin/python run.py --input excel --output output
```

Expected: pipeline completes, `output/forecasts/anomalies.csv` is created, anomaly summary printed to console.

- [ ] **Step 5: Commit**

```bash
git add run.py
git commit -m "feat: wire anomaly detection into pipeline, write anomalies.csv"
```

---

## Task 4: Add section 11 to `ml_choices_explained.md`

**Files:**
- Modify: `docs/ml_choices_explained.md`

- [ ] **Step 1: Append section 11 and update the summary table**

Open `docs/ml_choices_explained.md`. At the end of the file, replace the summary table's closing line and everything after it with the following (the new section goes before the table; then update the table itself):

Append after the last `---` divider (before the Summary Table section):

```markdown
## 11. Anomaly Detection — Z-Score (Day-of-Week)

**What it is:**
An anomaly is a day where the observed value is statistically far from what is normal for that day of the week. We use Z-score to measure this distance:

    z = (actual − weekday_mean) / weekday_std

Where `weekday_mean` and `weekday_std` are the mean and standard deviation computed from all historical days of the same weekday (e.g. all Mondays, all Tuesdays, etc.).

**Why day-of-week grouping:**
A gaming center has strong weekly seasonality — weekends are busier than weekdays. Comparing a Sunday against the overall daily average would flag almost every Sunday as an anomaly, which is meaningless. By comparing each day only against its own weekday peers, we detect days that are unusual relative to what is expected for that specific day of the week.

**Why all data is used (no train/test split):**
Anomaly detection does not predict the future — it asks which past days were statistically unusual. Using all available data gives the most accurate baseline (mean and std per weekday). Unlike forecasting models, nothing is held back for evaluation.

**Threshold — 2σ:**
A day is flagged if its Z-score exceeds 2.0 in either direction. Statistically, roughly 5% of days in a normal distribution fall outside ±2σ. In practice, this means only genuinely unusual days are flagged. A minimum of 4 data points per weekday group is required to compute a meaningful standard deviation.

**Severity:**
- **Mild (2–3σ):** unusual but plausible — e.g. a slow Monday or a moderately busy Sunday
- **Severe (>3σ):** very unlikely to occur by chance (~0.3% probability) — likely caused by an external event such as a power cut, a gaming tournament, a public holiday, or a cashier error

**Three series monitored independently:**
- Revenue (TND) — daily sum of income transactions
- Session volume — daily count of all transactions
- Member activity — daily count of member transactions

Each series uses its own mean and std. An anomaly in revenue has no effect on the session volume Z-score.

**Alternatives considered:**
- **Rolling Z-score** — uses a sliding window instead of the full historical mean. More adaptive to long-term trends but requires more data and adds complexity. With 7 months of data, the global weekday mean is stable enough.
- **Isolation Forest** — a machine learning method that learns what "normal" looks like from a multi-dimensional feature set. More powerful but requires sklearn, harder to explain to a non-technical audience, and overkill for three independent univariate series.
- **Prophet residuals** — flag days where actual revenue deviates from Prophet's forecast. Academically interesting but ties anomaly detection to the forecast model; if Prophet overfits, it masks anomalies rather than finding them.

**Conclusion:** Day-of-week Z-score is the right balance of simplicity, statistical rigor, and explainability for a thesis project of this scope.

---
```

Then in the **Summary Table**, add two rows before the closing `|` line:

```markdown
| Anomaly detection algorithm | Z-score (day-of-week) | Statistical standard, no extra library, easy to explain |
| Anomaly threshold | 2σ (mild) / 3σ (severe) | Flags ~5% of days; 3σ threshold reserves "severe" for true outliers |
```

- [ ] **Step 2: Commit**

```bash
git add docs/ml_choices_explained.md
git commit -m "docs: add anomaly detection section to ml_choices_explained"
```

---

## Done

After all four tasks, verify:

```
C:/Users/sarah/AppData/Local/Python/bin/python -m pytest -v
C:/Users/sarah/AppData/Local/Python/bin/python run.py --input excel --output output
```

Both should pass cleanly and `output/forecasts/anomalies.csv` should exist with columns: `date, series, weekday, actual, weekday_mean, weekday_std, z_score, direction, severity`.
