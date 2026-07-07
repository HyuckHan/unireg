from __future__ import annotations

import json
from pathlib import Path

from unireg.analysis import ErrorCategory, analyze_error_traces, classify_trace
from unireg.analysis.cli import main as analysis_main
from unireg.analysis.models import QATraceRecord
from unireg.analysis.reports import write_error_analysis_reports


def test_error_taxonomy_contains_required_categories() -> None:
    assert {category.value for category in ErrorCategory} == {
        "NO_ERROR",
        "PARSER_ERROR",
        "METADATA_ERROR",
        "RETRIEVAL_MISS",
        "RETRIEVAL_RANKING_ERROR",
        "CITATION_MISMATCH",
        "INSUFFICIENT_EVIDENCE",
        "MISSING_REGULATION",
        "COMPLETENESS_MISCLASSIFICATION",
        "HALLUCINATION",
        "UNSUPPORTED_ANSWER",
        "AMBIGUOUS_GOLD",
        "UNKNOWN_ERROR",
    }


def test_classifies_no_error_for_fully_grounded_trace() -> None:
    trace = _trace(
        gold=[_citation("제1조")],
        predicted=[_citation("제1조")],
        evidence=[_evidence("제1조", rank=1)],
    )

    classification = classify_trace(trace)

    assert classification.categories == (ErrorCategory.NO_ERROR,)
    assert classification.success is True


def test_classifies_single_label_citation_mismatch() -> None:
    trace = _trace(
        gold=[_citation("제1조")],
        predicted=[_citation("제2조")],
        evidence=[_evidence("제1조", rank=1), _evidence("제2조", rank=2)],
        citation_accuracy=0.0,
    )

    classification = classify_trace(trace)

    assert classification.categories == (ErrorCategory.CITATION_MISMATCH,)
    assert classification.success is False


def test_classifies_multi_label_retrieval_miss_and_missing_regulation() -> None:
    trace = _trace(
        answerability="missing_regulation",
        expected="missing_regulation",
        actual="missing_regulation",
        gold=[_citation("제9조")],
        predicted=[],
        evidence=[_evidence("제1조", rank=1, text="세부사항은 따로 정한다.")],
        citation_accuracy=0.0,
    )

    classification = classify_trace(trace)

    assert ErrorCategory.RETRIEVAL_MISS in classification.categories
    assert ErrorCategory.MISSING_REGULATION in classification.categories
    assert len(classification.categories) > 1


def test_classifies_missing_regulation_hallucination() -> None:
    trace = _trace(
        answerability="missing_regulation",
        expected="missing_regulation",
        actual="complete",
        gold=[_citation("제1조")],
        predicted=[_citation("제1조")],
        evidence=[_evidence("제1조", rank=1, text="세부사항은 따로 정한다.")],
        completeness_accuracy=0.0,
    )

    classification = classify_trace(trace)

    assert ErrorCategory.HALLUCINATION in classification.categories
    assert ErrorCategory.COMPLETENESS_MISCLASSIFICATION in classification.categories
    assert ErrorCategory.MISSING_REGULATION in classification.categories


def test_classifies_unsupported_answer_and_metadata_errors() -> None:
    trace = _trace(
        gold=[_citation("제1조")],
        predicted=[_citation("제999조")],
        evidence=[_evidence("제1조", rank=1)],
        citation_accuracy=0.0,
        groundedness=0.0,
    )

    classification = classify_trace(trace)

    assert ErrorCategory.UNSUPPORTED_ANSWER in classification.categories
    assert ErrorCategory.CITATION_MISMATCH in classification.categories


