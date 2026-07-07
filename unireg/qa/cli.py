"""Command-line interface for grounded QA."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from unireg.benchmark.loader import load_benchmark
from unireg.benchmark.validation import validate_benchmark
from unireg.qa.adapters import MockLLMAdapter
from unireg.qa.evaluation import evaluate_qa, write_qa_reports
from unireg.qa.pipeline import GroundedQAPipeline
from unireg.qa.retrievers import BM25EvidenceRetriever, BM25EvidenceRetrieverConfig
from unireg.retrieval.corpus import (
    DEFAULT_RETRIEVAL_UNIT_TYPES,
    parse_retrieval_unit_types,
)
from unireg.retrieval.runner import RetrievalScope


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return run(args)


def run(args: argparse.Namespace) -> int:
    dataset = load_benchmark(args.benchmark_dir)
    issues = validate_benchmark(dataset)
    for issue in issues:
        print(f"{issue.code}: {issue.record_id or '-'}: {issue.message}")
    if issues:
        return 1

    retriever = _build_retriever(args, dataset)
    pipeline = GroundedQAPipeline(
        retriever=retriever,
        llm_adapter=MockLLMAdapter(),
    )

    if args.benchmark:
        answers = [
            pipeline.answer(
                question.question,
                metadata={**question.metadata, "question_id": question.id},
            )
            for question in dataset.questions
        ]
        result = evaluate_qa(dataset.questions, answers)
        write_qa_reports(result, args.report_dir)
        metrics = result.metrics
        print(f"Wrote QA reports: {args.report_dir}")
        print(
            "QA: "
            f"questions={metrics.question_count} "
            f"citation_accuracy={metrics.citation_accuracy:.3f} "
            f"groundedness={metrics.groundedness:.3f} "
            "completeness_classification="
            f"{metrics.completeness_classification_accuracy:.3f} "
            f"hallucination_rate={metrics.hallucination_rate:.3f}"
        )
        return 0

    question = _read_question(args)
    answer = pipeline.answer(
        question,
        metadata=_single_question_metadata(args),
    )
    payload = answer.to_dict()
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"Wrote QA answer: {args.output}")
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run grounded QA.")
    parser.add_argument(
        "--question",
        type=Path,
        default=None,
        help="Path to a UTF-8 text file containing one question.",
    )
    parser.add_argument(
        "--question-text",
        default=None,
        help="Question text. Used when --question is not provided.",
    )
    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="Run QA over every benchmark question.",
    )
    parser.add_argument(
        "--benchmark-dir",
        type=Path,
        default=Path("benchmark"),
        help="Benchmark root directory.",
    )
    parser.add_argument(
        "--retriever",
        choices=["bm25"],
        default="bm25",
        help="Retriever backend.",
    )
    parser.add_argument(
        "--llm",
        choices=["mock"],
        default="mock",
        help="LLM adapter. Only mock is implemented in this milestone.",
    )
    parser.add_argument(
        "--scope",
        choices=[scope.value for scope in RetrievalScope],
        default=RetrievalScope.QUESTION_SOURCE.value,
        help="Retrieval scope.",
    )
    parser.add_argument(
        "--source-file",
        default=None,
        help="Optional source file filter for a single question.",
    )
    parser.add_argument(
        "--units",
        default=",".join(unit.value for unit in DEFAULT_RETRIEVAL_UNIT_TYPES),
        help="Comma-separated retrieval units: article,clause,item,sub_item.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of evidence items to retrieve.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional JSON output path for a single answer trace.",
    )
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=Path("benchmark/reports"),
        help="Directory for benchmark QA reports.",
    )
    return parser


def _build_retriever(
    args: argparse.Namespace,
    dataset,
) -> BM25EvidenceRetriever:
    if args.retriever != "bm25":
        raise ValueError(f"Unsupported retriever: {args.retriever}")
    return BM25EvidenceRetriever(
        dataset=dataset,
        config=BM25EvidenceRetrieverConfig(
            top_k=args.top_k,
            scope=RetrievalScope(args.scope),
            unit_types=parse_retrieval_unit_types(args.units),
        ),
    )


def _read_question(args: argparse.Namespace) -> str:
    if args.question is not None:
        return args.question.read_text(encoding="utf-8").strip()
    if args.question_text is not None:
        return args.question_text.strip()
    raise ValueError("Provide --question, --question-text, or --benchmark.")


def _single_question_metadata(args: argparse.Namespace) -> dict[str, str]:
    metadata: dict[str, str] = {}
    if args.source_file is not None:
        metadata["source_file"] = args.source_file
    return metadata
