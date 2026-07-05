"""Dataclasses for the UniRegBench benchmark schema."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import cast


class Answerability(StrEnum):
    """Supported answerability labels for benchmark questions."""

    ANSWERABLE = "answerable"
    PARTIALLY_ANSWERABLE = "partially_answerable"
    MISSING_REGULATION = "missing_regulation"
    UNANSWERABLE = "unanswerable"
    COMPARISON = "comparison"
    MULTI_HOP = "multi_hop"


@dataclass(frozen=True, slots=True, kw_only=True)
class GoldCitation:
    """A gold legal citation used by retrieval and QA benchmarks."""

    article: str | None = None
    clause: str | None = None
    item: str | None = None
    sub_item: str | None = None
    node_id: str | None = None
    regulation_title: str | None = None
    source_file: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "article": self.article,
            "clause": self.clause,
            "item": self.item,
            "sub_item": self.sub_item,
            "node_id": self.node_id,
            "regulation_title": self.regulation_title,
            "source_file": self.source_file,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> GoldCitation:
        return cls(
            article=_optional_str(data, "article"),
            clause=_optional_str(data, "clause"),
            item=_optional_str(data, "item"),
            sub_item=_optional_str(data, "sub_item"),
            node_id=_optional_str(data, "node_id"),
            regulation_title=_optional_str(data, "regulation_title"),
            source_file=_optional_str(data, "source_file"),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class BenchmarkQuestion:
    """One benchmark question stored in JSONL."""

    id: str
    question: str
    answerability: Answerability
    gold_citations: list[GoldCitation] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "question": self.question,
            "answerability": self.answerability.value,
            "gold_citations": [citation.to_dict() for citation in self.gold_citations],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> BenchmarkQuestion:
        return cls(
            id=_required_str(data, "id"),
            question=_required_str(data, "question"),
            answerability=Answerability(_required_str(data, "answerability")),
            gold_citations=[
                GoldCitation.from_dict(item)
                for item in _dict_list(data, "gold_citations")
            ],
            metadata=_str_dict(data, "metadata"),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class RetrievalPrediction:
    """Ranked retrieval output for one question."""

    question_id: str
    ranked_citations: list[GoldCitation]
    metadata: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "question_id": self.question_id,
            "ranked_citations": [
                citation.to_dict() for citation in self.ranked_citations
            ],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> RetrievalPrediction:
        return cls(
            question_id=_required_str(data, "question_id"),
            ranked_citations=[
                GoldCitation.from_dict(item)
                for item in _dict_list(data, "ranked_citations")
            ],
            metadata=_str_dict(data, "metadata"),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ParserBenchmarkCase:
    """Parser benchmark case with stable expected structural properties."""

    id: str
    source_file: str
    expected_title: str | None = None
    expected_chapter_count: int | None = None
    expected_article_count: int | None = None
    expected_clause_count: int | None = None
    min_article_count: int | None = None
    min_clause_count: int | None = None
    min_citation_count: int | None = None
    required_citations: list[GoldCitation] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "source_file": self.source_file,
            "expected_title": self.expected_title,
            "expected_chapter_count": self.expected_chapter_count,
            "expected_article_count": self.expected_article_count,
            "expected_clause_count": self.expected_clause_count,
            "min_article_count": self.min_article_count,
            "min_clause_count": self.min_clause_count,
            "min_citation_count": self.min_citation_count,
            "required_citations": [
                citation.to_dict() for citation in self.required_citations
            ],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ParserBenchmarkCase:
        return cls(
            id=_required_str(data, "id"),
            source_file=_required_str(data, "source_file"),
            expected_title=_optional_str(data, "expected_title"),
            expected_chapter_count=_optional_int(data, "expected_chapter_count"),
            expected_article_count=_optional_int(data, "expected_article_count"),
            expected_clause_count=_optional_int(data, "expected_clause_count"),
            min_article_count=_optional_int(data, "min_article_count"),
            min_clause_count=_optional_int(data, "min_clause_count"),
            min_citation_count=_optional_int(data, "min_citation_count"),
            required_citations=[
                GoldCitation.from_dict(item)
                for item in _dict_list(data, "required_citations")
            ],
            metadata=_str_dict(data, "metadata"),
        )


def _required_str(data: dict[str, object], key: str) -> str:
    value = data[key]
    if not isinstance(value, str):
        raise TypeError(f"Expected '{key}' to be str.")
    return value


def _optional_str(data: dict[str, object], key: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError(f"Expected '{key}' to be str or None.")
    return value


def _optional_int(data: dict[str, object], key: str) -> int | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, int):
        raise TypeError(f"Expected '{key}' to be int or None.")
    return value


def _dict_list(data: dict[str, object], key: str) -> list[dict[str, object]]:
    value = data.get(key, [])
    if not isinstance(value, list):
        raise TypeError(f"Expected '{key}' to be list.")
    if not all(isinstance(item, dict) for item in value):
        raise TypeError(f"Expected every item in '{key}' to be object.")
    return cast(list[dict[str, object]], value)


def _str_dict(data: dict[str, object], key: str) -> dict[str, str]:
    value = data.get(key, {})
    if not isinstance(value, dict):
        raise TypeError(f"Expected '{key}' to be object.")
    if not all(isinstance(item_key, str) for item_key in value):
        raise TypeError(f"Expected every key in '{key}' to be str.")
    if not all(isinstance(item_value, str) for item_value in value.values()):
        raise TypeError(f"Expected every value in '{key}' to be str.")
    return cast(dict[str, str], value)
