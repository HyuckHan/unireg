"""Command-line interface for QA error analysis."""

from __future__ import annotations

import argparse
from pathlib import Path

from unireg.analysis.reports import write_error_analysis_reports
from unireg.analysis.runner import analyze_error_traces


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return run(args)


def run(args: argparse.Namespace) -> int:
    report = analyze_error_traces(
        args.traces,
        benchmark_dir=args.benchmark_dir,
    )
    write_error_analysis_reports(report, args.out)
    print(f"Wrote error analysis reports: {args.out}")
    print(
        "Error analysis: "
        f"traces={report.summary.trace_count} "
        f"success={report.summary.success_count} "
        f"failure={report.summary.failure_count} "
        f"malformed={report.summary.malformed_trace_count}"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analyze grounded QA trace failures.",
    )
    add_arguments(parser)
    return parser


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--traces",
        type=Path,
        required=True,
        help="Path to Milestone 13 QA answer trace JSONL.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Output directory for JSON, CSV, and Markdown reports.",
    )
    parser.add_argument(
        "--benchmark-dir",
        type=Path,
        default=Path("benchmark"),
        help=(
            "Optional benchmark root used to enrich older traces with "
            "answerability labels and gold citations."
        ),
    )
