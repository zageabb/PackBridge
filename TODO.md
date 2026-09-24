# PackBridge TODO

This is the working implementation backlog. Keep it updated as features are completed or design decisions change.

## Phase 0 — Foundation and documentation

- [x] Name application PackBridge.
- [x] Define product purpose and core principles.
- [x] Document two-panel UI concept.
- [x] Document Virtual SSD concept.
- [x] Document generic local-LLM mapping architecture.
- [x] Document document-driven Knowledge approach.
- [x] Document editable working data with immutable source evidence.
- [x] Document deterministic SSD-generation boundary.
- [x] Verify the SSD workbook structure and implement the deterministic mapping for the verified SAP-import candidate scope. *(SoCs package/project mapping is implemented and documented; PL/ML physical item-sheet mapping is deliberately conditional on SAP acceptance proving those sheets are required.)*
- [x] Implement the macro-free XLSX-capable output path behind an explicit SAP acceptance gate. *(Actual SAP acceptance remains an external qualification task below.)*
- [x] Decide initial supported source file types for v0.1.
- [x] Select initial Ollama model for baseline testing.
- [x] Define acceptance criteria, quality gates and controlled benchmark documents.

## Phase 1 — Application shell

- [x] Create Flask application skeleton.
- [x] Add configuration management and `.env.example`.
- [x] Add SQLite database initialisation/migrations.
- [x] Create job/workspace model.
- [x] Create file-storage layout for source, working artefacts and outputs.
- [x] Add basic top navigation: Jobs / Knowledge / Settings.
- [x] Build two-panel responsive workspace.
- [x] Make assistant panel collapsible/resizable.
- [x] Add diagnostics page for Ollama connection/model status.

## Phase 2 — Upload and document ingestion

- [x] Add drag/drop and file-picker upload.
- [x] Store original source file unchanged.
- [x] Implement digital PDF text extraction.
- [x] Implement PDF page rendering for source verification.
- [x] Implement table/row extraction strategy.
- [x] Add DOCX source extraction.
- [x] Add XLSX/XLSM source extraction where needed.
- [x] Add optional fully local Tesseract OCR fallback for scanned PDFs.
- [x] Store page/section/table evidence metadata.
- [x] Show visible processing progress steps.

## Phase 3 — Canonical schema and mapper

- [x] Implement canonical PackingList model.
- [x] Implement provenance-aware field values: source vs working.
- [x] Implement package/case model.
- [x] Implement item model.
- [x] Implement issues/status model.
- [x] Load canonical schema from Knowledge.
- [x] Build generic Ollama mapper service.
- [x] Require structured JSON output.
- [x] Enforce null for absent values.
- [x] Capture source evidence.
- [x] Support package continuation across pages.
- [x] Add staged/chunked processing for large documents.
- [x] Preserve manual edits on safe reprocessing or explicitly warn before overwrite.

## Phase 4 — Knowledge loader and profiles

- [x] Load `knowledge/system/*.md`.
- [x] Load vendor/document-profile Markdown.
- [x] Add profile matching using deterministic document indicators.
- [x] Add document-profile/version metadata.
- [x] Parse/validate structured YAML/JSON rule blocks.
- [x] Select only relevant knowledge for each prompt.
- [x] Support approved few-shot examples. *(approved learned examples live inside the active profile and are explicitly injected into mapper context)*
- [x] Add Knowledge browser/editor. *(governed proposal/approval editing implemented)*
- [x] Add validation before activating changed knowledge.
- [x] Add import/export/replace workflow for remote support.

## Phase 5 — Virtual SSD

- [x] Add SSD project/default context separate from source evidence.
- [x] Add case-specific SSD output overrides that inherit job defaults.

- [x] Create Summary tab.
- [x] Create case tabs / searchable case selector.
- [x] Create editable SSD-style field layout.
- [x] Create editable item grid.
- [x] Add origin indicators: source / modified / calculated / project-default / issue.
- [x] Show original/source value for modified fields.
- [x] Add field-level revert.
- [x] Add case-level revert.
- [x] Add job-level revert.
- [x] Add Previous/Next case navigation.
- [x] Add Issues tab.
- [x] Add Source tab.
- [x] Add Output Preview tab.
- [x] Add source-verification popup with source page next to Virtual SSD data.

## Phase 6 — Validation

- [x] Implement gross >= net weight rule with override support.
- [x] Validate dimensions and units.
- [x] Validate package identifiers and duplicates.
- [x] Validate continuation-page grouping.
- [x] Validate item quantities/UOMs.
- [x] Validate required SSD fields.
- [x] Add INFO/WARNING/BLOCKING severities.
- [x] Revalidate immediately after working-data edits.
- [x] Add warning acknowledgement/override audit where appropriate.
- [x] Prevent normal generation while unresolved blocking issues remain.

## Phase 7 — Context-aware assistant

- [x] Add job-scoped chat.
- [x] Pass selected case/field as assistant context.
- [x] Allow "where did this come from?" evidence queries.
- [x] Explain validation failures.
- [x] Answer structured shipment questions through application tools/data.
- [x] Add assistant-proposed data changes with Apply/Cancel.
- [x] Add assistant-generated clarification questions during processing.
- [x] Persist job chat.
- [x] Add field/case reprocessing from retained source evidence with manual-edit protection.
- [x] Ensure the assistant cannot directly mutate the SSD workbook.

