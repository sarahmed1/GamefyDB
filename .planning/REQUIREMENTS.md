# Requirements

## v1 Requirements

### Core Pipeline
- [ ] **PIPE-01**: User can specify a local directory containing `.html` files for processing
- [ ] **PIPE-02**: System extracts data from `.html` DOM using BeautifulSoup4 and lxml
- [ ] **PIPE-03**: System normalizes extracted data into a standardized structure
- [ ] **PIPE-04**: System persists normalized data sequentially in a local SQLite database schema

### User Interface
- [ ] **UI-01**: User can initiate the parsing and normalization pipeline via the desktop app
- [ ] **UI-02**: User sees real-time progress tracking (e.g., progress bar) without the UI freezing (via QThread)
- [ ] **UI-03**: User can view basic logs and status messages for the current pipeline run
- [ ] **UI-04**: User can gracefully cancel or pause a long-running pipeline extraction process

## v2 Requirements (Deferred)
- [ ] **V2-01**: User can preview/verify batch anomalies in the UI before committing them to SQLite
- [ ] **V2-02**: User can view a comprehensive, filterable live log viewer within the app
- [ ] **V2-03**: System provides integrated Machine Learning prediction based on normalized data

## Out of Scope
- **Cloud/Remote Database**: Overcomplicates infrastructure, requires authentication, slows local processing. Everything must be contained in a local SQLite file.
- **Machine Learning for v1**: Explicitly stated as out-of-scope for the initial phases. Store normalized data precisely so ML can be trivially added later.
- **Web-based Electron UI**: High overhead, complex packaging, slow IPC to Python tools. Use native PySide6.

## Traceability
*(To be populated by roadmapper)*