# PackBridge Roadmap

## Milestone 1 — First visible proof

**Goal:** Upload the reference packing list and show correctly grouped cases in a browser Virtual SSD.

Deliverables:

- Flask shell;
- upload;
- PDF extraction;
- Ollama connection;
- canonical case/package JSON;
- basic case summary;
- source evidence link/page;
- no SSD generation yet.

Success means the user can visually confirm that PackBridge understood the source document.

## Milestone 2 — Editable Virtual SSD

**Goal:** Make the extracted result useful as a reviewed business dataset.

Deliverables:

- source vs working values;
- direct field editing;
- editable line items;
- provenance indicators;
- revert actions;
- Summary / Case / Issues views;
- validation engine.

Success means the user can correct a bad source value and see exactly what will be used downstream.

## Milestone 3 — Context-aware assistant

**Goal:** Handle exceptions without making chat mandatory.

Deliverables:

- right-hand assistant panel;
- selected-case/field context;
- evidence explanations;
- assistant clarification questions;
- assistant-proposed edits with approval;
- per-job chat history.

Success means an unfamiliar mapping issue can be diagnosed without leaving the job screen.

## Milestone 4 — Knowledge and learning

**Goal:** Make new vendor layouts supportable without code forks.

Deliverables:

- Knowledge loader;
- vendor/document profiles;
- profile matching;
- Learning workflow;
- proposed Knowledge diffs;
- approved examples;
- profile versioning;
- remote support import/export.

Success means a new vendor format can be taught through a Knowledge update rather than writing a custom parser.

## Milestone 5 — SSD generation

**Goal:** Produce the real SAP-sensitive output safely.

Deliverables:

- verified SSD template analysis;
- deterministic field mapping;
- template/version checks;
- generated workbook;
- structural regression;
- downloadable final output;
- job audit trail.

Success means the generated file is accepted by the established SAP process.

## Milestone 6 — Broader vendor proof

**Goal:** Demonstrate generality.

Deliverables:

- multiple internal layouts;
- at least one materially different external vendor layout;
- unknown-layout fallback;
- benchmark test set;
- 14B and 7B comparison.

Success means PackBridge is demonstrably a generic mapping application rather than a wrapper around one packing-list layout.

## Milestone 7 — Production handover

**Goal:** Make support and operation straightforward for another team.

Deliverables:

- deployment guide;
- backup/restore;
- production configuration;
- user/admin guide;
- Knowledge support guide;
- template support guide;
- health/diagnostics;
- authentication/roles if required;
- release/version process.
