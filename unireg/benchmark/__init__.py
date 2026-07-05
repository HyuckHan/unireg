"""UniRegBench benchmark loading, validation, and evaluation."""

from unireg.benchmark.evaluation import (
    BenchmarkRunResult,
    ParserCaseResult,
    ParserEvaluationResult,
    RetrievalEvaluationResult,
    RetrievalMetrics,
    evaluate_parser,
    evaluate_retrieval,
    write_benchmark_reports,
)
from unireg.benchmark.loader import (
    BenchmarkDataset,
    load_benchmark,
    load_parser_cases,
    load_questions,
    load_retrieval_predictions,
)
from unireg.benchmark.models import (
    Answerability,
    BenchmarkQuestion,
    GoldCitation,
    ParserBenchmarkCase,
    RetrievalPrediction,
)
from unireg.benchmark.validation import ValidationIssue, validate_benchmark

__all__ = [
    "Answerability",
    "BenchmarkDataset",
    "BenchmarkQuestion",
    "BenchmarkRunResult",
    "GoldCitation",
    "ParserBenchmarkCase",
    "ParserCaseResult",
    "ParserEvaluationResult",
    "RetrievalEvaluationResult",
    "RetrievalMetrics",
    "RetrievalPrediction",
    "ValidationIssue",
    "evaluate_parser",
    "evaluate_retrieval",
    "load_benchmark",
    "load_parser_cases",
    "load_questions",
    "load_retrieval_predictions",
    "validate_benchmark",
    "write_benchmark_reports",
]
