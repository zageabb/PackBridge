# UI / UX Design

## Primary layout

PackBridge should use a two-panel workspace.

- **Left: 70% approximately** — upload, processing, Virtual SSD, review, validation and output.
- **Right: 30% approximately** — context-aware local LLM assistant.
- Right panel should be collapsible and preferably resizable.

```text
┌────────────────────────────────────────────────────────────┬─────────────────────────┐
│ PACKBRIDGE — SSD WORKSPACE                                 │ LOCAL ASSISTANT         │
│ Sales Order / Job                     Status               │ Local model • Online    │
│                                                            │                         │
│ [Summary] [Cases…] [Issues] [Source] [Output]              │ Current context         │
│                                                            │                         │
│ Virtual SSD                                                │ Explanations / questions│
│ editable fields and line items                             │ / proposed actions      │
│                                                            │                         │
│                                             [Generate SSD]  │ [Ask…]                  │
└────────────────────────────────────────────────────────────┴─────────────────────────┘
```

## Main navigation

Suggested application-level navigation:

- Workspace / Jobs
- Knowledge
- Settings
- About / Diagnostics

Do not over-complicate the first release with many modules.

## Job workspace states

### 1. Upload

Show:

- drag/drop or file picker;
- source filename;
- detected document type/vendor if known;
- relevant knowledge profile if found;
- selected local LLM;
- Process button.

### 2. Processing

Do not leave a static screen.

Show progressive steps such as:

- Reading document
- Extracting text/tables
- Loading relevant knowledge
- Mapping packages
- Validating extracted data
- Building Virtual SSD

If processing requires a user answer, leave completed work intact and surface the question in the assistant panel.

### 3. Virtual SSD

This is the main working view.

Recommended tabs:

- **Summary**
- individual case tabs for smaller jobs
- **Issues**
- **Source**
- **Output Preview**

For a large number of cases, add a searchable case selector and Previous/Next navigation rather than forcing hundreds of tabs.

## Summary view

Provide a concise shipment table:

```text
Case       L     W     H    Gross   Net   Items   Status
48366831  148   152    66     830    643     2      ✓
48366832  148   152    66     830    643     2      ✓
...
48366844  307   249    73     875    518     8      ✎
```

Summary should show counts such as:

- cases;
- ready;
- manually changed;
- warnings;
- unresolved issues.

Clicking a row opens the case.

## Case view

Present a browser representation of the SSD fields for the selected package/case.

Example:

```text
CASE 48366844

Qty              [ 1 ]
Description      [ QBANK ]
EQ Group         [ 011 ]
Declare As       [ System ]
PO Number        [ .......... ]
PO Position      [ 10 ]

Length           [ 307 ] CM      ✓ Source
Width            [ 249 ] CM      ✓ Source
Height           [  73 ] CM      ✓ Source
Volume           [ ... ] M3      ƒ Calculated
Net Weight       [ 518 ] KG      ✓ Source
Gross Weight     [ 875 ] KG      ✎ Modified

Case Number      [ 48366844 ]
Packaging        [ ... ]
Stackability     [ ... ]
Dangerous Goods  [ ... ]
```

Exact fields will be finalised after the SSD template mapping is verified.

## Editable working data

Users must be able to edit values read from the source.

The UI must preserve:

- source value;
- working value;
- who changed it;
- when it changed;
- optional reason;
- revert action.

Indicators:

- ✓ source/extracted and unchanged
- ✎ user modified
- ƒ calculated
- ● project/default/master data
- ⚠ needs attention
- ? missing

## Line-item editor

Case contents should be presented as an editable grid:

- sequence;
- position;
- item number;
- description;
- serial number;
- quantity;
- UOM;
- other required item fields.

Changes rerun validation.

## Source verification popup

Provide a large side-by-side or overlay comparison:

```text
┌────────────────────────────┬───────────────────────────────┐
│ ORIGINAL PACKING LIST      │ CURRENT VIRTUAL SSD          │
│ rendered relevant page(s) │ field values / line items    │
│                            │ editable                     │
└────────────────────────────┴───────────────────────────────┘
```

For a selected field, highlight or identify the relevant source evidence where practical.

## Issues view

Only unresolved or noteworthy items:

- ambiguous mappings;
- missing required data;
- validation failures;
- manually overridden values;
- unknown UOMs;
- unmatched project/master data;
- output/template structural issues.

The user should not need to inspect every case when only two fields need attention.

## Assistant panel

The assistant should be quiet when everything works.

Normal successful state:

> No issues found. Ask me anything about this packing list.

When the user selects a field/case, show a small context indicator such as:

```text
Context
Case 48366844 › Gross Weight
```

Then short questions such as "Where did this come from?", "Why is this different?" and "What rule mapped this?" are meaningful without repeating context.

## Assistant-proposed changes

The assistant may propose but not silently apply a data change.

Example:

```text
Proposed update

Case: 48366844
Field: Gross Weight
Current: 1590 KG
Proposed: 875 KG

Evidence: Packing List page 14

[Apply] [Cancel]
```

Applying the change updates the working dataset through deterministic application logic and reruns validation.

## Final generation

When ready:

```text
✓ SSD DATA READY

17 cases
0 unresolved issues

[Generate SSD]
```

Generation should be disabled or require explicit acknowledgement if blocking validation errors remain.
