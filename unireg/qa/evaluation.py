"""Evaluation for grounded QA outputs."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

from unireg.benchmark.models import Answerability, BenchmarkQuestion
from unireg.qa.citations import citation_is_supported, citation_matches_any
from unireg.qa.models import CompletenessStatus, GroundedAnswer


@dataclass(frozen=True, slots=True)
class QAEvaluationMetrics:
    """Aggregate QA metrics."""

    question_count: int
    citation_accuracy: float
    groundedness: float
    completeness_classification_accuracy: float
    hallucination_rate: float

    def to_dict(self) -> dict[str, object]:
        return {
            "question_count": self.question_count,
            "citation_accuracy": self.citation_accuracy,
            "groundedness": self.groundedness,
            "completeness_classification_accuracy": (
                self.completeness_classification_accuracy
            ),
            "hallucination_rate": self.hallucination_rate,
        }


@dataclass(frozen=True, slots=True)
class QAEvaluationResult:
    """QA evaluation result with traceable answers."""

    metrics: QAEvaluationMetrics
    per_question: list[dict[str, object]]
    answers: list[GroundedAnswer]

    def to_dict(self) -> dict[str, object]:
        return {
            "metrics": self.metrics.to_dict(),
            "per_question": self.per_question,
            "answers": [answer.to_dict() for answer in self.answers],
        }


def evaluate_qa(
    questions: list[BenchmarkQuestion],
    answers: list[GroundedAnswer],
) -> QAEvaluationResult:
    """Evaluate grounded answers against benchmark question metadata."""

    answer_by_question = {answer.question: answer for answer in answers}
    per_question: list[dict[str, object]] = []
    evaluated_answers: list[GroundedAnswer] = []

    for question in questions:
        answer = answer_by_question.get(question.question)
        if answer is None:
            row = _missing_answer_row(question)
            per_question.append(row)
            continue
        row = _evaluate_answer(question, answer)
        per_question.append(row)
        evaluated_answers.append(answer.with_evaluation(row))

    denominator = len(per_question) or 1
    metrics = QAEvaluationMetrics(
        question_count=len(per_question),
        citation_accuracy=sum(float(row["citation_accuracy"]) for row in per_question)
        / denominator,
        groundedness=sum(float(row["groundedness"]) for row in per_question)
        / denominator,
        completeness_classification_accuracy=sum(
            float(row["completeness_classification"]) for row in per_question
        )
        / denominator,
        hallucination_rate=sum(
            1.0 if row["hallucination_detected"] else 0.0 for row in per_question
        )
        / denominator,
    )
    return QAEvaluationResult(
        metrics=metrics,
        per_question=per_question,
        answers=evaluated_answers,
    )


def write_qa_reports(
    result: QAEvaluationResult,
    report_dir: str | Path,
    *,
    prefix: str = "qa_mock",
) -> None:
    """Write traceable QA JSON, CSV, and JSONL reports."""

    output_dir = Path(report_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / f"{prefix}_report.json", result.to_dict())
    _write_csv(output_dir / f"{prefix}_questions.csv", result.per_question)
    _write_answers_jsonl(output_dir / f"{prefix}_answers.jsonl", result.answers)


def _evaluate_answer(
    question: BenchmarkQuestion,
    answer: GroundedAnswer,
) -> dict[str, object]:
    citation_accuracy = _citation_accuracy(question, answer)
    groundedness = _groundedness(answer)
    expected = _expected_completeness(question.answerability)
    completeness = 1.0 if answer.completeness_status == expected else 0.0
    hallucination = _hallucination_detected(answer)
    return {
        "question_id": question.id,
        "answer_id": answer.answer_id,
        "answerability": question.answerability.value,
        "gold_citations": [citation.to_dict() for citation in question.gold_citations],
        "citation_accuracy": citation_accuracy,
        "groundedness": groundedness,
        "expected_completeness": expected.value,
        "actual_completeness": answer.completeness_status.value,
        "completeness_classification": completeness,
        "hallucination_detected": hallucination,
        "confidence": answer.confidence,
    }


def _missing_answer_row(question: BenchmarkQuestion) -> dict[str, object]:
    expected = _expected_completeness(question.answerability)
    return {
        "question_id": question.id,
        "answer_id": "",
        "answerability": question.answerability.value,
        "gold_citations": [citation.to_dict() for citation in question.gold_citations],
        "citation_accuracy": 0.0,
        "groundedness": 0.0,
        "expected_completeness": expected.value,
        "actual_completeness": "",
        "completeness_classification": 0.0,
        "hallucination_detected": False,
        "confidence": 0.0,
    }


def _citation_accuracy(
    question: BenchmarkQuestion,
    answer: GroundedAnswer,
) -> float:
    if not question.gold_citations:
        return 1.0 if not answer.citations else 0.0
    if not answer.citations:
        return 0.0
    return (
        1.0
        if any(
            citation_matches_any(citation, question.gold_citations)
            for citation in answer.citations
        )
        else 0.0
    )


def _groundedness(answer: GroundedAnswer) -> float:
    if not answer.citations:
        return 1.0 if answer.completeness_status == CompletenessStatus.UNKNOWN else 0.0
    return (
        1.0
        if all(
            citation_is_supported(citation, answer.evidence)
            for citation in answer.citations
        )
        else 0.0
    )


def _hallucination_detected(answer: GroundedAnswer) -> bool:
    if any(
        not citation_is_supported(citation, answer.evidence)
        for citation in answer.citations
    ):
        return True
    return (
        answer.completeness_status == CompletenessStatus.COMPLETE
        and not answer.citations
    )


def _expected_completeness(answerability: Answerability) -> CompletenessStatus:
    if answerability == Answerability.MISSING_REGULATION:
        return CompletenessStatus.MISSING_REGULATION
    if answerability == Answerability.PARTIALLY_ANSWERABLE:
        return CompletenessStatus.PARTIAL
    if answerability == Answerability.UNANSWERABLE:
        return CompletenessStatus.UNKNOWN
    return CompletenessStatus.COMPLETE


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fieldnames = [
        "question_id",
        "answer_id",
        "answerability",
        "gold_citations",
        "citation_accuracy",
        "groundedness",
        "expected_completeness",
        "actual_completeness",
        "completeness_classification",
        "hallucination_detected",
        "confidence",
    ]
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_answers_jsonl(path: Path, answers: list[GroundedAnswer]) -> None:
    lines = [json.dumps(answer.to_dict(), ensure_ascii=False) for answer in answers]
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
