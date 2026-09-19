# PackBridge

**PackBridge — Local AI-assisted packing-list mapping, validation and SAP-ready SSD generation.**

PackBridge is a local-first document-processing application that converts internal and external vendor packing lists into a reviewed working dataset and then deterministically generates the SAP-compatible SSD workbook.

## Core principles

- **Local AI only** — document interpretation is performed through a local Ollama-hosted LLM; cloud AI is not required.
- **Generic document mapper** — all vendors, including internal vendors, use the same semantic mapping pipeline.
- **Document-driven knowledge** — vendor/document guidance is maintained as human-readable knowledge documents rather than hidden across many database tables.
- **Virtual SSD review** — users review and edit a browser representation of the SSD before generation.
- **Source values are preserved** — manual corrections never destroy what was originally read from the packing list.
- **Deterministic SAP output** — the LLM never writes the final workbook directly. Approved structured data is written into a controlled SSD template by application code.
- **Human control** — ambiguity, validation failures and proposed knowledge changes are presented for review rather than silently inferred.

## Initial reference documents

The initial proof of concept is based on:

- an internal vendor packing-list PDF containing multiple package/case records, including continuation pages; and
- the existing SSD workbook used as the downstream SAP-import format.

The first implementation should prove that PackBridge can ingest the packing list, map it through a local 7B/14B-class LLM, present the result as an editable Virtual SSD, validate it, and generate a structurally controlled SSD workbook.

## Documentation

See the [design documentation](docs/00_PRODUCT_VISION.md), [architecture](docs/01_ARCHITECTURE.md), [UI/UX design](docs/02_UI_UX_DESIGN.md), [roadmap](docs/ROADMAP.md), and the main [TODO](TODO.md).

The `knowledge/` directory is designed to contain the human-readable mapping guidance used by the local mapper.


## Local run

PackBridge is assigned **TCP port 5085** for the local Ubuntu deployment.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
.venv/bin/python app.py
```

Open:

```text
http://<server-ip>:5085/
```

The default local model is `qwen3:14b`; change the Ollama URL/model through Settings or environment configuration.

## Current implementation

PackBridge source development is complete for the currently verified scope.

The application now includes:

- local document ingestion for PDF/DOCX/XLSX/XLSM/CSV/TXT/Markdown, with optional local Tesseract OCR for scanned PDFs;
- deterministic profile matching plus generic structured mapping through local Ollama;
- staged mapping for larger documents and continuation-page/case merging;
- an editable provenance-aware Virtual SSD with source evidence, PDF-page verification, validation, acknowledgements, reverts and field/case reprocessing;
- a job-aware local assistant with evidence grounding, deterministic shipment queries and reviewable Apply/Cancel changes;
- governed Knowledge/profile learning, versioning, diff/approval, import/export and correction-to-profile proposals;
- multi-job SSD Projects, controlled template inspection/cleaning/versioning and deterministic SoCs output;
- structurally/value-verified validation workbooks and an explicitly SAP-gated production generation/download path;
- optional local authentication and centrally enforced roles;
- rotating logs, database migrations, backup/restore, opt-in retention, health/readiness diagnostics and Ubuntu/UDA deployment packaging;
- a multi-layout golden benchmark harness for comparing the 14B baseline with smaller local candidates.

PackBridge does **not** claim that SAP acceptance has happened. Production output remains locked by deployment flags until the external checks in [External Acceptance Checklist](docs/19_EXTERNAL_ACCEPTANCE_CHECKLIST.md) are completed. The software never guesses unverified PL/ML workbook cell mappings.

See [Acceptance and Benchmark Criteria](docs/17_ACCEPTANCE_AND_BENCHMARK.md) and [Production Handover](docs/18_PRODUCTION_HANDOVER.md).
