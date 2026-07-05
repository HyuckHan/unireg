"""Load UniRegBench JSONL files."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from unireg.benchmark.models import (
    BenchmarkQuestion,
    ParserBenchmarkCase,
    RetrievalPrediction,
)


@dataclass(frozen=True, slots=True)
class BenchmarkDataset:
    """Loaded benchmark dataset."""

    root: Path
    questions: list[BenchmarkQuestion]
    parser_cases: list[ParserBenchmarkCase]


def load_benchmark(root: str | Path) -> BenchmarkDataset:
    benchmark_root = Path(root)
    return BenchmarkDataset(
        root=benchmark_root,
        questions=load_questions(benchmark_root / "questions"),
        parser_cases=load_parser_cases(benchmark_root / "parser"),
    )


def load_questions(path: str | Path) -> list[BenchmarkQuestion]:
    return _load_jsonl_dir(Path(path), BenchmarkQuestion.from_dict)


def load_parser_cases(path: str | Path) -> list[ParserBenchmarkCase]:
    return _load_jsonl_dir(Path(path), ParserBenchmarkCase.from_dict)


def load_retrieval_predictions(path: str | Path) -> list[RetrievalPrediction]:
    return _load_jsonl_file(Path(path), RetrievalPrediction.from_dict)


def _load_jsonl_dir[T](
    path: Path,
    factory: Callable[[dict[str, object]], T],
) -> list[T]:
    if not path.exists():
        return []
    values: list[T] = []
    for file_path in sorted(path.glob("*.jsonl")):
        values.extend(_load_jsonl_file(file_path, factory))
    return values


def _load_jsonl_file[T](
    path: Path,
    factory: Callable[[dict[str, object]], T],
) -> list[T]:
    values: list[T] = []
    with path.open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSONL") from exc
            if not isinstance(payload, dict):
                raise TypeError(f"{path}:{line_number}: expected JSON object")
            values.append(factory(payload))
    return values
