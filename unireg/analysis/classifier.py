"""Automatic error classification for grounded QA traces."""

from __future__ import annotations

from pathlib import Path
from typing import cast

from unireg.analysis.models import (
    ErrorCategory,
    ErrorClassification,
    QATraceRecord,
)
from unireg.qa.models import CompletenessStatus

_MISSING_REGULATION_SIGNALS = (
    "따로 정한다",
    "별도로 정한다",
    "총장이 따로 정한다",
    "세부사항",
    "시행세칙",
    "규정으로 정한다",
)

_PRIMARY_PRIORITY = (
    ErrorCategory.HALLUCINATION,
    ErrorCategory.UNSUPPORTED_ANSWER,
    ErrorCategory.COMPLETENESS_MISCLASSIFICATION,
    ErrorCategory.RETRIEVAL_MISS,
    ErrorCategory.RETRIEVAL_RANKING_ERROR,
    ErrorCategory.CITATION_MISMATCH,
    ErrorCategory.INSUFFICIENT_EVIDENCE,
    ErrorCategory.MISSING_REGULATION,
    ErrorCategory.PARSER_ERROR,
    ErrorCategory.METADATA_ERROR,
    ErrorCategory.AMBIGUOUS_GOLD,
    ErrorCategory.UNKNOWN_ERROR,
)


def classify_trace(trace: QATraceRecord) -> ErrorClassification:
    """Classify the likely cause of success or failure for one QA trace."""

    categories: set[ErrorCategory] = set()
    reasons: list[str] = []
    gold_hit_rank = _first_gold_hit_rank(trace)
    citation_accuracy = _metric(trace, "citation_accuracy")
    groundedness = _metric(trace, "groundedness")
    completeness_accuracy = _metric(trace, "completeness_classification")
    recall_at_3 = 1.0 if gold_hit_rank is not None and gold_hit_rank <= 3 else 0.0
    expected_completeness = _expected_completeness(trace)
    requires_missing_regulation = _requires_missing_regulation(trace)

    if _has_ambiguous_gold(trace):
        categories.add(ErrorCategory.AMBIGUOUS_GOLD)
        reasons.append("Gold citation is missing, empty, or underspecified.")

    if _has_parser_source_span_problem(trace):
        categories.add(ErrorCategory.PARSER_ERROR)
        reasons.append("A retrieved or cited evidence node lacks source-page metadata.")

    if _has_metadata_problem(trace):
        categories.add(ErrorCategory.METADATA_ERROR)
        reasons.append("Trace, evidence, or citation metadata is incomplete.")

    if trace.gold_citations and gold_hit_rank is None:
        categories.add(ErrorCategory.RETRIEVAL_MISS)
        reasons.append("No retrieved evidence matches any gold citation.")

    if not trace.retrieved_evidence:
        categories.add(ErrorCategory.INSUFFICIENT_EVIDENCE)
        reasons.append("The evidence package contains no retrieved evidence.")

    if trace.gold_citations and gold_hit_rank is not None:
        if gold_hit_rank > 1 and citation_accuracy < 1.0:
            categories.add(ErrorCategory.RETRIEVAL_RANKING_ERROR)
            reasons.append(
                f"Gold evidence was retrieved at rank {gold_hit_rank}, not rank 1."
            )
        if trace.predicted_citations and not _predicted_matches_gold(trace):
            categories.add(ErrorCategory.CITATION_MISMATCH)
            reasons.append(
                "Gold evidence was retrieved but predicted citation differs."
            )

    if trace.gold_citations and not trace.predicted_citations:
        categories.add(ErrorCategory.CITATION_MISMATCH)
        reasons.append("Gold citation exists but the answer contains no citation.")

    if groundedness < 1.0 or _has_unsupported_predicted_citation(trace):
        categories.add(ErrorCategory.UNSUPPORTED_ANSWER)
        reasons.append("The answer cites material not supported by retrieved evidence.")

    if completeness_accuracy < 1.0 or (
        expected_completeness and trace.completeness_status != expected_completeness
    ):
        categories.add(ErrorCategory.COMPLETENESS_MISCLASSIFICATION)
        reasons.append(
            "Predicted completeness status does not match the expected status."
        )

    if _hallucination_detected(trace, requires_missing_regulation):
        categories.add(ErrorCategory.HALLUCINATION)
        reasons.append(
            "The answer asserts a complete result despite insufficient support."
        )

    if _answerable_but_incomplete(trace, expected_completeness):
        categories.add(ErrorCategory.INSUFFICIENT_EVIDENCE)
        reasons.append("An answerable question was returned as incomplete.")

    if requires_missing_regulation and categories:
        categories.add(ErrorCategory.MISSING_REGULATION)
        reasons.append(
            "The question or evidence requires a missing downstream regulation."
        )

    if not categories:
        categories.add(ErrorCategory.NO_ERROR)
        reasons.append("Citation, groundedness, and completeness checks passed.")

    if _needs_unknown_category(trace, categories):
        categories.add(ErrorCategory.UNKNOWN_ERROR)
        reasons.append("The trace failed evaluation but no known rule explained it.")

    ordered_categories = _ordered_categories(categories)
    success = ordered_categories == (ErrorCategory.NO_ERROR,)
    return ErrorClassification(
        question_id=trace.question_id,
        answer_id=trace.answer_id,
        categories=ordered_categories,
        primary_category=ordered_categories[0],
        success=success,
        reasons=tuple(reasons),
        gold_hit_rank=gold_hit_rank,
        recall_at_3=recall_at_3,
        citation_accuracy=citation_accuracy,
        groundedness=groundedness,
        completeness_accuracy=completeness_accuracy,
    )


