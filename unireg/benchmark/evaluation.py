"""Evaluation routines for UniRegBench."""

from __future__ import annotations

import csv
import json
import math
import statistics
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from unireg.benchmark.loader import BenchmarkDataset
from unireg.benchmark.models import (
    BenchmarkQuestion,
    GoldCitation,
    ParserBenchmarkCase,
    RetrievalPrediction,
)
from unireg.benchmark.validation import ValidationIssue
from unireg.citations import CitationGenerator
from unireg.models import Article, Regulation
from unireg.parser import RegulationParser


@dataclass(frozen=True, slots=True)
class RetrievalMetrics:
    """Standard retrieval metrics for ranked citation output."""

    question_count: int
    evaluated_question_count: int
    recall_at_1: float
    recall_at_3: float
    recall_at_5: float
    mrr: float
    ndcg_at_5: float

    def to_dict(self) -> dict[str, object]:
        return {
            "question_count": self.question_count,
            "evaluated_question_count": self.evaluated_question_count,
            "recall_at_1": self.recall_at_1,
            "recall_at_3": self.recall_at_3,
            "recall_at_5": self.recall_at_5,
            "mrr": self.mrr,
            "ndcg_at_5": self.ndcg_at_5,
        }


@dataclass(frozen=True, slots=True)
class RetrievalEvaluationResult:
    """Retrieval evaluation result."""

    metrics: RetrievalMetrics
    per_question: list[dict[str, object]]

    def to_dict(self) -> dict[str, object]:
        return {
            "metrics": self.metrics.to_dict(),
            "per_question": self.per_question,
        }


@dataclass(frozen=True, slots=True)
class ParserCaseResult:
    """Parser evaluation result for one source document."""

    id: str
    source_file: str
    ok: bool
    title: str = ""
    chapter_count: int = 0
    article_count: int = 0
    clause_count: int = 0
    citation_count: int = 0
    article_extraction_accuracy: float = 0.0
    clause_extraction_accuracy: float = 0.0
    hierarchy_preservation: float = 0.0
    citation_generation: float = 0.0
    metadata_completeness: float = 0.0
    error: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "source_file": self.source_file,
            "ok": self.ok,
            "title": self.title,
            "chapter_count": self.chapter_count,
            "article_count": self.article_count,
            "clause_count": self.clause_count,
            "citation_count": self.citation_count,
            "article_extraction_accuracy": self.article_extraction_accuracy,
            "clause_extraction_accuracy": self.clause_extraction_accuracy,
            "hierarchy_preservation": self.hierarchy_preservation,
            "citation_generation": self.citation_generation,
            "metadata_completeness": self.metadata_completeness,
            "error": self.error,
        }


@dataclass(frozen=True, slots=True)
class ParserEvaluationResult:
    """Parser benchmark result."""

    case_count: int
    ok_count: int
    article_extraction_accuracy: float
    clause_extraction_accuracy: float
    hierarchy_preservation: float
    citation_generation: float
    metadata_completeness: float
    cases: list[ParserCaseResult]

    def to_dict(self) -> dict[str, object]:
        return {
            "case_count": self.case_count,
            "ok_count": self.ok_count,
            "article_extraction_accuracy": self.article_extraction_accuracy,
            "clause_extraction_accuracy": self.clause_extraction_accuracy,
            "hierarchy_preservation": self.hierarchy_preservation,
            "citation_generation": self.citation_generation,
            "metadata_completeness": self.metadata_completeness,
            "cases": [case.to_dict() for case in self.cases],
        }


@dataclass(frozen=True, slots=True)
class BenchmarkRunResult:
    """Combined benchmark run result."""

    validation_issues: list[ValidationIssue] = field(default_factory=list)
    parser: ParserEvaluationResult | None = None
    retrieval: RetrievalEvaluationResult | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "validation_issues": [issue.to_dict() for issue in self.validation_issues],
            "parser": None if self.parser is None else self.parser.to_dict(),
            "retrieval": None if self.retrieval is None else self.retrieval.to_dict(),
        }


