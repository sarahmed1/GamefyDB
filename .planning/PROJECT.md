## What This Is
A desktop application built with PySide6 that ingests a Python data pipeline. The system handles parsing and extracting data from local `.html` files (which contain raw database data) using BeautifulSoup4/lxml, normalizes this data, and stores it systematically in a local SQLite database. Future milestones will include an ML prediction module, but initial efforts focus purely on the foundational stack, data extraction, and normalization pipeline.

## Core Value
Providing a reliable, user-friendly desktop interface to streamline the extraction, normalization, and local storage of HTML-based data, ensuring it is cleanly formatted for subsequent ML modeling.

## Requirements

### Validated
- ✓ Extract tabular/structured data from `.html` files using BeautifulSoup4 and lxml — v1.0
- ✓ Normalize the extracted raw data — v1.0
- ✓ Persist normalized data in a local SQLite database — v1.0
- ✓ Implement a PySide6-based desktop UI for initiating and monitoring the data pipeline — v1.0
- ✓ Provide basic status, progress tracking, and logging within the desktop UI — v1.0

### Active
(None - run `/gsd-new-milestone` to plan next version)

### Out of Scope
- Machine Learning / Prediction features — Deferred to a later phase (v2.0)
- Cloud/Remote Database — Overcomplicates infrastructure, slows local processing
- Web-based Electron UI — High overhead, complex packaging, slow IPC to Python tools

## Context
Shipped v1.0 MVP with 740 LOC Python.
Tech stack: PySide6, SQLAlchemy, Pydantic, BeautifulSoup4, Pandas.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Desktop Stack: PySide6 | A pure Python stack simplifies integration with the existing Python data pipeline and future ML tools, avoiding cross-language IPC overhead. | ✓ Good |
| Data Parsing: BS4/lxml | The industry standard, robust Python tooling for handling potentially messy HTML data extraction. | ✓ Good |
| Storage: SQLite | Self-contained, file-based SQL database perfectly suited for normalized, structured data on a desktop environment without requiring a separate database server. | ✓ Good |
| Validation: Pydantic | Schema defines strict typing via Pydantic matching the DB structure. | ✓ Good |
| Background: QThread | Used QThread with signals for non-blocking UI integration | ✓ Good |

## Current State
v1.0 MVP Shipped (2026-03-23) — Core data extraction pipeline is fully wired to a PySide6 desktop interface for user-driven processing and real-time monitoring.

## Next Milestone Goals
(To be defined via `/gsd-new-milestone`)

---
*Last updated: 2026-03-23 after v1.0 milestone*
