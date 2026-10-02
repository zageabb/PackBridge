# Development Status

Last reviewed: 2026-10-02
Current development state: ACTIVE

## Purpose
Common development ledger for the user and AI agents. Existing project-specific planning documents remain valid; this file standardises status and completion evidence.

## Current objective
Document-processing, canonical working data, local-LLM mapping, SSD generation and production acceptance.

## Existing planning and evidence sources
- `TODO.md`
- `docs/ROADMAP.md`
- `docs/15_DEVELOPMENT_STATUS.md`
- `docs/17_ACCEPTANCE_AND_BENCHMARK.md`
- `docs/19_EXTERNAL_ACCEPTANCE_CHECKLIST.md`
- `tests/`
- `GitHub Actions`

## Status values
- 🔵 PLANNED
- 🔨 IN PROGRESS
- 🚫 BLOCKED
- ⏳ AWAITING ACCEPTANCE
- ✅ COMPLETE
- 💤 DEFERRED

## Evidence standard
An item is COMPLETE only when applicable repository evidence verifies it: implementation, changed files/non-empty diff, tests or recorded no-test reason, passing tests, CI where available, commit/PR evidence, intended-branch merge, and separately recorded external/user acceptance.

For coding work, an empty result, no write/edit action, unchanged branch HEAD, empty diff or missing requested validation means the task is not complete.

## Development ledger

### DEV-000 — Establish evidence-based development ledger
Status: ✅ COMPLETE

Evidence:
- Files: `DEVELOPMENT.md`, `AGENTS.md`
- Git history records these changes.
- Tests: not required for this documentation/process-only change.
- User acceptance: requested 2026-10-02.

## Existing backlog/history

Use the project-specific files listed above for historical and detailed backlog entries. New meaningful development should also receive a DEV entry here so status and evidence are visible consistently across repositories.

## New item template

### DEV-XXX — Short title
Status: 🔵 PLANNED
Priority: Medium

Requirement:

Implementation:

Evidence:
- Commit:
- PR:
- Files:
- Tests:
- CI:
- Merged to intended branch:
- User/business acceptance:

Completion criteria:
- [ ] Implementation exists.
- [ ] Relevant files changed.
- [ ] Tests added/updated, or reason recorded.
- [ ] Relevant tests pass.
- [ ] CI passes where applicable.
- [ ] Commit/PR evidence recorded.
- [ ] Merged where required.
- [ ] External/user acceptance separated from development completion.

Notes:

## Maintenance rule
Update this file during the same development pass that changes implementation. Repository evidence wins when prose disagrees.
