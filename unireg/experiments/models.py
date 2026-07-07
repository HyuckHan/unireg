"""Dataclasses for reproducible UniReg experiments."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class ExperimentKind(StrEnum):
    """Supported experiment families."""

    PARSER_ACCURACY = "parser_accuracy"
    RETRIEVAL = "retrieval"
    GROUNDED_QA = "grounded_qa"
    MISSING_REGULATION = "missing_regulation"
    CROSS_UNIVERSITY = "cross_university"


class ExecutionMode(StrEnum):
    """How an experiment obtains system outputs."""

    RUN = "run"
    PRECOMPUTED = "precomputed"


@dataclass(frozen=True, slots=True)
class ExperimentConfig:
    """Normalized experiment configuration."""

    name: str
    experiment_types: tuple[ExperimentKind, ...]
    output_dir: Path
    config_path: Path | None = None
    corpus_location: Path | None = None
    benchmark_dir: Path | None = None
    benchmark_question_file: Path | None = None
    parser_output_location: Path | None = None
    retrieval_method: str = "bm25"
    qa_method: str = "mock"
    evaluation_metrics: tuple[str, ...] = ()
    random_seed: int | None = None
    notes: str = ""
    tags: tuple[str, ...] = ()
    parser: dict[str, object] = field(default_factory=dict)
    retrieval: dict[str, object] = field(default_factory=dict)
    qa: dict[str, object] = field(default_factory=dict)
    missing_regulation: dict[str, object] = field(default_factory=dict)
    cross_university: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "experiment_types": [
                experiment_type.value for experiment_type in self.experiment_types
            ],
            "output_dir": str(self.output_dir),
            "config_path": None if self.config_path is None else str(self.config_path),
            "corpus_location": (
                None if self.corpus_location is None else str(self.corpus_location)
            ),
            "benchmark_dir": (
                None if self.benchmark_dir is None else str(self.benchmark_dir)
            ),
            "benchmark_question_file": (
                None
                if self.benchmark_question_file is None
                else str(self.benchmark_question_file)
            ),
            "parser_output_location": (
                None
                if self.parser_output_location is None
                else str(self.parser_output_location)
            ),
            "retrieval_method": self.retrieval_method,
            "qa_method": self.qa_method,
            "evaluation_metrics": list(self.evaluation_metrics),
            "random_seed": self.random_seed,
            "notes": self.notes,
            "tags": list(self.tags),
            "parser": _stringify_paths(self.parser),
            "retrieval": _stringify_paths(self.retrieval),
            "qa": _stringify_paths(self.qa),
            "missing_regulation": _stringify_paths(self.missing_regulation),
            "cross_university": _stringify_paths(self.cross_university),
        }


@dataclass(frozen=True, slots=True)
class RunMetadata:
    """Reproducibility metadata saved with every experiment run."""

    timestamp: str
    config_path: str
    project_version: str
    git_commit: str
    python_version: str
    platform: str
    input_paths: dict[str, str]
    output_paths: dict[str, str]
    random_seed: int | None
    command_line: list[str]

    def to_dict(self) -> dict[str, object]:
        return {
            "timestamp": self.timestamp,
            "config_path": self.config_path,
            "project_version": self.project_version,
            "git_commit": self.git_commit,
            "python_version": self.python_version,
            "platform": self.platform,
            "input_paths": self.input_paths,
            "output_paths": self.output_paths,
            "random_seed": self.random_seed,
            "command_line": self.command_line,
        }


@dataclass(frozen=True, slots=True)
class MetricRecord:
    """One metric value in a paper-ready experiment table."""

    experiment_type: str
    metric: str
    value: float | str | None
    status: str = "available"
    group: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "experiment_type": self.experiment_type,
            "group": self.group,
            "metric": self.metric,
            "value": self.value,
            "status": self.status,
            "notes": self.notes,
        }


@dataclass(frozen=True, slots=True)
class ExperimentArtifact:
    """Path to a generated or consumed artifact."""

    name: str
    path: Path
    role: str

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "path": str(self.path),
            "role": self.role,
        }


@dataclass(frozen=True, slots=True)
class ExperimentRunResult:
    """Complete output of one experiment configuration."""

    config: ExperimentConfig
    metadata: RunMetadata
    metrics: list[MetricRecord]
    artifacts: list[ExperimentArtifact]
    tables: dict[str, list[dict[str, object]]]
    raw_results: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "config": self.config.to_dict(),
            "metadata": self.metadata.to_dict(),
            "metrics": [metric.to_dict() for metric in self.metrics],
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
            "tables": self.tables,
            "raw_results": self.raw_results,
        }


def unavailable_metric(
    experiment_type: ExperimentKind | str,
    metric: str,
    *,
    group: str = "",
    notes: str,
) -> MetricRecord:
    """Create a standardized unavailable metric record."""

    experiment_name = (
        experiment_type.value
        if isinstance(experiment_type, ExperimentKind)
        else experiment_type
    )
    return MetricRecord(
        experiment_type=experiment_name,
        group=group,
        metric=metric,
        value=None,
        status="unavailable",
        notes=notes,
    )


def _stringify_paths(value: dict[str, object]) -> dict[str, object]:
    converted: dict[str, object] = {}
    for key, item in value.items():
        if isinstance(item, Path):
            converted[key] = str(item)
        elif isinstance(item, tuple):
            converted[key] = list(item)
        else:
            converted[key] = item
    return converted
