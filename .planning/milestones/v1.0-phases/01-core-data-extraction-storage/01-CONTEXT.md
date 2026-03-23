# Phase 1: Core Data Extraction & Storage - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

The core backend pipeline to extract tabular/structured data from local `.html` files using BeautifulSoup4/lxml, apply data normalization using Pandas/Pydantic, and persist the standardized data sequentially in a local SQLite database schema using SQLAlchemy. This phase does NOT include the desktop UI.

</domain>

<decisions>
## Implementation Decisions

### Extraction Behavior
- **D-01:** Handling malformed HTML: Skip the file and log a warning rather than failing the entire pipeline or attempting partial extraction. (Auto-selected default)

### Data Normalization Approach
- **D-02:** Normalization strictness: Strict normalization — drop invalid rows and log them, rather than filling with nulls or halting. (Auto-selected default)

### Database Schema Management
- **D-03:** Schema creation: Use SQLAlchemy models with `create_all()` initially. Keep it simple; Alembic migrations can be added later if the schema evolves significantly. (Auto-selected default)

### Processing Scale/Batching
- **D-04:** Batching strategy: Process files in sequential batches to manage memory efficiently, rather than loading all files at once. (Auto-selected default)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

No external specs — requirements fully captured in decisions above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None (Greenfield project)

### Established Patterns
- SQLAlchemy 2.0 pattern (ORM models)
- BeautifulSoup4 with lxml parser

### Integration Points
- None yet. Future UI will invoke this pipeline via `QThread`.

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 01-core-data-extraction-storage*
*Context gathered: 2026-03-23*
