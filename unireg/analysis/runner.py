"""Run grounded QA error analysis and build aggregate reports."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from unireg.analysis.classifier import classify_trace
from unireg.analysis.loader import load_trace_records
from unireg.analysis.models import (
    BreakdownRow,
    ErrorAnalysisReport,
    ErrorAnalysisRow,
    ErrorAnalysisSummary,
    ErrorCategory,
    TraceLoadIssue,
    category_counter,
)


def analyze_error_traces(
    trace_path: str | Path,
    *,
    benchmark_dir: str | Path | None = None,
) -> ErrorAnalysisReport:
    """Load trace JSONL and produce deterministic error-analysis output."""

    records, issues = load_trace_records(trace_path, benchmark_dir=benchmark_dir)
    rows = [
        ErrorAnalysisRow(trace=record, classification=classify_trace(record))
        for record in records
    ]
    category_counts = category_counter(rows)
    summary = ErrorAnalysisSummary(
        trace_count=len(rows),
        malformed_trace_count=len(issues),
        success_count=sum(1 for row in rows if row.classification.success),
        failure_count=sum(1 for row in rows if not row.classification.success),
        category_distribution={
            category.value: category_counts.get(category, 0)
            for category in ErrorCategory
            if category_counts.get(category, 0)
        },
    )
    return ErrorAnalysisReport(
        summary=summary,
        rows=rows,
        answerability_breakdown=_breakdown(rows, "answerability"),
        retriever_breakdown=_breakdown(rows, "retriever", include_recall=True),
        university_breakdown=_breakdown(rows, "university"),
        top_failed_questions=_top_failed_questions(rows),
        representative_examples=_representative_examples(rows),
        load_issues=issues,
    )


def _breakdown(
    rows: list[ErrorAnalysisRow],
    field: str,
    *,
    include_recall: bool = False,
) -> list[BreakdownRow]:
    groups: dict[str, list[ErrorAnalysisRow]] = defaultdict(list)
    for row in rows:
        groups[_group_key(row, field)].append(row)
    breakdown_rows = [
        _breakdown_row(key, group, include_recall=include_recall)
        for key, group in sorted(groups.items())
    ]
    return breakdown_rows


def _breakdown_row(
    key: str,
    rows: list[ErrorAnalysisRow],
    *,
    include_recall: bool,
) -> BreakdownRow:
    total = len(rows)
    success_count = sum(1 for row in rows if row.classification.success)
    main_failure_mode = _main_failure_mode(rows)
    recall_at_3 = None
    if include_recall:
        recall_at_3 = _average(row.classification.recall_at_3 for row in rows)
    return BreakdownRow(
        key=key,
        total=total,
        success_count=success_count,
        accuracy=success_count / (total or 1),
        main_failure_mode=main_failure_mode,
        recall_at_3=recall_at_3,
    )


def _group_key(row: ErrorAnalysisRow, field: str) -> str:
    if field == "answerability":
        return row.trace.answerability or "unknown"
    if field == "retriever":
        return row.trace.retriever
    if field == "university":
        return row.trace.university_id
    raise ValueError(f"Unknown breakdown field: {field}")


def _main_failure_mode(rows: list[ErrorAnalysisRow]) -> str:
    counts: dict[ErrorCategory, int] = defaultdict(int)
    for row in rows:
        if row.classification.success:
            continue
        counts[row.classification.primary_category] += 1
    if not counts:
        return ErrorCategory.NO_ERROR.value
    category, _count = max(counts.items(), key=lambda item: (item[1], item[0].value))
    return category.value


def _top_failed_questions(rows: list[ErrorAnalysisRow]) -> list[dict[str, object]]:
    failed = [row for row in rows if not row.classification.success]
    failed.sort(
        key=lambda row: (
            len(row.classification.categories),
            row.classification.primary_category.value,
            row.trace.question_id,
        ),
        reverse=True,
    )
    return [_example_payload(row) for row in failed[:10]]


def _representative_examples(
    rows: list[ErrorAnalysisRow],
) -> dict[str, list[dict[str, object]]]:
    examples: dict[str, list[dict[str, object]]] = {}
    for category in ErrorCategory:
        if category == ErrorCategory.NO_ERROR:
            continue
        category_rows = [
            row for row in rows if category in row.classification.categories
        ]
        if not category_rows:
            continue
        examples[category.value] = [_example_payload(row) for row in category_rows[:3]]
    return examples


def _example_payload(row: ErrorAnalysisRow) -> dict[str, object]:
    return {
        "question_id": row.trace.question_id,
        "answer_id": row.trace.answer_id,
        "question": row.trace.question,
        "answerability": row.trace.answerability,
        "university_id": row.trace.university_id,
        "retriever": row.trace.retriever,
        "primary_category": row.classification.primary_category.value,
        "categories": [category.value for category in row.classification.categories],
        "reasons": list(row.classification.reasons),
        "gold_hit_rank": row.classification.gold_hit_rank,
        "actual_completeness": row.trace.completeness_status,
        "predicted_answer": row.trace.grounded_answer,
    }


def _average(values) -> float:
    items = [float(value) for value in values]
    return sum(items) / (len(items) or 1)


def report_load_issues(report: ErrorAnalysisReport) -> list[TraceLoadIssue]:
    """Return load issues for callers that want to surface warnings."""

    return report.load_issues
