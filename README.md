# GamefyDB

ETL pipeline that ingests four gaming center `.xls` reports, normalises the data, and outputs a star-schema dataset ready for data warehouse import.

## Project Structure

```
GamefyDB/
├── excel/                          # Source .xls files (input)
│   ├── Cash DATA 01-09-2025.xls
│   ├── DATA session reports 01-09-2025.xls
│   ├── Stock DATA 01-09-2025.xls
│   └── memeber DATA 01-09-2025.xls
│
├── gamefydb/                       # Pipeline modules
│   ├── ingestor.py                 # Reads .xls files via xlrd, strips artifacts
│   ├── cleaner.py                  # Type normalization (amounts, datetimes, durations)
│   ├── transformer.py              # Builds star schema (dims + facts)
│   └── writer.py                   # Writes CSV or Excel output
│
├── output/                         # Generated output (git-ignored)
│   ├── dims/
│   │   ├── dim_cashier.csv
│   │   ├── dim_terminal.csv
│   │   ├── dim_item.csv
│   │   └── dim_member.csv
│   ├── facts/
│   │   ├── fact_cash_transactions.csv
│   │   ├── fact_sessions.csv
│   │   ├── fact_stock_movements.csv
│   │   └── fact_member_stats.csv
│   └── gamefydb.xlsx               # Excel output (all tables as sheets)
│
├── tests/                          # pytest test suite
├── run.py                          # CLI entry point
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

## Output Schema

The pipeline produces 4 dimension tables and 4 fact tables:

| Table | Key columns |
|---|---|
| `dim_cashier` | `cashier_id`, `cashier_name` |
| `dim_terminal` | `terminal_id`, `terminal_name`, `terminal_type` |
| `dim_item` | `item_id`, `item_name`, `category` |
| `dim_member` | `member_id`, `username`, `firstname`, `lastname` |
| `fact_cash_transactions` | `cashier_id`, `terminal_id`*, `transaction_datetime`, `amount_tnd` |
| `fact_sessions` | `cashier_id`, `terminal_id`, `duration_minutes`, `paused_duration_minutes`* |
| `fact_stock_movements` | `cashier_id`, `item_id`, `terminal_id`*, `quantity`, `unit_price_tnd` |
| `fact_member_stats` | `member_id`, `duration_minutes`, `usage_tnd`, `total_amount_tnd` |

\* nullable

---

## Running Locally

**Requirements:** Python 3.12+

```bash
# Install dependencies
pip install -r requirements.txt

# CSV output (default) — writes to output/dims/ and output/facts/
python run.py --input excel --output output

# Excel output — writes output/gamefydb.xlsx
python run.py --input excel --output output --format excel

# Custom input/output directories
python run.py --input path/to/xls --output path/to/results --format csv

# Run tests
python -m pytest
```

---

## Running with Docker

**Requirements:** Docker, Docker Compose

```bash
# Build and run (CSV output by default)
docker compose up --build

# Excel output
docker compose run --rm etl --input excel --output output --format excel

# Rebuild after code changes
docker compose build
docker compose up
```

Source files are mounted read-only from `./excel` and output is written to `./output` on the host.

To change the output format permanently, edit the `command` in `docker-compose.yml`:

```yaml
services:
  etl:
    build: .
    volumes:
      - ./excel:/app/excel:ro
      - ./output:/app/output
    command: ["--input", "excel", "--output", "output", "--format", "excel"]
```