def test_report_generation_writes_json_csv_and_markdown(tmp_path: Path) -> None:
    trace_path = tmp_path / "traces.jsonl"
    _write_trace_jsonl(
        trace_path,
        [
            _trace(
                gold=[_citation("제1조")],
                predicted=[_citation("제1조")],
                evidence=[_evidence("제1조", rank=1)],
            ),
            _trace(
                question_id="Q2",
                gold=[_citation("제2조")],
                predicted=[_citation("제3조")],
                evidence=[_evidence("제2조", rank=1), _evidence("제3조", rank=2)],
                citation_accuracy=0.0,
            ),
        ],
    )

    report = analyze_error_traces(trace_path, benchmark_dir=None)
    write_error_analysis_reports(report, tmp_path / "error_analysis")

    payload = json.loads(
        (tmp_path / "error_analysis/error_analysis.json").read_text(encoding="utf-8")
    )
    markdown = (tmp_path / "error_analysis/error_analysis.md").read_text(
        encoding="utf-8"
    )

    assert payload["summary"]["trace_count"] == 2
    assert (tmp_path / "error_analysis/error_analysis.csv").exists()
    assert "Error Category | Count | Percentage" in markdown
    assert "Retriever | Recall@3 | QA Accuracy | Main Failure Mode" in markdown


def test_empty_trace_file_produces_empty_report(tmp_path: Path) -> None:
    trace_path = tmp_path / "empty.jsonl"
    trace_path.write_text("", encoding="utf-8")

    report = analyze_error_traces(trace_path, benchmark_dir=None)

    assert report.summary.trace_count == 0
    assert report.summary.success_count == 0
    assert report.summary.failure_count == 0


