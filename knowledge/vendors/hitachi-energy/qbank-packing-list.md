# Hitachi Energy — QBANK Packing List Profile

Version: 2

## Profile status

Initial reference profile for the PackBridge proof of concept.

This profile is **mapping guidance only**. The document must still pass through the generic PackBridge local LLM mapper.

Do not create a dedicated Hitachi Energy parser from these notes.

## Typical recognition indicators

The first reference document includes several of the following labels:

- Packing List
- Sales Order
- Pos.
- Product Type
- Item Description
- HS Code
- Case Number
- Internal HE Number
- Type of Package
- Gross Weight
- Net Weight
- Packed By
- Pack Date

A future Hitachi Energy/internal vendor document may use a different layout, so no single indicator is mandatory.

## Observed terminology

| Source term | Canonical meaning |
|---|---|
| Sales Order | order.sales_order |
| Pos. | order.position |
| Product Type | shipment.product_type |
| Item Description | shipment.description |
| HS Code | shipment.hs_code |
| Case Number | package.case_number |
| Internal HE Number | package.internal_reference |
| Volume | package.volume |
| Dimensions | package.dimensions |
| Gross Weight | package.gross_weight |
| Net Weight | package.net_weight |
| Type of Package | package.package_type / package description context |
| Status | package.status |
| Packed By | package.packed_by |
| Pack Date | package.pack_date |

## Active structured rules

The following block is machine-validated PackBridge configuration as well as readable profile documentation.

~~~packbridge-yaml
document_profile:
  document_type: packing_list
  family: qbank
package_identity:
  canonical_field: package.case_number
  page_is_package: false
continuation:
  merge_key: package.case_number
field_aliases:
  Sales Order: order.sales_order
  Pos.: order.position
  Product Type: shipment.product_type
  Item Description: shipment.description
  HS Code: shipment.hs_code
  Case Number: package.case_number
  Internal HE Number: package.internal_reference
  Gross Weight: package.gross_weight
  Net Weight: package.net_weight
  Packed By: package.packed_by
  Pack Date: package.pack_date
dimension_labels:
  L: length
  W: width
  H: height
~~~

## Dimension format

The reference layout uses labelled dimensions similar to:

L=148 W=152 H=66 CM

Interpret the explicit labels:

- L → length
- W → width
- H → height

Preserve CM as the source unit.

## Package grouping

The initial reference packing list demonstrates that one case can span more than one PDF page.

Important rule:

> Case Number identifies the package. Page number does not.

When a following page repeats the same Case Number and continues the line-item sequence, merge those items into the existing package.

In the reference document used during development, 20 PDF pages represent 17 packages. Three packages continue onto a second page. This is a useful regression characteristic: the mapper must return 17 packages rather than 20.

## Line-item table

Observed columns include:

- Seq.
- Pos.
- Item
- Description
- Serial Number
- Quantity
- UOM
- Length

Blank Serial Number or Length cells remain null. Do not populate them from assumptions.

## Missing labelled fields

The reference document contains labels that can be blank, including project/customer/reference-style fields.

A visible label does not mean the application should invent a value.

Return null/MISSING where no value is present.

## Future learning

If another Hitachi Energy/internal packing-list layout is materially different, create another document profile/version rather than changing this profile so broadly that it becomes ambiguous.
