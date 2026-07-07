"""Experiment runner that orchestrates existing UniReg evaluation components."""

from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path
from typing import cast

from unireg.analysis.reports import write_error_analysis_reports
from unireg.analysis.runner import analyze_error_traces
from unireg.benchmark.evaluation import evaluate_parser
from unireg.benchmark.loader import load_benchmark
from unireg.benchmark.validation import validate_benchmark
from unireg.experiments.config import load_experiment_config
from unireg.experiments.metadata import build_run_metadata
from unireg.experiments.models import (
    ExecutionMode,
    ExperimentArtifact,
    ExperimentConfig,
    ExperimentKind,
    ExperimentRunResult,
    MetricRecord,
    unavailable_metric,
)
from unireg.experiments.reports import write_experiment_outputs
from unireg.qa.adapters import MockLLMAdapter
from unireg.qa.evaluation import evaluate_qa, write_qa_reports
from unireg.qa.pipeline import GroundedQAPipeline
from unireg.qa.retrievers import BM25EvidenceRetriever, BM25EvidenceRetrieverConfig
from unireg.retrieval.corpus import parse_retrieval_unit_types
from unireg.retrieval.runner import (
    BM25RetrievalRunner,
    RetrievalRunConfig,
    RetrievalScope,
    write_retrieval_run_reports,
)


def run_experiment(
    config_or_path: ExperimentConfig | str | Path,
    *,
    command_line: list[str] | None = None,
) -> ExperimentRunResult:
    """Run one experiment config and write all outputs."""

    config = (
        load_experiment_config(config_or_path)
        if isinstance(config_or_path, str | Path)
        else config_or_path
    )
    config.output_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir = config.output_dir / "artifacts"
    artifacts_dir.mkdir(exist_ok=True)

    context = _RunContext(
        config=config,
        artifacts_dir=artifacts_dir,
        command_line=command_line or [],
    )
    for experiment_type in config.experiment_types:
        if experiment_type == ExperimentKind.PARSER_ACCURACY:
            _run_parser_experiment(context)
        elif experiment_type == ExperimentKind.RETRIEVAL:
            _run_retrieval_experiment(context)
        elif experiment_type == ExperimentKind.GROUNDED_QA:
            _run_qa_experiment(context)
        elif experiment_type == ExperimentKind.MISSING_REGULATION:
            _run_missing_regulation_experiment(context)
        elif experiment_type == ExperimentKind.CROSS_UNIVERSITY:
            _run_cross_university_experiment(context)

    copy_config_to_run(config)
    metadata = build_run_metadata(config, command_line=context.command_line)
    metadata = _with_output_paths(metadata, config)
    result = ExperimentRunResult(
        config=config,
        metadata=metadata,
        metrics=context.metrics,
        artifacts=context.artifacts,
        tables=context.tables,
        raw_results=context.raw_results,
    )
    write_experiment_outputs(result)
    return result


class _RunContext:
    def __init__(
        self,
        *,
        config: ExperimentConfig,
        artifacts_dir: Path,
        command_line: list[str],
    ) -> None:
        self.config = config
        self.artifacts_dir = artifacts_dir
        self.command_line = command_line
        self.metrics: list[MetricRecord] = []
        self.artifacts: list[ExperimentArtifact] = []
        self.tables: dict[str, list[dict[str, object]]] = {}
        self.raw_results: dict[str, object] = {}
        self.qa_trace_path: Path | None = None


def _run_parser_experiment(context: _RunContext) -> None:
    config = context.config
    mode = _mode(config.parser)
    if mode == ExecutionMode.RUN:
        dataset = _load_valid_dataset(config)
        parser_result = evaluate_parser(dataset)
        payload = parser_result.to_dict()
        artifact_path = context.artifacts_dir / "parser_report.json"
        _write_json(artifact_path, payload)
        context.artifacts.append(
            ExperimentArtifact("parser_report", artifact_path, "generated")
        )
    else:
        artifact_path = _required_path(config.parser, "report_path")
        payload = _load_json(artifact_path)
        context.artifacts.append(
            ExperimentArtifact("parser_report", artifact_path, "input")
        )
        payload = _extract_nested(payload, "parser")

    context.raw_results[ExperimentKind.PARSER_ACCURACY.value] = payload
    context.metrics.extend(_parser_metrics(payload))
    context.tables["parser_results_by_university"] = _parser_table(payload)


