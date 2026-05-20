# SARIMA Comparison Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add SARIMA alongside Prophet on the same 80/20 split for each forecast, printing a side-by-side MAPE/MAE/RMSE comparison with a winner per series.

**Architecture:** Refactor `_evaluate_prophet` in `forecaster.py` to return a metrics dict instead of printing. Add `_evaluate_sarima` and `_print_comparison` helpers. Update the three Prophet-based forecast functions to call both evaluators and print the comparison. `pmdarima.auto_arima` handles SARIMA parameter selection automatically (no manual tuning).

**Tech Stack:** pmdarima (auto_arima), prophet, pandas, numpy

---

## File Map

| Action | Path |
|--------|------|
| Modify | `gamefydb/forecaster.py` |
| Create | `tests/test_forecaster_eval.py` |
| Modify | `requirements.txt` |

---

## Task 1: Add pmdarima and install

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Add pmdarima to requirements.txt**

Make `requirements.txt` read:

```
pandas
xlrd
openpyxl
pytest
prophet
scikit-learn
pmdarima
```

- [ ] **Step 2: Install**

```bash
C:/Users/sarah/AppData/Local/Python/bin/python -m pip install pmdarima
```

Expected: `Successfully installed pmdarima-...` (or `already satisfied`)

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "Add pmdarima dependency for SARIMA comparison"
```

---

## Task 2: Write failing tests for evaluation helpers

**Files:**
- Create: `tests/test_forecaster_eval.py`

- [ ] **Step 1: Create the test file**

```python
import numpy as np
import pandas as pd
import pytest

from gamefydb.forecaster import _evaluate_prophet, _evaluate_sarima, _print_comparison


def make_daily_series(n=100):
    dates = pd.date_range('2024-01-01', periods=n, freq='D')
    values = [20 + i * 0.2 + [0, 1, 2, 3, 2, 5, 4][i % 7] for i in range(n)]
    return pd.DataFrame({'ds': dates, 'y': values})


def make_weekly_series(n=40):
    dates = pd.date_range('2024-01-01', periods=n, freq='W')
    values = [50 + i * 0.5 + [0, 2, 4, 1][i % 4] for i in range(n)]
    return pd.DataFrame({'ds': dates, 'y': values})


# ── _evaluate_prophet ─────────────────────────────────────────────────────────

def test_evaluate_prophet_returns_dict():
    result = _evaluate_prophet(make_daily_series(), split=0.8)
    assert isinstance(result, dict)


def test_evaluate_prophet_has_required_keys():
    result = _evaluate_prophet(make_daily_series(), split=0.8)
    assert 'mae' in result
    assert 'mape' in result
    assert 'rmse' in result


def test_evaluate_prophet_metrics_are_positive():
    result = _evaluate_prophet(make_daily_series(), split=0.8)
    assert result['mae'] >= 0
    assert result['mape'] >= 0
    assert result['rmse'] >= 0


def test_evaluate_prophet_returns_empty_on_too_short():
    tiny = make_daily_series(n=4)
    result = _evaluate_prophet(tiny, split=0.8)
    assert result == {}


def test_evaluate_prophet_weekly_freq():
    result = _evaluate_prophet(make_weekly_series(), split=0.8, freq='W')
    assert isinstance(result, dict)
    assert 'mape' in result


# ── _evaluate_sarima ──────────────────────────────────────────────────────────

def test_evaluate_sarima_returns_dict():
    result = _evaluate_sarima(make_daily_series(), split=0.8, m=7)
    assert isinstance(result, dict)


def test_evaluate_sarima_has_required_keys():
    result = _evaluate_sarima(make_daily_series(), split=0.8, m=7)
    assert 'mae' in result
    assert 'mape' in result
    assert 'rmse' in result


def test_evaluate_sarima_metrics_are_positive():
    result = _evaluate_sarima(make_daily_series(), split=0.8, m=7)
    assert result['mae'] >= 0
    assert result['mape'] >= 0
    assert result['rmse'] >= 0


def test_evaluate_sarima_returns_none_on_too_short():
    tiny = make_daily_series(n=4)
    result = _evaluate_sarima(tiny, split=0.8, m=7)
    assert result is None


# ── _print_comparison ─────────────────────────────────────────────────────────

def test_print_comparison_runs_without_error(capsys):
    p = {'mae': 10.0, 'mape': 8.0, 'rmse': 12.0}
    s = {'mae': 15.0, 'mape': 14.0, 'rmse': 18.0}
    _print_comparison('Revenue (TND)', n=100, split=0.8, prophet_m=p, sarima_m=s)
    out = capsys.readouterr().out
    assert 'Prophet' in out
    assert 'SARIMA' in out
    assert 'Winner' in out


