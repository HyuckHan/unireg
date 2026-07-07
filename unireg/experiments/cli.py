"""Command-line interface for UniReg experiments."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from unireg.experiments.runner import run_experiment
from unireg.experiments.summarize import summarize_runs


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return run(args, argv if argv is not None else sys.argv[1:])


def run(args: argparse.Namespace, argv: list[str] | None = None) -> int:
    if args.experiment_command == "run":
        result = run_experiment(args.config, command_line=["experiment", *(argv or [])])
        print(f"Wrote experiment run: {result.config.output_dir}")
        return 0
    if args.experiment_command == "summarize":
        summarize_runs(args.runs, args.out)
        print(f"Wrote experiment summary: {args.out}")
        return 0
    raise ValueError(f"Unknown experiment command: {args.experiment_command}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run UniReg experiments.")
    add_arguments(parser)
    return parser


def add_arguments(parser: argparse.ArgumentParser) -> None:
    subparsers = parser.add_subparsers(dest="experiment_command", required=True)
    run_parser = subparsers.add_parser("run", help="Run an experiment config.")
    run_parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Path to a JSON experiment config.",
    )
    summarize_parser = subparsers.add_parser(
        "summarize",
        help="Aggregate experiment runs.",
    )
    summarize_parser.add_argument(
        "--runs",
        type=Path,
        required=True,
        help="Directory containing experiment run result.json files.",
    )
    summarize_parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Markdown summary output path.",
    )