def _run_retrieval_experiment(context: _RunContext) -> None:
    config = context.config
    mode = _mode(config.retrieval)
    if mode == ExecutionMode.RUN:
        dataset = _load_valid_dataset(config)
        retrieval_config = RetrievalRunConfig(
            method=config.retrieval_method,
            top_k=_int(config.retrieval.get("top_k"), default=5),
            scope=RetrievalScope(
                _str(config.retrieval.get("scope"), "question_source")
            ),
            unit_types=parse_retrieval_unit_types(
                config.retrieval.get("units", "article,clause,item,sub_item")
            ),
        )
        result = BM25RetrievalRunner(config=retrieval_config).run(dataset)
        predictions_path = context.artifacts_dir / "predictions.bm25.jsonl"
        write_retrieval_run_reports(
            result,
            context.artifacts_dir,
            predictions_path=predictions_path,
        )
        payload = result.to_dict()
        context.artifacts.extend(
            [
                ExperimentArtifact(
                    "retrieval_report",
                    context.artifacts_dir / "retrieval_bm25_report.json",
                    "generated",
                ),
                ExperimentArtifact(
                    "retrieval_predictions", predictions_path, "generated"
                ),
            ]
        )
    else:
        artifact_path = _required_path(config.retrieval, "report_path")
        payload = _load_json(artifact_path)
        context.artifacts.append(
            ExperimentArtifact("retrieval_report", artifact_path, "input")
        )

    context.raw_results[ExperimentKind.RETRIEVAL.value] = payload
    context.metrics.extend(_retrieval_metrics(payload))
    context.tables["retrieval_method_comparison"] = _retrieval_table(
        payload,
        method=config.retrieval_method,
    )


def _run_qa_experiment(context: _RunContext) -> None:
    config = context.config
    mode = _mode(config.qa)
    if mode == ExecutionMode.RUN:
        dataset = _load_valid_dataset(config)
        retriever = BM25EvidenceRetriever(
            dataset=dataset,
            config=BM25EvidenceRetrieverConfig(
                top_k=_int(config.qa.get("top_k"), default=5),
                scope=RetrievalScope(_str(config.qa.get("scope"), "question_source")),
                unit_types=parse_retrieval_unit_types(
                    config.qa.get("units", "article,clause,item,sub_item")
                ),
            ),
        )
        pipeline = GroundedQAPipeline(
            retriever=retriever,
            llm_adapter=MockLLMAdapter(),
        )
        answers = [
            pipeline.answer(
                question.question,
                metadata={**question.metadata, "question_id": question.id},
            )
            for question in dataset.questions
        ]
        qa_result = evaluate_qa(dataset.questions, answers)
        write_qa_reports(qa_result, context.artifacts_dir)
        payload = qa_result.to_dict()
        context.qa_trace_path = context.artifacts_dir / "qa_mock_answers.jsonl"
        context.artifacts.extend(
            [
                ExperimentArtifact(
                    "qa_report",
                    context.artifacts_dir / "qa_mock_report.json",
                    "generated",
                ),
                ExperimentArtifact("qa_traces", context.qa_trace_path, "generated"),
            ]
        )
    else:
        artifact_path = _required_path(config.qa, "report_path")
        payload = _load_json(artifact_path)
        context.artifacts.append(
            ExperimentArtifact("qa_report", artifact_path, "input")
        )
        traces_path = _optional_path(config.qa, "traces_path")
        if traces_path is not None:
            context.qa_trace_path = traces_path
            context.artifacts.append(
                ExperimentArtifact("qa_traces", traces_path, "input")
            )

    context.raw_results[ExperimentKind.GROUNDED_QA.value] = payload
    context.metrics.extend(_qa_metrics(payload))
    context.tables["qa_results_by_answerability"] = _qa_answerability_table(payload)


