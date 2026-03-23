# Technology Stack

**Project:** Data Normalization Desktop App
**Researched:** 2026-03-23
**Confidence:** HIGH

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

```bash
# Core Dependencies
pip install PySide6 beautifulsoup4 lxml pandas SQLAlchemy pydantic

# Dev Dependencies
pip install pytest pytest-qt PyInstaller ruff
```

## Sources
- Official PySide6 Documentation
- SQLAlchemy 2.0 Release Notes
- BeautifulSoup4 Official Documentation
