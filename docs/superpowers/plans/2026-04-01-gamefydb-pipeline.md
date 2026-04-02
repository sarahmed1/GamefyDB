# GamefyDB ETL Pipeline — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a modular Python ETL pipeline that ingests 4 raw `.xls` gaming center report files, strips page artifacts and footers, normalizes all data types, and outputs a star schema (dims + facts) as CSVs or Excel ready for DWH import.

**Architecture:** Four-stage pipeline (ingest → clean → transform → write), each stage as an independent module in the `gamefydb/` package. Data flows as plain pandas DataFrames between stages. The CLI entry point `run.py` wires the stages together.

**Tech Stack:** Python 3, pandas, xlrd (`.xls` reading), openpyxl (Excel output), pytest (testing), argparse (CLI)

> **Context7 note:** Use `mcp__plugin_context7_context7__resolve-library-id` + `mcp__plugin_context7_context7__query-docs` to fetch current docs for pandas, xlrd, and openpyxl before implementing tasks that use those libraries.

---

## File Map

| File | Responsibility |
|---|---|
| `gamefydb/ingestor.py` | Read `.xls` via xlrd, strip page-break artifacts + footers, return raw DataFrames |
| `gamefydb/cleaner.py` | Normalize amounts, datetimes, durations, terminal IDs, booleans per file type |
| `gamefydb/transformer.py` | Build star schema: 4 dim tables + 4 fact tables with FK resolution |
| `gamefydb/writer.py` | Write tables to `output/dims/` and `output/facts/` as CSV or single Excel workbook |
| `run.py` | CLI entry point: `--input`, `--output`, `--format` |
| `tests/test_ingestor.py` | Unit + integration tests for ingestor |
| `tests/test_cleaner.py` | Unit tests for each cleaner function + `clean_all` |
| `tests/test_transformer.py` | Unit tests for dim and fact building |
| `tests/test_writer.py` | Unit tests for CSV and Excel writing |
| `tests/test_run.py` | Subprocess tests for the CLI |

---

## Verified Column Positions (from source file inspection)

These are the **data** column indices (0-based) in the raw `.xls` files — some differ from header positions due to merged cells.

**Cash** (60 cols):
`0=cashier, 4=date, 9=income_expense, 11=payment_method, 21=transaction_type, 40=amount, 51=comment`

**Sessions** (35 cols):
`0=cashier, 4=terminal, 9=session_type, 12=free_time, 14=paused, 20=duration, 22=order_transfer, 27=usb_data, 28=usage, 30=discount, 32=total_amount`

**Stock** (36 cols):
`0=cashier, 4=date, 8=item_name, 13=category, 20=in_out, 25=quantity, 28=unit_price, 29=total_amount, 32=comment`

**Members** (34 cols):
`2=member_id, 6=username, 8=firstname, 13=lastname, 14=duration, 22=usage, 27=orders_transfer, 28=usb_data, 30=total_amount`

---

## Task 1: Project scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `gamefydb/__init__.py`
- Create: `tests/__init__.py`
- Create: `pytest.ini`

- [ ] **Step 1: Create `requirements.txt`**

```
pandas
xlrd
openpyxl
pytest
```

- [ ] **Step 2: Create `.gitignore`**

```
output/
__pycache__/
*.pyc
.pytest_cache/
*.egg-info/
```

- [ ] **Step 3: Create `gamefydb/__init__.py` (empty)**

```python
```

- [ ] **Step 4: Create `tests/__init__.py` (empty)**

```python
```

- [ ] **Step 5: Create `pytest.ini`**

```ini
[pytest]
testpaths = tests
```

- [ ] **Step 6: Install dependencies**

Run: `pip install -r requirements.txt`
Expected: All packages install without error.

- [ ] **Step 7: Initialize git and make first commit**

```bash
git init
git add requirements.txt .gitignore gamefydb/__init__.py tests/__init__.py pytest.ini
git commit -m "chore: scaffold gamefydb package"
```

---

## Task 2: Ingestor — `_strip_artifacts`

**Files:**
- Create: `gamefydb/ingestor.py`
- Create: `tests/test_ingestor.py`

Core stripping logic: given a raw DataFrame (all rows × all cols, no header), a column map `{col_idx: name}`, and the name of the key column, return a clean DataFrame with only real data rows and the mapped columns.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_ingestor.py`:

```python
import numpy as np
import pandas as pd
import pytest
from gamefydb.ingestor import _strip_artifacts

CASH_COL_MAP = {
    0: 'cashier', 4: 'date', 9: 'income_expense', 11: 'payment_method',
    21: 'transaction_type', 40: 'amount', 51: 'comment',
}


def make_cash_raw():
    """Minimal raw Cash DataFrame replicating real artifact structure."""
    n = 60
    nan = np.nan

    def row(vals):
        r = [nan] * n
        for k, v in vals.items():
            r[k] = v
        return r

    return pd.DataFrame([
        row({0: 'Cash Reports'}),                           # 0: title
        row({55: '23/03/2026'}),                            # 1: report date
        row({}),                                            # 2: blank
        row({}),                                            # 3: blank
        row({0: 'Cashier', 4: 'Date', 9: 'Income/Expense', # 4: headers
             11: 'Payment Method', 21: 'Transaction Type',
             40: 'Amount', 50: 'Comment'}),
        row({0: 'taktek', 4: '23.03.2026 03:23:54',         # 5: data row 1
             9: 'Income', 11: 'Cash',
             21: 'Order Incomes', 40: '27,50 TND',
             51: '(PS5 (1))'}),
        row({0: 'youssef', 4: '22.03.2026 17:41:47',        # 6: data row 2
             9: 'Income', 11: 'Cash',
             21: 'Member Transactions', 40: '30,00 TND',
             51: 'Money deposited to member'}),
        row({}),                                            # 7: blank (page break)
        row({}),                                            # 8: blank
        row({54: 'Page 1/3'}),                              # 9: page marker
        row({}),                                            # 10: blank after marker
        row({0: 'Cashier', 4: 'Date'}),                    # 11: repeated header
        row({0: 'taktek', 4: '21.03.2026 03:38:54',         # 12: data row 3
             9: 'Income', 11: 'Cash',
             21: 'Computer Incomes', 40: '24,50 TND',
             51: '(GAMEFY09)'}),
        row({}),                                            # 13: blank (footer)
        row({8: 'Computer Incomes'}),                       # 14: footer row
        row({8: '76245,51 TND'}),                           # 15: footer row
        row({}),                                            # 16: blank
        row({54: 'Page 3/3'}),                              # 17: final page marker
    ])


def test_strip_artifacts_row_count():
    result = _strip_artifacts(make_cash_raw(), CASH_COL_MAP, 'date')
    assert len(result) == 3