def _run_missing_regulation_experiment(context: _RunContext) -> None:
    config = context.config
    section = config.missing_regulation
    error_analysis_path = _optional_path(section, "error_analysis_path")
    if _mode(section) == ExecutionMode.PRECOMPUTED and error_analysis_path is not None:
        payload = _load_json(error_analysis_path)
        context.artifacts.append(
            ExperimentArtifact("error_analysis", error_analysis_path, "input")
        )
    else:
        traces_path = _optional_path(section, "traces_path") or context.qa_trace_path
        if traces_path is None:
            traces_path = _optional_path(config.qa, "traces_path")
        if traces_path is None:
            raise ValueError("Missing QA trace path for missing-regulation analysis.")
        report = analyze_error_traces(
            traces_path,
            benchmark_dir=config.benchmark_dir,
        )
        error_dir = context.artifacts_dir / "error_analysis"
        write_error_analysis_reports(report, error_dir)
        payload = report.to_dict()
        context.artifacts.append(
            ExperimentArtifact(
                "error_analysis", error_dir / "error_analysis.json", "generated"
            )
        )

    context.raw_results[ExperimentKind.MISSING_REGULATION.value] = payload
    context.metrics.extend(_missing_regulation_metrics(payload))
    missing_table, error_table = _missing_regulation_tables(payload)
    context.tables["missing_regulation_error_analysis"] = missing_table
    context.tables["error_category_distribution"] = error_table


def _run_cross_university_experiment(context: _RunContext) -> None:
    config = context.config
    mode = _mode(config.cross_university)
    if mode == ExecutionMode.RUN:
        payload = _run_cross_university_pdf_eval(config, context.artifacts_dir)
        artifact_path = context.artifacts_dir / "cross_university_report.csv"
        context.artifacts.append(
            ExperimentArtifact("cross_university_report", artifact_path, "generated")
        )
    else:
        artifact_path = _required_path(config.cross_university, "report_path")
        rows = _read_csv(artifact_path)
        payload = {"rows": rows}
        context.artifacts.append(
            ExperimentArtifact("cross_university_report", artifact_path, "input")
        )

    context.raw_results[ExperimentKind.CROSS_UNIVERSITY.value] = payload
    context.metrics.extend(_cross_university_metrics(payload))
    context.tables["cross_university_generalization"] = _cross_university_table(payload)


def _load_valid_dataset(config: ExperimentConfig):
    if config.benchmark_dir is None:
        raise ValueError("benchmark_dir is required for run-mode experiments.")
    dataset = load_benchmark(config.benchmark_dir)
    issues = validate_benchmark(dataset)
    if issues:
        messages = "; ".join(issue.message for issue in issues)
        raise ValueError(f"Benchmark validation failed: {messages}")
    return dataset


def _run_cross_university_pdf_eval(
    config: ExperimentConfig,
    artifacts_dir: Path,
) -> dict[str, object]:
    from scripts.check_eval_pdfs import (
        EvalThresholds,
        _discover_pdfs,
        _write_report,
        evaluate_pdf,
    )
    from unireg.citations import CitationGenerator
    from unireg.loaders import PDFLoader
    from unireg.parser import RegulationParser

    eval_dir = (
        _optional_path(config.cross_university, "eval_dir") or config.corpus_location
    )
    if eval_dir is None:
        raise ValueError("cross_university eval_dir or corpus_location is required.")
    pattern = _str(config.cross_university.get("pattern"), "*.pdf")
    paths = _discover_pdfs(eval_dir, pattern)
    thresholds = EvalThresholds(
        min_articles=_int(config.cross_university.get("min_articles"), default=20),
        min_page_coverage=float(config.cross_university.get("min_page_coverage", 0.25)),
    )
    loader = PDFLoader()
    parser = RegulationParser()
    citation_generator = CitationGenerator()
    results = [
        evaluate_pdf(
            path=path,
            eval_dir=eval_dir,
            loader=loader,
            parser=parser,
            citation_generator=citation_generator,
            thresholds=thresholds,
        )
        for path in paths
    ]
    report_path = artifacts_dir / "cross_university_report.csv"
    _write_report(report_path, results)
    return {"rows": _read_csv(report_path)}


