# Forecasting Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Prophet-based forecasting module that reads pipeline CSV output and predicts per-item consumption and total revenue, writing CSV + Excel output and printing a terminal summary.

**Architecture:** `gamefydb/forecaster.py` holds five pure functions (`load_data`, `prepare_revenue_series`, `prepare_consumption_series`, `fit_prophet`, `forecast_all`). `forecast.py` is the argparse CLI entry point. Everything reads from existing pipeline output; no ETL code is touched.

**Tech Stack:** Python 3, prophet, pandas, openpyxl (already in project), pytest, argparse

> **Context7 note:** Use `mcp__plugin_context7_context7__resolve-library-id` + `mcp__plugin_context7_context7__query-docs` for `/facebook/prophet` before implementing any Prophet code.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `requirements.txt` | Modify | Add `prophet` |
| `gamefydb/forecaster.py` | Create | All forecasting logic |
| `forecast.py` | Create | CLI entry point |
| `tests/test_forecaster.py` | Create | Unit + integration tests |

---

## Task 1: Add dependency

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Add `prophet` to requirements.txt**

```
pandas
xlrd
openpyxl
pytest
prophet
```

- [ ] **Step 2: Commit**

```bash
git add requirements.txt
git commit -m "chore: add prophet to requirements"
```

---

## Task 2: `load_data`

**Files:**
- Create: `gamefydb/forecaster.py`
- Create: `tests/test_forecaster.py`

- [ ] **Step 1: Create `tests/test_forecaster.py` with the failing tests**

```python
import os
import pytest
import pandas as pd
from pathlib import Path
from gamefydb.forecaster import load_data


def _write_empty_csvs(base_dir: Path) -> None:
    """Write the three required pipeline CSVs as empty but schema-valid files."""
    (base_dir / 'dims').mkdir(parents=True, exist_ok=True)
    (base_dir / 'facts').mkdir(parents=True, exist_ok=True)
    pd.DataFrame(columns=['item_id', 'item_name', 'category']).to_csv(
        base_dir / 'dims' / 'dim_item.csv', index=False)
    pd.DataFrame(columns=[
        'movement_datetime', 'in_out', 'item_id',
        'quantity', 'unit_price_tnd', 'total_amount_tnd',
    ]).to_csv(base_dir / 'facts' / 'fact_stock_movements.csv', index=False)
    pd.DataFrame(columns=[
        'transaction_datetime', 'income_expense', 'amount_tnd',
    ]).to_csv(base_dir / 'facts' / 'fact_cash_transactions.csv', index=False)


def test_load_data_missing_files_raises(tmp_path):
    with pytest.raises(FileNotFoundError, match="Run the pipeline first"):
        load_data(str(tmp_path))


def test_load_data_returns_dict_with_correct_keys(tmp_path):
    _write_empty_csvs(tmp_path)
    data = load_data(str(tmp_path))
    assert set(data.keys()) == {'stock', 'cash', 'items'}
    assert isinstance(data['stock'], pd.DataFrame)
    assert isinstance(data['cash'], pd.DataFrame)
    assert isinstance(data['items'], pd.DataFrame)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
C:/Users/sarah/AppData/Local/Python/bin/python -m pytest tests/test_forecaster.py -v
```

Expected: `ImportError` or `ModuleNotFoundError` — `gamefydb.forecaster` does not exist yet.

- [ ] **Step 3: Create `gamefydb/forecaster.py` with `load_data`**

```python
import logging
import os

import pandas as pd

try:
    from prophet import Prophet
except ImportError as exc:
    raise ImportError("Install prophet: pip install prophet") from exc


def load_data(output_dir: str) -> dict:
    """Read pipeline CSV output. Raises FileNotFoundError if any file is missing."""
    paths = {
        'stock': os.path.join(output_dir, 'facts', 'fact_stock_movements.csv'),
        'cash':  os.path.join(output_dir, 'facts', 'fact_cash_transactions.csv'),
        'items': os.path.join(output_dir, 'dims',  'dim_item.csv'),
    }
    for key, path in paths.items():
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"Missing {path}. Run the pipeline first: python run.py"
            )
    return {key: pd.read_csv(path) for key, path in paths.items()}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
C:/Users/sarah/AppData/Local/Python/bin/python -m pytest tests/test_forecaster.py -v
```