def test_strip_artifacts_columns():
    result = _strip_artifacts(make_cash_raw(), CASH_COL_MAP, 'date')
    assert list(result.columns) == [
        'cashier', 'date', 'income_expense',
        'payment_method', 'transaction_type', 'amount', 'comment',
    ]


def test_strip_artifacts_data_preserved():
    result = _strip_artifacts(make_cash_raw(), CASH_COL_MAP, 'date')
    assert result.iloc[0]['cashier'] == 'taktek'
    assert result.iloc[0]['amount'] == '27,50 TND'
    assert result.iloc[1]['cashier'] == 'youssef'
    assert result.iloc[2]['cashier'] == 'taktek'
    assert result.iloc[2]['date'] == '21.03.2026 03:38:54'


def test_strip_artifacts_no_page_markers():
    result = _strip_artifacts(make_cash_raw(), CASH_COL_MAP, 'date')
    for col in result.columns:
        assert not result[col].astype(str).str.contains(r'Page \d+/\d+').any()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_ingestor.py -v`
Expected: `ImportError: cannot import name '_strip_artifacts' from 'gamefydb.ingestor'`

- [ ] **Step 3: Implement `_strip_artifacts` in `gamefydb/ingestor.py`**

```python
import re
import pandas as pd
import xlrd

PAGE_PATTERN = re.compile(r'Page \d+/\d+')


def _strip_artifacts(df: pd.DataFrame, col_map: dict, key_col: str) -> pd.DataFrame:
    """Strip all non-data rows from a raw Excel DataFrame.

    Removes: title row, report date row, blank rows, page markers,
    repeated header rows, and footer rows below the last data row.

    Args:
        df: Raw DataFrame read with header=None (all rows, all cols).
        col_map: {raw_col_index: output_col_name} for the columns to keep.
        key_col: Name (from col_map) of the column that is non-empty only on
                 real data rows (e.g. 'date' for Cash/Stock, 'terminal' for
                 Sessions, 'member_id' for Members).

    Returns:
        DataFrame with only the mapped columns and only data rows.
    """
    # Drop title, report-date, blank, blank, header rows (rows 0–4)
    df = df.iloc[5:].reset_index(drop=True)

    # Drop page marker rows — any cell matching "Page X/Y"
    has_page = df.apply(
        lambda row: any(PAGE_PATTERN.search(str(v)) for v in row),
        axis=1,
    )
    df = df[~has_page].reset_index(drop=True)

    # Drop repeated header rows ("Cashier" text in the first mapped column)
    first_idx = min(col_map.keys())
    df = df[
        df.iloc[:, first_idx].astype(str).str.strip() != 'Cashier'
    ].reset_index(drop=True)

    # Extract and rename the mapped columns
    df = df[list(col_map.keys())].rename(columns=col_map)

    # Drop rows where the key column is empty or NaN (footer / blank rows)
    key = df[key_col].astype(str).str.strip()
    df = df[~key.isin(['', 'nan'])].reset_index(drop=True)

    return df
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ingestor.py -v`
Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add gamefydb/ingestor.py tests/test_ingestor.py
git commit -m "feat: ingestor - strip page artifacts and footers"
```

---

## Task 3: Ingestor — `ingest_all`

**Files:**
- Modify: `gamefydb/ingestor.py`
- Modify: `tests/test_ingestor.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_ingestor.py`:

```python
import os
from gamefydb.ingestor import ingest_all

EXCEL_DIR = os.path.join(os.path.dirname(__file__), '..', 'excel')


def test_ingest_all_returns_four_keys():
    result = ingest_all(EXCEL_DIR)
    assert set(result.keys()) == {'cash', 'sessions', 'stock', 'members'}


def test_ingest_cash_columns():
    result = ingest_all(EXCEL_DIR)
    assert list(result['cash'].columns) == [
        'cashier', 'date', 'income_expense', 'payment_method',
        'transaction_type', 'amount', 'comment',
    ]


def test_ingest_sessions_columns():
    result = ingest_all(EXCEL_DIR)
    assert list(result['sessions'].columns) == [
        'cashier', 'terminal', 'session_type', 'free_time', 'paused',
        'duration', 'order_transfer', 'usb_data', 'usage', 'discount', 'total_amount',
    ]


def test_ingest_stock_columns():
    result = ingest_all(EXCEL_DIR)
    assert list(result['stock'].columns) == [
        'cashier', 'date', 'item_name', 'category', 'in_out',
        'quantity', 'unit_price', 'total_amount', 'comment',
    ]


def test_ingest_members_columns():
    result = ingest_all(EXCEL_DIR)
    assert list(result['members'].columns) == [
        'member_id', 'username', 'firstname', 'lastname',
        'duration', 'usage', 'orders_transfer', 'usb_data', 'total_amount',
    ]


def test_ingest_cash_has_data():
    result = ingest_all(EXCEL_DIR)
    assert len(result['cash']) > 100


def test_ingest_no_page_marker_rows():
    result = ingest_all(EXCEL_DIR)
    for name, df in result.items():
        for col in df.columns:
            has_page = df[col].astype(str).str.contains(r'Page \d+/\d+', regex=True)
            assert not has_page.any(), f"{name}.{col} still contains page markers"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_ingestor.py::test_ingest_all_returns_four_keys -v`
Expected: `ImportError: cannot import name 'ingest_all'`

- [ ] **Step 3: Add column maps and `ingest_all` to `gamefydb/ingestor.py`**

Append to `gamefydb/ingestor.py` (after `_strip_artifacts`):

```python
COLUMN_MAPS = {
    'cash': {
        0: 'cashier', 4: 'date', 9: 'income_expense', 11: 'payment_method',
        21: 'transaction_type', 40: 'amount', 51: 'comment',
    },
    'sessions': {
        0: 'cashier', 4: 'terminal', 9: 'session_type', 12: 'free_time',
        14: 'paused', 20: 'duration', 22: 'order_transfer', 27: 'usb_data',
        28: 'usage', 30: 'discount', 32: 'total_amount',
    },
    'stock': {
        0: 'cashier', 4: 'date', 8: 'item_name', 13: 'category',
        20: 'in_out', 25: 'quantity', 28: 'unit_price', 29: 'total_amount',
        32: 'comment',
    },
    'members': {
        2: 'member_id', 6: 'username', 8: 'firstname', 13: 'lastname',
        14: 'duration', 22: 'usage', 27: 'orders_transfer', 28: 'usb_data',
        30: 'total_amount',
    },
}

FILE_MAP = {
    'cash':     'Cash DATA 01-09-2025.xls',
    'sessions': 'DATA session reports 01-09-2025.xls',
    'stock':    'Stock DATA 01-09-2025.xls',
    'members':  'memeber DATA 01-09-2025.xls',
}

KEY_COLS = {
    'cash':     'date',
    'sessions': 'terminal',
    'stock':    'date',
    'members':  'member_id',
}


def _read_raw(path: str) -> pd.DataFrame:
    """Read .xls via xlrd into a DataFrame with no header parsing."""
    wb = xlrd.open_workbook(path)
    ws = wb.sheet_by_index(0)
    return pd.DataFrame([ws.row_values(i) for i in range(ws.nrows)])


def ingest_all(input_dir: str) -> dict:
    """Read all four source files and return stripped DataFrames.

    Returns:
        {'cash': df, 'sessions': df, 'stock': df, 'members': df}
    """
    base = input_dir.rstrip('/').rstrip('\\')
    result = {}
    for name, filename in FILE_MAP.items():
        path = f"{base}/{filename}"
        df_raw = _read_raw(path)
        result[name] = _strip_artifacts(df_raw, COLUMN_MAPS[name], KEY_COLS[name])
    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ingestor.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add gamefydb/ingestor.py tests/test_ingestor.py
git commit -m "feat: ingestor - load all four source files"
```

