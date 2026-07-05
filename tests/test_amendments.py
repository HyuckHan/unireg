from __future__ import annotations

from datetime import date

from unireg.models import AmendmentEventType, ProvisionStatus
from unireg.parser import RegulationParser


def test_parser_enriches_regulation_dates_from_title() -> None:
    text = """
테스트 규정[시행 2026.07.05.] [2026.07.06.,일부개정]
제1장 총칙
제1조(목적)
본문
"""

    result = RegulationParser().parse_text(text, source_file="dates.txt")

    assert result.document is not None
    regulation = result.document.regulation
    assert regulation.effective_date == date(2026, 7, 5)
    assert regulation.amendment_date == date(2026, 7, 6)
    assert regulation.amendment_history[0].event_type == AmendmentEventType.AMENDED
    assert regulation.amendment_history[0].date == date(2026, 7, 6)


def test_parser_enriches_article_amendment_history() -> None:
    text = """
테스트 규정
제1장 총칙
제1조(목적)
본문 <개정 2026.7.5., 2026.7.6.>
제2조(신설조문)
본문 [본조신설 2025.1.2.]
"""

    result = RegulationParser().parse_text(text, source_file="amendments.txt")

    assert result.document is not None
    articles = result.document.regulation.chapters[0].articles
    assert [
        (event.event_type, event.date) for event in articles[0].amendment_history
    ] == [
        (AmendmentEventType.AMENDED, date(2026, 7, 5)),
        (AmendmentEventType.AMENDED, date(2026, 7, 6)),
    ]
    assert articles[1].amendment_history[0].event_type == (AmendmentEventType.INSERTED)
    assert articles[1].amendment_history[0].date == date(2025, 1, 2)


def test_parser_enriches_deleted_and_repealed_article_status() -> None:
    text = """
테스트 규정
제1장 총칙
제1조(삭제)
삭제 <2018.2.23.>
제2조(폐지)
폐지 <2020.3.4.>
제3조(활성)
1. 삭제 항목은 article 전체 삭제가 아니다.
"""

    result = RegulationParser().parse_text(text, source_file="statuses.txt")

    assert result.document is not None
    articles = result.document.regulation.chapters[0].articles
    assert articles[0].status == ProvisionStatus.DELETED
    assert articles[0].amendment_history[0].event_type == AmendmentEventType.REPEALED
    assert articles[0].amendment_history[0].date == date(2018, 2, 23)
    assert articles[1].status == ProvisionStatus.REPEALED
    assert articles[1].amendment_history[0].event_type == AmendmentEventType.REPEALED
    assert articles[2].status == ProvisionStatus.ACTIVE


def test_real_pdf_first_article_has_amendment_history() -> None:
    result = RegulationParser().parse_file(
        "examples/pdf/[2-1-1] 학칙(20260414개정).pdf"
    )

    assert result.document is not None
    regulation = result.document.regulation
    first_article = regulation.chapters[0].articles[0]
    assert regulation.effective_date == date(2026, 4, 15)
    assert regulation.amendment_date == date(2026, 4, 14)
    assert first_article.status == ProvisionStatus.ACTIVE
    assert first_article.amendment_history[0].event_type == AmendmentEventType.AMENDED
    assert first_article.amendment_history[0].date == date(2026, 2, 26)
