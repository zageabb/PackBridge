# Test Strategy

## Goal

Prove that PackBridge is reliable enough to transform varied packing lists into approved SSD data without relying on a large cloud model.

## Golden document tests

Maintain a controlled set of sample documents with expected canonical JSON.

For each document verify:

- document/vendor recognition;
- package count;
- package identifiers;
- continuation-page grouping;
- dimensions;
- gross/net weights;
- item count;
- quantities;
- UOMs;
- source evidence references;
- missing-field behaviour.

## Initial regression case

The first reference PDF is useful because it includes:

- repeated common header structure;
- multiple package types;
- different dimensions/weights;
- line-item tables;
- cases spanning more than one page.

Create a redacted/safe test fixture if the real document cannot be committed to the repository.

## Mapping tests

Test terminology variation such as:

- Case Number / Crate ID / Package No.
- Gross Weight / Shipping Weight / Gross Mass.
- Net Weight / Equipment Weight / Unladen Mass.
- Dimensions in different units/order.

## Negative tests

Ensure the mapper does not invent:

- country of origin when blank;
- customer project when absent;
- serial numbers when blank;
- units not present/derivable;
- project-specific defaults from unrelated examples.

## User-edit tests

Verify:

- source value remains unchanged;
- working value changes;
- modified indicator appears;
- validation reruns;
- field revert works;
- package revert works;
- whole-job revert works;
- approved SSD uses working/approved value.

## Validation tests

Examples:

- gross < net;
- missing case number;
- duplicate case number;
- invalid quantity;
- unknown UOM;
- missing required SSD field;
- continuation pages with same case;
- malformed dimensions.

## Knowledge tests

- load valid Markdown profile;
- reject invalid structured rule block;
- match correct vendor/document layout;
- no-match fallback;
- profile version selection;
- approved example injection;
- proposed knowledge diff;
- rollback/reload.

## Assistant tests

Verify:

- selected field context is passed correctly;
- evidence answers reference source data;
- assistant cannot mutate data without Apply;
- assistant cannot mutate Knowledge without approval;
- chat is stored per job;
- structured shipment questions use canonical data rather than hallucinated arithmetic.

## SSD output tests

The final workbook requires strong regression testing.

Compare generated workbook against the approved template for:

- sheet names/order;
- required tables/ranges;
- formulas;
- number formats;
- validations;
- hidden sheets;
- named ranges;
- allowed changed cells;
- unexpected structural additions/deletions.

Add a template fingerprint/version check.

## Model benchmark

Use the exact same golden set for candidate models.

Measure at least:

- header-field accuracy;
- package grouping accuracy;
- line-item accuracy;
- UOM accuracy;
- unknown-format accuracy;
- JSON validity;
- average latency;
- peak memory/GPU usage.

Do not choose the 7B model merely because it is faster. Choose the smallest model that satisfies defined acceptance thresholds.

## Suggested acceptance criteria

Initial targets should be agreed after baseline testing. Example categories:

- 100% valid structured JSON;
- 100% correct case grouping on approved internal test set;
- no invented values in required blank-field tests;
- deterministic validation catches all seeded errors;
- SSD structural regression passes before output release.

Numerical extraction-accuracy thresholds should be based on measured test data rather than guessed up front.