Expected: `PASSED` for both `test_load_data_*` tests.

- [ ] **Step 5: Commit**

```bash
git add gamefydb/forecaster.py tests/test_forecaster.py
git commit -m "feat: forecaster - load_data with FileNotFoundError guard"
```

---

## Task 3: `prepare_revenue_series`

**Files:**
- Modify: `gamefydb/forecaster.py`
- Modify: `tests/test_forecaster.py`

- [ ] **Step 1: Add failing tests to `tests/test_forecaster.py`**

Add these imports at the top:
```python
from gamefydb.forecaster import load_data, prepare_revenue_series
```

Add these tests:
```python
def test_prepare_revenue_series_excludes_expense_rows():
    cash = pd.DataFrame({
        'transaction_datetime': [
            '2025-09-01 10:00:00',
            '2025-09-01 11:00:00',  # Expense — must be excluded
            '2025-09-02 10:00:00',
        ],
        'income_expense': ['Income', 'Expense', 'Income'],
        'amount_tnd':     [100.0,    50.0,       200.0],
    })
    result = prepare_revenue_series(cash)
    assert result['2025-09-01'] == pytest.approx(100.0)  # Expense not counted
    assert result['2025-09-02'] == pytest.approx(200.0)


def test_prepare_revenue_series_fills_missing_dates_with_zero():
    cash = pd.DataFrame({
        'transaction_datetime': ['2025-09-01 10:00:00', '2025-09-03 10:00:00'],
        'income_expense': ['Income', 'Income'],
        'amount_tnd':     [100.0,    200.0],
    })
    result = prepare_revenue_series(cash)
    assert result['2025-09-02'] == pytest.approx(0.0)  # gap filled


def test_prepare_revenue_series_all_expenses_raises():
    cash = pd.DataFrame({
        'transaction_datetime': ['2025-09-01 10:00:00'],
        'income_expense': ['Expense'],
        'amount_tnd':     [50.0],
    })
    with pytest.raises(ValueError, match="No income data found"):
        prepare_revenue_series(cash)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
C:/Users/sarah/AppData/Local/Python/bin/python -m pytest tests/test_forecaster.py::test_prepare_revenue_series_excludes_expense_rows tests/test_forecaster.py::test_prepare_revenue_series_fills_missing_dates_with_zero tests/test_forecaster.py::test_prepare_revenue_series_all_expenses_raises -v
```

Expected: `AttributeError` — `prepare_revenue_series` not defined yet.

- [ ] **Step 3: Add `prepare_revenue_series` to `gamefydb/forecaster.py`**

```python
def prepare_revenue_series(cash: pd.DataFrame) -> pd.Series:
    """Aggregate daily Income totals from fact_cash_transactions.

    Returns a DatetimeIndex Series with zeros for days with no income.
    Raises ValueError if no Income rows exist.
    """
    income = cash[cash['income_expense'] == 'Income'].copy()
    income['date'] = pd.to_datetime(income['transaction_datetime']).dt.normalize()
    daily = income.groupby('date')['amount_tnd'].sum()
    if daily.empty or daily.sum() == 0:
        raise ValueError("No income data found in fact_cash_transactions")
    full_index = pd.date_range(daily.index.min(), daily.index.max(), freq='D')
    return daily.reindex(full_index, fill_value=0.0)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
C:/Users/sarah/AppData/Local/Python/bin/python -m pytest tests/test_forecaster.py -v
```

Expected: all tests `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add gamefydb/forecaster.py tests/test_forecaster.py
git commit -m "feat: forecaster - prepare_revenue_series"
```

---

## Task 4: `prepare_consumption_series`

**Files:**
- Modify: `gamefydb/forecaster.py`
- Modify: `tests/test_forecaster.py`

- [ ] **Step 1: Add failing tests to `tests/test_forecaster.py`**

Update the import line:
```python
from gamefydb.forecaster import load_data, prepare_revenue_series, prepare_consumption_series
```

Add these tests:

