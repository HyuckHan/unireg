from __future__ import annotations

from unireg.cleaning import DocumentCleaner
from unireg.models import ExtractedDocument, ExtractedPage


def test_cleaner_normalizes_lines_and_preserves_source_spans() -> None:
    document = ExtractedDocument(
        source_file="sample.pdf",
        extraction_method="test",
        pages=[
            ExtractedPage(
                page_number=3,
                text="  제1장   총칙  \n\n\t제1조(목적)   이 규정은  \n",
            )
        ],
    )

    clean_document = DocumentCleaner().clean(document)

    assert [line.text for line in clean_document.lines] == [
        "제1장 총칙",
        "제1조(목적) 이 규정은",
    ]
    assert [line.line_number for line in clean_document.lines] == [1, 2]
    assert clean_document.lines[0].source_span.source_file == "sample.pdf"
    assert clean_document.lines[0].source_span.page_start == 3
    assert clean_document.lines[0].source_span.line_start == 1
    assert clean_document.lines[1].source_span.line_start == 3


def test_cleaner_normalizes_compatibility_width() -> None:
    assert DocumentCleaner.normalize_line("  \uff11\uff0e  내용  ") == "1. 내용"


def test_cleaner_strips_pdf_header_and_splits_structural_markers() -> None:
    document = ExtractedDocument(
        source_file="sample.pdf",
        extraction_method="test",
        pages=[
            ExtractedPage(
                page_number=2,
                text=(
                    "학칙 2-1-1~22 부설연구소 내용"
                    "제4장 수업연한과 재학연한"
                    "제6조(수업연한과 재학연한) 본문"
                ),
            )
        ],
    )

    clean_document = DocumentCleaner().clean(document)

    assert [line.text for line in clean_document.lines] == [
        "2 부설연구소 내용",
        "제4장 수업연한과 재학연한",
        "제6조(수업연한과 재학연한) 본문",
    ]
    assert {line.source_span.page_start for line in clean_document.lines} == {2}
