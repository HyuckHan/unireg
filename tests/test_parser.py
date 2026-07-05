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
    assert first_chapter.articles[0].regulation_title == "테스트 학칙"
    assert first_chapter.articles[0].chapter_title == "총칙"
    assert first_chapter.sections == []
    assert first_chapter.articles[0].body_lines == ["이 학칙은 테스트를 목적으로 한다."]
    assert first_chapter.articles[0].clauses[0].clause_number is None
    assert first_chapter.articles[0].clauses[0].text == (
        "이 학칙은 테스트를 목적으로 한다."
    )
    assert first_chapter.articles[1].title == "정의"
    assert first_chapter.articles[1].body_lines == [
        "이 학칙에서 사용하는 용어는 다음과 같다.",
        "① 이 줄은 아직 clause로 파싱하지 않는다.",
    ]
    assert [clause.clause_number for clause in first_chapter.articles[1].clauses] == [
        None,
        "1",
    ]

    second_chapter = regulation.chapters[1]
    assert second_chapter.number == "2"
    assert second_chapter.articles[0].body_lines == ["조직에 관한 사항은 따로 정한다."]


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


def test_parser_builds_clause_hierarchy() -> None:
    text = """
테스트 규정
제1장 총칙
제1조(목적) ① 첫째 항이다.② 둘째 항이다.
둘째 항의 이어지는 문장이다.
제2조(정의)
번호 없는 본문이다.
"""

    result = RegulationParser().parse_text(text, source_file="clause.txt")

    assert result.document is not None
    articles = result.document.regulation.chapters[0].articles
    first_article = articles[0]
    assert first_article.body_lines == [
        "① 첫째 항이다.② 둘째 항이다.",
        "둘째 항의 이어지는 문장이다.",
    ]
    assert [clause.clause_number for clause in first_article.clauses] == ["1", "2"]
    assert first_article.clauses[0].text == "첫째 항이다."
    assert first_article.clauses[0].raw_text == "① 첫째 항이다."
    assert first_article.clauses[0].path == ["chapter:1", "article:1", "clause:1"]
    assert first_article.clauses[1].text == (
        "둘째 항이다.\n둘째 항의 이어지는 문장이다."
    )
    assert first_article.clauses[1].id.endswith("/clause:2")

    second_article = articles[1]
    assert len(second_article.clauses) == 1
    assert second_article.clauses[0].clause_number is None
    assert second_article.clauses[0].path == [
        "chapter:1",
        "article:2",
        "clause:unnumbered",
    ]
    assert second_article.clauses[0].text == "번호 없는 본문이다."


def test_parser_builds_item_and_sub_item_hierarchy() -> None:
    text = """
테스트 규정
제1장 총칙
제1조(목적) ① 다음 각 호와 같다. 1. 첫째 항목2. 둘째 항목
둘째 항목의 이어지는 문장이다.
제2조(세부) ① 다음 각 목과 같다. 1. 상위 문구 가. 세부 첫째 나. 세부 둘째
세부 둘째의 이어지는 문장이다.
"""

    result = RegulationParser().parse_text(text, source_file="item.txt")

    assert result.document is not None
    articles = result.document.regulation.chapters[0].articles
    first_clause = articles[0].clauses[0]
    assert first_clause.text == (
        "다음 각 호와 같다. 1. 첫째 항목2. 둘째 항목\n" "둘째 항목의 이어지는 문장이다."
    )
    assert [item.item_number for item in first_clause.items] == ["1", "2"]
    assert first_clause.items[0].text == "첫째 항목"
    assert first_clause.items[0].path == [
        "chapter:1",
        "article:1",
        "clause:1",
        "item:1",
    ]
    assert first_clause.items[1].text == ("둘째 항목\n둘째 항목의 이어지는 문장이다.")

    second_clause = articles[1].clauses[0]
    item = second_clause.items[0]
    assert item.item_number == "1"
    assert item.text == "상위 문구"
    assert [sub_item.sub_item_number for sub_item in item.sub_items] == ["가", "나"]
    assert item.sub_items[0].text == "세부 첫째"
    assert item.sub_items[0].path == [
        "chapter:1",
        "article:2",
        "clause:1",
        "item:1",
        "sub-item:가",
    ]
    assert item.sub_items[1].text == ("세부 둘째\n세부 둘째의 이어지는 문장이다.")


def test_parser_builds_section_hierarchy() -> None:
    text = """
테스트 규정
제1장 총칙
제1조(직접조문)
직접 조문 본문
제1절 통칙
절 머리말
제2조(목적)
섹션 조문 본문
제2절 정의
제3조(정의)
정의 조문 본문
"""

    result = RegulationParser().parse_text(text, source_file="section.txt")

    assert result.document is not None
    regulation = result.document.regulation
    chapter = regulation.chapters[0]
    assert result.stats.article_count == 3
    assert [article.article_number for article in chapter.articles] == ["제1조"]
    assert [section.number for section in chapter.sections] == ["1", "2"]

    first_section = chapter.sections[0]
    assert first_section.title == "통칙"
    assert first_section.intro_lines == ["절 머리말"]
    assert first_section.articles[0].article_number == "제2조"
    assert first_section.articles[0].section_title == "통칙"
    assert first_section.articles[0].chapter_title == "총칙"
    assert first_section.articles[0].path == [
        "chapter:1",
        "section:1",
        "article:2",
    ]
    assert first_section.articles[0].id.endswith("/section:1/article:2")
    assert first_section.articles[0].body_lines == ["섹션 조문 본문"]
    assert first_section.articles[0].clauses[0].clause_number is None

    second_section = chapter.sections[1]
    assert second_section.title == "정의"
    assert second_section.articles[0].article_number == "제3조"


def test_parser_warns_and_creates_implicit_chapter_for_section_before_chapter() -> None:
    text = """
장 없는 규정
제1절 통칙
제1조(목적)
본문
"""

    result = RegulationParser().parse_text(text, source_file="no-chapter-section.txt")

    assert result.document is not None
    regulation = result.document.regulation
    assert regulation.chapters[0].number == "implicit"
    assert regulation.chapters[0].sections[0].number == "1"
    assert regulation.chapters[0].sections[0].articles[0].article_number == "제1조"
    assert result.diagnostics[0].severity == DiagnosticSeverity.WARNING
    assert result.diagnostics[0].code == "section_before_chapter"


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
    regulation = payload["document"]["regulation"]
    first_chapter = regulation["chapters"][0]
    first_article = first_chapter["articles"][0]
    assert first_chapter["node_type"] == "chapter"
    assert first_chapter["sections"] == []
    assert first_article["node_type"] == "article"
    assert first_article["clauses"][0]["node_type"] == "clause"
    assert first_article["clauses"][0]["clause_number"] is None


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
    assert first_chapter.articles[0].clauses[0].clause_number is None

    chapter_24 = regulation.chapters[23]
    assert chapter_24.number == "24"
    assert chapter_24.title == "시간제등록생"
    assert chapter_24.articles[0].article_number == "제80조"