def test_malformed_trace_is_reported_without_stopping(tmp_path: Path) -> None:
    trace_path = tmp_path / "malformed.jsonl"
    trace_path.write_text(
        "{not-json}\n" + json.dumps(_trace_payload(), ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    report = analyze_error_traces(trace_path, benchmark_dir=None)

    assert report.summary.trace_count == 1
    assert report.summary.malformed_trace_count == 1
    assert report.load_issues[0].line_number == 1


def test_error_analysis_cli_writes_reports(tmp_path: Path) -> None:
    trace_path = tmp_path / "traces.jsonl"
    _write_trace_jsonl(
        trace_path,
        [
            _trace(
                gold=[_citation("제1조")],
                predicted=[_citation("제1조")],
                evidence=[_evidence("제1조", rank=1)],
            )
        ],
    )

    exit_code = analysis_main(
        [
            "--traces",
            str(trace_path),
            "--out",
            str(tmp_path / "out"),
            "--benchmark-dir",
            str(tmp_path / "missing-benchmark"),
        ]
    )

    assert exit_code == 0
    assert (tmp_path / "out/error_analysis.json").exists()


def _trace(
    *,
    question_id: str = "Q1",
    answerability: str = "answerable",
    expected: str = "complete",
    actual: str = "complete",
    gold: list[dict[str, object]],
    predicted: list[dict[str, object]],
    evidence: list[dict[str, object]],
    citation_accuracy: float = 1.0,
    groundedness: float = 1.0,
    completeness_accuracy: float = 1.0,
) -> QATraceRecord:
    evidence_package = {
        "package_id": f"EP_{question_id}",
        "question": "질문",
        "retriever": "bm25",
        "retrieval_scope": "question_source",
        "top_k": 5,
        "evidence": evidence,
        "metadata": {
            "question_id": question_id,
            "university_id": "university_test",
            "source_file": "test.pdf",
        },
    }
    evaluation = {
        "question_id": question_id,
        "answer_id": f"A_{question_id}",
        "answerability": answerability,
        "gold_citations": gold,
        "citation_accuracy": citation_accuracy,
        "groundedness": groundedness,
        "expected_completeness": expected,
        "actual_completeness": actual,
        "completeness_classification": completeness_accuracy,
        "hallucination_detected": False,
        "confidence": 1.0,
    }
    return QATraceRecord(
        line_number=1,
        answer_id=f"A_{question_id}",
        question_id=question_id,
        question="질문",
        answerability=answerability,
        gold_citations=gold,
        predicted_citations=predicted,
        retrieved_evidence=evidence,
        completeness_status=actual,
        grounded_answer="답변",
        evidence_package=evidence_package,
        retriever_metadata={"retriever": "bm25", "retrieval_scope": "question_source"},
        llm_adapter_metadata={"provider": "mock", "model": "mock-grounded-v1"},
        evaluation=evaluation,
        metadata={
            "university_id": "university_test",
            "source_file": "test.pdf",
        },
        raw=_trace_payload(
            question_id=question_id,
            answerability=answerability,
            actual=actual,
            gold=gold,
            predicted=predicted,
            evidence=evidence,
            evidence_package=evidence_package,
            evaluation=evaluation,
        ),
    )


def _trace_payload(
    *,
    question_id: str = "Q1",
    answerability: str = "answerable",
    actual: str = "complete",
    gold: list[dict[str, object]] | None = None,
    predicted: list[dict[str, object]] | None = None,
    evidence: list[dict[str, object]] | None = None,
    evidence_package: dict[str, object] | None = None,
    evaluation: dict[str, object] | None = None,
) -> dict[str, object]:
    active_gold = gold if gold is not None else [_citation("제1조")]
    active_predicted = predicted if predicted is not None else [_citation("제1조")]
    active_evidence = evidence if evidence is not None else [_evidence("제1조", rank=1)]
    active_package = evidence_package or {
        "package_id": f"EP_{question_id}",
        "question": "질문",
        "retriever": "bm25",
        "retrieval_scope": "question_source",
        "top_k": 5,
        "evidence": active_evidence,
        "metadata": {"question_id": question_id, "university_id": "university_test"},
    }
    active_evaluation = evaluation or {
        "question_id": question_id,
        "answer_id": f"A_{question_id}",
        "answerability": answerability,
        "gold_citations": active_gold,
        "citation_accuracy": 1.0,
        "groundedness": 1.0,
        "expected_completeness": "complete",
        "actual_completeness": actual,
        "completeness_classification": 1.0,
        "hallucination_detected": False,
    }
    return {
        "answer_id": f"A_{question_id}",
        "question": "질문",
        "answer": "답변",
        "citations": active_predicted,
        "evidence": active_evidence,
        "completeness_status": actual,
        "evidence_package": active_package,
        "llm_request": {"provider": "mock", "model": "mock-grounded-v1"},
        "evaluation": active_evaluation,
        "trace": {
            "question": "질문",
            "retrieved_evidence": active_evidence,
            "llm_input": {"provider": "mock", "model": "mock-grounded-v1"},
            "grounded_answer": {
                "answer": "답변",
                "citations": active_predicted,
                "completeness_status": actual,
                "confidence": 1.0,
            },
            "evaluation": active_evaluation,
        },
    }


def _write_trace_jsonl(path: Path, traces: list[QATraceRecord]) -> None:
    lines = [
        json.dumps(trace.raw, ensure_ascii=False, sort_keys=True) for trace in traces
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _citation(article: str) -> dict[str, object]:
    return {
        "article": article,
        "clause": None,
        "item": None,
        "sub_item": None,
        "node_id": None,
        "regulation_title": "학칙",
        "source_file": "test.pdf",
    }


def _evidence(
    article: str,
    *,
    rank: int,
    text: str | None = None,
) -> dict[str, object]:
    citation = _citation(article)
    return {
        "evidence_id": f"E_{article}",
        "rank": rank,
        "score": 1.0,
        "confidence": 1.0,
        "node_id": f"node:{article}",
        "node_type": "article",
        "text": text or f"{article} 근거",
        "citation": citation,
        "citation_label": f"학칙, {article}",
        "source_label": "test.pdf p.1",
        "source_file": "test.pdf",
        "source_pages": [1],
        "metadata": {"source_file": "test.pdf", "article_number": article},
        "incompleteness_flags": [],
    }