```python
def _stock_with_n_nonzero_days(item_id: int, item_name: str, n: int) -> tuple:
    """Helper: n days of Out movements for one item + matching dim_item row."""
    dates = pd.date_range('2025-09-01', periods=n, freq='D').astype(str).tolist()
    stock = pd.DataFrame({
        'movement_datetime': dates,
        'in_out': ['Out'] * n,
        'item_id': [item_id] * n,
        'quantity': [5] * n,
        'unit_price_tnd': [2.5] * n,
        'total_amount_tnd': [12.5] * n,
    })
    items = pd.DataFrame({'item_id': [item_id], 'item_name': [item_name]})
    return stock, items


def test_prepare_consumption_series_counts_out_only():
    # 14 days of Out movements + 1 In on day 1 — only Out should be counted
    dates = pd.date_range('2025-09-01', periods=14, freq='D').astype(str).tolist()
    stock = pd.DataFrame({
        'movement_datetime': dates + ['2025-09-01'],
        'in_out': ['Out'] * 14 + ['In'],
        'item_id': [1] * 15,
        'quantity': [3] * 14 + [10],
        'unit_price_tnd': [2.5] * 15,
        'total_amount_tnd': [2.5] * 15,
    })
    items = pd.DataFrame({'item_id': [1], 'item_name': ['Soda']})
    series_dict, _ = prepare_consumption_series(stock, items)
    assert series_dict['Soda'].loc['2025-09-01'] == pytest.approx(3.0)  # Out only, not 10


def test_prepare_consumption_series_fills_zeros_for_missing_dates():
    stock, items = _stock_with_n_nonzero_days(1, 'Soda', 14)
    # Add one more sale on day 20 (gap of 5 days)
    extra = pd.DataFrame({
        'movement_datetime': ['2025-09-20'],
        'in_out': ['Out'],
        'item_id': [1],
        'quantity': [5],
        'unit_price_tnd': [2.5],
        'total_amount_tnd': [12.5],
    })
    stock = pd.concat([stock, extra], ignore_index=True)
    series_dict, _ = prepare_consumption_series(stock, items)
    assert series_dict['Soda'].loc['2025-09-17'] == pytest.approx(0.0)


def test_prepare_consumption_series_skips_sparse_items():
    # Chips only sold on 3 days — below the 14-day threshold
    stock = pd.DataFrame({
        'movement_datetime': ['2025-09-01', '2025-09-02', '2025-09-03'],
        'in_out': ['Out', 'Out', 'Out'],
        'item_id': [1, 1, 1],
        'quantity': [1, 1, 1],
        'unit_price_tnd': [2.5, 2.5, 2.5],
        'total_amount_tnd': [2.5, 2.5, 2.5],
    })
    items = pd.DataFrame({'item_id': [1], 'item_name': ['Chips']})
    series_dict, skipped = prepare_consumption_series(stock, items)
    assert 'Chips' not in series_dict
    assert any(name == 'Chips' for name, _ in skipped)


def test_prepare_consumption_series_keeps_items_with_enough_data():
    stock, items = _stock_with_n_nonzero_days(1, 'Soda', 14)
    series_dict, skipped = prepare_consumption_series(stock, items)
    assert 'Soda' in series_dict
    assert len(skipped) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
C:/Users/sarah/AppData/Local/Python/bin/python -m pytest tests/test_forecaster.py::test_prepare_consumption_series_counts_out_only tests/test_forecaster.py::test_prepare_consumption_series_fills_zeros_for_missing_dates tests/test_forecaster.py::test_prepare_consumption_series_skips_sparse_items tests/test_forecaster.py::test_prepare_consumption_series_keeps_items_with_enough_data -v
```

Expected: `AttributeError` — `prepare_consumption_series` not defined yet.

- [ ] **Step 3: Add `prepare_consumption_series` to `gamefydb/forecaster.py`**

