# Project Roadmap

## Phases
- [ ] **Phase 1: Core Data Extraction & Storage** - The system can extract, normalize, and persist HTML data to a local database.
- [ ] **Phase 2: Desktop Interface & Processing Control** - Users can control and monitor the data pipeline through a responsive desktop application.

## Phase Details

### Phase 1: Core Data Extraction & Storage
**Goal**: The system can extract, normalize, and persist HTML data to a local database.
**Depends on**: None
**Requirements**: PIPE-02, PIPE-03, PIPE-04
**Success Criteria** (what must be TRUE):
  1. System can read raw HTML files and extract structured data using BeautifulSoup4 and lxml.
  2. Extracted data is normalized into a consistent standard format.
  3. Normalized records are successfully saved to a local SQLite database file.
**Plans**: 3 plans
- [x] 01-01-PLAN.md — Setup Database Models and Session
- [ ] 01-02-PLAN.md — HTML Extractor and Data Normalizer
- [ ] 01-03-PLAN.md — Batch Orchestrator and CLI Runner

### Phase 2: Desktop Interface & Processing Control
**Goal**: Users can control and monitor the data pipeline through a responsive desktop application.
**Depends on**: Phase 1
**Requirements**: PIPE-01, UI-01, UI-02, UI-03, UI-04
**Success Criteria** (what must be TRUE):
  1. User can visually select a target directory and initiate the pipeline via a PySide6 window.
  2. User can view a live progress bar and status logs while files are processing.
  3. The UI remains responsive (does not freeze) during heavy data extraction.
  4. User can click a cancel button to safely stop an active pipeline run.
**Plans**: TBD
**UI hint**: yes

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Core Data Extraction & Storage | 0/3 | Not started | - |
| 2. Desktop Interface & Processing Control | 0/0 | Not started | - |
