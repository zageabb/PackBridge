from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

import fitz


class LocalOCRError(RuntimeError):
    pass


def tesseract_available() -> bool:
    return shutil.which("tesseract") is not None


def ocr_pdf_bytes(
    payload: bytes,
    *,
    language: str = "eng",
    max_pages: int = 200,
    scale: float = 2.0,
) -> list[tuple[int, str]]:
    """OCR a scanned PDF entirely on the local host with Tesseract."""

    executable = shutil.which("tesseract")
    if not executable:
        raise LocalOCRError(
            "Local OCR is enabled but the tesseract executable is not installed."
        )

    try:
        document = fitz.open(stream=payload, filetype="pdf")
    except Exception as exc:
        raise LocalOCRError("The PDF could not be opened for local OCR.") from exc

    try:
        if document.page_count > max_pages:
            raise LocalOCRError(
                f"OCR safety limit is {max_pages} pages; this PDF has {document.page_count}."
            )

        result: list[tuple[int, str]] = []
        with tempfile.TemporaryDirectory(prefix="packbridge-ocr-") as temporary:
            root = Path(temporary)
            for index in range(document.page_count):
                page = document.load_page(index)
                pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
                image_path = root / f"page-{index + 1}.png"
                image_path.write_bytes(pixmap.tobytes("png"))

                process = subprocess.run(
                    [
                        executable,
                        str(image_path),
                        "stdout",
                        "-l",
                        language,
                        "--psm",
                        "6",
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=120,
                    check=False,
                )
                if process.returncode != 0:
                    message = (process.stderr or "").strip()
                    raise LocalOCRError(
                        f"Tesseract failed on page {index + 1}: {message or 'unknown error'}"
                    )
                text = (process.stdout or "").strip()
                if text:
                    result.append((index + 1, text))
        return result
    finally:
        document.close()
