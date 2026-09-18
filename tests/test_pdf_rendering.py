import fitz

from packbridge.services.pdf_rendering import render_pdf_page


def test_pdf_page_can_be_rendered_to_png(tmp_path):
    source = tmp_path / "source.pdf"
    document = fitz.open()
    page = document.new_page(width=300, height=200)
    page.insert_text((30, 60), "Case CASE-1 Gross Weight 830 KG")
    document.save(source)
    document.close()

    destination = tmp_path / "rendered" / "page-1.png"
    render_pdf_page(source, destination, 1)

    assert destination.is_file()
    assert destination.read_bytes().startswith(b"\x89PNG")
