# SSD Workbook Reverse Engineering

## Scope

This note records what has been verified from the reference workbook **SSD test HV QBANK - Copy.xlsm** and the reference position-10 packing list.

The objective is to define PackBridge's deterministic output boundary from evidence rather than assumptions.

## Key conclusion

The SSD workbook is **not** a simple flat import sheet.

Its architecture is:

1. **SoCs_Temp** — the central case/shipment dataset.
2. **PLs_Temp** — a very-hidden Packing List template.
3. generated **PL-<case number>** sheets.
4. **MLs_Temp** — a very-hidden Marking Label template.
5. generated **ML-<case number>** sheets.
6. VBA that creates/deletes the per-case PL/ML sheets and creates PDFs.

The reference workbook contains:

- 139 worksheets in total;
- 1 visible SoCs_Temp sheet;
- 1 very-hidden PLs_Temp sheet;
- 68 generated PL sheets;
- 1 very-hidden MLs_Temp sheet;
- 68 generated ML sheets;
- an embedded VBA project.

The VBA is therefore part of the workbook's document-generation workflow, even if it ultimately proves unnecessary for the SAP data import itself.

## Reference packing-list relationship

The supplied reference PDF for sales order 890170033 position 10 contains:

- 20 PDF pages;
- 17 unique packages/cases;
- cases 48366831 through 48366847;
- three continuation cases that span two pages.

The continuation cases are:

- 48366844;
- 48366845;
- 48366846.

The reference SSD contains exactly 17 SoCs rows for position 10, at rows 23–39.

This confirms the PackBridge rule:

> A source page is not a package. Package identity is determined by Case Number and continuation pages must be merged.

## Important reference discrepancy

The existing SSD workbook must **not** be treated as a golden source for every commercial/packing value.

For case 48366844 the source packing list and the reference SSD disagree on net/gross weight. The dimensions and case identity agree, but the weight values in the SSD repeat the preceding case values.

PackBridge must therefore generate from approved source/working data and must compare output back to that data. It must not simply copy values from this historical SSD example.

## SoCs_Temp structure

### Main package table

The principal Excel table is:

- table name: **Table2**
- table range in the verified reference workbook: **C22:W90**
- data rows in that reference: **23:90**
- capacity in that reference: **68 package rows**

PackBridge no longer assumes every valid SSD workbook must have exactly 68 rows. The controlled-template inspector derives the package capacity from the actual Table2 end row, provided the table still starts at C22, ends in column W, and the required validation controls cover the corresponding data rows. For example, Table2 `C22:W38` is treated as a 16-package template rather than rejected solely because it is shorter.

Column X is visually part of the worksheet's case-data area but sits outside Table2.

### Row 21 business headers

| Column | Header |
|---|---|
| C | Qty |
| D | Content Description / Equipment (Name) |
| E | EQ (nnn) |
| F | Border Crossing Value |
| G | Declare As |
| H | PO Number |
| I | PO Pos.Nr. |
| J:L | Case Dimensions |
| M | Volume (cbm) |
| N | Net Weight (Kg.) |
| O | Gross Weight (Kg.) |
| P:Q | Pick-up week planned / actual |
| R | Storage Requirements |
| S | Case Number |
| T | Packaging Material |
| U | Stackability |
| V | Dangerous Goods (Y/N) |
| W | Item designation |
| X | Remarks |

### Verified data validation

The reference workbook contains controlled list/numeric validation for:

- G23:G90 — Declare As;
- O23:O90 — gross/net relationship;
- R23:R90 — Storage Requirements;
- T23:T90 — Packaging Material;
- U23:U90 — Stackability;
- V23:V90 — Dangerous Goods.

The template inspector in PackBridge verifies that these structural controls cover the active Table2 data rows. The reference ranges above are evidence from the reference workbook, not a hard-coded requirement that every template must end at row 90.

### Lookup lists observed

The reference workbook contains lists for:

- Stackable 1 tier / 2 tier / 3 tier / Not stackable;
- Outdoor / Outdoor covered / Indoor / Indoor heated;
- Dangerous Goods Y/N;
- PALLET / CARTON_BOX / WOODEN_FRAME / BUNDLE / WOODEN_BOX / DRUM / UNPACKED;
- Declare As: System / Loose Parts.

These are **SSD business values**, not necessarily values present on a vendor packing list.

## Project-level fields

The upper portion of SoCs_Temp includes project/header data such as:

- HE PO Number;
- currency for border-crossing value;
- supplier name and pickup address;
- supplier contact;
- Preliminary/Final flag;
- BU details;
- customer/contact remarks;
- project name;
- delivery location;
- total package count;
- total volume;
- total net weight;
- total gross weight.

Some values are formulas derived from the case table.

PackBridge must distinguish these project/default values from source packing-list values.

## Safe direct mappings verified from the reference source

