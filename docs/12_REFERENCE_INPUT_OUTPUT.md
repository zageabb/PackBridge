# Reference Input and Output

## Purpose

This document records the first business example used to design PackBridge. It is descriptive design context, not a permanent vendor-specific parser specification.

## Initial source

Reference source file used during design:

`890170033_10_Completed.pdf`

Observed characteristics discussed during design:

- packing-list date and sales/order information;
- case/package numbers;
- product type and item description;
- HS code;
- dimensions;
- volume;
- gross/net weight;
- package type/description;
- internal reference;
- packing status/user/date;
- line items with item number, description, quantity and UOM;
- some cases continue onto a second page;
- the package/case identifier, rather than page number, is the grouping key.

The production application must not assume all internal vendor documents use this layout.

## Initial target

Reference target file used during design:

`SSD test HV QBANK - Copy.xlsm`

Business requirement:

- output format is critical because the file is used for SAP import;
- macros are not required for the generated file;
- user wants a Virtual SSD representation in the browser;
- users may edit extracted values before generating the real SSD.

## Important implementation note

Before coding the final SSD writer, formally inspect and document the exact workbook structures that SAP relies upon.

Do not treat design-conversation assumptions as verified workbook mappings.

The verified mapping should be recorded in the structured SSD output rules and protected with regression tests.

## End-to-end interpretation

```text
Original packing list
        ↓
Generic local mapper + Knowledge
        ↓
Source extraction
        ↓
Virtual SSD working data
        ↓
User review / correction
        ↓
Approved snapshot
        ↓
Deterministic SSD template writer
        ↓
SAP-compatible workbook
```
