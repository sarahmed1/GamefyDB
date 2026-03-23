---
phase: 01-core-data-extraction-storage
plan: 02
subsystem: data-storage
tags:
  - pipeline
  - beautifulsoup
  - pandas
  - pydantic
  - data-extraction
requires:
  - beautifulsoup4
  - lxml
  - pandas
  - pydantic
provides:
  - HTML Parsing Module
  - Pandas-based normalization and Pydantic validation
affects:
  - src/pipeline/extractor.py
  - src/pipeline/normalizer.py
tech-stack:
  added:
    - beautifulsoup4
    - lxml
    - pandas
  patterns:
    - BeautifulSoup lxml parsing
    - Pandas vectorized DataFrame cleaning
    - Pydantic BaseModel iteration and validation
key-files:
  created:
    - src/pipeline/extractor.py
    - src/pipeline/normalizer.py
    - tests/test_extractor.py
    - tests/test_normalizer.py
  modified: []
decisions:
  - "Used BeautifulSoup with lxml parser for robust handling of malformed HTML files."
  - "Leveraged Pandas for vectorized NaN cleaning before iterating and validating via Pydantic schema."
  - "Invalid rows during normalization strictly trigger warnings and are dropped rather than saved."
metrics:
  duration: 60
  completed_date: "2026-03-23"
---

# Phase 01 Plan 02: Core Data Pipeline Summary

**Core execution:** Implemented the core pipeline modules for HTML parsing and data normalization, ensuring malformed files are skipped and invalid rows are strictly dropped.

## Executed Tasks
1. **Task 1: HTML Extractor**
   - Created `extract_html_file(filepath)` using `BeautifulSoup4` with the `lxml` parser.
   - Handled `FileNotFoundError`, empty files, and malformed HTML correctly by returning `None` and logging a warning.
   - Built a test suite for `valid`, `empty`, and `missing_fields` cases.
2. **Task 2: Data Normalizer**
   - Implemented `normalize_data(raw_data_list)` loading dict lists into a Pandas `DataFrame`.
   - Cleaned `NaN` fields, stripped strings, and handled `to_dict` mappings to pass strict Pydantic requirements.
   - Filtered out valid instances into a strict list of `GameRecordSchema` objects, dropping and logging the invalid ones.

## Deviations from Plan
None - plan executed exactly as written.

## Self-Check: PASSED
- `src/pipeline/extractor.py` and `tests/test_extractor.py` found.
- `src/pipeline/normalizer.py` and `tests/test_normalizer.py` found.
- Commits made successfully.
