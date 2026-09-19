from packbridge.services import local_ocr


def test_tesseract_availability_uses_local_executable(monkeypatch):
    monkeypatch.setattr(local_ocr.shutil, "which", lambda name: "/usr/bin/tesseract")
    assert local_ocr.tesseract_available() is True

    monkeypatch.setattr(local_ocr.shutil, "which", lambda name: None)
    assert local_ocr.tesseract_available() is False
