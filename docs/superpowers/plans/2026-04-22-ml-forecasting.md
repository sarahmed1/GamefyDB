# ML Forecasting & Bundle Suggestions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `gamefydb/forecaster.py` that reads pipeline CSVs, forecasts revenue + member activity (Prophet), and suggests item bundles (FP-Growth), with results written to `output/forecasts/` for Power BI.

**Architecture:** Standalone 5th pipeline stage. `forecaster.py` reads existing `output/facts/` and `output/dims/` CSVs, runs three independent models, and writes three forecast CSVs. Triggered via `--forecast` / `--forecast-only` flags in `run.py`.

**Tech Stack:** `prophet` (time-series forecasting), `mlxtend` (FP-Growth association rules), `pandas`

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `gamefydb/forecaster.py` | All three ML models + file I/O orchestrator |
| Create | `tests/test_forecaster.py` | Tests for all public functions |
| Modify | `requirements.txt` | Add prophet, mlxtend |
| Modify | `run.py` | Add `--forecast` and `--forecast-only` flags |

---

## Input Column Reference

These columns come from the current pipeline's transformer output:

**`output/facts/fact_cash_transactions.csv`**
- `transaction_datetime` — ISO datetime string
- `income_expense` — `'Income'` or `'Expense'`
- `transaction_type` — e.g. `'Computer Incomes'`, `'Member Transactions'`, `'Order Incomes'`
- `amount_tnd` — float

**`output/facts/fact_stock_movements.csv`**
- `movement_datetime` — ISO datetime string
- `item_id` — int FK
- `quantity` — int

**`output/dims/dim_item.csv`**
- `item_id` — int PK
- `item_name` — string

---

## Task 1: Add Dependencies

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Add prophet and mlxtend**

Replace the contents of `requirements.txt` with:

```
pandas
xlrd
openpyxl
pytest
prophet
mlxtend
```

- [ ] **Step 2: Install dependencies**

```bash
C:/Users/sarah/AppData/Local/Python/bin/python -m pip install prophet mlxtend
```

Expected: both packages install without error. Note: `prophet` installs `cmdstanpy` as a backend — first run compiles Stan models (~60s, one-time only).

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "feat: add prophet and mlxtend dependencies for ML forecasting"
```

---

## Task 2: Write Failing Tests for `forecast_revenue()`

**Files:**
- Create: `tests/test_forecaster.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_forecaster.py`:

```python
import os
from datetime import datetime, timedelta

import pandas as pd
import pytest

from gamefydb.forecaster import (
    bundle_suggestions,
    forecast_members,
    forecast_revenue,
    run_forecasts,
)


@pytest.fixture
def transactions_df():
    """60 days of synthetic cash transactions — enough for Prophet to learn weekly patterns."""
    base = datetime(2025, 9, 1)
    rows = []
    for i in range(60):
        date = base + timedelta(days=i)
        dt = date.strftime('%Y-%m-%d %H:%M:%S')
        rows.append({
            'cashier_id': 1,
            'transaction_datetime': dt,
            'income_expense': 'Income',
            'payment_method': 'Cash',
            'transaction_type': 'Computer Incomes',
            'amount_tnd': 100 + (i % 7) * 15,
            'terminal_id': 1,
        })
        rows.append({
            'cashier_id': 1,
            'transaction_datetime': dt,
            'income_expense': 'Income',
            'payment_method': 'Cash',
            'transaction_type': 'Member Transactions',
            'amount_tnd': 30.0,
            'terminal_id': None,
        })
    return pd.DataFrame(rows)


