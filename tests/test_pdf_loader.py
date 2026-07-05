from __future__ import annotations

from typing import BinaryIO

import pytest

from unireg.loaders import PDFLoader, PDFLoadError


class FakePage:
    def __init__(self, text: str | None) -> None:
        self._text = text

    def extract_text(self) -> str | None:
        return self._text


class FakeReader:
    def __init__(self) -> None:
        self.pages = [FakePage("첫 페이지"), FakePage(None), FakePage("셋째 페이지")]


def fake_reader_factory(stream: BinaryIO) -> FakeReader:
    assert stream.read(1) == b"%"
    return FakeReader()


def test_pdf_loader_extracts_pages_with_numbers(tmp_path) -> None:
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-pretend")

    document = PDFLoader(reader_factory=fake_reader_factory).load(pdf_path)

    assert document.source_file == str(pdf_path)
    assert document.extraction_method == "pypdf"
    assert [page.page_number for page in document.pages] == [1, 2, 3]
    assert [page.text for page in document.pages] == ["첫 페이지", "", "셋째 페이지"]


def test_pdf_loader_rejects_non_pdf(tmp_path) -> None:
    text_path = tmp_path / "sample.txt"
    text_path.write_text("not pdf", encoding="utf-8")

    with pytest.raises(PDFLoadError):
        PDFLoader(reader_factory=fake_reader_factory).load(text_path)