def test_print_comparison_prophet_wins(capsys):
    p = {'mae': 10.0, 'mape': 8.0, 'rmse': 12.0}
    s = {'mae': 20.0, 'mape': 16.0, 'rmse': 24.0}
    _print_comparison('Revenue (TND)', n=100, split=0.8, prophet_m=p, sarima_m=s)
    out = capsys.readouterr().out
    assert 'Winner: Prophet' in out


def test_print_comparison_sarima_wins(capsys):
    p = {'mae': 20.0, 'mape': 16.0, 'rmse': 24.0}
    s = {'mae': 10.0, 'mape': 8.0, 'rmse': 12.0}
    _print_comparison('Revenue (TND)', n=100, split=0.8, prophet_m=p, sarima_m=s)
    out = capsys.readouterr().out
    assert 'Winner: SARIMA' in out


def test_print_comparison_handles_none_sarima(capsys):
    p = {'mae': 10.0, 'mape': 8.0, 'rmse': 12.0}
    _print_comparison('Revenue (TND)', n=100, split=0.8, prophet_m=p, sarima_m=None)
    out = capsys.readouterr().out
    assert 'Prophet' in out
    assert 'skipped' in out
```

- [ ] **Step 2: Run to confirm all fail**

```bash
C:/Users/sarah/AppData/Local/Python/bin/python -m pytest tests/test_forecaster_eval.py -v
```

Expected: All tests FAIL with `ImportError: cannot import name '_evaluate_sarima'`

- [ ] **Step 3: Commit**

```bash
git add tests/test_forecaster_eval.py
git commit -m "Add failing tests for SARIMA evaluation helpers"
```

---

## Task 3: Refactor forecaster.py evaluation helpers

**Files:**
- Modify: `gamefydb/forecaster.py`

This task replaces `_evaluate_prophet` (currently prints, returns None) with three new helpers: a refactored `_evaluate_prophet` that returns a dict, a new `_evaluate_sarima`, and a new `_print_comparison`.

- [ ] **Step 1: Add pmdarima import at the top of forecaster.py**

The imports section currently reads:

```python
import logging
import math

import pandas as pd
from prophet import Prophet
```

Change it to:

```python
import logging
import math

import numpy as np
import pandas as pd
from pmdarima import auto_arima
from prophet import Prophet
```

- [ ] **Step 2: Replace `_evaluate_prophet` with the refactored version**

Find and replace the entire current `_evaluate_prophet` function (lines 21–54):

```python
def _evaluate_prophet(df: pd.DataFrame, split: float, label: str, freq: str = 'D') -> None:
    n = len(df)
    cutoff = int(n * split)
    if cutoff < 2 or n - cutoff < 2:
        return

    train, test = df.iloc[:cutoff].copy(), df.iloc[cutoff:].copy()

    m = Prophet(interval_width=0.8)
    m.fit(train)
    future = m.make_future_dataframe(periods=len(test), freq=freq)
    fc = m.predict(future)

    merged = test.merge(fc[['ds', 'yhat']], on='ds', how='inner')
    if merged.empty:
        return

    mae = (merged['y'] - merged['yhat']).abs().mean()
    rmse = ((merged['y'] - merged['yhat']) ** 2).mean() ** 0.5
    nonzero = merged['y'] != 0
    mape = (
        ((merged.loc[nonzero, 'y'] - merged.loc[nonzero, 'yhat']).abs()
         / merged.loc[nonzero, 'y']).mean() * 100
        if nonzero.any() else float('nan')
    )

    pct = int(split * 100)
    t0, t1 = train['ds'].min().date(), train['ds'].max().date()
    v0, v1 = test['ds'].min().date(), test['ds'].max().date()
    verdict = 'GOOD' if mape < 10 else ('ACCEPTABLE' if mape < 20 else 'POOR')
    print(f'    [{label}] {pct}/{100 - pct} split')
    print(f'      Train: {t0} → {t1}  ({len(train)} points)')
    print(f'      Test:  {v0} → {v1}  ({len(test)} points)')
    print(f'      MAE {mae:.2f} | MAPE {mape:.1f}% | RMSE {rmse:.2f}  → {verdict}')
```

Replace with:

```python
def _evaluate_prophet(df: pd.DataFrame, split: float, freq: str = 'D') -> dict:
    n = len(df)
    cutoff = int(n * split)
    if cutoff < 2 or n - cutoff < 2:
        return {}

    train, test = df.iloc[:cutoff].copy(), df.iloc[cutoff:].copy()

    m = Prophet(interval_width=0.8)
    m.fit(train)
    future = m.make_future_dataframe(periods=len(test), freq=freq)
    fc = m.predict(future)

    merged = test.merge(fc[['ds', 'yhat']], on='ds', how='inner')
    if merged.empty:
        return {}

    mae = float((merged['y'] - merged['yhat']).abs().mean())
    rmse = float(((merged['y'] - merged['yhat']) ** 2).mean() ** 0.5)
    nonzero = merged['y'] != 0
    mape = float(
        ((merged.loc[nonzero, 'y'] - merged.loc[nonzero, 'yhat']).abs()
         / merged.loc[nonzero, 'y']).mean() * 100
        if nonzero.any() else float('nan')
    )
    return {'mae': mae, 'mape': mape, 'rmse': rmse}


