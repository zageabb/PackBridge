# Canonical Packing List Schema

## Purpose

Every source packing list maps into the same supplier-independent business model before it can be reviewed in the Virtual SSD or written to the SAP SSD workbook.

The source document may use different terminology. Do not force source wording into the canonical structure when the business meaning is different.

## Top-level structure

- Document identity
- Order/project context
- Shipment context
- Packages/cases
- Package line items
- Mapping/validation issues

## Document identity

Typical fields:

- document type
- vendor
- document profile/layout family
- document reference
- document date

## Order/project context

Potential canonical fields:

- sales order
- customer order number
- order position
- project
- customer project
- purchase order
- purchase order position

Some of these may not be present on a packing list. Missing source fields must remain null until supplied by project/master data or a user.

## Shipment context

Potential fields:

- product type
- description
- country of origin
- HS code
- supplier name

## Package / case

A package is a physical/logical shipping package. The source may call it Case Number, Package Number, Crate ID, Box Number, Shipping Unit or Packing Unit.

Canonical package fields include:

- case number
- internal reference
- volume
- length / width / height
- gross weight
- net weight
- package type
- package description
- status
- packed by
- pack date
- items

## Items

Canonical item fields:

- sequence
- position
- item number
- description
- serial number
- quantity
- UOM
- length

## Field provenance

For important fields PackBridge retains:

- source value;
- raw source wording;
- source locator/page/sheet;
- mapping status;
- working value;
- working-value origin;
- manual-change flag;
- optional change reason.

The source value is evidence and is not overwritten by a user correction.

## Value origins

Expected working-value origins:

- source
- user_edit
- project_data
- default_rule
- calculated
- assistant_proposal_approved

## Mapping statuses

Use:

- **CONFIRMED** — explicit source evidence directly supports the value.
- **SUPPORTED** — context clearly supports the interpretation.
- **AMBIGUOUS** — more than one interpretation is reasonable.
- **MISSING** — no source value is present.
- **INVALID** — deterministic validation rejects the mapped/working value.

Do not invent percentage confidence values.
