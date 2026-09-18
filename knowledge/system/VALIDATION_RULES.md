# PackBridge Validation Rules

## Principle

Use deterministic Python validation wherever a rule can be checked without semantic judgement.

The LLM may explain a validation issue, but it is not the authority that decides whether a numeric check passed.

## Package identity

- A package should have a case/package identifier when required by the SSD.
- Duplicate case identifiers after mapping are blocking until reviewed because continuation pages should normally have been merged.
- A source page number must never be used as a package identifier merely because no case number was found.

## Weights

- Gross and net weights should be numeric when present.
- Gross weight is normally greater than or equal to net weight.
- Gross below net is a review warning, not an automatic rewrite.
- Missing gross/net weight should be visible to the user.

## Dimensions

- If one of L/W/H is mapped, check whether all three are present.
- Dimension values should be numeric and non-negative.
- Preserve the source unit.
- Do not assume dimensions are L × W × H unless labels/profile evidence support that order.

## Items

- Quantity should be numeric when present.
- Quantity with a missing UOM should produce a warning.
- UOM must be preserved exactly in source evidence before any deterministic normalisation.
- Item number and description should not be invented.
- Duplicate sequence numbers within one package should be reviewed when they are not clearly caused by source structure.

## Readiness

Blocking issues should prevent normal SSD generation.

Warnings may be acknowledged/overridden by an authorised user and recorded in audit history.

Informational messages never block generation.

## Revalidation

Run validation after initial mapping, after a user edit, after an assistant-approved edit, after project/default data is applied, and immediately before final SSD generation.
