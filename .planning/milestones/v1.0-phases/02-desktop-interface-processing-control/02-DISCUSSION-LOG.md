# Phase 2: Desktop Interface & Processing Control - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-23
**Phase:** 2-Desktop Interface & Processing Control
**Areas discussed:** Directory Selection, Progress Tracking, Log Viewing, Cancellation Behavior

---

## Directory Selection

| Option | Description | Selected |
|--------|-------------|----------|
| Standard native file dialog button + path display | (Recommended) Reuses native file picker dialog | ✓ |
| Drag and drop area | Dragging folder into app | |

**User's choice:** Standard native file dialog button + path display (Auto-selected)
**Notes:** Selected via --auto default.

---

## Progress Tracking

| Option | Description | Selected |
|--------|-------------|----------|
| Single progress bar tracking overall file count | (Recommended) Tracks total file process vs complete | ✓ |
| Detailed progress with current file parsing status | Shows what is currently parsing | |

**User's choice:** Single progress bar tracking overall file count (Auto-selected)
**Notes:** Selected via --auto default.

---

## Log Viewing

| Option | Description | Selected |
|--------|-------------|----------|
| Embedded plain text widget (QPlainTextEdit) in a lower pane | (Recommended) Fits all in one window | ✓ |
| Separate "Logs" tab/window | Uses extra window or tab component | |

**User's choice:** Embedded plain text widget (QPlainTextEdit) in a lower pane (Auto-selected)
**Notes:** Selected via --auto default.

---

## Cancellation Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Graceful stop at the end of the current batch | (Recommended) Safest for DB consistency | ✓ |
| Immediate interrupt | Kills thread immediately, may leave transactions open | |

**User's choice:** Graceful stop at the end of the current batch (Auto-selected)
**Notes:** Selected via --auto default.

---

## the agent's Discretion

None

## Deferred Ideas

None