---

## Task 4: Cleaner — `parse_amount`

**Files:**
- Create: `gamefydb/cleaner.py`
- Create: `tests/test_cleaner.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_cleaner.py`:

```python
import pytest
from gamefydb.cleaner import parse_amount


def test_parse_amount_simple():
    assert parse_amount('27,50 TND') == 27.50


def test_parse_amount_thousands_narrow_space():
    # \u202f is the narrow no-break space used as thousands separator
    assert parse_amount('1\u202f745,44 TND') == 1745.44


def test_parse_amount_zero():
    assert parse_amount('0,00 TND') == 0.0


def test_parse_amount_large():
    assert parse_amount('53\u202f366,12 TND') == 53366.12


def test_parse_amount_whole():
    assert parse_amount('8,00 TND') == 8.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_cleaner.py -v`
Expected: `ImportError: cannot import name 'parse_amount' from 'gamefydb.cleaner'`

- [ ] **Step 3: Implement `parse_amount` in `gamefydb/cleaner.py`**

```python
import re
import pandas as pd


def parse_amount(value: str) -> float:
    """Parse '1 745,44 TND' → 1745.44.

    Handles narrow no-break space (\\u202f) as thousands separator
    and comma as decimal separator.
    """
    s = str(value).replace('\u202f', '').replace(' TND', '').replace(',', '.')
    return float(s)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_cleaner.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add gamefydb/cleaner.py tests/test_cleaner.py
git commit -m "feat: cleaner - parse_amount"
```

---

## Task 5: Cleaner — `parse_datetime`

**Files:**
- Modify: `gamefydb/cleaner.py`
- Modify: `tests/test_cleaner.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_cleaner.py`:

```python
from datetime import datetime
from gamefydb.cleaner import parse_datetime


def test_parse_datetime_full():
    assert parse_datetime('23.03.2026 03:23:54') == datetime(2026, 3, 23, 3, 23, 54)


def test_parse_datetime_midnight():
    assert parse_datetime('01.09.2025 08:00:00') == datetime(2025, 9, 1, 8, 0, 0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_cleaner.py::test_parse_datetime_full -v`
Expected: `ImportError: cannot import name 'parse_datetime'`

- [ ] **Step 3: Add `parse_datetime` to `gamefydb/cleaner.py`**

Append to `gamefydb/cleaner.py`:

```python
from datetime import datetime as _dt


def parse_datetime(value: str) -> _dt:
    """Parse '23.03.2026 03:23:54' → datetime(2026, 3, 23, 3, 23, 54)."""
    return _dt.strptime(str(value).strip(), '%d.%m.%Y %H:%M:%S')
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_cleaner.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add gamefydb/cleaner.py tests/test_cleaner.py
git commit -m "feat: cleaner - parse_datetime"
```

---

## Task 6: Cleaner — `parse_duration`

**Files:**
- Modify: `gamefydb/cleaner.py`
- Modify: `tests/test_cleaner.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_cleaner.py`:

```python
from gamefydb.cleaner import parse_duration


def test_parse_duration_hours_and_minutes():
    assert parse_duration('1 h 29 min') == 89


def test_parse_duration_minutes_only():
    assert parse_duration('30 min') == 30


def test_parse_duration_hours_zero_minutes():
    assert parse_duration('2 h 00 min') == 120


def test_parse_duration_large():
    assert parse_duration('223 h 26 min') == 13406
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_cleaner.py::test_parse_duration_hours_and_minutes -v`
Expected: `ImportError: cannot import name 'parse_duration'`

- [ ] **Step 3: Add `parse_duration` to `gamefydb/cleaner.py`**

Append to `gamefydb/cleaner.py`:

```python
_DURATION_RE = re.compile(r'(?:(\d+)\s*h\s*)?(\d+)\s*min')


def parse_duration(value: str) -> int:
    """Parse '1 h 29 min' → 89, '30 min' → 30 (total minutes)."""
    m = _DURATION_RE.search(str(value))
    if not m:
        raise ValueError(f"Cannot parse duration: {value!r}")
    hours = int(m.group(1)) if m.group(1) else 0
    return hours * 60 + int(m.group(2))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_cleaner.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add gamefydb/cleaner.py tests/test_cleaner.py
git commit -m "feat: cleaner - parse_duration"
```

---

## Task 7: Cleaner — `extract_terminal`

**Files:**
- Modify: `gamefydb/cleaner.py`
- Modify: `tests/test_cleaner.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_cleaner.py`:

```python
from gamefydb.cleaner import extract_terminal


def test_extract_terminal_simple():
    assert extract_terminal('(GAMEFY01)') == 'GAMEFY01'


def test_extract_terminal_with_inner_parens():
    # PS5 (1) has inner parentheses — outer parens only are stripped
    assert extract_terminal('(PS5 (1))') == 'PS5 (1)'


def test_extract_terminal_vip():
    assert extract_terminal('(GAMEFY-VIP)') == 'GAMEFY-VIP'


def test_extract_terminal_no_match():
    assert extract_terminal('Money deposited to member') is None


def test_extract_terminal_none():
    assert extract_terminal(None) is None


def test_extract_terminal_nan():
    import math
    assert extract_terminal(float('nan')) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_cleaner.py::test_extract_terminal_simple -v`
Expected: `ImportError: cannot import name 'extract_terminal'`

- [ ] **Step 3: Add `extract_terminal` to `gamefydb/cleaner.py`**

Append to `gamefydb/cleaner.py`:

```python
_TERMINAL_RE = re.compile(r'^\((.+)\)$')


def extract_terminal(value) -> str | None:
    """Extract terminal name from comment like '(GAMEFY01)' → 'GAMEFY01'.

    The regex strips only the outermost parens, so '(PS5 (1))' → 'PS5 (1)'.
    Returns None if the value is null or does not match the pattern.
    """
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    m = _TERMINAL_RE.match(str(value).strip())
    return m.group(1) if m else None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_cleaner.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add gamefydb/cleaner.py tests/test_cleaner.py
git commit -m "feat: cleaner - extract_terminal"
```

