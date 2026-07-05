from __future__ import annotations

from unireg.models import (
    IncompletenessType,
    ReferenceStatus,
    ReferenceType,
)
from unireg.parser import RegulationParser


def test_parser_detects_reference_and_incompleteness_patterns() -> None:
    text = """
테스트 규정
제1장 총칙
제1조(세부)
세부사항은 따로 정한다.
제2조(권한)
① 운영 기준은 총장이 따로 정한다.
제3조(세칙)
① 세부 기준은 시행세칙에 따른다.
제4조(별도)
① 신청 절차는 별도 규정에 따른다.
"""

    result = RegulationParser().parse_text(text, source_file="references.txt")

    assert result.document is not None
    articles = result.document.regulation.chapters[0].articles
    implicit_clause = articles[0].clauses[0]
    admin_clause = articles[1].clauses[0]
    rule_clause = articles[2].clauses[0]
    separate_rule_clause = articles[3].clauses[0]

    assert implicit_clause.references[0].reference_type == (
        ReferenceType.IMPLICIT_REFERENCE
    )
    assert implicit_clause.references[0].status == ReferenceStatus.UNRESOLVED
    assert implicit_clause.incompleteness_flags[0].flag_type == (
        IncompletenessType.REQUIRES_MISSING_REGULATION
    )
    assert implicit_clause.incompleteness_flags[0].missing_source is None

    assert admin_clause.references[0].reference_type == (
        ReferenceType.ADMINISTRATIVE_DISCRETION
    )
    assert admin_clause.references[0].target_name == "총장"
    assert admin_clause.incompleteness_flags[0].flag_type == (
        IncompletenessType.ADMINISTRATIVE_DISCRETION
    )

    assert rule_clause.references[0].reference_type == (
        ReferenceType.MISSING_INTERNAL_RULE
    )
    assert rule_clause.references[0].status == ReferenceStatus.MISSING
    assert rule_clause.references[0].required_document_name == "시행세칙"
    assert rule_clause.incompleteness_flags[0].missing_source == "시행세칙"

    assert separate_rule_clause.references[0].reference_type == (
        ReferenceType.MISSING_INTERNAL_RULE
    )
    assert separate_rule_clause.references[0].required_document_name == "별도 규정"
    assert separate_rule_clause.incompleteness_flags[0].missing_source == "별도 규정"


def test_parser_attaches_references_to_item_and_sub_item_nodes() -> None:
    text = """
테스트 규정
제1장 총칙
제1조(항목)
① 다음 각 호와 같다. 1. 기준은 시행세칙에 따른다. 2. 기타 가. 세부사항은 따로 정한다.
"""

    result = RegulationParser().parse_text(text, source_file="item-references.txt")

    assert result.document is not None
    clause = result.document.regulation.chapters[0].articles[0].clauses[0]
    first_item = clause.items[0]
    second_item = clause.items[1]
    sub_item = second_item.sub_items[0]

    assert clause.references == []
    assert first_item.references[0].required_document_name == "시행세칙"
    assert first_item.incompleteness_flags[0].missing_source == "시행세칙"
    assert second_item.references == []
    assert sub_item.references[0].reference_type == ReferenceType.IMPLICIT_REFERENCE
    assert sub_item.incompleteness_flags[0].flag_type == (
        IncompletenessType.REQUIRES_MISSING_REGULATION
    )


def test_reference_enrichment_serializes_from_parser_output() -> None:
    result = RegulationParser().parse_text(
        """
테스트 규정
제1장 총칙
제1조(목적)
시행세칙에 따른다.
""",
        source_file="reference-serialize.txt",
    )

    payload = result.to_dict()

    assert payload["document"] is not None
    clause = payload["document"]["regulation"]["chapters"][0]["articles"][0]["clauses"][
        0
    ]
    assert clause["references"][0]["required_document_name"] == "시행세칙"
    assert clause["incompleteness_flags"][0]["missing_source"] == "시행세칙"