def _evaluate_sarima(df: pd.DataFrame, split: float, m: int = 7):
    n = len(df)
    cutoff = int(n * split)
    if cutoff < 2 or n - cutoff < 2:
        return None

    train, test = df.iloc[:cutoff], df.iloc[cutoff:]

    try:
        model = auto_arima(
            train['y'],
            seasonal=True,
            m=m,
            stepwise=True,
            suppress_warnings=True,
            error_action='ignore',
            information_criterion='aic',
        )
        predictions = model.predict(n_periods=len(test))
    except Exception:
        return None

    actual = test['y'].values
    mae = float(np.abs(actual - predictions).mean())
    rmse = float(np.sqrt(((actual - predictions) ** 2).mean()))
    nonzero = actual != 0
    mape = float(
        np.abs((actual[nonzero] - predictions[nonzero]) / actual[nonzero]).mean() * 100
        if nonzero.any() else float('nan')
    )
    return {'mae': mae, 'mape': mape, 'rmse': rmse}


def _print_comparison(label: str, n: int, split: float, prophet_m: dict, sarima_m) -> None:
    n_train = int(n * split)
    n_test = n - n_train
    pct = int(split * 100)

    p_verdict = 'GOOD' if prophet_m['mape'] < 10 else ('ACCEPTABLE' if prophet_m['mape'] < 20 else 'POOR')

    print(f'    [{label}] {pct}/{100 - pct} split — {n_train} train / {n_test} test points')
    print(f'      [Prophet] MAPE {prophet_m["mape"]:5.1f}%  MAE {prophet_m["mae"]:8.2f}  RMSE {prophet_m["rmse"]:8.2f}  → {p_verdict}')

    if sarima_m:
        s_verdict = 'GOOD' if sarima_m['mape'] < 10 else ('ACCEPTABLE' if sarima_m['mape'] < 20 else 'POOR')
        winner = 'Prophet' if prophet_m['mape'] <= sarima_m['mape'] else 'SARIMA'
        print(f'      [SARIMA]  MAPE {sarima_m["mape"]:5.1f}%  MAE {sarima_m["mae"]:8.2f}  RMSE {sarima_m["rmse"]:8.2f}  → {s_verdict}')
        print(f'      Winner: {winner}')
    else:
        print(f'      [SARIMA]  failed to converge — skipped')
```

- [ ] **Step 3: Run the tests**

```bash
C:/Users/sarah/AppData/Local/Python/bin/python -m pytest tests/test_forecaster_eval.py -v
```

Expected: All tests PASS (note: SARIMA tests may take 30–60 seconds to run)

- [ ] **Step 4: Commit**

```bash
git add gamefydb/forecaster.py
git commit -m "Refactor _evaluate_prophet, add _evaluate_sarima and _print_comparison"
```

---

## Task 4: Update the three forecast functions to use comparison

**Files:**
- Modify: `gamefydb/forecaster.py`

- [ ] **Step 1: Update `forecast_revenue`**

Find:

```python
    _evaluate_prophet(daily, split=0.8, label='Revenue (TND)')
    weekly, monthly = _prophet_forecast(daily)
```

Replace with:

```python
    p = _evaluate_prophet(daily, split=0.8)
    s = _evaluate_sarima(daily, split=0.8, m=7)
    _print_comparison('Revenue (TND)', len(daily), 0.8, p, s)
    weekly, monthly = _prophet_forecast(daily)
```

- [ ] **Step 2: Update `forecast_members`**

Find:

```python
    _evaluate_prophet(weekly_hist, split=0.8, label='Member activity', freq='W')

    m = Prophet(interval_width=0.8)
```

Replace with:

```python
    p = _evaluate_prophet(weekly_hist, split=0.8, freq='W')
    s = _evaluate_sarima(weekly_hist, split=0.8, m=4)
    _print_comparison('Member activity', len(weekly_hist), 0.8, p, s)

    m = Prophet(interval_width=0.8)
```

- [ ] **Step 3: Update `forecast_session_volume`**

Find:

```python
    _evaluate_prophet(daily, split=0.8, label='Session volume')
    weekly, monthly = _prophet_forecast(daily)
```

Replace with:

```python
    p = _evaluate_prophet(daily, split=0.8)
    s = _evaluate_sarima(daily, split=0.8, m=7)
    _print_comparison('Session volume', len(daily), 0.8, p, s)
    weekly, monthly = _prophet_forecast(daily)
```

- [ ] **Step 4: Run full test suite**

```bash
C:/Users/sarah/AppData/Local/Python/bin/python -m pytest -v
```

Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add gamefydb/forecaster.py
git commit -m "Add SARIMA vs Prophet comparison to all forecast functions"
```
