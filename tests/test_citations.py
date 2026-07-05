from __future__ import annotations

import pytest

from unireg.citations import Citation, CitationGenerator
from unireg.models import (
    Article,
    NodeType,
    ParseResult,
    ParseStats,
    Regulation,
    SourceSpan,
)
from unireg.parser import RegulationParser


def test_citation_generator_builds_article_clause_item_labels() -> None:
    result = RegulationParser().parse_text(
        """
테스트 규정
제1장 총칙
제1조(목적) ① 다음 각 호와 같다. 1. 첫째 항목 가. 세부 기준
""",
        source_file="sample.pdf",
    )

    citations = CitationGenerator().generate(result)

    assert [citation.node_type for citation in citations] == [
        NodeType.ARTICLE,
        NodeType.CLAUSE,
        NodeType.ITEM,
        NodeType.SUB_ITEM,
    ]
    assert [citation.label for citation in citations] == [
        "테스트 규정, 제1조(목적)",
        "테스트 규정, 제1조(목적), 제1항",
        "테스트 규정, 제1조(목적), 제1항, 제1호",
        "테스트 규정, 제1조(목적), 제1항, 제1호, 가목",
    ]
    assert all(citation.source_label == "sample.pdf p.1" for citation in citations)
    assert citations[0].quote == "① 다음 각 호와 같다. 1. 첫째 항목 가. 세부 기준"
    assert citations[2].quote == "첫째 항목"
    assert citations[3].quote == "세부 기준"


def test_citation_generator_can_omit_quotes() -> None:
    result = RegulationParser().parse_text(
        """
테스트 규정
제1조(목적)
본문
""",
        source_file="quote.pdf",
    )

    citations = CitationGenerator().generate(result, include_quotes=False)

    assert citations[0].quote is None


def test_citation_serializes_round_trip_with_source_span() -> None:
    span = SourceSpan(
        source_file="/tmp/source.pdf",
        page_start=2,
        page_end=3,
        line_start=10,
        line_end=12,
    )
    citation = Citation(
        node_id="node:1",
        node_type=NodeType.ARTICLE,
        regulation_title="테스트 규정",
        label="테스트 규정, 제1조",
        source_label="source.pdf pp.2-3",
        source_span=span,
        quote="본문",
    )

    restored = Citation.from_dict(citation.to_dict())

    assert restored == citation


def test_citation_generator_formats_source_page_ranges() -> None:
    span = SourceSpan(source_file="/tmp/source.pdf", page_start=2, page_end=3)
    regulation = Regulation(
        id="reg", title="테스트 규정", source_file="/tmp/source.pdf"
    )
    article = Article(
        id="reg/article:1",
        article_number="제1조",
        title=None,
        path=["article:1"],
        source_span=span,
    )

    citation = CitationGenerator().article(regulation, article)

    assert citation.source_label == "source.pdf pp.2-3"


def test_citation_generator_formats_missing_sources() -> None:
    missing = Citation(
        node_id="node:missing",
        node_type=NodeType.ARTICLE,
        regulation_title="테스트 규정",
        label="테스트 규정, 제1조",
        source_label="source unavailable",
        source_span=None,
    )

    assert missing.source_label == "source unavailable"


def test_citation_generator_rejects_empty_parse_result() -> None:
    result = ParseResult(
        document=None,
        diagnostics=[],
        stats=ParseStats(
            line_count=0,
            parsed_line_count=0,
            unknown_line_count=0,
            chapter_count=0,
            article_count=0,
            diagnostic_count=0,
        ),
    )

    with pytest.raises(ValueError):
        CitationGenerator().generate(result)
