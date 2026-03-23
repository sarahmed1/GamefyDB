# Feature Landscape

**Domain:** Desktop Data Processing & Normalization Application
**Researched:** 2026-03-23

## Table Stakes

Features users expect. Missing = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Directory Selection | Essential to specify the folder of raw `.html` files for processing | Low | `QFileDialog` standard component |
| Parsing Engine | Core logic to extract data from `.html` DOM using BS4/lxml | High | Crucial point for handling broken/messy HTML structures |
| Data Normalization | Core logic for cleaning and standardizing extracted data before persistence | Med | Relies heavily on Pandas/Pydantic validation |
| Local Database Persistence | Persist normalized data sequentially in an SQLite schema | Low | Requires schema migrations via SQLAlchemy/Alembic |
| Progress Tracking UI | Prevent the application from appearing frozen during long parsing tasks | Med | Must be offloaded to `QThread` with Qt signals updating the progress bar |

## Differentiators

Features that set product apart. Not expected, but valued.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Live Log Viewer | Real-time debugging and processing errors directly in the UI | Med | Built with `QPlainTextEdit` and custom logging handler |
| Cancel/Pause Pipeline | Allows users to gracefully interrupt a long-running extraction process | High | Requires safely terminating worker threads and rolling back SQLite transactions |
| Batch Verification | Validation step highlighting anomalies in the UI before committing them to SQLite | Med | High value for data integrity |

## Anti-Features

Features to explicitly NOT build.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Cloud/Remote Database | Overcomplicates infrastructure, requires authentication, slows local processing | Keep everything contained in a local `data.sqlite` file. |
| Machine Learning | Explicitly stated as out-of-scope for the initial phases | Store normalized data precisely so ML can be trivially added later |
| Web-based Electron UI | High overhead, complex packaging, slow IPC to Python ML tools | Use native PySide6. |

## Feature Dependencies

```text
Directory Selection → Parsing Engine (BS4) → Data Normalization (Pandas) → Local DB Persistence (SQLite)
Parsing Engine → Progress Tracking UI
```

## MVP Recommendation

Prioritize:
1. Parsing Engine and Data Normalization logic (Headless first)
2. Local Database Persistence (SQLAlchemy/SQLite)
3. Basic PySide6 UI with Directory Selection and a Progress Bar

Defer: Live Log Viewer, Batch Verification

## Sources

- PySide6 Application Patterns
- Python Data Engineering Best Practices
