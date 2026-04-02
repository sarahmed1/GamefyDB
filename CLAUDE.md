# GamefyDB

ETL pipeline: ingests 4 `.xls` gaming center reports → normalizes → outputs a star-schema CSV/Excel dataset ready for DWH import.

## Commands

```bash
# Python is NOT on PATH — use full path for all commands
PYTHON="C:/Users/sarah/AppData/Local/Python/bin/python"

# Install dependencies
$PYTHON -m pip install -r requirements.txt

# Run tests
$PYTHON -m pytest

# Run pipeline — CSV output (default)
$PYTHON run.py --input excel --output output

# Run pipeline — Excel output
$PYTHON run.py --input excel --output output --format excel
```

## Architecture

Four pipeline stages, one module each:

```
excel/*.xls
    → gamefydb/ingestor.py   ingest_all()    raw DataFrames (strings)
    → gamefydb/cleaner.py    clean_all()     typed DataFrames
    → gamefydb/transformer.py transform()    star schema (4 dims + 4 facts)
    → gamefydb/writer.py     write_all()     CSV (dims/ facts/) or Excel
```

**Output tables:**
- `dim_cashier`, `dim_terminal`, `dim_item`, `dim_member`
- `fact_cash_transactions`, `fact_sessions`, `fact_stock_movements`, `fact_member_stats`

## Source Files (`excel/`)

| Key | Filename |
|-----|----------|
| `cash` | `Cash DATA 01-09-2025.xls` |
| `sessions` | `DATA session reports 01-09-2025.xls` |
| `stock` | `Stock DATA 01-09-2025.xls` |
| `members` | `memeber DATA 01-09-2025.xls` ← typo is in the real filename |

## Gotchas

**xlrd instead of pd.read_excel** — The members file triggers a `charmap` encoding error with pandas. All files are read with `xlrd.open_workbook()` + `ws.row_values()` directly.

**Column positions are DATA positions, not header positions** — Excel merged cells shift where data actually lands. `COLUMN_MAPS` in `ingestor.py` stores the empirically verified xlrd column indices. Do not adjust without re-verifying against the raw file.

**Narrow no-break space (`\u202f`) as thousands separator** — TND amounts look like `1 745,44 TND` where the space is `\u202f`. `parse_amount()` strips it before converting.

**Page-break artifacts every ~40 rows** — Each file repeats `Page X/Y`, two blank rows, and a header row periodically. `_strip_artifacts()` removes all of these.

**Members footer row** — The members file ends with a `Report Result :` row that passes the key-column check. `_clean_members` coerces `member_id` with `errors='coerce'` and drops NaN rows to catch it.

**Sessions `terminal` is already a clean name** — Unlike cash/stock where terminal is extracted from a `(NAME)` comment, sessions has the terminal name directly.
