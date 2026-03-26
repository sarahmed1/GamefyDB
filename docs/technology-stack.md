# Technology Stack Used

This stack list reflects what is currently used in code and project configuration.

## 1) Runtime Language and App Type

- Python 3.12+ (targeted in README)
- Desktop application with optional CLI mode

## 2) UI Stack

- PySide6 (requirements.txt)
	- QApplication startup: src/frontend/app/gui.py
	- Main UI, widgets, dialogs: src/frontend/ui/main_window.py
	- Background threading and signals: src/frontend/ui/worker.py
	- SQL table viewer layer: QSqlDatabase + QSqlTableModel in main_window.py

## 3) Extraction and Parsing Stack

- pandas (requirements.txt)
	- Excel table extraction with read_excel
	- Legacy HTML extraction with read_html
	- DataFrame transformations and null handling
	- Used in src/backend/pipeline/extractor.py and src/backend/pipeline/normalizer.py

- openpyxl (requirements.txt)
	- Engine used by pandas.read_excel for `.xlsx` files
	- Used by extraction pipeline in src/backend/pipeline/extractor.py

- xlrd (requirements.txt)
	- Engine used by pandas.read_excel for `.xls` files
	- Used by extraction pipeline in src/backend/pipeline/extractor.py

- lxml (requirements.txt)
	- Parser backend selected through pandas.read_html(flavor="lxml")
	- Used by legacy HTML extraction in src/backend/pipeline/extractor.py

- beautifulsoup4 (requirements.txt)
	- Declared dependency in project stack for optional HTML parsing support.
	- Current extractor implementation uses pandas engines directly.

## 4) Validation and Data Contracts

- pydantic (requirements.txt)
	- Strong schema validation and serialization for normalized records
	- Implemented in src/backend/schemas/record.py
	- Consumed in src/backend/pipeline/normalizer.py

## 5) Persistence Layer

- SQLAlchemy 2.x (requirements.txt)
	- Declarative models: src/backend/database/models.py
	- Engine/session lifecycle: src/backend/database/session.py
	- Transactional inserts and delete-before-insert rerun-safe behavior: src/backend/pipeline/orchestrator.py

- SQLite (via SQLAlchemy URL sqlite:///...)
	- Default local database path local.db
	- Used by both CLI and GUI modes

Managed ORM tables:

- sessions
- cash_reports
- stock_reports
- member_reports

## 6) Packaging and Distribution

- PyInstaller
	- Spec file: GamefyDB.spec
	- Build outputs: build/GamefyDB/
	- Distribution outputs: dist/GamefyDB/

## 7) Testing Stack

- pytest (requirements.txt)
	- Test suite location: tests/
	- End-to-end extraction/normalization checks
	- Rerun-safety and database cleanup checks

## 8) Standard Library Usage

Frequently used built-in modules:

- argparse: CLI argument parsing
- pathlib: file system traversal and path handling
- logging: pipeline and CLI logs
- datetime: timestamp parsing and UTC defaults
- re: noise filtering and value parsing helpers
- math: batch count calculation
- typing: callback and schema typing hints

## 9) Effective Architectural Style

Current code follows a layered pipeline architecture:

- Entrypoints: src/main.py, src/backend/app/cli.py, src/frontend/app/gui.py
- Processing: src/backend/pipeline/*
- Validation: src/backend/schemas/record.py
- Persistence: src/backend/database/*
- Presentation: src/frontend/ui/*

This keeps extraction, normalization, storage, and UI concerns separated while sharing one backend pipeline.
