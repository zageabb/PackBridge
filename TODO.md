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
- [ ] Verify the exact SSD workbook structure and create the canonical → SSD mapping specification. *(workbook reverse engineering and safe direct package mappings complete; remaining project/item mappings pending)*
- [ ] Confirm whether generated XLSX without macros is accepted by the SAP import process.
- [x] Decide initial supported source file types for v0.1.
- [x] Select initial Ollama model for baseline testing.
- [ ] Define initial acceptance criteria and benchmark documents.

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
- [ ] Implement PDF page rendering for source verification.
- [ ] Implement table/row extraction strategy.
- [x] Add DOCX source extraction.
- [x] Add XLSX/XLSM source extraction where needed.
- [ ] Add optional local OCR/vision path for scanned documents.
- [x] Store page/section/table evidence metadata.
- [ ] Show visible processing progress steps.

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
- [ ] Parse/validate structured YAML/JSON rule blocks.
- [x] Select only relevant knowledge for each prompt.
- [ ] Support approved few-shot examples.
- [x] Add Knowledge browser/editor. *(governed proposal/approval editing implemented)*
- [ ] Add validation before activating changed knowledge. *(Markdown safety/content validation implemented; structured YAML/JSON rule validation still pending)*
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
- [ ] Answer structured shipment questions through application tools/data.
- [x] Add assistant-proposed data changes with Apply/Cancel.
- [x] Add assistant-generated clarification questions during processing.
- [x] Persist job chat.
- [ ] Add reprocess field/case actions.
- [x] Ensure the assistant cannot directly mutate the SSD workbook.

## Phase 8 — Learning

- [ ] Detect unrecognised/new document layouts.
- [ ] Let user resolve unknown mappings.
- [x] Propose additions to vendor/document Knowledge.
- [ ] Default correction scope to current document only.
- [ ] Allow explicit "apply to profile" approval.
- [ ] Version Knowledge profile changes.
- [x] Keep knowledge change audit history.
- [ ] Generate profile/examples from an approved new-document learning session.
- [x] Add compare/diff view before approving Knowledge changes.

## Phase 9 — SSD generator

- [x] Add SSD/project aggregation to support assembling multiple packing-list jobs into one workbook.
- [x] Add structural SSD template inspection and controlled template installation.

- [x] Inspect and document reference SSD workbook structure.
- [ ] Establish approved clean SSD template. *(controlled cleaner/derivation implemented; live approved template still needs deployment/acceptance)*
- [x] Implement template version management.
- [ ] Implement deterministic canonical → SSD mapping. *(verified SoCs package/project mapping implemented; detailed PL/ML item mapping still pending)*
- [x] Write only permitted values/locations.
- [x] Preserve required formatting/formulas/validations/named structures.
- [ ] Generate XLSX without macros if SAP validation confirms this is acceptable.
- [x] Run post-generation workbook structural checks.
- [x] Store output metadata/hash with SSD project.
- [ ] Provide final production download only after generation checks pass. *(verified validation-workbook download implemented; SAP approval still pending)*

## Phase 10 — Audit, security and production readiness

- [x] Add job audit timeline.
- [x] Record model/version used.
- [x] Record knowledge/profile version.
- [x] Record template version.
- [x] Record every user/assistant-approved change.
- [ ] Add user authentication if required for production deployment.
- [ ] Add role/permission design for edit/approve/knowledge administration.
- [ ] Define file-retention policy.
- [ ] Add backup/restore process.
- [ ] Add application logging.
- [x] Add health checks.
- [ ] Add automated deployment consistent with local Ubuntu environment. *(5085 is now the PackBridge application port; systemd/UDA deployment package prepared, live registration still pending)*
- [ ] Create production handover guide.

## Phase 11 — Testing and benchmark

- [ ] Build golden test set from multiple packing-list formats.
- [ ] Add expected canonical JSON for each test document.
- [x] Add continuation-page regression tests.
- [x] Add source-vs-working edit tests.
- [x] Add validation tests.
- [x] Add SSD structure regression tests.
- [ ] Benchmark 14B baseline.
- [ ] Benchmark 7B candidate against same tests.
- [ ] Measure extraction accuracy, package grouping, line-item accuracy and latency.
- [ ] Decide smallest acceptable production model based on measured results.
