# GamefyDB ETL Pipeline — Design Spec
**Date:** 2026-04-01

## Overview

A Python ETL pipeline that ingests four raw `.xls` report files exported from a gaming center management system, normalizes and cleans the data, and outputs a star-schema-ready set of CSV (or Excel) files suitable for loading into a data warehouse.

---

## Source Files

| File | Rows | Pages | Description |
|---|---|---|---|
| `Cash DATA 01-09-2025.xls` | 4,604 | 115 | Cash transactions (income/expense) |
| `DATA session reports 01-09-2025.xls` | 7,254 | 181 | Per-terminal gaming sessions |
| `Stock DATA 01-09-2025.xls` | 2,370 | 60 | Stock movements (items sold/added) |
| `memeber DATA 01-09-2025.xls` | 118 | 3 | Member usage statistics |

All files share the same structural pattern: title row, report date row, blank rows, column headers on row 4, data rows interleaved with page-break artifacts, and a footer section with aggregate summaries.

---

## Project Structure

```
GamefyDB/
├── gamefydb/
│   ├── __init__.py
│   ├── ingestor.py       # Read .xls, strip page breaks + footers → raw DataFrames
│   ├── cleaner.py        # Normalize types: amounts, dates, durations, strings
│   ├── transformer.py    # Build star schema (fact + dim tables)
│   └── writer.py         # Write output as CSV or clean Excel
├── output/
│   ├── dims/             # dim_*.csv
│   └── facts/            # fact_*.csv
├── run.py                # Entry point
└── requirements.txt      # pandas, xlrd, openpyxl
```

---

## Stage 1: Ingestor (`ingestor.py`)

Reads each `.xls` file and returns a clean `DataFrame` with correct column names and only real data rows.

**Artifact rows stripped:**

| Row type | Detection method | Action |
|---|---|---|
| Title row | Row 0, col 0 = report title string | Drop |
| Report date row | Row 1, contains `DD/MM/YYYY` date string | Drop |
| Blank rows | All cells empty | Drop |
| Page marker rows | Any cell matches `Page \d+/\d+` | Drop |
| Repeated header rows | Row values match known column header set | Drop |
| Footer rows | All rows after last real data row (Filter Status, Report Result, totals, print timestamp) | Drop |
| Inflated columns | All-NaN columns from merged-cell inflation | Drop |

**Header detection:** Row 4 in every file contains the real column headers. The ingestor reads with `header=None`, uses row 4 as column names, then drops all artifact rows.

---

## Stage 2: Cleaner (`cleaner.py`)

Per-column normalization applied to the output of the ingestor.

| Data type | Raw example | Clean output | Method |
|---|---|---|---|
| Amount | `1 745,44 TND` | `1745.44` (float) | Strip ` TND`, remove `\u202f`, replace `,` → `.`, cast float |
| Datetime | `23.03.2026 03:23:54` | `2026-03-23 03:23:54` (datetime) | `pd.to_datetime(format="%d.%m.%Y %H:%M:%S")` |
| Duration | `1 h 29 min` / `30 min` | `89` (int minutes) | Regex extract hours + minutes, compute `h*60 + m` |
| Terminal ID | `(GAMEFY01)` / `(PS5 (1))` | `GAMEFY01` / `PS5 (1)` | Regex: content inside outermost parens from Comment column |
| Boolean | Non-empty / NaN | `True` / `False` | Applied to Free Time and Paused columns in sessions |
| Strings | Cashier names, item names | Whitespace-normalized | `.strip()`, collapse internal whitespace |

**Known limitation:** The session report export has no per-row timestamp. Individual session dates cannot be recovered; only the report date range (`01.09.2025 – 24.03.2026`) is known.

---

## Stage 3: Transformer (`transformer.py`)

Builds the star schema from cleaned DataFrames. Surrogate keys for dimension tables are sequential integers starting at 1. FK columns in fact tables are resolved by joining on the natural key.

