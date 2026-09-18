from __future__ import annotations

from pathlib import Path

import fitz


class PDFRenderingError(ValueError):
    pass


def render_pdf_page(
    source: str | Path,
    destination: str | Path,
    page_number: int,
    *,
    scale: float = 1.5,
) -> Path:
    source = Path(source)
    destination = Path(destination)

    if source.suffix.casefold() != ".pdf":
        raise PDFRenderingError("Only PDF source documents can be rendered as pages.")
    if page_number < 1:
        raise PDFRenderingError("PDF page numbers start at 1.")

    destination.parent.mkdir(parents=True, exist_ok=True)

    try:
        document = fitz.open(source)
    except Exception as exc:
        raise PDFRenderingError("The PDF could not be opened for rendering.") from exc

    try:
        if page_number > document.page_count:
            raise PDFRenderingError(
                f"Page {page_number} is outside this {document.page_count}-page PDF."
            )
        page = document.load_page(page_number - 1)
        matrix = fitz.Matrix(scale, scale)
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        pixmap.save(temporary)
        temporary.replace(destination)
    finally:
        document.close()

    return destination