def evaluate_retrieval(
    questions: list[BenchmarkQuestion],
    predictions: list[RetrievalPrediction],
) -> RetrievalEvaluationResult:
    prediction_by_question = {
        prediction.question_id: prediction for prediction in predictions
    }
    per_question: list[dict[str, object]] = []
    reciprocal_ranks: list[float] = []
    ndcg_scores: list[float] = []
    recall_hits = {1: 0, 3: 0, 5: 0}
    evaluated = 0

    for question in questions:
        gold_citations = question.gold_citations
        if not gold_citations:
            continue
        evaluated += 1
        prediction = prediction_by_question.get(question.id)
        ranked = [] if prediction is None else prediction.ranked_citations
        hit_rank = _first_hit_rank(gold_citations, ranked)
        for cutoff in recall_hits:
            if hit_rank is not None and hit_rank <= cutoff:
                recall_hits[cutoff] += 1
        reciprocal_rank = 0.0 if hit_rank is None else 1.0 / hit_rank
        ndcg_at_5 = _ndcg_at_k(gold_citations, ranked, k=5)
        reciprocal_ranks.append(reciprocal_rank)
        ndcg_scores.append(ndcg_at_5)
        per_question.append(
            {
                "id": question.id,
                "answerability": question.answerability.value,
                "hit_rank": hit_rank,
                "reciprocal_rank": reciprocal_rank,
                "recall_at_1": 1.0 if hit_rank is not None and hit_rank <= 1 else 0.0,
                "recall_at_3": 1.0 if hit_rank is not None and hit_rank <= 3 else 0.0,
                "recall_at_5": 1.0 if hit_rank is not None and hit_rank <= 5 else 0.0,
                "ndcg_at_5": ndcg_at_5,
            }
        )

    denominator = evaluated or 1
    metrics = RetrievalMetrics(
        question_count=len(questions),
        evaluated_question_count=evaluated,
        recall_at_1=recall_hits[1] / denominator,
        recall_at_3=recall_hits[3] / denominator,
        recall_at_5=recall_hits[5] / denominator,
        mrr=sum(reciprocal_ranks) / denominator,
        ndcg_at_5=sum(ndcg_scores) / denominator,
    )
    return RetrievalEvaluationResult(metrics=metrics, per_question=per_question)


def evaluate_parser(
    dataset: BenchmarkDataset,
    *,
    parser: RegulationParser | None = None,
) -> ParserEvaluationResult:
    active_parser = parser or RegulationParser()
    citation_generator = CitationGenerator()
    cases = [
        _evaluate_parser_case(
            dataset,
            case,
            parser=active_parser,
            citation_generator=citation_generator,
        )
        for case in dataset.parser_cases
    ]
    return ParserEvaluationResult(
        case_count=len(cases),
        ok_count=sum(1 for case in cases if case.ok),
        article_extraction_accuracy=_average(
            case.article_extraction_accuracy for case in cases
        ),
        clause_extraction_accuracy=_average(
            case.clause_extraction_accuracy for case in cases
        ),
        hierarchy_preservation=_average(case.hierarchy_preservation for case in cases),
        citation_generation=_average(case.citation_generation for case in cases),
        metadata_completeness=_average(case.metadata_completeness for case in cases),
        cases=cases,
    )


def write_benchmark_reports(
    result: BenchmarkRunResult,
    report_dir: str | Path,
) -> None:
    output_dir = Path(report_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "benchmark_report.json", result.to_dict())
    _write_markdown(output_dir / "benchmark_report.md", result)
    _write_parser_csv(output_dir / "parser_report.csv", result.parser)
    _write_retrieval_csv(output_dir / "retrieval_report.csv", result.retrieval)


def _evaluate_parser_case(
    dataset: BenchmarkDataset,
    case: ParserBenchmarkCase,
    *,
    parser: RegulationParser,
    citation_generator: CitationGenerator,
) -> ParserCaseResult:
    source_path = _resolve_source_file(dataset.root, case.source_file)
    try:
        parse_result = parser.parse_file(source_path)
    except Exception as exc:  # pragma: no cover - input dependent.
        return ParserCaseResult(
            id=case.id,
            source_file=case.source_file,
            ok=False,
            error=f"{type(exc).__name__}: {exc}",
        )

    if parse_result.document is None:
        return ParserCaseResult(
            id=case.id,
            source_file=case.source_file,
            ok=False,
            error="parser returned no document",
        )

    regulation = parse_result.document.regulation
    articles = regulation.all_articles()
    clauses = [clause for article in articles for clause in article.clauses]
    citations = citation_generator.generate(parse_result, include_quotes=False)
    article_accuracy = _count_score(
        actual=len(articles),
        expected=case.expected_article_count,
        minimum=case.min_article_count,
    )
    clause_accuracy = _count_score(
        actual=len(clauses),
        expected=case.expected_clause_count,
        minimum=case.min_clause_count,
    )
    hierarchy = _required_citation_score(case.required_citations, regulation)
    citation_score = _citation_score(
        required_citations=case.required_citations,
        citation_labels=[citation.label for citation in citations],
        min_citation_count=case.min_citation_count,
    )
    metadata_score = _metadata_score(case, regulation)
    ok = (
        min(
            article_accuracy,
            clause_accuracy,
            hierarchy,
            citation_score,
            metadata_score,
        )
        >= 1.0
    )

    return ParserCaseResult(
        id=case.id,
        source_file=case.source_file,
        ok=ok,
        title=regulation.title,
        chapter_count=len(regulation.chapters),
        article_count=len(articles),
        clause_count=len(clauses),
        citation_count=len(citations),
        article_extraction_accuracy=article_accuracy,
        clause_extraction_accuracy=clause_accuracy,
        hierarchy_preservation=hierarchy,
        citation_generation=citation_score,
        metadata_completeness=metadata_score,
    )


