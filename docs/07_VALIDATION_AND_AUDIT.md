# Validation and Audit

## Validation philosophy

PackBridge should use deterministic validation wherever a rule can be expressed reliably in code.

The LLM may explain a warning but should not be the authority that decides whether a numeric/business constraint passed.

## Example validation rules

### Package data

- case/package identifier present where required;
- duplicate case identifiers detected;
- dimensions numeric and non-negative;
- expected dimension count is three;
- gross weight normally >= net weight;
- volume numeric and non-negative;
- units recognised;
- continuation pages merge under the correct case.

### Item data

- quantity numeric and non-negative;
- UOM recognised or explicitly reviewed;
- item identifier/description present where required;
- repeated sequence numbers checked within a package;
- quantity/UOM combinations checked for obvious extraction errors where rules exist.

### SSD readiness

- required fields present;
- project/master data resolved;
- no blocking ambiguities;
- output template version available;
- all user overrides accepted;
- final generation validation passed.

## Warnings versus blockers

Not every unusual value should prevent work.

Use:

- **INFO** — notable but no action required;
- **WARNING** — should be reviewed but can potentially be accepted;
- **BLOCKING** — SSD generation should not proceed without resolution/explicit authorised override.

## Editable data

Users can change values read from the original source.

When changed, retain:

- source value;
- working value;
- user;
- timestamp;
- optional reason;
- edit method;
- approval status.

## Revert actions

Support:

- revert one field;
- revert all changes in a case;
- revert all user changes in a job.

Do not destroy source extraction.

## Audit events

Record important events such as:

- file uploaded;
- processing started/completed;
- knowledge profile selected;
- model/version used;
- canonical extraction version;
- field edited;
- assistant proposal approved/rejected;
- validation warning acknowledged;
- knowledge change proposed/approved;
- approved snapshot created;
- SSD generated;
- SSD downloaded/exported.

## Assistant edits

If a user asks in chat:

> Change case X gross weight to Y

the assistant creates a proposal. On user approval, application code performs the update and records:

- method = assistant proposal;
- approved by;
- before/after;
- evidence cited by assistant if available.

## Reproducibility

A historical job should retain enough information to understand:

- which source file was used;
- which knowledge/profile version was active;
- which model/version was used;
- what the extracted values were;
- what changed;
- what data was approved;
- which SSD template version produced the output.

Full bit-for-bit reproducibility may depend on model determinism, but the approved data → SSD generation stage should be deterministic.