def _parser_metrics(payload: dict[str, object]) -> list[MetricRecord]:
    metrics: list[MetricRecord] = []
    for key in [
        "article_extraction_accuracy",
        "clause_extraction_accuracy",
        "hierarchy_preservation",
        "citation_generation",
        "metadata_completeness",
    ]:
        metrics.append(
            _metric_from_payload(
                ExperimentKind.PARSER_ACCURACY,
                payload,
                key,
            )
        )
    metrics.append(
        unavailable_metric(
            ExperimentKind.PARSER_ACCURACY,
            "parser_warnings",
            notes=(
                "Parser warning counts are not exposed by the current parser "
                "benchmark report."
            ),
        )
    )
    return metrics


def _retrieval_metrics(payload: dict[str, object]) -> list[MetricRecord]:
    metrics_payload = _object(_object(payload.get("evaluation")).get("metrics"))
    return [
        _metric_from_payload(ExperimentKind.RETRIEVAL, metrics_payload, key)
        for key in ["recall_at_1", "recall_at_3", "recall_at_5", "mrr", "ndcg_at_5"]
    ]


def _qa_metrics(payload: dict[str, object]) -> list[MetricRecord]:
    metrics_payload = _object(payload.get("metrics"))
    return [
        _metric_from_payload(ExperimentKind.GROUNDED_QA, metrics_payload, key)
        for key in [
            "citation_accuracy",
            "groundedness",
            "hallucination_rate",
            "completeness_classification_accuracy",
        ]
    ]


def _missing_regulation_metrics(payload: dict[str, object]) -> list[MetricRecord]:
    answerability_rows = _dict_list(payload.get("answerability_breakdown"))
    missing_row = next(
        (row for row in answerability_rows if row.get("key") == "missing_regulation"),
        None,
    )
    summary = _object(payload.get("summary"))
    distribution = _object(summary.get("category_distribution"))
    trace_count = _int(summary.get("trace_count"), default=0)
    return [
        MetricRecord(
            experiment_type=ExperimentKind.MISSING_REGULATION.value,
            metric="missing_regulation_detection_accuracy",
            value=None if missing_row is None else _float(missing_row.get("accuracy")),
            status="unavailable" if missing_row is None else "available",
            notes="" if missing_row is not None else "No missing_regulation rows.",
        ),
        MetricRecord(
            experiment_type=ExperimentKind.MISSING_REGULATION.value,
            metric="hallucination_under_incomplete_evidence",
            value=_rate(distribution.get("HALLUCINATION"), trace_count),
            notes="HALLUCINATION category count divided by trace count.",
        ),
        MetricRecord(
            experiment_type=ExperimentKind.MISSING_REGULATION.value,
            metric="completeness_misclassification_count",
            value=_int(distribution.get("COMPLETENESS_MISCLASSIFICATION"), default=0),
        ),
        MetricRecord(
            experiment_type=ExperimentKind.MISSING_REGULATION.value,
            metric="unsupported_answer_count",
            value=_int(distribution.get("UNSUPPORTED_ANSWER"), default=0),
        ),
    ]