```python
def prepare_consumption_series(
    stock: pd.DataFrame, items: pd.DataFrame, freq: str = 'D',
) -> tuple:
    """Aggregate Out-quantity per item from fact_stock_movements.

    Returns:
        ({item_name: qty_Series}, [(skipped_name, nonzero_count)])
        Series have a full DatetimeIndex (resampled to `freq`) with zeros
        for periods with no sales. Items with fewer than 14 non-zero
        periods (after resampling) are excluded and listed in skipped.
    """
    out_rows = stock[stock['in_out'] == 'Out'].copy()
    out_rows = out_rows.merge(items[['item_id', 'item_name']], on='item_id', how='left')
    out_rows['date'] = pd.to_datetime(out_rows['movement_datetime']).dt.normalize()

    daily = (
        out_rows.groupby(['date', 'item_name'])['quantity']
        .sum()
        .unstack(fill_value=0)
    )
    full_index = pd.date_range(daily.index.min(), daily.index.max(), freq='D')
    daily = daily.reindex(full_index, fill_value=0)

    series_dict = {}
    skipped = []
    for item_name in daily.columns:
        s = daily[item_name].resample(freq).sum()
        nonzero = int((s > 0).sum())
        if nonzero < 14:
            skipped.append((item_name, nonzero))
        else:
            series_dict[item_name] = s
    return series_dict, skipped
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
C:/Users/sarah/AppData/Local/Python/bin/python -m pytest tests/test_forecaster.py -v
```

Expected: all tests `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add gamefydb/forecaster.py tests/test_forecaster.py
git commit -m "feat: forecaster - prepare_consumption_series"
```

---

## Task 5: `fit_prophet`

**Files:**
- Modify: `gamefydb/forecaster.py`
- Modify: `tests/test_forecaster.py`

> **Note:** These tests actually run Prophet (which compiles Stan on first use). First run is slow (~20–60 s). Subsequent runs are fast due to Stan caching.

- [ ] **Step 1: Add failing tests to `tests/test_forecaster.py`**

Update the import line:
```python
from gamefydb.forecaster import (
    load_data, prepare_revenue_series, prepare_consumption_series, fit_prophet,
)
```

Add these tests:

```python
def _make_daily_series(n_days: int = 60, base_value: float = 5.0) -> pd.Series:
    """Synthetic daily series with a mild weekly pattern."""
    dates = pd.date_range('2025-09-01', periods=n_days, freq='D')
    values = [base_value + (i % 7) * 0.5 for i in range(n_days)]
    return pd.Series(values, index=dates)


def test_fit_prophet_returns_correct_number_of_rows():
    series = _make_daily_series(60)
    forecast = fit_prophet(series, horizon=7, freq='D')
    assert len(forecast) == 7


def test_fit_prophet_has_required_columns():
    series = _make_daily_series(60)
    forecast = fit_prophet(series, horizon=7, freq='D')
    assert {'ds', 'yhat', 'yhat_lower', 'yhat_upper'}.issubset(forecast.columns)


def test_fit_prophet_clamps_negative_values_to_zero():
    # Near-zero series reliably produces negative yhat_lower; clamping must catch it
    dates = pd.date_range('2025-09-01', periods=60, freq='D')
    series = pd.Series([0.01] * 60, index=dates)
    forecast = fit_prophet(series, horizon=7, freq='D')
    assert (forecast['yhat'] >= 0).all()
    assert (forecast['yhat_lower'] >= 0).all()
    assert (forecast['yhat_upper'] >= 0).all()


def test_fit_prophet_weekly_freq_returns_correct_rows():
    series = _make_daily_series(60)
    forecast = fit_prophet(series, horizon=4, freq='W')
    assert len(forecast) == 4
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
C:/Users/sarah/AppData/Local/Python/bin/python -m pytest tests/test_forecaster.py::test_fit_prophet_returns_correct_number_of_rows tests/test_forecaster.py::test_fit_prophet_has_required_columns tests/test_forecaster.py::test_fit_prophet_clamps_negative_values_to_zero tests/test_forecaster.py::test_fit_prophet_weekly_freq_returns_correct_rows -v
```

Expected: `AttributeError` — `fit_prophet` not defined yet.

- [ ] **Step 3: Add `fit_prophet` to `gamefydb/forecaster.py`**

