# SSD Output Rules

## Status

The final canonical-to-SSD mapping is **not yet verified**. Do not infer workbook destinations from this document until the reference SSD workbook has been formally inspected and the mapping rules are approved.

## Safety boundary

The local LLM does not write the final SSD workbook.

The final workbook is generated only from approved Virtual SSD data by deterministic application code.

## Template rule

Use a controlled approved SSD template.

Preserve every workbook structure required by the SAP import, including where applicable:

- worksheet names;
- worksheet order;
- hidden worksheets;
- formulas;
- named ranges;
- table definitions;
- number formats;
- data-validation lists;
- required blank cells;
- column/row positions;
- expected data types.

## Allowed mutations

Normal SSD generation should expose only explicit approved field mappings.

Do not expose generic workbook operations such as add worksheet, delete worksheet, rename worksheet, insert arbitrary columns, remove arbitrary rows, change formatting or create formulas.

Those generic primitives may exist internally for inspection/testing but are outside the normal output path.

## Macros

Macros are not required for the current business process.

Target output may be XLSX if controlled testing proves that SAP accepts the macro-free workbook while all required structures remain intact.

## Verification

Before release of a generated SSD:

1. verify template/version identity;
2. write approved data;
3. reopen the generated workbook;
4. verify required worksheets/structures;
5. compare structural fingerprint against the template;
6. verify only allowed locations changed;
7. record output/template version in the job audit.

## Mapping definition

The verified mapping should eventually be recorded in a structured YAML block with canonical field, sheet, target, data type and unit.

No placeholder mapping in this document is active configuration.
