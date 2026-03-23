## Project

A desktop application built with PySide6 that ingests a Python data pipeline. The system handles parsing and extracting data from local `.html` files (which contain raw database data) using BeautifulSoup4/lxml, normalizes this data, and stores it systematically in a local SQLite database. Future milestones will include an ML prediction module, but initial efforts focus purely on the foundational stack, data extraction, and normalization pipeline.

**Core Value:** Providing a reliable, user-friendly desktop interface to streamline the extraction, normalization, and local storage of HTML-based data, ensuring it is cleanly formatted for subsequent ML modeling.

## Technology Stack

## Recommended Stack
### Core Framework
| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| PySide6 | 6.8+ | Desktop UI | Qt for Python is the standard for robust, cross-platform native Python UIs. It has an official LTS branch, avoids IPC overhead compared to Electron, and directly integrates with Python ML/data tools. | HIGH |
| Python | 3.12+ | Runtime | Best performance for data processing and native tool compatibility. | HIGH |
### Data Parsing & Extraction
| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| BeautifulSoup4 | 4.12+ | HTML Parsing | Industry standard for handling messy HTML files. Easy API for navigating DOM. | HIGH |
| lxml | 5.2+ | Parsing Engine | Highly performant C-based backend for BS4. Crucial for speed when processing many large local `.html` files. | HIGH |
### Data Normalization
| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Pandas | 2.2+ | Data Manipulation | While built-in Python logic works, Pandas provides vectorized operations essential for heavy data normalization, cleaning, and preparation for future ML pipelines. | HIGH |
| Pydantic | 2.7+ | Data Validation | Ensures data quality before it hits the database. Validates types and catches anomalies early. | HIGH |
### Storage & Database
| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| SQLite3 (built-in) | 3.45+ | Storage Engine | Zero-configuration, serverless, single-file database. Perfect for a local desktop app pipeline. | HIGH |
| SQLAlchemy | 2.0+ | ORM / Core | Provides a robust, typed interface to SQLite. Better than raw SQL strings for maintainability, schema migrations (via Alembic), and structured querying. | HIGH |
### Infrastructure & Tooling
| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| PyInstaller | 6.6+ | Packaging | Bundles the PySide6 app, Pandas, and Python interpreter into a single executable for easy distribution. | HIGH |
| pytest-qt | latest | UI Testing | Essential for testing PySide6 components headless. | MEDIUM |
## Alternatives Considered
| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Desktop UI | PySide6 | PyQt6 | PySide6 is officially supported by the Qt Company (LGPL), making licensing simpler than PyQt6 (GPL/Commercial). |
| Desktop UI | PySide6 | Electron/React | Introduces IPC overhead (Node vs Python), complicates packaging, and uses significantly more memory. |
| DB Access | SQLAlchemy | Raw sqlite3 | Raw SQL strings are brittle, lack type safety, and make schema migrations difficult as the data model evolves for ML. |
| Normalization | Pandas | Built-in Python Dicts | Fine for small data, but built-in data structures are too slow and lack the statistical/cleaning methods needed for ML preparation. |
## Installation
# Core Dependencies
# Dev Dependencies
## Sources
- Official PySide6 Documentation
- SQLAlchemy 2.0 Release Notes
- BeautifulSoup4 Official Documentation

## Conventions

Conventions not yet established. Will populate as patterns emerge during development.

## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.

## Workflow

Use direct repository edits for implementation and fixes.

Suggested approach:
- Keep changes small and focused
- Add or update tests when behavior changes
- Run relevant tests before finishing
- Document assumptions and follow-up work clearly

## Context7 Usage

Use Context7 for library, framework, and API documentation questions instead of relying on memory.

When Context7 applies:
- Setup or configuration tasks for a framework/library
- Code generation that depends on external libraries
- API reference requests or method/option lookups
- Version-specific questions (prefer versioned docs when available)

Context7 flow:
1. Resolve the library ID using `mcp_io_github_ups_resolve-library-id`.
2. Fetch docs with `mcp_io_github_ups_get-library-docs` using the selected ID.
3. Base implementation details on fetched docs and mention version context when relevant.




