# Reuse Plan

PackBridge should reuse proven modules and design patterns from existing repositories rather than rebuilding infrastructure unnecessarily.

## Selected architecture

PackBridge will be a **Flask/Python local-first application**.

This choice maximises direct reuse from Tender Designer, System Knowledge Designer, Should-Cost Intelligence, General Search and Internet Pricing, while still borrowing the strongest Office/Knowledge ideas from Context Studio and Olladex.

## Reuse matrix

| Source repository | What PackBridge will reuse/adapt | PackBridge area |
|---|---|---|
| **General Search** | Generic document-extraction helpers, Markdown/table normalisation, untrusted-document context pattern | Source ingestion and LLM context preparation |
| **Internet Pricing** | Profile-runtime concept: a document profile selects guidance while retaining one generic processing engine; settings/activity UX ideas | Document profile selection and processing telemetry |
| **Tender Designer** | Secure upload ingestion, managed file storage, prompt-file service, right-side contextual chat panel, safe proposed-action/confirmation pattern | Uploads, storage, prompts, assistant UI and change proposals |
| **Context Studio** | Split-screen workspace concepts, scoped Knowledge retrieval, source section locators, Office safety boundaries, workbook inspect/compare/formula validation ideas | Virtual SSD, Knowledge, evidence/source viewer, SSD verification |
| **Should-Cost Intelligence** | Robust typed Ollama client, Pydantic structured-response validation, deterministic/LLM boundary, evidence models, governed Knowledge proposals and version-conflict handling | Mapper client, canonical schemas, Learning/Knowledge proposals |
| **System Knowledge Designer** | Primary robust document-ingestion foundation: PDF/DOCX/XLSX extraction with page/row locators, Office/ZIP safety limits, FTS5 Knowledge search, grounded assistant patterns | Document reader, Knowledge index, source evidence, assistant grounding |
| **Olladex** | Runtime Ollama settings/model discovery/test, conversation states such as waiting-for-input/approval, Excel inspection/mutation primitives | Settings/diagnostics, assistant workflow, SSD workbook adapter |

## What will not be reused

### General Search / Internet Pricing web research

PackBridge does not currently need public-web research. The search/retrieval/browser pipeline will therefore **not** be copied into PackBridge.

If a future requirement needs external product/vendor information, PackBridge should call the existing service or shared research core rather than fork it again.

### Pricing-specific logic

Internet Pricing and Should-Cost pricing, comparable-selection and market-evidence logic are outside PackBridge's scope.

### Context Studio frontend framework

Context Studio uses a Next/FastAPI architecture. PackBridge will not pull that framework into a Flask application merely for visual reuse. We will reuse its interaction patterns and selected backend logic instead.

### Olladex coding-agent tooling

Repository editing, terminal execution and coding-agent worktrees are not PackBridge requirements. Only the reusable local-model/runtime and approval-state ideas are relevant.

## Preferred implementation sources

Where several repositories contain similar code, use one main implementation rather than maintaining duplicate variants.

### Document ingestion

**Primary:** System Knowledge Designer `services/knowledge.py`

Why:

- page/row locators;
- file signatures;
- Office ZIP safety;
- size limits;
- chunking;
- PDF/DOCX/XLSX coverage.

**Supplement:** General Search `document_extraction.py`

Use its concise table-to-Markdown representation where that improves LLM mapping input.

### Ollama client

**Primary:** Should-Cost Intelligence `app/llm/client.py`

Why:

- temperature 0;
- retries/timeouts;
- bounded response size;
- typed Pydantic response validation;
- JSON schema support;
- explicit error codes;
- bounded tool conversations.

**Supplement:** Olladex runtime settings for connection testing/model discovery.

### Upload/storage

**Primary:** Tender Designer

- `services/upload_ingestion.py`
- `services/file_storage.py`

Adapt directory names from tender/session to PackBridge job/source/output.

### Knowledge

**Primary runtime/search:** System Knowledge Designer + Context Studio.

**Change governance:** Should-Cost Knowledge proposal/approval model.

The PackBridge source of truth remains Markdown Knowledge files. Database records track proposals/history rather than replacing the documents.

### Assistant UI

**Primary:** Tender Designer `templates/partials/chat_panel.html` and `static/js/chat.js`.

Adapt it to:

- selected case/field context;
- source evidence actions;
- proposal Apply/Cancel;
- waiting-for-input questions;
- collapse/resizing.

### Conversation states

**Pattern:** Olladex `conversation_runtime.py`.

PackBridge initially needs only a small subset:

- running;
- waiting_for_input;
- waiting_for_approval;
- completed;
- failed.

Do not copy coding-agent/task-worktree behaviour.

### SSD workbook

**Primary primitives:** Olladex `office_excel.py` and Context Studio spreadsheet validation/comparison code.

PackBridge will place a **much tighter safety layer** around these generic operations. The SSD writer will expose only approved mappings and will not support arbitrary add/delete/rename operations during normal generation.

## New PackBridge-specific code

The following must be purpose-built because it is the business core:

- canonical Packing List schema;
- source/working/approved value states;
- package continuation/grouping logic;
- Virtual SSD data/view model;
- packing-list mapping prompt/schema;
- vendor/document-profile matcher;
- validation rules;
- canonical → SSD mapping rules;
- SSD template fingerprint/structural verification;
- source-vs-working audit;
- Learning flow that writes/proposes Markdown Knowledge updates.

## Development sequence

1. Reuse/adapt infrastructure modules.
2. Build PackBridge canonical schema.
3. Build upload + document extraction.
4. Connect `qwen3:14b` using typed JSON mapping.
5. Render the first Virtual SSD shell.
6. Process the reference packing list.
7. Add editing/validation/evidence.
8. Add assistant.
9. Add Knowledge/Learning.
10. Only then implement the final SSD writer after the workbook mapping is verified.

## Baseline local model

Initial baseline:

`qwen3:14b`

Later benchmark:

`qwen3:8b`

No new model is required to begin development.
