from __future__ import annotations

import json
from pathlib import Path

from unireg.benchmark.models import Answerability, BenchmarkQuestion, GoldCitation
from unireg.models import NodeType
from unireg.qa.adapters import LLMAdapter, MockLLMAdapter
from unireg.qa.cli import main as qa_main
from unireg.qa.evaluation import evaluate_qa
from unireg.qa.evidence import build_evidence_package
from unireg.qa.models import CompletenessStatus, LLMProvider, LLMRequest, LLMResponse
from unireg.qa.pipeline import GroundedQAPipeline
from unireg.qa.retrievers import EvidenceRetriever
from unireg.retrieval.bm25 import BM25SearchHit
from unireg.retrieval.corpus import RetrievalDocument

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_DIR = PROJECT_ROOT / "benchmark"


def test_evidence_package_preserves_traceable_retrieval_metadata() -> None:
    hit = _hit(
        rank=1,
        score=12.0,
        article="제1조",
        text="학칙 제1조 목적",
        metadata={"incompleteness_types": "requires_missing_regulation"},
    )

    package = build_evidence_package(
        question="질문",
        hits=[hit],
        retriever="bm25",
        retrieval_scope="corpus",
        top_k=5,
        metadata={"question_id": "Q"},
    )

    assert package.package_id.startswith("evidence:")
    assert package.evidence[0].source_pages == [1]
    assert package.evidence[0].confidence == 1.0
    assert package.evidence[0].incompleteness_flags == ["requires_missing_regulation"]
    assert package.to_llm_dict()["evidence"][0]["citation_label"] == "학칙, 제1조"


def test_mock_llm_returns_incomplete_answer_for_missing_regulation_signal() -> None:
    package = build_evidence_package(
        question="세부사항은 현재 corpus만으로 알 수 있는가?",
        hits=[
            _hit(
                rank=1,
                score=1.0,
                article="제1조",
                text="세부사항은 따로 정한다.",
            )
        ],
        retriever="bm25",
        retrieval_scope="corpus",
        top_k=5,
    )
    adapter = MockLLMAdapter()

    response = adapter.complete(adapter.build_request(package))

    assert response.completeness_status == CompletenessStatus.MISSING_REGULATION
    assert response.citations == [package.evidence[0].citation]


def test_pipeline_removes_unsupported_adapter_citations() -> None:
    retriever = _StaticRetriever([_hit(rank=1, score=1.0, article="제1조")])
    pipeline = GroundedQAPipeline(
        retriever=retriever,
        llm_adapter=_UnsupportedCitationAdapter(),
    )

    answer = pipeline.answer("질문")

    assert answer.completeness_status == CompletenessStatus.PARTIAL
    assert answer.citations == []
    assert "unsupported_citations_removed" in answer.guardrail_events
    assert answer.to_dict()["trace"]["llm_input"]["request_id"].startswith(
        "llm_request:"
    )


def test_qa_evaluation_scores_citations_groundedness_and_completeness() -> None:
    question = BenchmarkQuestion(
        id="Q1",
        question="휴학 기간은?",
        answerability=Answerability.ANSWERABLE,
        gold_citations=[
            GoldCitation(
                article="제1조",
                regulation_title="학칙",
                source_file="test.pdf",
            )
        ],
    )
    answer = GroundedQAPipeline(
        retriever=_StaticRetriever([_hit(rank=1, score=1.0, article="제1조")]),
        llm_adapter=MockLLMAdapter(),
    ).answer(question.question)

    result = evaluate_qa([question], [answer])
    evaluated_answer = result.answers[0]

    assert result.metrics.citation_accuracy == 1.0
    assert result.metrics.groundedness == 1.0
    assert result.metrics.completeness_classification_accuracy == 1.0
    assert result.metrics.hallucination_rate == 0.0
    assert evaluated_answer.evaluation is not None
    assert evaluated_answer.to_dict()["trace"]["evaluation"]["question_id"] == "Q1"


def test_qa_cli_benchmark_writes_traceable_reports(tmp_path: Path) -> None:
    exit_code = qa_main(
        [
            "--benchmark",
            "--benchmark-dir",
            str(BENCHMARK_DIR),
            "--report-dir",
            str(tmp_path),
            "--retriever",
            "bm25",
            "--llm",
            "mock",
        ]
    )

    assert exit_code == 0
    report = json.loads((tmp_path / "qa_mock_report.json").read_text())
    assert report["metrics"]["question_count"] == 20
    assert 0.0 <= report["metrics"]["citation_accuracy"] <= 1.0
    answer_line = (tmp_path / "qa_mock_answers.jsonl").read_text().splitlines()[0]
    answer = json.loads(answer_line)
    assert answer["trace"]["question"]
    assert answer["trace"]["retrieved_evidence"]
    assert answer["trace"]["llm_input"]
    assert answer["trace"]["grounded_answer"]
    assert answer["trace"]["evaluation"]


class _StaticRetriever(EvidenceRetriever):
    def __init__(self, hits: list[BM25SearchHit]) -> None:
        self._hits = hits

    def retrieve(
        self,
        question: str,
        *,
        metadata: dict[str, str] | None = None,
    ) -> list[BM25SearchHit]:
        return self._hits

    def trace_config(self) -> dict[str, object]:
        return {
            "method": "static",
            "scope": "test",
            "top_k": len(self._hits),
            "document_count": len(self._hits),
        }


class _UnsupportedCitationAdapter(LLMAdapter):
    provider = LLMProvider.MOCK
    model = "unsupported-citation-test"

    def complete(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(
            answer="없는 조항입니다.",
            citations=[
                GoldCitation(
                    article="제999조",
                    regulation_title="학칙",
                    source_file="test.pdf",
                )
            ],
            completeness_status=CompletenessStatus.COMPLETE,
            confidence=1.0,
        )


def _hit(
    *,
    rank: int,
    score: float,
    article: str,
    text: str = "학칙 제1조 근거",
    metadata: dict[str, str] | None = None,
) -> BM25SearchHit:
    document_metadata = {
        "regulation_title": "학칙",
        "source_file": "test.pdf",
        "article_number": article,
        **(metadata or {}),
    }
    document = RetrievalDocument(
        document_id=f"doc:{article}",
        node_id=f"node:{article}",
        node_type=NodeType.ARTICLE,
        text=text,
        citation=GoldCitation(
            node_id=f"node:{article}",
            article=article,
            regulation_title="학칙",
            source_file="test.pdf",
        ),
        citation_label=f"학칙, {article}",
        source_label="test.pdf p.1",
        source_file="test.pdf",
        source_pages=[1],
        metadata=document_metadata,
    )
    return BM25SearchHit(document=document, score=score, rank=rank)
