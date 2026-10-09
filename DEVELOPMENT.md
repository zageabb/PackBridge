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

### OPS-UDA-001 — Reverse-proxy path compatibility
Status: 🔨 IN PROGRESS
Priority: High
Branch: `feat/uda-subpath-compatibility`
Requirement:
- Support UDA's `/apps/<slug>/` proxy paths while retaining direct local root-mode use, existing PackBridge authentication, and functional document processing.
Implementation:
- Flask one-hop ProxyFix to generate prefix-aware routes.
- Unique session cookie name, optional cookie path via `PACKBRIDGE_COOKIE_PATH` (deploy with `/apps/<slug>/` if public cookie isolation desired).
- Base URL for client-side API resolution, scoped fetch requests, and application redirects.
- Regression test covering prefixed and local routes.
Evidence:
- Code committed on migration branch; live UDA registry/public route unchanged.
- CI and deployed Caddy testing pending.
- No production UDA/public enablement performed.
Completion criteria:
- [ ] CI confirms tests pass and changes merge to main.
- [ ] Browser upload, streaming, redirect, logout and API flows validated in UDA.
- [ ] No direct backend exposure to untrusted forged headers.
- [ ] User acceptance separately recorded.


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
Owner/Agent:
Branch:
Depends on:
Can run in parallel with:
Integration status:

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

## Parallel development coordination

Use the coordination fields on every active DEV item when parallel work is possible.

- **Owner/Agent** — the person or AI agent currently responsible for the item.
- **Branch** — the working branch or worktree used for the item.
- **Depends on** — DEV items, decisions or external prerequisites that must complete first.
- **Can run in parallel with** — DEV items that are safe to develop concurrently without conflicting ownership or sequencing.
- **Integration status** — for example: not started, isolated, ready for integration, integrated, or integration blocked.

Before starting parallel work, agents should check these fields and avoid claiming the same item, branch or overlapping integration responsibility. If two items touch the same subsystem or files, record the conflict explicitly and sequence or coordinate integration rather than assuming they are independent.

Parallel execution does not weaken the completion standard: each DEV item still requires its own implementation, tests/validation, CI evidence where applicable, and integration/merge evidence before it can be marked COMPLETE.

## Maintenance rule
Update this file during the same development pass that changes implementation. Repository evidence wins when prose disagrees.