## Phase 8 — Learning

- [x] Detect unrecognised/new document layouts.
- [x] Let user resolve unknown mappings. *(ambiguous mappings are surfaced as warnings and resolved through working-data edits)*
- [x] Propose additions to vendor/document Knowledge.
- [x] Default correction scope to current document only.
- [x] Allow explicit "apply to profile" approval. *(corrected fields can create a profile-learning proposal; Knowledge approval is separate)*
- [x] Version Knowledge profile changes.
- [x] Keep knowledge change audit history.
- [x] Generate profile/examples from an approved new-document learning session. *(unrecognised jobs can draft a review-only local-AI profile proposal)*
- [x] Add compare/diff view before approving Knowledge changes.

## Phase 9 — SSD generator

- [x] Add SSD/project aggregation to support assembling multiple packing-list jobs into one workbook.
- [x] Add structural SSD template inspection and controlled template installation.

- [x] Inspect and document reference SSD workbook structure.
- [x] Implement controlled template installation, structural inspection, cleaner/derivation and versioned activation. *(Live business approval of the selected template remains external.)*
- [x] Implement template version management.
- [x] Implement deterministic canonical → SSD mapping for every physically verified SoCs field and approved project/default context. *(No unverified PL/ML cell mapping is guessed.)*
- [x] Write only permitted values/locations.
- [x] Preserve required formulas/validations/named structures while allowing non-critical presentation formatting to vary.
- [x] Dynamically expand SoCs Table2 and validation ranges beyond the source template package capacity.
- [x] Deterministically clone PLs_Temp / MLs_Temp into per-case PL-/ML- worksheets without invoking VBA.
- [x] Support macro-free generation when a compatible XLSX template is installed and the explicit SAP macro-free release gate is enabled.
- [x] Run post-generation workbook structural checks.
- [x] Store output metadata/hash with SSD project.
- [x] Provide gated production SSD generation/download only after preview, template, structural and value checks pass and external SAP release flags are enabled.

## Phase 10 — Audit, security and production readiness

- [x] Add job audit timeline.
- [x] Record model/version used.
- [x] Record knowledge/profile version.
- [x] Record template version.
- [x] Record every user/assistant-approved change.
- [x] Add optional local authentication with external password-hash user store.
- [x] Add centrally enforced viewer / processor / approver / knowledge_admin / admin roles.
- [x] Implement configurable operational/backup retention policy and cleanup commands; destructive retention is disabled by default until the production owner chooses periods.
- [x] Add SQLite-safe operational backup, inspection, offline restore and optional systemd backup timer.
- [x] Add rotating application logging plus systemd/journal operational guidance.
- [x] Add health checks.
- [x] Add Ubuntu systemd deployment, migrations, health checks, port 5085 and monitor-only Universal Deployment Agent source registration. *(First live-host activation remains external.)*
- [x] Create production handover, recovery, access, backup, retention and release-gate guide.

## Phase 11 — Testing and benchmark

- [x] Build a controlled multi-layout golden benchmark set plus the HE continuation regression fixture.
- [x] Add expected canonical JSON for the controlled golden benchmark documents.
- [x] Add continuation-page regression tests.
- [x] Add source-vs-working edit tests.
- [x] Add validation tests.
- [x] Add SSD structure regression tests.
- [x] Add repeatable qwen3:14b baseline benchmark command/reporting.
- [x] Add same-test qwen3:8b/candidate benchmark command and comparison gate.
- [x] Implement repeatable benchmark measurement/reporting for structured validity, package grouping, fields, line items, null preservation and latency.
- [x] Define the smallest-model acceptance rule; live-host measured results determine whether the configured baseline is changed.


## External acceptance / live qualification

These are not unfinished application-development items. They require the live Ubuntu host, a production-owner decision or the real SAP/business process. See `docs/19_EXTERNAL_ACCEPTANCE_CHECKLIST.md`.

- [ ] Recheck port 5085 and complete the first manual Ubuntu deployment/health check.
- [ ] Install and business-approve the clean controlled SSD generation template on the live host.
- [ ] Run the real HE reference packing list through `qwen3:14b` and confirm the expected 17-case result against source evidence.
- [ ] Run an actual SAP import acceptance test with a PackBridge validation workbook.
- [ ] Confirm whether the SAP import requires only the verified SoCs dataset or also requires PackBridge to recreate physical PL/ML item sheets.
- [ ] If SoCs-only is accepted, enable `PACKBRIDGE_SAP_OUTPUT_APPROVED=1` and `PACKBRIDGE_SAP_SOCS_ONLY_APPROVED=1`.
- [ ] Test macro-free XLSX with SAP; enable `PACKBRIDGE_SAP_MACRO_FREE_APPROVED=1` only if accepted.
- [ ] Run the 14B and 8B benchmark commands on the deployment host, record RAM/VRAM/latency, and choose the smallest model that passes the documented quality gate.
- [ ] Agree non-zero operational/backup retention periods if automatic deletion is desired.
- [ ] Perform a production backup/restore drill.
- [ ] After a successful manual deployment cycle, decide whether to change the live UDA entry from monitor-only to automatic deployment.
