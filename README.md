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

The current development build includes document upload/extraction, deterministic document-profile matching, local Ollama structured mapping, an editable provenance-aware Virtual SSD, validation issues, field/case/job revert controls, a resizable job assistant, audit history, and a read-only Knowledge browser.

Final SSD generation remains intentionally disabled until the reference workbook has been inspected and its SAP-sensitive mapping has been verified.
