"""Experiment configuration loading and validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from unireg.experiments.models import ExecutionMode, ExperimentConfig, ExperimentKind

_PATH_FIELDS = {
    "corpus_location",
    "benchmark_dir",
    "benchmark_question_file",
    "parser_output_location",
    "output_dir",
}

_SECTION_PATH_FIELDS = {
    "report_path",
    "predictions_path",
    "traces_path",
    "error_analysis_path",
    "eval_dir",
}


def load_experiment_config(path: str | Path) -> ExperimentConfig:
    """Load a JSON experiment config."""

    config_path = Path(path)
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("Experiment config must be a JSON object.")
    config = _config_from_dict(cast(dict[str, object], payload), config_path)
    validate_config(config)
    return config


def validate_config(config: ExperimentConfig) -> None:
    """Validate required fields and referenced inputs."""

    if not config.name:
        raise ValueError("Experiment config requires a non-empty name.")
    if not config.experiment_types:
        raise ValueError("Experiment config requires at least one experiment type.")
    if config.retrieval_method != "bm25":
        raise ValueError("Only retrieval_method='bm25' is supported in Milestone 14.")
    if config.qa_method != "mock":
        raise ValueError("Only qa_method='mock' is supported in Milestone 14.")

    for experiment_type in config.experiment_types:
        if experiment_type == ExperimentKind.PARSER_ACCURACY:
            _validate_parser(config)
        elif experiment_type == ExperimentKind.RETRIEVAL:
            _validate_retrieval(config)
        elif experiment_type == ExperimentKind.GROUNDED_QA:
            _validate_qa(config)
        elif experiment_type == ExperimentKind.MISSING_REGULATION:
            _validate_missing_regulation(config)
        elif experiment_type == ExperimentKind.CROSS_UNIVERSITY:
            _validate_cross_university(config)


def _config_from_dict(
    payload: dict[str, object],
    config_path: Path,
) -> ExperimentConfig:
    base = config_path.parent
    experiment_types = tuple(
        ExperimentKind(item) for item in _str_list(payload, "experiment_types")
    )
    return ExperimentConfig(
        name=_required_str(payload, "name"),
        experiment_types=experiment_types,
        output_dir=_path(payload.get("output_dir", "experiments/runs/default"), base),
        config_path=config_path,
        corpus_location=_optional_path(payload.get("corpus_location"), base),
        benchmark_dir=_optional_path(payload.get("benchmark_dir"), base),
        benchmark_question_file=_optional_path(
            payload.get("benchmark_question_file"),
            base,
        ),
        parser_output_location=_optional_path(
            payload.get("parser_output_location"),
            base,
        ),
        retrieval_method=_str(payload.get("retrieval_method"), default="bm25"),
        qa_method=_str(payload.get("qa_method"), default="mock"),
        evaluation_metrics=tuple(_str_list(payload, "evaluation_metrics")),
        random_seed=_optional_int(payload.get("random_seed")),
        notes=_str(payload.get("notes"), default=""),
        tags=tuple(_str_list(payload, "tags")),
        parser=_section(payload, "parser", base),
        retrieval=_section(payload, "retrieval", base),
        qa=_section(payload, "qa", base),
        missing_regulation=_section(payload, "missing_regulation", base),
        cross_university=_section(payload, "cross_university", base),
    )


def _validate_parser(config: ExperimentConfig) -> None:
    mode = _mode(config.parser)
    if mode == ExecutionMode.RUN:
        _require_existing_path(config.benchmark_dir, "benchmark_dir")
    else:
        _require_existing_path(
            _path_value(config.parser, "report_path"), "parser.report_path"
        )


def _validate_retrieval(config: ExperimentConfig) -> None:
    mode = _mode(config.retrieval)
    if mode == ExecutionMode.RUN:
        _require_existing_path(config.benchmark_dir, "benchmark_dir")
    else:
        _require_existing_path(
            _path_value(config.retrieval, "report_path"),
            "retrieval.report_path",
        )


def _validate_qa(config: ExperimentConfig) -> None:
    mode = _mode(config.qa)
    if mode == ExecutionMode.RUN:
        _require_existing_path(config.benchmark_dir, "benchmark_dir")
    else:
        _require_existing_path(_path_value(config.qa, "report_path"), "qa.report_path")


def _validate_missing_regulation(config: ExperimentConfig) -> None:
    mode = _mode(config.missing_regulation)
    if mode == ExecutionMode.PRECOMPUTED and _path_value(
        config.missing_regulation,
        "error_analysis_path",
    ):
        _require_existing_path(
            _path_value(config.missing_regulation, "error_analysis_path"),
            "missing_regulation.error_analysis_path",
        )
        return
    traces_path = _path_value(config.missing_regulation, "traces_path")
    if traces_path is None:
        traces_path = _path_value(config.qa, "traces_path")
    _require_existing_path(traces_path, "missing_regulation.traces_path")


def _validate_cross_university(config: ExperimentConfig) -> None:
    mode = _mode(config.cross_university)
    if mode == ExecutionMode.RUN:
        eval_dir = _path_value(config.cross_university, "eval_dir")
        if eval_dir is None:
            eval_dir = config.corpus_location
        _require_existing_path(eval_dir, "cross_university.eval_dir")
    else:
        _require_existing_path(
            _path_value(config.cross_university, "report_path"),
            "cross_university.report_path",
        )


def _mode(section: dict[str, object]) -> ExecutionMode:
    value = section.get("mode", ExecutionMode.RUN.value)
    if not isinstance(value, str):
        raise TypeError("Experiment section mode must be a string.")
    return ExecutionMode(value)


def _path_value(section: dict[str, object], key: str) -> Path | None:
    value = section.get(key)
    return value if isinstance(value, Path) else None


def _require_existing_path(path: Path | None, label: str) -> None:
    if path is None:
        raise ValueError(f"Missing required input path: {label}.")
    if not path.exists():
        raise FileNotFoundError(f"Missing required input path for {label}: {path}")


def _section(
    payload: dict[str, object],
    key: str,
    base: Path,
) -> dict[str, object]:
    value = payload.get(key, {})
    if not isinstance(value, dict):
        raise TypeError(f"Expected '{key}' to be an object.")
    section = dict(cast(dict[str, object], value))
    for field in _SECTION_PATH_FIELDS:
        if field in section:
            section[field] = _optional_path(section[field], base)
    return section


def _path(value: object, base: Path) -> Path:
    if not isinstance(value, str):
        raise TypeError("Expected path value to be a string.")
    path = Path(value)
    if path.is_absolute():
        return path
    return (base / path).resolve()


def _optional_path(value: object, base: Path) -> Path | None:
    if value is None:
        return None
    return _path(value, base)


def _required_str(data: dict[str, object], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise TypeError(f"Expected '{key}' to be a non-empty string.")
    return value


def _str(value: object, *, default: str) -> str:
    if value is None:
        return default
    if not isinstance(value, str):
        raise TypeError("Expected string value.")
    return value


def _str_list(data: dict[str, object], key: str) -> list[str]:
    value = data.get(key, [])
    if value is None:
        return []
    if not isinstance(value, list):
        raise TypeError(f"Expected '{key}' to be a list.")
    if not all(isinstance(item, str) for item in value):
        raise TypeError(f"Expected every item in '{key}' to be a string.")
    return cast(list[str], value)


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int):
        raise TypeError("Expected integer value.")
    return value