The following canonical package fields have a clear direct relationship to SoCs_Temp:

| Canonical field | SoCs target | Rule |
|---|---|---|
| package.dimensions.length | J | source dimension L, normalised to required unit only by deterministic rule |
| package.dimensions.width | K | source dimension W |
| package.dimensions.height | L | source dimension H |
| package.volume | M | preserve template formula; do not overwrite when formula is present |
| package.net_weight | N | approved working net weight |
| package.gross_weight | O | approved working gross weight |
| package.case_number | S | approved working case number |

These are the first fields that can safely be part of a deterministic writer.

## Fields that must not be guessed from the packing list

The current evidence does **not** justify blindly populating the following from similarly named source fields:

- D Content Description / Equipment;
- E EQ number;
- F Border Crossing Value;
- G Declare As;
- H HE/PO Number;
- I PO position;
- P/Q pickup week;
- R Storage Requirement;
- T Packaging Material;
- U Stackability;
- V Dangerous Goods;
- W Item designation;
- X Remarks.

Examples from the reference prove why:

- the source Sales Order is not the same value as the SSD PO Number;
- the source package type such as CAP-BOX... is not the same vocabulary as SSD Packaging Material (PALLET, WOODEN_BOX, etc.);
- Storage Requirement and Stackability can be populated in the SSD even when the packing list does not provide those values.

These fields need project/master data, approved defaults, explicit user input, or an approved deterministic translation rule.

## Packing List sheets

PLs_Temp is very hidden.

It looks up package-level data from SoCs_Temp using the Case Number and provides a detailed line-item table with columns including:

- Article/Item Number;
- HE PO Number;
- HE PO Position;
- Quantity;
- UoM;
- Description;
- Country of Origin;
- DG indicator;
- UN Number;
- ECCN;
- Tariff Code;
- Commodity Code;
- Border Crossing Value;
- Gross Weight per unit;
- Net Weight per unit.

Generated PL sheets contain item-level data that is not stored in the SoCs package row itself.

This means final PackBridge generation may require two deterministic layers:

1. populate/verify the SoCs package dataset;
2. populate the generated per-case PL line-item dataset when those sheets are required.

## Marking Label sheets

MLs_Temp is very hidden.

Generated marking labels pull from SoCs data, including:

- Project Name;
- Delivery Location;
- Supplier;
- PO;
- position;
- Storage Requirement;
- EQ group;
- Content Description;
- Net/Gross Weight;
- dimensions;
- Case Number.

The VBA creates one ML sheet per package.

## VBA role

Printable strings recovered from the embedded VBA show routines associated with:

- creating Packing List sheets;
- creating Marking Label sheets;
- checking uniqueness of Case Number;
- copying the hidden templates;
- naming sheets PL-<case> and ML-<case>;
- protecting/unprotecting workbook sheets;
- creating per-sheet PDF files;
- optional Outlook/email/ZIP workflow.

This supports the conclusion that VBA is primarily a **workbook document-generation mechanism**.

It does **not yet prove** whether VBA is required by the SAP import.

Therefore:

> PackBridge must preserve the macro-enabled template for the first controlled output implementation. A macro-free XLSX route should be enabled only after SAP acceptance testing proves it is safe.

## Multi-packing-list / project aggregation finding

The reference SSD has 68 case rows, grouped by PO position:

- position 10 — 17 cases;
- position 30 — 17 cases;
- position 70 — 16 cases;
- position 110 — 16 cases;
- position 270 — 1 case;
- position 280 — 1 case.

The supplied PDF represents only position 10.

This means PackBridge eventually needs to support **assembling multiple packing-list jobs into one SSD/project shipment dataset**, rather than assuming one PDF always equals one complete SSD.

That aggregation feature should be added before production SSD generation.

## Implemented safety support

PackBridge now includes a controlled SSD-template inspector that verifies:

- required SoCs_Temp / PLs_Temp / MLs_Temp worksheets;
- expected hidden states;
- Table2 name and range;
- key SoCs headers;
- expected data-validation ranges;
- VBA presence;
- file SHA-256;
- structural fingerprint.

Settings can install an XLSM/XLSX template only if the required structure passes validation. Installed templates are versioned by SHA-256 rather than overwritten in place.

## Next engineering work

1. Add an explicit SSD/project-data model for values not sourced from the packing list.
2. Add shipment aggregation so multiple mapped packing lists can feed one SSD.
3. Implement a read-only SSD Output Preview using the verified SoCs mapping.
4. Add deterministic pre-generation comparison: Virtual SSD → proposed SoCs rows.
5. Implement the first writer against a copied XLSM template while preserving VBA.
6. Re-open and structurally verify the generated workbook.
7. Compare every written SoCs value back to approved working data.
8. Determine whether PL/ML generation is required for the SAP process.
9. Only after SAP testing, decide whether a macro-free XLSX output path is valid.
