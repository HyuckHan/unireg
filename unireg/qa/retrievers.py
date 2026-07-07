"""Retriever adapters for grounded QA."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from unireg.benchmark.loader import BenchmarkDataset
from unireg.models import NodeType
from unireg.parser import RegulationParser
from unireg.retrieval.bm25 import BM25Index, BM25SearchHit
from unireg.retrieval.corpus import (
    DEFAULT_RETRIEVAL_UNIT_TYPES,
    RetrievalDocument,
    build_retrieval_documents_from_benchmark,
)
from unireg.retrieval.runner import RetrievalScope


class EvidenceRetriever(ABC):
    """Retriever boundary for QA pipelines."""

    @abstractmethod
    def retrieve(
        self,
        question: str,
        *,
        metadata: dict[str, str] | None = None,
    ) -> list[BM25SearchHit]:
        """Return ranked evidence hits for a question."""

    @abstractmethod
    def trace_config(self) -> dict[str, object]:
        """Return reproducible retriever configuration."""


@dataclass(frozen=True, slots=True, kw_only=True)
class BM25EvidenceRetrieverConfig:
    """Configuration for BM25 QA retrieval."""

    top_k: int = 5
    scope: RetrievalScope = RetrievalScope.QUESTION_SOURCE
    unit_types: tuple[NodeType, ...] = DEFAULT_RETRIEVAL_UNIT_TYPES

    def to_dict(self) -> dict[str, object]:
        return {
            "method": "bm25",
            "top_k": self.top_k,
            "scope": self.scope.value,
            "unit_types": [unit_type.value for unit_type in self.unit_types],
        }


class BM25EvidenceRetriever(EvidenceRetriever):
    """BM25 retriever adapter used by the grounded QA pipeline."""

    def __init__(
        self,
        *,
        dataset: BenchmarkDataset,
        parser: RegulationParser | None = None,
        config: BM25EvidenceRetrieverConfig | None = None,
    ) -> None:
        self._dataset = dataset
        self._config = config or BM25EvidenceRetrieverConfig()
        self._documents = build_retrieval_documents_from_benchmark(
            dataset,
            parser=parser,
            unit_types=self._config.unit_types,
        )
        self._index = BM25Index(self._documents)

    def retrieve(
        self,
        question: str,
        *,
        metadata: dict[str, str] | None = None,
    ) -> list[BM25SearchHit]:
        return self._index.search(
            question,
            top_k=self._config.top_k,
            filter_document=self._document_filter(metadata or {}),
        )

    def trace_config(self) -> dict[str, object]:
        return {
            **self._config.to_dict(),
            "benchmark_root": str(self._dataset.root),
            "document_count": len(self._documents),
        }

    def _document_filter(
        self,
        metadata: dict[str, str],
    ) -> Callable[[RetrievalDocument], bool] | None:
        if self._config.scope == RetrievalScope.CORPUS:
            return None
        source_file = metadata.get("source_file")
        if source_file is None:
            return None
        expected = Path(source_file).resolve()
        return lambda document: Path(document.source_file).resolve() == expected
