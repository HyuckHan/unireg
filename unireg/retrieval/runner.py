"""Retrieval evaluation runner for benchmark questions."""

from __future__ import annotations

import csv
import json
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from unireg.benchmark.evaluation import (
    RetrievalEvaluationResult,
    evaluate_retrieval,
)
from unireg.benchmark.loader import BenchmarkDataset
from unireg.benchmark.models import BenchmarkQuestion, RetrievalPrediction
from unireg.models import NodeType
from unireg.parser import RegulationParser
from unireg.retrieval.bm25 import BM25Index, BM25SearchHit
from unireg.retrieval.corpus import (
    DEFAULT_RETRIEVAL_UNIT_TYPES,
    RetrievalDocument,
    build_retrieval_documents_from_benchmark,
)


class RetrievalScope(StrEnum):
    """Supported retrieval corpus scopes."""

    CORPUS = "corpus"
    QUESTION_SOURCE = "question_source"


@dataclass(frozen=True, slots=True, kw_only=True)
class RetrievalRunConfig:
    """Configuration for a deterministic retrieval run."""

    method: str = "bm25"
    top_k: int = 5
    scope: RetrievalScope = RetrievalScope.QUESTION_SOURCE
    unit_types: tuple[NodeType, ...] = DEFAULT_RETRIEVAL_UNIT_TYPES

    def to_dict(self) -> dict[str, object]:
        return {
            "method": self.method,
            "top_k": self.top_k,
            "scope": self.scope.value,
            "unit_types": [unit_type.value for unit_type in self.unit_types],
        }


@dataclass(frozen=True, slots=True)
class RetrievalRunResult:
    """Complete output from one retrieval run."""

    config: RetrievalRunConfig
    document_count: int
    predictions: list[RetrievalPrediction]
    evaluation: RetrievalEvaluationResult
    hits_by_question: dict[str, list[BM25SearchHit]]
    per_university: list[dict[str, object]]

    def to_dict(self) -> dict[str, object]:
        return {
            "config": self.config.to_dict(),
            "document_count": self.document_count,
            "predictions": [prediction.to_dict() for prediction in self.predictions],
            "evaluation": self.evaluation.to_dict(),
            "hits_by_question": {
                question_id: [hit.to_dict() for hit in hits]
                for question_id, hits in self.hits_by_question.items()
            },
            "per_university": self.per_university,
        }


class BM25RetrievalRunner:
    """Run the BM25 baseline against benchmark questions."""

    def __init__(
        self,
        *,
        parser: RegulationParser | None = None,
        config: RetrievalRunConfig | None = None,
    ) -> None:
        self._parser = parser or RegulationParser()
        self._config = config or RetrievalRunConfig()

    def run(self, dataset: BenchmarkDataset) -> RetrievalRunResult:
        documents = build_retrieval_documents_from_benchmark(
            dataset,
            parser=self._parser,
            unit_types=self._config.unit_types,
        )
        index = BM25Index(documents)
        predictions: list[RetrievalPrediction] = []
        hits_by_question: dict[str, list[BM25SearchHit]] = {}

        for question in dataset.questions:
            hits = index.search(
                question.question,
                top_k=self._config.top_k,
                filter_document=self._document_filter(question),
            )
            hits_by_question[question.id] = hits
            predictions.append(
                RetrievalPrediction(
                    question_id=question.id,
                    ranked_citations=[hit.document.citation for hit in hits],
                    metadata={
                        "method": self._config.method,
                        "scope": self._config.scope.value,
                        "unit_types": ",".join(
                            unit_type.value for unit_type in self._config.unit_types
                        ),
                    },
                )
            )

        evaluation = evaluate_retrieval(dataset.questions, predictions)
        return RetrievalRunResult(
            config=self._config,
            document_count=len(documents),
            predictions=predictions,
            evaluation=evaluation,
            hits_by_question=hits_by_question,
            per_university=_aggregate_by_metadata(
                dataset.questions,
                evaluation,
                key="university_id",
            ),
        )

    def _document_filter(
        self,
        question: BenchmarkQuestion,
    ) -> Callable[[RetrievalDocument], bool] | None:
        if self._config.scope == RetrievalScope.CORPUS:
            return None
        source_file = _question_source_file(question)
        if source_file is None:
            return None
        expected = Path(source_file).resolve()
        return lambda document: Path(document.source_file).resolve() == expected


def write_retrieval_run_reports(
    result: RetrievalRunResult,
    report_dir: str | Path,
    *,
    predictions_path: str | Path | None = None,
) -> None:
    """Write reproducible JSON, CSV, and JSONL retrieval artifacts."""

    output_dir = Path(report_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "retrieval_bm25_report.json", result.to_dict())
    _write_question_csv(output_dir / "retrieval_bm25_questions.csv", result)
    _write_hits_csv(output_dir / "retrieval_bm25_hits.csv", result)
    if predictions_path is not None:
        _write_predictions_jsonl(Path(predictions_path), result.predictions)


def _question_source_file(question: BenchmarkQuestion) -> str | None:
    if source_file := question.metadata.get("source_file"):
        return source_file
    for citation in question.gold_citations:
        if citation.source_file is not None:
            return citation.source_file
    return None


def _aggregate_by_metadata(
    questions: list[BenchmarkQuestion],
    evaluation: RetrievalEvaluationResult,
    *,
    key: str,
) -> list[dict[str, object]]:
    question_by_id = {question.id: question for question in questions}
    rows_by_group: dict[str, list[dict[str, object]]] = {}
    for row in evaluation.per_question:
        question_id = str(row["id"])
        question = question_by_id[question_id]
        group = question.metadata.get(key, "unknown")
        rows_by_group.setdefault(group, []).append(row)

    return [
        {
            "group": group,
            "question_count": len(rows),
            "recall_at_1": _average(float(row["recall_at_1"]) for row in rows),
            "recall_at_3": _average(float(row["recall_at_3"]) for row in rows),
            "recall_at_5": _average(float(row["recall_at_5"]) for row in rows),
            "mrr": _average(float(row["reciprocal_rank"]) for row in rows),
            "ndcg_at_5": _average(float(row["ndcg_at_5"]) for row in rows),
        }
        for group, rows in sorted(rows_by_group.items())
    ]


def _average(values: Iterable[float]) -> float:
    collected = list(values)
    if not collected:
        return 0.0
    return sum(collected) / len(collected)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _write_question_csv(path: Path, result: RetrievalRunResult) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "id",
                "answerability",
                "hit_rank",
                "reciprocal_rank",
                "recall_at_1",
                "recall_at_3",
                "recall_at_5",
                "ndcg_at_5",
            ],
        )
        writer.writeheader()
        for row in result.evaluation.per_question:
            writer.writerow(row)


def _write_hits_csv(path: Path, result: RetrievalRunResult) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "question_id",
                "rank",
                "score",
                "node_id",
                "node_type",
                "citation_label",
                "source_file",
                "source_label",
            ],
        )
        writer.writeheader()
        for question_id, hits in result.hits_by_question.items():
            for hit in hits:
                writer.writerow(
                    {
                        "question_id": question_id,
                        "rank": hit.rank,
                        "score": f"{hit.score:.8f}",
                        "node_id": hit.document.node_id,
                        "node_type": hit.document.node_type.value,
                        "citation_label": hit.document.citation_label,
                        "source_file": hit.document.source_file,
                        "source_label": hit.document.source_label,
                    }
                )


def _write_predictions_jsonl(
    path: Path,
    predictions: list[RetrievalPrediction],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        json.dumps(prediction.to_dict(), ensure_ascii=False)
        for prediction in predictions
    ]
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
