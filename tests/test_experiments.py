from __future__ import annotations

import json
from pathlib import Path

import pytest

from unireg.experiments.cli import main as experiment_main
from unireg.experiments.config import load_experiment_config
from unireg.experiments.models import ExperimentKind
from unireg.experiments.runner import run_experiment
from unireg.experiments.summarize import summarize_runs

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = PROJECT_ROOT / "experiments/fixtures/sample"


def test_experiment_config_loading_and_validation(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path)

    config = load_experiment_config(config_path)

    assert config.name == "test_experiment"
    assert config.experiment_types == (
        ExperimentKind.PARSER_ACCURACY,
        ExperimentKind.RETRIEVAL,
        ExperimentKind.GROUNDED_QA,
        ExperimentKind.MISSING_REGULATION,
        ExperimentKind.CROSS_UNIVERSITY,
    )
    assert config.retrieval_method == "bm25"
    assert config.qa_method == "mock"


def test_experiment_config_reports_missing_inputs(tmp_path: Path) -> None:
    config_path = _write_config(
        tmp_path,
        parser_report=tmp_path / "missing_parser_report.json",
    )

    with pytest.raises(FileNotFoundError):
        load_experiment_config(config_path)


def test_experiment_config_rejects_online_qa_method(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path, qa_method="openai")

    with pytest.raises(ValueError, match="qa_method='mock'"):
        load_experiment_config(config_path)


def test_experiment_runner_writes_result_metadata_and_tables(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path)

    result = run_experiment(config_path, command_line=["experiment", "run"])

    output_dir = result.config.output_dir
    assert (output_dir / "result.json").exists()
    assert (output_dir / "metadata.json").exists()
    assert (output_dir / "metrics.csv").exists()
    assert (output_dir / "summary.md").exists()
    assert (output_dir / "tables/retrieval_method_comparison.csv").exists()
    assert (output_dir / "tables/error_category_distribution.md").exists()
    assert result.metadata.python_version
    assert result.metadata.git_commit
    assert result.metadata.random_seed == 0


def test_experiment_runner_records_unavailable_metrics(tmp_path: Path) -> None:
    result = run_experiment(_write_config(tmp_path))

    unavailable = [
        metric for metric in result.metrics if metric.metric == "parser_warnings"
    ]

    assert unavailable
    assert unavailable[0].status == "unavailable"
    assert unavailable[0].value is None


def test_deterministic_sample_experiment_metrics(tmp_path: Path) -> None:
    result = run_experiment(_write_config(tmp_path))
    metrics = {
        (metric.experiment_type, metric.metric): metric for metric in result.metrics
    }

    assert metrics[("retrieval", "recall_at_3")].value == 1.0
    assert metrics[("grounded_qa", "citation_accuracy")].value == pytest.approx(
        0.6666666667
    )
    assert metrics[("cross_university", "parse_success_rate")].value == 1.0


def test_experiment_outputs_are_machine_readable(tmp_path: Path) -> None:
    result = run_experiment(_write_config(tmp_path))
    payload = json.loads((result.config.output_dir / "result.json").read_text())

    assert payload["config"]["qa_method"] == "mock"
    assert payload["metadata"]["input_paths"]
    assert payload["tables"]["qa_results_by_answerability"]
    assert "api_key" not in json.dumps(payload).lower()


def test_experiment_summarizer_aggregates_runs(tmp_path: Path) -> None:
    result = run_experiment(_write_config(tmp_path))
    summary_path = tmp_path / "reports/summary.md"

    payload = summarize_runs(result.config.output_dir.parent, summary_path)

    assert payload["run_count"] == 1
    assert summary_path.exists()
    assert summary_path.with_suffix(".json").exists()
    assert summary_path.with_suffix(".csv").exists()
    assert "Retrieval Method Comparison" in summary_path.read_text()


def test_experiment_cli_run_and_summarize(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path)
    runs_dir = tmp_path / "runs"
    summary_path = tmp_path / "reports/summary.md"

    run_code = experiment_main(["run", "--config", str(config_path)])
    summarize_code = experiment_main(
        ["summarize", "--runs", str(runs_dir), "--out", str(summary_path)]
    )

    assert run_code == 0
    assert summarize_code == 0
    assert (runs_dir / "test_experiment/result.json").exists()
    assert summary_path.exists()


def _write_config(
    tmp_path: Path,
    *,
    parser_report: Path | None = None,
    qa_method: str = "mock",
) -> Path:
    output_dir = tmp_path / "runs/test_experiment"
    payload = {
        "name": "test_experiment",
        "experiment_types": [
            "parser_accuracy",
            "retrieval",
            "grounded_qa",
            "missing_regulation",
            "cross_university",
        ],
        "corpus_location": str(FIXTURE_DIR / "corpus"),
        "benchmark_dir": str(FIXTURE_DIR / "benchmark"),
        "benchmark_question_file": str(
            FIXTURE_DIR / "benchmark/questions/sample_questions.jsonl"
        ),
        "parser_output_location": str(
            parser_report or FIXTURE_DIR / "parser_report.json"
        ),
        "retrieval_method": "bm25",
        "qa_method": qa_method,
        "evaluation_metrics": ["recall_at_3", "citation_accuracy"],
        "output_dir": str(output_dir),
        "random_seed": 0,
        "notes": "pytest synthetic experiment",
        "tags": ["pytest", "offline"],
        "parser": {
            "mode": "precomputed",
            "report_path": str(parser_report or FIXTURE_DIR / "parser_report.json"),
        },
        "retrieval": {
            "mode": "precomputed",
            "report_path": str(FIXTURE_DIR / "retrieval_bm25_report.json"),
            "scope": "question_source",
            "top_k": 5,
            "units": "article,clause",
        },
        "qa": {
            "mode": "precomputed",
            "report_path": str(FIXTURE_DIR / "qa_mock_report.json"),
            "traces_path": str(FIXTURE_DIR / "qa_traces.jsonl"),
        },
        "missing_regulation": {
            "mode": "precomputed",
            "traces_path": str(FIXTURE_DIR / "qa_traces.jsonl"),
        },
        "cross_university": {
            "mode": "precomputed",
            "report_path": str(FIXTURE_DIR / "cross_university_report.csv"),
        },
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return config_path
