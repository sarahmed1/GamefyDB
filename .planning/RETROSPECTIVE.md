# Project Retrospective

Living document capturing learnings, trends, and execution feedback across all project milestones.

## Milestone: v1.0 — Initial Pipeline MVP

**Shipped:** 2026-03-23
**Phases:** 2 | **Plans:** 6

### What Was Built
- Established core database connection with SQLAlchemy and strict validation via Pydantic schemas.
- Implemented core pipeline modules for HTML parsing (BeautifulSoup) and data normalization (pandas).
- Built an end-to-end extraction orchestrator and CLI wrapper.
- Created a native PySide6 `MainWindow` with directory selection.
- Implemented a `QThread`-based `PipelineWorker` to run the data pipeline asynchronously.
- Wired the worker to the main interface, enabling real-time feedback and safe cancellation.

### What Worked
- Clean separation of concerns between domain logic and UI. The pipeline logic remained framework agnostic by using simple callbacks.
- Pydantic validation caught invalid rows cleanly without bringing down the database transaction.

### What Was Inefficient
- None. Development proceeded precisely according to plans with no major rework.

### Patterns Established
- Dependency-injected callbacks for long-running pipeline execution (UI provides callbacks, Core uses them).
- Background worker `QThread` pattern to prevent UI freeze during data extraction.

### Key Lessons
- PySide6 integrates cleanly with standard Python tools when keeping the threading models isolated via signals/slots.

## Cross-Milestone Trends

(No trends yet - initial milestone.)
