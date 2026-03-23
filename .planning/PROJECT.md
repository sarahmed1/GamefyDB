## What This Is
A desktop application built with PySide6 that ingests a Python data pipeline. The system handles parsing and extracting data from local `.html` files (which contain raw database data) using BeautifulSoup4/lxml, normalizes this data, and stores it systematically in a local SQLite database. Future milestones will include an ML prediction module, but initial efforts focus purely on the foundational stack, data extraction, and normalization pipeline.

## Core Value
Providing a reliable, user-friendly desktop interface to streamline the extraction, normalization, and local storage of HTML-based data, ensuring it is cleanly formatted for subsequent ML modeling.

## Requirements

### Validated
- [x] Extract tabular/structured data from `.html` files using BeautifulSoup4 and lxml (Validated in Phase 1: core-data-extraction-storage)
- [x] Normalize the extracted raw data (Validated in Phase 1: core-data-extraction-storage)
- [x] Persist normalized data in a local SQLite database (Validated in Phase 1: core-data-extraction-storage)

### Active
- [ ] Implement a PySide6-based desktop UI for initiating and monitoring the data pipeline
- [ ] Provide basic status, progress tracking, and logging within the desktop UI

### Out of Scope
- Machine Learning / Prediction features (Deferred to a later phase per user request)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Desktop Stack: PySide6 | A pure Python stack simplifies integration with the existing Python data pipeline and future ML tools, avoiding cross-language IPC overhead. | — Pending |
| Data Parsing: BS4/lxml | The industry standard, robust Python tooling for handling potentially messy HTML data extraction. | Validated in Phase 1 |
| Storage: SQLite | Self-contained, file-based SQL database perfectly suited for normalized, structured data on a desktop environment without requiring a separate database server. | Validated in Phase 1 |

## Current State
Phase 1 complete — core data extraction and storage pipeline is established and functionally parsing HTML into local SQLite.

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: Mon Mar 23 2026 after phase 1 completion*
