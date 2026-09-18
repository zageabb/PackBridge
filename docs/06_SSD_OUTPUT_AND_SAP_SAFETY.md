# SSD Output and SAP Safety

## Critical requirement

The final SSD format is used downstream for SAP import. Format integrity is therefore more important than convenience.

The LLM must never directly author the final workbook.

## Output boundary

```mermaid
flowchart LR
    A[LLM Mapping] --> B[Canonical JSON]
    B --> C[Working / Approved Data]
    C --> D[Validation]
    D --> E[Deterministic Python SSD Writer]
    E --> F[Controlled SSD Workbook]
    F --> G[Structural Verification]
    G --> H[SAP]
```

The AI boundary ends before workbook generation.

## Template strategy

Use an approved SSD workbook as the output template.

Application code should modify only approved data locations.

Preserve, as required:

- sheet names;
- sheet order;
- row/column structure;
- formulas;
- number formats;
- validation lists;
- named ranges;
- hidden sheets;
- table structures;
- cell types;
- formatting required by import or operations.

Macros are not required for the current design. The target may therefore be generated as XLSX if testing confirms that SAP accepts the same required workbook structure without VBA.

## Never regenerate the SSD layout from an LLM description

Do not ask the model to:

- decide column locations;
- invent missing columns;
- rename fields;
- add sheets;
- reorder worksheets;
- create formulas;
- determine data types;
- create the final workbook from scratch.

## SSD mapping specification

The exact canonical-field → SSD-cell/column mapping must be documented in structured rules after the reference workbook is formally inspected.

Example only:

```yaml
ssd_mapping:
  package.case_number:
    sheet: "<verified sheet>"
    target: "<verified column/range>"
    type: text

  package.gross_weight:
    sheet: "<verified sheet>"
    target: "<verified column/range>"
    type: decimal
    unit: KG
```

Do not activate example mappings until verified against the real template.

## Virtual SSD

The browser Virtual SSD is the user-facing preview of the approved data, not an editable embedded Excel workbook.

Benefits:

- clearer review;
- safer editing;
- simple provenance indicators;
- responsive validation;
- source comparison;
- no risk of users accidentally changing workbook structure.

## Pre-generation checks

Before enabling normal generation:

- all blocking required fields present;
- no unresolved ambiguous mappings;
- numeric/unit validation complete;
- project/default values resolved;
- output row counts make sense;
- approved template available and version recognised.

## Post-generation checks

After writing:

- workbook opens successfully;
- expected sheets exist;
- required sheet names/order unchanged;
- expected named structures remain;
- permitted cells contain approved values;
- no accidental extra rows/columns/sheets;
- data types are correct;
- no formula/reference errors introduced;
- output hash/version information recorded with the job.

## Template versioning

Store template identity/version with every generated job.

If a new SSD version is introduced, keep old template support where practical so historical jobs remain reproducible.