---

## Task 8: Cleaner — `clean_all`

**Files:**
- Modify: `gamefydb/cleaner.py`
- Modify: `tests/test_cleaner.py`

`clean_all` applies per-file normalizations. Output column names after cleaning:

- **cash**: `cashier, date (datetime), income_expense, payment_method, transaction_type, amount_tnd (float), comment, terminal (str|None)`
- **sessions**: `cashier, terminal, session_type, is_free_time (bool), is_paused (bool), duration_minutes (int), order_transfer_tnd, usb_data_tnd, usage_tnd, discount_tnd, total_amount_tnd (float)`
- **stock**: `cashier, date (datetime), item_name, category, in_out, quantity (int), unit_price_tnd (float), total_amount_tnd (float), comment, terminal (str|None)`
- **members**: `member_id (int), username, firstname, lastname, duration_minutes (int), usage_tnd, orders_transfer_tnd, usb_data_tnd, total_amount_tnd (float)`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_cleaner.py`:

```python
import numpy as np
from gamefydb.cleaner import clean_all


def make_raw_for_clean_all():
    cash = pd.DataFrame([
        {'cashier': 'taktek', 'date': '23.03.2026 03:23:54',
         'income_expense': 'Income', 'payment_method': 'Cash',
         'transaction_type': 'Order Incomes', 'amount': '27,50 TND',
         'comment': '(PS5 (1))'},
        {'cashier': 'youssef', 'date': '22.03.2026 17:41:47',
         'income_expense': 'Income', 'payment_method': 'Cash',
         'transaction_type': 'Member Transactions', 'amount': '30,00 TND',
         'comment': 'Money deposited to member'},
    ])
    sessions = pd.DataFrame([
        {'cashier': 'taktek', 'terminal': 'GAMEFY04', 'session_type': 'Member',
         'free_time': np.nan, 'paused': np.nan, 'duration': '1 h 29 min',
         'order_transfer': '0,00 TND', 'usb_data': '0,00 TND',
         'usage': '11,87 TND', 'discount': '0,00 TND', 'total_amount': '11,87 TND'},
        {'cashier': 'taktek', 'terminal': 'PS5 (2)', 'session_type': 'Free',
         'free_time': 'x', 'paused': np.nan, 'duration': '1 h 45 min',
         'order_transfer': '0,00 TND', 'usb_data': '0,00 TND',
         'usage': '0,00 TND', 'discount': '0,00 TND', 'total_amount': '0,00 TND'},
    ])
    stock = pd.DataFrame([
        {'cashier': 'taktek', 'date': '23.03.2026 03:23:54',
         'item_name': 'Soda', 'category': 'Drinks', 'in_out': 'Out',
         'quantity': '4', 'unit_price': '2,00 TND',
         'total_amount': '8,00 TND', 'comment': '(PS5 (1))'},
    ])
    members = pd.DataFrame([
        {'member_id': '35', 'username': 'mhmd', 'firstname': 'MOHAMED',
         'lastname': 'LOUATI', 'duration': '223 h 26 min',
         'usage': '1\u202f745,44 TND', 'orders_transfer': '0,00 TND',
         'usb_data': '0,00 TND', 'total_amount': '1\u202f745,44 TND'},
    ])
    return {'cash': cash, 'sessions': sessions, 'stock': stock, 'members': members}


def test_clean_cash_date_is_datetime():
    result = clean_all(make_raw_for_clean_all())
    assert pd.api.types.is_datetime64_any_dtype(result['cash']['date'])


def test_clean_cash_amount_is_float():
    result = clean_all(make_raw_for_clean_all())
    assert result['cash']['amount_tnd'].iloc[0] == 27.50


def test_clean_cash_terminal_extracted():
    result = clean_all(make_raw_for_clean_all())
    assert result['cash']['terminal'].iloc[0] == 'PS5 (1)'
    assert pd.isna(result['cash']['terminal'].iloc[1])


def test_clean_sessions_duration_minutes():
    result = clean_all(make_raw_for_clean_all())
    assert result['sessions']['duration_minutes'].iloc[0] == 89
    assert result['sessions']['duration_minutes'].iloc[1] == 105


def test_clean_sessions_bool_free_time():
    result = clean_all(make_raw_for_clean_all())
    assert result['sessions']['is_free_time'].iloc[0] == False
    assert result['sessions']['is_free_time'].iloc[1] == True


def test_clean_sessions_amounts_are_float():
    result = clean_all(make_raw_for_clean_all())
    assert result['sessions']['usage_tnd'].iloc[0] == 11.87


def test_clean_stock_quantity_is_int():
    result = clean_all(make_raw_for_clean_all())
    assert result['stock']['quantity'].iloc[0] == 4
    assert pd.api.types.is_integer_dtype(result['stock']['quantity'])


def test_clean_members_duration_minutes():
    result = clean_all(make_raw_for_clean_all())
    assert result['members']['duration_minutes'].iloc[0] == 13406


def test_clean_members_amount_with_narrow_space():
    result = clean_all(make_raw_for_clean_all())
    assert result['members']['total_amount_tnd'].iloc[0] == 1745.44


def test_clean_members_id_is_int():
    result = clean_all(make_raw_for_clean_all())
    assert result['members']['member_id'].iloc[0] == 35
```

Add the missing `import pandas as pd` at the top of `tests/test_cleaner.py`:

```python
import pandas as pd
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_cleaner.py::test_clean_cash_date_is_datetime -v`
Expected: `ImportError: cannot import name 'clean_all'`

- [ ] **Step 3: Implement `clean_all` in `gamefydb/cleaner.py`**

Append to `gamefydb/cleaner.py`:

```python
def _is_truthy(value) -> bool:
    """Return True if value is a non-empty, non-NaN string."""
    if value is None:
        return False
    if isinstance(value, float) and pd.isna(value):
        return False
    return str(value).strip() != ''


