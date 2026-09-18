# Wireframes

These are low-fidelity design references. They describe behaviour, not final styling.

## Upload / empty job

```text
┌────────────────────────────────────────────────────────────┬─────────────────────────┐
│ PackBridge                                                 │ Local Assistant         │
│                                                            │                         │
│ Packing List Workspace                                     │ Qwen 14B • Local        │
│                                                            │                         │
│     Drop packing list here                                 │ No job loaded.          │
│     or [Choose File]                                       │                         │
│                                                            │                         │
│     Supported: PDF / DOCX / XLSX ...                       │                         │
│                                                            │                         │
│                               [Process Packing List]        │                         │
└────────────────────────────────────────────────────────────┴─────────────────────────┘
```

## Processing

```text
┌────────────────────────────────────────────────────────────┬─────────────────────────┐
│ Processing vendor-packing-list.pdf                         │ Local Assistant         │
│                                                            │                         │
│ ✓ File loaded                                              │ I will ask here only if │
│ ✓ Text extracted                                           │ something is ambiguous. │
│ ✓ Knowledge loaded                                         │                         │
│ ◉ Mapping cases                                            │                         │
│ ○ Validating                                               │                         │
│ ○ Building Virtual SSD                                     │                         │
└────────────────────────────────────────────────────────────┴─────────────────────────┘
```

## Summary

```text
┌────────────────────────────────────────────────────────────┬─────────────────────────┐
│ Job 890170033                      16 Ready • 1 Changed     │ Local Assistant         │
│ [Summary] [Cases ▼] [Issues] [Source] [Output]             │                         │
│                                                            │ No unresolved issues.   │
│ Case       L    W    H    Gross  Net   Items Status        │ Ask me about this job.  │
│ 48366831  148  152   66     830  643      2    ✓           │                         │
│ 48366832  148  152   66     830  643      2    ✓           │                         │
│ 48366844  307  249   73     890  518      8    ✎           │                         │
│                                                            │                         │
│                                   [Generate SSD]            │ [Ask…]                  │
└────────────────────────────────────────────────────────────┴─────────────────────────┘
```

## Case editor

```text
┌────────────────────────────────────────────────────────────┬─────────────────────────┐
│ Case 48366844                           [‹ Prev] [Next ›]   │ Local Assistant         │
│                                                            │ Context                 │
│ Length         [307] CM     ✓                              │ Case 48366844           │
│ Width          [249] CM     ✓                              │                         │
│ Height         [ 73] CM     ✓                              │                         │
│ Gross Weight   [890] KG     ✎                              │ The gross weight was    │
│ Net Weight     [518] KG     ✓                              │ manually changed from   │
│ Package Type   [...]                                       │ the source value.       │
│                                                            │                         │
│ Original Gross Weight: 875 KG                              │ [Show evidence]         │
│ [Revert] [View Source]                                     │                         │
│                                                            │                         │
│ Contents                                                   │                         │
│ Seq Item             Description            Qty UOM         │                         │
│ ... editable grid ...                                      │                         │
└────────────────────────────────────────────────────────────┴─────────────────────────┘
```

## Clarification question

```text
┌────────────────────────────────────────────────────────────┬─────────────────────────┐
│ Processing paused only for this mapping                    │ I need one answer       │
│                                                            │                         │
│ Other cases remain available.                              │ Shipping Weight: 1280kg │
│                                                            │ Equipment Weight:1095kg │
│                                                            │                         │
│                                                            │ I believe these mean    │
│                                                            │ Gross / Net. Correct?   │
│                                                            │                         │
│                                                            │ [Yes] [Edit mapping]    │
└────────────────────────────────────────────────────────────┴─────────────────────────┘
```

## Source verification popup

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Source Verification — Case 48366844                                   [X]   │
├────────────────────────────────────┬─────────────────────────────────────────┤
│ Original Packing List              │ Current Virtual SSD                     │
│                                    │                                         │
│ Rendered relevant page             │ Case Number      48366844               │
│                                    │ Gross Weight     890 KG  ✎              │
│                                    │ Source value     875 KG                 │
│                                    │ Net Weight       518 KG                 │
│                                    │ ...                                     │
└────────────────────────────────────┴─────────────────────────────────────────┘
```