def _cross_university_metrics(payload: dict[str, object]) -> list[MetricRecord]:
    rows = _dict_list(payload.get("rows"))
    total = len(rows)
    ok_count = sum(1 for row in rows if _truthy(row.get("ok")))
    return [
        MetricRecord(
            experiment_type=ExperimentKind.CROSS_UNIVERSITY.value,
            metric="parse_success_rate",
            value=ok_count / (total or 1),
        ),
        MetricRecord(
            experiment_type=ExperimentKind.CROSS_UNIVERSITY.value,
            metric="average_page_coverage",
            value=_average(_float(row.get("page_coverage")) for row in rows),
        ),
        MetricRecord(
            experiment_type=ExperimentKind.CROSS_UNIVERSITY.value,
            metric="university_count",
            value=total,
        ),
    ]


def _parser_table(payload: dict[str, object]) -> list[dict[str, object]]:
    rows = []
    for case in _dict_list(payload.get("cases")):
        source_file = str(case.get("source_file", "unknown"))
        rows.append(
            {
                "university": _university_from_path(source_file),
                "source_file": source_file,
                "ok": case.get("ok", ""),
                "article_count": case.get("article_count", ""),
                "clause_count": case.get("clause_count", ""),
                "citation_count": case.get("citation_count", ""),
                "article_extraction_accuracy": case.get(
                    "article_extraction_accuracy",
                    "",
                ),
                "clause_extraction_accuracy": case.get(
                    "clause_extraction_accuracy",
                    "",
                ),
                "hierarchy_preservation": case.get("hierarchy_preservation", ""),
                "metadata_completeness": case.get("metadata_completeness", ""),
            }
        )
    return rows


def _retrieval_table(
    payload: dict[str, object],
    *,
    method: str,
) -> list[dict[str, object]]:
    metrics = _object(_object(payload.get("evaluation")).get("metrics"))
    config = _object(payload.get("config"))
    return [
        {
            "method": method,
            "scope": config.get("scope", ""),
            "unit_types": (
                ",".join(str(item) for item in config.get("unit_types", []))
                if isinstance(config.get("unit_types"), list)
                else config.get("unit_types", "")
            ),
            "question_count": metrics.get("question_count", ""),
            "recall_at_1": metrics.get("recall_at_1", ""),
            "recall_at_3": metrics.get("recall_at_3", ""),
            "recall_at_5": metrics.get("recall_at_5", ""),
            "mrr": metrics.get("mrr", ""),
            "ndcg_at_5": metrics.get("ndcg_at_5", ""),
        }
    ]


def _qa_answerability_table(payload: dict[str, object]) -> list[dict[str, object]]:
    groups: dict[str, list[dict[str, object]]] = {}
    for row in _dict_list(payload.get("per_question")):
        groups.setdefault(str(row.get("answerability", "unknown")), []).append(row)
    table: list[dict[str, object]] = []
    for answerability, rows in sorted(groups.items()):
        table.append(
            {
                "answerability": answerability,
                "question_count": len(rows),
                "citation_accuracy": _average(
                    _float(row.get("citation_accuracy")) for row in rows
                ),
                "groundedness": _average(
                    _float(row.get("groundedness")) for row in rows
                ),
                "hallucination_rate": _average(
                    1.0 if _truthy(row.get("hallucination_detected")) else 0.0
                    for row in rows
                ),
                "completeness_classification_accuracy": _average(
                    _float(row.get("completeness_classification")) for row in rows
                ),
            }
        )
    return table


