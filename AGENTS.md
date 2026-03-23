<!-- GSD:project-start source:PROJECT.md -->
## Project

A desktop application built with PySide6 that ingests a Python data pipeline. The system handles parsing and extracting data from local `.html` files (which contain raw database data) using BeautifulSoup4/lxml, normalizes this data, and stores it systematically in a local SQLite database. Future milestones will include an ML prediction module, but initial efforts focus purely on the foundational stack, data extraction, and normalization pipeline.

**Core Value:** Providing a reliable, user-friendly desktop interface to streamline the extraction, normalization, and local storage of HTML-based data, ensuring it is cleanly formatted for subsequent ML modeling.
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
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
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