def _clean_cash(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out['date'] = pd.to_datetime(out['date'], format='%d.%m.%Y %H:%M:%S')
    out['amount_tnd'] = out['amount'].apply(parse_amount)
    out['terminal'] = out['comment'].apply(extract_terminal)
    return out.drop(columns=['amount'])


def _clean_sessions(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out['duration_minutes'] = out['duration'].apply(parse_duration)
    out['is_free_time'] = out['free_time'].apply(_is_truthy)
    out['is_paused'] = out['paused'].apply(_is_truthy)
    for src, dst in [
        ('order_transfer', 'order_transfer_tnd'),
        ('usb_data',       'usb_data_tnd'),
        ('usage',          'usage_tnd'),
        ('discount',       'discount_tnd'),
        ('total_amount',   'total_amount_tnd'),
    ]:
        out[dst] = out[src].apply(parse_amount)
    return out.drop(columns=[
        'duration', 'free_time', 'paused',
        'order_transfer', 'usb_data', 'usage', 'discount', 'total_amount',
    ])


def _clean_stock(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out['date'] = pd.to_datetime(out['date'], format='%d.%m.%Y %H:%M:%S')
    out['quantity'] = pd.to_numeric(out['quantity']).astype(int)
    out['unit_price_tnd'] = out['unit_price'].apply(parse_amount)
    out['total_amount_tnd'] = out['total_amount'].apply(parse_amount)
    out['terminal'] = out['comment'].apply(extract_terminal)
    return out.drop(columns=['unit_price', 'total_amount'])


def _clean_members(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out['member_id'] = pd.to_numeric(out['member_id']).astype(int)
    out['duration_minutes'] = out['duration'].apply(parse_duration)
    out['usage_tnd'] = out['usage'].apply(parse_amount)
    out['orders_transfer_tnd'] = out['orders_transfer'].apply(parse_amount)
    out['usb_data_tnd'] = out['usb_data'].apply(parse_amount)
    out['total_amount_tnd'] = out['total_amount'].apply(parse_amount)
    return out.drop(columns=['duration', 'usage', 'orders_transfer', 'usb_data', 'total_amount'])


def clean_all(raw: dict) -> dict:
    """Apply per-file type normalization to all ingested DataFrames.

    Args:
        raw: Output of ingest_all — {'cash': df, 'sessions': df, ...}

    Returns:
        Same keys, with typed and normalized columns.
    """
    return {
        'cash':     _clean_cash(raw['cash']),
        'sessions': _clean_sessions(raw['sessions']),
        'stock':    _clean_stock(raw['stock']),
        'members':  _clean_members(raw['members']),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_cleaner.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add gamefydb/cleaner.py tests/test_cleaner.py
git commit -m "feat: cleaner - clean_all with per-file normalization"
```

---

## Task 9: Transformer — dimension tables

**Files:**
- Create: `gamefydb/transformer.py`
- Create: `tests/test_transformer.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_transformer.py`:

```python
import pandas as pd
import pytest
from gamefydb.transformer import build_dims


def make_cleaned():
    cash = pd.DataFrame([
        {'cashier': 'taktek', 'date': pd.Timestamp('2026-03-23 03:23:54'),
         'income_expense': 'Income', 'payment_method': 'Cash',
         'transaction_type': 'Order Incomes', 'amount_tnd': 27.50,
         'comment': '(PS5 (1))', 'terminal': 'PS5 (1)'},
        {'cashier': 'youssef', 'date': pd.Timestamp('2026-03-22 17:41:47'),
         'income_expense': 'Income', 'payment_method': 'Cash',
         'transaction_type': 'Member Transactions', 'amount_tnd': 30.00,
         'comment': 'Money deposited', 'terminal': None},
    ])
    sessions = pd.DataFrame([
        {'cashier': 'taktek', 'terminal': 'GAMEFY04', 'session_type': 'Member',
         'is_free_time': False, 'is_paused': False, 'duration_minutes': 89,
         'order_transfer_tnd': 0.0, 'usb_data_tnd': 0.0, 'usage_tnd': 11.87,
         'discount_tnd': 0.0, 'total_amount_tnd': 11.87},
        {'cashier': 'taktek', 'terminal': 'PS5 (1)', 'session_type': 'Free',
         'is_free_time': True, 'is_paused': False, 'duration_minutes': 105,
         'order_transfer_tnd': 0.0, 'usb_data_tnd': 0.0, 'usage_tnd': 0.0,
         'discount_tnd': 0.0, 'total_amount_tnd': 0.0},
    ])
    stock = pd.DataFrame([
        {'cashier': 'taktek', 'date': pd.Timestamp('2026-03-23 03:23:54'),
         'item_name': 'Soda', 'category': 'Drinks', 'in_out': 'Out',
         'quantity': 4, 'unit_price_tnd': 2.0, 'total_amount_tnd': 8.0,
         'comment': '(PS5 (1))', 'terminal': 'PS5 (1)'},
    ])
    members = pd.DataFrame([
        {'member_id': 35, 'username': 'mhmd', 'firstname': 'MOHAMED',
         'lastname': 'LOUATI', 'duration_minutes': 13406, 'usage_tnd': 1745.44,
         'orders_transfer_tnd': 0.0, 'usb_data_tnd': 0.0, 'total_amount_tnd': 1745.44},
        {'member_id': 64, 'username': 'zinox', 'firstname': 'Helmi',
         'lastname': 'Chermiti', 'duration_minutes': 7735, 'usage_tnd': 919.72,
         'orders_transfer_tnd': 0.0, 'usb_data_tnd': 0.0, 'total_amount_tnd': 919.72},
    ])
    return {'cash': cash, 'sessions': sessions, 'stock': stock, 'members': members}


def test_dim_cashier_columns():
    dims = build_dims(make_cleaned())
    assert list(dims['dim_cashier'].columns) == ['cashier_id', 'cashier_name']


def test_dim_cashier_unique_names():
    dims = build_dims(make_cleaned())
    # taktek + youssef appear across cash/sessions/stock — 2 unique
    assert set(dims['dim_cashier']['cashier_name']) == {'taktek', 'youssef'}


def test_dim_cashier_sequential_ids():
    dims = build_dims(make_cleaned())
    assert sorted(dims['dim_cashier']['cashier_id'].tolist()) == [1, 2]


def test_dim_terminal_columns():
    dims = build_dims(make_cleaned())
    assert list(dims['dim_terminal'].columns) == ['terminal_id', 'terminal_name', 'terminal_type']


def test_dim_terminal_union_across_files():
    dims = build_dims(make_cleaned())
    # GAMEFY04 and PS5 (1) from sessions; PS5 (1) also in cash/stock (deduplicated)
    assert set(dims['dim_terminal']['terminal_name']) == {'GAMEFY04', 'PS5 (1)'}


def test_dim_terminal_type_classification():
    dims = build_dims(make_cleaned())
    types = dict(zip(dims['dim_terminal']['terminal_name'], dims['dim_terminal']['terminal_type']))
    assert types['GAMEFY04'] == 'Computer'
    assert types['PS5 (1)'] == 'PlayStation'


def test_dim_item_columns():
    dims = build_dims(make_cleaned())
    assert list(dims['dim_item'].columns) == ['item_id', 'item_name', 'category']


def test_dim_item_from_stock():
    dims = build_dims(make_cleaned())
    assert dims['dim_item']['item_name'].iloc[0] == 'Soda'
    assert dims['dim_item']['category'].iloc[0] == 'Drinks'


def test_dim_member_columns():
    dims = build_dims(make_cleaned())
    assert list(dims['dim_member'].columns) == ['member_id', 'username', 'firstname', 'lastname']


def test_dim_member_uses_source_ids():
    dims = build_dims(make_cleaned())
    assert set(dims['dim_member']['member_id']) == {35, 64}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_transformer.py -v`
Expected: `ImportError: cannot import name 'build_dims'`

- [ ] **Step 3: Implement `build_dims` in `gamefydb/transformer.py`**

Create `gamefydb/transformer.py`:

```python
import pandas as pd


def _classify_terminal(name: str) -> str:
    n = str(name).upper()
    if 'VIP' in n:
        return 'VIP'
    if n.startswith('PS'):
        return 'PlayStation'
    if n.startswith('GAMEFY'):
        return 'Computer'
    return 'Other'


def build_dims(cleaned: dict) -> dict:
    """Build all four dimension tables from cleaned DataFrames.

    Returns:
        {'dim_cashier': df, 'dim_terminal': df, 'dim_item': df, 'dim_member': df}
    """
    cash = cleaned['cash']
    sessions = cleaned['sessions']
    stock = cleaned['stock']
    members = cleaned['members']

    # dim_cashier — union of cashier names across all transactional files
    all_cashiers = pd.concat([cash['cashier'], sessions['cashier'], stock['cashier']])
    cashier_names = sorted(set(
        str(n).strip() for n in all_cashiers.dropna() if str(n).strip()
    ))
    dim_cashier = pd.DataFrame({
        'cashier_id': range(1, len(cashier_names) + 1),
        'cashier_name': cashier_names,
    })

    # dim_terminal — union from sessions + cash.terminal + stock.terminal (nullable)
    terminal_sources = [sessions['terminal']]
    if 'terminal' in cash.columns:
        terminal_sources.append(cash['terminal'].dropna())
    if 'terminal' in stock.columns:
        terminal_sources.append(stock['terminal'].dropna())
    terminal_names = sorted(set(
        str(n).strip() for n in pd.concat(terminal_sources).dropna() if str(n).strip()
    ))
    dim_terminal = pd.DataFrame({
        'terminal_id': range(1, len(terminal_names) + 1),
        'terminal_name': terminal_names,
        'terminal_type': [_classify_terminal(n) for n in terminal_names],
    })

    # dim_item — unique (item_name, category) pairs from stock
    items = (
        stock[['item_name', 'category']]
        .drop_duplicates()
        .sort_values(['category', 'item_name'])
        .reset_index(drop=True)
    )
    dim_item = pd.DataFrame({
        'item_id': range(1, len(items) + 1),
        'item_name': items['item_name'].values,
        'category': items['category'].values,
    })

    # dim_member — descriptive columns only (member_id is the source PK)
    dim_member = (
        members[['member_id', 'username', 'firstname', 'lastname']]
        .copy()
        .reset_index(drop=True)
    )

    return {
        'dim_cashier': dim_cashier,
        'dim_terminal': dim_terminal,
        'dim_item': dim_item,
        'dim_member': dim_member,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_transformer.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add gamefydb/transformer.py tests/test_transformer.py
git commit -m "feat: transformer - build dimension tables"
```

---

## Task 10: Transformer — fact tables

**Files:**
- Modify: `gamefydb/transformer.py`
- Modify: `tests/test_transformer.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_transformer.py`:

```python
from gamefydb.transformer import build_facts


def test_fact_cash_columns():
    dims = build_dims(make_cleaned())
    facts = build_facts(make_cleaned(), dims)
    assert list(facts['fact_cash_transactions'].columns) == [
        'cashier_id', 'transaction_datetime', 'income_expense',
        'payment_method', 'transaction_type', 'amount_tnd', 'terminal_id',
    ]


def test_fact_cash_cashier_fk_resolved():
    cleaned = make_cleaned()
    dims = build_dims(cleaned)
    facts = build_facts(cleaned, dims)
    taktek_id = dims['dim_cashier'].loc[
        dims['dim_cashier']['cashier_name'] == 'taktek', 'cashier_id'
    ].iloc[0]
    assert facts['fact_cash_transactions']['cashier_id'].iloc[0] == taktek_id


def test_fact_cash_terminal_id_nullable():
    cleaned = make_cleaned()
    dims = build_dims(cleaned)
    facts = build_facts(cleaned, dims)
    # Row 1 has no terminal (comment = 'Money deposited')
    assert pd.isna(facts['fact_cash_transactions']['terminal_id'].iloc[1])


def test_fact_sessions_columns():
    dims = build_dims(make_cleaned())
    facts = build_facts(make_cleaned(), dims)
    assert list(facts['fact_sessions'].columns) == [
        'cashier_id', 'terminal_id', 'session_type', 'is_free_time', 'is_paused',
        'duration_minutes', 'order_transfer_tnd', 'usb_data_tnd', 'usage_tnd',
        'discount_tnd', 'total_amount_tnd',
    ]


def test_fact_sessions_terminal_fk_resolved():
    cleaned = make_cleaned()
    dims = build_dims(cleaned)
    facts = build_facts(cleaned, dims)
    gamefy04_id = dims['dim_terminal'].loc[
        dims['dim_terminal']['terminal_name'] == 'GAMEFY04', 'terminal_id'
    ].iloc[0]
    assert facts['fact_sessions']['terminal_id'].iloc[0] == gamefy04_id


def test_fact_stock_columns():
    dims = build_dims(make_cleaned())
    facts = build_facts(make_cleaned(), dims)
    assert list(facts['fact_stock_movements'].columns) == [
        'cashier_id', 'movement_datetime', 'item_id', 'in_out', 'quantity',
        'unit_price_tnd', 'total_amount_tnd', 'terminal_id',
    ]


def test_fact_stock_item_fk_resolved():
    cleaned = make_cleaned()
    dims = build_dims(cleaned)
    facts = build_facts(cleaned, dims)
    soda_id = dims['dim_item'].loc[
        dims['dim_item']['item_name'] == 'Soda', 'item_id'
    ].iloc[0]
    assert facts['fact_stock_movements']['item_id'].iloc[0] == soda_id


def test_fact_member_stats_columns():
    dims = build_dims(make_cleaned())
    facts = build_facts(make_cleaned(), dims)
    assert list(facts['fact_member_stats'].columns) == [
        'member_id', 'duration_minutes', 'usage_tnd',
        'orders_transfer_tnd', 'usb_data_tnd', 'total_amount_tnd',
    ]


def test_fact_member_stats_ids():
    cleaned = make_cleaned()
    dims = build_dims(cleaned)
    facts = build_facts(cleaned, dims)
    assert set(facts['fact_member_stats']['member_id']) == {35, 64}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_transformer.py::test_fact_cash_columns -v`
Expected: `ImportError: cannot import name 'build_facts'`

- [ ] **Step 3: Implement `build_facts` in `gamefydb/transformer.py`**

Append to `gamefydb/transformer.py`:

```python
def _resolve_fk(df: pd.DataFrame, src_col: str,
                dim: pd.DataFrame, dim_name_col: str, dim_id_col: str) -> pd.Series:
    """Map natural key column → surrogate FK using the dimension table.

    Unresolved values (e.g. None terminals) become NaN (nullable float).
    """
    mapping = dict(zip(dim[dim_name_col], dim[dim_id_col]))
    return df[src_col].map(mapping)


def build_facts(cleaned: dict, dims: dict) -> dict:
    """Build all four fact tables, resolving FK columns via dimension tables.

    Args:
        cleaned: Output of clean_all.
        dims: Output of build_dims.

    Returns:
        {'fact_cash_transactions': df, 'fact_sessions': df,
         'fact_stock_movements': df, 'fact_member_stats': df}
    """
    cash = cleaned['cash']
    sessions = cleaned['sessions']
    stock = cleaned['stock']
    members = cleaned['members']
    dim_cashier = dims['dim_cashier']
    dim_terminal = dims['dim_terminal']
    dim_item = dims['dim_item']

    fact_cash = pd.DataFrame({
        'cashier_id':           _resolve_fk(cash, 'cashier', dim_cashier, 'cashier_name', 'cashier_id'),
        'transaction_datetime': cash['date'],
        'income_expense':       cash['income_expense'],
        'payment_method':       cash['payment_method'],
        'transaction_type':     cash['transaction_type'],
        'amount_tnd':           cash['amount_tnd'],
        'terminal_id':          _resolve_fk(cash, 'terminal', dim_terminal, 'terminal_name', 'terminal_id'),
    }).reset_index(drop=True)

    fact_sessions = pd.DataFrame({
        'cashier_id':        _resolve_fk(sessions, 'cashier', dim_cashier, 'cashier_name', 'cashier_id'),
        'terminal_id':       _resolve_fk(sessions, 'terminal', dim_terminal, 'terminal_name', 'terminal_id'),
        'session_type':      sessions['session_type'],
        'is_free_time':      sessions['is_free_time'],
        'is_paused':         sessions['is_paused'],
        'duration_minutes':  sessions['duration_minutes'],
        'order_transfer_tnd': sessions['order_transfer_tnd'],
        'usb_data_tnd':      sessions['usb_data_tnd'],
        'usage_tnd':         sessions['usage_tnd'],
        'discount_tnd':      sessions['discount_tnd'],
        'total_amount_tnd':  sessions['total_amount_tnd'],
    }).reset_index(drop=True)

    fact_stock = pd.DataFrame({
        'cashier_id':        _resolve_fk(stock, 'cashier', dim_cashier, 'cashier_name', 'cashier_id'),
        'movement_datetime': stock['date'],
        'item_id':           _resolve_fk(stock, 'item_name', dim_item, 'item_name', 'item_id'),
        'in_out':            stock['in_out'],
        'quantity':          stock['quantity'],
        'unit_price_tnd':    stock['unit_price_tnd'],
        'total_amount_tnd':  stock['total_amount_tnd'],
        'terminal_id':       _resolve_fk(stock, 'terminal', dim_terminal, 'terminal_name', 'terminal_id'),
    }).reset_index(drop=True)

    fact_members = members[[
        'member_id', 'duration_minutes', 'usage_tnd',
        'orders_transfer_tnd', 'usb_data_tnd', 'total_amount_tnd',
    ]].copy().reset_index(drop=True)

    return {
        'fact_cash_transactions': fact_cash,
        'fact_sessions':          fact_sessions,
        'fact_stock_movements':   fact_stock,
        'fact_member_stats':      fact_members,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_transformer.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add gamefydb/transformer.py tests/test_transformer.py
git commit -m "feat: transformer - build fact tables with FK resolution"
```

---

## Task 11: Transformer — `transform`

**Files:**
- Modify: `gamefydb/transformer.py`
- Modify: `tests/test_transformer.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_transformer.py`:

```python
from gamefydb.transformer import transform


def test_transform_returns_all_eight_tables():
    result = transform(make_cleaned())
    expected = {
        'dim_cashier', 'dim_terminal', 'dim_item', 'dim_member',
        'fact_cash_transactions', 'fact_sessions',
        'fact_stock_movements', 'fact_member_stats',
    }
    assert set(result.keys()) == expected


def test_transform_all_values_are_dataframes():
    for name, val in transform(make_cleaned()).items():
        assert isinstance(val, pd.DataFrame), f"{name} is not a DataFrame"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_transformer.py::test_transform_returns_all_eight_tables -v`
Expected: `ImportError: cannot import name 'transform'`

- [ ] **Step 3: Add `transform` to `gamefydb/transformer.py`**

Append to `gamefydb/transformer.py`:

```python
def transform(cleaned: dict) -> dict:
    """Build the full star schema from cleaned DataFrames.

    Returns:
        Dict of all 8 tables: 4 dims + 4 facts.
    """
    dims = build_dims(cleaned)
    facts = build_facts(cleaned, dims)
    return {**dims, **facts}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_transformer.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add gamefydb/transformer.py tests/test_transformer.py
git commit -m "feat: transformer - transform() entry point"
```

---

## Task 12: Writer — CSV output

**Files:**
- Create: `gamefydb/writer.py`
- Create: `tests/test_writer.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_writer.py`:

```python
import os
import shutil
import pandas as pd
import pytest
from gamefydb.writer import write_all


@pytest.fixture
def schema():
    return {
        'dim_cashier':  pd.DataFrame({'cashier_id': [1, 2], 'cashier_name': ['taktek', 'youssef']}),
        'dim_terminal': pd.DataFrame({'terminal_id': [1], 'terminal_name': ['GAMEFY01'], 'terminal_type': ['Computer']}),
        'dim_item':     pd.DataFrame({'item_id': [1], 'item_name': ['Soda'], 'category': ['Drinks']}),
        'dim_member':   pd.DataFrame({'member_id': [35], 'username': ['mhmd'], 'firstname': ['MOHAMED'], 'lastname': ['LOUATI']}),
        'fact_cash_transactions': pd.DataFrame({'cashier_id': [1], 'transaction_datetime': [pd.Timestamp('2026-03-23')], 'amount_tnd': [27.50]}),
        'fact_sessions':          pd.DataFrame({'cashier_id': [1], 'terminal_id': [1], 'duration_minutes': [89]}),
        'fact_stock_movements':   pd.DataFrame({'cashier_id': [1], 'item_id': [1], 'quantity': [4]}),
        'fact_member_stats':      pd.DataFrame({'member_id': [35], 'total_amount_tnd': [1745.44]}),
    }


@pytest.fixture
def output_dir(tmp_path):
    return str(tmp_path / 'output')


def test_write_csv_creates_dims_directory(schema, output_dir):
    write_all(schema, output_dir)
    assert os.path.isdir(os.path.join(output_dir, 'dims'))


def test_write_csv_creates_facts_directory(schema, output_dir):
    write_all(schema, output_dir)
    assert os.path.isdir(os.path.join(output_dir, 'facts'))


def test_write_csv_all_files_exist(schema, output_dir):
    write_all(schema, output_dir)
    for name in ['dim_cashier', 'dim_terminal', 'dim_item', 'dim_member']:
        assert os.path.isfile(os.path.join(output_dir, 'dims', f'{name}.csv')), f"Missing {name}.csv"
    for name in ['fact_cash_transactions', 'fact_sessions', 'fact_stock_movements', 'fact_member_stats']:
        assert os.path.isfile(os.path.join(output_dir, 'facts', f'{name}.csv')), f"Missing {name}.csv"


def test_write_csv_content(schema, output_dir):
    write_all(schema, output_dir)
    df = pd.read_csv(os.path.join(output_dir, 'dims', 'dim_cashier.csv'))
    assert list(df.columns) == ['cashier_id', 'cashier_name']
    assert df['cashier_name'].tolist() == ['taktek', 'youssef']
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_writer.py -v`
Expected: `ImportError: cannot import name 'write_all'`

- [ ] **Step 3: Implement `write_all` (CSV only) in `gamefydb/writer.py`**

```python
import os
import pandas as pd


def write_all(schema: dict, output_dir: str, fmt: str = 'csv') -> None:
    """Write all star-schema tables to output_dir.

    Args:
        schema: Output of transformer.transform() — {table_name: DataFrame}.
        output_dir: Root output directory (created if absent).
        fmt: 'csv' (default) writes dims/ and facts/ subdirectories.
             'excel' writes a single gamefydb.xlsx workbook.
    """
    dims_dir = os.path.join(output_dir, 'dims')
    facts_dir = os.path.join(output_dir, 'facts')
    os.makedirs(dims_dir, exist_ok=True)
    os.makedirs(facts_dir, exist_ok=True)

    if fmt == 'excel':
        _write_excel(schema, output_dir)
        return

    for name, df in schema.items():
        subdir = dims_dir if name.startswith('dim_') else facts_dir
        df.to_csv(os.path.join(subdir, f'{name}.csv'), index=False)


def _write_excel(schema: dict, output_dir: str) -> None:
    path = os.path.join(output_dir, 'gamefydb.xlsx')
    with pd.ExcelWriter(path, engine='openpyxl') as writer:
        for name, df in schema.items():
            df.to_excel(writer, sheet_name=name, index=False)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_writer.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add gamefydb/writer.py tests/test_writer.py
git commit -m "feat: writer - CSV output"
```

---

## Task 13: Writer — Excel output tests

**Files:**
- Modify: `tests/test_writer.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_writer.py`:

```python
def test_write_excel_creates_single_file(schema, output_dir):
    write_all(schema, output_dir, fmt='excel')
    assert os.path.isfile(os.path.join(output_dir, 'gamefydb.xlsx'))


def test_write_excel_has_all_sheets(schema, output_dir):
    write_all(schema, output_dir, fmt='excel')
    xl = pd.ExcelFile(os.path.join(output_dir, 'gamefydb.xlsx'))
    assert set(xl.sheet_names) == set(schema.keys())


def test_write_excel_sheet_content(schema, output_dir):
    write_all(schema, output_dir, fmt='excel')
    df = pd.read_excel(os.path.join(output_dir, 'gamefydb.xlsx'), sheet_name='dim_cashier')
    assert df['cashier_name'].tolist() == ['taktek', 'youssef']
```

- [ ] **Step 2: Run tests — they should PASS (Excel was implemented in Task 12)**

Run: `pytest tests/test_writer.py -v`
Expected: All PASS (including new Excel tests — `_write_excel` was already implemented)

- [ ] **Step 3: Commit**

```bash
git add tests/test_writer.py
git commit -m "test: writer - add Excel output coverage"
```

---

## Task 14: CLI — `run.py`

**Files:**
- Create: `run.py`
- Create: `tests/test_run.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_run.py`:

```python
import os
import subprocess
import sys

PYTHON = sys.executable
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_run_help():
    result = subprocess.run(
        [PYTHON, 'run.py', '--help'],
        capture_output=True, text=True, cwd=ROOT,
    )
    assert result.returncode == 0
    assert '--format' in result.stdout
    assert '--input' in result.stdout
    assert '--output' in result.stdout


def test_run_csv_output(tmp_path):
    result = subprocess.run(
        [PYTHON, 'run.py', '--input', 'excel', '--output', str(tmp_path)],
        capture_output=True, text=True, cwd=ROOT,
    )
    assert result.returncode == 0, result.stderr
    assert os.path.isfile(os.path.join(tmp_path, 'dims', 'dim_cashier.csv'))
    assert os.path.isfile(os.path.join(tmp_path, 'facts', 'fact_cash_transactions.csv'))


def test_run_excel_output(tmp_path):
    result = subprocess.run(
        [PYTHON, 'run.py', '--input', 'excel', '--output', str(tmp_path), '--format', 'excel'],
        capture_output=True, text=True, cwd=ROOT,
    )
    assert result.returncode == 0, result.stderr
    assert os.path.isfile(os.path.join(tmp_path, 'gamefydb.xlsx'))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_run.py::test_run_help -v`
Expected: FAIL — `run.py` does not exist yet

- [ ] **Step 3: Create `run.py`**

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
    args = parser.parse_args()

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


if __name__ == '__main__':
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_run.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add run.py tests/test_run.py
git commit -m "feat: run.py CLI entry point"
```

---

## Task 15: Full suite and end-to-end verification

- [ ] **Step 1: Run the full test suite**

Run: `pytest -v`
Expected: All tests PASS with no failures or errors.

- [ ] **Step 2: Run the pipeline end-to-end**

Run: `python run.py --input excel --output output`

Expected output:
```
Ingesting from excel...
Cleaning...
Transforming to star schema...
Writing csv output to output...
Done.
  dim_cashier: 2 rows
  dim_terminal: ~12 rows
  dim_item: ~10 rows
  dim_member: ~113 rows
  fact_cash_transactions: ~4400 rows
  fact_sessions: ~6200 rows
  fact_stock_movements: ~2000 rows
  fact_member_stats: ~113 rows
```

- [ ] **Step 3: Spot-check key output files**

Run:
```bash
head -3 output/dims/dim_cashier.csv
head -3 output/facts/fact_cash_transactions.csv
head -3 output/facts/fact_sessions.csv
```

Verify:
- `dim_cashier.csv`: headers `cashier_id,cashier_name`, values like `1,taktek`
- `fact_cash_transactions.csv`: `amount_tnd` values are floats (e.g. `27.5`), not `"27,50 TND"`
- `fact_sessions.csv`: `duration_minutes` values are integers, no `"1 h 29 min"` strings

- [ ] **Step 4: Final commit**

```bash
git add output/.gitkeep 2>/dev/null || true
git commit -m "chore: verified pipeline end-to-end — all 8 tables output correctly"
```
