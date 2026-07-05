"""Validation for UniRegBench datasets."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from unireg.benchmark.loader import BenchmarkDataset
from unireg.benchmark.models import Answerability, GoldCitation


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """A non-fatal benchmark validation issue."""

    code: str
    message: str
    record_id: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "message": self.message,
            "record_id": self.record_id,
        }


def validate_benchmark(dataset: BenchmarkDataset) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    issues.extend(_validate_questions(dataset))
    issues.extend(_validate_parser_cases(dataset))
    return issues


def _validate_questions(dataset: BenchmarkDataset) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    seen_ids: set[str] = set()
    for question in dataset.questions:
        if question.id in seen_ids:
            issues.append(
                ValidationIssue(
                    code="duplicate_question_id",
                    message=f"Duplicate question id: {question.id}",
                    record_id=question.id,
                )
            )
        seen_ids.add(question.id)
        if not question.question.strip():
            issues.append(
                ValidationIssue(
                    code="empty_question",
                    message="Question text must not be empty.",
                    record_id=question.id,
                )
            )
        if (
            _requires_gold_citation(question.answerability)
            and not question.gold_citations
        ):
            issues.append(
                ValidationIssue(
                    code="missing_gold_citation",
                    message="Answerable retrieval questions need gold citations.",
                    record_id=question.id,
                )
            )
        for citation in question.gold_citations:
            if not _citation_has_anchor(citation):
                issues.append(
                    ValidationIssue(
                        code="invalid_gold_citation",
                        message="Gold citation needs node_id or article.",
                        record_id=question.id,
                    )
                )
    return issues


def _validate_parser_cases(dataset: BenchmarkDataset) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    seen_ids: set[str] = set()
    for case in dataset.parser_cases:
        if case.id in seen_ids:
            issues.append(
                ValidationIssue(
                    code="duplicate_parser_case_id",
                    message=f"Duplicate parser case id: {case.id}",
                    record_id=case.id,
                )
            )
        seen_ids.add(case.id)
        source_path = _resolve_source_file(dataset.root, case.source_file)
        if not source_path.exists():
            issues.append(
                ValidationIssue(
                    code="missing_parser_source_file",
                    message=f"Parser source file does not exist: {case.source_file}",
                    record_id=case.id,
                )
            )
        for citation in case.required_citations:
            if not _citation_has_anchor(citation):
                issues.append(
                    ValidationIssue(
                        code="invalid_required_citation",
                        message="Required parser citation needs node_id or article.",
                        record_id=case.id,
                    )
                )
    return issues


def _requires_gold_citation(answerability: Answerability) -> bool:
    return answerability in {
        Answerability.ANSWERABLE,
        Answerability.PARTIALLY_ANSWERABLE,
        Answerability.COMPARISON,
        Answerability.MULTI_HOP,
    }


def _citation_has_anchor(citation: GoldCitation) -> bool:
    return citation.node_id is not None or citation.article is not None


def _resolve_source_file(benchmark_root: Path, source_file: str) -> Path:
    path = Path(source_file)
    if path.is_absolute():
        return path
    project_root = benchmark_root.parent
    return project_root / path
