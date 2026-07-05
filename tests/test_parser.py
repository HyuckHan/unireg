from __future__ import annotations

from pathlib import Path

from unireg.models import DiagnosticSeverity
from unireg.parser import RegulationParser

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_PDF = PROJECT_ROOT / "examples/pdf/[2-1-1] 학칙(20260414개정).pdf"


def test_parser_builds_chapter_and_article_hierarchy() -> None:
    text = """
테스트 학칙
제1장 총칙
제1조(목적)
이 학칙은 테스트를 목적으로 한다.
제2조(정의) 이 학칙에서 사용하는 용어는 다음과 같다.
① 이 줄은 아직 clause로 파싱하지 않는다.
제2장 조직
제3조(조직)
조직에 관한 사항은 따로 정한다.
"""

    result = RegulationParser().parse_text(text, source_file="test.txt")

    assert result.document is not None
    regulation = result.document.regulation
    assert regulation.title == "테스트 학칙"
    assert result.stats.chapter_count == 2
    assert result.stats.article_count == 3

    first_chapter = regulation.chapters[0]
    assert first_chapter.number == "1"
    assert first_chapter.title == "총칙"
    assert [article.article_number for article in first_chapter.articles] == [
        "제1조",
        "제2조",
    ]
    assert first_chapter.articles[0].title == "목적"
    assert first_chapter.articles[0].body_lines == [
        "이 학칙은 테스트를 목적으로 한다."
    ]
    assert first_chapter.articles[1].title == "정의"
    assert first_chapter.articles[1].body_lines == [
        "이 학칙에서 사용하는 용어는 다음과 같다.",
        "① 이 줄은 아직 clause로 파싱하지 않는다.",
    ]

    second_chapter = regulation.chapters[1]
    assert second_chapter.number == "2"
    assert second_chapter.articles[0].body_lines == [
        "조직에 관한 사항은 따로 정한다."
    ]


def test_parser_preserves_inserted_article_number() -> None:
    text = """
테스트 규정
제1장 총칙
제1조의2(추가 조항)
추가 조항 본문
"""

    result = RegulationParser().parse_text(text, source_file="inserted.txt")

    assert result.document is not None
    article = result.document.regulation.chapters[0].articles[0]
    assert article.article_number == "제1조의2"
    assert article.path == ["chapter:1", "article:1-2"]
    assert article.id.endswith("/article:1-2")


def test_parser_warns_and_creates_implicit_chapter_for_article_before_chapter() -> None:
    text = """
장 없는 규정
제1조(목적)
본문
"""

    result = RegulationParser().parse_text(text, source_file="no-chapter.txt")

    assert result.document is not None
    regulation = result.document.regulation
    assert regulation.chapters[0].number == "implicit"
    assert regulation.chapters[0].articles[0].article_number == "제1조"
    assert result.diagnostics[0].severity == DiagnosticSeverity.WARNING
    assert result.diagnostics[0].code == "article_before_chapter"


def test_parser_serializes_to_dict() -> None:
    result = RegulationParser().parse_text(
        """
테스트 규정
제1장 총칙
제1조(목적)
본문
""",
        source_file="serialize.txt",
    )

    payload = result.to_dict()

    assert payload["document"] is not None
    assert payload["stats"]["article_count"] == 1


def test_parser_handles_real_pdf_extraction() -> None:
    result = RegulationParser().parse_file(SAMPLE_PDF)

    assert result.document is not None
    regulation = result.document.regulation
    assert result.stats.chapter_count == 29
    assert result.stats.article_count >= 85
    assert result.stats.unknown_line_count == 0
    assert [chapter.number for chapter in regulation.chapters] == [
        str(number) for number in range(1, 30)
    ]

    first_chapter = regulation.chapters[0]
    assert first_chapter.title == "총칙"
    assert first_chapter.articles[0].article_number == "제1조"
    assert first_chapter.articles[0].title == "교육목적"
    assert first_chapter.articles[0].source_span is not None
    assert first_chapter.articles[0].source_span.page_start == 1

    chapter_24 = regulation.chapters[23]
    assert chapter_24.number == "24"
    assert chapter_24.title == "시간제등록생"
    assert chapter_24.articles[0].article_number == "제80조"
