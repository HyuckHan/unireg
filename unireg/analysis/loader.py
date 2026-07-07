"""Load and normalize grounded QA traces for error analysis."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from unireg.analysis.models import QATraceRecord, TraceLoadIssue
from unireg.benchmark.loader import BenchmarkDataset, load_benchmark
from unireg.benchmark.models import BenchmarkQuestion
from unireg.qa.models import CompletenessStatus


def load_trace_records(
    trace_path: str | Path,
    *,
    benchmark_dir: str | Path | None = None,
) -> tuple[list[QATraceRecord], list[TraceLoadIssue]]:
    """Read a QA trace JSONL file and normalize every valid line."""

    benchmark_questions = _load_benchmark_questions(benchmark_dir)
    records: list[QATraceRecord] = []
    issues: list[TraceLoadIssue] = []

    path = Path(trace_path)
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if not raw_line.strip():
            continue
        try:
            payload = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            issues.append(
                TraceLoadIssue(
                    line_number=line_number,
                    message=f"Invalid JSON: {exc.msg}",
                    raw_line=raw_line,
                )
            )
            continue
        if not isinstance(payload, dict):
            issues.append(
                TraceLoadIssue(
                    line_number=line_number,
                    message="Expected a JSON object trace.",
                    raw_line=raw_line,
                )
            )
            continue
        try:
            records.append(
                _record_from_payload(
                    cast(dict[str, object], payload),
                    line_number=line_number,
                    benchmark_questions=benchmark_questions,
                )
            )
        except (TypeError, ValueError) as exc:
            issues.append(
                TraceLoadIssue(
                    line_number=line_number,
                    message=f"Malformed trace: {exc}",
                    raw_line=raw_line,
                )
            )
    return records, issues


def _record_from_payload(
    payload: dict[str, object],
    *,
    line_number: int,
    benchmark_questions: dict[str, BenchmarkQuestion],
) -> QATraceRecord:
    trace = _object(payload.get("trace"))
    evaluation = {
        **_object(trace.get("evaluation")),
        **_object(payload.get("evaluation")),
    }
    llm_input = _object(trace.get("llm_input"))
    evidence_package = {
        **_object(llm_input.get("evidence_package")),
        **_object(trace.get("evidence_package")),
        **_object(payload.get("evidence_package")),
    }
    grounded_answer = {
        **_object(trace.get("grounded_answer")),
        **_object(payload.get("grounded_answer")),
    }

    question = _first_str(
        payload.get("question"),
        trace.get("question"),
        evidence_package.get("question"),
    )
    answer_id = _first_str(payload.get("answer_id"), evaluation.get("answer_id"))
    metadata = _metadata_from_payload(payload, evidence_package)
    question_id = _first_str(
        payload.get("question_id"),
        evaluation.get("question_id"),
        metadata.get("question_id"),
    )
    benchmark_question = benchmark_questions.get(question_id)
    answerability = _answerability(payload, evaluation, benchmark_question)
    gold_citations = _gold_citations(payload, evaluation, benchmark_question)
    predicted_citations = _dict_list(
        payload.get("citations"),
        grounded_answer.get("citations"),
    )
    retrieved_evidence = _dict_list(
        trace.get("retrieved_evidence"),
        evidence_package.get("evidence"),
        payload.get("evidence"),
    )

    llm_request = {**llm_input, **_object(payload.get("llm_request"))}
    llm_response = _object(payload.get("llm_response"))
    completeness_status = _first_str(
        payload.get("completeness_status"),
        grounded_answer.get("completeness_status"),
        llm_response.get("completeness_status"),
        evaluation.get("actual_completeness"),
    )
    answer_text = _first_str(
        payload.get("answer"),
        grounded_answer.get("answer"),
        llm_response.get("answer"),
    )

    return QATraceRecord(
        line_number=line_number,
        answer_id=answer_id,
        question_id=question_id,
        question=question,
        answerability=answerability,
        gold_citations=gold_citations,
        predicted_citations=predicted_citations,
        retrieved_evidence=retrieved_evidence,
        completeness_status=completeness_status,
        grounded_answer=answer_text,
        evidence_package=evidence_package,
        retriever_metadata=_retriever_metadata(evidence_package),
        llm_adapter_metadata=_llm_adapter_metadata(payload, llm_request),
        evaluation=evaluation,
        metadata=metadata,
        raw=payload,
    )


def _load_benchmark_questions(
    benchmark_dir: str | Path | None,
) -> dict[str, BenchmarkQuestion]:
    if benchmark_dir is None:
        default_dir = Path("benchmark")
        if not default_dir.exists():
            return {}
        benchmark_dir = default_dir
    path = Path(benchmark_dir)
    if not path.exists():
        return {}
    dataset: BenchmarkDataset = load_benchmark(path)
    return {question.id: question for question in dataset.questions}


def _answerability(
    payload: dict[str, object],
    evaluation: dict[str, object],
    benchmark_question: BenchmarkQuestion | None,
) -> str:
    answerability = _first_str(
        payload.get("answerability"),
        evaluation.get("answerability"),
    )
    if answerability:
        return answerability
    if benchmark_question is not None:
        return benchmark_question.answerability.value
    expected = _first_str(evaluation.get("expected_completeness"))
    return _answerability_from_expected(expected)


def _gold_citations(
    payload: dict[str, object],
    evaluation: dict[str, object],
    benchmark_question: BenchmarkQuestion | None,
) -> list[dict[str, object]]:
    citations = _dict_list(
        payload.get("gold_citations"), evaluation.get("gold_citations")
    )
    if citations:
        return citations
    if benchmark_question is None:
        return []
    return [citation.to_dict() for citation in benchmark_question.gold_citations]


def _metadata_from_payload(
    payload: dict[str, object],
    evidence_package: dict[str, object],
) -> dict[str, object]:
    package_metadata = _object(evidence_package.get("metadata"))
    payload_metadata = _object(payload.get("metadata"))
    metadata = {**package_metadata, **payload_metadata}
    if "source_file" not in metadata:
        source_file = _first_evidence_source_file(evidence_package)
        if source_file:
            metadata["source_file"] = source_file
    return metadata


def _first_evidence_source_file(evidence_package: dict[str, object]) -> str:
    evidence = _dict_list(evidence_package.get("evidence"))
    for item in evidence:
        source_file = _first_str(item.get("source_file"))
        if source_file:
            return source_file
    return ""


def _retriever_metadata(evidence_package: dict[str, object]) -> dict[str, object]:
    metadata = _object(evidence_package.get("metadata"))
    return {
        "retriever": _first_str(evidence_package.get("retriever")),
        "retrieval_scope": _first_str(evidence_package.get("retrieval_scope")),
        "top_k": evidence_package.get("top_k"),
        "retriever_config": metadata.get("retriever_config", ""),
    }


def _llm_adapter_metadata(
    payload: dict[str, object],
    llm_request: dict[str, object],
) -> dict[str, object]:
    reasoning = _object(payload.get("reasoning_metadata"))
    return {
        "provider": _first_str(llm_request.get("provider")),
        "model": _first_str(llm_request.get("model")),
        "reasoning_metadata": reasoning,
    }


def _answerability_from_expected(expected: str) -> str:
    if expected == CompletenessStatus.MISSING_REGULATION.value:
        return "missing_regulation"
    if expected == CompletenessStatus.PARTIAL.value:
        return "partially_answerable"
    if expected == CompletenessStatus.UNKNOWN.value:
        return "unanswerable"
    if expected == CompletenessStatus.COMPLETE.value:
        return "answerable"
    return "unknown"


def _object(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return cast(dict[str, object], value)
    return {}


def _dict_list(*values: object) -> list[dict[str, object]]:
    saw_list = False
    for value in values:
        if not isinstance(value, list):
            continue
        saw_list = True
        items: list[dict[str, object]] = []
        for item in value:
            if isinstance(item, dict):
                items.append(cast(dict[str, object], item))
        if items:
            return items
    if saw_list:
        return []
    return []


def _first_str(*values: object) -> str:
    for value in values:
        if isinstance(value, str) and value:
            return value
    return ""
