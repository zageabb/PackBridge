# PackBridge Knowledge

This directory contains human-readable guidance used by the local PackBridge document mapper.

## Principle

Knowledge explains how PackBridge should understand documents. It is intentionally kept in readable, version-controlled files so that a production support team can inspect, replace and exchange the relevant document without editing application database tables.

## Structure

```text
knowledge/
├── system/
│   ├── CANONICAL_SCHEMA.md
│   ├── PACKING_LIST_MAPPING.md
│   ├── SSD_OUTPUT_RULES.md
│   └── VALIDATION_RULES.md
└── vendors/
    └── <vendor>/
        └── <document-profile>.md
```

## Support model

When a document fails:

1. identify the active vendor/document profile;
2. collect a safe failing example;
3. update the relevant Knowledge document;
4. validate the change;
5. return/import the updated file;
6. reprocess the affected job.

PackBridge may cache parsed knowledge internally, but the files in this directory remain the maintainable source of truth.