```python
def fit_prophet(series: pd.Series, horizon: int, freq: str) -> pd.DataFrame:
    """Fit a Prophet model on `series` and return a forecast DataFrame.

    The series is resampled to `freq` before fitting so the model and forecast
    are at the same granularity. Returns only future rows (beyond training data).
    yhat / yhat_lower / yhat_upper are clamped to >= 0.
    """
    logging.getLogger('prophet').setLevel(logging.WARNING)
    logging.getLogger('cmdstanpy').setLevel(logging.WARNING)

    resampled = series.resample(freq).sum()
    prophet_df = resampled.reset_index()
    prophet_df.columns = ['ds', 'y']

    m = Prophet(
        weekly_seasonality=True,
        daily_seasonality=False,
        yearly_seasonality=False,
    )
    m.fit(prophet_df)

    future = m.make_future_dataframe(periods=horizon, freq=freq)
    forecast = m.predict(future)

    max_train_date = prophet_df['ds'].max()
    future_only = forecast[forecast['ds'] > max_train_date][
        ['ds', 'yhat', 'yhat_lower', 'yhat_upper']
    ].copy()

    for col in ['yhat', 'yhat_lower', 'yhat_upper']:
        future_only[col] = future_only[col].clip(lower=0)

    return future_only.reset_index(drop=True)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
C:/Users/sarah/AppData/Local/Python/bin/python -m pytest tests/test_forecaster.py -v
```

Expected: all tests `PASSED`. (First run will be slow while Stan compiles.)

- [ ] **Step 5: Commit**

```bash
git add gamefydb/forecaster.py tests/test_forecaster.py
git commit -m "feat: forecaster - fit_prophet with resample + clamping"
```

---

## Task 6: `forecast_all` and `_print_summary`

**Files:**
- Modify: `gamefydb/forecaster.py`
- Modify: `tests/test_forecaster.py`

- [ ] **Step 1: Add failing test to `tests/test_forecaster.py`**

Update the import line:
```python
from gamefydb.forecaster import (
    load_data, prepare_revenue_series, prepare_consumption_series,
    fit_prophet, forecast_all,
)
```

Add this test:

```python
def _write_synthetic_pipeline_output(base_dir: Path) -> None:
    """Write 30-day synthetic pipeline CSV output for integration tests."""
    (base_dir / 'dims').mkdir(parents=True, exist_ok=True)
    (base_dir / 'facts').mkdir(parents=True, exist_ok=True)

    pd.DataFrame({
        'item_id': [1],
        'item_name': ['Soda'],
        'category': ['Drinks'],
    }).to_csv(base_dir / 'dims' / 'dim_item.csv', index=False)

    dates = pd.date_range('2025-09-01', periods=30, freq='D')
    pd.DataFrame({
        'movement_datetime': dates.astype(str),
        'in_out': 'Out',
        'item_id': 1,
        'quantity': 5,
        'unit_price_tnd': 2.5,
        'total_amount_tnd': 12.5,
    }).to_csv(base_dir / 'facts' / 'fact_stock_movements.csv', index=False)

    pd.DataFrame({
        'transaction_datetime': dates.astype(str),
        'income_expense': 'Income',
        'amount_tnd': 100.0,
    }).to_csv(base_dir / 'facts' / 'fact_cash_transactions.csv', index=False)


def test_forecast_all_creates_output_files(tmp_path):
    input_dir = tmp_path / 'pipeline_output'
    output_dir = tmp_path / 'forecasts'
    _write_synthetic_pipeline_output(input_dir)

    result = forecast_all(
        output_dir=str(input_dir),
        horizon=7,
        freq='D',
        forecast_dir=str(output_dir),
    )

    assert set(result.keys()) == {'consumption', 'revenue'}
    assert (output_dir / 'forecast_consumption.csv').exists()
    assert (output_dir / 'forecast_revenue.csv').exists()
    assert (output_dir / 'forecast.xlsx').exists()

    revenue_df = pd.read_csv(output_dir / 'forecast_revenue.csv')
    assert len(revenue_df) == 7
    assert set(['date', 'direct_revenue_tnd', 'direct_lower_tnd',
                'direct_upper_tnd', 'derived_revenue_tnd']).issubset(revenue_df.columns)

    consumption_df = pd.read_csv(output_dir / 'forecast_consumption.csv')
    assert set(['date', 'item_name', 'predicted_qty',
                'lower_qty', 'upper_qty']).issubset(consumption_df.columns)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
C:/Users/sarah/AppData/Local/Python/bin/python -m pytest tests/test_forecaster.py::test_forecast_all_creates_output_files -v
```

Expected: `AttributeError` — `forecast_all` not defined yet.