def _first_gold_hit_rank(trace: QATraceRecord) -> int | None:
    if not trace.gold_citations:
        return None
    for evidence in sorted(trace.retrieved_evidence, key=_evidence_rank):
        citation = _object(evidence.get("citation"))
        if any(_citation_matches(gold, citation) for gold in trace.gold_citations):
            return _evidence_rank(evidence)
    return None


def _predicted_matches_gold(trace: QATraceRecord) -> bool:
    return any(
        _citation_matches(gold, predicted)
        for gold in trace.gold_citations
        for predicted in trace.predicted_citations
    )


def _has_unsupported_predicted_citation(trace: QATraceRecord) -> bool:
    if not trace.predicted_citations:
        return False
    evidence_citations = [
        _object(evidence.get("citation")) for evidence in trace.retrieved_evidence
    ]
    return any(
        not any(
            _citation_matches(predicted, evidence) for evidence in evidence_citations
        )
        for predicted in trace.predicted_citations
    )


def _has_ambiguous_gold(trace: QATraceRecord) -> bool:
    if trace.answerability in {
        "answerable",
        "partially_answerable",
        "missing_regulation",
    }:
        if not trace.gold_citations:
            return True
    for citation in trace.gold_citations:
        if not _first_str(citation.get("node_id"), citation.get("article")):
            return True
    return False


def _has_parser_source_span_problem(trace: QATraceRecord) -> bool:
    cited_node_ids = {
        _first_str(citation.get("node_id")) for citation in trace.predicted_citations
    }
    cited_node_ids.update(
        _first_str(citation.get("node_id")) for citation in trace.gold_citations
    )
    cited_node_ids.discard("")
    for evidence in trace.retrieved_evidence:
        citation = _object(evidence.get("citation"))
        node_id = _first_str(evidence.get("node_id"), citation.get("node_id"))
        if cited_node_ids and node_id not in cited_node_ids:
            continue
        source_pages = evidence.get("source_pages")
        source_label = _first_str(evidence.get("source_label"))
        if (
            not isinstance(source_pages, list) or not source_pages
        ) and not source_label:
            return True
    return False


def _has_metadata_problem(trace: QATraceRecord) -> bool:
    if not trace.question_id or not trace.question:
        return True
    for citation in [*trace.gold_citations, *trace.predicted_citations]:
        if not _first_str(citation.get("node_id"), citation.get("article")):
            return True
        if not _first_str(citation.get("source_file")):
            return True
    for evidence in trace.retrieved_evidence:
        citation = _object(evidence.get("citation"))
        if not _first_str(evidence.get("source_file"), citation.get("source_file")):
            return True
        if not _first_str(citation.get("node_id"), citation.get("article")):
            return True
    return False


def _requires_missing_regulation(trace: QATraceRecord) -> bool:
    if trace.answerability == "missing_regulation":
        return True
    expected = _first_str(trace.evaluation.get("expected_completeness"))
    if expected == CompletenessStatus.MISSING_REGULATION.value:
        return True
    if trace.answerability and trace.answerability != "unknown":
        return False
    for evidence in trace.retrieved_evidence:
        flags = evidence.get("incompleteness_flags")
        if isinstance(flags, list) and flags:
            return True
        text = _first_str(evidence.get("text"))
        if any(signal in text for signal in _MISSING_REGULATION_SIGNALS):
            return True
    return False


