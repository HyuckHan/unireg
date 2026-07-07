"""Deterministic BM25 retrieval baseline."""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass

from unireg.retrieval.corpus import RetrievalDocument

_TOKEN_PATTERN = re.compile(r"[0-9A-Za-z가-힣]+")
_HANGUL_PATTERN = re.compile(r"[가-힣]")


@dataclass(frozen=True, slots=True)
class BM25SearchHit:
    """One ranked BM25 result."""

    document: RetrievalDocument
    score: float
    rank: int

    def to_dict(self) -> dict[str, object]:
        return {
            "rank": self.rank,
            "score": self.score,
            "document": self.document.to_dict(),
        }


class BM25Index:
    """Small in-process BM25 index for reproducible baselines."""

    def __init__(
        self,
        documents: list[RetrievalDocument],
        *,
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        self._documents = documents
        self._k1 = k1
        self._b = b
        self._term_frequencies = [
            Counter(tokenize(document.text)) for document in documents
        ]
        self._document_lengths = [
            sum(frequencies.values()) for frequencies in self._term_frequencies
        ]
        self._average_document_length = (
            sum(self._document_lengths) / len(self._document_lengths)
            if self._document_lengths
            else 0.0
        )
        self._document_frequencies = self._build_document_frequencies()

    @property
    def documents(self) -> list[RetrievalDocument]:
        return self._documents

    def search(
        self,
        query: str,
        *,
        top_k: int = 5,
        filter_document: Callable[[RetrievalDocument], bool] | None = None,
    ) -> list[BM25SearchHit]:
        """Return ranked documents for a query."""

        if top_k <= 0:
            return []
        query_terms = tokenize(query)
        if not query_terms:
            return []

        scored: list[tuple[float, RetrievalDocument]] = []
        for index, document in enumerate(self._documents):
            if filter_document is not None and not filter_document(document):
                continue
            score = self._score(query_terms, index)
            if score <= 0.0:
                continue
            scored.append((score, document))

        scored.sort(key=lambda item: (-item[0], item[1].document_id))
        return [
            BM25SearchHit(document=document, score=score, rank=rank)
            for rank, (score, document) in enumerate(scored[:top_k], start=1)
        ]

    def _score(self, query_terms: list[str], document_index: int) -> float:
        frequencies = self._term_frequencies[document_index]
        document_length = self._document_lengths[document_index]
        score = 0.0
        for term in query_terms:
            term_frequency = frequencies.get(term, 0)
            if term_frequency == 0:
                continue
            document_frequency = self._document_frequencies.get(term, 0)
            score += self._idf(document_frequency) * self._term_score(
                term_frequency,
                document_length,
            )
        return score

    def _term_score(self, term_frequency: int, document_length: int) -> float:
        if self._average_document_length == 0.0:
            return 0.0
        denominator = term_frequency + self._k1 * (
            1 - self._b + self._b * document_length / self._average_document_length
        )
        return term_frequency * (self._k1 + 1) / denominator

    def _idf(self, document_frequency: int) -> float:
        document_count = len(self._documents)
        return math.log(
            1 + (document_count - document_frequency + 0.5) / (document_frequency + 0.5)
        )

    def _build_document_frequencies(self) -> dict[str, int]:
        document_frequencies: dict[str, int] = {}
        for frequencies in self._term_frequencies:
            for term in frequencies:
                document_frequencies[term] = document_frequencies.get(term, 0) + 1
        return document_frequencies


def tokenize(text: str) -> list[str]:
    """Tokenize Korean legal text without external dependencies."""

    tokens: list[str] = []
    for raw_token in _TOKEN_PATTERN.findall(text.casefold()):
        tokens.append(raw_token)
        if _HANGUL_PATTERN.search(raw_token):
            tokens.extend(_character_ngrams(raw_token, n=2))
            tokens.extend(_character_ngrams(raw_token, n=3))
    return tokens


def _character_ngrams(value: str, *, n: int) -> list[str]:
    if len(value) < n:
        return []
    return [value[index : index + n] for index in range(0, len(value) - n + 1)]
