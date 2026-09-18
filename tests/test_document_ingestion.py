import fitz
from openpyxl import Workbook

from packbridge.services.document_ingestion import extract_path


def test_csv_is_rendered_with_locator(tmp_path):
    path = tmp_path / "packing.csv"
    path.write_text("Case Number,Gross Weight\nC-1,830\n", encoding="utf-8")

    document = extract_path(path)

    assert document.extension == ".csv"
    assert document.chunks
    assert document.chunks[0].locator == "CSV"
    assert "Case Number" in document.chunks[0].text
    assert "C-1" in document.chunks[0].text


def test_xlsx_preserves_sheet_name_in_locator(tmp_path):
    path = tmp_path / "packing.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Packing"
    sheet.append(["Case Number", "Gross Weight"])
    sheet.append(["C-1", 830])
    workbook.save(path)

    document = extract_path(path)

    assert document.extension == ".xlsx"
    assert any(chunk.locator.startswith("Sheet: Packing") for chunk in document.chunks)
    assert "C-1" in document.text



def test_pdf_table_is_extracted_with_page_table_locator(tmp_path):
    path = tmp_path / "packing.pdf"
    pdf = fitz.open()
    page = pdf.new_page(width=300, height=160)

    # Draw a simple two-column table with two rows.
    for x in (30, 150, 270):
        page.draw_line((x, 30), (x, 110))
    for y in (30, 70, 110):
        page.draw_line((30, y), (270, y))

    page.insert_text((40, 55), "Case Number")
    page.insert_text((160, 55), "Gross Weight")
    page.insert_text((40, 95), "C-1")
    page.insert_text((160, 95), "830 KG")
    pdf.save(path)
    pdf.close()

    document = extract_path(path)

    table_chunks = [
        chunk for chunk in document.chunks
        if chunk.locator.startswith("Page 1, Table ")
    ]
    assert table_chunks
    assert "Case Number" in table_chunks[0].text
    assert "Gross Weight" in table_chunks[0].text
    assert "C-1" in table_chunks[0].text
