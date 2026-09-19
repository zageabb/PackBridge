# Development Status

## Status

**Source development is complete for the currently verified PackBridge scope.**

PackBridge is a runnable local-first Flask/Python application designed for port **5085**, with the full packing-list → canonical data → Virtual SSD → controlled SSD-output workflow implemented.

Remaining unchecked work is external acceptance/live qualification rather than unfinished source development. See `docs/19_EXTERNAL_ACCEPTANCE_CHECKLIST.md`.

## Implemented application flow

### Local document intake

- drag/drop and file-picker upload;
- original file retained unchanged with SHA-256;
- digital PDF extraction with page locators and table recognition;
- PDF page rendering beside source evidence;
- DOCX, XLSX/XLSM, CSV, TXT and Markdown extraction;
- optional fully local Tesseract OCR fallback for scanned PDFs;
- Office-container/file-size safety limits;
- retained page/sheet/table evidence locators.

### Generic local mapper

- local Ollama only;
- baseline model `qwen3:14b`;
- typed JSON/Pydantic output validation;
- temperature-zero bounded Ollama client;
- deterministic vendor/document-profile matching;
- document-driven Knowledge context;
- staged/chunked mapping for larger documents;
- deterministic merge of repeated cases/continuation pages;
- conflict warnings rather than silent overwrite;
- source/working provenance for every mapped value;
- deterministic post-mapping validation.

### Virtual SSD

- shipment/package summary and case navigation;
- editable package and item values;
- immutable source evidence vs working values;
- direct source-page verification popup;
- field/case/job revert;
- field/case reprocessing from retained evidence;
- protection before discarding manual edits;
- SSD project/default context and case-specific overrides;
- Issues / Source / Output Preview / Audit views;
- warning acknowledgement/reopen with audit.

### Context-aware assistant

- persistent job-scoped local chat;
- selected case/current working data context;
- retained source-evidence grounding;
- deterministic validation explanations;
- deterministic data queries for counts, filtering, totals, changed values and issues;
- reviewable assistant-proposed edits with Apply/Cancel;
- clarification-question workflow;
- no direct SSD workbook mutation by the LLM.

### Knowledge and Learning

- system and vendor/document Markdown Knowledge;
- validated structured PackBridge YAML/JSON blocks;
- deterministic profile matching and profile fingerprints;
- versioned vendor profiles;
- governed edit/new/import proposals;
- diff review plus approve/reject;
- approved correction examples retained in the active profile;
- field-correction → profile-learning proposal;
- local-AI draft profile for previously unrecognised layouts;
- remote Markdown download/import support;
- job audit links to Knowledge changes.

### SSD Projects and output

- aggregate multiple mapped packing-list jobs into one SSD Project;
- preserve per-job source identity and canonical PO/position;
- duplicate-case and 68-row capacity protection;
- verified SoCs project/default and package mappings;
- controlled SSD template inspection, cleaning and versioning;
- VBA-preserving OOXML writer for controlled XLSM templates;
- macro-free XLSX-capable path behind an explicit acceptance gate;
- formula/validation/named-structure preservation;
- reopen generated workbook and verify structural fingerprint;
- compare every explicitly written cell against approved preview;
- output SHA-256, template SHA-256, structural fingerprint and write counts;
- validation workbook download;
- production generation/download path that remains locked until external SAP release flags are enabled.

Physical PL/ML cell mapping is **not guessed**. The current verified evidence shows these sheets are document-generation artefacts, but it has not established that PackBridge must recreate them for SAP import. If SAP acceptance proves they are required, a verified workbook/cell mapping becomes a new evidence-backed scope.

### Security and production operations

- optional local authentication using an external password-hash user file;
- viewer / processor / approver / knowledge_admin / admin roles;
- route-level capability enforcement;
- SQLite/Alembic migrations;
- rotating application logs;
- health and readiness endpoints;
- SQLite-safe backup plus archive inspection/offline restore;
- opt-in operational/backup retention (automatic deletion disabled by default);
- daily backup and weekly retention systemd examples;
- Ubuntu user-systemd service;
- port 5085 deployment configuration;
- Universal Deployment Agent monitor-only source registration;
- production handover/recovery documentation.

### Testing and model qualification

- automated pytest suite and GitHub Actions;
- ingestion/table/PDF-render/OCR configuration tests;
- mapping/continuation/working-data/reprocess tests;
- Knowledge governance/learning tests;
- assistant/evidence/data-query tests;
- validation/acknowledgement tests;
- SSD preview/template/cleaner/writer/aggregation regression tests;
- authentication and operations tests;
- benchmark-scoring tests;
- three non-sensitive golden document layouts plus the HE continuation regression;
- CLI benchmark runner and 14B-vs-candidate comparison gate.

Acceptance thresholds and benchmark rules are in `docs/17_ACCEPTANCE_AND_BENCHMARK.md`.

## External qualification still required

The following cannot be truthfully completed by source-code changes alone:

1. first live Ubuntu deployment/manual health check on port 5085;
2. live installation/business approval of the controlled clean SSD template;
3. real HE reference run through `qwen3:14b` and review against source evidence;
4. actual SAP import acceptance;
5. decision whether SAP needs only the verified SoCs dataset or also PackBridge-created PL/ML sheets;
6. actual macro-free XLSX SAP acceptance;
7. live-host 14B/8B benchmark runs and final production-model choice;
8. production-owner decisions for non-zero retention and auto-deployment;
9. backup/restore drill.

These items and the release flags they control are documented in `docs/19_EXTERNAL_ACCEPTANCE_CHECKLIST.md`.

## Production release flags

All are intentionally disabled by default:

~~~text
PACKBRIDGE_SAP_OUTPUT_APPROVED=0
PACKBRIDGE_SAP_SOCS_ONLY_APPROVED=0
PACKBRIDGE_SAP_MACRO_FREE_APPROVED=0
~~~

Changing these values is an acceptance decision, not a development shortcut.

## Current safe baseline

- Port: **5085**
- Mapper: **qwen3:14b**
- OCR: off unless local Tesseract is explicitly enabled
- Authentication: off by default for trusted development; implemented for production
- Retention deletion: disabled until non-zero policies are agreed
- UDA: monitor-only first deployment
- Production SSD: release-gated until SAP/business acceptance
