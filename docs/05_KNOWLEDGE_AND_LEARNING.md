# Knowledge and Learning

## Design choice

PackBridge knowledge should be primarily **document-driven**, not hidden across a large configuration database.

This makes the application easier to:

- explain;
- hand over;
- audit;
- support remotely;
- version in Git;
- update without database migrations.

Operational activity still belongs in the database. Mapping knowledge belongs in readable files.

## Proposed structure

```text
knowledge/
├── system/
│   ├── CANONICAL_SCHEMA.md
│   ├── PACKING_LIST_MAPPING.md
│   ├── SSD_OUTPUT_RULES.md
│   └── VALIDATION_RULES.md
└── vendors/
    ├── hitachi-energy/
    │   ├── qbank-packing-list.md
    │   └── other-document-family.md
    └── vendor-abc/
        └── packing-list.md
```

## Profile hierarchy

Do not assume one mapping per vendor.

Use the conceptual hierarchy:

```text
Vendor
└── Document Type
    └── Layout / Version Family
```

A vendor may have multiple unrelated packing-list formats.

## What a profile may contain

- document-identification indicators;
- terminology mappings;
- document-structure hints;
- unit conventions;
- continuation-page rules;
- approved examples;
- known exceptions;
- interpretation notes;
- vendor-specific validation notes.

## What should not be learned casually

Do not turn a one-off observed value into a global rule.

Examples requiring caution:

- Dangerous Goods = N
- Stackability = 1 tier
- Country of Origin
- Packaging type
- project-specific PO
- equipment group

These may be shipment/project-specific rather than document-format knowledge.

## Learning workflow

When a new format is encountered:

1. process generically;
2. identify ambiguous/unrecognised fields;
3. user resolves them;
4. PackBridge proposes a knowledge amendment;
5. user approves or rejects;
6. approved knowledge document is updated/versioned.

Example proposal:

```text
Vendor: ABC Engineering
Document type: Packing List

Add mapping:
"Shipping Mass" → package.gross_weight

[Approve Knowledge Change] [Reject]
```

## Correction scope

When a user corrects a mapping, offer scope:

- This document only — default
- This document profile
- All documents from this vendor — only where genuinely appropriate

Defaulting to current document protects against accidental over-learning.

## Few-shot examples

Knowledge documents may include small source → expected-output examples.

Example:

```text
SOURCE:
Shipping Weight: 1,250 kg
Unladen Mass: 1,087 kg

EXPECTED:
gross_weight = 1250 KG
net_weight = 1087 KG
```

A small number of relevant approved examples can be injected into the mapper prompt to improve a 7B/14B model without fine-tuning.

## Versioning

Knowledge profiles should be versionable.

Do not destroy old behaviour when a supplier changes format.

Example:

```text
Hitachi Energy / Packing List
- Layout v1 — historical
- Layout v2 — current
```

## Remote support model

Desired support process:

1. production team sends the relevant knowledge document plus a failing example;
2. support updates the document;
3. updated knowledge file is returned;
4. production imports/replaces the file;
5. PackBridge validates/reloads the knowledge.

This is intentionally easier than asking support staff to modify a collection of database configuration tables.

## Structured blocks

Human-readable Markdown may contain structured YAML/JSON blocks for rules that application code must interpret deterministically.

The distinction is:

- prose/examples guide the LLM;
- structured rule blocks control deterministic behaviour;
- application code validates structured blocks before activation.
