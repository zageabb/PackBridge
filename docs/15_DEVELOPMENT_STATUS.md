# Development Status

## Current state

PackBridge is in active application development with a runnable Flask/Python application, verified reference-document regression knowledge and a guarded SSD validation-output path.

The selected local deployment port is **5085**.

## Implemented

### Application shell and deployment packaging

- Flask application factory
- SQLite/SQLAlchemy operational models
- Jobs / SSD Projects / Knowledge / Settings navigation
- managed source/working/output storage layout
- responsive two-panel job workspace
- collapsible/resizable local assistant
- Ollama settings/model discovery
- health/readiness endpoints
- user-systemd example for port 5085
- Universal Deployment Agent registry fragment
- external operational data/template paths in deployment examples

The deployment package is prepared but has not been registered on the live Ubuntu host from this chat.

### Document ingestion

- drag/drop and file-picker upload
- retained original source file with SHA-256
- PDF text extraction with page locators
- DOCX paragraph/heading/table extraction
- XLSX/XLSM worksheet extraction
- CSV/TXT/Markdown support
- Office-container safety checks and extraction limits
- stored source section locators

### Generic mapping

- local typed Ollama JSON client
- baseline model `qwen3:14b`
- generic packing-list mapping prompt
- relevant vendor/document Knowledge context
- canonical source/working value model
- raw source evidence/locator support
- deterministic Knowledge-profile matching
- deterministic post-mapping validation
- deterministic continuation-page merge by Case Number
- conflict warnings rather than silent continuation overwrite
- regression test for 20 page records collapsing to the known 17 reference cases

### Knowledge

Initial Knowledge includes:

- canonical schema
- generic packing-list mapping rules
- validation rules
- SSD output safety rules
- initial Hitachi Energy QBANK reference profile

The vendor profile remains guidance to the generic mapper, not a separate parser.

A read-only Knowledge browser/search page is implemented. Governed editing, versioning and approval remain pending.

### Virtual SSD

The Virtual SSD is an editable working-data layer.

Implemented:

- shipment/package summary
- case tabs / selection
- Previous / Next case navigation
- package details
- dimensions/weights
- editable item grid
- immutable source vs editable working values
- source/modified indicators
- original source value shown for modified fields
- field/case/job revert
- immediate deterministic revalidation
- Issues / Source / Audit sections
- source-locator jump from the field editor
- separate SSD project/default output context
- case-specific SSD overrides that inherit the job defaults
- read-only proposed SoCs_Temp output preview

### Multi-job SSD Projects

A separate SSD Project workspace now supports the architecture shown by the reference workbook, where several packing-list positions feed one SSD.

Implemented:

- create SSD project
- attach/remove mapped packing-list jobs
- one job belongs to one SSD project
- package rows are aggregated in attachment order
- source job retained on every aggregated preview row
- duplicate Case Numbers across jobs are blocking
- 68-row SoCs template capacity is enforced
- project-level SSD header/default context
- each job retains its own canonical PO/position when project defaults are blank
- combined SoCs output preview

### SSD workbook reverse engineering

The reference packing list and reference SSD workbook were inspected directly.

Verified findings include:

- the PDF is 20 pages but represents 17 unique cases;
- cases 48366844, 48366845 and 48366846 continue onto a second page;
- the reference SSD contains 68 SoCs package rows across several positions;
- SoCs_Temp is the central package dataset;
- PLs_Temp and MLs_Temp are very-hidden templates;
- generated PL/ML sheets and VBA are part of the workbook's document-generation workflow;
- direct verified package mappings include dimensions, volume formula, net/gross weights and Case Number;
- a historical SSD row disagrees with the supplied source PDF, so the historical workbook is not treated as golden truth.

Detailed findings are in `docs/16_SSD_WORKBOOK_REVERSE_ENGINEERING.md`.

### Controlled SSD template management

Implemented:

