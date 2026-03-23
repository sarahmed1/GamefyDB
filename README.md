# GamefyDB

A robust Python application built with **PySide6** and **Pandas** designed to ingest, normalize, and store FastReport HTML data exports into a structured SQLite database. This system acts as a foundational data pipeline to cleanly format raw tabular data for future Machine Learning modeling.

## Features

- **Automated HTML Extraction:** Reads complex FastReport HTML files featuring merged cells and spacer columns.
- **Robust Normalization:** Cleans currencies (e.g., `6,00 TND` -> `6.0`), time durations (e.g., `3 h 54 min` -> `234` mins), and messy strings.
- **Data Integrity:** Strict validation layer using **Pydantic** schemas and modern **SQLAlchemy 2.0** ORM typed models.
- **Targeted Storage:** Dynamically routes reports to 4 specific SQLite tables:
  - `sessions` (Session Data)
  - `cash_reports` (Cash Data)
  - `stock_reports` (Stock Data)
  - `member_reports` (Member Data)
- **Dual Interface:** Run as a PySide6 Desktop GUI or an automated CLI background pipeline.

## Project Structure

```text
src/
   main.py                  # Thin launcher (routes GUI vs CLI)
   backend/
      app/                   # Backend app entrypoints
      database/              # SQLAlchemy models and DB session utilities
      pipeline/              # Extractor, normalizer, orchestrator
      schemas/               # Pydantic validation schemas
   frontend/
      app/                   # Frontend app entrypoints
      ui/                    # PySide6 windows and background workers
tests/                     # Pipeline and DB tests
data/                      # Local HTML fixture data
```

## Prerequisites

- Python 3.12+

## Installation

1. Clone the repository and navigate to the project directory:
   ```bash
   cd GamefyDB
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   ```

3. Activate the virtual environment:
   - **Windows:**
     ```cmd
     venv\Scripts\activate
     ```
   - **macOS / Linux:**
     ```bash
     source venv/bin/activate
     ```

4. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### 1. Start the Desktop GUI
To launch the PySide6 user interface:
```bash
python src/main.py
```

Direct GUI module entrypoint:
```bash
python -m src.frontend.app.gui
```

### 2. Run the CLI Pipeline
To run the extraction and normalization pipeline directly from the command line, use the `--target` flag and point it to the directory containing your `.html` files (e.g., the `data/` directory).

```bash
python src/main.py --target data
```

Direct CLI module entrypoint:
```bash
python -m src.backend.app.cli
```
*Optional arguments:*
- `--batch-size <int>`: Number of files to process per batch (default: 50)
- `--db-url <string>`: Database connection string (default: `sqlite:///local.db`)

## Testing

To verify the extraction and normalization logic against your raw data sets:

```bash
python -m pytest tests/
```
