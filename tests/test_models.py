from __future__ import annotations

from datetime import date

from unireg.models import (
    AmendmentEvent,
    AmendmentEventType,
    Appendix,
    Article,
    Chapter,
    Clause,
    IncompletenessFlag,
    IncompletenessType,
    Item,
    ProvisionStatus,
    Reference,
    ReferenceStatus,
    ReferenceType,
    Regulation,
    RegulationDocument,
    Section,
    SourceSpan,
    SubItem,
    Table,
)


def test_regulation_document_round_trips_full_hierarchy() -> None:
    span = SourceSpan(
        source_file="sample.pdf",
        page_start=1,
        page_end=2,
        line_start=1,
        line_end=5,
        extraction_method="test",
        text_hash="abc123",
    )
    sub_item = SubItem(
        id="reg/chapter:1/section:1/article:1/clause:1/item:1/sub-item:가",
        sub_item_number="가",
        path=["chapter:1", "section:1", "article:1", "clause:1", "item:1"],
        text="세부 기준",
        source_span=span,
    )
    item = Item(
        id="reg/chapter:1/section:1/article:1/clause:1/item:1",
        item_number="1",
        path=["chapter:1", "section:1", "article:1", "clause:1", "item:1"],
        text="첫 번째 항목",
        source_span=span,
        sub_items=[sub_item],
    )
    clause_reference = Reference(
        id="ref:clause:1",
        source_node_id="reg/chapter:1/section:1/article:1/clause:1",
        reference_type=ReferenceType.IMPLICIT_REFERENCE,
        status=ReferenceStatus.UNRESOLVED,
        raw_text="세부사항은 따로 정한다.",
        confidence=0.85,
        source_span=span,
    )
    clause_flag = IncompletenessFlag(
        id="flag:clause:1",
        node_id="reg/chapter:1/section:1/article:1/clause:1",
        flag_type=IncompletenessType.REQUIRES_MISSING_REGULATION,
        raw_text="세부사항은 따로 정한다.",
        source_span=span,
    )
    clause = Clause(
        id="reg/chapter:1/section:1/article:1/clause:1",
        clause_number="1",
        path=["chapter:1", "section:1", "article:1", "clause:1"],
        text="첫 번째 항",
        source_span=span,
        items=[item],
        references=[clause_reference],
        incompleteness_flags=[clause_flag],
    )
    reference = Reference(
        id="ref:1",
        source_node_id="reg/chapter:1/section:1/article:1",
        reference_type=ReferenceType.MISSING_INTERNAL_RULE,
        status=ReferenceStatus.MISSING,
        raw_text="세부사항은 따로 정한다.",
        required_document_name="시행세칙",
        confidence=0.9,
        source_span=span,
    )
    flag = IncompletenessFlag(
        id="flag:1",
        node_id="reg/chapter:1/section:1/article:1",
        flag_type=IncompletenessType.REQUIRES_MISSING_REGULATION,
        raw_text="세부사항은 따로 정한다.",
        missing_source="시행세칙",
        source_span=span,
    )
    table = Table(
        id="reg/appendix:annex-1/table:1",
        path=["appendix:annex-1", "table:1"],
        caption="별표 1",
        text="대학 학과 정원",
        raw_text="[별표 1]\n대학 학과 정원",
        source_span=span,
    )
    appendix = Appendix(
        id="reg/appendix:annex-1",
        path=["appendix:annex-1"],
        number="1",
        title="별표 1",
        text="대학 학과 정원",
        raw_text="[별표 1]\n대학 학과 정원",
        source_span=span,
        tables=[table],
    )
    article = Article(
        id="reg/chapter:1/section:1/article:1",
        article_number="제1조",
        title="목적",
        path=["chapter:1", "section:1", "article:1"],
        source_span=span,
        status=ProvisionStatus.ACTIVE,
        regulation_title="테스트 규정",
        chapter_title="총칙",
        section_title="통칙",
        amendment_history=[
            AmendmentEvent(
                event_type=AmendmentEventType.AMENDED,
                date=date(2026, 7, 5),
                raw_text="<개정 2026.7.5.>",
                source_span=span,
            )
        ],
        clauses=[clause],
        references=[reference],
        incompleteness_flags=[flag],
    )
    section = Section(
        id="reg/chapter:1/section:1",
        number="1",
        title="통칙",
        path=["chapter:1", "section:1"],
        source_span=span,
        articles=[article],
    )
    regulation = Regulation(
        id="reg",
        title="테스트 규정",
        source_file="sample.pdf",
        institution="테스트 대학",
        effective_date=date(2026, 7, 5),
        amendment_date=date(2026, 7, 5),
        source_span=span,
        chapters=[
            Chapter(
                id="reg/chapter:1",
                number="1",
                title="총칙",
                path=["chapter:1"],
                source_span=span,
                sections=[section],
            )
        ],
        appendices=[appendix],
        references=[reference],
        incompleteness_flags=[flag],
    )
    document = RegulationDocument(regulation=regulation)

    payload = document.to_dict()
    restored = RegulationDocument.from_dict(payload)

    assert restored.to_dict() == payload
    assert (
        restored.regulation.chapters[0]
        .sections[0]
        .articles[0]
        .clauses[0]
        .items[0]
        .sub_items[0]
        .sub_item_number
        == "가"
    )
    assert restored.regulation.references[0].status == ReferenceStatus.MISSING
    assert restored.regulation.appendices[0].tables[0].caption == "별표 1"
    assert (
        restored.regulation.chapters[0]
        .sections[0]
        .articles[0]
        .clauses[0]
        .incompleteness_flags[0]
        .flag_type
        == IncompletenessType.REQUIRES_MISSING_REGULATION
    )


def test_chapter_all_articles_includes_section_articles() -> None:
    direct_article = Article(
        id="reg/chapter:1/article:1",
        article_number="제1조",
        title="직접 조문",
        path=["chapter:1", "article:1"],
    )
    section_article = Article(
        id="reg/chapter:1/section:1/article:2",
        article_number="제2조",
        title="섹션 조문",
        path=["chapter:1", "section:1", "article:2"],
    )
    chapter = Chapter(
        id="reg/chapter:1",
        number="1",
        title="총칙",
        path=["chapter:1"],
        articles=[direct_article],
        sections=[
            Section(
                id="reg/chapter:1/section:1",
                number="1",
                title="통칙",
                path=["chapter:1", "section:1"],
                articles=[section_article],
            )
        ],
    )

    assert [article.article_number for article in chapter.all_articles()] == [
        "제1조",
        "제2조",
    ]
