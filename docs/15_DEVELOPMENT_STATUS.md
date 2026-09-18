# Development Status

## Current state

PackBridge is now in active application development. The repository contains a runnable Flask/Python application and the second development slice has been implemented.

The selected local deployment port is **5085**.

## Implemented

### Application shell

- Flask application factory
- SQLite/SQLAlchemy operational models
- job/source/chat/audit records
- managed source/working/output storage layout
- Jobs / Knowledge / Settings navigation
- responsive two-panel job workspace
- collapsible and resizable right-hand local assistant
- Ollama settings/model discovery
- health/readiness endpoints

### Document ingestion

- drag/drop and file-picker upload
- retained original source file with SHA-256
- PDF text extraction with page locators
- DOCX paragraph/heading/table extraction
- XLSX/XLSM worksheet extraction
- CSV/TXT/Markdown support
- file signature/Office container safety checks
- extraction size limits
- stored source section locators

### Generic mapping

- local Ollama typed JSON client
- baseline model `qwen3:14b`
- generic packing-list mapping prompt
- vendor/document Knowledge context
- canonical source/working value model
- raw source evidence/locator support
- package and item structures
- continuation-page instruction
- deterministic post-mapping validation
- deterministic Knowledge-profile matching before mapping

### Knowledge

Initial document-driven Knowledge includes:

- canonical schema
- generic packing-list mapping rules
- validation rules
- SSD output safety rules
- initial Hitachi Energy QBANK reference profile

The HE profile remains guidance to the generic mapper, not a separate parser.

A read-only Knowledge browser and search page are now available. Governed Knowledge editing/approval is still pending.

### Virtual SSD

The Virtual SSD is now an editable working-data layer rather than display-only.

Implemented:

- shipment/package summary
- case tabs / selection
- Previous / Next case navigation
- package details
- dimensions/weights
- editable item grid
- source / working value separation
- modified-value indicators
- original source value shown for modified fields
- field-level revert
- case-level revert
- whole-job revert
- immediate deterministic revalidation after edits
- Issues section with INFO / WARNING / BLOCKING counts
- Source section
- audit timeline

The source evidence is never overwritten by a user edit.

### Assistant

- job-scoped persistent chat
- current working data supplied as context
- selected case supplied as context
- local Ollama only
- collapsible/resizable panel
- assistant remains unable to write the final SSD workbook

Assistant Apply/Cancel change proposals are still a later slice.

### Validation

Current deterministic checks include:

- missing/duplicate package identifiers
- gross/net numeric checks
- gross below net warning
- incomplete/invalid dimensions
- item quantity checks
- quantity without UOM
- issue severity counts

Validation runs after initial mapping and after every working-data change/revert.

### Audit

The job workspace now shows an append-oriented audit timeline for:

- uploads
- extraction
- profile matching
- mapping
- working-field edits
- field/case/job reverts
- assistant messages

The mapping event records the local model used.

### Automated tests

Tests now cover:

- CSV/XLSX ingestion
- canonical normalisation
- deterministic validation
- Knowledge search
- Ollama request behaviour
- working-data edits/reverts
- deterministic document-profile matching

A GitHub Actions pytest workflow exists, but a workflow execution result has not yet been observed through the connected GitHub interface.

## Port

The application default and `.env.example` now use:

```text
5085
```

The deployment agent's live port inventory should only be amended once PackBridge is actually deployed and verified on the host.

## Intentionally not implemented yet

The following remain deliberately deferred:

- PDF page-image rendering / side-by-side source popup
- local OCR/vision fallback
- staged mapper for very large documents
- assistant Apply/Cancel data-change proposals
- warning override/acknowledgement workflow
- Learning/Knowledge amendment approvals and versioning
- final canonical-to-SSD cell/range mapping
- final SSD generation
- SAP import acceptance validation

## Next development slice

1. Deploy/run PackBridge on port 5085.
2. Upload the real reference HE packing list.
3. Run `qwen3:14b` through the generic mapper.
4. Compare the result against the expected 17-case reference and continuation-page behaviour.
5. Fix any real-document extraction/mapping issues.
6. Add source-verification navigation/popups and clarification handling.
7. Add assistant proposed changes with explicit Apply/Cancel.
8. Formally inspect the SSD workbook and define the deterministic output mapping before enabling generation.

## Current design constraint

Do not implement the final SSD writer from assumptions. The workbook is SAP-sensitive and must be inspected, mapped and regression-tested before the output path becomes active.