@pytest.fixture
def movements_df():
    """60 days of stock movements: 5 popular items sold daily, 2 slow items sold every 10 days."""
    base = datetime(2025, 9, 1)
    popular_ids = [1, 2, 3, 4, 5]
    slow_ids = [6, 7]
    rows = []
    for i in range(60):
        date = base + timedelta(days=i)
        dt = f"{date.strftime('%Y-%m-%d')} 14:00:00"
        for item_id in popular_ids:
            rows.append({
                'cashier_id': 1,
                'movement_datetime': dt,
                'item_id': item_id,
                'in_out': 'OUT',
                'quantity': 5,
                'unit_price_tnd': 2.0,
                'total_amount_tnd': 10.0,
                'terminal_id': None,
            })
        if i % 10 == 0:
            for item_id in slow_ids:
                rows.append({
                    'cashier_id': 1,
                    'movement_datetime': dt,
                    'item_id': item_id,
                    'in_out': 'OUT',
                    'quantity': 1,
                    'unit_price_tnd': 5.0,
                    'total_amount_tnd': 5.0,
                    'terminal_id': None,
                })
    return pd.DataFrame(rows)


@pytest.fixture
def items_df():
    return pd.DataFrame({
        'item_id':   [1,      2,        3,         4,            5,     6,       7],
        'item_name': ['Soda', 'Cookie', 'Redbull', 'Schweppes', 'Eau', 'Bouza', 'North'],
        'category':  ['Drinks', 'Food', 'Drinks', 'Drinks', 'Other', 'Other', 'Drinks'],
    })


# --- forecast_revenue tests ---

def test_forecast_revenue_columns(transactions_df):
    result = forecast_revenue(transactions_df)
    assert list(result.columns) == ['date', 'granularity', 'yhat', 'yhat_lower', 'yhat_upper']


def test_forecast_revenue_granularity_values(transactions_df):
    result = forecast_revenue(transactions_df)
    assert set(result['granularity'].unique()) == {'weekly', 'monthly'}


def test_forecast_revenue_weekly_row_count(transactions_df):
    result = forecast_revenue(transactions_df)
    assert len(result[result['granularity'] == 'weekly']) == 4


def test_forecast_revenue_monthly_row_count(transactions_df):
    result = forecast_revenue(transactions_df)
    assert len(result[result['granularity'] == 'monthly']) == 3


def test_forecast_revenue_yhat_positive(transactions_df):
    result = forecast_revenue(transactions_df)
    assert (result['yhat'] > 0).all()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
C:/Users/sarah/AppData/Local/Python/bin/python -m pytest tests/test_forecaster.py::test_forecast_revenue_columns -v
```

Expected: `ImportError` or `ModuleNotFoundError` — `gamefydb.forecaster` does not exist yet.

---

## Task 3: Implement `forecast_revenue()`

**Files:**
- Create: `gamefydb/forecaster.py`

- [ ] **Step 1: Create `gamefydb/forecaster.py` with the revenue function**

```python
import logging
import os

import pandas as pd
from mlxtend.frequent_patterns import association_rules, fpgrowth
from prophet import Prophet

logging.getLogger('cmdstanpy').setLevel(logging.WARNING)
logging.getLogger('prophet').setLevel(logging.WARNING)


def _to_daily(df: pd.DataFrame, date_col: str, value_col: str) -> pd.DataFrame:
    """Aggregate df to a daily Prophet DataFrame with columns ds, y."""
    daily = df.copy()
    daily['ds'] = pd.to_datetime(daily[date_col]).dt.normalize()
    return (
        daily.groupby('ds')[value_col]
        .sum()
        .reset_index()
        .rename(columns={value_col: 'y'})
    )


