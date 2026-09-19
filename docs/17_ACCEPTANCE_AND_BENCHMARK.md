# PackBridge Acceptance and Benchmark Criteria

## Purpose

These criteria separate software completion from business/SAP acceptance. PackBridge can be development-complete while production output remains release-gated until the external SAP checks below are recorded.

## Local mapper quality gate

A candidate model must pass the controlled golden set with:

- 100% valid structured responses;
- 100% expected package/case count and case identity;
- 100% preservation of explicitly blank/null test fields (no invented values);
- at least 99% accuracy across expected package fields;
- at least 99% accuracy across expected line-item signatures;
- no unresolved blocking validation issues caused by mapping;
- ambiguous evidence surfaced for review rather than silently guessed.

## Smaller-model selection

`qwen3:14b` is the baseline. A smaller candidate such as `qwen3:8b` may replace it only when:

- all hard gates above pass;
- field and item accuracy are each no more than 0.5 percentage points below the baseline, and still at least 99%;
- package grouping and null preservation remain 100%;
- measured latency and resource use provide a practical benefit on the deployment host.

The CLI command `packbridge benchmark-compare` applies the quality portion of this rule. Final model selection should also consider host memory/VRAM and concurrent-use behaviour.

## Golden document set

The repository contains three non-sensitive multi-layout regression examples under `benchmarks/golden/`:

- an internal QBANK-style continuation-page example;
- an external ACME-style table example using different terminology;
- an external Northstar-style prose example with two packages.

The real HE reference regression remains separately represented by the 20-page to 17-case continuation tests. Additional real supplier examples should be added only when safe to retain and after their expected canonical output is manually approved.

## SSD generation gate

Before production Generate SSD is enabled on a deployment, all of the following must be true:

1. The active controlled template passes PackBridge structural inspection and is generation-ready.
2. The project preview has no unresolved blockers or warnings.
3. Every value written by PackBridge is reopened and compared to the approved preview.
4. The generated workbook retains the controlled structural fingerprint.
5. `PACKBRIDGE_SAP_OUTPUT_APPROVED=1` is set only after an actual SAP import acceptance test.
6. `PACKBRIDGE_SAP_SOCS_ONLY_APPROVED=1` is set only after confirming the deterministic SoCs dataset is sufficient for the SAP import route and PL/ML recreation is not required by that import.
7. `PACKBRIDGE_SAP_MACRO_FREE_APPROVED=1` is set only after SAP accepts a macro-free XLSX template/output. Until then, the macro-enabled controlled template remains the safe path.

## Production acceptance record

The deployment team should retain the accepted test workbook, its PackBridge output SHA-256, template SHA-256, structural fingerprint, application commit, model/version, Knowledge profile version and the SAP acceptance result. This forms the release evidence for enabling the production flags.

## Performance measurements

Each benchmark report records per-document and aggregate latency. On the real host, record:

- average and slowest document mapping time;
- package grouping accuracy;
- field accuracy;
- line-item accuracy;
- null-preservation rate;
- model name/version;
- host RAM/VRAM use observed during the test.

No fixed latency threshold is imposed before the first host baseline because the requirement is deployment-hardware dependent. Quality gates are not relaxed to gain speed.