def _count_score(
    *,
    actual: int,
    expected: int | None,
    minimum: int | None,
) -> float:
    if expected is not None:
        if expected == 0:
            return 1.0 if actual == 0 else 0.0
        return max(0.0, 1.0 - abs(actual - expected) / expected)
    if minimum is not None:
        if minimum == 0:
            return 1.0
        return min(1.0, actual / minimum)
    return 1.0


def _required_citation_score(
    required_citations: list[GoldCitation],
    regulation: Regulation,
) -> float:
    if not required_citations:
        return 1.0
    article_map = {
        (article.article_number, article.title): article
        for article in regulation.all_articles()
    }
    hits = 0
    for required in required_citations:
        if _find_article(required, article_map) is not None:
            hits += 1
    return hits / len(required_citations)


def _citation_score(
    *,
    required_citations: list[GoldCitation],
    citation_labels: list[str],
    min_citation_count: int | None,
) -> float:
    count_score = _count_score(
        actual=len(citation_labels),
        expected=None,
        minimum=min_citation_count,
    )
    if not required_citations:
        return count_score
    hits = 0
    for required in required_citations:
        if any(_label_matches_required(label, required) for label in citation_labels):
            hits += 1
    return min(count_score, hits / len(required_citations))


def _metadata_score(case: ParserBenchmarkCase, regulation: Regulation) -> float:
    checks = [
        bool(regulation.title),
        bool(regulation.source_file),
    ]
    if case.expected_title is not None:
        checks.append(regulation.title == case.expected_title)
    if case.expected_chapter_count is not None:
        checks.append(len(regulation.chapters) == case.expected_chapter_count)
    return sum(1 for check in checks if check) / len(checks)


def _find_article(
    required: GoldCitation,
    article_map: dict[tuple[str, str | None], Article],
) -> Article | None:
    if required.article is None:
        return None
    for (article_number, _title), article in article_map.items():
        if article_number != required.article:
            continue
        return article
    return None


def _label_matches_required(label: str, required: GoldCitation) -> bool:
    if required.article is not None and required.article not in label:
        return False
    if required.clause is not None and _normalized_clause(required.clause) not in label:
        return False
    if required.item is not None and _normalized_item(required.item) not in label:
        return False
    if (
        required.sub_item is not None
        and _normalized_sub_item(required.sub_item) not in label
    ):
        return False
    return True


def _first_hit_rank(
    gold_citations: list[GoldCitation],
    ranked_citations: list[GoldCitation],
) -> int | None:
    for index, citation in enumerate(ranked_citations, start=1):
        if _is_relevant_citation(citation, gold_citations):
            return index
    return None


def _ndcg_at_k(
    gold_citations: list[GoldCitation],
    ranked_citations: list[GoldCitation],
    *,
    k: int,
) -> float:
    if not gold_citations or k <= 0:
        return 0.0
    gains = _relevance_gains_at_k(gold_citations, ranked_citations, k=k)
    dcg = _discounted_gain(gains)
    ideal_relevant_count = min(len(gold_citations), k)
    idcg = _discounted_gain([1.0] * ideal_relevant_count)
    if idcg == 0:
        return 0.0
    return dcg / idcg


def _discounted_gain(gains: list[float]) -> float:
    return sum(gain / math.log2(index + 2) for index, gain in enumerate(gains))


def _relevance_gains_at_k(
    gold_citations: list[GoldCitation],
    ranked_citations: list[GoldCitation],
    *,
    k: int,
) -> list[float]:
    matched_gold_indexes: set[int] = set()
    gains: list[float] = []
    for candidate in ranked_citations[:k]:
        matched_index = _first_unmatched_gold_index(
            candidate,
            gold_citations,
            matched_gold_indexes,
        )
        if matched_index is None:
            gains.append(0.0)
            continue
        matched_gold_indexes.add(matched_index)
        gains.append(1.0)
    return gains


