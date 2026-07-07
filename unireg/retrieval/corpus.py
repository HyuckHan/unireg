"""Build retrieval documents from parsed regulation projections."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from unireg.benchmark.loader import BenchmarkDataset
from unireg.benchmark.models import GoldCitation
from unireg.models import NodeType, ParseResult
from unireg.parser import RegulationParser
from unireg.projections import BM25Document, ProjectionBuilder

DEFAULT_RETRIEVAL_UNIT_TYPES: tuple[NodeType, ...] = (
    NodeType.ARTICLE,
    NodeType.CLAUSE,
    NodeType.ITEM,
    NodeType.SUB_ITEM,
)

_UNIT_ALIASES = {
    "article": NodeType.ARTICLE,
    "articles": NodeType.ARTICLE,
    "clause": NodeType.CLAUSE,
    "clauses": NodeType.CLAUSE,
    "item": NodeType.ITEM,
    "items": NodeType.ITEM,
    "sub_item": NodeType.SUB_ITEM,
    "sub_items": NodeType.SUB_ITEM,
    "sub-item": NodeType.SUB_ITEM,
    "sub-items": NodeType.SUB_ITEM,
    "subitem": NodeType.SUB_ITEM,
    "subitems": NodeType.SUB_ITEM,
}


@dataclass(frozen=True, slots=True, kw_only=True)
class RetrievalDocument:
    """One searchable legal unit."""

    document_id: str
    node_id: str
    node_type: NodeType
    text: str
    citation: GoldCitation
    citation_label: str
    source_label: str
    source_file: str
    source_pages: list[int]
    metadata: dict[str, str]

    def to_dict(self) -> dict[str, object]:
        return {
            "document_id": self.document_id,
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "text": self.text,
            "citation": self.citation.to_dict(),
            "citation_label": self.citation_label,
            "source_label": self.source_label,
            "source_file": self.source_file,
            "source_pages": self.source_pages,
            "metadata": self.metadata,
        }


def parse_retrieval_unit_types(value: str | Iterable[str]) -> tuple[NodeType, ...]:
    """Parse CLI unit names into stable node types."""

    if isinstance(value, str):
        raw_units = [part.strip() for part in value.split(",")]
    else:
        raw_units = [part.strip() for part in value]

    parsed: list[NodeType] = []
    for raw_unit in raw_units:
        if not raw_unit:
            continue
        normalized = raw_unit.lower().replace("-", "_")
        node_type = _UNIT_ALIASES.get(normalized)
        if node_type is None:
            raise ValueError(f"Unsupported retrieval unit: {raw_unit}")
        if node_type not in parsed:
            parsed.append(node_type)
    if not parsed:
        raise ValueError("At least one retrieval unit is required.")
    return tuple(parsed)


def build_retrieval_documents(
    parse_results: Iterable[ParseResult],
    *,
    unit_types: Iterable[NodeType] = DEFAULT_RETRIEVAL_UNIT_TYPES,
    projection_builder: ProjectionBuilder | None = None,
) -> list[RetrievalDocument]:
    """Build searchable retrieval units from parser output."""

    active_builder = projection_builder or ProjectionBuilder()
    allowed_types = set(unit_types)
    documents: list[RetrievalDocument] = []
    for parse_result in parse_results:
        projection = active_builder.build(parse_result)
        for document in projection.bm25_documents:
            if document.node_type not in allowed_types:
                continue
            documents.append(_from_bm25_document(document))
    return documents


def build_retrieval_documents_from_benchmark(
    dataset: BenchmarkDataset,
    *,
    parser: RegulationParser | None = None,
    unit_types: Iterable[NodeType] = DEFAULT_RETRIEVAL_UNIT_TYPES,
    projection_builder: ProjectionBuilder | None = None,
) -> list[RetrievalDocument]:
    """Parse benchmark source files and build retrieval units."""

    active_parser = parser or RegulationParser()
    source_files = sorted({case.source_file for case in dataset.parser_cases})
    parse_results = [
        active_parser.parse_file(_resolve_source_file(dataset.root, source_file))
        for source_file in source_files
    ]
    return build_retrieval_documents(
        parse_results,
        unit_types=unit_types,
        projection_builder=projection_builder,
    )


def _from_bm25_document(document: BM25Document) -> RetrievalDocument:
    source_file = document.metadata.get("source_file", "")
    return RetrievalDocument(
        document_id=document.document_id,
        node_id=document.node_id,
        node_type=document.node_type,
        text=_search_text(document),
        citation=_citation_from_document(document),
        citation_label=document.citation_label,
        source_label=document.source_label,
        source_file=source_file,
        source_pages=_source_pages(document),
        metadata=document.metadata,
    )


def _citation_from_document(document: BM25Document) -> GoldCitation:
    metadata = document.metadata
    return GoldCitation(
        node_id=document.node_id,
        regulation_title=metadata.get("regulation_title"),
        article=metadata.get("article_number"),
        clause=metadata.get("clause_number"),
        item=metadata.get("item_number"),
        sub_item=metadata.get("sub_item_number"),
        source_file=metadata.get("source_file"),
    )


def _search_text(document: BM25Document) -> str:
    metadata_keys = [
        "institution",
        "regulation_title",
        "regulation_code",
        "source_file",
        "chapter_title",
        "section_title",
        "article_number",
        "article_title",
        "clause_number",
        "item_number",
        "sub_item_number",
        "citation_label",
    ]
    metadata_text = " ".join(
        value
        for key in metadata_keys
        if (value := document.metadata.get(key)) is not None
    )
    return "\n".join(
        part for part in [document.title, document.text, metadata_text] if part
    )


def _source_pages(document: BM25Document) -> list[int]:
    source_span = document.source_span
    if source_span is None or source_span.page_start is None:
        return []
    page_end = source_span.page_end or source_span.page_start
    return list(range(source_span.page_start, page_end + 1))


def _resolve_source_file(benchmark_root: Path, source_file: str) -> Path:
    path = Path(source_file)
    if path.is_absolute():
        return path
    return benchmark_root.parent / path
