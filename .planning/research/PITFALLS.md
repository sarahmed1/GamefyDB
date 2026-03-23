# Domain Pitfalls

**Domain:** Desktop Data Processing & Normalization Application
**Researched:** 2026-03-23

## Critical Pitfalls

Mistakes that cause rewrites or major issues.

### Pitfall 1: Blocking the Main Thread
**What goes wrong:** The UI freezes as soon as the user clicks the "Start Processing" button to parse the `.html` files.
**Why it happens:** Executing heavy operations (like reading local files with `BeautifulSoup` or writing to SQLite) directly within a UI event handler (like a button's `clicked.connect()` slot) halts the Qt Event Loop.
**Consequences:** Windows/macOS reports the application as "Not Responding," progress bars do not update, and the user must force-quit.
**Prevention:** Strictly separate the UI logic from the data extraction/normalization logic by utilizing `QThread`, `QRunnable`, and `QThreadPool`. All heavy tasks must execute in the background and communicate with the main UI thread via Qt Signals and Slots.

### Pitfall 2: Memory Leaks with Large HTML Processing
**What goes wrong:** The app consumes all available RAM when processing thousands of `.html` files.
**Why it happens:** `BeautifulSoup` objects are large memory structures. If a script appends the full parsed tree (or entire file contents) to a global list before normalizing and saving to SQLite, memory consumption explodes.
**Consequences:** `MemoryError` crashes during execution.
**Prevention:** Implement a streaming or batching architecture. Parse an HTML file, extract the specific tabular/structured data, normalize it via Pandas, flush/commit it to SQLite via SQLAlchemy, and immediately delete the `BeautifulSoup` reference to allow garbage collection before moving to the next file.

## Moderate Pitfalls

### Pitfall 1: SQLite Concurrency Limitations
**What goes wrong:** `sqlite3.OperationalError: database is locked`.
**Why it happens:** Attempting to write to the local SQLite database concurrently from multiple threads. SQLite is primarily a single-writer database.
**Prevention:** Ensure that the database connection/session created by SQLAlchemy is correctly scoped to a single background worker thread handling all writes sequentially, or use `Queue` patterns if multi-threaded writes are absolutely required.

### Pitfall 2: Unhandled HTML Anomalies
**What goes wrong:** The pipeline crashes midway through processing because an `.html` file is missing a `<table id="data">` tag.
**Prevention:** Robust exception handling around the `bs4` finding and extraction logic, logging the specific file that failed rather than crashing the entire batch process. Use Pydantic to strictly validate the extracted rows before attempting to insert them into the database.

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Data Extraction | Slow parsing speeds with standard `html.parser` | Explicitly use the C-based `lxml` backend (`BeautifulSoup(html, "lxml")`) which is significantly faster for batch operations. |
| Normalization | Writing Python loops for cleaning tabular data | Use Pandas vectorized operations (e.g., `df.dropna()`, `df.astype()`) which execute in C and are orders of magnitude faster than iterating row-by-row. |
| UI Integration | Flooding the UI thread with progress updates | Only emit progress signals periodically (e.g., every 50 files) rather than on every single parsed row, as signal flooding can also lock the UI. |

## Sources

- PySide6 QThread Documentation
- BeautifulSoup Performance Tuning (lxml)
- SQLAlchemy SQLite Concurrency
