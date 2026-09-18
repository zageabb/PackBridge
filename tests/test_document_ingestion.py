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
