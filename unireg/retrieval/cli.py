"""Command-line interface for deterministic retrieval baselines."""

from __future__ import annotations

import argparse
from pathlib import Path

from unireg.benchmark.loader import load_benchmark
from unireg.benchmark.validation import validate_benchmark
from unireg.retrieval.corpus import (
    DEFAULT_RETRIEVAL_UNIT_TYPES,
    parse_retrieval_unit_types,
)
from unireg.retrieval.runner import (
    BM25RetrievalRunner,
    RetrievalRunConfig,
    RetrievalScope,
    write_retrieval_run_reports,
)


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "bm25":
        return _run_bm25(args)
    parser.error(f"Unknown command: {args.command}")
    return 2


def _run_bm25(args: argparse.Namespace) -> int:
    dataset = load_benchmark(args.benchmark_dir)
    issues = validate_benchmark(dataset)
    for issue in issues:
        print(f"{issue.code}: {issue.record_id or '-'}: {issue.message}")
    if issues:
        return 1

    config = RetrievalRunConfig(
        top_k=args.top_k,
        scope=RetrievalScope(args.scope),
        unit_types=parse_retrieval_unit_types(args.units),
    )
    result = BM25RetrievalRunner(config=config).run(dataset)
    write_retrieval_run_reports(
        result,
        args.report_dir,
        predictions_path=args.predictions,
    )
    print(f"Wrote retrieval reports: {args.report_dir}")
    print(f"Wrote retrieval predictions: {args.predictions}")
    print(
        "BM25: "
        f"questions={result.evaluation.metrics.evaluated_question_count} "
        f"documents={result.document_count} "
        f"Recall@1={result.evaluation.metrics.recall_at_1:.3f} "
        f"Recall@3={result.evaluation.metrics.recall_at_3:.3f} "
        f"Recall@5={result.evaluation.metrics.recall_at_5:.3f} "
        f"MRR={result.evaluation.metrics.mrr:.3f} "
        f"nDCG@5={result.evaluation.metrics.ndcg_at_5:.3f}"
    )
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run UniReg retrieval baselines.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    bm25 = subparsers.add_parser("bm25", help="Run the deterministic BM25 baseline.")
    bm25.add_argument(
        "--benchmark-dir",
        type=Path,
        default=Path("benchmark"),
        help="Benchmark root directory.",
    )
    bm25.add_argument(
        "--report-dir",
        type=Path,
        default=Path("benchmark/reports"),
        help="Directory for retrieval CSV and JSON reports.",
    )
    bm25.add_argument(
        "--predictions",
        type=Path,
        default=Path("benchmark/retrieval/predictions.bm25.jsonl"),
        help="Output JSONL path for ranked retrieval predictions.",
    )
    bm25.add_argument(
        "--units",
        default=",".join(unit.value for unit in DEFAULT_RETRIEVAL_UNIT_TYPES),
        help="Comma-separated retrieval units: article,clause,item,sub_item.",
    )
    bm25.add_argument(
        "--scope",
        choices=[scope.value for scope in RetrievalScope],
        default=RetrievalScope.QUESTION_SOURCE.value,
        help="Search the full corpus or only the benchmark question source file.",
    )
    bm25.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of ranked citations to emit per question.",
    )
    return parser
