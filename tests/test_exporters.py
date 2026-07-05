from __future__ import annotations

import json
from datetime import date

import pytest

from unireg.exporters import JSONExporter, MarkdownExporter
from unireg.models import (
    Appendix,
    Article,
    Chapter,
    Clause,
    IncompletenessFlag,
    IncompletenessType,
    Item,
    Reference,
    ReferenceStatus,
    ReferenceType,
    Regulation,
    RegulationDocument,
    SubItem,
    Table,
)


def test_json_exporter_dumps_versioned_document_snapshot() -> None:
    document = _sample_document()

    text = JSONExporter().dumps(document)
    payload = json.loads(text)
    restored = JSONExporter.loads_document(text)

    assert text.endswith("\n")
    assert payload["schema_version"] == "unireg.regulation.v1"
    assert payload["regulation"]["title"] == "테스트 규정"
    assert payload["regulation"]["effective_date"] == "2026-07-05"
    assert restored.to_dict() == document.to_dict()


def test_json_exporter_rejects_non_document_json() -> None:
    with pytest.raises(TypeError):
        JSONExporter.loads_document("[1, 2, 3]")


def test_markdown_exporter_dumps_hierarchy_snapshot() -> None:
    document = _sample_document()

    text = MarkdownExporter().dumps(document)

    assert text == """# 테스트 규정

- Source file: sample.pdf
- Effective date: 2026-07-05
- Amendment date: 2026-07-06

## 제1장 총칙

### 제1조 목적

- 제1항 다음 각 호와 같다.
  - 제1호 첫째 항목
    - 가목 세부 기준

> Reference (missing_internal_rule/missing target=시행세칙): 시행세칙에 따른다.
> Incomplete (requires_missing_regulation missing=시행세칙): 시행세칙에 따른다.

## Appendices

### 별표 1

#### Table: 별표 1

대학 학과 정원
"""


def test_markdown_exporter_rejects_empty_parse_result() -> None:
    from unireg.models import ParseResult, ParseStats

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
        MarkdownExporter().dumps(result)


def _sample_document() -> RegulationDocument:
    reference = Reference(
        id="reg/chapter:1/article:1/clause:1/reference:1",
        source_node_id="reg/chapter:1/article:1/clause:1",
        reference_type=ReferenceType.MISSING_INTERNAL_RULE,
        status=ReferenceStatus.MISSING,
        raw_text="시행세칙에 따른다.",
        required_document_name="시행세칙",
    )
    flag = IncompletenessFlag(
        id="reg/chapter:1/article:1/clause:1/incompleteness:1",
        node_id="reg/chapter:1/article:1/clause:1",
        flag_type=IncompletenessType.REQUIRES_MISSING_REGULATION,
        raw_text="시행세칙에 따른다.",
        missing_source="시행세칙",
    )
    sub_item = SubItem(
        id="reg/chapter:1/article:1/clause:1/item:1/sub-item:가",
        sub_item_number="가",
        path=["chapter:1", "article:1", "clause:1", "item:1", "sub-item:가"],
        text="세부 기준",
    )
    item = Item(
        id="reg/chapter:1/article:1/clause:1/item:1",
        item_number="1",
        path=["chapter:1", "article:1", "clause:1", "item:1"],
        text="첫째 항목",
        sub_items=[sub_item],
    )
    clause = Clause(
        id="reg/chapter:1/article:1/clause:1",
        path=["chapter:1", "article:1", "clause:1"],
        clause_number="1",
        text="다음 각 호와 같다. 1. 첫째 항목 가. 세부 기준",
        items=[item],
        references=[reference],
        incompleteness_flags=[flag],
    )
    article = Article(
        id="reg/chapter:1/article:1",
        article_number="제1조",
        title="목적",
        path=["chapter:1", "article:1"],
        clauses=[clause],
    )
    chapter = Chapter(
        id="reg/chapter:1",
        number="1",
        title="총칙",
        path=["chapter:1"],
        articles=[article],
    )
    table = Table(
        id="reg/appendix:annex-1/table:1",
        path=["appendix:annex-1", "table:1"],
        caption="별표 1",
        text="대학 학과 정원",
    )
    appendix = Appendix(
        id="reg/appendix:annex-1",
        path=["appendix:annex-1"],
        number="1",
        title="별표 1",
        tables=[table],
    )
    regulation = Regulation(
        id="reg",
        title="테스트 규정",
        source_file="sample.pdf",
        effective_date=date(2026, 7, 5),
        amendment_date=date(2026, 7, 6),
        chapters=[chapter],
        appendices=[appendix],
    )
    return RegulationDocument(regulation=regulation)
