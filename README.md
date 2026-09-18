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