def _hallucination_detected(
    trace: QATraceRecord,
    requires_missing_regulation: bool,
) -> bool:
    detected = trace.evaluation.get("hallucination_detected")
    if isinstance(detected, bool) and detected:
        return True
    if trace.completeness_status == CompletenessStatus.COMPLETE.value:
        if not trace.predicted_citations:
            return True
        if requires_missing_regulation:
            return True
    return False


def _answerable_but_incomplete(
    trace: QATraceRecord,
    expected_completeness: str,
) -> bool:
    return (
        expected_completeness == CompletenessStatus.COMPLETE.value
        and trace.completeness_status
        in {
            CompletenessStatus.PARTIAL.value,
            CompletenessStatus.MISSING_REGULATION.value,
            CompletenessStatus.UNKNOWN.value,
        }
    )


def _needs_unknown_category(
    trace: QATraceRecord,
    categories: set[ErrorCategory],
) -> bool:
    if categories == {ErrorCategory.NO_ERROR}:
        return False
    if categories:
        return False
    return any(
        _metric(trace, key) < 1.0
        for key in ("citation_accuracy", "groundedness", "completeness_classification")
    )


def _expected_completeness(trace: QATraceRecord) -> str:
    expected = _first_str(trace.evaluation.get("expected_completeness"))
    if expected:
        return expected
    if trace.answerability == "missing_regulation":
        return CompletenessStatus.MISSING_REGULATION.value
    if trace.answerability == "partially_answerable":
        return CompletenessStatus.PARTIAL.value
    if trace.answerability == "unanswerable":
        return CompletenessStatus.UNKNOWN.value
    if trace.answerability in {"answerable", "comparison", "multi_hop"}:
        return CompletenessStatus.COMPLETE.value
    return ""


def _metric(trace: QATraceRecord, key: str) -> float:
    value = trace.evaluation.get(key)
    if isinstance(value, int | float):
        return float(value)
    if key == "citation_accuracy":
        if not trace.gold_citations:
            return 1.0 if not trace.predicted_citations else 0.0
        return 1.0 if _predicted_matches_gold(trace) else 0.0
    if key == "groundedness":
        return 0.0 if _has_unsupported_predicted_citation(trace) else 1.0
    if key == "completeness_classification":
        expected = _expected_completeness(trace)
        if not expected:
            return 0.0
        return 1.0 if trace.completeness_status == expected else 0.0
    return 0.0


def _citation_matches(expected: dict[str, object], actual: dict[str, object]) -> bool:
    expected_node_id = _first_str(expected.get("node_id"))
    if expected_node_id:
        return expected_node_id == _first_str(actual.get("node_id"))

    for key in ("regulation_title", "source_file", "article"):
        expected_value = _first_str(expected.get(key))
        if not expected_value:
            continue
        actual_value = _first_str(actual.get(key))
        if not actual_value:
            return False
        if _normalize(key, expected_value) != _normalize(key, actual_value):
            return False

    for key in ("clause", "item", "sub_item"):
        expected_value = _first_str(expected.get(key))
        if not expected_value:
            continue
        actual_value = _first_str(actual.get(key))
        if not actual_value:
            return False
        if _normalize(key, expected_value) != _normalize(key, actual_value):
            return False
    return True


def _normalize(key: str, value: str) -> str:
    if key == "source_file":
        return str(Path(value).resolve())
    if key == "clause":
        return (
            value if value.startswith("제") and value.endswith("항") else f"제{value}항"
        )
    if key == "item":
        return (
            value if value.startswith("제") and value.endswith("호") else f"제{value}호"
        )
    if key == "sub_item":
        return value if value.endswith("목") else f"{value}목"
    return value.strip()


def _evidence_rank(evidence: dict[str, object]) -> int:
    value = evidence.get("rank")
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return 999_999


def _ordered_categories(
    categories: set[ErrorCategory],
) -> tuple[ErrorCategory, ...]:
    if categories == {ErrorCategory.NO_ERROR}:
        return (ErrorCategory.NO_ERROR,)
    categories.discard(ErrorCategory.NO_ERROR)
    ordered = [category for category in _PRIMARY_PRIORITY if category in categories]
    remaining = sorted(
        (category for category in categories if category not in _PRIMARY_PRIORITY),
        key=lambda category: category.value,
    )
    return tuple([*ordered, *remaining])


def _object(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return cast(dict[str, object], value)
    return {}


def _first_str(*values: object) -> str:
    for value in values:
        if isinstance(value, str) and value:
            return value
    return ""
