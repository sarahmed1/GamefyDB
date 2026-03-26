# Project Workflow

## 1) Runtime Entry

The application starts in src/main.py.

- If --target is not provided, the GUI mode runs.
- If --target is provided, the CLI mode runs.

Main runtime flags:

- --target: directory containing Excel exports (`.xlsx` / `.xls`) and optional legacy HTML exports
- --batch-size: number of files per batch (default 50)
- --db-url: SQLAlchemy database URL (default sqlite:///local.db)

## 2) GUI Workflow (PySide6)

GUI entrypoint: src/frontend/app/gui.py

1. Create QApplication.
2. Create and show MainWindow.
3. User selects data directory.
4. User starts the pipeline.
5. Pipeline runs in a background QThread (PipelineWorker).
6. Progress and logs are streamed to the UI.
7. On completion, database table view is refreshed.

Main window behavior in src/frontend/ui/main_window.py:

- Data Pipeline tab:
  - Browse folder
  - Start/Cancel pipeline
  - Progress bar + log view
- Database Explorer tab:
  - View tables sessions, cash_reports, stock_reports, member_reports
  - Refresh table data
  - Empty all tables via confirmation

Worker behavior in src/frontend/ui/worker.py:

- Calls run_pipeline with callbacks:
  - progress_callback
  - log_callback
  - should_cancel

## 3) CLI Workflow

CLI entrypoint: src/backend/app/cli.py

1. Validate target directory exists.
2. Initialize database schema.
3. Execute run_pipeline.
4. Return process exit code (0 success, 1 failure).

## 4) Pipeline Core Workflow

Pipeline orchestrator: src/backend/pipeline/orchestrator.py

For each batch of supported source files:

1. Extraction
  - Function: extract_file in src/backend/pipeline/extractor.py
  - Detect report type from filename:
    - SESSION DATA -> session
    - CASH DATA -> cash
    - STOCK DATA -> stock
    - MEMBER DATA -> member
  - Parse by extension:
    - `.xlsx` / `.xls` via pandas.read_excel
    - `.html` via pandas.read_html(flavor="lxml") for legacy compatibility
  - Normalize malformed table layout by collapsing duplicate columns.
  - Emit Python dict rows and attach source_file.

2. Normalization
  - Function: normalize_data in src/backend/pipeline/normalizer.py
  - Convert extracted dicts into Pydantic schemas.
  - Parse domain values:
    - Currency text -> float
    - Duration text -> integer minutes
    - Date text -> datetime
  - Remove noise rows (page footer metadata and timestamp-only artifacts).

3. Persistence
  - Database session via src/backend/database/session.py.
  - ORM models in src/backend/database/models.py.
  - Per batch, upsert behavior is rerun-safe by source_file:
    - Delete existing rows for touched source_file values
    - Insert fresh normalized rows
  - Commit transaction or rollback on failure.

## 5) Data Model Layers

- Validation layer: src/backend/schemas/record.py (Pydantic)
- Persistence layer: src/backend/database/models.py (SQLAlchemy ORM)
- Storage engine: SQLite (through SQLAlchemy URL sqlite:///...)

Managed tables:

- sessions
- cash_reports
- stock_reports
- member_reports

## 6) Behavior Confirmed by Tests

From tests:

- tests/test_pipeline_e2e.py
  - Extraction and normalization succeed against supported fixture files.
  - Noise rows are removed.
  - Output volume remains high (>1000 rows across fixtures).
- tests/test_orchestrator_dedupe.py
  - Running the same input twice does not increase row count.
- tests/test_empty_database.py
  - empty_database clears all managed tables.
  - extracted_at defaults are timezone-aware UTC callables.

Operational note from repository memory:

- CLI run against data/ inserted 12,764 rows and rerun kept counts stable.

## 7) Desktop Packaging Workflow

Executable packaging uses PyInstaller with the committed spec file:

- Command:
  - `python -m PyInstaller --clean --noconfirm GamefyDB.spec`
- Output directories:
  - `dist/GamefyDB/` (release-ready output)
  - `build/GamefyDB/` (intermediate artifacts)
