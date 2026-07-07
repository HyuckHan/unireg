"""Aggregate multiple experiment runs into paper-oriented summaries."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import cast


def summarize_runs(runs_dir: str | Path, out: str | Path) -> dict[str, object]:
    """Aggregate experiment run result files and write summary outputs."""

    root = Path(runs_dir)
    output_path = Path(out)
    results = [_load_result(path) for path in sorted(root.rglob("result.json"))]
    metrics = [
        {
            "run_name": str(result["config"].get("name", "")),
            **metric,
        }
        for result in results
        for metric in _dict_list(result.get("metrics"))
    ]
    tables = _aggregate_named_tables(results)
    payload = {
        "run_count": len(results),
        "runs_dir": str(root),
        "runs": [
            {
                "name": result["config"].get("name", ""),
                "result_path": result.get("_result_path", ""),
                "timestamp": result["metadata"].get("timestamp", ""),
                "git_commit": result["metadata"].get("git_commit", ""),
            }
            for result in results
        ],
        "metrics": metrics,
        "tables": tables,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(_summary_markdown(payload), encoding="utf-8")
    _write_json(output_path.with_suffix(".json"), payload)
    _write_csv(output_path.with_suffix(".csv"), metrics)
    return payload


def _load_result(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"Expected JSON object in {path}")
    result = cast(dict[str, object], payload)
    result["_result_path"] = str(path)
    return result


def _aggregate_named_tables(
    results: list[dict[str, object]],
) -> dict[str, list[dict[str, object]]]:
    tables: dict[str, list[dict[str, object]]] = {}
    for result in results:
        run_name = str(_object(result.get("config")).get("name", ""))
        for table_name, rows in _object(result.get("tables")).items():
            table_rows = _dict_list(rows)
            tables.setdefault(table_name, []).extend(
                {"run_name": run_name, **row} for row in table_rows
            )
    return tables


def _summary_markdown(payload: dict[str, object]) -> str:
    lines = [
        "# UniReg Experiment Summary",
        "",
        f"- Runs: {payload['run_count']}",
        f"- Source: `{payload['runs_dir']}`",
        "",
        "## Runs",
        "",
        "| Run | Timestamp | Git Commit | Result |",
        "| --- | --- | --- | --- |",
    ]
    for run in _dict_list(payload.get("runs")):
        lines.append(
            "| "
            f"{_escape(str(run.get('name', '')))} | "
            f"{_escape(str(run.get('timestamp', '')))} | "
            f"`{_escape(str(run.get('git_commit', '')))}` | "
            f"`{_escape(str(run.get('result_path', '')))}` |"
        )
    if not _dict_list(payload.get("runs")):
        lines.append("| none |  |  |  |")

    lines.extend(
        [
            "",
            "## Metrics",
            "",
            "| Run | Experiment | Group | Metric | Value | Status |",
            "| --- | --- | --- | --- | ---: | --- |",
        ]
    )
    for metric in _dict_list(payload.get("metrics")):
        lines.append(
            "| "
            f"{_escape(str(metric.get('run_name', '')))} | "
            f"{_escape(str(metric.get('experiment_type', '')))} | "
            f"{_escape(str(metric.get('group', '')))} | "
            f"{_escape(str(metric.get('metric', '')))} | "
            f"{_escape(str(metric.get('value', '')))} | "
            f"{_escape(str(metric.get('status', '')))} |"
        )

    lines.extend(["", "## Aggregated Tables", ""])
    for table_name, rows in sorted(_object(payload.get("tables")).items()):
        lines.append(f"### {table_name.replace('_', ' ').title()}")
        lines.append("")
        table_rows = _dict_list(rows)
        if not table_rows:
            lines.extend(["No rows.", ""])
            continue
        headers = list(table_rows[0].keys())
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("| " + " | ".join("---" for _ in headers) + " |")
        for row in table_rows:
            lines.append(
                "| "
                + " | ".join(_escape(str(row.get(header, ""))) for header in headers)
                + " |"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _object(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return cast(dict[str, object], value)
    return {}


def _dict_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [cast(dict[str, object], item) for item in value if isinstance(item, dict)]


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")
