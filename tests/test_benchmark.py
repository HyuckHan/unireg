from __future__ import annotations

import json
from pathlib import Path

from unireg.benchmark.cli import main
from unireg.benchmark.evaluation import evaluate_parser, evaluate_retrieval
from unireg.benchmark.loader import (
    load_benchmark,
    load_retrieval_predictions,
)
from unireg.benchmark.models import GoldCitation, RetrievalPrediction
from unireg.benchmark.validation import validate_benchmark

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_DIR = PROJECT_ROOT / "benchmark"
EXPECTED_UNIVERSITY_IDS = {
    "university_dongduk",
    "university_dongyang",
    "university_duksung",
    "university_kwangwoon",
    "university_seoulwomen",
}


def test_benchmark_loader_and_validation_accept_official_dataset() -> None:
    dataset = load_benchmark(BENCHMARK_DIR)

    issues = validate_benchmark(dataset)

    assert issues == []
    assert len(dataset.questions) == 20
    assert len(dataset.parser_cases) == 5
    assert {
        question.metadata["university_id"] for question in dataset.questions
    } == EXPECTED_UNIVERSITY_IDS
    assert {
        case.metadata["university_id"] for case in dataset.parser_cases
    } == EXPECTED_UNIVERSITY_IDS
    assert all(
        citation.source_file
        for question in dataset.questions
        for citation in question.gold_citations
    )


def test_retrieval_evaluation_computes_recall_and_mrr() -> None:
    dataset = load_benchmark(BENCHMARK_DIR)
    predictions = load_retrieval_predictions(
        BENCHMARK_DIR / "retrieval/predictions.sample.jsonl"
    )

    result = evaluate_retrieval(dataset.questions, predictions)

    assert result.metrics.question_count == 20
    assert result.metrics.evaluated_question_count == 20
    assert result.metrics.recall_at_1 == 1.0
    assert result.metrics.recall_at_3 == 1.0
    assert result.metrics.recall_at_5 == 1.0
    assert result.metrics.mrr == 1.0


def test_retrieval_evaluation_uses_source_file_to_disambiguate_citations() -> None:
    dataset = load_benchmark(BENCHMARK_DIR)
    question = next(
        item for item in dataset.questions if item.id == "Q_DONGDUK_GRAD_CREDITS_001"
    )
    wrong_university_prediction = RetrievalPrediction(
        question_id=question.id,
        ranked_citations=[
            GoldCitation(
                article="제32조",
                clause="2",
                regulation_title="학칙",
                source_file="unireg-eval/university_kwangwoon/학칙.pdf",
            )
        ],
    )

    result = evaluate_retrieval([question], [wrong_university_prediction])

    assert result.metrics.recall_at_1 == 0.0
    assert result.metrics.mrr == 0.0


def test_parser_evaluation_runs_against_tracked_sample_pdf() -> None:
    dataset = load_benchmark(BENCHMARK_DIR)

    result = evaluate_parser(dataset)

    assert result.case_count == 5
    assert result.ok_count == 5
    assert result.article_extraction_accuracy == 1.0
    assert result.clause_extraction_accuracy == 1.0
    assert result.hierarchy_preservation == 1.0
    assert result.citation_generation == 1.0
    assert result.metadata_completeness == 1.0


def test_benchmark_cli_run_writes_reproducible_reports(tmp_path: Path) -> None:
    report_dir = tmp_path / "reports"

    exit_code = main(
        [
            "run",
            "--benchmark-dir",
            str(BENCHMARK_DIR),
            "--predictions",
            str(BENCHMARK_DIR / "retrieval/predictions.sample.jsonl"),
            "--report-dir",
            str(report_dir),
        ]
    )

    assert exit_code == 0
    report = json.loads((report_dir / "benchmark_report.json").read_text())
    assert report["validation_issues"] == []
    assert report["parser"]["ok_count"] == 5
    assert report["retrieval"]["metrics"]["question_count"] == 20
    assert report["retrieval"]["metrics"]["mrr"] == 1.0
    assert (report_dir / "parser_report.csv").exists()
    assert (report_dir / "retrieval_report.csv").exists()
    assert (report_dir / "benchmark_report.md").exists()
