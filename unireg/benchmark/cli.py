"""Command-line interface for UniRegBench."""

from __future__ import annotations

import argparse
from pathlib import Path

from unireg.benchmark.evaluation import (
    BenchmarkRunResult,
    evaluate_parser,
    evaluate_retrieval,
    write_benchmark_reports,
)
from unireg.benchmark.loader import (
    load_benchmark,
    load_retrieval_predictions,
)
from unireg.benchmark.validation import validate_benchmark


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "validate":
        return _validate(args)
    if args.command == "evaluate-parser":
        return _evaluate_parser(args)
    if args.command == "evaluate-retrieval":
        return _evaluate_retrieval(args)
    if args.command == "run":
        return _run(args)
    parser.error(f"Unknown command: {args.command}")
    return 2


def _validate(args: argparse.Namespace) -> int:
    dataset = load_benchmark(args.benchmark_dir)
    issues = validate_benchmark(dataset)
    for issue in issues:
        print(f"{issue.code}: {issue.record_id or '-'}: {issue.message}")
    print(
        f"Validation: questions={len(dataset.questions)} "
        f"parser_cases={len(dataset.parser_cases)} issues={len(issues)}"
    )
    return 1 if issues else 0


def _evaluate_parser(args: argparse.Namespace) -> int:
    dataset = load_benchmark(args.benchmark_dir)
    result = BenchmarkRunResult(
        validation_issues=validate_benchmark(dataset),
        parser=evaluate_parser(dataset),
    )
    write_benchmark_reports(result, args.report_dir)
    print(f"Wrote benchmark reports: {args.report_dir}")
    if result.validation_issues:
        return 1
    if result.parser.ok_count != result.parser.case_count:
        return 1
    return 0


def _evaluate_retrieval(args: argparse.Namespace) -> int:
    dataset = load_benchmark(args.benchmark_dir)
    predictions = load_retrieval_predictions(args.predictions)
    result = BenchmarkRunResult(
        validation_issues=validate_benchmark(dataset),
        retrieval=evaluate_retrieval(dataset.questions, predictions),
    )
    write_benchmark_reports(result, args.report_dir)
    print(f"Wrote benchmark reports: {args.report_dir}")
    return 1 if result.validation_issues else 0


def _run(args: argparse.Namespace) -> int:
    dataset = load_benchmark(args.benchmark_dir)
    issues = validate_benchmark(dataset)
    retrieval = None
    if args.predictions is not None:
        retrieval = evaluate_retrieval(
            dataset.questions,
            load_retrieval_predictions(args.predictions),
        )
    parser_result = evaluate_parser(dataset)
    result = BenchmarkRunResult(
        validation_issues=issues,
        parser=parser_result,
        retrieval=retrieval,
    )
    write_benchmark_reports(result, args.report_dir)
    print(f"Wrote benchmark reports: {args.report_dir}")
    if issues:
        return 1
    return 0 if parser_result.ok_count == parser_result.case_count else 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run UniRegBench.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="Validate benchmark files.")
    _add_benchmark_dir(validate)

    parser_eval = subparsers.add_parser(
        "evaluate-parser",
        help="Evaluate parser output against benchmark parser cases.",
    )
    _add_benchmark_dir(parser_eval)
    _add_report_dir(parser_eval)

    retrieval_eval = subparsers.add_parser(
        "evaluate-retrieval",
        help="Evaluate ranked retrieval predictions against gold citations.",
    )
    _add_benchmark_dir(retrieval_eval)
    _add_report_dir(retrieval_eval)
    retrieval_eval.add_argument(
        "--predictions",
        type=Path,
        required=True,
        help="JSONL file containing retrieval predictions.",
    )

    run = subparsers.add_parser(
        "run",
        help="Validate and run all currently available benchmark evaluations.",
    )
    _add_benchmark_dir(run)
    _add_report_dir(run)
    run.add_argument(
        "--predictions",
        type=Path,
        default=None,
        help="Optional retrieval predictions JSONL file.",
    )

    return parser


def _add_benchmark_dir(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--benchmark-dir",
        type=Path,
        default=Path("benchmark"),
        help="Benchmark root directory.",
    )


def _add_report_dir(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=Path("benchmark/reports"),
        help="Directory for JSON, CSV, and Markdown reports.",
    )
