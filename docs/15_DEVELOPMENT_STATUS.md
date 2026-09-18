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

A separate SSD project/default context layer has also been added so output-only values are not falsely attributed to the packing-list source.

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
- the remaining non-source/project canonical-to-SSD mappings
- multi-packing-list/project aggregation
- final SSD generation
- SAP import acceptance validation

## SSD reverse engineering completed in this slice

The reference packing list and reference SSD workbook were inspected directly.

Verified findings include:

- the PDF is 20 pages but represents 17 unique cases;
- cases 48366844, 48366845 and 48366846 continue onto a second page;
- the SSD workbook contains 68 SoCs package rows across several positions, so one packing list is only part of the complete SSD;
- SoCs_Temp is the central package dataset;
- PLs_Temp and MLs_Temp are very-hidden templates;
- the workbook contains generated PL/ML sheets and VBA that creates/refreshes them and produces PDFs;
- the first safe direct canonical mappings are dimensions, volume formula, net/gross weights and case number;
- at least one historical SSD row differs from the supplied source packing list, confirming that the historical workbook must not be treated as golden truth.

A controlled template inspector and versioned template installer are now implemented. It distinguishes structural compatibility from a clean generation template.

The job workspace now includes a deterministic read-only SoCs output preview and forms for SSD-specific project/default values.

## Next development slice

1. Deploy/run PackBridge on port 5085.
2. Process the real reference HE packing list through qwen3:14b and compare the mapped result against the known 17-case shape.
3. Add per-case SSD context overrides and project/workspace aggregation.
4. Add assistant proposed changes with explicit Apply/Cancel.
5. Build a controlled clean SSD template from the verified workbook structure.
6. Implement the first deterministic SoCs writer against a copied macro-enabled template.
7. Re-open and verify every generated value/structure before enabling the download button.
8. Test the resulting workbook through the actual SAP import before considering a macro-free XLSX path.

## Current design constraint

Do not implement the final SSD writer from assumptions. The workbook is SAP-sensitive and must be inspected, mapped and regression-tested before the output path becomes active.
