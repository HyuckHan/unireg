from __future__ import annotations

import json
from pathlib import Path

from unireg.benchmark.loader import load_benchmark
from unireg.benchmark.models import GoldCitation
from unireg.models import NodeType
from unireg.parser import RegulationParser
from unireg.retrieval import (
    BM25Index,
    BM25RetrievalRunner,
    RetrievalDocument,
    RetrievalRunConfig,
    RetrievalScope,
    build_retrieval_documents,
    parse_retrieval_unit_types,
    tokenize,
    write_retrieval_run_reports,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_DIR = PROJECT_ROOT / "benchmark"


def test_tokenize_adds_korean_character_ngrams() -> None:
    tokens = tokenize("휴학기간은 6학기")

    assert "휴학기간은" in tokens
    assert "휴학" in tokens
    assert "학기" in tokens


def test_bm25_index_ranks_relevant_korean_document_first() -> None:
    documents = [
        _retrieval_document(
            document_id="doc:leave",
            text="학칙 제25조 휴학기간 휴학은 통산하여 6개 학기를 초과할 수 없다.",
            article="제25조",
        ),
        _retrieval_document(
            document_id="doc:degree",
            text="학칙 제40조 졸업요건을 충족한 자에게 학위를 수여한다.",
            article="제40조",
        ),
    ]

    hits = BM25Index(documents).search("휴학은 몇 학기까지 가능한가?", top_k=2)

    assert [hit.document.document_id for hit in hits] == ["doc:leave"]


def test_parse_retrieval_unit_types_accepts_all_supported_units() -> None:
    unit_types = parse_retrieval_unit_types("article,clause,item,sub-item")

    assert unit_types == (
        NodeType.ARTICLE,
        NodeType.CLAUSE,
        NodeType.ITEM,
        NodeType.SUB_ITEM,
    )


def test_build_retrieval_documents_supports_article_clause_item_and_sub_item() -> None:
    result = RegulationParser().parse_text(
        """
        테스트 학칙
        제1장 총칙
        제1조(휴학) ① 휴학 기준은 다음 각 호와 같다. 1. 일반휴학 가. 6학기
        """,
        source_file="test.pdf",
    )

    documents = build_retrieval_documents([result])

    assert {document.node_type for document in documents} == {
        NodeType.ARTICLE,
        NodeType.CLAUSE,
        NodeType.ITEM,
        NodeType.SUB_ITEM,
    }
    assert all(document.citation.source_file == "test.pdf" for document in documents)


def test_bm25_runner_writes_reproducible_reports(tmp_path: Path) -> None:
    dataset = load_benchmark(BENCHMARK_DIR)
    config = RetrievalRunConfig(
        top_k=5,
        scope=RetrievalScope.QUESTION_SOURCE,
        unit_types=(
            NodeType.ARTICLE,
            NodeType.CLAUSE,
            NodeType.ITEM,
            NodeType.SUB_ITEM,
        ),
    )
    result = BM25RetrievalRunner(config=config).run(dataset)
    predictions_path = tmp_path / "predictions.bm25.jsonl"

    write_retrieval_run_reports(
        result,
        tmp_path,
        predictions_path=predictions_path,
    )

    report = json.loads((tmp_path / "retrieval_bm25_report.json").read_text())
    assert report["document_count"] > 0
    assert report["evaluation"]["metrics"]["question_count"] == 20
    assert 0.0 <= report["evaluation"]["metrics"]["recall_at_1"] <= 1.0
    assert 0.0 <= report["evaluation"]["metrics"]["ndcg_at_5"] <= 1.0
    assert len(report["per_university"]) == 5
    assert predictions_path.exists()
    assert (tmp_path / "retrieval_bm25_questions.csv").exists()
    assert (tmp_path / "retrieval_bm25_hits.csv").exists()


def _retrieval_document(
    *,
    document_id: str,
    text: str,
    article: str,
) -> RetrievalDocument:
    return RetrievalDocument(
        document_id=document_id,
        node_id=document_id,
        node_type=NodeType.ARTICLE,
        text=text,
        citation=GoldCitation(
            article=article,
            regulation_title="학칙",
            source_file="test.pdf",
        ),
        citation_label=f"학칙, {article}",
        source_label="test.pdf p.1",
        source_file="test.pdf",
        source_pages=[1],
        metadata={
            "regulation_title": "학칙",
            "source_file": "test.pdf",
            "article_number": article,
        },
    )
