"""Report and table writers for experiment runs."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from unireg.experiments.models import ExperimentRunResult, MetricRecord


def write_experiment_outputs(result: ExperimentRunResult) -> None:
    """Write machine-readable and human-readable experiment outputs."""

    output_dir = result.config.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "figures").mkdir(exist_ok=True)
    tables_dir = output_dir / "tables"
    tables_dir.mkdir(exist_ok=True)

    _write_json(output_dir / "result.json", result.to_dict())
    _write_json(output_dir / "metadata.json", result.metadata.to_dict())
    _write_metrics_csv(output_dir / "metrics.csv", result.metrics)
    _write_summary_markdown(output_dir / "summary.md", result)
    for table_name, rows in result.tables.items():
        _write_table_csv(tables_dir / f"{table_name}.csv", rows)
        _write_table_markdown(tables_dir / f"{table_name}.md", table_name, rows)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _write_metrics_csv(path: Path, metrics: list[MetricRecord]) -> None:
    fieldnames = [
        "experiment_type",
        "group",
        "metric",
        "value",
        "status",
        "notes",
    ]
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for metric in metrics:
            writer.writerow(metric.to_dict())


def _write_table_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_table_markdown(
    path: Path,
    table_name: str,
    rows: list[dict[str, object]],
) -> None:
    lines = [f"# {_title(table_name)}", ""]
    if not rows:
        lines.append("No rows.")
        path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        return
    headers = list(rows[0].keys())
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join("---" for _ in headers) + " |")
    for row in rows:
        values = [_format_cell(row.get(header)) for header in headers]
        lines.append("| " + " | ".join(values) + " |")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _write_summary_markdown(path: Path, result: ExperimentRunResult) -> None:
    lines = [
        f"# Experiment: {result.config.name}",
        "",
        "## Metadata",
        "",
        f"- Timestamp: `{result.metadata.timestamp}`",
        f"- Config: `{result.metadata.config_path}`",
        f"- Git commit: `{result.metadata.git_commit}`",
        f"- Python: `{result.metadata.python_version}`",
        f"- Platform: `{result.metadata.platform}`",
        "",
        "## Metrics",
        "",
        "| Experiment | Group | Metric | Value | Status | Notes |",
        "| --- | --- | --- | ---: | --- | --- |",
    ]
    for metric in result.metrics:
        lines.append(
            "| "
            f"{metric.experiment_type} | "
            f"{metric.group or ''} | "
            f"{metric.metric} | "
            f"{_format_cell(metric.value)} | "
            f"{metric.status} | "
            f"{_escape(metric.notes)} |"
        )
    if not result.metrics:
        lines.append("| none |  | none |  | unavailable | no metrics produced |")

    lines.extend(["", "## Tables", ""])
    for table_name in sorted(result.tables):
        lines.append(f"- `tables/{table_name}.md`")

    lines.extend(["", "## Artifacts", ""])
    for artifact in result.artifacts:
        lines.append(f"- `{artifact.name}` ({artifact.role}): `{artifact.path}`")
    if not result.artifacts:
        lines.append("- none")

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _format_cell(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6g}"
    return _escape(str(value))


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _title(value: str) -> str:
    return value.replace("_", " ").title()
