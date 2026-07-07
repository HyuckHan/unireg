"""Report writers for QA explainability and error analysis."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from unireg.analysis.models import ErrorAnalysisReport


def write_error_analysis_reports(
    report: ErrorAnalysisReport,
    output_dir: str | Path,
) -> None:
    """Write JSON, CSV, and Markdown error-analysis reports."""

    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    _write_json(path / "error_analysis.json", report.to_dict())
    _write_csv(path / "error_analysis.csv", report)
    _write_markdown(path / "error_analysis.md", report)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _write_csv(path: Path, report: ErrorAnalysisReport) -> None:
    fieldnames = [
        "question_id",
        "answer_id",
        "answerability",
        "university_id",
        "source_file",
        "retriever",
        "success",
        "primary_category",
        "categories",
        "gold_hit_rank",
        "recall_at_3",
        "citation_accuracy",
        "groundedness",
        "completeness_accuracy",
        "actual_completeness",
        "question",
        "reasons",
    ]
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in report.rows:
            payload = row.to_dict()
            payload["categories"] = ";".join(payload["categories"])
            payload["reasons"] = " | ".join(payload["reasons"])
            writer.writerow({key: payload.get(key, "") for key in fieldnames})


def _write_markdown(path: Path, report: ErrorAnalysisReport) -> None:
    path.write_text(_markdown(report), encoding="utf-8")


def _markdown(report: ErrorAnalysisReport) -> str:
    summary = report.summary
    lines = [
        "# UniReg QA Error Analysis",
        "",
        "## Summary",
        "",
        f"- Traces: {summary.trace_count}",
        f"- Successful traces: {summary.success_count}",
        f"- Failed traces: {summary.failure_count}",
        f"- Malformed traces: {summary.malformed_trace_count}",
        "",
        "## Error Category Distribution",
        "",
        "| Error Category | Count | Percentage |",
        "| --- | ---: | ---: |",
    ]
    denominator = summary.trace_count or 1
    if summary.category_distribution:
        for category, count in sorted(summary.category_distribution.items()):
            lines.append(
                f"| `{category}` | {count} | {_percentage(count, denominator)} |"
            )
    else:
        lines.append("| `NO_ERROR` | 0 | 0.0% |")

    lines.extend(
        [
            "",
            "## Answerability Breakdown",
            "",
            "| Answerability Type | Accuracy | Major Error Type | Count |",
            "| --- | ---: | --- | ---: |",
        ]
    )
    for row in report.answerability_breakdown:
        lines.append(
            "| "
            f"{_escape(row.key)} | {_percentage(row.success_count, row.total)} | "
            f"`{row.main_failure_mode}` | {row.total} |"
        )
    if not report.answerability_breakdown:
        lines.append("| none | 0.0% | `UNKNOWN_ERROR` | 0 |")

    lines.extend(
        [
            "",
            "## Retriever Breakdown",
            "",
            "| Retriever | Recall@3 | QA Accuracy | Main Failure Mode | Count |",
            "| --- | ---: | ---: | --- | ---: |",
        ]
    )
    for row in report.retriever_breakdown:
        recall = "n/a" if row.recall_at_3 is None else f"{row.recall_at_3:.3f}"
        lines.append(
            "| "
            f"{_escape(row.key)} | {recall} | "
            f"{_percentage(row.success_count, row.total)} | "
            f"`{row.main_failure_mode}` | {row.total} |"
        )
    if not report.retriever_breakdown:
        lines.append("| none | n/a | 0.0% | `UNKNOWN_ERROR` | 0 |")

    lines.extend(
        [
            "",
            "## Per-University Breakdown",
            "",
            "| University | Accuracy | Main Failure Mode | Count |",
            "| --- | ---: | --- | ---: |",
        ]
    )
    for row in report.university_breakdown:
        lines.append(
            "| "
            f"{_escape(row.key)} | {_percentage(row.success_count, row.total)} | "
            f"`{row.main_failure_mode}` | {row.total} |"
        )
    if not report.university_breakdown:
        lines.append("| none | 0.0% | `UNKNOWN_ERROR` | 0 |")

    lines.extend(
        [
            "",
            "## Top Failed Questions",
            "",
            "| Question ID | Primary Error | Categories | Gold Hit Rank | Question |",
            "| --- | --- | --- | ---: | --- |",
        ]
    )
    for item in report.top_failed_questions[:10]:
        lines.append(
            "| "
            f"{_escape(str(item['question_id']))} | "
            f"`{item['primary_category']}` | "
            f"{_escape(', '.join(str(value) for value in item['categories']))} | "
            f"{item['gold_hit_rank'] or ''} | "
            f"{_escape(_truncate(str(item['question']), 100))} |"
        )
    if not report.top_failed_questions:
        lines.append("| none | `NO_ERROR` | none |  |  |")

    lines.extend(
        [
            "",
            "## Representative Examples",
            "",
        ]
    )
    if report.representative_examples:
        for category, examples in sorted(report.representative_examples.items()):
            lines.extend([f"### `{category}`", ""])
            for example in examples:
                reasons = " ".join(str(reason) for reason in example["reasons"])
                lines.append(
                    "- "
                    f"{example['question_id']}: "
                    f"{_truncate(str(example['question']), 120)} "
                    f"Reason: {_truncate(reasons, 180)}"
                )
            lines.append("")
    else:
        lines.append("No failed examples.")
        lines.append("")

    if report.load_issues:
        lines.extend(
            [
                "## Load Issues",
                "",
                "| Line | Issue |",
                "| ---: | --- |",
            ]
        )
        for issue in report.load_issues:
            lines.append(
                f"| {issue.line_number} | {_escape(_truncate(issue.message, 120))} |"
            )
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _percentage(numerator: int, denominator: int) -> str:
    return f"{(numerator / (denominator or 1)) * 100:.1f}%"


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _truncate(value: str, length: int) -> str:
    if len(value) <= length:
        return value
    return value[: length - 1].rstrip() + "..."