def _first_unmatched_gold_index(
    candidate: GoldCitation,
    gold_citations: list[GoldCitation],
    matched_gold_indexes: set[int],
) -> int | None:
    for index, gold in enumerate(gold_citations):
        if index in matched_gold_indexes:
            continue
        if _citation_matches(gold, candidate):
            return index
    return None


def _is_relevant_citation(
    candidate: GoldCitation,
    gold_citations: list[GoldCitation],
) -> bool:
    return any(_citation_matches(gold, candidate) for gold in gold_citations)


def _citation_matches(gold: GoldCitation, candidate: GoldCitation) -> bool:
    if gold.node_id is not None:
        return candidate.node_id == gold.node_id

    checks = [
        (gold.regulation_title, candidate.regulation_title, _normalize_plain),
        (gold.source_file, candidate.source_file, _normalize_path),
        (gold.article, candidate.article, _normalize_plain),
        (gold.clause, candidate.clause, _normalized_clause),
        (gold.item, candidate.item, _normalized_item),
        (gold.sub_item, candidate.sub_item, _normalized_sub_item),
    ]
    for expected, actual, normalizer in checks:
        if expected is None:
            continue
        if actual is None:
            return False
        if normalizer(expected) != normalizer(actual):
            return False
    return True


def _normalize_plain(value: str) -> str:
    return value.strip()


def _normalize_path(value: str) -> str:
    return str(Path(value))


def _normalized_clause(value: str) -> str:
    if value.startswith("제") and value.endswith("항"):
        return value
    return f"제{value}항"


def _normalized_item(value: str) -> str:
    if value.startswith("제") and value.endswith("호"):
        return value
    return f"제{value}호"


def _normalized_sub_item(value: str) -> str:
    if value.endswith("목"):
        return value
    return f"{value}목"


def _average(values: Iterable[float]) -> float:
    collected = list(values)
    if not collected:
        return 0.0
    return statistics.fmean(collected)


def _resolve_source_file(benchmark_root: Path, source_file: str) -> Path:
    path = Path(source_file)
    if path.is_absolute():
        return path
    return benchmark_root.parent / path


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _write_markdown(path: Path, result: BenchmarkRunResult) -> None:
    lines = ["# UniRegBench Report", ""]
    lines.append(f"- Validation issues: {len(result.validation_issues)}")
    if result.parser is not None:
        parser = result.parser
        lines.extend(
            [
                "",
                "## Parser",
                "",
                f"- Cases: {parser.ok_count}/{parser.case_count}",
                "- Article extraction accuracy: "
                f"{parser.article_extraction_accuracy:.3f}",
                "- Clause extraction accuracy: "
                f"{parser.clause_extraction_accuracy:.3f}",
                f"- Hierarchy preservation: {parser.hierarchy_preservation:.3f}",
                f"- Citation generation: {parser.citation_generation:.3f}",
                f"- Metadata completeness: {parser.metadata_completeness:.3f}",
            ]
        )
    if result.retrieval is not None:
        metrics = result.retrieval.metrics
        lines.extend(
            [
                "",
                "## Retrieval",
                "",
                f"- Evaluated questions: {metrics.evaluated_question_count}",
                f"- Recall@1: {metrics.recall_at_1:.3f}",
                f"- Recall@3: {metrics.recall_at_3:.3f}",
                f"- Recall@5: {metrics.recall_at_5:.3f}",
                f"- MRR: {metrics.mrr:.3f}",
                f"- nDCG@5: {metrics.ndcg_at_5:.3f}",
            ]
        )
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _write_parser_csv(
    path: Path,
    result: ParserEvaluationResult | None,
) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "id",
                "source_file",
                "ok",
                "title",
                "chapter_count",
                "article_count",
                "clause_count",
                "citation_count",
                "article_extraction_accuracy",
                "clause_extraction_accuracy",
                "hierarchy_preservation",
                "citation_generation",
                "metadata_completeness",
                "error",
            ],
        )
        writer.writeheader()
        if result is None:
            return
        for case in result.cases:
            writer.writerow(case.to_dict())


def _write_retrieval_csv(
    path: Path,
    result: RetrievalEvaluationResult | None,
) -> None:
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
        if result is None:
            return
        for row in result.per_question:
            writer.writerow(row)
