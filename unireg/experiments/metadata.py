"""Run metadata generation for reproducible experiments."""

from __future__ import annotations

import platform
import subprocess
import sys
from datetime import UTC, datetime
from importlib import metadata as importlib_metadata
from pathlib import Path

from unireg.experiments.models import ExperimentConfig, RunMetadata


def build_run_metadata(
    config: ExperimentConfig,
    *,
    command_line: list[str] | None = None,
) -> RunMetadata:
    """Build metadata required to reproduce an experiment run."""

    return RunMetadata(
        timestamp=datetime.now(UTC).isoformat(),
        config_path="" if config.config_path is None else str(config.config_path),
        project_version=_project_version(),
        git_commit=_git_commit(),
        python_version=sys.version.split()[0],
        platform=platform.platform(),
        input_paths=_input_paths(config),
        output_paths={"output_dir": str(config.output_dir)},
        random_seed=config.random_seed,
        command_line=command_line or [],
    )


def _project_version() -> str:
    try:
        return importlib_metadata.version("unireg")
    except importlib_metadata.PackageNotFoundError:
        return "0.1.0"


def _git_commit() -> str:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            cwd=Path(__file__).resolve().parents[2],
        )
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"
    return completed.stdout.strip() or "unavailable"


def _input_paths(config: ExperimentConfig) -> dict[str, str]:
    paths: dict[str, str] = {}
    for key, value in {
        "corpus_location": config.corpus_location,
        "benchmark_dir": config.benchmark_dir,
        "benchmark_question_file": config.benchmark_question_file,
        "parser_output_location": config.parser_output_location,
    }.items():
        if value is not None:
            paths[key] = str(value)
    for section_name, section in {
        "parser": config.parser,
        "retrieval": config.retrieval,
        "qa": config.qa,
        "missing_regulation": config.missing_regulation,
        "cross_university": config.cross_university,
    }.items():
        for key, value in section.items():
            if isinstance(value, Path):
                paths[f"{section_name}.{key}"] = str(value)
    return paths