- [ ] **Step 3: Add `forecast_all` and `_print_summary` to `gamefydb/forecaster.py`**

```python
def _print_summary(
    consumption_df: pd.DataFrame,
    revenue_df: pd.DataFrame,
    skipped: list,
    horizon: int,
    freq: str,
) -> None:
    print(f"\n{'=' * 60}")
    print(f"FORECAST SUMMARY  (horizon={horizon}, freq={freq})")
    print(f"{'=' * 60}")

    if not consumption_df.empty:
        top10 = (
            consumption_df.groupby('item_name')['predicted_qty']
            .sum()
            .sort_values(ascending=False)
            .head(10)
            .rename('predicted_total_qty')
        )
        print("\nTop items by predicted total consumption:")
        print(top10.to_string())

    total_direct = revenue_df['direct_revenue_tnd'].sum()
    low = revenue_df['direct_lower_tnd'].sum()
    high = revenue_df['direct_upper_tnd'].sum()
    print(f"\nTotal predicted revenue: {total_direct:.2f} TND  [{low:.2f} – {high:.2f}]")

    if skipped:
        parts = [f"{name} ({count} days)" for name, count in skipped]
        print(f"\nSkipped (< 14 non-zero periods): {', '.join(parts)}")

    print(f"{'=' * 60}\n")


def forecast_all(
    output_dir: str,
    horizon: int,
    freq: str,
    forecast_dir: str,
) -> dict:
    """Orchestrate the full forecast run.

    Reads pipeline output from output_dir, fits Prophet models, writes
    CSV + Excel to forecast_dir, prints a terminal summary.

    Returns:
        {'consumption': DataFrame, 'revenue': DataFrame}
    """
    data = load_data(output_dir)
    series_dict, skipped = prepare_consumption_series(data['stock'], data['items'], freq)
    revenue_series = prepare_revenue_series(data['cash'])

    # Fit per-item consumption models
    item_forecasts = {}
    for item_name, series in series_dict.items():
        print(f"  Forecasting consumption: {item_name}...")
        item_forecasts[item_name] = fit_prophet(series, horizon, freq)

    # Fit revenue model
    print("  Forecasting revenue...")
    revenue_forecast = fit_prophet(revenue_series, horizon, freq)

    # Average unit price per item (mean of non-zero historical prices)
    stock_named = data['stock'].merge(
        data['items'][['item_id', 'item_name']], on='item_id', how='left'
    )
    avg_prices = (
        stock_named[stock_named['unit_price_tnd'] > 0]
        .groupby('item_name')['unit_price_tnd']
        .mean()
        .to_dict()
    )

    # Build consumption DataFrame (long format)
    consumption_rows = []
    for item_name, fc in item_forecasts.items():
        for _, row in fc.iterrows():
            consumption_rows.append({
                'date':          row['ds'].date(),
                'item_name':     item_name,
                'predicted_qty': row['yhat'],
                'lower_qty':     row['yhat_lower'],
                'upper_qty':     row['yhat_upper'],
            })
    consumption_df = pd.DataFrame(consumption_rows)

    # Derived revenue: sum(predicted_qty * avg_unit_price) per date
    if consumption_df.empty:
        derived_by_date: dict = {}
    else:
        consumption_df['_derived'] = consumption_df.apply(
            lambda r: r['predicted_qty'] * avg_prices.get(r['item_name'], 0.0),
            axis=1,
        )
        derived_by_date = consumption_df.groupby('date')['_derived'].sum().to_dict()
        consumption_df = consumption_df.drop(columns=['_derived'])

    # Build revenue DataFrame
    revenue_df = pd.DataFrame({
        'date':                revenue_forecast['ds'].dt.date,
        'direct_revenue_tnd':  revenue_forecast['yhat'].values,
        'direct_lower_tnd':    revenue_forecast['yhat_lower'].values,
        'direct_upper_tnd':    revenue_forecast['yhat_upper'].values,
        'derived_revenue_tnd': [
            derived_by_date.get(d, 0.0) for d in revenue_forecast['ds'].dt.date
        ],
    })

    # Write outputs
    os.makedirs(forecast_dir, exist_ok=True)
    consumption_df.to_csv(
        os.path.join(forecast_dir, 'forecast_consumption.csv'), index=False)
    revenue_df.to_csv(
        os.path.join(forecast_dir, 'forecast_revenue.csv'), index=False)

    xlsx_path = os.path.join(forecast_dir, 'forecast.xlsx')
    with pd.ExcelWriter(xlsx_path, engine='openpyxl') as writer:
        consumption_df.to_excel(writer, sheet_name='Consumption', index=False)
        revenue_df.to_excel(writer, sheet_name='Revenue', index=False)

    _print_summary(consumption_df, revenue_df, skipped, horizon, freq)

    return {'consumption': consumption_df, 'revenue': revenue_df}
```

