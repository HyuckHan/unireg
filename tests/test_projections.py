from __future__ import annotations

import pytest

from unireg.models import NodeType, ParseResult, ParseStats
from unireg.parser import RegulationParser
from unireg.projections import GraphEdgeType, ProjectionBuilder, ProjectionSet


def test_projection_builder_creates_search_vector_and_graph_outputs() -> None:
    result = RegulationParser().parse_text(
        "\n"
        "테스트 규정\n"
        "제1장 총칙\n"
        "제1조(목적) ① 다음 각 호와 같다. "
        "1. 기준은 시행세칙에 따른다. "
        "2. 기타 가. 세부사항은 따로 정한다.\n",
        source_file="projection.pdf",
    )

    projection = ProjectionBuilder().build(result)

    assert {document.node_type for document in projection.bm25_documents} == {
        NodeType.ARTICLE,
        NodeType.CLAUSE,
        NodeType.ITEM,
        NodeType.SUB_ITEM,
    }
    assert [document.node_id for document in projection.vector_documents] == [
        document.node_id for document in projection.bm25_documents
    ]

    article_document = projection.bm25_documents[0]
    assert article_document.title == "테스트 규정, 제1조(목적)"
    assert article_document.citation_label == "테스트 규정, 제1조(목적)"
    assert article_document.source_label == "projection.pdf p.1"
    assert article_document.metadata["regulation_title"] == "테스트 규정"
    assert article_document.metadata["chapter_title"] == "총칙"
    assert article_document.metadata["article_number"] == "제1조"
    assert article_document.metadata["provision_status"] == "active"

    item_document = next(
        document
        for document in projection.bm25_documents
        if document.node_type == NodeType.ITEM
        and document.metadata.get("item_number") == "1"
    )
    assert item_document.metadata["required_documents"] == "시행세칙"
    assert item_document.metadata["missing_sources"] == "시행세칙"
    assert item_document.metadata["reference_statuses"] == "missing"

    node_ids = {node.node_id for node in projection.graph_nodes}
    assert result.document is not None
    regulation = result.document.regulation
    first_article = regulation.chapters[0].articles[0]
    first_item = first_article.clauses[0].items[0]
    assert regulation.id in node_ids
    assert first_article.id in node_ids

    contains_edges = [
        edge
        for edge in projection.graph_edges
        if edge.edge_type == GraphEdgeType.CONTAINS
    ]
    assert any(
        edge.source_node_id == regulation.id
        and edge.target_node_id == regulation.chapters[0].id
        for edge in contains_edges
    )

    missing_edges = [
        edge
        for edge in projection.graph_edges
        if edge.edge_type == GraphEdgeType.MISSING_REFERENCE
    ]
    assert missing_edges
    assert missing_edges[0].source_node_id == first_item.id
    assert missing_edges[0].target_node_id is None
    assert missing_edges[0].properties["required_document_name"] == "시행세칙"


def test_projection_serializes_round_trip() -> None:
    result = RegulationParser().parse_text(
        """
테스트 규정
제1장 총칙
제1조(목적)
본문
""",
        source_file="serialize.pdf",
    )
    projection = ProjectionBuilder().build(result)

    restored = ProjectionSet.from_dict(projection.to_dict())

    assert restored == projection


def test_projection_builder_rejects_empty_parse_result() -> None:
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
        ProjectionBuilder().build(result)
