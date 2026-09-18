# Development Status

## Current state

PackBridge has moved from design into the first implementation slice.

The repository now contains a runnable Flask application skeleton plus the first reusable infrastructure adapted from existing applications.

## Implemented

### Application shell

- Flask application factory
- SQLite/SQLAlchemy operational models
- job/source/chat/audit records
- managed source/working/output storage layout
- local CSS/HTML application shell
- responsive two-panel job workspace
- collapsible right-hand local assistant
- Ollama settings/model discovery
- health/readiness endpoints

### Document ingestion

- PDF text extraction with page locators
- DOCX paragraph/heading/table extraction
- XLSX/XLSM worksheet extraction
- CSV/TXT/Markdown support
- file signature/Office container safety checks
- extraction size limits
- original-file SHA-256 and retained source copy

### Generic mapping

- local Ollama typed JSON client
- baseline model qwen3:14b
- generic packing-list mapping prompt
- vendor/document Knowledge context
- canonical source/working value model
- raw source evidence/locator support
- package and item structures
- continuation-page instruction
- deterministic post-mapping validation

### Knowledge

Initial document-driven Knowledge now includes:

- canonical schema
- generic packing-list mapping rules
- validation rules
- SSD output safety rules
- initial Hitachi Energy QBANK reference profile

The HE profile is guidance to the generic mapper, not a separate parser.

### Virtual SSD first slice

- shipment/package summary
- case selection
- package details
- dimensions/weights
- line-item display
- provenance indicator framework
- source extraction view
- final SSD button intentionally disabled until the mapping is verified

### Assistant first slice

- job-scoped persistent chat
- current job data supplied as context
- selected case supplied as context
- local Ollama only

### Automated tests

Initial tests cover:

- CSV/XLSX ingestion
- canonical normalisation
- deterministic validation
- Knowledge search
- Ollama request behaviour

A GitHub Actions pytest workflow has been added.

## Intentionally not implemented yet

The following are deliberately deferred until the first extraction/mapping loop is exercised against the real reference packing list:

- editable Virtual SSD values
- source-vs-working change/revert UI
- page-image PDF rendering
- profile auto-detection
- assistant Apply/Cancel change proposals
- Learning/Knowledge amendment workflow
- staged mapper for very large documents
- final canonical-to-SSD cell/range mapping
- final SSD generation
- SAP acceptance validation
- OCR/vision fallback

## Next development slice

1. Run the application on the Ubuntu host.
2. Upload the reference HE packing list.
3. Run qwen3:14b through the generic mapper.
4. Compare returned package count/values against the known 17-case reference.
5. Fix mapper/chunking/schema issues found by the real document.
6. Add editable working values and validation issue UI.
7. Inspect the SSD workbook formally and document its exact mapping before enabling generation.

## Current design constraint

Do not implement the final SSD writer based on assumptions from the design discussion. The workbook is SAP-sensitive and must be inspected and regression-tested before its mapping rules become active.
