import fitz

from packbridge.services.document_ingestion import extract_path


def test_blank_scanned_pdf_uses_configured_local_ocr_fallback(tmp_path, monkeypatch):
    source = tmp_path / "scan.pdf"
    document = fitz.open()
    document.new_page(width=300, height=200)
    document.save(source)
    document.close()

    monkeypatch.setattr(
        "packbridge.services.document_ingestion.ocr_pdf_bytes",
        lambda payload, language="eng": [
            (1, "Packing List\nCase Number: SCAN-1\nGross Weight: 100 KG")
        ],
    )

    extracted = extract_path(
        source,
        ocr_mode="tesseract",
        ocr_language="eng",
    )

    assert extracted.page_count == 1
    assert extracted.chunks[0].locator == "Page 1, OCR"
    assert "SCAN-1" in extracted.chunks[0].text
