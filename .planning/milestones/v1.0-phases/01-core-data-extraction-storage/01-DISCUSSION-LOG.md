# Phase 1: Core Data Extraction & Storage - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-23
**Phase:** 1-Core Data Extraction & Storage
**Areas discussed:** Extraction Behavior, Data Normalization Approach, Database Schema Management, Processing Scale/Batching

---

## Extraction Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Skip file and log warning (Recommended) | Gracefully handle malformed files without stopping the entire process. | ✓ |
| Fail fast | Abort pipeline on first malformed file. | |
| Attempt partial extraction | Try to extract what is available, skipping only broken fields. | |

**User's choice:** Skip file and log warning (Auto-selected)
**Notes:** Auto-selected recommended default via `--auto` mode.

---

## Data Normalization Approach

| Option | Description | Selected |
|--------|-------------|----------|
| Strict - drop invalid rows and log (Recommended) | Maintain high data quality by rejecting bad data. | ✓ |
| Permissive - fill with nulls | Keep all records even if some fields are missing/invalid. | |
| Halt pipeline on invalid data | Stop entirely if data doesn't match schema. | |

**User's choice:** Strict - drop invalid rows and log (Auto-selected)
**Notes:** Auto-selected recommended default via `--auto` mode.

---

## Database Schema Management

| Option | Description | Selected |
|--------|-------------|----------|
| SQLAlchemy models (create_all) (Recommended) | Keep it simple for phase 1; rely on SQLAlchemy to create tables. | ✓ |
| Alembic migrations | Setup full migration environment immediately. | |
| Raw SQL schema files | Execute raw .sql files to create schema. | |

**User's choice:** SQLAlchemy models (create_all) (Auto-selected)
**Notes:** Auto-selected recommended default via `--auto` mode.

---

## Processing Scale/Batching

| Option | Description | Selected |
|--------|-------------|----------|
| Process in batches (Recommended) | Prevent memory bloat when handling thousands of files. | ✓ |
| Load all at once | Load everything into memory before processing. | |
| One by one | Process files strictly sequentially without batching. | |

**User's choice:** Process in batches (Auto-selected)
**Notes:** Auto-selected recommended default via `--auto` mode.

---

## the agent's Discretion

- File path structures for logging outputs

## Deferred Ideas

- None
