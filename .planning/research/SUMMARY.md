# Research Summary: Data Normalization Desktop App

**Domain:** Desktop Data Processing & Normalization Application
**Researched:** 2026-03-23
**Overall confidence:** HIGH

## Executive Summary

The project requires a robust desktop application capable of parsing raw local HTML files, normalizing the extracted data, and persisting it to a local SQLite database, preparing it for future machine learning phases. The standard approach for this kind of Python desktop tooling is PySide6 due to its native integration with the Python data stack and official support from the Qt Company. By using PySide6, we avoid the heavy IPC (Inter-Process Communication) overhead of Node/Electron architectures while maintaining high performance for processing thousands of files.

For extraction and normalization, BeautifulSoup4 paired with the fast `lxml` parser handles messy HTML reliably, while Pandas and Pydantic provide a robust foundation for cleaning, validating, and vectorizing the dataset before insertion. SQLAlchemy 2.0 provides safe, typed SQL execution against local SQLite databases, far superior to raw `sqlite3` string execution as schemas evolve.

## Key Findings

**Stack:** PySide6 for UI, BS4/lxml for parsing, Pandas/Pydantic for normalization, and SQLAlchemy+SQLite for storage.
**Architecture:** Model-View-Controller (MVC) separating the Qt UI layer from the heavy, long-running data pipeline, utilizing QThread/QRunnable for non-blocking UI background processing.
**Critical pitfall:** Blocking the Qt event loop. The heavy HTML parsing and Pandas normalization must execute on dedicated worker threads, using Qt signals/slots to report progress back to the UI.

## Implications for Roadmap

Based on research, suggested phase structure:

1. **Phase 1: Foundation & Data Pipeline Backend** - Establish the headless data extraction and normalization logic.
   - Addresses: Parsing `.html` with BS4, validating data, building the SQLAlchemy models.
   - Avoids: Mixing UI and business logic prematurely.

2. **Phase 2: PySide6 UI & Integration** - Build the desktop interface to monitor and trigger the pipeline.
   - Addresses: Progress bars, logging windows, file selection.
   - Avoids: Event loop blocking by correctly implementing QThread workers.

3. **Phase 3: Final Packaging & Distribution** - Compile to an executable.
   - Addresses: Bundling SQLite, PySide6, and the Python runtime with PyInstaller.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | PySide6 and BS4 are the unequivocal industry standards for this use case. |
| Features | HIGH | Pipeline extraction and local storage are well-defined table stakes. |
| Architecture | HIGH | Qt threading models are well-documented and robust. |
| Pitfalls | HIGH | Blocking the main thread is the most common and universally recognized GUI pitfall. |

## Gaps to Address
- Which specific ML models will be integrated in future phases? This might influence the structure of the normalized data stored in SQLite.
- Expected volume of HTML files to process concurrently.
