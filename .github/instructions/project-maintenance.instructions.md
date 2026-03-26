---
description: "Project maintenance guardrails for cleanup, validation, and release packaging"
applyTo: "**"
---

# Project Maintenance

## Goal

Keep the repository clean, the data pipeline validated, and desktop packaging reproducible.

## Pre-Release Checklist

- Install dependencies:
  - `python -m pip install -r requirements.txt`
- Run automated tests:
  - `python -m pytest tests -q`
- Build executable from the committed spec:
  - `python -m PyInstaller --clean --noconfirm GamefyDB.spec`

## Cleanup Guidance

- Do not commit generated outputs from `build/` and `dist/`.
- Do not commit local runtime databases (`*.db`, `*.sqlite3`).
- Prefer removing transient files after local validation runs.

## Documentation Sync Rules

When changing pipeline behavior or packaging flow:

- Update `README.md` usage/build sections.
- Update `docs/project-workflow.md` for runtime/build workflow.
- Update `AGENTS.md` stack/workflow notes if tooling changes.

## Data Pipeline Safety

- Keep report type detection filename-based unless explicitly redesigning schemas.
- Preserve rerun-safe behavior by `source_file` replacement in orchestrator.
- Ensure new extraction paths still return the extractor contract:
  - `(record_type, list[dict])`

## Release Quality Bar

A change is release-ready only if:

- Tests pass in the project environment.
- CLI workflow runs successfully against fixture data.
- Executable build completes without errors.
