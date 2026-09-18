# Design Decision Log

This file records important architectural decisions made before and during implementation.

## D001 — Application name

**Decision:** PackBridge.

**Reason:** The application bridges varied vendor packing lists into a controlled internal/SAP-ready SSD representation while remaining broad enough for future logistics document use.

## D002 — Local LLM

**Decision:** Core operation uses a local Ollama model. Start with a 12B–14B-class model and benchmark a 7B-class model later.

**Reason:** The task is primarily semantic extraction/mapping rather than broad open-ended reasoning. Local processing is a core demonstration goal.

## D003 — Generic mapper for all vendors

**Decision:** Internal HE packing lists also pass through the generic mapper.

**Reason:** Different internal vendors may use different layouts. A special HE parser would create false assumptions and reduce extensibility.

## D004 — Vendor/document knowledge as documents

**Decision:** Mapping guidance lives primarily in human-readable Knowledge documents.

**Reason:** Easier production handover, remote support, explanation, version control and maintenance than a large set of relational configuration tables.

## D005 — Profile granularity

**Decision:** Knowledge profile concept is Vendor → Document Type → Layout/Version Family.

**Reason:** One vendor may issue multiple unrelated formats and may change layouts over time.

## D006 — Source vs working data

**Decision:** Users may edit extracted data, but source values are retained.

**Reason:** The packing list itself can contain errors. PackBridge must support human correction without losing traceability.

## D007 — Virtual SSD

**Decision:** The main left workspace presents a browser representation of the SSD.

**Reason:** Users can verify the result in a form that closely matches their real business output, edit it safely and understand whether processing worked.

## D008 — Two-panel UI

**Decision:** Main workflow on the left; context-aware local assistant on the right.

**Reason:** Chat is useful for exceptions, questions and learning, but should not dominate normal processing.

## D009 — LLM proposes; code applies

**Decision:** The assistant may propose changes but application code applies them only after user approval.

**Reason:** Prevent silent mutation and keep audit/control boundaries clear.

## D010 — LLM does not generate final workbook

**Decision:** Approved structured data is written to an SSD template deterministically by Python.

**Reason:** The workbook format is SAP-sensitive and must not depend on generative behaviour.

## D011 — Macros not required

**Decision:** The generated output does not need VBA/macros for the current use case.

**Open verification:** Confirm that macro-free XLSX preserves everything SAP requires from the reference workbook.

## D012 — Package identity is semantic, not page-based

**Decision:** A PDF page is not assumed to equal a case/package.

**Reason:** The initial packing list contains continuation pages for the same case.

## D013 — Confidence handling

**Decision:** Use operational statuses such as CONFIRMED / SUPPORTED / AMBIGUOUS / MISSING / INVALID rather than trusting arbitrary model-generated percentage confidence.

## D014 — Database purpose

**Decision:** SQLite stores operational history; Knowledge files explain behaviour.

**Reason:** Keep supportable mapping knowledge together while retaining structured audit/job persistence.
