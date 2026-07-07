"""Top-level UniReg command-line interface."""

from __future__ import annotations

import argparse
from pathlib import Path

from unireg.analysis.cli import add_arguments as add_error_analysis_arguments
from unireg.analysis.cli import run as run_error_analysis
from unireg.experiments.cli import add_arguments as add_experiment_arguments
from unireg.experiments.cli import run as run_experiment_command
from unireg.qa.cli import run as run_qa


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="UniReg command-line tools.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    qa = subparsers.add_parser("qa", help="Run grounded QA.")
    _add_qa_arguments(qa)
    analyze_errors = subparsers.add_parser(
        "analyze-errors",
        help="Analyze grounded QA trace failures.",
    )
    add_error_analysis_arguments(analyze_errors)
    experiment = subparsers.add_parser(
        "experiment",
        help="Run or summarize reproducible experiments.",
    )
    add_experiment_arguments(experiment)

    args = parser.parse_args(argv)
    if args.command == "qa":
        return run_qa(args)
    if args.command == "analyze-errors":
        return run_error_analysis(args)
    if args.command == "experiment":
        return run_experiment_command(args, argv)
    parser.error(f"Unknown command: {args.command}")
    return 2


def _add_qa_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--question", type=Path, default=None)
    parser.add_argument("--question-text", default=None)
    parser.add_argument("--benchmark", action="store_true")
    parser.add_argument("--benchmark-dir", type=Path, default=Path("benchmark"))
    parser.add_argument("--retriever", choices=["bm25"], default="bm25")
    parser.add_argument("--llm", choices=["mock"], default="mock")
    parser.add_argument(
        "--scope",
        choices=["corpus", "question_source"],
        default="question_source",
    )
    parser.add_argument("--source-file", default=None)
    parser.add_argument("--units", default="article,clause,item,sub_item")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--report-dir", type=Path, default=Path("benchmark/reports"))


if __name__ == "__main__":
    raise SystemExit(main())