- [ ] **Step 4: Run all tests**

```bash
C:/Users/sarah/AppData/Local/Python/bin/python -m pytest tests/test_forecaster.py -v
```

Expected: all tests `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add gamefydb/forecaster.py tests/test_forecaster.py
git commit -m "feat: forecaster - forecast_all orchestration + file output"
```

---

## Task 7: `forecast.py` CLI

**Files:**
- Create: `forecast.py`

- [ ] **Step 1: Create `forecast.py`**

```python
import argparse
from gamefydb.forecaster import forecast_all


def main():
    parser = argparse.ArgumentParser(description='GamefyDB forecasting pipeline')
    parser.add_argument('--input',   default='output',
                        help='Pipeline output directory (default: output)')
    parser.add_argument('--output',  default='output/forecasts',
                        help='Forecast output directory (default: output/forecasts)')
    parser.add_argument('--horizon', default=30, type=int,
                        help='Periods to forecast ahead (default: 30)')
    parser.add_argument('--freq',    default='D',
                        help='Forecast frequency: D=daily, W=weekly (default: D)')
    args = parser.parse_args()

    print(f'Forecasting {args.horizon} {args.freq}-period(s) ahead...')
    print(f'Reading pipeline output from: {args.input}')

    forecast_all(
        output_dir=args.input,
        horizon=args.horizon,
        freq=args.freq,
        forecast_dir=args.output,
    )

    print(f'Forecasts saved to: {args.output}/')


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: Smoke-test the CLI help**

```bash
C:/Users/sarah/AppData/Local/Python/bin/python forecast.py --help
```

Expected output includes `--horizon`, `--freq`, `--input`, `--output` arguments.

- [ ] **Step 3: Run the full test suite**

```bash
C:/Users/sarah/AppData/Local/Python/bin/python -m pytest -v
```

Expected: all tests `PASSED`.

- [ ] **Step 4: Commit**

```bash
git add forecast.py
git commit -m "feat: forecast.py CLI entry point"
```

---

## Self-Review

**Spec coverage:**

| Spec requirement | Task |
|---|---|
| `load_data` reads 3 CSVs, raises on missing | Task 2 |
| `prepare_revenue_series` Income-only, zero-fill, ValueError on all-zero | Task 3 |
| `prepare_consumption_series` Out-only, zero-fill, skip sparse (< 14 periods after resample) | Task 4 |
| `fit_prophet` resample to freq, suppress logs, clamp ≥ 0 | Task 5 |
| `forecast_all` orchestration + derived revenue | Task 6 |
| CSV output (`forecast_consumption.csv`, `forecast_revenue.csv`) | Task 6 |
| Excel output (`forecast.xlsx`, two sheets) | Task 6 |
| Terminal summary (top 10 items, total revenue, skipped list) | Task 6 |
| `forecast.py` CLI with `--input`, `--output`, `--horizon`, `--freq` | Task 7 |
| `prophet` added to `requirements.txt` | Task 1 |
| `ImportError` on missing prophet with install hint | Task 2 (module-level try/except) |

No gaps found.

**Type consistency:**

- `prepare_consumption_series` returns `(dict, list[tuple[str, int]])` — used as `series_dict, skipped` throughout. ✓
- `fit_prophet` returns DataFrame with columns `ds`, `yhat`, `yhat_lower`, `yhat_upper` — accessed by name in `forecast_all`. ✓
- `forecast_all` returns `{'consumption': DataFrame, 'revenue': DataFrame}` — checked in test. ✓
- `forecast_all(output_dir, horizon, freq, forecast_dir)` — called with same keyword args in `forecast.py`. ✓