Dimensions are built by collecting unique values **across all source files** that reference them:
- `dim_cashier` — union of cashier names from Cash, Sessions, and Stock files
- `dim_terminal` — union of terminal names from Sessions (Terminal column) and Cash/Stock (extracted from Comment)
- `dim_item` — item names and categories from Stock only
- `dim_member` — from Member file only

### Dimension Tables

**`dim_cashier`**
| Column | Type | Notes |
|---|---|---|
| cashier_id | int | Surrogate PK |
| cashier_name | str | e.g. `taktek`, `youssef` |

**`dim_terminal`**
| Column | Type | Notes |
|---|---|---|
| terminal_id | int | Surrogate PK |
| terminal_name | str | e.g. `GAMEFY01`, `PS5 (1)`, `GAMEFY-VIP` |
| terminal_type | str | Derived: `Computer` / `PlayStation` / `VIP` |

**`dim_item`**
| Column | Type | Notes |
|---|---|---|
| item_id | int | Surrogate PK |
| item_name | str | e.g. `Soda`, `Schweppes`, `Redbull/Shark` |
| category | str | e.g. `Drinks`, `Other` |

**`dim_member`**
| Column | Type | Notes |
|---|---|---|
| member_id | int | Source PK (from file) |
| username | str | e.g. `mhmd`, `zinox` |
| firstname | str | |
| lastname | str | |

### Fact Tables

**`fact_cash_transactions`**
| Column | Type | Notes |
|---|---|---|
| cashier_id | int | FK → dim_cashier |
| transaction_datetime | datetime | |
| income_expense | str | `Income` / `Expense` |
| payment_method | str | `Cash` / `Credit Card` |
| transaction_type | str | `Computer Incomes`, `Order Incomes`, etc. |
| amount_tnd | float | |
| terminal_id | int | FK → dim_terminal, extracted from Comment; **nullable** (not all transactions have a terminal reference) |

**`fact_sessions`**
| Column | Type | Notes |
|---|---|---|
| cashier_id | int | FK → dim_cashier |
| terminal_id | int | FK → dim_terminal |
| session_type | str | `Standard`, `Member`, `Free`, `Administrator` |
| is_free_time | bool | |
| is_paused | bool | |
| duration_minutes | int | |
| order_transfer_tnd | float | |
| usb_data_tnd | float | |
| usage_tnd | float | |
| discount_tnd | float | |
| total_amount_tnd | float | |

**`fact_stock_movements`**
| Column | Type | Notes |
|---|---|---|
| cashier_id | int | FK → dim_cashier |
| movement_datetime | datetime | |
| item_id | int | FK → dim_item |
| in_out | str | `In` / `Out` |
| quantity | int | |
| unit_price_tnd | float | |
| total_amount_tnd | float | |
| terminal_id | int | FK → dim_terminal, extracted from Comment; **nullable** |

**`fact_member_stats`**
| Column | Type | Notes |
|---|---|---|
| member_id | int | FK → dim_member |
| duration_minutes | int | |
| usage_tnd | float | |
| orders_transfer_tnd | float | |
| usb_data_tnd | float | |
| total_amount_tnd | float | |

---

## Stage 4: Writer (`writer.py`)

Writes all dimension and fact tables to `output/dims/` and `output/facts/` respectively.

**Default (CSV):**
```
output/
├── dims/
│   ├── dim_cashier.csv
│   ├── dim_terminal.csv
│   ├── dim_item.csv
│   └── dim_member.csv
└── facts/
    ├── fact_cash_transactions.csv
    ├── fact_sessions.csv
    ├── fact_stock_movements.csv
    └── fact_member_stats.csv
```

**Optional Excel:** Pass `--format excel` to write a single `output/gamefydb.xlsx` with one sheet per table.

---

## CLI (`run.py`)

```
python run.py                          # CSV output, default paths
python run.py --format excel           # Excel output
python run.py --input path/to/excel/   # Custom input directory
python run.py --output path/to/out/    # Custom output directory
```

---

## Dependencies (`requirements.txt`)

```
pandas
xlrd
openpyxl
```