- XLSM/XLSX structural inspector
- required worksheet/state checks
- Table2 `C22:W90` check
- verified SoCs header checks
- verified data-validation checks
- VBA presence detection
- file SHA-256 and structural fingerprint
- populated-template vs generation-ready distinction
- versioned template installation
- controlled cleaner that removes generated PL/ML sheets, clears SoCs input values, retains formulas/styles/validations/VBA and removes stale calc-chain/defined-name references
- post-clean structural reinspection

A live approved generation template still needs to be installed/accepted on the deployment host.

### Guarded validation SSD writer

The first deterministic writer is implemented for **validation output only**.

It:

- requires a clean structurally verified template;
- requires the macro-enabled template for the current path;
- refuses previews with blocking issues;
- writes only the verified SoCs header/package locations;
- never overwrites the volume formula column M;
- preserves the OOXML package and VBA project;
- reopens the generated workbook;
- checks the structural fingerprint;
- compares every explicitly written cell with the approved preview;
- records output SHA-256, template SHA, structure fingerprint and row/cell counts.

SSD Projects can build and download a clearly labelled **VALIDATION** workbook only when the combined preview has no warnings/blockers and the controlled template is generation-ready.

This is not yet the final production/SAP-approved Generate SSD action.

### Assistant

- job-scoped persistent chat
- current working data supplied as context
- selected case supplied as context
- local Ollama only
- collapsible/resizable panel
- assistant cannot directly write the SSD workbook

Assistant proposed data changes with explicit Apply/Cancel remain pending.

### Validation and audit

Current deterministic checks include:

- missing/duplicate package identifiers
- gross/net numeric checks
- gross below net warning
- incomplete/invalid dimensions
- item quantity/UOM checks
- continuation conflict checks
- SSD list-value checks
- SSD missing-context checks
- template capacity checks
- cross-job duplicate cases
- INFO/WARNING/BLOCKING severity

Audit history includes uploads, extraction, profile matching, mapping, working edits/reverts, assistant messages and SSD context changes.

### Automated tests

The pytest suite now covers:

- CSV/XLSX ingestion
- canonical normalisation
- deterministic validation
- Knowledge search
- Ollama request behaviour
- working-data edits/reverts
- document-profile matching
- continuation-page merging
- 20-page → 17-case reference regression
- SSD output preview and unit conversions
- SSD template structure validation
- controlled template cleaning
- guarded SoCs writer
- multi-job aggregation
- Flask route/template smoke tests

GitHub Actions is running these tests on every push. The test suite returned **success** after the writer-fixture correction on the current development line.

## Port

The application default, environment examples and deployment service use:

~~~text
5085
~~~

The live deployment agent inventory should only be amended after port 5085 is rechecked on the actual host and the service passes its first manual health check.

## Intentionally not implemented yet

- PDF page-image rendering / side-by-side visual source viewer
- local OCR/vision fallback
- staged mapper for very large documents
- assistant Apply/Cancel data-change proposals
- warning acknowledgement/override workflow
- Learning/Knowledge amendment approvals/versioning
- detailed PL/ML item-output mapping
- generated PL/ML sheet recreation by PackBridge itself
- final SAP-approved production output
- macro-free XLSX output
- live Ubuntu registration/deployment

## Next development slice

1. Deploy/run PackBridge on port 5085 with automatic deployment initially disabled.
2. Install the reference SSD workbook and derive the clean generation template through Settings.
3. Process the real reference HE packing list through `qwen3:14b` and compare its canonical result with the known 17-case regression.
4. Build a validation SSD and compare the position-10 SoCs rows against source/working data.
5. Add assistant proposed field changes with explicit Apply/Cancel.
6. Add governed Knowledge learning/versioning.
7. Define the remaining PL/ML item-level output rules.
8. Run an actual SAP acceptance test before enabling the final production Generate SSD path or any macro-free XLSX option.

## Current safety constraint

No final production mapping should be added from workbook appearance or naming alone.

Only fields verified from the reference workbook/business process should enter the deterministic writer. New mappings must be documented, tested and rechecked against source/working data before the production output path is enabled.
