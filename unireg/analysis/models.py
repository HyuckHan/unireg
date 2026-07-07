"""Dataclasses for grounded QA explainability reports."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from enum import StrEnum


class ErrorCategory(StrEnum):
    """Publication-oriented error categories for grounded QA failures."""

    NO_ERROR = "NO_ERROR"
    PARSER_ERROR = "PARSER_ERROR"
    METADATA_ERROR = "METADATA_ERROR"
    RETRIEVAL_MISS = "RETRIEVAL_MISS"
    RETRIEVAL_RANKING_ERROR = "RETRIEVAL_RANKING_ERROR"
    CITATION_MISMATCH = "CITATION_MISMATCH"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    MISSING_REGULATION = "MISSING_REGULATION"
    COMPLETENESS_MISCLASSIFICATION = "COMPLETENESS_MISCLASSIFICATION"
    HALLUCINATION = "HALLUCINATION"
    UNSUPPORTED_ANSWER = "UNSUPPORTED_ANSWER"
    AMBIGUOUS_GOLD = "AMBIGUOUS_GOLD"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


@dataclass(frozen=True, slots=True)
class TraceLoadIssue:
    """Non-fatal problem found while reading a QA trace JSONL file."""

    line_number: int
    message: str
    raw_line: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "line_number": self.line_number,
            "message": self.message,
            "raw_line": self.raw_line,
        }


@dataclass(frozen=True, slots=True)
class QATraceRecord:
    """Normalized view of one Milestone 13 QA trace."""

    line_number: int
    answer_id: str
    question_id: str
    question: str
    answerability: str
    gold_citations: list[dict[str, object]]
    predicted_citations: list[dict[str, object]]
    retrieved_evidence: list[dict[str, object]]
    completeness_status: str
    grounded_answer: str
    evidence_package: dict[str, object]
    retriever_metadata: dict[str, object]
    llm_adapter_metadata: dict[str, object]
    evaluation: dict[str, object]
    metadata: dict[str, object]
    raw: dict[str, object]

    @property
    def retriever(self) -> str:
        value = self.retriever_metadata.get("retriever")
        return value if isinstance(value, str) and value else "unknown"

    @property
    def university_id(self) -> str:
        for key in ("university_id", "institution", "source_file"):
            value = self.metadata.get(key)
            if isinstance(value, str) and value:
                return value
        return "unknown"

    @property
    def source_file(self) -> str:
        value = self.metadata.get("source_file")
        return value if isinstance(value, str) else ""

    def to_dict(self) -> dict[str, object]:
        return {
            "line_number": self.line_number,
            "answer_id": self.answer_id,
            "question_id": self.question_id,
            "question": self.question,
            "answerability": self.answerability,
            "gold_citations": self.gold_citations,
            "predicted_citations": self.predicted_citations,
            "retrieved_evidence": self.retrieved_evidence,
            "completeness_status": self.completeness_status,
            "grounded_answer": self.grounded_answer,
            "evidence_package": self.evidence_package,
            "retriever_metadata": self.retriever_metadata,
            "llm_adapter_metadata": self.llm_adapter_metadata,
            "evaluation": self.evaluation,
            "metadata": self.metadata,
        }


@dataclass(frozen=True, slots=True)
class ErrorClassification:
    """Error labels and diagnostics for one QA trace."""

    question_id: str
    answer_id: str
    categories: tuple[ErrorCategory, ...]
    primary_category: ErrorCategory
    success: bool
    reasons: tuple[str, ...]
    gold_hit_rank: int | None = None
    recall_at_3: float = 0.0
    citation_accuracy: float = 0.0
    groundedness: float = 0.0
    completeness_accuracy: float = 0.0

    def to_dict(self) -> dict[str, object]:
        return {
            "question_id": self.question_id,
            "answer_id": self.answer_id,
            "categories": [category.value for category in self.categories],
            "primary_category": self.primary_category.value,
            "success": self.success,
            "reasons": list(self.reasons),
            "gold_hit_rank": self.gold_hit_rank,
            "recall_at_3": self.recall_at_3,
            "citation_accuracy": self.citation_accuracy,
            "groundedness": self.groundedness,
            "completeness_accuracy": self.completeness_accuracy,
        }


@dataclass(frozen=True, slots=True)
class ErrorAnalysisRow:
    """Per-question report row."""

    trace: QATraceRecord
    classification: ErrorClassification

    def to_dict(self) -> dict[str, object]:
        return {
            "question_id": self.trace.question_id,
            "answer_id": self.trace.answer_id,
            "question": self.trace.question,
            "answerability": self.trace.answerability,
            "university_id": self.trace.university_id,
            "source_file": self.trace.source_file,
            "retriever": self.trace.retriever,
            "success": self.classification.success,
            "primary_category": self.classification.primary_category.value,
            "categories": [
                category.value for category in self.classification.categories
            ],
            "reasons": list(self.classification.reasons),
            "gold_hit_rank": self.classification.gold_hit_rank,
            "recall_at_3": self.classification.recall_at_3,
            "citation_accuracy": self.classification.citation_accuracy,
            "groundedness": self.classification.groundedness,
            "completeness_accuracy": self.classification.completeness_accuracy,
            "actual_completeness": self.trace.completeness_status,
        }


@dataclass(frozen=True, slots=True)
class BreakdownRow:
    """Aggregate accuracy row for a grouping."""

    key: str
    total: int
    success_count: int
    accuracy: float
    main_failure_mode: str
    recall_at_3: float | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "key": self.key,
            "total": self.total,
            "success_count": self.success_count,
            "accuracy": self.accuracy,
            "main_failure_mode": self.main_failure_mode,
            "recall_at_3": self.recall_at_3,
        }


@dataclass(frozen=True, slots=True)
class ErrorAnalysisSummary:
    """Aggregate counts for an error analysis run."""

    trace_count: int
    malformed_trace_count: int
    success_count: int
    failure_count: int
    category_distribution: dict[str, int]

    def to_dict(self) -> dict[str, object]:
        return {
            "trace_count": self.trace_count,
            "malformed_trace_count": self.malformed_trace_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "category_distribution": self.category_distribution,
        }


@dataclass(frozen=True, slots=True)
class ErrorAnalysisReport:
    """Complete error analysis output."""

    summary: ErrorAnalysisSummary
    rows: list[ErrorAnalysisRow]
    answerability_breakdown: list[BreakdownRow]
    retriever_breakdown: list[BreakdownRow]
    university_breakdown: list[BreakdownRow]
    top_failed_questions: list[dict[str, object]]
    representative_examples: dict[str, list[dict[str, object]]]
    load_issues: list[TraceLoadIssue] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "summary": self.summary.to_dict(),
            "answerability_breakdown": [
                row.to_dict() for row in self.answerability_breakdown
            ],
            "retriever_breakdown": [row.to_dict() for row in self.retriever_breakdown],
            "university_breakdown": [
                row.to_dict() for row in self.university_breakdown
            ],
            "top_failed_questions": self.top_failed_questions,
            "representative_examples": self.representative_examples,
            "load_issues": [issue.to_dict() for issue in self.load_issues],
            "rows": [row.to_dict() for row in self.rows],
        }


def category_counter(rows: list[ErrorAnalysisRow]) -> Counter[ErrorCategory]:
    """Count every category assignment, including multi-label failures."""

    counter: Counter[ErrorCategory] = Counter()
    for row in rows:
        counter.update(row.classification.categories)
    return counter