def _prophet_forecast(daily: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fit Prophet and return (weekly_4rows, monthly_3rows) DataFrames.

    Weekly: 28 daily predictions bucketed into 4 × 7-day groups (summed).
    Monthly: 90 daily predictions bucketed into 3 × 30-day groups (summed).
    """
    m = Prophet(interval_width=0.8)
    m.fit(daily)

    cols = ['ds', 'yhat', 'yhat_lower', 'yhat_upper']

    future_w = m.make_future_dataframe(periods=28)
    fc_w = m.predict(future_w)[cols].tail(28).reset_index(drop=True)
    fc_w['_b'] = fc_w.index // 7
    weekly = (
        fc_w.groupby('_b')
        .agg(date=('ds', 'last'), yhat=('yhat', 'sum'),
             yhat_lower=('yhat_lower', 'sum'), yhat_upper=('yhat_upper', 'sum'))
        .reset_index(drop=True)
    )
    weekly['granularity'] = 'weekly'

    future_m = m.make_future_dataframe(periods=90)
    fc_m = m.predict(future_m)[cols].tail(90).reset_index(drop=True)
    fc_m['_b'] = fc_m.index // 30
    monthly = (
        fc_m.groupby('_b')
        .agg(date=('ds', 'last'), yhat=('yhat', 'sum'),
             yhat_lower=('yhat_lower', 'sum'), yhat_upper=('yhat_upper', 'sum'))
        .reset_index(drop=True)
    )
    monthly['granularity'] = 'monthly'

    return weekly, monthly


def forecast_revenue(transactions_df: pd.DataFrame) -> pd.DataFrame:
    """Forecast total revenue for next 4 weeks and 3 months.

    Args:
        transactions_df: fact_cash_transactions DataFrame.
            Required columns: transaction_datetime, income_expense, amount_tnd.

    Returns:
        DataFrame — 7 rows (4 weekly + 3 monthly) with columns:
        date, granularity, yhat, yhat_lower, yhat_upper.
    """
    income = transactions_df[transactions_df['income_expense'] == 'Income'].copy()
    income['_v'] = income['amount_tnd']
    daily = _to_daily(income, 'transaction_datetime', '_v')
    weekly, monthly = _prophet_forecast(daily)
    result = pd.concat([weekly, monthly], ignore_index=True)
    return result[['date', 'granularity', 'yhat', 'yhat_lower', 'yhat_upper']]


def forecast_members(transactions_df: pd.DataFrame) -> pd.DataFrame:
    """Placeholder — implemented in Task 5."""
    raise NotImplementedError


def bundle_suggestions(movements_df: pd.DataFrame, items_df: pd.DataFrame) -> pd.DataFrame:
    """Placeholder — implemented in Task 7."""
    raise NotImplementedError


def run_forecasts(output_dir: str) -> None:
    """Placeholder — implemented in Task 9."""
    raise NotImplementedError
```

- [ ] **Step 2: Run revenue tests**

```bash
C:/Users/sarah/AppData/Local/Python/bin/python -m pytest tests/test_forecaster.py -k "revenue" -v
```

Expected: all 5 revenue tests PASS. Note: first run is slow (~60s) due to Stan compilation. Subsequent runs are fast.

- [ ] **Step 3: Commit**

```bash
git add gamefydb/forecaster.py tests/test_forecaster.py
git commit -m "feat: add forecast_revenue() with Prophet — weekly + monthly output"
```

---

## Task 4: Write Failing Tests for `forecast_members()`

**Files:**
- Modify: `tests/test_forecaster.py`

- [ ] **Step 1: Add member forecast tests** (append to `tests/test_forecaster.py`):

```python
# --- forecast_members tests ---

def test_forecast_members_columns(transactions_df):
    result = forecast_members(transactions_df)
    assert list(result.columns) == ['date', 'granularity', 'yhat', 'yhat_lower', 'yhat_upper']


def test_forecast_members_granularity_values(transactions_df):
    result = forecast_members(transactions_df)
    assert set(result['granularity'].unique()) == {'weekly', 'monthly'}


def test_forecast_members_weekly_row_count(transactions_df):
    result = forecast_members(transactions_df)
    assert len(result[result['granularity'] == 'weekly']) == 4


def test_forecast_members_monthly_row_count(transactions_df):
    result = forecast_members(transactions_df)
    assert len(result[result['granularity'] == 'monthly']) == 3


def test_forecast_members_yhat_positive(transactions_df):
    result = forecast_members(transactions_df)
    assert (result['yhat'] > 0).all()
```

- [ ] **Step 2: Run to verify failure**

```bash
C:/Users/sarah/AppData/Local/Python/bin/python -m pytest tests/test_forecaster.py -k "members" -v
```

Expected: all 5 tests FAIL with `NotImplementedError`.

---

## Task 5: Implement `forecast_members()`

**Files:**
- Modify: `gamefydb/forecaster.py`

- [ ] **Step 1: Replace the `forecast_members` placeholder**

Find this in `gamefydb/forecaster.py`:
```python
def forecast_members(transactions_df: pd.DataFrame) -> pd.DataFrame:
    """Placeholder — implemented in Task 5."""
    raise NotImplementedError
```

Replace with:
```python
def forecast_members(transactions_df: pd.DataFrame) -> pd.DataFrame:
    """Forecast member transaction count for next 4 weeks and 3 months.

    Uses 'Member Transactions' rows as a daily proxy for member activity.

    Args:
        transactions_df: fact_cash_transactions DataFrame.
            Required columns: transaction_datetime, transaction_type.

    Returns:
        DataFrame — 7 rows (4 weekly + 3 monthly) with columns:
        date, granularity, yhat, yhat_lower, yhat_upper.
    """
    members = transactions_df[
        transactions_df['transaction_type'] == 'Member Transactions'
    ].copy()
    members['_v'] = 1
    daily = _to_daily(members, 'transaction_datetime', '_v')
    weekly, monthly = _prophet_forecast(daily)
    result = pd.concat([weekly, monthly], ignore_index=True)
    return result[['date', 'granularity', 'yhat', 'yhat_lower', 'yhat_upper']]
```

- [ ] **Step 2: Run member tests**

```bash
C:/Users/sarah/AppData/Local/Python/bin/python -m pytest tests/test_forecaster.py -k "members" -v
```

Expected: all 5 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add gamefydb/forecaster.py tests/test_forecaster.py
git commit -m "feat: add forecast_members() — daily member activity forecasted via Prophet"
```

---

## Task 6: Write Failing Tests for `bundle_suggestions()`

**Files:**
- Modify: `tests/test_forecaster.py`

- [ ] **Step 1: Add bundle tests** (append to `tests/test_forecaster.py`):

```python
# --- bundle_suggestions tests ---

def test_bundle_suggestions_columns(movements_df, items_df):
    result = bundle_suggestions(movements_df, items_df)
    assert list(result.columns) == ['slow_item', 'pair_with', 'co_occurrence_pct']


def test_bundle_suggestions_slow_items_are_not_popular(movements_df, items_df):
    result = bundle_suggestions(movements_df, items_df)
    popular_names = {'Soda', 'Cookie', 'Redbull', 'Schweppes', 'Eau'}
    for _, row in result.iterrows():
        assert row['slow_item'] not in popular_names, (
            f"Expected slow_item to not be in popular set, got {row['slow_item']}"
        )


def test_bundle_suggestions_pair_with_is_popular(movements_df, items_df):
    result = bundle_suggestions(movements_df, items_df)
    popular_names = {'Soda', 'Cookie', 'Redbull', 'Schweppes', 'Eau'}
    for _, row in result.iterrows():
        assert row['pair_with'] in popular_names, (
            f"Expected pair_with to be popular, got {row['pair_with']}"
        )


def test_bundle_suggestions_one_row_per_slow_item(movements_df, items_df):
    result = bundle_suggestions(movements_df, items_df)
    assert result['slow_item'].nunique() == len(result)


def test_bundle_suggestions_empty_when_no_data(items_df):
    empty_movements = pd.DataFrame(columns=[
        'cashier_id', 'movement_datetime', 'item_id',
        'in_out', 'quantity', 'unit_price_tnd', 'total_amount_tnd', 'terminal_id'
    ])
    result = bundle_suggestions(empty_movements, items_df)
    assert list(result.columns) == ['slow_item', 'pair_with', 'co_occurrence_pct']
    assert len(result) == 0
```

- [ ] **Step 2: Run to verify failure**

```bash
C:/Users/sarah/AppData/Local/Python/bin/python -m pytest tests/test_forecaster.py -k "bundle" -v
```

Expected: all 5 tests FAIL with `NotImplementedError`.

---

## Task 7: Implement `bundle_suggestions()`

**Files:**
- Modify: `gamefydb/forecaster.py`

- [ ] **Step 1: Replace the `bundle_suggestions` placeholder**

Find:
```python
def bundle_suggestions(movements_df: pd.DataFrame, items_df: pd.DataFrame) -> pd.DataFrame:
    """Placeholder — implemented in Task 7."""
    raise NotImplementedError
```

Replace with:
```python
def bundle_suggestions(movements_df: pd.DataFrame, items_df: pd.DataFrame) -> pd.DataFrame:
    """Find bundle pairings: slow items paired with popular items they co-occur with.

    Groups stock movements by date+hour to form baskets, then mines association
    rules where a slow item (below-median quantity) implies a popular item (top 5).

    Args:
        movements_df: fact_stock_movements DataFrame.
            Required columns: movement_datetime, item_id, quantity.
        items_df: dim_item DataFrame.
            Required columns: item_id, item_name.

    Returns:
        DataFrame with columns: slow_item, pair_with, co_occurrence_pct.
        One row per slow item (best pairing by confidence).
        Empty DataFrame with correct columns if no rules are found.
    """
    empty = pd.DataFrame(columns=['slow_item', 'pair_with', 'co_occurrence_pct'])

    if movements_df.empty:
        return empty

    qty = movements_df.groupby('item_id')['quantity'].sum()
    popular_ids = set(qty.nlargest(5).index)
    slow_ids = set(qty[qty < qty.median()].index)

    item_name = dict(zip(items_df['item_id'], items_df['item_name']))

    df = movements_df.copy()
    df['basket_key'] = pd.to_datetime(df['movement_datetime']).dt.strftime('%Y-%m-%d %H')
    baskets = (
        df.groupby(['basket_key', 'item_id'])
        .size()
        .unstack(fill_value=0)
        .gt(0)
    )

    if baskets.shape[0] < 2 or baskets.shape[1] < 2:
        return empty

    freq = fpgrowth(baskets, min_support=0.01, use_colnames=True)
    if freq.empty:
        return empty

    rules = association_rules(freq, metric='confidence', min_threshold=0.1,
                              num_itemsets=len(freq))

    rows = []
    for _, rule in rules.iterrows():
        ants, cons = rule['antecedents'], rule['consequents']
        if len(ants) == 1 and len(cons) == 1:
            ant_id, con_id = next(iter(ants)), next(iter(cons))
            if ant_id in slow_ids and con_id in popular_ids:
                rows.append({
                    'slow_item': item_name.get(ant_id, str(ant_id)),
                    'pair_with': item_name.get(con_id, str(con_id)),
                    'co_occurrence_pct': round(rule['confidence'] * 100, 1),
                })

    if not rows:
        return empty

    return (
        pd.DataFrame(rows)
        .sort_values('co_occurrence_pct', ascending=False)
        .drop_duplicates(subset=['slow_item'])
        .reset_index(drop=True)
    )
```

- [ ] **Step 2: Run bundle tests**

```bash
C:/Users/sarah/AppData/Local/Python/bin/python -m pytest tests/test_forecaster.py -k "bundle" -v
```

Expected: all 5 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add gamefydb/forecaster.py tests/test_forecaster.py
git commit -m "feat: add bundle_suggestions() via FP-Growth association rules"
```

---

## Task 8: Write Failing Tests for `run_forecasts()`

**Files:**
- Modify: `tests/test_forecaster.py`

- [ ] **Step 1: Add orchestration tests** (append to `tests/test_forecaster.py`):

```python
# --- run_forecasts tests ---

def test_run_forecasts_creates_forecast_directory(tmp_path, transactions_df, movements_df, items_df):
    facts_dir = tmp_path / 'facts'
    dims_dir = tmp_path / 'dims'
    facts_dir.mkdir()
    dims_dir.mkdir()
    transactions_df.to_csv(facts_dir / 'fact_cash_transactions.csv', index=False)
    movements_df.to_csv(facts_dir / 'fact_stock_movements.csv', index=False)
    items_df.to_csv(dims_dir / 'dim_item.csv', index=False)

    run_forecasts(str(tmp_path))

    assert (tmp_path / 'forecasts').is_dir()


def test_run_forecasts_creates_revenue_csv(tmp_path, transactions_df, movements_df, items_df):
    facts_dir = tmp_path / 'facts'
    dims_dir = tmp_path / 'dims'
    facts_dir.mkdir()
    dims_dir.mkdir()
    transactions_df.to_csv(facts_dir / 'fact_cash_transactions.csv', index=False)
    movements_df.to_csv(facts_dir / 'fact_stock_movements.csv', index=False)
    items_df.to_csv(dims_dir / 'dim_item.csv', index=False)

    run_forecasts(str(tmp_path))

    result = pd.read_csv(tmp_path / 'forecasts' / 'forecast_revenue.csv')
    assert list(result.columns) == ['date', 'granularity', 'yhat', 'yhat_lower', 'yhat_upper']


def test_run_forecasts_creates_members_csv(tmp_path, transactions_df, movements_df, items_df):
    facts_dir = tmp_path / 'facts'
    dims_dir = tmp_path / 'dims'
    facts_dir.mkdir()
    dims_dir.mkdir()
    transactions_df.to_csv(facts_dir / 'fact_cash_transactions.csv', index=False)
    movements_df.to_csv(facts_dir / 'fact_stock_movements.csv', index=False)
    items_df.to_csv(dims_dir / 'dim_item.csv', index=False)

    run_forecasts(str(tmp_path))

    result = pd.read_csv(tmp_path / 'forecasts' / 'forecast_members.csv')
    assert list(result.columns) == ['date', 'granularity', 'yhat', 'yhat_lower', 'yhat_upper']


def test_run_forecasts_creates_bundles_csv(tmp_path, transactions_df, movements_df, items_df):
    facts_dir = tmp_path / 'facts'
    dims_dir = tmp_path / 'dims'
    facts_dir.mkdir()
    dims_dir.mkdir()
    transactions_df.to_csv(facts_dir / 'fact_cash_transactions.csv', index=False)
    movements_df.to_csv(facts_dir / 'fact_stock_movements.csv', index=False)
    items_df.to_csv(dims_dir / 'dim_item.csv', index=False)

    run_forecasts(str(tmp_path))

    result = pd.read_csv(tmp_path / 'forecasts' / 'bundle_suggestions.csv')
    assert list(result.columns) == ['slow_item', 'pair_with', 'co_occurrence_pct']
```

- [ ] **Step 2: Run to verify failure**

```bash
C:/Users/sarah/AppData/Local/Python/bin/python -m pytest tests/test_forecaster.py -k "run_forecasts" -v
```

Expected: all 4 tests FAIL with `NotImplementedError`.

---

## Task 9: Implement `run_forecasts()`

**Files:**
- Modify: `gamefydb/forecaster.py`

- [ ] **Step 1: Replace the `run_forecasts` placeholder**

Find:
```python
def run_forecasts(output_dir: str) -> None:
    """Placeholder — implemented in Task 9."""
    raise NotImplementedError
```

Replace with:
```python
def run_forecasts(output_dir: str) -> None:
    """Read pipeline output CSVs, run all forecasts, write to output_dir/forecasts/.

    Args:
        output_dir: Root output directory containing facts/ and dims/ subdirectories.
    """
    forecasts_dir = os.path.join(output_dir, 'forecasts')
    os.makedirs(forecasts_dir, exist_ok=True)

    transactions = pd.read_csv(
        os.path.join(output_dir, 'facts', 'fact_cash_transactions.csv')
    )
    movements = pd.read_csv(
        os.path.join(output_dir, 'facts', 'fact_stock_movements.csv')
    )
    items = pd.read_csv(os.path.join(output_dir, 'dims', 'dim_item.csv'))

    print('  Forecasting revenue...')
    forecast_revenue(transactions).to_csv(
        os.path.join(forecasts_dir, 'forecast_revenue.csv'), index=False
    )

    print('  Forecasting member activity...')
    forecast_members(transactions).to_csv(
        os.path.join(forecasts_dir, 'forecast_members.csv'), index=False
    )

    print('  Computing bundle suggestions...')
    bundle_suggestions(movements, items).to_csv(
        os.path.join(forecasts_dir, 'bundle_suggestions.csv'), index=False
    )

    print(f'  Forecasts saved to {forecasts_dir}/')
```

- [ ] **Step 2: Run orchestration tests**

```bash
C:/Users/sarah/AppData/Local/Python/bin/python -m pytest tests/test_forecaster.py -k "run_forecasts" -v
```

Expected: all 4 tests PASS.

- [ ] **Step 3: Run the full test suite**

```bash
C:/Users/sarah/AppData/Local/Python/bin/python -m pytest -v
```

Expected: all tests PASS (forecaster tests + existing writer/transformer/cleaner/ingestor tests).

- [ ] **Step 4: Commit**

```bash
git add gamefydb/forecaster.py tests/test_forecaster.py
git commit -m "feat: add run_forecasts() orchestrator — reads pipeline CSVs, writes forecast CSVs"
```

---

## Task 10: Wire `--forecast` and `--forecast-only` into `run.py`

**Files:**
- Modify: `run.py`

- [ ] **Step 1: Replace `run.py` with the updated version**

```python
import argparse

from gamefydb.ingestor import ingest_all
from gamefydb.cleaner import clean_all
from gamefydb.transformer import transform
from gamefydb.writer import write_all


def main():
    parser = argparse.ArgumentParser(description='GamefyDB ETL pipeline')
    parser.add_argument('--input',  default='excel',  help='Directory containing .xls source files')
    parser.add_argument('--output', default='output', help='Output directory')
    parser.add_argument('--format', dest='fmt', choices=['csv', 'excel'], default='csv',
                        help='Output format: csv (default) or excel')
    parser.add_argument('--forecast', action='store_true',
                        help='Run ML forecasting after the ETL pipeline')
    parser.add_argument('--forecast-only', action='store_true',
                        help='Skip ETL and run only forecasting on existing output CSVs')
    args = parser.parse_args()

    if not args.forecast_only:
        print(f'Ingesting from {args.input}...')
        raw = ingest_all(args.input)

        print('Cleaning...')
        cleaned = clean_all(raw)

        print('Transforming to star schema...')
        schema = transform(cleaned)

        print(f'Writing {args.fmt} output to {args.output}...')
        write_all(schema, args.output, fmt=args.fmt)

        print('Done.')
        for name, df in schema.items():
            print(f'  {name}: {len(df)} rows')

    if args.forecast or args.forecast_only:
        from gamefydb.forecaster import run_forecasts
        print('Running forecasts...')
        run_forecasts(args.output)


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: Verify `--help` output**

```bash
C:/Users/sarah/AppData/Local/Python/bin/python run.py --help
```

Expected output includes:
```
  --forecast            Run ML forecasting after the ETL pipeline
  --forecast-only       Skip ETL and run only forecasting on existing output CSVs
```

- [ ] **Step 3: Run the full test suite one last time**

```bash
C:/Users/sarah/AppData/Local/Python/bin/python -m pytest -v
```

Expected: all tests PASS.

- [ ] **Step 4: Commit**

```bash
git add run.py
git commit -m "feat: add --forecast and --forecast-only flags to run.py"
```

---

## Task 11: End-to-End Smoke Test

- [ ] **Step 1: Run the full pipeline + forecast on real data**

```bash
C:/Users/sarah/AppData/Local/Python/bin/python run.py --input excel --output output --forecast
```

Expected: pipeline completes, then prints:
```
Running forecasts...
  Forecasting revenue...
  Forecasting member activity...
  Computing bundle suggestions...
  Forecasts saved to output/forecasts/
```

- [ ] **Step 2: Verify output files exist and have data**

```bash
C:/Users/sarah/AppData/Local/Python/bin/python -c "
import pandas as pd
for f in ['output/forecasts/forecast_revenue.csv',
          'output/forecasts/forecast_members.csv',
          'output/forecasts/bundle_suggestions.csv']:
    df = pd.read_csv(f)
    print(f'{f}: {len(df)} rows')
    print(df.to_string(index=False))
    print()
"
```

Expected: 3 files, each with data. `forecast_revenue.csv` and `forecast_members.csv` each have 7 rows (4 weekly + 3 monthly). `bundle_suggestions.csv` has at least 1 row.

- [ ] **Step 3: Commit**

```bash
git add output/forecasts/
git commit -m "feat: add forecast output files to output/forecasts/"
```