def _missing_regulation_tables(
    payload: dict[str, object],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    answerability_rows = _dict_list(payload.get("answerability_breakdown"))
    missing_rows = [
        row for row in answerability_rows if row.get("key") == "missing_regulation"
    ]
    summary = _object(payload.get("summary"))
    distribution = _object(summary.get("category_distribution"))
    error_rows = [
        {
            "error_category": category,
            "count": count,
            "percentage": _rate(count, _int(summary.get("trace_count"), default=0)),
        }
        for category, count in sorted(distribution.items())
    ]
    return missing_rows, error_rows


def _cross_university_table(payload: dict[str, object]) -> list[dict[str, object]]:
    rows = []
    for row in _dict_list(payload.get("rows")):
        rows.append(
            {
                "university": row.get("university", ""),
                "ok": row.get("ok", ""),
                "article_count": row.get("article_count", ""),
                "clause_count": row.get("clause_count", ""),
                "item_count": row.get("item_count", ""),
                "citation_count": row.get("citation_count", ""),
                "page_coverage": row.get("page_coverage", ""),
                "title_warnings": row.get("title_warnings", ""),
            }
        )
    return rows


def _metric_from_payload(
    experiment_type: ExperimentKind,
    payload: dict[str, object],
    key: str,
) -> MetricRecord:
    if key not in payload or payload.get(key) is None:
        return unavailable_metric(
            experiment_type,
            key,
            notes=f"Metric '{key}' was not available in the input artifact.",
        )
    return MetricRecord(
        experiment_type=experiment_type.value,
        metric=key,
        value=_float_or_raw(payload.get(key)),
    )


def _extract_nested(payload: dict[str, object], key: str) -> dict[str, object]:
    nested = payload.get(key)
    if isinstance(nested, dict):
        return cast(dict[str, object], nested)
    return payload


def _with_output_paths(metadata, config: ExperimentConfig):
    output_paths = {
        **metadata.output_paths,
        "result_json": str(config.output_dir / "result.json"),
        "metrics_csv": str(config.output_dir / "metrics.csv"),
        "summary_md": str(config.output_dir / "summary.md"),
        "tables_dir": str(config.output_dir / "tables"),
    }
    return type(metadata)(
        timestamp=metadata.timestamp,
        config_path=metadata.config_path,
        project_version=metadata.project_version,
        git_commit=metadata.git_commit,
        python_version=metadata.python_version,
        platform=metadata.platform,
        input_paths=metadata.input_paths,
        output_paths=output_paths,
        random_seed=metadata.random_seed,
        command_line=metadata.command_line,
    )


def _load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"Expected JSON object in {path}")
    return cast(dict[str, object], payload)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _read_csv(path: Path) -> list[dict[str, object]]:
    with path.open(newline="", encoding="utf-8") as file:
        return [dict(row) for row in csv.DictReader(file)]


def _mode(section: dict[str, object]) -> ExecutionMode:
    value = section.get("mode", ExecutionMode.RUN.value)
    if not isinstance(value, str):
        raise TypeError("Experiment section mode must be a string.")
    return ExecutionMode(value)


def _required_path(section: dict[str, object], key: str) -> Path:
    path = _optional_path(section, key)
    if path is None:
        raise ValueError(f"Missing required path: {key}")
    return path


def _optional_path(section: dict[str, object], key: str) -> Path | None:
    value = section.get(key)
    return value if isinstance(value, Path) else None


def _object(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return cast(dict[str, object], value)
    return {}


def _dict_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [cast(dict[str, object], item) for item in value if isinstance(item, dict)]


def _str(value: object, default: str) -> str:
    return value if isinstance(value, str) else default


def _int(value: object, *, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return default


def _float(value: object) -> float:
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return 0.0
    return 0.0


def _float_or_raw(value: object) -> float | str | None:
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return value
    return None


def _average(values) -> float:
    collected = [float(value) for value in values]
    return sum(collected) / (len(collected) or 1)


def _rate(value: object, denominator: int) -> float:
    return _float(value) / (denominator or 1)


def _truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in {"true", "1", "yes", "ok"}
    return bool(value)


def _university_from_path(source_file: str) -> str:
    parts = Path(source_file).parts
    for part in reversed(parts[:-1]):
        if part:
            return part
    return Path(source_file).stem or "unknown"


def copy_config_to_run(config: ExperimentConfig) -> None:
    """Copy the source config into the run directory for auditability."""

    if config.config_path is None:
        return
    destination = config.output_dir / "config.json"
    if config.config_path.resolve() == destination.resolve():
        return
    shutil.copyfile(config.config_path, destination)
